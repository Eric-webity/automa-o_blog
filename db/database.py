"""Engine SQLite e ciclo de vida da sessão."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.paths import DATA_DIR, DB_PATH
import os

from db.models import Base, UserRole

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


def _migrate_articles_user_id(engine: Engine) -> None:
    """Adiciona ``user_id`` e associa matérias antigas ao primeiro utilizador."""
    insp = inspect(engine)
    if not insp.has_table("articles"):
        return
    existing = {col["name"] for col in insp.get_columns("articles")}
    with engine.begin() as conn:
        if "user_id" not in existing:
            conn.execute(
                text("ALTER TABLE articles ADD COLUMN user_id INTEGER REFERENCES users(id)")
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_articles_user_id ON articles (user_id)"))
        if not insp.has_table("users"):
            return
        owner_id = conn.execute(
            text("SELECT id FROM users ORDER BY id ASC LIMIT 1")
        ).scalar()
        if owner_id is not None:
            conn.execute(
                text("UPDATE articles SET user_id = :uid WHERE user_id IS NULL"),
                {"uid": owner_id},
            )


def _migrate_users_role(engine: Engine) -> None:
    """Adiciona coluna ``role`` e garante pelo menos um administrador."""
    insp = inspect(engine)
    if not insp.has_table("users"):
        return
    existing = {col["name"] for col in insp.get_columns("users")}
    with engine.begin() as conn:
        if "role" not in existing:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN role VARCHAR(16) "
                    f"NOT NULL DEFAULT '{UserRole.USER.value}'"
                )
            )
        conn.execute(
            text(
                "UPDATE users SET role = :admin WHERE id = ("
                "SELECT id FROM users ORDER BY id ASC LIMIT 1"
                ") AND NOT EXISTS (SELECT 1 FROM users WHERE role = :admin)"
            ),
            {"admin": UserRole.ADMIN.value},
        )
        admin_email = (
            os.getenv("GEO_ADMIN_EMAIL", "").strip().lower()
            or os.getenv("GEO_LOGIN_EMAIL", "").strip().lower()
        )
        if admin_email:
            conn.execute(
                text("UPDATE users SET role = :admin WHERE lower(email) = :email"),
                {"admin": UserRole.ADMIN.value, "email": admin_email},
            )


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
    _migrate_users_role(_engine)
    _migrate_articles_user_id(_engine)
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
