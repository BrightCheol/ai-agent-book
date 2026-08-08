"""
고급 예제 - Web Search Agent의 다양한 활용법 시연
"""

import json
from typing import List, Dict, Any
from agent import WebSearchAgent, is_failure_answer
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedWebSearchAgent(WebSearchAgent):
    """
    고급 Web Search Agent - 기능 확장 클래스
    """
    
    def batch_search(self, questions: List[str]) -> List[Dict[str, str]]:
        """
        여러 질문을 일괄 검색합니다.
        
        Args:
            questions: 질문 목록
            
        Returns:
            답변 결과 목록
        """
        results = []
        for i, question in enumerate(questions, 1):
            logger.info(f"질문 처리 중 {i}/{len(questions)}: {question}")
            try:
                answer = self.search_and_answer(question)
                # search_and_answer 내부에서 예외를 잡고 에러 문자열을 반환하므로(agent.py 참조),
                # 아래의 except는 일반적으로 트리거되지 않습니다. 통합된 is_failure_answer를 통해
                # "오류 발생 / 최대 반복 초과 / 정보 부족" 등 모든 실패 케이스를 판정하여
                # 실패한 검색이 success로 오판되는 것을 방지합니다.
                status = "error" if is_failure_answer(answer) else "success"
                results.append({
                    "question": question,
                    "answer": answer,
                    "status": status
                })
            except Exception as e:
                results.append({
                    "question": question,
                    "answer": str(e),
                    "status": "error"
                })
            # 대화 이력을 초기화하여 컨텍스트 간섭을 방지
            self.clear_history()
        return results
    
    def search_with_context(self, question: str, context: str) -> str:
        """
        컨텍스트 기반 검색
        
        Args:
            question: 사용자 질문
            context: 추가 배경 정보 컨텍스트
            
        Returns:
            답변 문자열
        """
        # 컨텍스트가 포함된 질문 구성
        contextualized_question = f"""
배경 정보: {context}

위 배경 정보를 바탕으로 다음 질문에 답변해 주세요:
{question}
"""
        return self.search_and_answer(contextualized_question)
    
    def comparative_search(self, items: List[str], aspect: str) -> str:
        """
        비교 검색 - 여러 항목을 검색하고 비교합니다.
        
        Args:
            items: 비교할 항목 목록
            aspect: 비교할 측면/기준
            
        Returns:
            비교 결과 문자열
        """
        # 비교 질문 구성
        items_str = ", ".join(items)
        question = f"{items_str}의 {aspect} 측면에서의 차이점과 장단점을 검색하여 비교 분석해 주세요."
        
        return self.search_and_answer(question)
    
    def fact_check(self, statement: str) -> Dict[str, Any]:
        """
        팩트 체크 - 주장의 사실 여부를 검증합니다.
        
        Args:
            statement: 검증할 주장 문장
            
        Returns:
            검증 결과 딕셔너리
        """
        question = f"""
다음 주장의 사실 여부를 검증해 주세요:
"{statement}"

반드시 다음 형식으로 엄격히 답변해 주세요:
- 첫 줄에는 판정 결과만 출력 (다음 3가지 중 택 1: 참 / 거짓 / 일부 사실)
- 그 다음 줄부터 관련 사실, 근거 및 정보 출처를 설명
"""
        answer = self.search_and_answer(question)

        # 판정 파싱: 모델이 첫 줄에 "참/거짓/일부 사실"만 출력하도록 요청됨
        first_line = next((ln.strip() for ln in answer.splitlines() if ln.strip()), "")
        if "일부 사실" in first_line or "일부 참" in first_line or "일부 맞음" in first_line:
            is_true = False
        elif any(neg in first_line for neg in ("거짓", "허위", "사실 아님", "틀림", "오류", "아님")):
            is_true = False
        else:
            is_true = "참" in first_line or "사실" in first_line or "맞음" in first_line or "진실" in first_line
        return {
            "statement": statement,
            "is_true": is_true,
            "explanation": answer
        }


def example_basic_search():
    """기본 검색 예제"""
    print("\n" + "="*60)
    print("📌 예제 1: 기본 검색")
    print("="*60)
    
    agent = WebSearchAgent(Config.get_api_key())
    
    questions = [
        "OpenAI가 최근 발표한 최신 모델의 주요 특징은 무엇인가요?",
        "머신러닝을 공부하기 위한 추천 학습 로드맵과 자료를 알려주세요.",
    ]
    
    for q in questions:
        print(f"\n질문: {q}")
        print("-"*40)
        answer = agent.search_and_answer(q)
        print(f"답변: {answer}")


def example_batch_search():
    """일괄(Batch) 검색 예제"""
    print("\n" + "="*60)
    print("📌 예제 2: 일괄 검색")
    print("="*60)
    
    agent = AdvancedWebSearchAgent(Config.get_api_key())
    
    questions = [
        "React와 Vue의 주요 아키텍처 차이점은 무엇인가요?",
        "Python이 가장 적합한 프로젝트 분야는 무엇인가요?",
        "인공지능 공부를 시작하는 가장 좋은 방법은 무엇인가요?",
    ]
    
    results = agent.batch_search(questions)
    
    for result in results:
        print(f"\n질문: {result['question']}")
        print(f"상태: {result['status']}")
        print(f"답변: {result['answer'][:200]}...")  # 앞 200자만 출력


def example_contextual_search():
    """컨텍스트 기반 검색 예제"""
    print("\n" + "="*60)
    print("📌 예제 3: 컨텍스트 기반 검색")
    print("="*60)
    
    agent = AdvancedWebSearchAgent(Config.get_api_key())
    
    context = "저는 이제 막 프로그래밍을 시작한 대학생이며, 웹 개발에 가장 관심이 많습니다."
    question = "어떤 프로그래밍 언어를 먼저 공부하는 것이 좋을까요?"
    
    print(f"컨텍스트: {context}")
    print(f"질문: {question}")
    print("-"*40)
    
    answer = agent.search_with_context(question, context)
    print(f"답변: {answer}")


def example_comparative_search():
    """비교 검색 예제"""
    print("\n" + "="*60)
    print("📌 예제 4: 비교 검색")
    print("="*60)
    
    agent = AdvancedWebSearchAgent(Config.get_api_key())
    
    # 여러 기술 프레임워크 비교
    items = ["TensorFlow", "PyTorch", "JAX"]
    aspect = "성능 및 사용 편의성"
    
    print(f"비교 대상: {', '.join(items)}")
    print(f"비교 기준: {aspect}")
    print("-"*40)
    
    result = agent.comparative_search(items, aspect)
    print(f"비교 결과:\n{result}")


def example_fact_check():
    """팩트 체크 예제"""
    print("\n" + "="*60)
    print("📌 예제 5: 팩트 체크")
    print("="*60)
    
    agent = AdvancedWebSearchAgent(Config.get_api_key())
    
    statements = [
        "Python은 전 세계에서 가장 인기 있는 프로그래밍 언어 중 하나이다.",
        "양자 컴퓨터는 이미 모든 현대 암호화 알고리즘을 해독할 수 있다.",
        "GPT-4는 1.76조 개의 파라미터를 가지고 있다.",
    ]
    
    for statement in statements:
        print(f"\n검증 대상 문장: {statement}")
        result = agent.fact_check(statement)
        print(f"진위 여부: {'✅ 참' if result['is_true'] else '❌ 거짓/불확실'}")
        print(f"상세 설명: {result['explanation'][:200]}...")


def example_research_assistant():
    """연구 보조 예제 - 특정 주제에 대한 심층 연구"""
    print("\n" + "="*60)
    print("📌 예제 6: 연구 보조 - 심층 연구")
    print("="*60)
    
    agent = AdvancedWebSearchAgent(Config.get_api_key())
    
    topic = "대규모 언어 모델(LLM)의 발전 과정"
    
    # 연구 질문 시퀀스 구성
    research_questions = [
        f"{topic}이란 무엇인가요? 상세한 정의를 제공해 주세요.",
        f"{topic}의 주요 마일스톤과 핵심 사건은 무엇인가요?",
        f"{topic}이 직면한 주요 기술적 과제는 무엇인가요?",
        f"{topic}의 미래 발전 트렌드는 어떻게 전망되나요?",
    ]
    
    print(f"연구 주제: {topic}")
    print("="*60)
    
    research_report = []
    for i, q in enumerate(research_questions, 1):
        print(f"\n연구 질문 {i}: {q}")
        print("-"*40)
        answer = agent.search_and_answer(q)
        research_report.append({
            "section": i,
            "question": q,
            "findings": answer
        })
        print(f"조사 결과: {answer[:300]}...")
        agent.clear_history()  # 질문별 독립성을 위해 이력 초기화
    
    # 연구 보고서 저장
    with open("research_report.json", "w", encoding="utf-8") as f:
        json.dump(research_report, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 연구 보고서가 research_report.json에 저장되었습니다.")


def main():
    """모든 예제 실행"""
    
    if not Config.validate():
        print("请先设置 MOONSHOT_API_KEY（或 KIMI_API_KEY）环境变量")
        return
    
    examples = [
        ("기본 검색", example_basic_search),
        ("일괄 검색", example_batch_search),
        ("컨텍스트 기반 검색", example_contextual_search),
        ("비교 검색", example_comparative_search),
        ("팩트 체크", example_fact_check),
        ("연구 보조", example_research_assistant),
    ]
    
    print("\n" + "="*60)
    print("🎯 Kimi Web Search Agent - 고급 예제")
    print("="*60)
    print("\n실행할 예제를 선택하세요:")
    
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    print(f"{len(examples) + 1}. 모든 예제 순차 실행")
    print("0. 종료")
    
    try:
        choice = input("\n옵션을 입력하세요 (0-7): ").strip()
        choice = int(choice)
        
        if choice == 0:
            print("프로그램을 종료합니다.")
            return
        elif 1 <= choice <= len(examples):
            examples[choice - 1][1]()
        elif choice == len(examples) + 1:
            for name, func in examples:
                try:
                    func()
                except Exception as e:
                    logger.error(f"{name} 실행 중 오류 발생: {str(e)}")
        else:
            print("유효하지 않은 옵션입니다.")
    except ValueError:
        print("유효한 숫자를 입력해 주세요.")
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
    except Exception as e:
        logger.error(f"예제 실행 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    main()
