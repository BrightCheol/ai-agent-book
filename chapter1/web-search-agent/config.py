"""
설정 모듈 - Kimi API 설정
"""

import os
from typing import Optional
from dotenv import load_dotenv

# 작업 디렉토리 상위로 검색하여 가장 가까운 .env를 로드하므로
# 저장소 루트에 있는 단일 .env 파일로 모든 챕터에서 공용으로 사용할 수 있습니다.
load_dotenv()


# Provider resolution lives in the shared agentbook package so every chapter
# stays consistent; see agentbook/providers.py. The fallback keeps this
# experiment runnable from a checkout where agentbook is not installed.
try:
    from agentbook.providers import (
        SUPPORTED_PROVIDERS,
        map_model_to_openrouter,
        resolve_backend,
        resolve_llm_backend,
    )
except ImportError:  # pragma: no cover - exercised only without the package
    import sys as _sys

    _sys.path.insert(
        0, str(__import__("pathlib").Path(__file__).resolve().parents[2])
    )
    from agentbook.providers import (
        SUPPORTED_PROVIDERS,
        map_model_to_openrouter,
        resolve_backend,
        resolve_llm_backend,
    )


class Config:
    """설정 클래스"""
    
    # Kimi API 설정
    MOONSHOT_API_KEY: str = os.getenv("MOONSHOT_API_KEY", "")
    # 하위 호환성: MOONSHOT_API_KEY가 없으면 KIMI_API_KEY 사용 시도
    if not MOONSHOT_API_KEY:
        MOONSHOT_API_KEY = os.getenv("KIMI_API_KEY", "")
    
    # 空值视为「未配置」，与共享注册表 Provider.resolved_base_url() 一致，
    # 避免 .env 里留空的 KIMI_BASE_URL 把端点清空。
    KIMI_BASE_URL: str = (
        os.getenv("KIMI_BASE_URL", "").strip() or "https://api.moonshot.cn/v1"
    )
    
    # 모델 설정
    DEFAULT_MODEL: str = "kimi-k3"  # 최신 Kimi K3 모델 사용

    # 搜索配置
    MAX_SEARCH_ITERATIONS: int = 5  # 最大搜索迭代次数（与 agent 默认值保持一致）
    # 这个超时同时作用于 Formula 工具调用和 chat completion。kimi-k3 以
    # reasoning_effort=max 运行，单次 completion 常需 1-3 分钟（validation/
    # 目录里保留的真实运行记录中有 161 秒、121 秒的调用），30 秒会让交互模式
    # 反复 "Request timed out"。默认值与 run_experiment_1_2.py 的 --timeout
    # 保持一致，确保 README 里的交互入口与验收脚本跑在同一配置下。
    SEARCH_TIMEOUT: float = float(os.getenv("SEARCH_TIMEOUT", "180"))
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def validate(cls) -> bool:
        """
        설정이 유효한지 검증합니다.
        
        Returns:
            bool: 설정 유효 여부
        """
        if not cls.MOONSHOT_API_KEY:
            print("오류: MOONSHOT_API_KEY 환경 변수가 설정되지 않았습니다.")
            print("환경 변수를 설정하세요: export MOONSHOT_API_KEY='your-api-key'")
            print("(또는 기존 변수명 사용: export KIMI_API_KEY='your-api-key')")
            return False
        return True
    
    @classmethod
    def get_api_key(cls, api_key: Optional[str] = None) -> str:
        """
        API Key를 가져옵니다.
        
        Args:
            api_key: 선택적 API key (제공되면 이를 사용하고, 그렇지 않으면 환경 변수에서 가져옴)
            
        Returns:
            API key 문자열
        """
        if api_key:
            return api_key
        return cls.MOONSHOT_API_KEY
