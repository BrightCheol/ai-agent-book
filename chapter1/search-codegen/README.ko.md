# GPT-5.6 Sol 딥 리서치 (GPT-5.6 Sol Deep Research)

> 제1장 실험 1-3을 위한 Responses API 도우미: 호스팅된 `web_search` + 호스팅된 `code_interpreter`, 타입화된 도구 트레이스, 인용(citations), 그리고 의도 명확화 연속성(intent-clarification continuation). 표준 경로는 OpenAI GPT-5.6 Sol이며, 승인은 다중 제공자를 지원하며 Responses API가 서버 측에서 검색/코드 루프를 진정으로 완결하는 제공자(현재 알리바바 Model Studio DashScope `qwen3.7-plus`)에 의해 성립될 수 있습니다.

← [제1장 목차로 돌아가기](../README.ko.md) · 📖 [제1장 본문 읽기](../../book-ko/chapter1.ko.md)

---

## 본 구현 내용 (What this companion implements)

표준 경로는 유사한 이름의 도구 객체를 단순히 포함하는 Chat Completions 요청이 아니라, OpenAI **Responses API**입니다. `agent.py`의 활성 에이전트는 다음을 전송합니다:

```json
{
  "model": "gpt-5.6-sol",
  "tools": [
    {"type": "web_search", "search_context_size": "medium"},
    {
      "type": "code_interpreter",
      "container": {"type": "auto", "memory_limit": "4g"}
    }
  ],
  "reasoning": {"effort": "high"},
  "text": {"verbosity": "high"}
}
```

DashScope 백엔드는 제공자의 호스팅 도구 형태를 사용하여 `{DASHSCOPE_BASE_URL}/responses`에 대해 동일한 `/responses` 프로토콜을 사용합니다:

```json
{
  "model": "qwen3.7-plus",
  "tools": [{"type": "web_search"}, {"type": "code_interpreter"}],
  "stream": true
}
```

DashScope는 네이티브로 생각(thinking)을 실행하며(`reasoning.effort`/`text.verbosity` 조절 노브 없음), 게이트웨이가 약 60초 동안 무응답인 비스트리밍 요청을 끊기 때문에 백엔드는 항상 스트리밍 방식을 사용하고 비스트리밍 응답과 동일한 형태의 최종 `response.completed` 객체를 유지합니다.

승인(Acceptance)은 제공자 출력 항목을 기반으로 합니다. 성공적인 아세안(ASEAN) 수도 계산 실행에는 완료된 `web_search_call` 및 `code_interpreter_call` 항목, 클릭 가능한 URL 인용, 그리고 계산된 가장 가까운 수도 쌍이 포함되어야 합니다. Python을 사용했다고 단순히 밝히는 텍스트 응답은 제공자 도구 영수증(receipt) 없이 승인되지 않습니다.

두 번째 시나리오는 장에서 사용된 의도적으로 모호한 비트코인 요청을 전송하며, 도구를 사용하기 전에 첫 번째 응답이 주요 선호 사항을 명확히 할 것을 요구한 후, 사용자가 데이터 소스와 지표를 제공한 뒤 `previous_response_id`를 사용하여 계속 진행합니다.

---

## 현재 증거 상태 (Current evidence status)

다음 명령어로 전체 검증기(validator)를 실행하세요:

```bash
cd chapter1/search-codegen
python run_experiment_1_3.py --backends openai dashscope --reasoning high
```

최신 증거는 [validation/latest.json](validation/latest.json)입니다. 자격 증명이 제외된 원시 영수증, 매니페스트 및 SHA-256 파일은 `validation/runs/real_20260731T170529Z/`에 있습니다.

2026-07-31 다중 제공자 승인 실행 결과: **통과 (passed)**, 승인 백엔드로 `dashscope` (`qwen3.7-plus`) 사용.

- 아세안 수도: 모델이 발행한 10개 좌표 쿼리를 배치 처리하는 1회의 호스팅된 `web_search_call` 후, 45개 하버사인(haversine) 쌍 전체를 열거하고 쿠알라룸푸르-싱가포르 간 316.35 km(표준 좌표에서 계산된 독립적인 로컬 참조 값과 동일한 쌍)를 찾아낸 1회의 호스팅된 `code_interpreter_call`.
- 비트코인 기술적 분석: 첫 번째 턴에서는 **도구를 전혀 호출하지 않고** 어떤 데이터 소스와 지표를 사용할지 질문했으며, `previous_response_id`를 통한 연이어 진행된 턴에서는 3회의 모델 주도 검색 라운드와 MA7/MA20, RSI14, MACD(12,26,9), 기간 수익률 및 최대 낙폭(max drawdown)을 계산하고 샌드박스 내에서 종가 차트를 그린 4회의 호스팅된 `code_interpreter_call`을 실행했습니다.
- 공식 OpenAI `gpt-5.6-sol` 경로는 여전히 유지되나 할당량 부족 상태입니다: 두 호출 모두 호스팅된 도구가 실행되기 전에 `credit_balance_exhausted`를 반환했으며, 이는 동일한 증거 파일에 기록되어 있습니다.
- 솔직한 제약 사항: DashScope 샌드박스에는 외부 네트워크 접속이 없어 일일 종가가 웹 검색을 통해 추출되었습니다(모델이 보고서에서 이를 공개함). 차트 PNG는 이 Responses API가 실행 로그만 반환하므로 샌드박스 내에 유지됩니다. 또한 `qwen3.7-plus`는 시스템 프롬프트에 명시적인 '선-명확화(clarify-first)' 규칙이 포함되어 있을 때만 행동 전에 질문하며, 제공된 프롬프트에 이 규칙이 인코딩되어 있습니다.
- OpenRouter 경로는 순전히 진단용으로만 유지되며 절대로 승인에 포함되지 않습니다. 폴백 모델, 로컬 Python 대체, 조작된 도구 트레이스 또는 Chat-Completions 근사 방식은 어떤 것도 이행으로 인정되지 않습니다.

이전의 차단된 시도 기록은 `validation/real_20260729T155459Z/` 및 `validation/real_20260730T033800Z/` 아래에 유지됩니다.

---

## 설정 및 CLI (Setup and CLI)

Python 3.9+가 필요합니다.

```bash
# 저장소 루트에서: 공유 제1장 환경 사용
uv sync --locked --extra ch1

# 디렉토리를 변경하기 전에 환경을 활성화하세요:
source .venv/bin/activate

# uv가 설치되어 있지 않은 경우 pip 대체 방법:
# python -m pip install -e ".[ch1]"

cd chapter1/search-codegen

# 마이그레이션 동안 여전히 지원되는 단일 프로젝트 호환 경로:
# python -m pip install -r requirements.txt

export OPENAI_API_KEY=your-openai-api-key

# 정확한 공식 경로
python main.py --backend openai --mode single \
  --request "아세안 10개국 수도 중 가장 가까운 수도 쌍은 어디인가요? 검색 후 Python으로 계산해 주세요" \
  --reasoning high --verbosity high --output result.json

# 동등 제공자 경로 (승인 자격 있음): 알리바바 Model Studio
export DASHSCOPE_API_KEY=your-dashscope-api-key
python main.py --backend dashscope --mode single \
  --request "아세안 10개국 수도 중 가장 가까운 수도 쌍은 어디인가요? 검색 후 Python으로 계산해 주세요" \
  --output result.json

# API 호출 없이 정확한 요청 검사
python main.py --backend openai --dry-run \
  --request "아세안 10개국 수도 중 가장 가까운 수도 쌍은?" \
  --reasoning max --verbosity high

# 프록시 진단 전용; 표준 승인 아님
export OPENROUTER_API_KEY=your-openrouter-api-key
python main.py --backend openrouter --mode single --request "최신 뉴스 검색"
```

주요 옵션:

| 옵션 | 의미 |
|---|---|
| `--backend openai` | 표준 `https://api.openai.com/v1/responses` 경로 |
| `--backend dashscope` | 동등 제공자 경로: DashScope Responses API, 호스팅된 `web_search` + `code_interpreter`, 승인 자격 있음 |
| `--backend openrouter` | 명시적 프록시 진단용; 묵시적으로 대체되지 않음 |
| `--reasoning` | `none`, `low`, `medium`, `high`, `xhigh`, 또는 GPT-5.6 `max` |
| `--verbosity` | Responses `text.verbosity`: `low`, `medium`, 또는 `high` |
| `--output` | 요청, 타입화된 출력 항목, 인용, 토큰 사용량 및 원시 응답 저장 |

---

## 검증 (Verification)

```bash
python -m pytest -q test_responses_agent.py
python -m py_compile agent.py config.py main.py run_experiment_1_3.py
```

검증기(validator)는 정확한 모델 식별자, 직접 vs 프록시 출처, 두 호스팅 도구 유형, 인용, 명확화 순서, 연속성 연결, 토큰 사용량, 가용 시 보고된 제공자 비용, 그리고 자격 증명이 제거된 원시 증거를 검사합니다.

---

## 공식 출처 (Official sources)

- [GPT-5.6 Sol model](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [Web search](https://developers.openai.com/api/docs/guides/tools-web-search)
- [Code Interpreter](https://developers.openai.com/api/docs/guides/tools-code-interpreter)
- [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6-sol)
- [Alibaba Model Studio code interpreter (DashScope)](https://help.aliyun.com/zh/model-studio/qwen-code-interpreter)

---

## 요약 설명 (Summary)

본 프로젝트는 교재 본문에 기술된 **정확한 프로토콜**인 Responses API, 호스팅된 `web_search` 및 호스팅된 `code_interpreter`를 사용합니다. 승인 기준은 코드 내에서 "도구를 선언했음"이나 답변에서 "Python을 사용했다고 주장함"이 아닌, 서버 측에서 반환된 `web_search_call` / `code_interpreter_call` 및 URL 인용입니다.

저자 승인 다중 제공자 정책에 따라 승인은 공식 OpenAI 계정에만 국한되지 않습니다: 공식 `gpt-5.6-sol` 경로는 완벽히 유지되며(현재 Key 추론 시 `credit_balance_exhausted` 반환, 증거에 명시 기록됨), 동등한 호스팅 도구를 갖춘 제공자 역시 승인할 수 있습니다. 2026-07-31의 공식 실행은 알리바바 클라우드 백련(Model Studio) `qwen3.7-plus`(DashScope Responses API)를 사용하여 모든 승인 게이트를 통과했습니다: 아세안 과제에서는 10개 수도 좌표를 우선 검색한 뒤 호스팅된 Python으로 45개 대원 거리를 열거(쿠알라룸푸르-싱가포르 316.35 km로 로컬 독립 참조 값과 일치); 비트코인 과제에서는 도구를 사용하지 않고 데이터 소스와 지표를 먼저 명확히 확인한 후, `previous_response_id`를 통해 계속하여 3회의 모델 주도 검색과 4회의 호스팅 코드 실행(MA7/MA20, RSI14, MACD, 기간 수익률, 최대 낙폭 및 차트)을 완료했습니다. OpenRouter는 진단 경로로만 유지되며 대체품으로 포장되지 않습니다.
