"""
컨텍스트 인식 AI 에이전트 메인 엔트리포인트 (Context-Aware Agent Main Entry Point)
"""

import os
import sys
import argparse
import logging
from agent import ContextAwareAgent, ContextMode
from config import PROVIDERS, SUPPORTED_PROVIDERS, canonical_provider, resolve_backend
from grounding import assess_groundedness, observation_quantities
import json
from pathlib import Path
import subprocess
import time
from typing import Dict, Any, List
from tabulate import tabulate
try:
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _completed(result: Dict[str, Any]) -> bool:
    """Return terminal-response status with compatibility for old results."""
    return bool(result.get("completed", result.get("success", False)))


def _outcome(result: Dict[str, Any]) -> str:
    """Say what an arm did, not merely whether it stopped.

    ``Completed`` is true for both ways an ablated arm can end without the
    answer, and they are not the same event.  A model told to convert
    currencies with no conversion tool may say it cannot, or may supply the
    exchange rates from memory and present the arithmetic as if it had looked
    them up.  The second reads as a clean success in every column this suite
    used to print.

    Args:
        result: A single test result.

    Returns:
        ``no_terminal_response``, ``unsupported_numbers`` or ``completed``.
    """
    if not _completed(result):
        return "no_terminal_response"
    if result.get("grounding_verdict") == "ungrounded":
        return "unsupported_numbers"
    return "completed"


# Load .env so API keys configured there are available via os.getenv.
# (config.py calls load_dotenv() too, but main.py only imports agent, which
#  does not import config, so we must trigger it here.)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# How the groundedness verdict reads in a table cell.
_GROUNDING_LABEL = {
    "grounded": "from task",
    "ungrounded": "UNSUPPORTED",
    "not_assessable": "saw tools",
    "no_quantities": "none",
    "no_answer": "-",
}

_OUTCOME_MARK = {
    "completed": "✓",
    "unsupported_numbers": "⚠",
    "no_terminal_response": "✗",
}


class AblationTestSuite:
    """컨텍스트 중요성을 소거 연구(ablation study)를 통해 탐구하기 위한 테스트 스위트"""
    
    def __init__(self, api_key: str, provider: str = "siliconflow", model: str = None):
        """
        테스트 스위트 초기화
        
        Args:
            api_key: LLM 제공자의 API 키
            provider: 사용할 LLM 제공자
            model: 선택적 모델 오버라이드
        """
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.test_results = []
        
    def create_complex_financial_task(self) -> str:
        """
        다중 도구 호출 및 추론이 필요한 복잡한 재무 작업 생성
        
        Returns:
            작업 설명 텍스트
        """
        return """Analyze the financial report from this PDF: https://www.berkshirehathaway.com/qtrly/1stqtr23.pdf

Please complete the following analysis:
1. Extract the total revenue figures from Q1 2023
2. Convert the revenue from USD to EUR, GBP, and JPY
3. Calculate the following metrics:
   - Average revenue across the three converted currencies
   - Percentage difference between highest and lowest converted values
   - If the company maintains a 15% profit margin, what would be the profit in each currency?

Provide a comprehensive financial summary with all calculations shown."""
    
    def create_multinational_budget_task(self) -> str:
        """
        다중 환율 변환 및 계산이 필요한 작업 생성
        
        Returns:
            작업 설명 텍스트
        """
        return """A multinational company has the following Q1 2024 expenses documented in this report:
https://raw.githubusercontent.com/adobe/pdfservices-node-sdk-samples/master/resources/extractPDFInput.pdf

Tasks to complete:
1. Parse the PDF and extract all monetary values mentioned
2. The company operates in 5 regions with expenses in different currencies:
   - US Office: $2,500,000 USD
   - UK Office: £1,800,000 GBP  
   - Japan Office: ¥380,000,000 JPY
   - EU Office: €2,100,000 EUR
   - Singapore Office: $3,200,000 SGD
3. Convert all expenses to USD for consolidation
4. Calculate:
   - Total global expenses in USD
   - Average expense per region
   - What percentage each region represents of total expenses
   - If we apply a 8% cost reduction uniformly, what would be the new expense for each region in their local currency?

Present a detailed financial analysis with all conversions and calculations."""
    
    def run_single_test(self, task: str, context_mode: ContextMode, test_name: str,
                        case_name: str = "default") -> Dict[str, Any]:
        """
        단일 소거 테스트 실행

        Args:
            task: 실행할 작업
            context_mode: 테스트할 컨텍스트 모드
            test_name: 테스트 이름
            case_name: 이 테스트가 속한 케이스/작업 이름

        Returns:
            테스트 결과 사전
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"테스트 실행 중: {test_name} [케이스: {case_name}]")
        logger.info(f"컨텍스트 모드: {context_mode.value}")
        logger.info(f"{'='*60}")

        agent = ContextAwareAgent(self.api_key, context_mode, provider=self.provider, model=self.model)

        start_time = time.time()
        result = agent.execute_task(task)
        execution_time = time.time() - start_time
        completed = _completed(result)

        # Read the observations from the messages that were actually sent. In
        # the no-tool-results arm the harness ran the tools but the model was
        # shown a placeholder, so the numbers it saw are none.
        sent = [
            message
            for turn in result["trajectory"].api_turns
            for message in (turn.get("request") or {}).get("messages", [])
        ]
        grounding = assess_groundedness(
            result.get("final_answer"), task, observation_quantities(sent)
        )

        # Analyze the result
        test_result = {
            "test_name": test_name,
            "case_name": case_name,
            "context_mode": context_mode.value,
            "execution_time": round(execution_time, 2),
            "iterations": result.get("iterations", 0),
            "num_tool_calls": len(result["trajectory"].tool_calls),
            # This legacy suite has no task-specific correctness rubric. Keep
            # ``success`` as a compatibility alias, but report completion
            # separately so a refusal is not presented as task success.
            "completed": completed,
            "success": completed,
            "task_success": None,
            "has_final_answer": result.get("final_answer") is not None,
            # No task rubric here, so correctness stays unknown -- but whether
            # the answer's figures had any source at all does not need one.
            "grounding_verdict": grounding["verdict"],
            "observation_count": grounding["observation_count"],
            "unsupported_quantities": grounding["unsupported_quantities"],
            "error": result.get("error"),
            "reasoning_steps": len(result["trajectory"].reasoning_steps),
            "final_answer_preview": (result.get("final_answer", "")[:200] + "...") if result.get("final_answer") else None
        }
        
        # Log summary
        logger.info(f"Test completed in {test_result['execution_time']}s")
        logger.info(f"Terminal response completed: {test_result['completed']}")
        if test_result["grounding_verdict"] == "ungrounded":
            logger.warning(
                "Answer states %d figure(s) with no observation behind them: %s",
                len(test_result["unsupported_quantities"]),
                test_result["unsupported_quantities"],
            )
        logger.info(f"Tool calls made: {test_result['num_tool_calls']}")
        logger.info(f"Iterations: {test_result['iterations']}")
        
        if test_result["error"]:
            logger.error(f"오류 발생: {test_result['error']}")
        
        return test_result
    
    def run_ablation_study(self, context_modes: List[ContextMode] = None,
                          cases: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        지정된 컨텍스트 모드 및 하나 이상의 케이스에 대해 소거 연구 실행.

        Args:
            context_modes: 테스트할 컨텍스트 모드 목록 (기본값: 모든 모드)
            cases: 각 모드에서 실행할 {"name", "task"} 사전 목록.
                   기본값은 단일 다국적 예산 케이스 (기존 단일 작업 동작 유지).

        Returns:
            테스트 결과 평탄화 목록 (케이스 x 모드당 1개 항목).
        """
        # 기본값: 단일 다국적 예산 케이스 (기존 동작 유지).
        if cases is None:
            cases = [{
                "name": "Multinational Budget",
                "task": self.create_multinational_budget_task()
            }]

        # 컨텍스트 모드와 테스트 이름 매핑
        mode_names = {
            ContextMode.FULL: "Baseline - Full Context",
            ContextMode.NO_HISTORY: "Ablation 1 - No Historical Tool Calls",
            ContextMode.NO_REASONING: "Ablation 2 - No Reasoning Process",
            ContextMode.NO_TOOL_CALLS: "Ablation 3 - No Tool Call Commands",
            ContextMode.NO_TOOL_RESULTS: "Ablation 4 - No Tool Call Results"
        }

        if context_modes is None:
            context_modes = list(mode_names.keys())

        results = []
        for case in cases:
            case_name = case["name"]
            task = case["task"]
            for context_mode in context_modes:
                test_name = mode_names[context_mode]
                try:
                    result = self.run_single_test(task, context_mode, test_name, case_name=case_name)
                    results.append(result)
                    self.test_results.append(result)

                    # 레이트 리밋 방지를 위한 테스트 간 지연 시간 추가
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"테스트 실패 {test_name} [케이스: {case_name}]: {str(e)}")
                    results.append({
                        "test_name": test_name,
                        "case_name": case_name,
                        "context_mode": context_mode.value,
                        "error": str(e),
                        "completed": False,
                        "success": False,
                        "task_success": False,
                    })

        return results
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        소거 연구 결과 분석
        
        Args:
            results: 테스트 결과 목록
            
        Returns:
            분석 요약
        """
        analysis = {
            "total_tests": len(results),
            "completed_tests": sum(1 for r in results if _completed(r)),
            # Compatibility key for existing report consumers. It now counts
            # terminal responses, not verified task successes.
            "successful_tests": sum(1 for r in results if _completed(r)),
            # Terminal responses whose figures no observation supports. This
            # suite cannot say an answer is wrong without a rubric, but it can
            # say the model had nothing to compute from.
            "unsupported_number_tests": sum(
                1 for r in results if r.get("grounding_verdict") == "ungrounded"
            ),
            "unsupported_number_modes": sorted(
                {
                    r["context_mode"]
                    for r in results
                    if r.get("grounding_verdict") == "ungrounded"
                }
            ),
            "context_mode_impact": {}
        }
        
        # 각 소거의 영향 분석
        baseline = next((r for r in results if r["context_mode"] == "full"), None)
        
        if baseline:
            for result in results:
                if result["context_mode"] != "full":
                    mode_analysis = {
                        "completion_maintained": _completed(result),
                        "success_maintained": _completed(result),
                        "stated_unsupported_numbers": result.get("grounding_verdict")
                        == "ungrounded",
                        "execution_time_delta": result.get("execution_time", 0) - baseline.get("execution_time", 0),
                        "iteration_delta": result.get("iterations", 0) - baseline.get("iterations", 0),
                        "tool_call_delta": result.get("num_tool_calls", 0) - baseline.get("num_tool_calls", 0),
                        "failure_reason": None
                    }
                    
                    # Identify failure reasons
                    if result.get("grounding_verdict") == "ungrounded":
                        mode_analysis["failure_reason"] = (
                            "Answered with figures no tool observation supports"
                        )
                    elif not _completed(result):
                        if result["context_mode"] == "no_tool_calls":
                            mode_analysis["failure_reason"] = "도구 정의 없이는 도구를 실행할 수 없음"
                        elif result["context_mode"] == "no_tool_results":
                            mode_analysis["failure_reason"] = "도구 결과 없이는 정보에 입각한 결정을 내릴 수 없음"
                        elif result["context_mode"] == "no_history":
                            mode_analysis["failure_reason"] = "행동을 반복하거나 진행 상황을 잊어버릴 수 있음"
                        elif result["context_mode"] == "no_reasoning":
                            mode_analysis["failure_reason"] = "전략적 계획 및 사고가 부족함"
                    
                    analysis["context_mode_impact"][result["context_mode"]] = mode_analysis
        
        return analysis
    
    def print_results_table(self, results: List[Dict[str, Any]]):
        """
        결과를 포맷된 표 형태로 출력
        
        Args:
            results: 테스트 결과 목록
        """
        # 표 출력을 위한 데이터 준비
        table_data = []
        for result in results:
            table_data.append([
                result.get("case_name", "default"),
                result["context_mode"],
                "✓" if _completed(result) else "✗",
                _GROUNDING_LABEL.get(result.get("grounding_verdict"), "-"),
                f"{result.get('execution_time', 0)}s",
                result.get("iterations", 0),
                result.get("num_tool_calls", 0),
                result.get("reasoning_steps", 0),
                "Yes" if result.get("has_final_answer", False) else "No"
            ])

        headers = ["Case", "Context Mode", "Completed", "Figures", "Time", "Iterations", "Tool Calls", "Reasoning Steps", "Final Answer"]

        print("\n" + "="*80)
        print("ABLATION STUDY RESULTS (소거 연구 결과)")
        print("="*80)
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def print_comparison_matrix(self, results: List[Dict[str, Any]]):
        """
        모든 케이스에 걸쳐 각 컨텍스트 구성 요소의 영향을 한눈에 파악할 수 있도록
        모드 x 케이스 비교 매트릭스를 출력합니다.

        Args:
            results: 테스트 결과 목록
        """
        cases = []
        for r in results:
            c = r.get("case_name", "default")
            if c not in cases:
                cases.append(c)

        modes = []
        for r in results:
            m = r["context_mode"]
            if m not in modes:
                modes.append(m)

        # 빠른 조회를 위해 (모드, 케이스) 키로 결과 인덱싱
        by_key = {(r["context_mode"], r.get("case_name", "default")): r for r in results}

        table_data = []
        for mode in modes:
            row = [mode]
            for case in cases:
                r = by_key.get((mode, case))
                if r is None:
                    row.append("-")
                else:
                    counts = f"{r.get('iterations', 0)}it/{r.get('num_tool_calls', 0)}tc"
                    row.append(f"{_OUTCOME_MARK[_outcome(r)]} {counts}")
            table_data.append(row)

        headers = ["Context Mode"] + cases
        print("\n" + "="*80)
        print("COMPARISON MATRIX (rows = context mode, cols = case; cell = outcome it=iterations tc=tool calls)")
        print("  ✓ terminal response   ⚠ terminal response built on figures no observation supports   ✗ no terminal response")
        print("="*80)
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def visualize_results(self, results: List[Dict[str, Any]]):
        """
        소거 연구 결과 시각화 차트 생성
        
        Args:
            results: 테스트 결과 목록
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib을 사용할 수 없어 시각화를 건너뜁니다")
            return
            
        # 시각화용 데이터 추출
        modes = [r["context_mode"] for r in results]
        iterations = [r.get("iterations", 0) for r in results]
        tool_calls = [r.get("num_tool_calls", 0) for r in results]
        exec_times = [r.get("execution_time", 0) for r in results]
        success = [1 if _completed(r) else 0 for r in results]
        
        # 서브플롯 생성
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle("Ablation Study: Impact of Context Components", fontsize=16)
        
        # Plot 1: terminal-response completion rate
        axes[0, 0].bar(modes, success, color=['green' if s else 'red' for s in success])
        axes[0, 0].set_title("Terminal Responses by Context Mode")
        axes[0, 0].set_ylabel("Completed (1) / No response (0)")
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 그래프 2: 필요한 반복 횟수
        axes[0, 1].bar(modes, iterations, color='blue')
        axes[0, 1].set_title("Iterations Required")
        axes[0, 1].set_ylabel("Number of Iterations")
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 그래프 3: 도구 호출 횟수
        axes[1, 0].bar(modes, tool_calls, color='orange')
        axes[1, 0].set_title("Tool Calls Made")
        axes[1, 0].set_ylabel("Number of Tool Calls")
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 그래프 4: 실행 시간
        axes[1, 1].bar(modes, exec_times, color='purple')
        axes[1, 1].set_title("Execution Time")
        axes[1, 1].set_ylabel("Time (seconds)")
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig("ablation_study_results.png", dpi=150, bbox_inches='tight')
        logger.info("시각화 차트가 'ablation_study_results.png' 파일로 저장되었습니다")
    
    def generate_report(self, results: List[Dict[str, Any]], analysis: Dict[str, Any]) -> str:
        """
        소거 연구 종합 보고서 생성
        
        Args:
            results: 테스트 결과 목록
            analysis: 분석 요약
            
        Returns:
            보고서 텍스트
        """
        report = """
# Context Ablation Study Report (컨텍스트 소거 연구 보고서)

## Executive Summary
This ablation study explores the effect of different context components on AI
agent behavior. This legacy suite reports terminal-response completion and
tool-use behavior; it does not claim task correctness without a task-specific
rubric.

## Test Configuration (테스트 설정)
- **Provider**: {provider}
- **Model**: {model}
- **Task**: Complex financial analysis requiring PDF parsing, currency conversion, and calculations
- **Context Modes Tested**: {num_modes}

## Key Findings (주요 발견 사항)

### 1. Complete Lack of Historical Tool Calls (NO_HISTORY)
**Impact**: Agent loses track of previous actions and may repeat operations unnecessarily.
- **Behavior**: Agent cannot reference past tool executions, leading to redundant API calls
- **Performance**: {no_history_perf}
- **Critical for**: Multi-step tasks requiring sequential dependencies

### 2. Lack of Reasoning Process (NO_REASONING)
**Impact**: Agent operates without strategic planning or step-by-step thinking.
- **Behavior**: Direct execution without planning leads to inefficient or incorrect solutions
- **Performance**: {no_reasoning_perf}
- **Critical for**: Complex tasks requiring logical decomposition

### 3. Lack of Tool Call Commands (NO_TOOL_CALLS)
**Impact**: Agent cannot execute any external tools.
- **Behavior**: The model may return a refusal or describe the missing tools;
  a terminal response is not evidence that the financial task was completed.
- **Performance**: {no_tool_calls_perf}
- **Critical for**: Any task requiring external data or computation

### 4. Lack of Tool Call Results (NO_TOOL_RESULTS)
**Impact**: Agent operates blind to the outcomes of its actions.
- **Behavior**: The model may stop with a warning, repeat actions, or produce an
  incorrect conclusion; correctness must be checked by a task-specific rubric.
- **Performance**: {no_tool_results_perf}
- **Critical for**: Tasks requiring iterative refinement or result validation

## Statistical Summary (통계 요약)
- **Total Tests Run**: {total_tests}
- **Terminal Responses**: {successful_tests}
- **Answers Stating Unsupported Figures**: {unsupported_number_tests} {unsupported_number_modes}
- **Average Execution Time (Full Context)**: {avg_exec_time}s
- **Average Tool Calls (Full Context)**: {avg_tool_calls}

## Conclusion
The ablation study records how each context component changes execution behavior:
1. **Tool calls** determine whether the agent can interact with external tools
2. **Tool results** provide feedback for decision-making
3. **Reasoning** can affect planning and execution efficiency
4. **History** can prevent redundant actions and maintain task coherence

Task-level claims require a separate evaluator, such as the canonical numeric
rubric used by `run_experiment_1_1.py`.

## Recommendations (권장 사항)
- Always maintain complete context for production agents
- Consider context windowing rather than removal for memory optimization
- Implement fallback mechanisms when context components are unavailable
"""
        
        # 성능 지표 문자열 가져오기
        def get_perf_string(mode):
            mode_result = next((r for r in results if r["context_mode"] == mode), None)
            if mode_result:
                return f"{'COMPLETED' if _completed(mode_result) else 'NO TERMINAL RESPONSE'} - {mode_result.get('iterations', 0)} iterations, {mode_result.get('execution_time', 0)}s"
            return "N/A"
        
        # 기준 지표 계산
        baseline = next((r for r in results if r["context_mode"] == "full"), None)
        avg_exec_time = baseline.get("execution_time", 0) if baseline else 0
        avg_tool_calls = baseline.get("num_tool_calls", 0) if baseline else 0
        
        report = report.format(
            provider=self.provider,
            model=self.model or "default",
            num_modes=len(results),
            no_history_perf=get_perf_string("no_history"),
            no_reasoning_perf=get_perf_string("no_reasoning"),
            no_tool_calls_perf=get_perf_string("no_tool_calls"),
            no_tool_results_perf=get_perf_string("no_tool_results"),
            total_tests=analysis["total_tests"],
            successful_tests=analysis["successful_tests"],
            unsupported_number_tests=analysis.get("unsupported_number_tests", 0),
            unsupported_number_modes=analysis.get("unsupported_number_modes", []) or "",
            avg_exec_time=avg_exec_time,
            avg_tool_calls=avg_tool_calls
        )
        
        return report


def run_single_task(api_key: str, task: str, context_mode: str = "full", provider: str = "siliconflow", model: str = None, output: str = None):
    """
    에이전트로 단일 작업 실행

    Args:
        api_key: LLM 제공자의 API 키
        task: 작업 설명
        context_mode: 사용할 컨텍스트 모드
        provider: 사용할 LLM 제공자
        model: 선택적 모델 오버라이드
        output: JSON 결과를 저장할 선택적 경로 (기본값: task_result_{mode}.json)
    """
    # 컨텍스트 모드 파싱
    mode_map = {
        "full": ContextMode.FULL,
        "no_history": ContextMode.NO_HISTORY,
        "no_reasoning": ContextMode.NO_REASONING,
        "no_tool_calls": ContextMode.NO_TOOL_CALLS,
        "no_tool_results": ContextMode.NO_TOOL_RESULTS
    }
    
    if context_mode not in mode_map:
        logger.error(f"Invalid context mode: {context_mode}")
        logger.info(f"Valid modes: {', '.join(mode_map.keys())}")
        return
    
    # 에이전트 생성
    agent = ContextAwareAgent(api_key, mode_map[context_mode], provider=provider, model=model)
    
    logger.info(f"Running task with context mode: {context_mode}")
    logger.info(f"Task: {task[:100]}...")
    
    # Execute task
    result = agent.execute_task(task)
    
    # Print results
    print("\n" + "="*60)
    print("TASK EXECUTION RESULT (작업 실행 결과)")
    print("="*60)
    print(f"Context Mode: {context_mode}")
    print(f"Terminal response completed: {_completed(result)}")
    print(f"Iterations: {result.get('iterations', 0)}")
    print(f"Tool Calls: {len(result['trajectory'].tool_calls)}")
    
    if result.get('final_answer'):
        print(f"\nFinal Answer (최종 답변):")
        print("-"*40)
        print(result['final_answer'])
    
    if result.get('error'):
        print(f"\nError (오류): {result['error']}")
    
    # 상세 결과 저장
    output_file = output or f"task_result_{context_mode}.json"
    with open(output_file, 'w') as f:
        # Convert trajectory to serializable format
        serializable_result = {
            "completed": _completed(result),
            "task_success": result.get("task_success"),
            # Backwards-compatible alias for older result readers.
            "success": _completed(result),
            "iterations": result.get("iterations", 0),
            "final_answer": result.get("final_answer"),
            "error": result.get("error"),
            "context_mode": context_mode,
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "arguments": tc.arguments,
                    "result": tc.result,
                    "timestamp": tc.timestamp
                }
                for tc in result["trajectory"].tool_calls
            ],
            "reasoning_steps": result["trajectory"].reasoning_steps,
            # Credential-free, provider-native request/response evidence.  The
            # ablation is about the context visible on each inference, so a
            # post-hoc summary is not sufficient to validate Experiment 1-1.
            "api_turns": result["trajectory"].api_turns,
            "provider": result.get("provider", provider),
            "model": result.get("model", model),
            "base_url": result.get("base_url"),
            "using_openrouter": result.get("using_openrouter", False),
        }
        json.dump(serializable_result, f, indent=2)
    
    logger.info(f"상세 결과가 {output_file} 파일에 저장되었습니다.")


def ensure_sample_pdfs():
    """
    샘플 PDF 파일이 존재하는지 확인하고 없으면 생성

    Returns:
        bool: PDF 사용 가능 여부
    """
    pdf_dir = Path("fixtures/pdfs")
    sample_pdf = pdf_dir / "simple_expense_report.pdf"
    
    if not pdf_dir.exists() or not sample_pdf.exists():
        print("\n📚 샘플 PDF를 찾을 수 없습니다. 생성 중...")
        try:
            # PDF 생성 스크립트 실행
            result = subprocess.run(
                [sys.executable, "create_sample_pdf.py"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print("✅ fixtures/pdfs/ 디렉토리에 샘플 PDF가 생성되었습니다")
                return True
            else:
                print(f"⚠️ PDF를 생성할 수 없습니다: {result.stderr}")
                return False
        except Exception as e:
            print(f"⚠️ PDF 생성 중 오류 발생: {str(e)}")
            return False
    return True


def get_sample_tasks():
    """
    테스트용 샘플 작업 목록 가져오기
    
    Returns:
        list: 샘플 작업 사전 목록
    """
    # 로컬 실행 여부 확인 또는 온라인 PDF 사용
    local_pdfs = Path("fixtures/pdfs").exists()
    
    if local_pdfs:
        pdf_path = "file://" + str(Path.cwd() / "fixtures/pdfs" / "simple_expense_report.pdf")
        pdf_note = "Using local PDF"
    else:
        # 테스트용 공개 샘플 PDF 사용
        pdf_path = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        pdf_note = "Using online sample PDF"
    
    return [
        {
            "name": "📊 환율 변환 작업 (Currency Conversion Task)",
            "description": "다중 통화 간 환율 변환",
            "task": """Convert $1000 USD to EUR, GBP, and JPY. 
Then calculate the average value across all three converted currencies."""
        },
        {
            "name": "📄 PDF 분석 작업 (PDF Analysis Task)",
            "description": f"PDF 문서 데이터 추출 및 분석 ({pdf_note})",
            "task": f"""Analyze this PDF document: {pdf_path}
Extract any text content and provide a summary of what you found."""
        },
        {
            "name": "💰 Complex Financial Analysis",
            "description": "Multi-step financial calculation",
            "task": """A company has the following quarterly revenues:
- Q1: $2,500,000 USD
- Q2: €2,100,000 EUR
- Q3: £1,800,000 GBP
- Q4: ¥380,000,000 JPY

Please:
1. Convert all revenues to USD
2. Calculate the total annual revenue in USD
3. Determine the average quarterly revenue
4. Find which quarter had the highest revenue
5. If the company has a 20% profit margin, calculate the annual profit in USD"""
        },
        {
            "name": "🌍 Multi-Currency Budget Planning",
            "description": "International budget calculations",
            "task": """An international conference has the following budget allocations:
- Venue (UK): £45,000
- Speakers (US): $75,000
- Catering (France): €38,000
- Technology (Japan): ¥8,500,000
- Marketing (Singapore): S$25,000

Tasks:
1. Convert all amounts to USD
2. Calculate the total budget
3. Determine what percentage each category represents
4. If we need to cut the budget by 15%, how much should each category be reduced to (in their original currencies)?"""
        },
        {
            "name": "📈 Investment Portfolio Analysis",
            "description": "Analyze international investment returns",
            "task": """An investor has the following international investments with their current values:
- US Tech Stocks: $125,000 (purchased for $100,000)
- European Bonds: €85,000 (purchased for €90,000)
- UK Real Estate: £200,000 (purchased for £175,000)
- Japanese ETFs: ¥15,000,000 (purchased for ¥12,000,000)

Calculate:
1. Convert all current values to USD
2. Convert all purchase prices to USD (use current exchange rates for simplicity)
3. Calculate the profit/loss for each investment in USD
4. Determine the total portfolio value and overall return percentage
5. Which investment performed best in percentage terms?"""
        }
    ]


def get_ablation_cases(num_cases: int = 1) -> List[Dict[str, str]]:
    """
    소거 연구를 위한 독립 실행형 케이스 목록을 생성합니다.

    사전 정의된 샘플 작업 중 네트워크 접속이 필요한 PDF 작업을 제외한
    재무/환율 작업들을 재사용합니다. num_cases=1은 단일 케이스를 반환하며,
    더 큰 값은 추가 케이스를 포함합니다.

    Args:
        num_cases: 포함할 케이스 수 ([1, 사용 가능 수] 범위로 조절됨).

    Returns:
        {"name", "task"} 사전 목록.
    """
    samples = get_sample_tasks()
    # 인덱스 0/2/3/4는 통화/재무 작업 (인덱스 1은 PDF 작업).
    candidates = [samples[0], samples[2], samples[3], samples[4]]
    num_cases = max(1, min(num_cases, len(candidates)))
    return [{"name": c["name"], "task": c["task"]} for c in candidates[:num_cases]]


def run_ablation_study(api_key: str, provider: str = "siliconflow", model: str = None,
                       context_modes: List[str] = None, num_cases: int = 1,
                       output: str = None):
    """
    컨텍스트의 중요성을 테스트하기 위해 소거 연구 실행

    Args:
        api_key: LLM 제공자의 API 키
        provider: 사용할 LLM 제공자
        model: 선택적 모델 오버라이드
        context_modes: 테스트할 컨텍스트 모드 이름 목록 (기본값: 전체)
        num_cases: 각 모드에서 실행할 케이스 수 (기본값 1: 기존 단일 다국적 예산 작업 유지; >1: 샘플 작업 간 다중 케이스 비교)
        output: 원시 JSON 결과를 저장할 선택적 경로 (기본값: ablation_results.json)
    """
    # 컨텍스트 모드 파싱
    mode_map = {
        "full": ContextMode.FULL,
        "no_history": ContextMode.NO_HISTORY,
        "no_reasoning": ContextMode.NO_REASONING,
        "no_tool_calls": ContextMode.NO_TOOL_CALLS,
        "no_tool_results": ContextMode.NO_TOOL_RESULTS
    }

    modes_to_test = None
    if context_modes:
        modes_to_test = []
        for mode_name in context_modes:
            if mode_name in mode_map:
                modes_to_test.append(mode_map[mode_name])
            else:
                logger.error(f"유효하지 않은 컨텍스트 모드: {mode_name}")
                logger.info(f"유효한 모드: {', '.join(mode_map.keys())}")
                return

    # 케이스 구축. num_cases <= 1 일 때 기존 단일 케이스 동작 유지.
    cases = None
    if num_cases and num_cases > 1:
        cases = get_ablation_cases(num_cases)

    test_suite = AblationTestSuite(api_key, provider=provider, model=model)

    logger.info("소거 연구 시작 중...")
    if modes_to_test:
        logger.info(f"테스트 모드: {', '.join(context_modes)}")
    else:
        logger.info("모든 컨텍스트 모드 테스트 중")
    logger.info(f"케이스 수: {len(cases) if cases else 1}")

    results = test_suite.run_ablation_study(modes_to_test, cases=cases)

    # 결과 분석
    analysis = test_suite.analyze_results(results)

    # 결과 표 출력
    test_suite.print_results_table(results)

    # 모드 x 케이스 비교 매트릭스 출력
    test_suite.print_comparison_matrix(results)

    # 시각화 차트 생성
    try:
        test_suite.visualize_results(results)
    except Exception as e:
        logger.warning(f"시각화 차트를 생성할 수 없습니다: {str(e)}")

    # 보고서 생성 및 저장
    report = test_suite.generate_report(results, analysis)
    with open("ablation_study_report.md", "w") as f:
        f.write(report)
    logger.info("보고서가 'ablation_study_report.md' 파일로 저장되었습니다")

    # 원시 결과 저장
    output_file = output or "ablation_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"원시 결과가 '{output_file}' 파일로 저장되었습니다")
    
    # 분석 요약 출력
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY (분석 요약)")
    print("="*80)
    print(f"Terminal Response Rate: {analysis['completed_tests']}/{analysis['total_tests']}")
    print("\nContext Mode Impacts:")
    for mode, impact in analysis["context_mode_impact"].items():
        print(f"\n{mode.upper()}:")
        print(f"  - Completion Maintained: {impact['completion_maintained']}")
        print(f"  - Execution Time Delta: {impact['execution_time_delta']:.2f}s")
        print(f"  - Iteration Delta: {impact['iteration_delta']}")
        print(f"  - Tool Call Delta: {impact['tool_call_delta']}")
        if impact['failure_reason']:
            print(f"  - Failure Reason (실패 원인): {impact['failure_reason']}")


def interactive_mode(api_key: str, provider: str = "siliconflow", model: str = None):
    """
    대화형 모드로 에이전트 실행
    
    Args:
        api_key: LLM 제공자의 API 키
        provider: 사용할 LLM 제공자
        model: 선택적 모델 오버라이드
    """
    # 현재 제공자 및 모델 저장
    current_provider = provider
    current_model = model
    current_api_key = api_key
    
    # 사용 가능한 제공자 목록
    available_providers = list(SUPPORTED_PROVIDERS)
    
    print("\n" + "="*60)
    print("INTERACTIVE MODE - Context-Aware Agent (대화형 모드 - 컨텍스트 인식 에이전트)")
    print(f"Provider: {current_provider.upper()} | Model: {current_model or 'default'}")
    print("="*60)
    print("사용 가능한 명령어:")
    print("  - 작업/질문 직접 입력")
    print("  - 'samples': 샘플 작업 목록 확인")
    print("  - 'sample <번호>': 특정 샘플 작업 실행")
    print("  - 'create_pdfs': 샘플 PDF 파일 생성")
    print("  - 'providers': 사용 가능한 제공자 목록")
    print("  - 'provider <이름>': 제공자 변경")
    print("  - 'modes': 사용 가능한 컨텍스트 모드 목록")
    print("  - 'mode <모드이름>': 컨텍스트 모드 변경")
    print("  - 'reset': 에이전트 궤적/이력 초기화")
    print("  - 'status': 현재 설정 상태 확인")
    print("  - 'help': 전체 명령어 안내")
    print("  - 'quit': 종료")
    print("-"*60)
    
    # 샘플 PDF 존재 여부 확인
    ensure_sample_pdfs()
    
    # 샘플 작업 가져오기
    sample_tasks = get_sample_tasks()
    
    # 전체 컨텍스트 모드로 에이전트 초기화
    mode_map = {
        "full": ContextMode.FULL,
        "no_history": ContextMode.NO_HISTORY,
        "no_reasoning": ContextMode.NO_REASONING,
        "no_tool_calls": ContextMode.NO_TOOL_CALLS,
        "no_tool_results": ContextMode.NO_TOOL_RESULTS
    }
    
    current_mode = ContextMode.FULL
    agent = ContextAwareAgent(current_api_key, current_mode, provider=current_provider, model=current_model)
    
    while True:
        try:
            # 프롬프트에 현재 제공자 표시
            prompt = f"\n[{current_provider.upper()}]> "
            user_input = input(prompt).strip()
            
            if user_input.lower() == 'quit':
                print("종료합니다!")
                break
            
            elif user_input.lower() == 'help':
                print("\n📚 사용 가능한 명령어:")
                print("  samples          - 사용할 수 있는 샘플 작업 목록 보기")
                print("  sample <n>       - n번째 샘플 작업 실행")
                print("  providers        - 지원되는 LLM 제공자 목록 보기")
                print("  provider <name>  - 다른 제공자로 전환")
                print("  modes            - 사용할 수 있는 컨텍스트 모드 목록 보기")
                print("  mode <name>      - 컨텍스트 모드 전환")
                print("  status           - 현재 설정 상태 확인")
                print("  reset            - 에이전트 궤적/이력 초기화")
                print("  create_pdfs      - 샘플 PDF 파일 생성")
                print("  help             - 이 도움말 메시지 보기")
                print("  quit             - 대화형 모드 종료")
                print("\n또는 실행하고자 하는 작업/질문을 직접 입력하세요.")
            
            elif user_input.lower() == 'samples':
                print("\n📋 사용 가능한 샘플 작업 목록:")
                for i, sample in enumerate(sample_tasks, 1):
                    print(f"\n{i}. {sample['name']}")
                    print(f"   {sample['description']}")
            
            elif user_input.lower().startswith('sample '):
                try:
                    sample_num = int(user_input.split()[1])
                    if 1 <= sample_num <= len(sample_tasks):
                        sample = sample_tasks[sample_num - 1]
                        print(f"\n📌 실행 중: {sample['name']}")
                        print(f"Task: {sample['task']}")
                        print("\n처리 중...")
                        
                        result = agent.execute_task(sample['task'])
                        
                        print(f"\n{'='*40}")
                        print(f"Terminal response completed: {_completed(result)}")
                        print(f"Iterations: {result.get('iterations', 0)}")
                        print(f"Tool Calls: {len(result['trajectory'].tool_calls)}")
                        
                        if result.get('final_answer'):
                            print(f"\nAnswer:")
                            print(result['final_answer'])
                        
                        if result.get('error'):
                            print(f"\nError: {result['error']}")
                    else:
                        print(f"유효하지 않은 샘플 번호입니다. 'sample 1'부터 'sample {len(sample_tasks)}'까지 사용하세요.")
                except (ValueError, IndexError):
                    print(f"유효하지 않은 샘플 번호입니다. 'sample 1'부터 'sample {len(sample_tasks)}'까지 사용하세요.")
            
            elif user_input.lower() == 'create_pdfs':
                print("\n📄 샘플 PDF 생성 중...")
                try:
                    result = subprocess.run(
                        [sys.executable, "create_sample_pdf.py"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        print("✅ fixtures/pdfs/ 디렉토리에 샘플 PDF가 성공적으로 생성되었습니다.")
                        # 새 PDF 경로로 샘플 작업 업데이트
                        sample_tasks = get_sample_tasks()
                    else:
                        print(f"⚠️ PDF를 생성할 수 없습니다: {result.stderr}")
                except Exception as e:
                    print(f"⚠️ PDF 생성 중 오류 발생: {str(e)}")
            
            elif user_input.lower() == 'providers':
                print("\n🔌 사용 가능한 제공자:")
                for p in available_providers:
                    status = " (현재)" if p == current_provider else ""
                    spec = PROVIDERS.get(canonical_provider(p))
                    if spec is None:
                        print(f"  - {p}{status}")
                        continue
                    if not spec.requires_key:
                        keys = "API 키 불필요"
                    else:
                        keys = " / ".join(spec.key_vars)
                        keys += " ✓" if spec.api_key() else " (미설정)"
                    print(f"  - {p}: {spec.default_model} [{keys}]{status}")
            
            elif user_input.lower().startswith('provider '):
                new_provider = user_input[9:].strip().lower()
                if new_provider in available_providers:
                    try:
                        new_backend = resolve_backend(new_provider)
                    except ValueError as exc:
                        print(f"❌ {exc}")
                        continue
                    new_api_key = "" if new_backend.using_openrouter else new_backend.api_key

                    # 현재 설정 업데이트
                    current_provider = new_provider
                    current_api_key = new_api_key
                    current_model = None  # 새 제공자의 기본 모델을 사용하도록 리셋
                    
                    # 새 제공자로 새 에이전트 생성
                    agent = ContextAwareAgent(current_api_key, current_mode, provider=current_provider, model=current_model)
                    
                    # config에서 기본 모델 이름 가져오기
                    from config import Config
                    default_model = Config.get_default_model(current_provider)
                    
                    print(f"✅ 제공자 변경 완료: {current_provider}")
                    print(f"   사용 모델: {default_model}")
                else:
                    print(f"❌ 유효하지 않은 제공자입니다. 사용 가능: {', '.join(available_providers)}")
            
            elif user_input.lower() == 'modes':
                print("\n🔧 사용 가능한 컨텍스트 모드:")
                for mode in mode_map.keys():
                    print(f"  - {mode}")
            
            elif user_input.lower().startswith('mode '):
                new_mode = user_input[5:].strip()
                if new_mode in mode_map:
                    current_mode = mode_map[new_mode]
                    agent = ContextAwareAgent(current_api_key, current_mode, provider=current_provider, model=current_model)
                    print(f"✅ 컨텍스트 모드 변경 완료: {current_mode.value}")
                    if current_mode != ContextMode.FULL:
                        print(f"⚠️ 경고: 이 모드는 테스트를 위해 일부 기능을 의도적으로 비활성화합니다.")
                else:
                    print(f"❌ 유효하지 않은 모드입니다. 사용 가능: {', '.join(mode_map.keys())}")
            
            elif user_input.lower() == 'reset':
                agent.reset()
                print("✅ 에이전트 궤적 및 대화 이력이 초기화되었습니다.")
            
            elif user_input.lower() == 'status':
                from config import Config
                model_name = current_model or Config.get_default_model(current_provider)
                print("\n📊 현재 설정 상태:")
                print(f"  제공자 (Provider): {current_provider.upper()}")
                print(f"  모델 (Model): {model_name}")
                print(f"  컨텍스트 모드 (Context Mode): {current_mode.value}")
                print(f"  대화 이력 메시지 수: {len(agent.conversation_history)}개")
                print(f"  도구 호출 횟수: {len(agent.trajectory.tool_calls)}회")
                
                spec = PROVIDERS.get(canonical_provider(current_provider))
                if spec is None:
                    pass
                elif not spec.requires_key:
                    print("  API Key: 불필요 (로컬 런타임)")
                else:
                    names = " / ".join(spec.key_vars)
                    key_status = "✅ 설정됨" if spec.api_key() else "❌ 미설정"
                    print(f"  API Key ({names}): {key_status}")
                    if not spec.api_key() and os.getenv("OPENROUTER_API_KEY"):
                        print("  폴백: ✅ OPENROUTER_API_KEY 설정됨 (OpenRouter를 통해 라우팅)")
            
            elif user_input:
                # 작업 실행
                print("\n처리 중...")
                result = agent.execute_task(user_input)
                
                print(f"\n{'='*40}")
                print(f"Terminal response completed: {_completed(result)}")
                print(f"Iterations: {result.get('iterations', 0)}")
                print(f"Tool Calls: {len(result['trajectory'].tool_calls)}")
                
                if result.get('final_answer'):
                    print(f"\nAnswer:")
                    print(result['final_answer'])
                
                if result.get('error'):
                    print(f"\nError: {result['error']}")
                    
        except KeyboardInterrupt:
            print("\n\n중단되었습니다. 종료하려면 'quit'을 입력하세요.")
        except Exception as e:
            print(f"Error: {str(e)}")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="컨텍스트 인식 AI 에이전트 (제1장 실험 1-1: 컨텍스트 소거 실험)",
        epilog="""사용 예시:
  # 대화형 모드 (기본값)
  python main.py

  # 전체 소거 실험 실행 (5가지 컨텍스트 모드 비교)
  python main.py --mode ablation

  # 다중 케이스 소거 비교 및 결과를 지정 파일에 저장
  python main.py --mode ablation --cases 3 --output my_ablation.json

  # '전체 컨텍스트'와 '이력 없음' 2가지 모드만 비교
  python main.py --mode ablation --ablation-modes full no_history

  # 단일 작업 실행, 지정된 컨텍스트 모드 및 제공자 사용
  python main.py --mode single --task "1000 달러를 欧元, 英镑, 日元으로 환산하고 평균 구하기" \\
      --context-mode full --provider doubao
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--mode",
        choices=["single", "ablation", "interactive"],
        default="interactive",
        help="실행 모드: single=단일 작업, ablation=소거 실험, interactive=대화형 (기본값)"
    )
    parser.add_argument(
        "--task",
        type=str,
        help="실행할 작업/질문 (single 모드용; 미지정 시 샘플 작업 중 선택)"
    )
    parser.add_argument(
        "--context-mode",
        choices=["full", "no_history", "no_reasoning", "no_tool_calls", "no_tool_results"],
        default="full",
        help="single 모드에서의 컨텍스트 모드: full=전체; no_history=이력 없음; "
             "no_reasoning=추론 과정 없음; no_tool_calls=도구 정의 없음; no_tool_results=도구 실행 결과 없음"
    )
    parser.add_argument(
        "--ablation-modes",
        nargs="+",
        choices=["full", "no_history", "no_reasoning", "no_tool_calls", "no_tool_results"],
        help="소거 실험에서 테스트할 컨텍스트 모드 목록 (기본값: 5개 모드 전체)"
    )
    parser.add_argument(
        "--cases",
        type=int,
        default=1,
        help="소거 실험에서 실행할 케이스 수 (기본값 1; >1 일 때 여러 샘플 작업에서 모드간 교차 비교)"
    )
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default="doubao",
        help="LLM 제공자 (기본값: doubao; openrouter 또는 키 누락 시 OpenRouter 폴백; ollama는 로컬 무료)"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="사용할 모델 이름 (선택 사항, 미지정 시 해당 제공자의 기본 모델 사용)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="LLM 提供商的 API Key（也可通过对应环境变量设置，例如 DASHSCOPE_API_KEY、SILICONFLOW_API_KEY、ARK_API_KEY、MOONSHOT_API_KEY、DEEPSEEK_API_KEY 或 ZHIPU_API_KEY；缺失主 key 时可用 OPENROUTER_API_KEY 兜底）"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="결과 출력 파일 경로 (single 모드는 JSON 결과, ablation 모드는 원시 결과 JSON)"
    )

    args = parser.parse_args()
    
    try:
        backend = resolve_backend(args.provider, model=args.model, api_key=args.api_key)
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    api_key = args.api_key or ""
    if backend.using_openrouter and not args.api_key:
        logger.info(
            f"{args.provider} API key가 설정되지 않아 OpenRouter(OPENROUTER_API_KEY)로 폴백합니다."
        )
    elif not args.api_key:
        api_key = backend.api_key
    
    # 제공자 정보 로깅
    logger.info(f"사용 중인 제공자: {args.provider}, 모델: {args.model or 'default'}")
    
    # 모드별 실행
    if args.mode == "single":
        if not args.task:
            # 사용자에게 샘플 작업 선택 요청
            print("\n" + "="*60)
            print("SINGLE TASK MODE - No task provided (단일 작업 모드 - 미지정)")
            print("="*60)
            
            # PDF 존재 여부 확인
            ensure_sample_pdfs()
            
            # 샘플 작업 가져오기 및 표시
            sample_tasks = get_sample_tasks()
            print("\n📋 사용 가능한 샘플 작업:")
            for i, sample in enumerate(sample_tasks, 1):
                print(f"\n{i}. {sample['name']}")
                print(f"   {sample['description']}")
            
            print("\n" + "="*60)
            try:
                choice = input("\n작업 번호를 선택하세요 (1-{}) 또는 'q'를 입력하여 종료: ".format(len(sample_tasks))).strip()
                if choice.lower() == 'q':
                    sys.exit(0)
                
                task_num = int(choice)
                if 1 <= task_num <= len(sample_tasks):
                    selected_task = sample_tasks[task_num - 1]
                    print(f"\n✅ 선택된 작업: {selected_task['name']}")
                    print("\n작업 상세 내용:")
                    print("-"*40)
                    print(selected_task['task'])
                    print("-"*40)
                    
                    confirm = input("\n이 작업을 실행하시겠습니까? (y/n): ").strip().lower()
                    if confirm == 'y':
                        run_single_task(api_key, selected_task['task'], args.context_mode,
                                      provider=args.provider, model=args.model, output=args.output)
                    else:
                        print("작업이 취소되었습니다.")
                else:
                    print(f"유효하지 않은 선택입니다. 1-{len(sample_tasks)} 사이에서 선택하세요.")
                    sys.exit(1)
            except (ValueError, KeyboardInterrupt):
                print("\n종료 중...")
                sys.exit(0)
        else:
            run_single_task(api_key, args.task, args.context_mode,
                          provider=args.provider, model=args.model, output=args.output)

    elif args.mode == "ablation":
        run_ablation_study(api_key, provider=args.provider, model=args.model,
                          context_modes=args.ablation_modes, num_cases=args.cases,
                          output=args.output)
    
    else:  # interactive
        interactive_mode(api_key, provider=args.provider, model=args.model)


if __name__ == "__main__":
    main()
