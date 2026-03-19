import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True, enable_decoding=False)

    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60 * 24, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"], alias="CORS_ORIGINS")
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "backend", "frontend"],
        alias="ALLOWED_HOSTS",
    )
    enable_security_headers: bool = Field(True, alias="ENABLE_SECURITY_HEADERS")
    sql_echo: bool = Field(False, alias="SQL_ECHO")
    db_pool_size: int = Field(10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(20, alias="DB_MAX_OVERFLOW")
    db_pool_timeout_seconds: int = Field(30, alias="DB_POOL_TIMEOUT_SECONDS")
    db_pool_recycle_seconds: int = Field(1800, alias="DB_POOL_RECYCLE_SECONDS")
    db_connect_timeout_seconds: int = Field(10, alias="DB_CONNECT_TIMEOUT_SECONDS")
    first_admin_login: str = Field("", alias="FIRST_ADMIN_LOGIN")
    first_admin_password: str = Field("", alias="FIRST_ADMIN_PASSWORD")
    first_admin_full_name: str = Field("First Administrator", alias="FIRST_ADMIN_FULL_NAME")
    artifacts_dir: str = Field("/tmp/pmm_artifacts", alias="ARTIFACTS_DIR")
    backup_dir: str = Field("/tmp/pmm_backups", alias="BACKUP_DIR")
    backup_retention_count: int = Field(10, alias="BACKUP_RETENTION_COUNT")
    posting_error_log_path: str = Field("/tmp/pmm_posting_errors.log", alias="POSTING_ERROR_LOG_PATH")
    frontend_base_url: str = Field("http://localhost:3000", alias="FRONTEND_BASE_URL")
    print_qr_target_url: str = Field("https://pmm.66br.pp.ua", alias="PRINT_QR_TARGET_URL")
    backend_version: str = Field("dev", alias="BACKEND_VERSION")
    frontend_version: str = Field("dev", alias="FRONTEND_VERSION")
    update_manifest_path: str = Field("/app/app/update_manifest.json", alias="UPDATE_MANIFEST_PATH")
    update_manifest_url: str = Field("", alias="UPDATE_MANIFEST_URL")
    update_manifest_sha256_pin: str = Field("", alias="UPDATE_MANIFEST_SHA256_PIN")
    allowed_image_repos: list[str] = Field(default_factory=list, alias="ALLOWED_IMAGE_REPOS")
    update_github_repo: str = Field("", alias="UPDATE_GITHUB_REPO")
    update_github_token: str = Field("", alias="UPDATE_GITHUB_TOKEN")
    require_signed_tags: bool = Field(False, alias="REQUIRE_SIGNED_TAGS")
    update_check_cache_ttl_seconds: int = Field(300, alias="UPDATE_CHECK_CACHE_TTL_SECONDS")
    update_releases_limit: int = Field(10, alias="UPDATE_RELEASES_LIMIT")
    update_releases_keep: int = Field(5, alias="UPDATE_RELEASES_KEEP")
    update_min_free_gb: int = Field(2, alias="UPDATE_MIN_FREE_GB")
    update_logs_dir: str = Field("/opt/pmm/logs", alias="UPDATE_LOGS_DIR")
    update_project_dir: str = Field("/opt/pmm", alias="UPDATE_PROJECT_DIR")
    update_compose_file: str = Field("/opt/pmm/current/docker-compose.prod.yml", alias="UPDATE_COMPOSE_FILE")
    update_env_file: str = Field("/opt/pmm/.env.prod", alias="UPDATE_ENV_FILE")
    update_version_env_key: str = Field("APP_VERSION", alias="UPDATE_VERSION_ENV_KEY")
    updater_poll_interval_seconds: int = Field(5, alias="UPDATER_POLL_INTERVAL_SECONDS")
    updater_mode: bool = Field(False, alias="UPDATER_MODE")
    enable_legacy_json_restore: bool = Field(False, alias="ENABLE_LEGACY_JSON_RESTORE")

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value.strip()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
        return value

    @field_validator("first_admin_password")
    @classmethod
    def validate_first_admin_password(cls, value: str) -> str:
        if value and len(value.strip()) < 8:
            raise ValueError("FIRST_ADMIN_PASSWORD must be at least 8 characters long")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_image_repos", mode="before")
    @classmethod
    def parse_allowed_image_repos(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def validate_postgresql_only(cls, value: str) -> str:
        try:
            url = make_url(value)
        except Exception as exc:
            raise ValueError(f"Invalid DATABASE_URL: {exc}") from exc
        backend = (url.drivername or "").split("+", 1)[0]
        if backend != "postgresql":
            raise ValueError(
                "This deployment is PostgreSQL-only. Set DATABASE_URL to postgresql+..."
            )
        return value

    @field_validator(
        "db_pool_size",
        "db_max_overflow",
        "db_pool_timeout_seconds",
        "db_pool_recycle_seconds",
        "db_connect_timeout_seconds",
    )
    @classmethod
    def validate_positive_pool_values(cls, value: int) -> int:
        if int(value) < 1:
            raise ValueError("Database pool settings must be >= 1")
        return int(value)

settings = Settings()
