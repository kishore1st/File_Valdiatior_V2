from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PG_DSN: str = "postgresql://fvi:fvi@db:5432/fvi"
    OKTA_ISSUER: str = ""
    OKTA_AUDIENCE: str = ""
    OKTA_JWKS_URL: str = ""
    DATABRICKS_HOST: str = ""
    DATABRICKS_TOKEN: str = ""
    WORKER_CONCURRENCY: int = 4
    WATCHER_ENABLED: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()