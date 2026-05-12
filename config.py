from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tl_port: int = 8000
    tl_llm_url: str = "https://api.groq.com/openai/v1"
    tl_llm_key: str = "placeholder_key"
    tl_lt_port: int = 8080
    tl_lt_binary: str = "./lobstertrap/lobstertrap"
    tl_lt_policy: str = "./configs/thoughtlens_policy.yaml"
    tl_log_level: str = "info"
    prism_provider: str = "https://api.groq.com/openai/v1"
    prism_key: str = "placeholder_key"
    prism_model: str = "llama-3.3-70b-versatile"

    class Config:
        env_file = ".env"


settings = Settings()
