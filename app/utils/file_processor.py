import os
from transformers import pipeline
import torch
from PIL import Image
import pytesseract
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
import json
import io

class FileProcessor:
    def __init__(self):
        # Initialize the summarization model
        self.summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            device=0 if torch.cuda.is_available() else -1
        )

    def _optimize_length_params(self, text_length, summary_depth):
        """Calculate optimal length parameters based on summary depth"""
        depth_configs = {
            0.0: {'max_ratio': 0.05, 'min_ratio': 0.02},  # Minimal
            1.0: {'max_ratio': 0.15, 'min_ratio': 0.05},  # Short
            2.0: {'max_ratio': 0.30, 'min_ratio': 0.10},  # Medium
            3.0: {'max_ratio': 0.40, 'min_ratio': 0.20},  # Standard
            4.0: {'max_ratio': 0.60, 'min_ratio': 0.30}   # Comprehensive
        }
        
        # Get closest depth configuration
        depths = list(depth_configs.keys())
        closest_depth = min(depths, key=lambda x: abs(x - float(summary_depth)))
        config = depth_configs[closest_depth]
        
        max_length = int(text_length * config['max_ratio'])
        min_length = int(text_length * config['min_ratio'])
        
        return max_length, min_length

    def process_file(self, file_content, file_type, summary_depth):
        """Process file and return summary with display format suggestion"""
        try:
            # Extract text based on file type
            if file_type in ['pdf']:
                text = extract_pdf_text(io.BytesIO(file_content))
            elif file_type in ['docx', 'doc']:
                doc = Document(io.BytesIO(file_content))
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            elif file_type in ['xlsx', 'xls']:
                wb = load_workbook(io.BytesIO(file_content))
                text = ""
                for sheet in wb.active:
                    for row in sheet.iter_rows(values_only=True):
                        text += " ".join([str(cell) for cell in row if cell]) + "\n"
            elif file_type in ['pptx', 'ppt']:
                prs = Presentation(io.BytesIO(file_content))
                text = ""
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text += shape.text + "\n"
            elif file_type in ['png', 'jpg', 'jpeg']:
                image = Image.open(io.BytesIO(file_content))
                text = pytesseract.image_to_string(image)
            else:  # txt, md
                text = file_content.decode('utf-8')

            # Calculate optimal length parameters
            max_length, min_length = self._optimize_length_params(len(text.split()), summary_depth)

            # Generate summary
            summary = self.summarizer(
                text,
                max_length=max_length,
                min_length=min_length,
                do_sample=False
            )[0]['summary_text']

            # Analyze content to suggest display format
            display_format = self._suggest_display_format(summary)

            return {
                'summary': summary,
                'display_format': display_format
            }

        except Exception as e:
            raise Exception(f"Error processing file: {str(e)}")

    def _suggest_display_format(self, text):
        """Analyze text and suggest appropriate display format"""
        # Simple heuristic-based format suggestion
        words = text.split()
        sentences = text.split('.')
        
        if len(sentences) > 10 and any(['first' in text.lower(), 'second' in text.lower(), 'finally' in text.lower()]):
            # Content seems to have clear sections
            sections = self._extract_sections(text)
            return {
                'type': 'sections',
                'sections': sections,
                'image_query': 'education presentation'
            }
        elif len(sentences) < 5 or (len(words) / len(sentences)) < 10:
            # Short, concise points
            return {
                'type': 'bullet_points',
                'points': [s.strip() for s in sentences if s.strip()],
                'image_query': 'education notes'
            }
        else:
            # Default to paragraph format
            return {
                'type': 'paragraph',
                'image_query': 'education learning'
            }

    def _extract_sections(self, text):
        """Extract sections from text"""
        # Simple section extraction logic
        sentences = text.split('.')
        sections = []
        current_section = {'title': 'Overview', 'content': ''}
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in ['first', 'second', 'finally', 'moreover', 'furthermore']):
                if current_section['content']:
                    sections.append(current_section)
                current_section = {
                    'title': sentence.strip(),
                    'content': ''
                }
            else:
                current_section['content'] += sentence + '.'
                
        if current_section['content']:
            sections.append(current_section)
            
        return sections