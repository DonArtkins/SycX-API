import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../../.env'))

class Config:
    """Application configuration class."""
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))
    API_TITLE = os.getenv('API_TITLE', 'SycX-API API')
    API_VERSION = os.getenv('API_VERSION', 'v1')
    RATE_LIMIT = int(os.getenv('RATE_LIMIT', 1000))
    RATE_LIMIT_PERIOD = timedelta(minutes=int(os.getenv('RATE_LIMIT_PERIOD', 15)))
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    TESTING = False
    MODEL_PATH = os.getenv('MODEL_PATH', 'app/models/trained_models')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
