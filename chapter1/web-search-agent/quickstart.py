#!/usr/bin/env python3
"""
빠른 시작 스크립트 - Kimi Web Search Agent 원클릭 체험
"""

import os
import sys
from agent import WebSearchAgent

# 컬러 콘솔 출력
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_colored(text, color):
    """컬러 텍스트를 출력합니다."""
    print(f"{color}{text}{Colors.END}")


def print_banner():
    """환영 배너를 출력합니다."""
    banner = """
╔══════════════════════════════════════════════════════════╗
║         🤖 Kimi Web Search Agent - 빠른 체험              ║
║                                                          ║
║  Kimi API 기반의 지능형 검색 어시스턴트                     ║
║  웹 정보를 자동으로 검색하고 지능형 답변을 생성합니다          ║
╚══════════════════════════════════════════════════════════╝
"""
    print_colored(banner, Colors.CYAN)


def check_api_key():
    """API Key 설정을 확인합니다."""
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        # 하위 호환성: 기존 환경 변수명 확인
        api_key = os.getenv("KIMI_API_KEY")
    
    if not api_key:
        print_colored("\n⚠️  API Key가 감지되지 않았습니다.", Colors.WARNING)
        print("\n다음 단계에 따라 설정해 주세요:")
        print("1. https://platform.moonshot.ai/ 에 방문하여 API Key를 발급받으세요.")
        print("2. 환경 변수를 설정하세요:")
        print("   export MOONSHOT_API_KEY='your-api-key'")
        print("   (또는: export KIMI_API_KEY='your-api-key')")
        print("\n또는 API Key를 직접 입력하세요 (건너뛰려면 'skip' 입력):")
        
        user_input = input("> ").strip()
        
        if user_input.lower() == 'skip':
            return None
        elif user_input:
            return user_input
        else:
            return None
    
    print_colored("✅ API Key가 설정되었습니다.", Colors.GREEN)
    return api_key


def demo_search(agent):
    """검색 기능을 시연합니다."""
    print_colored("\n📝 검색 기능 시연", Colors.HEADER)
    print("-" * 60)
    
    demo_questions = [
        "OpenAI가 최근 출시한 신제품은 무엇인가요?",
        "2024년에 어떤 중요한 AI 기술 혁신이 있었나요?",
        "머신러닝 학습은 어떻게 시작하는 것이 좋나요?",
    ]
    
    print("데모 질문 중 하나를 선택하거나, 원하는 질문을 직접 입력하세요:")
    for i, q in enumerate(demo_questions, 1):
        print(f"{i}. {q}")
    print("0. 사용자 정의 질문 직접 입력")
    
    choice = input("\n선택하세요 (0-3): ").strip()
    
    try:
        choice = int(choice)
        if choice == 0:
            question = input("질문을 입력하세요: ").strip()
            if not question:
                print_colored("❌ 질문을 비워둘 수 없습니다.", Colors.FAIL)
                return
        elif 1 <= choice <= len(demo_questions):
            question = demo_questions[choice - 1]
        else:
            print_colored("❌ 유효하지 않은 선택입니다.", Colors.FAIL)
            return
    except ValueError:
        print_colored("❌ 숫자를 입력해 주세요.", Colors.FAIL)
        return
    
    print_colored(f"\n🔍 검색 중: {question}", Colors.BLUE)
    print("잠시만 기다려 주세요. Agent가 검색 및 분석 중입니다...")
    print("-" * 60)
    
    try:
        answer = agent.search_and_answer(question)
        print_colored("\n📖 Agent 답변:", Colors.GREEN)
        print(answer)
    except Exception as e:
        print_colored(f"\n❌ 검색 실패: {str(e)}", Colors.FAIL)


def interactive_mode(agent):
    """대화형 모드"""
    print_colored("\n💬 대화형 모드에 진입했습니다.", Colors.HEADER)
    print("연속해서 질문할 수 있으며, 'quit'를 입력하면 종료됩니다.")
    print("-" * 60)
    
    while True:
        question = input("\n질문: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print_colored("👋 이용해 주셔서 감사합니다!", Colors.GREEN)
            break
        
        if not question:
            continue
        
        print_colored("🔍 검색 중...", Colors.BLUE)
        
        try:
            answer = agent.search_and_answer(question)
            print_colored("\n📖 답변:", Colors.GREEN)
            print(answer)
        except Exception as e:
            print_colored(f"❌ 오류: {str(e)}", Colors.FAIL)


def main():
    """메인 함수"""
    print_banner()
    
    # API Key 확인
    api_key = check_api_key()
    if not api_key:
        print_colored("\n⚠️  진행할 수 없습니다. API Key 설정이 필요합니다.", Colors.WARNING)
        sys.exit(1)
    
    # Agent 생성
    try:
        print_colored("\n🚀 Agent 초기화 중...", Colors.BLUE)
        agent = WebSearchAgent(api_key=api_key)
        print_colored("✅ Agent 준비 완료", Colors.GREEN)
    except Exception as e:
        print_colored(f"❌ 초기화 실패: {str(e)}", Colors.FAIL)
        sys.exit(1)
    
    # 모드 선택
    print("\n사용 모드를 선택하세요:")
    print("1. 데모 검색 (빠른 체험)")
    print("2. 대화형 모드 (연속 대화)")
    print("3. 종료")
    
    mode = input("\n선택하세요 (1-3): ").strip()
    
    if mode == "1":
        demo_search(agent)
        # 계속 여부 확인
        cont = input("\n대화형 모드로 전환하시겠습니까? (y/n): ").strip().lower()
        if cont == 'y':
            interactive_mode(agent)
    elif mode == "2":
        interactive_mode(agent)
    elif mode == "3":
        print_colored("👋 안녕히 가세요!", Colors.GREEN)
    else:
        print_colored("❌ 유효하지 않은 선택입니다.", Colors.FAIL)
    
    print_colored("\nKimi Web Search Agent를 이용해 주셔서 감사합니다!", Colors.CYAN)
    print("추가 기능 및 문서는 다음을 참고하세요:")
    print("- README.ko.md: 전체 한글 문서")
    print("- examples.py: 고급 예제")
    print("- main.py: 메인 실행 프로그램")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n👋 프로그램이 중단되었습니다.", Colors.WARNING)
    except Exception as e:
        print_colored(f"\n❌ 오류 발생: {str(e)}", Colors.FAIL)
        sys.exit(1)
