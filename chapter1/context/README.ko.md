# 컨텍스트 인식 AI 에이전트 및 소거 연구 (Context-Aware AI Agent with Ablation Studies)

> 컨텍스트 구성 요소(이력, 추론, 도구 호출, 도구 결과)의 체계적인 소거(ablation)를 지원하는 다중 제공자 컨텍스트 인식 에이전트.
> 교재 제1장 **실험 1-1 ★★: 컨텍스트의 핵심 역할** 연동.

← [제1장 목차로 돌아가기](../README.ko.md) · 📖 [제1장 본문 읽기](../../book-ko/chapter1.ko.md)

---

## 개요 (Overview)

본 프로젝트는 다양한 도구(PDF 파싱, 환율 변환, 계산기, 코드 인터프리터)를 갖춘 컨텍스트 인식 AI 에이전트를 구현하며, 서로 다른 컨텍스트 구성 요소가 에이전트의 행동과 성능에 미치는 영향을 탐구하기 위한 포괄적인 소거 테스트(ablation testing)를 제공합니다. SiliconFlow Qwen, ByteDance Doubao, Moonshot Kimi, DeepSeek 등 여러 LLM 제공자를 지원합니다.

## 주요 기능 (Key Features)

- **다중 제공자 지원 (Multi-provider Support)**: SiliconFlow (Qwen), Doubao (ByteDance), Kimi (Moonshot), DeepSeek LLM 지원
- **다중 도구 에이전트 (Multi-tool Agent)**: PDF 파싱, 환율 변환, 수학 계산 및 Python 코드 실행 지원
- **컨텍스트 모드 (Context Modes)**: 소거 연구를 위한 5가지 컨텍스트 설정 지원
- **대화형 및 배치 모드 (Interactive & Batch Modes)**: 단일 작업 실행 또는 포괄적인 테스트 스위트 실행
- **대화 이력 (Conversation History)**: 세션 내 다중 쿼리에 걸쳐 컨텍스트 유지
- **상세 분석 (Detailed Analytics)**: 성능 지표, 시각화 및 포괄적 보고서 제공

---

## 지원되는 LLM 제공자 (Supported LLM Providers)

### Doubao (ByteDance) - 기본값

- **모델**: `doubao-seed-1-6-thinking-250715` (변경 가능)
- **API**: Volcano Engine을 통한 OpenAI 호환 API
- **적합 분야**: 고급 추론, 빠른 응답 속도, 영어 및 중국어 작업 지원

### SiliconFlow

- **모델**: `Qwen/Qwen3.5-397B-A17B` (변경 가능)
- **API**: OpenAI 호환 API
- **적합 분야**: 복잡한 추론 작업, 상세 분석

### Kimi (Moonshot AI)

- **모델**: `kimi-k3` (K3 추론 모델; temperature는 1로 강제되며 max_tokens는 사고 출력을 수용하기 위해 충분히 크개 설정됨)
- **API**: Moonshot 플랫폼을 통한 OpenAI 호환 API
- **적합 분야**: 고급 추론, 다중 턴 대화, 영어 및 중국어 작업 지원
- **특징**: 비용 최적화를 위한 컨텍스트 캐싱(Context caching) 지원

### DeepSeek

- **모델**: `deepseek-v4-flash` (기본값; 더 강력한 계층을 사용하려면 `--model deepseek-v4-pro` 사용)
- **API**: [DeepSeek Platform](https://platform.deepseek.com/)을 통한 OpenAI 호환 API
- **적합 분야**: 비용 효율적인 도구 호출 에이전트; 사고 모드가 활성화되어 `no_reasoning` 소거 시 `reasoning_content`를 쉽게 분리 가능
- **참고**: 레거시 별칭인 `deepseek-chat` / `deepseek-reasoner`는 사용 중단됨(2026-07-24); V4 ID 권장

---

## 아키텍처 (Architecture)

### 컨텍스트 구성 요소 (Context Components)

1. **Full Context (전체 컨텍스트)** — 모든 구성 요소가 포함된 완전한 에이전트
2. **No History (이력 없음)** — 과거 도구 호출 추적 기록이 제거됨
3. **No Reasoning (추론 없음)** — 전략적 계획/사고 과정 없이 작동
4. **No Tool Calls (도구 호출 없음)** — 외부 도구를 실행할 수 없음
5. **No Tool Results (도구 결과 없음)** — 도구 실행 결과를 볼 수 없음

### 사용 가능한 도구 (Available Tools)

- **`parse_pdf(url)`** — PDF 문서 다운로드 및 텍스트 추출
- **`convert_currency(amount, from, to)`** — 실시간 환율 변환
- **`calculate(expression)`** — 수식 평가 및 단순 계산
- **`code_interpreter(code)`** — 복잡한 계산, 합계 및 데이터 처리를 위한 Python 코드 실행

---

## 사전 요구 사항 (Prerequisites)

- Python 3.10+
- 지원되는 제공자 중 하나의 API 키:
  - **SiliconFlow**: [SiliconFlow](https://siliconflow.cn)에서 발급
  - **Doubao (ByteDance)**: [Volcano Engine](https://www.volcengine.com/)에서 발급
  - **Kimi (Moonshot)**: [Moonshot Platform](https://platform.moonshot.cn/)에서 발급
  - **DeepSeek**: [DeepSeek Platform](https://platform.deepseek.com/api_keys)에서 발급

---

## 샘플 작업 (Sample Tasks)

시스템에는 다양한 기능을 시연하는 5가지 사전 정의된 샘플 작업이 포함되어 있습니다:

1. **단순 환율 변환 (Simple Currency Conversion)** — 기본 다중 통화 계산
2. **다중 통화 예산 분석 (Multi-Currency Budget Analysis)** — 지사 간 복잡한 지출 분석
3. **PDF 재무 분석 (PDF Financial Analysis)** — 재무 문서 파싱 및 분석
4. **투자 성장 계산 (Investment Growth Calculation)** — 환율 변환을 포함한 복리 계산
5. **종합 재무 보고서 (Comprehensive Financial Report)** — 모든 도구를 활용한 전체 워크플로우

---

## 빠른 시작 (Quick Start)

### 1. 설치 (Installation)

```bash
# 권장 사항: 저장소 루트에서 공유 제1장 환경 사용
uv sync --locked --extra ch1

# 디렉토리를 변경하기 전에 환경을 활성화하세요:
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Windows cmd: .venv\Scripts\activate.bat

# uv가 설치되어 있지 않은 경우 pip 대체 방법:
# python -m pip install -e ".[ch1]"

# 아래 명령어 실행을 위해 본 실험 디렉토리로 이동합니다
cd chapter1/context

# 마이그레이션 동안 여전히 지원되는 단일 프로젝트 호환 경로:
# python -m pip install -r requirements.txt

# 환경 변수 파일 복사 및 설정
cp env.example .env
# .env 파일을 수정하여 API 키 추가 (SILICONFLOW_API_KEY 또는 ARK_API_KEY)
```

### 2. 제공자 설정 (Configure Provider)

```bash
# Doubao (ByteDance) 설정 - 기본값
export ARK_API_KEY=your_key_here  
python main.py  # 기본적으로 Doubao 사용

# SiliconFlow (Qwen) 설정
export SILICONFLOW_API_KEY=your_key_here
python main.py --provider siliconflow

# Kimi (Moonshot) 설정
export MOONSHOT_API_KEY=your_key_here
python main.py --provider kimi

# DeepSeek 설정
export DEEPSEEK_API_KEY=your_key_here
python main.py --provider deepseek
# 더 강력한 모델 옵션:
python main.py --provider deepseek --model deepseek-v4-pro

# 사용자 지정 모델 지정
python main.py --model doubao-seed-1-6-thinking-250715

# 범용 OpenRouter 폴백: 직련 제공자 키가 누락되었거나 유효하지 않지만
# OPENROUTER_API_KEY가 설정된 경우 요청은 OpenRouter로 라우팅됩니다.
export OPENROUTER_API_KEY=your-openrouter-api-key
python main.py                       # ARK_API_KEY가 없을 때 OpenRouter로 폴백
python main.py --provider openrouter # 또는 OpenRouter 직접 사용
```

### 3. Kimi / DeepSeek 연동 테스트 (Testing Kimi / DeepSeek Integration)

```bash
# Kimi K3 모델 빠른 테스트
export MOONSHOT_API_KEY=your_key_here
python tests/manual/check_kimi.py

# 메인 스크립트에서 Kimi 사용
python main.py --provider kimi --mode interactive

# Kimi를 통한 소거 연구 실행
python main.py --provider kimi --mode ablation

# DeepSeek V4 빠른 테스트
export DEEPSEEK_API_KEY=your_key_here
python tests/manual/check_deepseek.py
# 또는: python tests/manual/check_deepseek_quick.py

# 메인 스크립트 / 소거 연구에서 DeepSeek 사용
python main.py --provider deepseek --mode interactive
python main.py --provider deepseek --mode ablation
```

### 4. 대화형 모드 실행 (Run Interactive Mode)

```bash
# 기본값 (Doubao)
python main.py --mode interactive

# SiliconFlow 제공자 사용
python main.py --mode interactive --provider siliconflow

# 대화형 모드 내 사용 명령어:
# - 'samples': 사전 정의된 샘플 작업 표시
# - 'sample 2': 2번 샘플(PDF 파싱) 테스트
# - 'providers': 사용 가능한 LLM 제공자 목록 표시
# - 'provider kimi': 제공자 변경 (예: Kimi)
# - 'status': 현재 설정 상태 확인
# - 'help': 전체 명령어 안내
```

### 5. 샘플 작업 실행 (Run Sample Tasks)

```bash
# 인자 없이 실행하여 샘플 선택
python main.py --mode single

# 특정 제공자 지정
python main.py --mode single --provider doubao

# 사용자 정의 작업 실행
python main.py --mode single \
  --task "Convert $1000 USD to EUR, GBP, and JPY. Calculate the average." \
  --context-mode full \
  --provider siliconflow
```

### 6. 소거 연구 실행 (Run Ablation Study)

```bash
# 기본 제공자로 실행 (단일 케이스, 5가지 컨텍스트 모드 전체)
python main.py --mode ablation

# Doubao 제공자로 실행
python main.py --mode ablation --provider doubao

# 다중 케이스 비교 실행 (교재 주장을 뒷받침하는 강력한 증거 확보)
python main.py --mode ablation --cases 3

# 특정 모드 2가지만 비교하고 결과를 지정 경로에 저장
python main.py --mode ablation --ablation-modes full no_history --output my_ablation.json
```

`main.py`는 단일 CLI 엔트리포인트입니다. `python main.py --help`를 실행하면 전체 옵션을 확인할 수 있습니다.

주요 플래그:

| 플래그 | 설명 |
|------|-------------|
| `--mode` | `single` / `ablation` / `interactive` (기본값) |
| `--task` | `single` 모드용 작업 텍스트 |
| `--context-mode` | `single` 모드용 컨텍스트 모드 (`full`, `no_history`, `no_reasoning`, `no_tool_calls`, `no_tool_results`) |
| `--ablation-modes` | `ablation` 모드에서 테스트할 모드 하위 집합 (기본값: 5개 모드 전체) |
| `--cases` | `ablation` 모드에서 각 모드가 실행될 케이스 수 (기본값: 1) |
| `--provider` / `--model` | LLM 제공자 및 선택적 모델 오버라이드 |
| `--output` | JSON 결과 저장 경로 (single 모드) 또는 원시 결과 경로 (ablation 모드) |

---

## 소거 연구 (Ablation Studies)

### Kimi K3 실측 수용 결과 (2026-07-29)

`run_experiment_1_1.py`는 원고의 5개 실험 아암(arm)을 실측하고 단순 요약표 대신 모든 원시 API 요청/응답을 기록합니다:

```bash
python run_experiment_1_1.py --provider kimi --model kimi-k3 --max-iterations 5
```

수용된 검증 아티팩트는 [validation/latest.json](validation/latest.json)입니다. 5개 요청 형태 규약이 Moonshot 직련 API에서 모두 통과되었습니다. 풀(full) 모드는 올바른 USD 총합과 평균을 도출했고, 도구 정의를 제거하면 도구 호출이 발생하지 않았으며, 도구 결과나 이력을 제거하면 모두 행동 반복이 관찰되었습니다. 단, 추론 제거(no-reasoning) 모드도 이번 실행에서 올바른 답변을 도출하여 원고의 필연적 모순 결정 주장은 **재현되지 않았으며** 별도로 기록되었습니다.

관찰 결과 (아래의 예상 동작 라벨과 다를 수 있음):

| 아암 (Arm) | 반복 횟수 | 도구 행동 수 | 행동 반복 여부 | 올바른 수치 답변 |
|---|---:|---:|---|---|
| full | 3 | 4 | 아니오 | 예 |
| no history | 5 (상한선) | 15 | 예 | 답변 없음 |
| no reasoning | 3 | 4 | 아니오 | **예 — 원고 주장에 대한 부적절한 결과** |
| no tool definitions | 1 | 0 | 아니오 | 아니오 (모델이 환율 조작을 명시적으로 거부) |
| no tool results | 5 | 7 | 예 | 아니오 (관찰 결과가 숨겨졌다고 최종 보고) |

소거 연구는 컨텍스트 구성 요소를 체계적으로 제거하여 그 중요성을 분석합니다.

### 테스트 시나리오 (Test Scenario)

다음이 필요한 복잡한 재무 분석 작업:

1. PDF 문서 파싱
2. 다중 통화 변환
3. 수학적 계산
4. 결과 집계

### 예상 동작 (Expected Behaviors)

| 컨텍스트 모드 | 제거된 구성 요소 (교재 §실험 1.1) | 예상 동작 | 영향 |
|-------------|-----------------------------------|-------------------|---------|
| **full** | 없음 (기준점/Baseline) | 완벽하고 성공적인 실행 | 기준 성능 |
| **no_history** | 대화 이력 (history) | 중복 작업, 효율성 저하 | 도구 호출 반복 가능성 |
| **no_reasoning** | 사고 과정 (reasoning) | 비구조적 접근, 오류 가능성 | 전략적 계획 결여 |
| **no_tool_calls** | 도구 정의 (tool definitions) | 완전한 실패 | 외부 환경과 상호작용 불가 |
| **no_tool_results** | 도구 실행 결과 (tool results) | 잘못된 결론 도출 | 피드백 없이 의사결정 수행 |

### 각 소거의 구현 방식 (`agent.py` 참조)

- **no_tool_calls** — 요청에서 `tools` 매개변수를 생략하여 모델에 도구 정의가 전달되지 않음.
- **no_tool_results** — 모든 도구 실행 결과가 `[Tool result hidden]` 자리표시자로 대체됨.
- **no_reasoning** — 어시스턴트 메시지가 궤적에 추가되기 전 `reasoning_content`를 제거함.
- **no_history** — `_prepare_messages_for_api()`가 슬라이딩 윈도우(시스템 프롬프트 + 현재 작업 + 최근 1단계 ReAct)만 전송하므로 이전 단계를 잊어버리고 도구를 반복 호출하게 됨. Full 모드는 전체 궤적을 전송함.

### 소거 연구 테스트 실행 (Running Tests)

```bash
# 전체 소거 연구 실행 (단일 케이스, 5가지 모드 모두)
python main.py --mode ablation

# 교재의 관점을 강력히 지원하기 위한 다중 케이스 실행
python main.py --mode ablation --cases 3
```

콘솔에는 2개의 표가 출력됩니다: 매 실행별 **소거 연구 결과 표(ablation study results)**와 각 요소의 영향을 한눈에 파악할 수 있는 **비교 매트릭스(comparison matrix)**.

### 자동화 Regression 테스트

```bash
python -m pytest tests
```

---

## 결과 이해하기 (Understanding Results)

### 성능 지표 (Performance Metrics)

- **Success Rate (성공률)**: 작업이 올바르게 완료되었는지 여부
- **Execution Time (실행 시간)**: 작업을 완료하는 데 걸린 총 시간
- **Iterations (반복 횟수)**: 에이전트와 모델 간의 상호작용 횟수
- **Tool Calls (도구 호출 수)**: 외부 도구 호출 횟수
- **Reasoning Steps (추론 단계)**: 전략적 계획 반복 횟수

---

## 핵심 인사이트 (Key Insights)

1. **도구 호출은 필수적 요소임** — 도구 호출 능력이 없으면 외부 시스템과 상호작용할 수 없어 작업을 완료할 수 없습니다.
2. **도구 결과는 핵심 피드백을 제공함** — 결과를 보지 못하면 맹목적으로 동작하게 되어 잘못된 결론이나 무한 루프에 빠집니다.
3. **추론은 효율성을 극대화함** — 전략적 계획은 반복 횟수와 도구 호출을 줄여 속도와 정확도를 향상시킵니다.
4. **이력은 중복을 방지함** — 이력 컨텍스트는 중복 작업을 방지하고 대화 전반에 걸쳐 일관성을 유지합니다.

---

## 고급 활용법 (Advanced Usage)

### 대화형 모드 명령어

| 명령어 | 설명 |
|---------|-------------|
| `samples` | 사전 정의된 모든 샘플 작업 표시 |
| `sample <n>` | n번째 샘플 작업 실행 |
| `providers` | 사용 가능한 모든 LLM 제공자 목록 |
| `provider <name>` | 다른 제공자로 전환 (예: `provider kimi`) |
| `modes` | 소거 테스트용 컨텍스트 모드 목록 |
| `mode <name>` | 컨텍스트 모드 변경 (예: `mode no_history`) |
| `status` | 현재 설정 상태 표시 (제공자, 모델, 모드 등) |
| `reset` | 에이전트 궤적 리셋 (이력 초기화) |
| `create_pdfs` | 테스트용 샘플 PDF 생성 |
| `quit` | 대화형 모드 종료 |

### 커스텀 작업 작성

```python
from agent import ContextAwareAgent, ContextMode

agent = ContextAwareAgent(api_key, ContextMode.FULL)
result = agent.execute_task("""
    Download the PDF from https://example.com/report.pdf,
    extract all monetary values, convert them to EUR,
    and calculate the total.
""")
```

---

## 프로젝트 구조 (Project Structure)

```
context/
├── README.md             # 영문 README
├── README.ko.md          # 한국어 README (본 파일)
├── main.py               # 단일 CLI 엔트리포인트 (single / ablation / interactive)
├── agent.py              # 에이전트 핵심 구현 및 컨텍스트 모드
├── config.py             # 설정 관리
├── create_sample_pdf.py  # PDF 생성 유틸리티
├── fixtures/
│   └── pdfs/             # 테스트용 샘플 PDF 파일
├── tests/
│   ├── test_agent.py
│   ├── test_code_interpreter.py
│   ├── test_malformed_tool_json.py
│   └── manual/           # API 키가 필요한 제공자 테스트 스크립트
├── requirements.txt      # 의존성 패키지
└── env.example           # 환경 변수 템플릿
```

> **참고**: 소거 연구 스위트는 `main.py` 내의 `AblationTestSuite` 클래스에 있으며 `python main.py --mode ablation`으로 실행됩니다. 별도의 `ablation_tests.py`는 존재하지 않습니다.

---

## 연구 응용 분야 (Research Applications)

- **AI 안전성 연구 (AI Safety Research)**: 실패 모드 이해
- **시스템 설계 (System Design)**: 핵심 구성 요소 식별
- **최적화 (Optimization)**: 최소한의 실행 가능한 구성 찾기
- **교육 (Education)**: 에이전트 아키텍처 원리 교육

---

## 참고 및 제약 사항 (Notes & Limitations)

- 본 프로젝트는 컨텍스트 소거 교육용입니다. 프로덕션 환경에 적용하려면 적절한 예외 처리, 레이트 리밋(rate limiting) 및 보안 조치를 추가해야 합니다.
- 직련 제공자 API 키가 없는 경우 OpenRouter가 범용 폴백으로 작동합니다.
- 라이선스: MIT. 추가 도구, 시나리오, 소거 전략 등 기여를 환영합니다.
