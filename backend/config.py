import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

class Config:
    DATABASE_PATH = os.environ.get('JOURNAL_DB_PATH', str(BASE_DIR / 'data' / 'journals.db'))
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
