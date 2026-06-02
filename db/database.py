"""Engine SQLite e ciclo de vida da sessão."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.paths import DATA_DIR, DB_PATH
from db.models import Base

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _migrate_blog_profile_columns(engine: Engine) -> None:
    """Adiciona colunas de perfil pessoal em bases SQLite já existentes."""
    insp = inspect(engine)
    if not insp.has_table("blog_profile"):
        return
    existing = {col["name"] for col in insp.get_columns("blog_profile")}
    additions = {
        "name": "VARCHAR(200) NOT NULL DEFAULT ''",
        "email": "VARCHAR(320) NOT NULL DEFAULT ''",
        "phone": "VARCHAR(50) NOT NULL DEFAULT ''",
        "bio": "TEXT NOT NULL DEFAULT ''",
    }
    with engine.begin() as conn:
        for column, ddl in additions.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE blog_profile ADD COLUMN {column} {ddl}"))


def get_database_url() -> str:
    """Retorna URL SQLAlchemy para o SQLite local."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_PATH.as_posix()}"


def init_db() -> None:
    """Cria tabelas e prepara o session factory."""
    global _engine, _SessionLocal
    if _engine is not None:
        return
    _engine = create_engine(
        get_database_url(),
        echo=False,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(_engine)
    _migrate_blog_profile_columns(_engine)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    logger.info("Base de dados inicializada em %s", DB_PATH)


def get_session() -> Session:
    """Abre uma sessão ORM (inicializa o banco se necessário)."""
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    return _SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager com commit/rollback automático."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
