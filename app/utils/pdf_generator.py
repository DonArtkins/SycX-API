import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
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
            spaceAfter=20,
            leading=16
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
        """Create PDF with enhanced formatting"""
        try:
            output_path = f"/tmp/{title.replace(' ', '_')}.pdf"
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            story = []

            # Title style
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=self.styles['Title'],
                fontName=self.font_name,
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor(display_format['style']['colors'].get('primary', '#000000'))
            )
            
            # Add title
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 12))

            # Add image at the top if available
            image_path = self._get_unsplash_image(display_format.get('image_query', 'document'))
            if image_path:
                img = Image(image_path)
                img.drawHeight = 4*inch
                img.drawWidth = 6*inch
                story.append(img)
                story.append(Spacer(1, 12))

            # Format content based on display type
            if display_format['type'] == 'bullet_points':
                for point in display_format['points']:
                    bullet_style = ParagraphStyle(
                        'BulletStyle',
                        parent=self.custom_style,
                        leftIndent=20,
                        spaceBefore=10
                    )
                    story.append(Paragraph(f"• {point}", bullet_style))
                    
            elif display_format['type'] == 'sections':
                for section in display_format['sections']:
                    # Section header
                    header_style = ParagraphStyle(
                        'SectionHeader',
                        parent=self.styles['Heading2'],
                        fontName=self.font_name,
                        fontSize=16,
                        textColor=colors.HexColor(display_format['style']['colors'].get('headers', '#000000'))
                    )
                    story.append(Paragraph(section['title'], header_style))
                    story.append(Spacer(1, 8))
                    
                    # Section content
                    story.append(Paragraph(section['content'], self.custom_style))
                    story.append(Spacer(1, 12))
                    
            else:  # Default paragraph format
                story.append(Paragraph(summary_content, self.custom_style))

            # Build PDF
            doc.build(story)

            # Upload to Cloudinary
            try:
                response = cloudinary.uploader.upload(
                    output_path,
                    folder="SycX Files",
                    public_id=title.replace(' ', '_'),
                    resource_type="raw",
                    overwrite=True
                )
                return response['secure_url']
            except Exception as e:
                logging.error(f"Cloudinary upload error: {e}")
                return None

        except Exception as e:
            logging.error(f"PDF generation error: {e}")
            return None