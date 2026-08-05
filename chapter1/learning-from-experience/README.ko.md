# 경험을 통한 학습: RL vs LLM 인컨텍스트 학습 (Learning from Experience: RL vs LLM In-Context Learning)

> 숨겨진 메커니즘이 있는 보물찾기 게임에서 테이블 방식 Q-learning과 LLM 인컨텍스트 학습을 비교합니다 (Shunyu Yao, “The Second Half”).
> 코드는 제1장 프로젝트 트리에 위치하며, 교재의 **실험 7-1 ★ (보물찾기 게임에서 Q-learning의 성능)** 및 **실험 7-2 ★★ (전통적 RL과 LLM Agent의 비교 연구)**에 대응합니다.

← [제1장 목차로 돌아가기](../README.ko.md) · 📖 [제7장 본문 읽기](../../book-ko/chapter7.ko.md)

---

## 개요 (Overview)

본 실험은 전통적인 강화학습(Q-learning)과 LLM 기반의 인컨텍스트 학습(in-context learning)을 비교하며, Shunyu Yao의 블로그 포스트 ["The Second Half"](https://ysymyth.github.io/The-Second-Half/)의 핵심 인사이트를 재현합니다.

전통적인 RL 방식은 게임 메커니즘을 학습하기 위해 광범위한 훈련이 필요한 반면, LLM은 추론을 통해 어떻게 일반화할 수 있는지를 보여줍니다. 에이전트가 경험을 통해 스스로 발견해야 하는 숨겨진 메커니즘을 가진 텍스트 기반 보물찾기 게임을 사용합니다.

## 검증 대상 핵심 인사이트 (Key Insights Being Tested)

1. **샘플 효율성 (Sample Efficiency)**: LLM은 전통적인 RL보다 훨씬 적은 예시만으로 학습할 수 있습니다.
2. **일반화 (Generalization)**: RL이 상태-행동 매핑을 암기하는 동안, LLM은 추론을 사용해 패턴을 이해합니다.
3. **사전 지식 (Prior Knowledge)**: 언어 사전 학습(Language pre-training)은 새로운 작업에 대해 추론할 수 있는 강력한 사전 지식(prior)을 제공합니다.
4. **숨겨진 메커니즘 발견 (Hidden Mechanics Discovery)**: RL이 철저한 탐색(exhaustive exploration)을 필요로 하는 반면, LLM은 가설을 세우고 이를 검증할 수 있습니다.

## 실행 시 확인 가능한 내용 (What You'll See)

LLM 실험을 실행하면 **전체 의사결정 과정**을 확인할 수 있습니다:

```
============================================================
LLM DECISION PROCESS
============================================================
📊 Experiences in memory: 15
🎮 Current room: hallway
🎯 Available actions: 8

💡 Recent successful patterns learned:
   • take red key → +5.0 reward
   • try crafting → +10.0 reward

🤔 LLM is thinking...

📝 LLM Reasoning:
----------------------------------------
  Based on my past experiences, I've learned that:
  1. The red key opens the locked door to the guard room
  2. Crafting rusty sword + magic crystal creates a silver sword
  3. The silver sword can defeat the strong guard
  
  Since I have the silver sword and I'm in the hallway...
----------------------------------------

✅ Chosen action: go north
```

이러한 투명성은 Q-learning의 블랙박스 특성과 달리 LLM이 어떻게 학습하고 추론하는지 정확히 보여줍니다.

## 게임 설명 (The Game)

에이전트가 수행해야 하는 텍스트 기반 보물찾기 게임:

- 여러 방을 돌아다니며 탐색
- 아이템과 열쇠 수집
- 적절한 무기를 사용하여 파수꾼(guard) 처치
- 경험을 통해 숨겨진 메커니즘 발견

### 숨겨진 메커니즘 (에이전트에게 공개되지 않음)

1. **색상별 잠금장치 (Color-coded locks)**: 특정 색상의 열쇠가 해당 색상의 문을 열 수 있음
2. **무기 유효성 (Weapon effectiveness)**: 서로 다른 무기가 서로 다른 적에게 효과를 발휘함
3. **조합 시스템 (Crafting system)**: 특정 아이템들을 조합하여 더 나은 아이템을 제작할 수 있음
4. **포션 효과 (Potion effects)**: 포션을 소비하여 일시적인 능력을 얻을 수 있음

## 빠른 시작 (Quick Start)

### 설치 (Installation)

```bash
# 권장 사항: 저장소 루트에서 공유 제1장 환경 사용
uv sync --locked --extra ch1

# 디렉토리를 변경하기 전에 환경을 활성화하세요:
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows cmd: .venv\Scripts\activate.bat

# uv가 설치되어 있지 않은 경우 pip 대체 방법:
# python -m pip install -e ".[ch1]"

# 아래 명령어 실행을 위해 본 실험 디렉토리로 이동합니다
cd chapter1/learning-from-experience

# 마이그레이션 동안 여전히 지원되는 단일 프로젝트 호환 경로:
# python -m pip install -r requirements.txt
```

- Q-learning은 **API 키 없이** 완전한 오프라인으로 실행됩니다.
- LLM 경로는 Moonshot/Kimi API 키가 필요합니다 (또는 OpenRouter 폴백).

### Kimi K3 API 설정 (Setting up Kimi K3 API)

LLM 실험을 실행하려면 Kimi (Moonshot) API 키가 필요합니다:

1. [Moonshot AI](https://platform.moonshot.cn/)에서 API 키를 발급받으세요.
2. 환경 변수를 설정하세요:

```bash
export MOONSHOT_API_KEY="your-api-key-here"
```

또는 `.env` 파일을 생성하세요:

```bash
echo "MOONSHOT_API_KEY=your-api-key-here" > .env
```

**범용 OpenRouter 폴백 (Universal OpenRouter fallback)**: `MOONSHOT_API_KEY`가 설정되어 있지 않고 `OPENROUTER_API_KEY`가 설정되어 있는 경우, LLM 경로는 OpenRouter를 통해 라우팅됩니다. Kimi 모델이 OpenRouter에서 안정적으로 제공되지 않을 수 있으므로, 폴백 시 `OPENROUTER_MODEL`(기본값 `openai/gpt-5.6-luna`)을 사용합니다:

```bash
export OPENROUTER_API_KEY=your-openrouter-api-key
python quick_demo.py   # MOONSHOT_API_KEY가 없을 때 OpenRouter를 통해 실행
```

## 실험 실행 (Running the Experiment)

### 빠른 데모 (LLM 학습 과정 관찰) (Quick Demo)

```bash
python quick_demo.py
```

이 데모는 LLM이 추론을 통해 어떻게 학습하는지 상세히 보여줍니다:

- 각 의사결정에 대한 전체 사고 과정
- 경험이 축적되고 향후 의사결정에 미치는 영향
- 전통적 RL 대비 압도적인 학습 속도 차이

### 커맨드 라인 인터페이스 (`experiment.py`)

`experiment.py`는 전체 CLI를 제공합니다. 모든 플래그 목록 확인:

```bash
python experiment.py --help
```

주요 매개변수:

| 매개변수 | 설명 | 기본값 |
| --- | --- | --- |
| `--mode {both,qlearning,rl,llm}` | 실행할 에이전트: `qlearning`/`rl` = Q-learning 전용 (오프라인), `llm` = LLM Agent 전용, `both` = 비교 | `both` |
| `--rl-episodes` | Q-learning 훈련 에피소드 수 (실험 7-1은 10000 사용) | `10000` |
| `--llm-episodes` | LLM Agent 훈련 에피소드 수 | `20` |
| `--eval-episodes` | Q-learning 후 탐욕적(Greedy) 평가 에피소드 수 | `100` |
| `--checkpoint-interval` | 학습 곡선 샘플링 간격 (매 N 에피소드마다) | `1000` |
| `--model` | LLM 모델 이름 (또는 `MOONSHOT_MODEL` 환경 변수) | `kimi-k3` |
| `--output` | 결과 출력 디렉토리 | `results` |
| `--seed` | 재현 가능한 Q-learning 곡선을 위한 랜덤 시드 | 미지정 |
| `--learning-rate` / `--discount` / `--epsilon-decay` / `--epsilon-min` | Q-learning 하이퍼파라미터 | `0.2 / 0.99 / 0.9995 / 0.1` |
| `--stochastic` | 확률적(stochastic) 환경 사용 | 결정론적(deterministic) |
| `--skip-llm` | `--mode qlearning`에 대한 레거시 별칭 | — |

### Q-Learning 전용 (실험 7-1, 오프라인, API 불필요)

```bash
python experiment.py --mode qlearning --rl-episodes 10000 --seed 42
```

훈련은 약 3초 이내에 완료되며, 에이전트가 1만 회에 가까운 에피소드 동안 승률 0%에서 숙련 단계까지 어떻게 도달하는지 보여주는 **학습 곡선 표**를 출력합니다 (아래 결과 참조).

### 전체 비교 (RL vs LLM, 실험 7-2)

```bash
python experiment.py --mode both --model kimi-k3
```

교재의 정확한 프로토콜 및 승인 등급 검증을 위해 표준 러너(canonical runner)를 사용하세요. 10,000 에피소드의 Q-learning, 100회의 탐욕적 평가 에피소드, 그리고 단 1회의 공식 Moonshot Kimi K3 첫 번째 시도 궤적을 실행합니다:

```bash
python run_experiment_7_2.py
```

표준 러너는 OpenRouter 대체, API 오류, 누락된 원시 공급자 응답 ID/본문, 및 파서 폴백(parser fallback)을 거부합니다. 결과를 `validation/<timestamp>/evidence.json`에 기록하며, 실행 후 직렬화만 복구해야 하는 경우 `finalize_experiment_7_2.py <campaign-dir>`를 통해 유료 모델 호출을 반복하지 않고 이미 저장된 원시 결과를 최종 확정합니다.

이 과정은 다음을 수행합니다:

1. Q-learning 에이전트를 10,000 에피소드 동안 훈련하고 (~3초) 학습 곡선을 출력
2. 상세한 추론 과정 표시와 함께 LLM 에이전트를 20 에피소드 동안 훈련
3. 두 에이전트 평가
4. 비교 그래프 생성
5. `results/` 디렉토리에 결과 저장

**참고**: `experiment.py`는 탐색적 다중 에피소드 러너입니다. 교재의 표준 캠페인은 의도적으로 첫 번째 시도 1회를 측정합니다. 승인된 2026-07-30 Kimi K3 시도는 17회의 순차적 추론 호출에 416.11초가 소요되었으며, 이전의 "게임당 1~2분" 추정치는 이 경로에서 재현되지 않았습니다.

### LLM 전용

```bash
python experiment.py --mode llm --llm-episodes 20
```

### 대화형 게임 플레이 (Interactive Game Play)

수동으로 게임을 테스트해보세요:

```python
from game_environment import TreasureHuntGame

game = TreasureHuntGame()
print(game.get_state_description())
print("Available actions:", game.get_available_actions())

# 행동 시도
feedback, reward, done = game.execute_action("take rusty sword")
print(f"Feedback: {feedback}")
print(f"Reward: {reward}")
```

## 검증 (Validation)

깨끗한 환경에서 pytest를 실행하기 전에 저장소 루트에서 `dev` extra를 설치하세요:

```bash
uv sync --locked --extra ch1 --extra dev

# 디렉토리를 변경하기 전에 환경을 활성화하세요:
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows cmd: .venv\Scripts\activate.bat

cd chapter1/learning-from-experience
python -m pytest tests
```

더 긴 Q-learning 학습 곡선 검사는 오프라인 수동 스모크 스크립트이며, 기본 pytest 수집 대상에서 제외됩니다:

```bash
python tests/manual/rl_learning_check.py --episodes 1000
```

## 실험 결과 (Experiment Results)

### 비교 지표 (Metrics Compared)

1. **샘플 효율성 (Sample Efficiency)** — 좋은 성능을 달성하기 위해 필요한 에피소드 수; 학습 속도
2. **성능 (Performance)** — 평가 시 승률; 평균 보상 및 에피소드 길이
3. **계산 비용 (Computational Cost)** — 훈련 시간; 메모리 (Q-테이블 크기 vs. 경험 저장소); LLM API 호출 횟수

### 시각화 (Visualizations)

실험을 통해 다음과 같은 비교 그래프가 생성됩니다:

- 시간에 따른 학습 곡선
- 승률 진행 상황
- 샘플 효율성 비교
- 핵심 인사이트 요약

### 예상 결과 (Expected Results)

#### Q-Learning 학습 곡선 (로컬 실측, `--mode qlearning --rl-episodes 10000 --seed 42`)

실측 곡선 (결정론적 환경; 최근 1000 에피소드 슬라이딩 윈도우 기준 승률; 전체 훈련 ~3초):

| 에피소드 (Episodes) | 승률 (Victory rate) | Q-테이블 상태 수 (Q-table states) | epsilon |
| ---: | ---: | ---: | ---: |
| 1000 | 0.3% | 123 | 0.606 |
| 2000 | 0.0% | 123 | 0.368 |
| 3000 | 0.1% | 126 | 0.223 |
| 5000 | 0.1% | 128 | 0.100 |
| 7000 | 97.0% | 138 | 0.100 |
| 8000 | 99.6% | 138 | 0.100 |
| 9000 | 99.8% | 139 | 0.100 |
| 10000 | **98.1%** | 142 | 0.100 |

훈련 후 표준 탐욕적 평가의 승률은 **100%**에 달하며 평균 12단계가 걸립니다. 승인된 Kimi K3 팔(arm)은 첫 시도에서 17/17의 실제 응답과 0건의 API 오류, 0건의 폴백, 28,242토큰으로 17단계 만에 승리했습니다. 이는 첫 시도 성공 결론을 재현하지만, 원고의 역사적 점 추정치인 정확히 18 Kimi 단계 및 11단계 Q-learning 솔루션과는 차이가 있습니다. [표준 증거(canonical evidence)](validation/20260730_011704/evidence.json)를 참조하세요.

#### RL vs LLM (실험 7-2 결론)

- **Q-Learning**: 안정적인 클리어를 위해 ~10,000 에피소드가 필요함; "문 / 열쇠 / 검"을 의미 없는 기호로 취급하고 통계적으로만 탐색함.
- **LLM In-Context**: 사전 학습된 사전 지식을 포함함; 게임 개념 구조에 대한 추론을 통해 수십 단계 내의 첫 번째 에피소드에서 통과하는 경우가 많음.
- **샘플 효율성**: LLM이 2~3 자릿수(orders of magnitude) 더 높음; 단, 에피소드당 추론 속도가 느림(API ~1-2분), 반면 Q-learning은 약 3초 만에 10,000 에피소드를 마침 — 트레이드오프는 상호작용 비용에 달려 있음 (교재 실험 7-2 참조).

## 프로젝트 구조 (Project Structure)

```
learning-from-experience/
├── game_environment.py    # 숨겨진 메커니즘이 있는 텍스트 기반 게임
├── rl_agent.py            # Q-learning 구현
├── llm_agent.py           # 인컨텍스트 학습이 적용된 LLM
├── experiment.py          # 메인 실험 러너
├── demo.py                # 대화형 로컬 게임 데모
├── quick_demo.py          # 짧은 LLM 학습 데모
├── run_experiment_7_2.py  # 실제 교재 규격 실측 및 승인 게이트
├── finalize_experiment_7_2.py # 증거 복구 전용; API 재호출 없음
├── env.example            # 선택 사항 API 키 템플릿
├── tests/
│   ├── test_basic.py
│   ├── test_zero_episodes.py
│   ├── test_rl_progress_small_episodes.py
│   └── manual/
│       └── rl_learning_check.py
├── requirements.txt       # Python 의존성
├── README.md              # 영어/중문 README
├── README.ko.md           # 한국어 README (본 파일)
└── results/               # 실험 출력 디렉토리 (실행 시 생성됨)
    └── [timestamp]/
        ├── rl_agent.pkl           # 훈련된 Q-learning 에이전트
        ├── llm_experiences.json   # LLM이 수집한 경험
        ├── experiment_results.json # 수치 결과
        └── comparison_plots.png   # 시각화 그래프
```

## 기술적 세부사항 (Technical Details)

### Q-Learning Agent

- **알고리즘**: ε-greedy 탐색이 적용된 Tabular Q-learning
- **상태 표현**: 방, 인벤토리, 게임 상태의 해시 조합
- **학습률 (Learning Rate)**: 0.2 (`--learning-rate`로 설정 가능)
- **할인율 (Discount Factor)**: 0.99 (`--discount`로 설정 가능)
- **탐색 (Exploration)**: ε는 1.0에서 시작하여 `--epsilon-decay`(0.9995) 비율로 `--epsilon-min`(0.1)까지 감쇄

### LLM Agent (Kimi K3)

- **모델**: `kimi-k3` (`--model` 또는 `MOONSHOT_MODEL`로 변경 가능)
- **추론 모델**: Kimi K3는 최종 답변(`message.content`) 전에 사고 과정(`message.reasoning_content`)을 출력하므로, 코드에서는 `max_tokens=2048`을 여유 있게 설정하여 `ACTION:` 줄이 추론 예산으로 인해 생략(truncated)되지 않도록 합니다.
- **학습 방법**: 경험 메모리(최대 50개 경험)를 이용한 인컨텍스트 학습
- **컨텍스트 관리**: 성공 및 실패 경험을 저장
- **추론**: 행동을 취하기 전에 과거 경험에 대해 추론하도록 LLM에 프롬프트 제공
- **Temperature**: 0.7을 요청하지만 추론 모델(Kimi K3, GPT-5)은 `temperature=1`만 허용하므로 코드가 자동으로 `1`로 강제 적용합니다 (`_reasoning_safe_temperature` 참조).

## 실험 확장하기 (Extending the Experiment)

### 후속 연구 아이디어 (Ideas for Further Research)

1. **다양한 게임**: 다른 숨겨진 메커니즘 게임에 적용
2. **하이브리드 접근 방식**: RL과 LLM 가이드를 결합
3. **전이 학습 (Transfer Learning)**: 유사한 게임으로 에이전트가 얼마나 잘 전이되는지 테스트
4. **소거 연구 (Ablation Studies)**: 추론 프롬프트를 제거하여 추론의 영향 독립 평가
5. **기타 LLM**: 다양한 언어 모델 간 비교

### 게임 수정하기 (Modifying the Game)

`game_environment.py`를 편집하여 다음을 수행할 수 있습니다:

- 새로운 방과 아이템 추가
- 더 복잡한 숨겨진 메커니즘 생성
- 난이도 및 보상 조절
- 새로운 유형의 퍼즐 추가

## 교육적 가치 (Educational Value)

1. **사전 지식의 힘 (The Power of Priors)**: 언어 사전 학습이 유용한 지식을 제공하는 방식
2. **추론 vs. 암기 (Reasoning vs. Memorization)**: 학습에 대한 서로 다른 접근 방식
3. **샘플 효율성 (Sample Efficiency)**: 실제 애플리케이션에서 이것이 중요한 이유
4. **"The Second Half" 가설**: "해결할 수 있는가?"에서 "얼마나 효율적인가?"로의 전환

## 참고 문헌 (References)

- [The Second Half](https://ysymyth.github.io/The-Second-Half/) by Shunyu Yao
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- Original Q-learning paper: Watkins & Dayan (1992)

---

## 참고 사항 (Notes)

- 프로젝트 유형: **✅ 독립 실행 가능** (Q-learning 오프라인, LLM은 API 키 필요).
- 교육 목적; AI 및 RL 관련 학술 연구에서 영감을 받음.
- 숨겨진 메커니즘, 다른 RL 알고리즘 (DQN, PPO 등), 제공자, 또는 더 풍부한 지표를 자유롭게 추가하세요.
