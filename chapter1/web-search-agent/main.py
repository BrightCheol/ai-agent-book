"""
메인 프로그램 - Web Search Agent 사용 예제

제1장의 ReAct 루프(Reasoning + Acting)를 시연합니다: 모델이 먼저 생각(Reasoning)하고,
web_search를 호출하여 행동(Action)하며, 검색 결과를 관찰(Observation)한 후 다시 생각하여
최종 답변을 종합할 때까지 반복합니다. 실행 시 ReAct 궤적이 단계별로 출력됩니다.
"""

import os
import sys
import json
import argparse
import logging
from typing import Optional
from agent import WebSearchAgent, run_offline_demo
from config import Config

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


def _save_output(path: str, payload: dict):
    """질문, ReAct 궤적, 답변을 JSON 파일로 저장합니다."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n💾 결과가 저장되었습니다: {path}")


def run_interactive_mode(agent: WebSearchAgent, output: Optional[str] = None):
    """
    交互式模式 - 每次提问独立（search_and_answer 会重置对话历史，无跨问题上下文）

    Args:
        agent: WebSearchAgent 인스턴스
        output: 선택 사항, 각 Q&A 궤적을 저장할 JSON 파일 경로
    """
    print("\n" + "="*60)
    print("🤖 Kimi Web Search Agent - 대화형 모드")
    print("="*60)
    print("输入您的问题，Agent 将自动搜索并回答")
    print("输入 'quit' 或 'exit' 退出")
    print("="*60 + "\n")

    while True:
        try:
            # 사용자 입력 받기
            user_input = input("질문: ").strip()

            # 종료 명령 확인
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 종료합니다. 안녕히 가세요!")
                break

            # 이력 초기화 확인
            if user_input.lower() == 'clear':
                agent.clear_history()
                print("✅ 대화 이력이 초기화되었습니다.\n")
                continue

            # 빈 입력 확인
            if not user_input:
                print("❌ 질문을 입력해 주세요.\n")
                continue

            # 검색 및 생각 중 표시
            print("\n🔍 Agent가 검색 및 생각 중입니다 (ReAct 궤적):\n")

            # 답변 가져오기 (verbose=True일 때 궤적이 agent 내부에서 실시간 출력됨)
            answer = agent.search_and_answer(user_input, max_iterations=Config.MAX_SEARCH_ITERATIONS)

            # 답변 출력
            print("\n" + "="*60)
            print("📝 Agent 답변:")
            print("-"*60)
            print(answer)
            print("="*60 + "\n")

            if output:
                _save_output(output, {"question": user_input,
                                      "trace": agent.get_trace(),
                                      "answer": answer,
                                      "api_turns": agent.get_api_turns(),
                                      "provider": "openrouter" if agent.using_openrouter else "moonshot",
                                      "model": agent.model,
                                      "base_url": agent.base_url})

        except KeyboardInterrupt:
            print("\n\n👋 인터럽트가 감지되어 프로그램을 종료합니다.")
            break
        except Exception as e:
            logger.error(f"질문 처리 중 오류 발생: {str(e)}")
            print(f"\n❌ 오류가 발생했습니다: {str(e)}\n")


def run_single_question(agent: WebSearchAgent, question: str,
                        max_iterations: int, output: Optional[str] = None):
    """
    단일 질문 모드 - 하나의 질문에 답변한 후 종료합니다.

    Args:
        agent: WebSearchAgent 인스턴스
        question: 답변할 질문
        max_iterations: 최대 ReAct 반복 횟수
        output: 선택 사항, 궤적을 저장할 JSON 파일 경로
    """
    print("\n" + "="*60)
    print("🤖 Kimi Web Search Agent")
    print("="*60)
    print(f"질문: {question}")
    print("-"*60)
    print("🔍 ReAct 궤적 (생각 → 행동 → 관찰):\n")

    try:
        answer = agent.search_and_answer(question, max_iterations=max_iterations)
        print("\n📝 최종 답변:")
        print("-"*60)
        print(answer)
        print("="*60 + "\n")

        if output:
            _save_output(output, {"question": question,
                                  "trace": agent.get_trace(),
                                  "answer": answer,
                                  "api_turns": agent.get_api_turns(),
                                  "provider": "openrouter" if agent.using_openrouter else "moonshot",
                                  "model": agent.model,
                                  "base_url": agent.base_url})
    except Exception as e:
        logger.error(f"질문 처리 중 오류 발생: {str(e)}")
        print(f"\n❌ 오류가 발생했습니다: {str(e)}\n")


def build_parser() -> argparse.ArgumentParser:
    """명령줄 인수 파서 구성 (한국어 도움말)"""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Kimi Web Search Agent —— ReAct 루프(생각 → 행동 → 관찰)를 시연하는 자율 검색 에이전트.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""사용 예시:
  python main.py                                  # 대화형 모드 진입
  python main.py "2024년 노벨 물리학상 수상자는 누구인가요?"    # 단일 질문 실행 (ReAct 궤적 출력)
  python main.py --provider offline-demo          # 오프라인 ReAct 루프 데모 (API Key 불필요)
  python main.py "비트코인 현재가" --max-steps 3 --output result.json
""",
    )
    parser.add_argument("query", nargs="*",
                        help="질문 내용 (생략 시 대화형 모드로 진입)")
    parser.add_argument("--provider", choices=["kimi", "offline-demo"], default="kimi",
                        help="검색 백엔드: kimi=Kimi Formula web_search 호출 (API Key 필요); "
                             "offline-demo=샘플 궤적 오프라인 재생 (기본값: kimi)")
    parser.add_argument("--model", default=Config.DEFAULT_MODEL,
                        help=f"사용할 모델 이름 (기본값: {Config.DEFAULT_MODEL})")
    parser.add_argument("--max-steps", type=int, default=Config.MAX_SEARCH_ITERATIONS,
                        help=f"최대 ReAct 반복 횟수 (기본값: {Config.MAX_SEARCH_ITERATIONS})")
    parser.add_argument("--base-url", default=Config.KIMI_BASE_URL,
                        help=f"API 기본 URL (기본값: {Config.KIMI_BASE_URL})")
    parser.add_argument("--api-key", default=None,
                        help="Kimi API Key (기본값: MOONSHOT_API_KEY / KIMI_API_KEY 환경 변수에서 로드)")
    parser.add_argument("--output", "-o", default=None,
                        help="질문, ReAct 궤적, 답변을 지정된 JSON 파일로 저장")
    parser.add_argument("--quiet", action="store_true",
                        help="ReAct 궤적을 실시간으로 출력하지 않음 (기본값: 실시간 출력)")
    return parser


def main(argv: Optional[list] = None):
    """메인 함수: 명령줄 인수를 파싱하고 해당 모드를 실행합니다."""
    parser = build_parser()
    args = parser.parse_args(argv)
    question = " ".join(args.query).strip()

    # 오프라인 데모 모드: API Key 없이 샘플 궤적을 재생하여 ReAct 루프를 시연
    if args.provider == "offline-demo":
        demo_question = question or "Moonshot AI의 Context Caching 기술이란 무엇인가요?"
        print("\n" + "="*60)
        print("🧪 오프라인 데모 모드 (샘플 궤적, 실제 검색 결과 아님)")
        print("="*60)
        print(f"질문: {demo_question}")
        print("-"*60)
        print("🔍 ReAct 궤적 (생각 → 행동 → 관찰):\n")
        result = run_offline_demo(demo_question, verbose=not args.quiet)
        print("\n📝 답변:")
        print("-"*60)
        print(result["answer"])
        print("="*60 + "\n")
        if args.output:
            _save_output(args.output, result)
        return

    # 온라인 모드: API Key 필요
    api_key = Config.get_api_key(args.api_key)
    if not api_key and not os.getenv("OPENROUTER_API_KEY"):
        Config.validate()
        print("안내: 범용 폴백을 위해 OPENROUTER_API_KEY를 설정할 수도 있습니다.")
        sys.exit(1)

    # Agent 생성
    try:
        agent = WebSearchAgent(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            verbose=not args.quiet,
        )
        logger.info("Agent 초기화 성공")
    except Exception as e:
        logger.error(f"Agent 초기화 실패: {str(e)}")
        sys.exit(1)

    # 질문이 있으면 단일 질의응답, 없으면 대화형 모드 진입
    if question:
        run_single_question(agent, question, args.max_steps, args.output)
    else:
        run_interactive_mode(agent, args.output)


if __name__ == "__main__":
    main()
