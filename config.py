import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application Configuration Settings."""

    SECRET_KEY = os.getenv("SECRET_KEY", "default-production-key-change-me")
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"

    # Base Paths
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    QR_CODES_DIR = DATA_DIR / "qr_codes"
    EXPORTS_DIR = DATA_DIR / "exports"
    LOGS_DIR = BASE_DIR / "logs"

    # Database Configuration
    DB_TYPE = os.getenv("DB_TYPE", "mysql").lower()  # 'mysql' or 'sqlite'
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME", "attendance_system")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    SQLITE_PATH = DATA_DIR / "attendance.db"

    # Camera Settings
    CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))
    CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", 1280))
    CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", 720))
    CAMERA_FPS = int(os.getenv("CAMERA_FPS", 30))

    # Scanner / Business Rules
    QR_SCAN_COOLDOWN_SECONDS = int(os.getenv("QR_SCAN_COOLDOWN_SECONDS", 8))
    ALLOW_EXIT_SCAN = os.getenv("ALLOW_EXIT_SCAN", "true").lower() in ("true", "1", "yes")
    EXCEL_AUTO_SYNC = os.getenv("EXCEL_AUTO_SYNC", "true").lower() in ("true", "1", "yes")
    EXCEL_MASTER_FILE = DATA_DIR / "Master_Attendance_Record.xlsx"

    @classmethod
    def init_app(cls):
        """Ensure all required directories exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.QR_CODES_DIR.mkdir(parents=True, exist_ok=True)
        cls.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
