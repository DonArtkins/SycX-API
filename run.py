import os
from dotenv import load_dotenv
from app import create_app
from app.config.config import config

# Load environment variables before creating the app
load_dotenv()

# Get environment from FLASK_ENV, default to 'development'
env = os.getenv('FLASK_ENV', 'development')

# Create the Flask application
app = create_app(config[env])

if __name__ == '__main__':
    # Configuration is now loaded from app.config instead of direct env vars
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )