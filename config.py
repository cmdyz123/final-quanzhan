import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nutrisnap-secret-key-dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "nutrisnap.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    # AI Configuration
    AI_MODE = os.environ.get('AI_MODE', 'simulation')  # 'simulation' or 'api'

    # LLM API Configuration (for 'api' mode)
    LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
    LLM_API_BASE = os.environ.get('LLM_API_BASE', 'https://api.openai.com/v1')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-4o')
    VISION_MODEL = os.environ.get('VISION_MODEL', 'gpt-4o')

    # Nutrition targets (defaults, user can override)
    DEFAULT_DAILY_CALORIES = 2000
    DEFAULT_DAILY_PROTEIN = 60   # g
    DEFAULT_DAILY_FAT = 65       # g
    DEFAULT_DAILY_CARBS = 300    # g
