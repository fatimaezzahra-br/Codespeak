
import os
import sys
import shutil
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

if getattr(sys, "frozen", False):
    # Dossier permanent pour les données de l'application
    DATA_DIR = os.path.join(
        os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
        "CodeSpeak"
    )

    # Dossier contenant les fichiers intégrés par PyInstaller
    RESOURCE_DIR = sys._MEIPASS

    os.makedirs(DATA_DIR, exist_ok=True)

    # Copier la base initiale uniquement si elle n'existe pas déjà
    bundled_db = os.path.join(RESOURCE_DIR, "codespeak.db")
    DATA_DB = os.path.join(DATA_DIR, "codespeak.db")

    if os.path.exists(bundled_db) and not os.path.exists(DATA_DB):
        shutil.copy2(bundled_db, DATA_DB)

    # Copier les anciens fichiers audio uniquement au premier lancement
    bundled_uploads = os.path.join(RESOURCE_DIR, "uploads")
    DATA_UPLOADS = os.path.join(DATA_DIR, "uploads")

    if os.path.isdir(bundled_uploads) and not os.path.exists(DATA_UPLOADS):
        shutil.copytree(bundled_uploads, DATA_UPLOADS)

else:
    # Mode développement : conserver les chemins du projet
    DATA_DIR = BASE_DIR
    DATA_DB = os.path.join(DATA_DIR, "codespeak.db")
    DATA_UPLOADS = os.path.join(DATA_DIR, "uploads")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + DATA_DB.replace("\\", "/")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = DATA_UPLOADS
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
