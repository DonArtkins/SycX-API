from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from app.config.config import Config

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    CORS(app)
    api = Api(app)

    # Register blueprints/resources
    from app.api.v1 import bp as api_v1
    app.register_blueprint(api_v1, url_prefix='/api/v1')

    @app.route('/')
    def index():
        """Root endpoint with API information."""
        return {
            'api_name': app.config['API_TITLE'],
            'version': app.config['API_VERSION'],
            'status': 'operational',
            'docs_url': '/api/v1/docs'
        }

    return app
