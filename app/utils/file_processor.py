import os
import base64
import logging
import nltk
import google.generativeai as genai
from flask import current_app
from PIL import Image
import re
import datetime

nltk.download('punkt', quiet=True)

class FileProcessor:
    def __init__(self):
        google_key = "AIzaSyA_sWMVNE-SuiXxF97lsrsqyR42cqkVd1w"

        try:
            genai.configure(api_key=google_key)
            logging.info("Google Gemini API configured successfully")
        except Exception as e:
            logging.error(f"Error configuring Gemini: {str(e)}")
            raise

    def _optimize_length_params(self, text_length, summary_depth):
        depth_configs = {
            0.0: {'max_ratio': 0.05, 'min_ratio': 0.02, 'title_length': 2},
            1.0: {'max_ratio': 0.15, 'min_ratio': 0.05, 'title_length': 3},
            2.0: {'max_ratio': 0.30, 'min_ratio': 0.10, 'title_length': 4},
            3.0: {'max_ratio': 0.40, 'min_ratio': 0.20, 'title_length': 5},
            4.0: {'max_ratio': 0.60, 'min_ratio': 0.30, 'title_length': 6}
        }
        depths = list(depth_configs.keys())
        closest_depth = min(depths, key=lambda x: abs(x - float(summary_depth)))
        return depth_configs[closest_depth]

    def process_file(self, file_content, file_type, summary_depth=2.0):
        try:
            config = self._optimize_length_params(1000, summary_depth)

            logging.info("Starting summarization with Gemini Flash 2.0")
            summary = self._gemini_summarization(file_content, file_type, summary_depth)

            if not summary:
                return None

            suggested_title = self._generate_title(summary)
            display_format = self._force_sections(summary)

            return {
                'summary': summary,
                'title': suggested_title,
                'display_format': display_format
            }

        except Exception as e:
            logging.error(f"File processing error: {str(e)}")
            raise

    def _gemini_summarization(self, file_content, file_type, summary_depth):
        """
        Summarizes the given file content using the Gemini 2.0 Flash model.

        Args:
            file_content (bytes): The content of the file to be summarized.
            file_type (str): The type of the file (e.g., 'pdf', 'txt').
            summary_depth (float): A value indicating the desired depth/detail of the summary.

        Returns:
            str: The summarized text.

        Raises:
            Exception: If there is an error during the Gemini API call.
        """
        try:
            base64_content = base64.b64encode(file_content).decode('utf-8')
            mime_mapping = {
                'pdf': 'application/pdf',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'doc': 'application/msword',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'xls': 'application/vnd.ms-excel',
                'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'ppt': 'application/vnd.ms-powerpoint',
                'txt': 'text/plain',
                'md': 'text/markdown',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'dart': 'text/plain',  # ADDED dart
                'csv': 'text/csv', # CSV
                'json': 'application/json', # JSON
                'html': 'text/html', #HTML
                'xml': 'application/xml', #XML
                'svg':'image/svg+xml',#SVG
                'gif': 'image/gif', # GIF
                'tiff': 'image/tiff', #TIFF
                'mp3': 'audio/mpeg',
                'wav': 'audio/wav',
                'mp4': 'video/mp4',
                'avi': 'video/x-msvideo',
                'mov': 'video/quicktime',
                'webm': 'video/webm',
                'zip': 'application/zip',
                'rar':'application/x-rar-compressed',
                '7z': 'application/x-7z-compressed'
            }

            mime_type = mime_mapping.get(file_type, 'application/octet-stream')
            model = genai.GenerativeModel('gemini-2.0-flash')

            depth_prompts = {
                0.0: "Generate an extremely concise summary in 1-2 sentences.",
                1.0: "Create a brief summary with key points only.",
                2.0: "Produce a balanced summary covering main points.",
                3.0: "Develop a detailed summary of important content.",
                4.0: "Create comprehensive summary covering nearly all content."
            }

            closest_depth = min([0.0, 1.0, 2.0, 3.0, 4.0], key=lambda x: abs(x - summary_depth))
            # Updated Prompt: Request structured output for the invoice information
            prompt = f"{depth_prompts[closest_depth]} Analyze this {file_type.upper()} file. Extract the content into well-defined sections, using clear titles and coherent paragraphs. Completely REMOVE any unnecessary markdown characters, bullet points, numbers or any other formatting symbols. Create well formated contents and subheadings."


            if file_type in ['txt', 'md', 'dart']:  # ADDED dart
                try:
                    text_content = file_content.decode('utf-8')
                    response = model.generate_content([prompt, text_content])
                except UnicodeDecodeError:
                    response = model.generate_content([prompt, {'mime_type': mime_type, 'data': base64_content}])
            else:
                response = model.generate_content([prompt, {'mime_type': mime_type, 'data': base64_content}])

            return response.text

        except Exception as e:
            logging.error(f"Gemini API error: {str(e)}")
            raise

    def _generate_title(self, text):
        """
        Generates a meaningful title using AI for the given text content.

        Args:
            text (str): The text content to generate a title for.

        Returns:
            str: A cleaned and shortened title for the content.

        Raises:
            Exception: If the title generation fails.
        """
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(
                f"Suggest a short, descriptive, and well-formatted title for the following document: {text[:2000]}. The title must not exceed 60 characters. Respond with just the title, removing any quotation marks or surrounding phrases. Format the title in title case; this is VERY IMPORTANT"
            )
            title = response.text.strip().replace('"', '')

            # Sanitize and shorten title
            clean_title = re.sub(r'[^a-zA-Z0-9 \-\_]', '', title)[:60]
            return clean_title

        except Exception as e:
            logging.error(f"Title generation failed: {str(e)}")
            return "Academic_Content_Summary"

    def _force_sections(self, text):
        """Forces the display format to be sections."""
        sections = self._extract_sections(text)
        return {
            'type': 'sections',
            'sections': sections,
            'style': {
                'font': 'Arial',  # More professional font
                'colors': {
                    'primary': '#0D47A1',  # Dark blue
                    'headers': '#1565C0',  # Strong blue
                    'accent': '#E64A19',  # Orange-red accent
                    'background': '#E3F2FD'  # Light blue background
                },
                'code_font': 'Courier',
                'icon_set': 'fontawesome'
            },
            # Modified image query to include title and summary for better results
            'image_query': f"{self._generate_title(text)} {text[:500]}"
        }

    def _extract_sections(self, text):
        """Extract sections from the given text."""
        sentences = nltk.sent_tokenize(text)
        sections = []
        current_section = {'title': 'Introduction', 'content': []}  # default section for the document

        # Use AI to generate dynamic section markers
        dynamic_markers = self._generate_section_markers(text)
        markers = ['introduction', 'overview', 'summary', 'background', 'conclusion', 'first', 'second', 'third', 'finally', 'next', 'moreover', 'furthermore'] + dynamic_markers

        for sentence in sentences:
            lower_sentence = sentence.lower()
            is_new_section = any(marker in lower_sentence for marker in markers)

            if is_new_section:
                if current_section['content']:
                    sections.append({
                        'title': current_section['title'],
                        'content': ' '.join(current_section['content'])
                    })
                current_section = {
                    'title': sentence.strip(),
                    'content': []
                }
            else:
                current_section['content'].append(sentence)

        if current_section['content']:
            sections.append({
                'title': current_section['title'],
                'content': ' '.join(current_section['content'])
            })

        return sections

    def _generate_section_markers(self, text):
        """
        Generates dynamic section markers using AI.

        Args:
            text (str): The text content to analyze.

        Returns:
            list: A list of suggested section markers.
        """
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(
                f"Suggest a list of 5-10 keywords or phrases that could indicate the start of a new section in the following text: {text[:1500]}.  Exclude the words introduction, overview, summary, background, and conclusion from your response. Respond with just a comma-separated list of keywords/phrases."
            )
            markers = [m.strip() for m in response.text.split(',')]
            return markers
        except Exception as e:
            logging.error(f"Section marker generation failed: {str(e)}")
            return []