import os
import platform

# Python 3.14 on Windows can block inside platform.machine()'s WMI lookup
# during SQLAlchemy import. SQLAlchemy only needs the architecture label.
# This guard ensures Render (Linux) is unaffected.
if os.name == "nt":
    platform.machine = lambda: "AMD64"

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ── Database path ─────────────────────────────────────────────────────────────
# On Render: use the mounted persistent disk so data survives redeploys.
# Locally:   store astro.db next to this file (backend/).
_RENDER_DATA_DIR = "/opt/render/project/src/data"

if os.path.isdir(_RENDER_DATA_DIR):
    # Running on Render — use persistent disk
    _DB_PATH = os.path.join(_RENDER_DATA_DIR, "astro.db")
else:
    # Local development
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _DB_PATH = os.path.join(_HERE, "astro.db")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
