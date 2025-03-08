import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import requests
from PIL import Image as PILImage
from io import BytesIO
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.custom_style = ParagraphStyle(
            'CustomStyle',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=12,
            spaceAfter=20
        )

    def _get_unsplash_image(self, query):
        """Fetch relevant image from Unsplash"""
        try:
            url = f"https://api.unsplash.com/photos/random"
            headers = {"Authorization": f"Client-ID {os.getenv('UNSPLASH_ACCESS_KEY')}"}
            params = {"query": query, "orientation": "landscape"}
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            image_url = data["urls"]["regular"]
            
            # Download and process image
            img_response = requests.get(image_url)
            img = PILImage.open(BytesIO(img_response.content))
            img = img.convert('RGB')
            
            # Save temporarily
            temp_path = "/tmp/temp_image.jpg"
            img.save(temp_path)
            return temp_path
        except Exception as e:
            print(f"Error fetching Unsplash image: {e}")
            return None

    def create_pdf(self, summary_content, display_format, output_path="/tmp/summary.pdf"):
        """Create PDF with enhanced formatting based on display_format"""
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []

        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30
        )
        story.append(Paragraph("Document Summary", title_style))
        story.append(Spacer(1, 12))

        # Process content based on display format
        if display_format.get('type') == 'table':
            # Create table
            data = display_format.get('data', [])
            if data:
                table = Table(data)
                story.append(table)
                
        elif display_format.get('type') == 'bullet_points':
            # Create bullet points
            for point in display_format.get('points', []):
                story.append(Paragraph(f"• {point}", self.custom_style))
                
        elif display_format.get('type') == 'sections':
            # Create sections with headers
            for section in display_format.get('sections', []):
                story.append(Paragraph(section['title'], self.styles['Heading2']))
                story.append(Paragraph(section['content'], self.custom_style))
                
        else:
            # Default paragraph format
            story.append(Paragraph(summary_content, self.custom_style))

        # Add relevant image
        image_path = self._get_unsplash_image(display_format.get('image_query', 'education'))
        if image_path:
            img = Image(image_path)
            img.drawHeight = 4*inch
            img.drawWidth = 6*inch
            story.append(img)

        # Build PDF
        doc.build(story)
        
        # Upload to Cloudinary
        try:
            response = cloudinary.uploader.upload(
                output_path,
                resource_type="raw",
                folder="summaries",
                use_filename=True
            )
            return response['secure_url']
        except Exception as e:
            print(f"Error uploading to Cloudinary: {e}")
            return None