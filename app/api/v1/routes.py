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

class Summarize(Resource):
    @rate_limit
    def get(self):
        return {"message": "Testing Summarize endpoint"}, 200
    
    @rate_limit
    def post(self):
        data = request.get_json()
        # Process your data here
        return {"result": "Testing Summarize endpoint complete"}, 201

class Feedback(Resource):
    @rate_limit
    def get(self):
        return {"message": "Testing Feedback endpoint"}, 200
    
    @rate_limit
    def post(self):
        data = request.get_json()
        # Process your data here
        return {"result": "Testing Feedback endpoint complete"}, 201

# Register routes
api.add_resource(HealthCheck, '/health')
api.add_resource(Summarize, '/summarize')
api.add_resource(Feedback, '/feedback')
