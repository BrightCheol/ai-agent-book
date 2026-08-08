Ran command: `python main.py --ㅔ개퍙ㄷㄱ ㅐㅔ두먀  --mode single`
Ran command: `python main.py --provider openai  --mode single`
Viewed README.ko.2.md:204-216
Viewed run_experiment_1_1.py:1-446
Viewed agent.py:1-100

`chapter1/context` 폴더의 **실험 1-1**에 대한 명확한 정의, 5대 세부 실험 구성, 그리고 각 실험별 구체적인 실행 명령어입니다.

---

### 1. 실험 1-1은 어떤 실험인가?

- **실험명**: **컨텍스트의 핵심 역할 (The Critical Role of Context) 및 소거 연구 (Ablation Study)**
- **실험 목적**:
  AI 에이전트가 문제를 해결할 때 필요한 **컨텍스트 4대 구성 요소(대화 이력, 모델의 사고/추론 과정, 도구 정의, 도구 실행 결과)**를 하나씩 체계적으로 제거(Ablation)했을 때, 에이전트의 의사결정 루프와 행동이 어떻게 붕괴되는지 실증하는 실험입니다.
- **표준 테스트 작업 (Canonical Task)**:
  다국적 통화로 작성된 4개 분기 수익(Q1: $2.5M USD, Q2: €2.1M EUR, Q3: £1.8M GBP, Q4: ¥380M JPY)을 도구를 사용해 USD로 변환한 뒤, 연간 총액(`$9,602,895.73`)과 분기별 평균(`$2,400,723.93`)을 계산하는 복합 다단계 과제입니다.

---

### 2. 개별 세부 실험(5대 아암, Arms) 구성

| 세부 실험 (Context Mode) | 제거된 컨텍스트 요소              | 구현 방식 (`agent.py`)                                        | 관찰되는 에이전트 행동 및 현상                                                                    |
| :----------------------- | :-------------------------------- | :------------------------------------------------------------ | :------------------------------------------------------------------------------------------------ |
| **1. `full` (기준선)**   | **없음 (전체 유지)**              | 모든 도구, 이전 대화 이력, 추론, 도구 결과를 온전히 전달      | **성공**: 4개 분기 환율 변환 후 정확한 총합/평균 계산 완료                                        |
| **2. `no_history`**      | **대화 이력 (History)**           | 슬라이딩 윈도우(시스템+현재 작업만) 적용, 직전 단계 기억 상실 | **행동 반복 (Repeated Action)**: 이미 변환한 통화를 계속 다시 호출하며 무한 루프 / 최대 반복 초과 |
| **3. `no_reasoning`**    | **추론 과정 (Reasoning)**         | 어시스턴트 메시지에서 `reasoning_content` (사고 과정)를 삭제  | **전략 부재/효율 저하**: 체계적 계획 없이 도구를 호출하거나 오류 발생                             |
| **4. `no_tool_calls`**   | **도구 정의 (Tool Defs)**         | API 요청 시 `tools` 파라미터 자체를 생략                      | **도구 호출 불가**: 외부 환경과 상호작용하지 못하고 임의 추정/환각/작업 포기                      |
| **5. `no_tool_results`** | **도구 실행 결과 (Tool Results)** | 도구 결과 메시지를 `[Tool result hidden]`으로 마스킹          | **결과 맹목/반복**: 도구 반환값을 확인하지 못해 동일 도구를 재호출하거나 엉뚱한 결론 도출         |

---

### 3. 세부 실험별 구체적인 실행 커맨드

> **참고 (LM Studio / 로컬 LLM 사용자)**:
> `--provider openai --model "<로드된_모델명>"`을 함께 붙여서 호출합니다. (클라우드 모델 사용 시 `--provider doubao` 또는 `--provider deepseek` 등으로 변경)

---

#### A. 세부 모드별 개별 단일 실행 (`--mode single --context-mode <모드>`)

각각의 컨텍스트 모드를 독립적으로 1회 실행하여 에이전트의 거동을 확인하는 커맨드입니다:

```bash
# 1) [Full 기준선 실험] 전체 컨텍스트 정상 실행
python main.py --mode single \
  --provider openai --model "google_gemma-4-26b-a4b-it" \
  --context-mode full \
  --task "According to quarterly revenue: Q1 $2.5M USD, Q2 €2.1M EUR, Q3 £1.8M GBP, Q4 ¥380M JPY. Convert all to USD and calculate annual total and quarterly average."

# 2) [No History 실험] 이력을 제거하여 도구 호출 반복 현상 확인
python main.py --mode single \
  --provider openai --model "google_gemma-4-26b-a4b-it" \
  --context-mode no_history \
  --task "According to quarterly revenue: Q1 $2.5M USD, Q2 €2.1M EUR, Q3 £1.8M GBP, Q4 ¥380M JPY. Convert all to USD and calculate annual total and quarterly average."

# 3) [No Reasoning 실험] 모델의 사고/추론 과정을 제거하여 효율성 저하 확인
python main.py --mode single \
  --provider openai --model "google_gemma-4-26b-a4b-it" \
  --context-mode no_reasoning \
  --task "According to quarterly revenue: Q1 $2.5M USD, Q2 €2.1M EUR, Q3 £1.8M GBP, Q4 ¥380M JPY. Convert all to USD and calculate annual total and quarterly average."

# 4) [No Tool Calls 실험] 도구 정의를 생략하여 도구 실행 불가 확인
python main.py --mode single \
  --provider openai --model "google_gemma-4-26b-a4b-it" \
  --context-mode no_tool_calls \
  --task "According to quarterly revenue: Q1 $2.5M USD, Q2 €2.1M EUR, Q3 £1.8M GBP, Q4 ¥380M JPY. Convert all to USD and calculate annual total and quarterly average."

# 5) [No Tool Results 실험] 도구 반환값을 숨겨 피드백 부재 시 행동 확인
python main.py --mode single \
  --provider openai --model "google_gemma-4-26b-a4b-it" \
  --context-mode no_tool_results \
  --task "According to quarterly revenue: Q1 $2.5M USD, Q2 €2.1M EUR, Q3 £1.8M GBP, Q4 ¥380M JPY. Convert all to USD and calculate annual total and quarterly average."
```

---

#### B. 5대 세부 실험 일괄 비교 모드 (`--mode ablation`)

5가지 모드를 순차적으로 자동 실행하고, 결과 비교 매트릭스 표를 콘솔에 출력합니다:

```bash
# 1) 5개 모드 전체를 한 번에 비교 실행
python main.py --mode ablation \
  --provider openai --model "google_gemma-4-26b-a4b-it"

# 2) 특정 모드들만 선별 비교하고 결과를 JSON 파일로 저장 (예: full vs no_history)
python main.py --mode ablation \
  --provider openai --model "google_gemma-4-26b-a4b-it" \
  --ablation-modes full no_history \
  --output ablation_result.json

# 3) 통계적 신뢰성을 위해 각 모드별로 3회씩 반복 실행
python main.py --mode ablation \
  --provider openai --model "google_gemma-4-26b-a4b-it" \
  --cases 3
```

---

#### C. 교재 실측 검증 전용 스크립트 (`run_experiment_1_1.py`)

교재 제1장의 5개 실험 아암을 엄밀하게 실행하고 원시 API 요청/응답 전문을 SHA-256 해시와 함께 JSON 검증 아티팩트로 남기는 스크립트입니다:

```bash
# 실측 실험 1-1 공식 벤치마크 실행 (최대 5회 iteration 제한)
python run_experiment_1_1.py \
  --provider openai \
  --model "google_gemma-4-26b-a4b-it" \
  --max-iterations 5 \
  --output-dir validation/my_run
```
