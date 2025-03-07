from flask import request, current_app, jsonify
from flask_restful import Resource
from app.api.v1 import api
from app.utils.helpers import rate_limit
from datetime import datetime

class HealthCheck(Resource):
    @rate_limit
    def get(self):
        """Health check endpoint."""
        # Use FLASK_ENV from config instead of ENV
        environment = current_app.config.get('FLASK_ENV', 'production')
        return {
            'status': 'healthy',
            'version': current_app.config['API_VERSION'],
            'timestamp': datetime.utcnow().isoformat(),
            'environment': environment
        }, 200

class HelloWorld(Resource):
    @rate_limit
    def get(self):
        """Example endpoint."""
        return {
            'message': 'Hello, World!',
            'timestamp': datetime.utcnow().isoformat()
        }, 200

    @rate_limit
    def post(self):
        """Example POST endpoint."""
        data = request.get_json()
        return {
            'message': f"Received: {data}",
            'timestamp': datetime.utcnow().isoformat()
        }, 201

# Register routes
api.add_resource(HealthCheck, '/health')
api.add_resource(HelloWorld, '/hello')
