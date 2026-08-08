"""
Kimi Web Search Agent
Kimi API 기반의 지능형 검색 Agent로, 사용자 질문을 이해하고 검색 엔진을 통해 정보를 수집한 뒤 답변을 종합합니다.
"""

import json
from typing import List, Dict, Any, Optional
from openai import APITimeoutError, OpenAI, RateLimitError
from openai.types.chat.chat_completion import Choice
import logging
import os
import requests
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _reasoning_safe_temperature(model, requested=1.0):
    """Reasoning models (Kimi K3, GPT-5, ...) only accept temperature=1.
    Return 1 for those; otherwise the requested value so non-reasoning
    providers (Doubao, DeepSeek, older Moonshot) are unchanged."""
    m = str(model or "").lower().replace("/", "-")
    return 1 if ("kimi-k3" in m or "gpt-5" in m) else requested


# ReAct 궤적의 단계 유형 및 표시 라벨 (생각 → 행동 → 관찰 → 최종 답변)
STEP_LABELS = {
    "thought": ("💭", "생각"),
    "action": ("🔧", "행동"),
    "observation": ("👀", "관찰"),
    "answer": ("✅", "최종 답변"),
}


def format_trace_step(step: Dict[str, Any], max_len: int = 500) -> str:
    """하나의 ReAct 궤적 단계를 읽기 쉬운 한 줄 텍스트로 렌더링합니다.

    본 챕터에서 강조하는 '궤적(Trajectory)'을 구성합니다. 사용자 메시지,
    모델의 생각, 도구 호출, 도구 결과가 명확히 분리되어 ReAct 루프(생각→행동→관찰)를 직관적으로 보여줍니다.
    """
    icon, label = STEP_LABELS.get(step["type"], ("•", step["type"]))
    prefix = f"{icon} [{step.get('iteration', '-')}] {label}"

    if step["type"] == "action":
        args = json.dumps(step.get("args", {}), ensure_ascii=False)
        return f"{prefix}: 도구 호출 {step.get('tool')}  인수={args}"

    content = str(step.get("content", "")).strip()
    if len(content) > max_len:
        content = content[:max_len] + f"…(생략 {len(content) - max_len} 자)"
    return f"{prefix}: {content}"


def search_impl(arguments: Dict[str, Any]) -> Any:
    """
    Moonshot AI가 제공하는 검색 도구를 사용할 때는 추가 처리 로직 없이 전달받은 인수를 그대로 반환합니다.

    다른 모델을 사용하면서 인터넷 검색 기능을 유지하려면 이 구현부(예: 검색 API 호출 및 웹페이지 콘텐츠 가져오기)만 수정하면 되며,
    함수 시그니처는 동일하게 유지되어 정상 작동합니다.

    이를 통해 코드에 파괴적인 변경 없이 다양한 모델 간의 최대 호환성을 보장합니다.
    """
    return arguments


# search_and_answer는 예외를 던지지 않고 실패 시 대체 안내 문구를 문자열로 반환합니다.
# 아래의 접두사/문구는 '검색 실패 여부'를 판정하는 유일한 기준이며, 호출처(예: examples.batch_search)에서 재사용됩니다.
SEARCH_ERROR_PREFIX = "검색 과정 중 오류가 발생했습니다"
MAX_ITERATIONS_MESSAGE = "죄송합니다. 검색 과정이 최대 반복 횟수를 초과했습니다. 잠시 후 다시 시도해 주세요."
NO_INFO_MESSAGE = "죄송합니다. 질문에 답변하기에 충분한 정보를 얻지 못했습니다."


def _error_hint(exc: Exception, timeout: Optional[float] = None) -> str:
    """给 provider 故障补一句可操作的提示。

    交互模式下最常见的两种失败是速率限制和请求超时，而且两者常常连在一起：
    429 会被 SDK 自动重试，重试把超时预算耗完之后，用户只看到一句
    "Request timed out"，很容易误判成网络问题或模型能力问题。
    """
    if isinstance(exc, RateLimitError):
        return "（触发了服务商的速率限制，请降低请求频率或稍后重试）"
    if isinstance(exc, APITimeoutError):
        budget = f"超过 {timeout:.0f} 秒未返回" if timeout else "超时未返回"
        return (
            f"（请求{budget}。kimi-k3 以 reasoning_effort=max 运行，"
            "单次调用可能需要一到数分钟；若持续超时，可调大环境变量 "
            "SEARCH_TIMEOUT，并检查日志中是否有 429 导致的反复重试）"
        )
    return ""


def is_failure_answer(answer: str) -> bool:
    """search_and_answer의 반환값이 실패 대체 문구(정상 답변 생성 불가)인지 판정합니다."""
    return (
        answer.startswith(SEARCH_ERROR_PREFIX)
        or answer == MAX_ITERATIONS_MESSAGE
        or answer == NO_INFO_MESSAGE
    )


class WebSearchAgent:
    """
    Web Search Agent - Kimi Formula API 공식 검색 도구를 사용합니다.

    kimi-k3의 공식 경로는 표준 ``function`` tool 선언과
    ``moonshot/web-search:latest`` Formula Fiber 실행을 조합하여 동작합니다.
    """
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.moonshot.cn/v1",
                 model: str = "kimi-k3", verbose: bool = False):
        """
        Agent를 초기화합니다.

        Args:
            api_key: Kimi API key (제공되지 않으면 환경 변수에서 가져옴)
            base_url: API 기본 URL
            model: 사용할 모델 이름 (기본값: kimi-k3)
            verbose: ReAct 궤적(생각/행동/관찰)을 실시간으로 출력할지 여부
        """
        # 전달받은 api_key를 우선 사용하고, 없으면 환경 변수에서 로드
        # Moonshot이 기본이며, MOONSHOT_API_KEY가 없을 경우 OpenRouter가 범용 폴백으로 작동
        from config import resolve_llm_backend, Config
        primary_key = api_key or os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
        resolved_key, resolved_base_url, model, self.using_openrouter = \
            resolve_llm_backend(primary_key, base_url, model)
        if self.using_openrouter:
            logger.info(
                f"MOONSHOT_API_KEY가 설정되지 않아 OpenRouter 폴백을 사용합니다 (모델: {model}). "
                "주의: Moonshot Formula web_search 도구는 OpenRouter에서 사용할 수 없으므로, "
                "이 모드에서는 실시간 웹 검색 없이 모델 자체 지식으로만 답변합니다."
            )

        self.client = OpenAI(
            api_key=resolved_key,
            base_url=resolved_base_url,
            # 설정된 검색 타임아웃을 적용하여 백엔드 지연 시 약 10분간 블로킹되는 문제를 방지
            timeout=Config.SEARCH_TIMEOUT,
        )
        self._api_key = resolved_key
        self.base_url = resolved_base_url
        self.model = model
        self.verbose = verbose
        self.conversation_history = []
        # ReAct 궤적: 순서대로 각 단계의 생각/행동/관찰을 기록하여 디버깅 및 시각화에 사용
        self.trace: List[Dict[str, Any]] = []
        # Credential-free provider requests/responses for Experiment 1-2
        # acceptance.  Search IDs in tool arguments are intentionally retained:
        # they prove that Moonshot's hosted built-in tool actually executed.
        self.api_turns: List[Dict[str, Any]] = []
        self.formula_uri = "moonshot/web-search:latest"
        self._formula_tools: Optional[List[Dict[str, Any]]] = None
        self._request_timeout = Config.SEARCH_TIMEOUT
        self.temperature = 0.6
        # 추론 모델(Kimi K3)은 충분한 출력 토큰 예산이 필요하여 max_tokens를 넉넉히 설정
        self.max_tokens = 32768

    def _emit(self, step: Dict[str, Any]):
        """ReAct 궤적 단계를 기록하고, verbose 모드일 때 실시간으로 출력합니다."""
        self.trace.append(step)
        if self.verbose:
            print(format_trace_step(step))
        
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Kimi 공식 Formula 도구 선언을 가져오고 캐시합니다."""
        if getattr(self, "using_openrouter", False):
            return []
        if self._formula_tools is not None:
            return self._formula_tools

        url = (
            f"{self.base_url.rstrip('/')}/formulas/"
            f"{self.formula_uri}/tools"
        )
        started = time.monotonic()
        response = None
        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._request_timeout,
            )
            payload = response.json()
            response.raise_for_status()
            tools = payload.get("tools")
            if not isinstance(tools, list) or not tools:
                raise RuntimeError("Formula 선언 응답에 tools가 없습니다.")
            if not any(
                tool.get("type") == "function"
                and tool.get("function", {}).get("name") == "web_search"
                for tool in tools
            ):
                raise RuntimeError(
                    "Formula 선언에 web_search 함수가 포함되어 있지 않습니다."
                )
        except Exception as exc:
            error_payload: Dict[str, Any] = {
                "class": type(exc).__name__,
                "message": str(exc),
            }
            if response is not None:
                try:
                    error_payload["response"] = response.json()
                except ValueError:
                    error_payload["response_text"] = response.text
            self.api_turns.append({
                "kind": "formula_tools",
                "formula_uri": self.formula_uri,
                "request": {"method": "GET", "url": url},
                "http_status": getattr(response, "status_code", None),
                "elapsed_seconds": round(time.monotonic() - started, 6),
                "error": error_payload,
            })
            raise

        self.api_turns.append({
            "kind": "formula_tools",
            "formula_uri": self.formula_uri,
            "request": {"method": "GET", "url": url},
            "http_status": response.status_code,
            "response": payload,
            "elapsed_seconds": round(time.monotonic() - started, 6),
        })
        self._formula_tools = tools
        return tools

    def _execute_formula(self, name: str, raw_arguments: str) -> str:
        """모델이 요청한 Kimi Formula Fiber를 실행합니다."""
        if self.using_openrouter:
            raise RuntimeError("OpenRouter에서는 Kimi Formula 도구를 사용할 수 없습니다.")

        url = (
            f"{self.base_url.rstrip('/')}/formulas/"
            f"{self.formula_uri}/fibers"
        )
        body = {"name": name, "arguments": raw_arguments}
        started = time.monotonic()
        response = None
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=body,
                timeout=self._request_timeout,
            )
            payload = response.json()
            response.raise_for_status()
            if payload.get("status") != "succeeded":
                raise RuntimeError(
                    f"Formula Fiber 실행이 성공하지 못했습니다: {payload.get('status')!r}"
                )
            context = payload.get("context") or {}
            result = context.get("output")
            if result in (None, ""):
                result = context.get("encrypted_output")
            if result in (None, ""):
                raise RuntimeError("성공한 Formula Fiber에서 결과가 반환되지 않았습니다.")
        except Exception as exc:
            error_payload: Dict[str, Any] = {
                "class": type(exc).__name__,
                "message": str(exc),
            }
            if response is not None:
                try:
                    error_payload["response"] = response.json()
                except ValueError:
                    error_payload["response_text"] = response.text
            self.api_turns.append({
                "kind": "formula_fiber",
                "formula_uri": self.formula_uri,
                "request": {
                    "method": "POST",
                    "url": url,
                    "body": body,
                },
                "http_status": getattr(response, "status_code", None),
                "elapsed_seconds": round(time.monotonic() - started, 6),
                "error": error_payload,
            })
            raise

        self.api_turns.append({
            "kind": "formula_fiber",
            "formula_uri": self.formula_uri,
            "request": {"method": "POST", "url": url, "body": body},
            "http_status": response.status_code,
            "response": payload,
            "elapsed_seconds": round(time.monotonic() - started, 6),
        })
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)
    
    def _get_system_prompt(self) -> str:
        """
        시스템 프롬프트를 반환합니다.
        """
        return f"""당신은 지능형 검색 어시스턴트 Kimi입니다.

다음 단계에 따라 문제를 해결하세요:
1. 사용자의 질문을 분석하고 핵심 정보 요구사항을 식별합니다.
2. web_search 공식 도구를 사용하여 관련 정보를 검색합니다.
3. 추가 정보가 필요하면 검색 도구를 여러 번 호출할 수 있습니다.
4. 모든 정보를 종합하여 정확하고 포괄적인 최종 답변을 생성합니다.

주의 사항:
- 검색 시 정확한 키워드를 사용하세요.
- 최신의 신뢰할 수 있는 정보를 우선적으로 수집하세요.
- 답변은 구조가 명확하고 근거가 있어야 합니다.
"""
    
    def _chat(self, messages: List[Dict[str, Any]]) -> Choice:
        """
        Kimi API를 호출하여 대화를 수행합니다.
        
        Args:
            messages: 메시지 목록
            
        Returns:
            API 응답의 Choice 객체
        """
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=_reasoning_safe_temperature(self.model, self.temperature),
            # Kimi K3는 추론 모델이므로 reasoning_content를 길게 생성하므로,
            # 최종 답변이 잘리지 않도록 충분한 max_tokens 예산을 확보합니다.
            max_tokens=self.max_tokens,
        )
        if str(self.model).lower() == "kimi-k3":
            kwargs["reasoning_effort"] = "max"
        tools = self._get_tools()
        if tools:  # OpenRouter 폴백 시에는 내장 검색 도구가 없으므로 tools 매개변수를 생략
            kwargs["tools"] = tools
        started = time.monotonic()
        try:
            completion = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            self.api_turns.append({
                "kind": "chat_completion",
                "request": json.loads(json.dumps(kwargs, ensure_ascii=False, default=str)),
                "elapsed_seconds": round(time.monotonic() - started, 6),
                "error": {"class": type(exc).__name__, "message": str(exc)},
            })
            raise
        response = (
            completion.model_dump() if hasattr(completion, "model_dump")
            else completion.dict() if hasattr(completion, "dict")
            else {"raw_response": str(completion)}
        )
        self.api_turns.append({
            "kind": "chat_completion",
            "request": json.loads(json.dumps(kwargs, ensure_ascii=False, default=str)),
            "response": json.loads(json.dumps(response, ensure_ascii=False, default=str)),
            "elapsed_seconds": round(time.monotonic() - started, 6),
        })
        return completion.choices[0]

    def search_and_answer(self, user_question: str, max_iterations: int = 5) -> str:
        """
        검색을 수행하고 답변을 생성합니다.
        
        Args:
            user_question: 사용자 질문
            max_iterations: 최대 검색 반복 횟수 (무한 루프 방지)
            
        Returns:
            최종 답변 문자열
        """
        # 시스템 프롬프트 구성
        system_prompt = self._get_system_prompt()
        
        # 대화 이력 재설정 및 새로운 시스템 프롬프트 추가
        self.conversation_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ]
        # ReAct 궤적 초기화
        self.trace = []
        self.api_turns = []
        # Each independent question keeps its own real declaration receipt.
        self._formula_tools = None
        logger.info("Kimi 검색 도구 호출을 시작합니다...")

        try:
            finish_reason = None
            iteration = 0
            
            # 최종 답변을 얻거나 최대 반복 횟수에 도달할 때까지 루프 실행
            while (finish_reason is None or finish_reason == "tool_calls") and iteration < max_iterations:
                iteration += 1
                logger.info(f"반복 {iteration}/{max_iterations}")
                
                # Kimi API 호출
                choice = self._chat(self.conversation_history)
                finish_reason = choice.finish_reason
                
                # 모델의 사고 과정 캡처 (Kimi K3 등 추론 모델은 reasoning_content를 통해 사고 패턴 노출)
                reasoning = getattr(choice.message, "reasoning_content", None)
                if reasoning:
                    self._emit({"iteration": iteration, "type": "thought", "content": reasoning})

                if finish_reason == "tool_calls":
                    # 도구 호출 처리
                    logger.info(f"모델이 {len(choice.message.tool_calls)}개의 도구 호출을 요청했습니다.")

                    # Add assistant message (including tool calls) to history.
                    # NOTE: The message must be reconstructed into a plain dict, not
                    # using the SDK's pydantic message object directly. The latter
                    # carries extra fields like reasoning_content / refusal that cause
                    # a "tokenization failed" 400 error when sent back to Moonshot.
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": choice.message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in choice.message.tool_calls
                        ],
                    })

                    # 각 도구 호출 실행
                    for tool_call in choice.message.tool_calls:
                        tool_call_name = tool_call.function.name
                        try:
                            tool_call_arguments = json.loads(
                                tool_call.function.arguments or "{}"
                            )
                        except json.JSONDecodeError:
                            # Models sometimes emit slightly invalid JSON; match
                            # chapter4 async-agent and keep the ReAct loop alive.
                            tool_call_arguments = {}
                            logger.warning(
                                "도구 인수가 올바른 JSON이 아닙니다. 빈 객체로 계속합니다: %r",
                                tool_call.function.arguments,
                            )

                        logger.info(f"도구 실행: {tool_call_name}, 인수: {tool_call_arguments}")
                        # 행동: 도구 호출 기록
                        self._emit({"iteration": iteration, "type": "action",
                                    "tool": tool_call_name, "args": tool_call_arguments})

                        if tool_call_name == "web_search":
                            # Formula requires the original serialized
                            # arguments, even though the parsed copy above is
                            # retained for a readable ReAct trace.
                            tool_result = self._execute_formula(
                                tool_call_name,
                                tool_call.function.arguments or "{}",
                            )
                        else:
                            tool_result = f"Error: unable to find tool by name '{tool_call_name}'"

                        tool_content = (
                            tool_result
                            if isinstance(tool_result, str)
                            else json.dumps(tool_result, ensure_ascii=False)
                        )
                        # 관찰: 도구 반환 결과 기록
                        self._emit({"iteration": iteration, "type": "observation",
                                    "tool": tool_call_name, "content": tool_content})
                        # 도구 응답 메시지를 구성하여 이력에 추가
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_content
                        })
                elif finish_reason == "length":
                    # Output budget (max_tokens) exhausted leading to truncation:
                    # return the generated content with a clear note,
                    # rather than treating a partial answer as complete,
                    # or falsely reporting “no sufficient info” (content
                    # being empty at this point means the thought process
                    # already ate the whole budget).
                    partial = (choice.message.content or "").strip()
                    logger.warning("답변이 max_tokens 상한에 도달하여 잘렸습니다 (finish_reason=length)")
                    note = "(주의: 답변이 max_tokens 상한에 도달하여 잘렸습니다. max_tokens를 늘린 후 다시 시도하세요.)"
                    final = f"{partial}\n\n{note}" if partial else note
                    self._emit({"iteration": iteration, "type": "answer", "content": final})
                    # Store truncated answer in history with the note, so get_conversation_history()
                    # preserves the truncation semantic; otherwise later reuse of the history
                    # might treat the incomplete answer as ordinary/complete.
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final
                    })
                    return final
                else:
                    # 최종 답변 획득
                    if choice.message.content:
                        answer = choice.message.content
                        logger.info("답변이 성공적으로 생성되었습니다.")
                        self._emit({"iteration": iteration, "type": "answer", "content": answer})

                        # 최종 답변을 이력에 추가
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": answer
                        })

                        return answer
            
            # 최대 반복 횟수에 도달했음에도 완료되지 않은 경우
            if iteration >= max_iterations:
                logger.warning(f"최대 반복 횟수 {max_iterations}에 도달했습니다.")
                return MAX_ITERATIONS_MESSAGE

            return NO_INFO_MESSAGE
                
        except Exception as e:
            hint = _error_hint(e, getattr(self, "_request_timeout", None))
            message = f"{SEARCH_ERROR_PREFIX}: {str(e)}{hint}"
            logger.error(message)
            return message
    
    def clear_history(self):
        """대화 이력을 초기화합니다."""
        self.conversation_history = []
        logger.info("대화 이력이 초기화되었습니다.")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """대화 이력을 반환합니다."""
        return self.conversation_history

    def get_trace(self) -> List[Dict[str, Any]]:
        """가장 최근 search_and_answer의 ReAct 궤적(생각/행동/관찰/최종 답변)을 반환합니다."""
        return self.trace

    def get_api_turns(self) -> List[Dict[str, Any]]:
        """최근 질문에 대한 실제 제공자 API 증거를 반환합니다."""
        return json.loads(json.dumps(self.api_turns, ensure_ascii=False, default=str))
    
    def set_temperature(self, temperature: float):
        """
        온도(temperature) 파라미터를 설정합니다.
        
        Args:
            temperature: 온도 값 (0.0 - 2.0)
        """
        if 0.0 <= temperature <= 2.0:
            self.temperature = temperature
            logger.info(f"온도가 {temperature}(으)로 설정되었습니다.")
        else:
            logger.warning(f"유효하지 않은 온도 값입니다: {temperature} (0.0에서 2.0 사이여야 함)")


def run_offline_demo(question: str = "Moonshot AI의 Context Caching 기술이란 무엇인가요?",
                     verbose: bool = True) -> Dict[str, Any]:
    """오프라인 ReAct 루프 시연 —— API Key나 인터넷 연결이 필요 없습니다.

    본 함수는 **실제 검색을 호출하지 않고** 샘플 궤적을 재생하여,
    본 챕터에서 설명하는 '생각→행동→관찰→생각→행동→관찰' 루프를 직관적으로 보여줍니다.
    궤적 내용은 교육용 예시이며 실제 검색 결과가 아닙니다.

    Returns:
        question / trace / answer를 포함하는 딕셔너리.
    """
    trace: List[Dict[str, Any]] = [
        {"iteration": 1, "type": "thought",
         "content": "사용자가 Context Caching에 대해 알고 싶어 합니다. 이는 Moonshot의 기능이므로 먼저 공식 문서를 검색하여 정의와 역할을 확인하겠습니다."},
        {"iteration": 1, "type": "action", "tool": "web_search",
         "args": {"query": "Moonshot AI Context Caching 기술이란"}},
        {"iteration": 1, "type": "observation", "tool": "web_search",
         "content": "(샘플 결과) Context Caching은 컨텍스트 캐싱 메커니즘입니다. 반복적으로 사용되는 접두사(예: 긴 시스템 프롬프트, 문서)를 서버 측에 캐시하여 후속 요청 시 재사용함으로써 중복 연산과 비용을 줄입니다."},
        {"iteration": 2, "type": "thought",
         "content": "대략적인 정의를 확인했으나 구체적인 활용 시나리오가 부족합니다. 보다 완성도 높은 답변을 위해 일반적인 용도와 과금 방식을 한 번 더 검색하겠습니다."},
        {"iteration": 2, "type": "action", "tool": "web_search",
         "args": {"query": "Context Caching 활용 시나리오 요금"}},
        {"iteration": 2, "type": "observation", "tool": "web_search",
         "content": "(샘플 결과) 다중 턴 대화, 긴 문서에 대한 반복 질문, 고정된 시스템 프롬프트 등의 시나리오에 주로 활용됩니다. 캐시가 적중된 토큰은 일반적으로 더 저렴한 가격이 적용되며 첫 토큰 지연 시간(TTFT)을 크게 단축합니다."},
        {"iteration": 3, "type": "answer",
         "content": "Context Caching(컨텍스트 캐싱)은 Moonshot AI가 제공하는 메커니즘입니다. 반복 사용되는 컨텍스트 접두사를 서버 측에 캐시하여 후속 요청 시 재사용함으로써 중복 연산을 줄이고 비용을 절감하며 응답 속도를 향상시킵니다. 긴 시스템 프롬프트, 긴 문서 반복 질의응답, 다중 턴 대화 등의 시나리오에 매우 적합합니다. (이 내용은 오프라인 샘플 궤적이며 실제 검색 결과가 아닙니다.)"},
    ]

    if verbose:
        for step in trace:
            print(format_trace_step(step))

    answer = next(s["content"] for s in trace if s["type"] == "answer")
    return {"question": question, "trace": trace, "answer": answer}


# Independent running example

def main():
    """
    기본 사용법을 시연하는 독립 실행 예제
    """
    # Set API key (ensure MOONSHOT_API_KEY environment variable is set)
    agent = WebSearchAgent()
    
    test_question = "Moonshot AI의 Context Caching 기술에 대해 검색하고 이것이 무엇인지 알려주세요."
    
    print(f"질문: {test_question}")
    print("-" * 60)
    print("검색 중...")
    
    # Get answer
    answer = agent.search_and_answer(test_question)
    
    print("\n답변:")
    print("-" * 60)
    print(answer)


if __name__ == '__main__':
    main()
