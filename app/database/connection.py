"""
Connexion Supabase + SQLAlchemy
"""
import os
from pathlib import Path
from supabase import create_client, Client
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

# ─── SUPABASE CLIENT ─────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ─── SQLALCHEMY ASYNC ─────────────────────────────────────────
# IMPORTANT : utiliser le Session Pooler Supabase (IPv4, port 5432) dans DATABASE_URL.
# Le host direct db.[ref].supabase.co est IPv6-only → échec sur macOS sans IPv6.
# Format attendu : postgresql://postgres.[ref]:[pwd]@aws-0-[region].pooler.supabase.com:5432/postgres
_raw_url = os.getenv("DATABASE_URL", "")
DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://").replace("postgres://", "postgresql+asyncpg://")
# Validation de DATABASE_URL
if not DATABASE_URL or DATABASE_URL == "postgresql+asyncpg://":
    print("[WARNING] DATABASE_URL est vide ou invalide. Vérifiez votre fichier .env")
    print(f"[WARNING] Valeur actuelle : '{_raw_url}'")
    # Utiliser une URL factice pour éviter le crash du engine
    DATABASE_URL = "postgresql+asyncpg://localhost/placeholder"
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    # SSL requis par Supabase ; statement_cache_size=0 requis pour le pooler
    connect_args={"ssl": True, "statement_cache_size": 0},
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency injection pour les routes FastAPI"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialisation de la base de données"""
    try:
        # Test de connectivité via le client Supabase REST — c'est l'interface
        # réellement utilisée par toutes les routes (supabase.table(...).execute()).
        # La connexion directe PostgreSQL (asyncpg) est IPv6-only sur Supabase
        # et n'est jamais appelée par les routes en production.
        supabase.table("formations").select("id", count="exact").limit(0).execute()
        print("[init_db] Connexion Supabase OK")
    except Exception as exc:
        print("[init_db] ERREUR: Impossible de joindre Supabase")
        print("[init_db] Vérifiez SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY dans .env")
        print(f"[init_db] Détail : {exc}")


def get_supabase() -> Client:
    """Retourne le client Supabase"""
    return supabase


