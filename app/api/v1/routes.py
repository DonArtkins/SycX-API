from flask import request, current_app, jsonify
from flask_restful import Resource
from app.api.v1 import api
from app.utils.helpers import rate_limit
from datetime import datetime
from app.utils.file_processor import FileProcessor
from app.utils.pdf_generator import PDFGenerator
from werkzeug.utils import secure_filename
import os

class HealthCheck(Resource):
    @rate_limit
    def get(self):
        """Health check endpoint."""
        environment = current_app.config['FLASK_ENV']
        return {
            'status': 'healthy',
            'version': current_app.config['API_VERSION'],
            'timestamp': datetime.utcnow().isoformat(),
            'environment': environment
        }, 200

class Summarize(Resource):
    def __init__(self):
        self.file_processor = FileProcessor()
        self.pdf_generator = PDFGenerator()
        self.allowed_extensions = {'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt', 'txt', 'md', 'png', 'jpg', 'jpeg'}

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    @rate_limit
    def post(self):
        try:
            if 'file' not in request.files:
                return {'error': 'No file provided'}, 400
                
            file = request.files['file']
            if file.filename == '':
                return {'error': 'No file selected'}, 400
                
            if not self.allowed_file(file.filename):
                return {'error': 'File type not supported'}, 400

            summary_depth = float(request.form.get('summary_depth', 2.0))
            if not 0.0 <= summary_depth <= 4.0:
                return {'error': 'Summary depth must be between 0.0 and 4.0'}, 400

            # Process file
            file_content = file.read()
            file_type = file.filename.rsplit('.', 1)[1].lower()
            
            # Get summary and display format
            result = self.file_processor.process_file(
                file_content,
                file_type,
                summary_depth
            )

            # Generate PDF and upload to Cloudinary
            pdf_url = self.pdf_generator.create_pdf(
                result['summary'],
                result['display_format']
            )

            if not pdf_url:
                return {'error': 'Failed to generate or upload PDF'}, 500

            return {
                'status': 'success',
                'pdf_url': pdf_url,
                'summary_length': len(result['summary'].split())
            }, 200

        except Exception as e:
            return {'error': str(e)}, 500

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
