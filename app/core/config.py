import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Info
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Cybersecurity Advisor API")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    
    # Google Cloud / Firebase
    # These MUST be provided by Cloud Run or .env
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    
    # Security Toggle (False for local dev, True for Prod)
    # Cloud Run env vars are always strings, so we parse "True"/"False" carefully
    APP_CHECK_ENFORCED: bool = os.getenv("APP_CHECK_ENFORCED", "True").lower() == "true"
    
    # Vertex AI / DeepSeek Configuration
    VERTEX_PROJECT_ID: str = os.getenv("VERTEX_PROJECT_ID", "")
    VERTEX_LOCATION: str = os.getenv("VERTEX_LOCATION", "us-central1")
    VERTEX_MODEL_NAME: str = os.getenv("VERTEX_MODEL_NAME", "deepseek-ai/deepseek-v3.2-maas")
    
    class Config:
        case_sensitive = True
        # Pydantic will still look for .env if variables aren't found in OS
        env_file = ".env" 

settings = Settings()
