from app import create_app
from app.config.config import config, Config

# Get environment from Config class, which already handles the env variable
env = Config.FLASK_ENV

# Create app with appropriate config
app = create_app(config[env])

if __name__ == '__main__':
    if env == 'production':
        print("Warning: Running production server directly is not recommended.")
        print("Consider using a production WSGI server instead.")
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )