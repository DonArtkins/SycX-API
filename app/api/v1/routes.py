from flask import request, current_app, jsonify
from flask_restful import Resource
from app.api.v1 import api
from app.utils.helpers import rate_limit
from datetime import datetime
from app.utils.file_processor import FileProcessor
from app.utils.pdf_generator import PDFGenerator
from werkzeug.utils import secure_filename
import os
import logging

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
        self.allowed_extensions = {
            'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt',
            'txt', 'md', 'png', 'jpg', 'jpeg'
        }

    def allowed_file(self, filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    @rate_limit
    def post(self):
        try:
            if 'file' not in request.files:
                return {'error': 'No file provided'}, 400
                
            file = request.files['file']
            if file.filename == '':
                return {'error': 'No file selected'}, 400
                
            if not self.allowed_file(file.filename):
                return {'error': f'File type not supported. Allowed types: {", ".join(sorted(self.allowed_extensions))}'}, 400

            summary_depth = float(request.form.get('summary_depth', 2.0))
            user_id = request.form.get('user_id', 'default_user')
            
            if not 0.0 <= summary_depth <= 4.0:
                return {'error': 'Summary depth must be between 0.0 and 4.0'}, 400

            try:
                file_content = file.read()
                file_type = file.filename.rsplit('.', 1)[1].lower()
                
                logging.info(f"Processing file: {file.filename}, type: {file_type}, size: {len(file_content)} bytes")
                
                result = self.file_processor.process_file(
                    file_content,
                    file_type,
                    summary_depth
                )

                if not result:
                    return {'error': 'Failed to process file with Gemini'}, 500

                pdf_url = self.pdf_generator.create_pdf(
                    summary_content=result['summary'],
                    display_format=result['display_format'],
                    title=result['title'] 
                )

                if not pdf_url:
                    return {'error': 'Failed to generate or upload PDF'}, 500

                response_data = {
                    'status': 'success',
                    'pdf_url': pdf_url.get('signed_url') if isinstance(pdf_url, dict) else pdf_url,
                    'title': result['title'],
                    'summary_length': len(result['summary'].split()),
                    'user_id': user_id
                }
                
                logging.info(f"Successfully processed file for user {user_id}: {result['title']}")
                return response_data, 200

            except Exception as e:
                logging.error(f"Error processing file: {str(e)}")
                return {'error': f'Error processing file: {str(e)}'}, 500

        except Exception as e:
            logging.error(f"Error in summarize endpoint: {str(e)}")
            return {'error': str(e)}, 500

class Feedback(Resource):
    @rate_limit
    def get(self):
        return {"message": "Testing Feedback endpoint"}, 200
    
    @rate_limit
    def post(self):
        data = request.get_json()
        return {"result": "Testing Feedback endpoint complete"}, 201

# Register routes
api.add_resource(HealthCheck, '/health')
api.add_resource(Summarize, '/summarize')
api.add_resource(Feedback, '/feedback')