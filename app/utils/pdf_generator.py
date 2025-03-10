import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, ListFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import requests
from PIL import Image as PILImage
from io import BytesIO
import cloudinary
import cloudinary.uploader
from flask import current_app
import logging
import uuid
import datetime
import time
import hashlib

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfdoc

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()

        # Register custom font
        font_path = os.path.join(os.path.dirname(current_app.root_path), 'assets/fonts/Coming_Soon/ComingSoon-Regular.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ComingSoon', font_path))
            self.font_name = 'ComingSoon'
        else:
            logging.warning("Custom font not found, using Helvetica")
            self.font_name = 'Helvetica'

        # Configure styles
        self.custom_style = ParagraphStyle(
            'CustomStyle',
            parent=self.styles['Normal'],
            fontName=self.font_name,
            fontSize=12,
            spaceAfter=16,  # Reduced spacing after
            leading=16,
            textColor=colors.HexColor('#263238')  # Darker grey
        )

        # Configure Cloudinary
        cloudinary.config(
            cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
            api_key=current_app.config['CLOUDINARY_API_KEY'],
            api_secret=current_app.config['CLOUDINARY_API_SECRET']
        )

    def _get_unsplash_image(self, query):
        """Fetch relevant image from Unsplash with error handling"""
        try:
            headers = {
                "Authorization": f"Client-ID {current_app.config['UNSPLASH_ACCESS_KEY']}"
            }
            params = {
                "query": query,
                "orientation": "landscape"
            }

            response = requests.get(
                "https://api.unsplash.com/photos/random",
                headers=headers,
                params=params,
                timeout=5
            )

            if response.status_code == 200:
                image_url = response.json()["urls"]["regular"]
                img_response = requests.get(image_url, timeout=5)
                if img_response.status_code == 200:
                    img = PILImage.open(BytesIO(img_response.content))
                    img = img.convert('RGB')
                    temp_path = "/tmp/temp_image.jpg"
                    img.save(temp_path)
                    return temp_path

            return None

        except Exception as e:
            logging.error(f"Error fetching Unsplash image: {e}")
            return None

    def create_pdf(self, summary_content, display_format, title):
        """Create PDF with enhanced formatting and metadata"""
        try:
            # Generate a unique filename to prevent collisions
            unique_id = str(uuid.uuid4())[:8]
            safe_title = title.replace(' ', '_').replace('/', '_').replace('\\', '_')
            output_path = f"/tmp/{safe_title}_{unique_id}.pdf"

            # Creation date for metadata
            creation_date = datetime.datetime.now()

            doc = SimpleDocTemplate(output_path, pagesize=letter,
                                  author="SycX AI",  # Setting Author
                                  title=title,        # Setting Title
                                  subject="AI Generated Summary",  # Setting Subject
                                  keywords=["AI", "Summary", "Document"], # Setting keywords
                                  creationdate=creation_date) # Setting creation date

            story = []

            # Title style
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=self.styles['Title'],
                fontName=self.font_name,
                fontSize=24,
                spaceAfter=8,  # Reduced spacing
                textColor=colors.HexColor(display_format['style']['colors'].get('primary', '#000000')),  # Primary Color
                alignment=1  # Center align
            )

            # Author style
            author_style = ParagraphStyle(
                'AuthorStyle',
                parent=self.styles['Normal'],
                fontName=self.font_name,
                fontSize=10,
                alignment=2,  # Align right
                spaceAfter=16,  # Reduced spacing
                textColor=colors.grey
            )

            # Add title
            story.append(Paragraph(title, title_style))

            # Add author
            story.append(Paragraph("SycX AI", author_style))  # Adding the author

            story.append(Spacer(1, 12))

            # Add image at the top if available
            image_path = self._get_unsplash_image(display_format.get('image_query', 'document'))
            if image_path:
                img = Image(image_path)
                img.drawHeight = 4 * inch
                img.drawWidth = 6 * inch
                story.append(img)
                story.append(Spacer(1, 12))

            # Format content based on display type
            if display_format['type'] == 'sections':
                for section in display_format['sections']:
                    # Section header
                    header_style = ParagraphStyle(
                        'SectionHeader',
                        parent=self.styles['Heading2'],
                        fontName=self.font_name,
                        fontSize=16,
                        spaceAfter=4,  # Reduced spacing
                        textColor=colors.HexColor(display_format['style']['colors'].get('headers', '#000000')),  # Headers Color
                        leading=18  # Increased leading
                    )
                    story.append(Paragraph(section['title'], header_style))
                    story.append(Spacer(1, 2))

                    # Section content
                    # Split the content into lines and format each as a paragraph
                    lines = section['content'].split('\n')
                    for line in lines:
                        story.append(Paragraph(line.strip(), self.custom_style))
                    story.append(Spacer(1, 10))  # Reduced spacing

            else:  # Default paragraph format
                story.append(Paragraph(summary_content, self.custom_style))

            # Metadata is passed directly during doc creation.
            doc.build(story)

            # Upload to Cloudinary with error handling and retry
            try:
                # First attempt
                response = self._upload_to_cloudinary(output_path, safe_title, unique_id)
                if response:
                    # Return the signed URL instead of secure_url
                    return response['signed_url']

                # Retry with different parameters if first attempt failed
                logging.warning("First Cloudinary upload attempt failed. Retrying with modified parameters...")
                response = self._upload_to_cloudinary(output_path, f"summary_{unique_id}", unique_id, retry=True)
                if response:
                    # Return the signed URL instead of secure_url
                    return response['signed_url']

                return None
            except Exception as e:
                logging.error(f"Cloudinary upload error: {e}")
                return None

        except Exception as e:
            logging.error(f"PDF generation error: {e}")
            return None

    def _upload_to_cloudinary(self, file_path, title, unique_id, retry=False):
        try:
            # Generate Cloudinary signature
            timestamp = str(int(time.time()))
            public_id = f"SycX Files/{title}_{unique_id}"
            
            # Create signature payload
            signature_str = f"public_id={public_id}×tamp={timestamp}{current_app.config['CLOUDINARY_API_SECRET']}"
            signature = hashlib.sha1(signature_str.encode('utf-8')).hexdigest()

            options = {
                "folder": "SycX Files",
                "public_id": public_id,
                "resource_type": "auto",
                "overwrite": True,
                "type": "upload",
                "access_mode": "authenticated",  # Private access
                "context": {"author": "SycX AI"},
                "timestamp": timestamp,
                "signature": signature,
                "api_key": current_app.config['CLOUDINARY_API_KEY']
            }

            response = cloudinary.uploader.upload(file_path, **options)
            
            if 'secure_url' not in response:
                logging.error(f"Cloudinary response: {response}")
                return None

            # Generate signed URL
            signed_url = self._generate_signed_url(response['public_id'], response['resource_type'])
            response['signed_url'] = signed_url
            
            return response

        except Exception as e:
            logging.error(f"Cloudinary upload error: {str(e)}")
            return None

    def _generate_signed_url(self, public_id, resource_type):
        try:
            # Generate signature
            timestamp = str(int(time.time()))
            signature_str = f"public_id={public_id}×tamp={timestamp}{current_app.config['CLOUDINARY_API_SECRET']}"
            signature = hashlib.sha1(signature_str.encode('utf-8')).hexdigest()

            return cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type,
                secure=True,
                sign_url=True,
                api_key=current_app.config['CLOUDINARY_API_KEY'],
                signature=signature,
                timestamp=timestamp
            )[0]

        except Exception as e:
            logging.error(f"Error generating signed URL: {str(e)}")
            return None