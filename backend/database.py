"""
Conexión a SQL Server (base de datos 'licamvel') con SQLAlchemy + pyodbc.
Soporta servidor local (localhost) e instancias nombradas (localhost\\SQLEXPRESS).
"""
import urllib.parse

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


class Settings(BaseSettings):
    """Configuración leída desde variables de entorno o archivo .env."""

    # Para SQL Express use: localhost\SQLEXPRESS
    DB_SERVER: str = r"localhost\SQLEXPRESS"
    DB_NAME: str = "licamvel"
    DB_DRIVER: str = "ODBC Driver 18 for SQL Server"

    # Si DB_USER está vacío se usa autenticación de Windows (Trusted_Connection)
    DB_USER: str = ""
    DB_PASSWORD: str = ""

    # Parámetros JWT
    SECRET_KEY: str = "cambia-esta-clave-en-produccion-usa-un-valor-largo-y-aleatorio"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Orígenes permitidos para CORS (separados por coma)
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


def build_connection_string() -> str:
    """Construye la cadena ODBC y la devuelve lista para SQLAlchemy."""
    parts = [
        f"DRIVER={{{settings.DB_DRIVER}}}",
        f"SERVER={settings.DB_SERVER}",
        f"DATABASE={settings.DB_NAME}",
        "TrustServerCertificate=yes",  # Necesario con ODBC Driver 18 en servidores locales
        "Encrypt=yes",
    ]

    if settings.DB_USER:
        parts.append(f"UID={settings.DB_USER}")
        parts.append(f"PWD={settings.DB_PASSWORD}")
    else:
        parts.append("Trusted_Connection=yes")

    odbc_str = ";".join(parts) + ";"
    return "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc_str)


engine = create_engine(
    build_connection_string(),
    pool_pre_ping=True,   # Verifica conexiones antes de usarlas
    pool_recycle=1800,    # Recicla conexiones cada 30 min
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: entrega una sesión y garantiza su cierre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()