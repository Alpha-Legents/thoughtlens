import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings:
    """Manually load settings from environment without Pydantic validation."""
    
    def __init__(self):
        self.tl_port = int(os.environ.get("TL_PORT", "8000"))
        self.tl_llm_url = os.environ.get("TL_LLM_URL", "https://api.groq.com/openai/v1")
        self.tl_llm_key = os.environ.get("TL_LLM_KEY", "placeholder_key")
        self.tl_lt_port = int(os.environ.get("TL_LT_PORT", "8080"))
        self.tl_lt_binary = os.environ.get("TL_LT_BINARY", "./lobstertrap/lobstertrap")
        self.tl_lt_policy = os.environ.get("TL_LT_POLICY", "./configs/thoughtlens_policy.yaml")
        self.tl_log_level = os.environ.get("TL_LOG_LEVEL", "info")
        self.prism_provider = os.environ.get("PRISM_PROVIDER", "https://api.groq.com/openai/v1")
        self.prism_key = os.environ.get("PRISM_KEY", "placeholder_key")
        self.prism_model = os.environ.get("PRISM_MODEL", "llama-3.3-70b-versatile")

settings = Settings()