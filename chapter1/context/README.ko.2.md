### 1. 사전 준비 및 환경 설정

```bash
# 1) 저장소 루트에서 의존성 설치 및 가상환경 활성화
uv sync --locked --extra ch1
source .venv/bin/activate       # (Windows: .\.venv\Scripts\Activate.ps1)

# 2) 실험 디렉토리로 이동
cd chapter1/context

# 3) 환경 변수 파일 생성 및 API 키 설정 (.env 파일 생성)
cp env.example .env

# 4) 사용하는 LLM 제공자 API 키 환경 변수 등록 (택 1 이상)
export ARK_API_KEY="your-doubao-api-key"          # Doubao (ByteDance) - 기본값
export SILICONFLOW_API_KEY="your-siliconflow-key" # SiliconFlow (Qwen)
export MOONSHOT_API_KEY="your-kimi-key"           # Kimi (Moonshot AI)
export DEEPSEEK_API_KEY="your-deepseek-key"       # DeepSeek
export OPENROUTER_API_KEY="your-openrouter-key"   # OpenRouter (범용 폴백)

# --- [로컬 LLM 서버 사용 시 설정 (LM Studio, llama.cpp, Ollama)] ---
# LM Studio (기본 포트: 1234)
export OPENAI_BASE_URL="http://localhost:1234/v1"
export OPENAI_API_KEY="lm-studio"                 # OpenAI 클라이언트 통과용 더미 키

# llama.cpp server (기본 포트: 8080)
export OPENAI_BASE_URL="http://localhost:8080/v1"
export OPENAI_API_KEY="llama-cpp"

# Ollama (기본 포트: 11434, API 키 불필요)
export OLLAMA_BASE_URL="http://localhost:11434/v1"
```

> [!IMPORTANT]
> **LM Studio / 로컬 LLM 실행 시 필수 주의사항**:
> `main.py` CLI 인자의 `--provider` 기본값이 `doubao`로 설정되어 있습니다. 따라서 옵션 없이 `python main.py --mode single`만 실행하면 `.env` 파일과 무관하게 `doubao`를 호출하여 `No API key found for provider 'doubao'` 에러가 발생합니다.
> **LM Studio / llama.cpp 로컬 모델을 사용할 때는 항상 `--provider openai --model "<로드된모델명>"`을 명시하여 실행해야 합니다.**

---

### 2. 단일 작업 실행 모드 (`--mode single`)

```bash
# [기능: 사전 정의된 샘플 작업 중 대화식으로 선택하여 실행 (기본 Doubao 사용)]
python main.py --mode single

# [기능: 특정 클라우드 LLM 제공자(Doubao)를 지정하여 단일 샘플 실행]
python main.py --mode single --provider doubao

# [기능: ★ LM Studio 로컬 모델로 단일 작업 실행 (provider와 model 필수 지정)]
python main.py --mode single \
  --provider openai \
  --model "google_gemma-4-26b-a4b-it"

# [기능: llama.cpp 로컬 서버로 단일 작업 실행]
python main.py --mode single \
  --provider openai \
  --model "default"

# [기능: Ollama 로컬 모델로 단일 작업 실행]
python main.py --mode single \
  --provider ollama \
  --model "qwen2.5:7b"

# [기능: 커스텀 프롬프트 작업 + 특정 컨텍스트 모드 + LLM 제공자 조합 실행]
python main.py --mode single \
  --task "Convert $1000 USD to EUR, GBP, and JPY. Calculate the average." \
  --context-mode full \
  --provider siliconflow

# [기능: 사용자 지정 모델 오버라이드 및 결과 JSON 저장]
python main.py --mode single \
  --provider deepseek \
  --model deepseek-v4-pro \
  --context-mode no_reasoning \
  --output single_result.json
```

> **사용 가능한 `--context-mode` 옵션:**
>
> - `full`: 전체 컨텍스트 (정상 기준선)
> - `no_history`: 대화 이력 제거 (슬라이딩 윈도우로 인한 반복 유발 테스트)
> - `no_reasoning`: 추론 과정(`reasoning_content`) 제거
> - `no_tool_calls`: 도구 정의 생략 (도구 사용 불가)
> - `no_tool_results`: 도구 실행 결과를 `[Tool result hidden]`으로 마스킹

---

### 3. 대화형 모드 (`--mode interactive`)

```bash
# [기능: 기본 모델(Doubao)로 대화형 REPL 세션 진입]
python main.py --mode interactive

# [기능: SiliconFlow 제공자로 대화형 세션 진입]
python main.py --mode interactive --provider siliconflow

# [기능: Kimi 제공자로 대화형 세션 진입]
python main.py --mode interactive --provider kimi

# [기능: DeepSeek 제공자로 대화형 세션 진입]
python main.py --mode interactive --provider deepseek

# [기능: ★ LM Studio 로컬 모델로 대화형 세션 진입]
python main.py --mode interactive \
  --provider openai \
  --model "google_gemma-4-26b-a4b-it"

# [기능: llama.cpp 로컬 서버로 대화형 세션 진입]
python main.py --mode interactive \
  --provider openai \
  --model "default"

# [기능: Ollama 로컬 모델로 대화형 세션 진입]
python main.py --mode interactive \
  --provider ollama \
  --model "qwen2.5:7b"
```

#### 대화형 셸 내부 명령어 (Interactive Shell Commands)

대화형 모드에 진입한 후 프롬프트에 직접 입력하는 명령어입니다:

| 대화형 명령어     | 기능 설명                                   |
| :---------------- | :------------------------------------------ |
| `samples`         | 사전 정의된 5가지 샘플 작업 목록 확인       |
| `sample 2`        | 2번 샘플(다중 통화 예산 분석) 즉시 실행     |
| `providers`       | 지원되는 LLM 제공자 목록 확인               |
| `provider kimi`   | 실행 중 실시간으로 Kimi 제공자로 변경       |
| `modes`           | 소거 연구용 5가지 컨텍스트 모드 목록 표시   |
| `mode no_history` | 컨텍스트 모드를 '이력 없음'으로 실시간 전환 |
| `status`          | 현재 설정된 모델, 제공자, 모드 상태 확인    |
| `reset`           | 에이전트 대화 궤적/이력 초기화              |
| `create_pdfs`     | 테스트용 샘플 PDF 생성                      |
| `quit`            | 대화형 세션 종료                            |

---

### 4. 소거 연구 실험 모드 (`--mode ablation`)

5가지 컨텍스트 모드(`full`, `no_history`, `no_reasoning`, `no_tool_calls`, `no_tool_results`)를 순차적으로 실행하며 컨텍스트 제거에 따른 모델 행동 변화를 비교 분석합니다.

```bash
# [기능: 기본 제공자로 5가지 컨텍스트 모드 전체 소거 연구 1회 실행]
python main.py --mode ablation

# [기능: 특정 제공자(Doubao / Kimi / DeepSeek)로 소거 연구 실행]
python main.py --mode ablation --provider doubao
python main.py --mode ablation --provider kimi
python main.py --mode ablation --provider deepseek

# [기능: ★ LM Studio 로컬 모델로 소거 연구 실행]
python main.py --mode ablation \
  --provider openai \
  --model "google_gemma-4-26b-a4b-it"

# [기능: llama.cpp 로컬 서버로 소거 연구 실행]
python main.py --mode ablation \
  --provider openai \
  --model "default"

# [기능: Ollama 로컬 모델로 3회 반복 케이스 소거 연구 실행]
python main.py --mode ablation \
  --provider ollama \
  --model "qwen2.5:7b" \
  --cases 3

# [기능: 특정 2개 모드(full vs no_history)만 선별 비교하고 결과 JSON 저장]
python main.py --mode ablation \
  --provider openai \
  --model "google_gemma-4-26b-a4b-it" \
  --ablation-modes full no_history \
  --output lm_studio_ablation.json
```

---

### 5. 한 줄 실행 (인라인 환경 변수 전달)

`.env`나 `export` 없이 일회성으로 즉시 실행할 때 사용합니다:

```bash
# [기능: LM Studio 로컬 서버에 인라인 환경변수로 단일 작업 즉시 실행]
OPENAI_BASE_URL="http://localhost:1234/v1" OPENAI_API_KEY="lm-studio" \
  python main.py --mode single --provider openai --model "google_gemma-4-26b-a4b-it"

# [기능: llama.cpp 로컬 서버에 인라인 환경변수로 소거 연구 즉시 실행]
OPENAI_BASE_URL="http://localhost:8080/v1" OPENAI_API_KEY="llama-cpp" \
  python main.py --mode ablation --provider openai --model "default"
```

---

### 6. 실측 실험 및 연동 점검 스크립트

```bash
# [기능: 교재 제1장 실험 1-1 전용 스크립트 실행 (모든 원시 API 요청/응답 기록)]
python run_experiment_1_1.py --provider kimi --model kimi-k3 --max-iterations 5

# [기능: Kimi API 연동 및 K3 모델 동작 수동 점검]
python tests/manual/check_kimi.py

# [기능: DeepSeek API 연동 및 V4 모델 동작 수동 점검]
python tests/manual/check_deepseek.py
python tests/manual/check_deepseek_quick.py
```

---

### 7. 자동화 테스트 (Pytest)

```bash
# [기능: 에이전트 핵심 로직 및 코드 인터프리터 회귀 테스트 수행]
python -m pytest tests
```
