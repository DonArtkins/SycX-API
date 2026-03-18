import os
import base64
import logging
import nltk
from google import genai
from google.genai import types
from flask import current_app
from PIL import Image
import re
import datetime

nltk.download('punkt', quiet=True)

class FileProcessor:
    def __init__(self):
        # We don't initialize the client here because current_app might not be bound yet
        # or we might want to initialize it per-request using the configured API key.
        pass

    def _get_genai_client(self):
        google_key = current_app.config.get('GOOGLE_API_KEY')
        if not google_key:
            raise ValueError("GOOGLE_API_KEY is not configured")
        return genai.Client(api_key=google_key)

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
        """
        try:
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
                'dart': 'text/plain',
                'csv': 'text/csv',
                'json': 'application/json',
                'html': 'text/html',
                'xml': 'application/xml',
                'svg':'image/svg+xml',
                'gif': 'image/gif',
                'tiff': 'image/tiff',
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
            client = self._get_genai_client()

            depth_prompts = {
                0.0: "Generate an extremely concise summary in 1-2 sentences.",
                1.0: "Create a brief summary with key points only.",
                2.0: "Produce a balanced summary covering main points.",
                3.0: "Develop a detailed summary of important content.",
                4.0: "Create comprehensive summary covering nearly all content."
            }

            closest_depth = min([0.0, 1.0, 2.0, 3.0, 4.0], key=lambda x: abs(x - summary_depth))
            prompt = f"{depth_prompts[closest_depth]} Analyze this {file_type.upper()} file. Extract the content into well-defined sections, using clear titles and coherent paragraphs. Completely REMOVE any unnecessary markdown characters, bullet points, numbers or any other formatting symbols. Create well formated contents and subheadings."

            contents = []
            if file_type in ['txt', 'md', 'dart']:
                try:
                    text_content = file_content.decode('utf-8')
                    contents = [prompt, text_content]
                except UnicodeDecodeError:
                    contents = [
                        prompt,
                        types.Part.from_bytes(data=file_content, mime_type=mime_type)
                    ]
            else:
                contents = [
                    prompt,
                    types.Part.from_bytes(data=file_content, mime_type=mime_type)
                ]

            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=contents
            )

            return response.text

        except Exception as e:
            logging.error(f"Gemini API error: {str(e)}")
            raise

    def _generate_title(self, text):
        """
        Generates a meaningful title using AI for the given text content.
        """
        try:
            client = self._get_genai_client()
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"Suggest a short, descriptive, and well-formatted title for the following document: {text[:2000]}. The title must not exceed 60 characters. Respond with just the title, removing any quotation marks or surrounding phrases. Format the title in title case; this is VERY IMPORTANT"
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
                'font': 'Arial',
                'colors': {
                    'primary': '#0D47A1',
                    'headers': '#1565C0',
                    'accent': '#E64A19',
                    'background': '#E3F2FD'
                },
                'code_font': 'Courier',
                'icon_set': 'fontawesome'
            },
            'image_query': f"{self._generate_title(text)} {text[:500]}"
        }

    def _extract_sections(self, text):
        """Extract sections from the given text."""
        sentences = nltk.sent_tokenize(text)
        sections = []
        current_section = {'title': 'Introduction', 'content': []}

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
        """
        try:
            client = self._get_genai_client()
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"Suggest a list of 5-10 keywords or phrases that could indicate the start of a new section in the following text: {text[:1500]}.  Exclude the words introduction, overview, summary, background, and conclusion from your response. Respond with just a comma-separated list of keywords/phrases."
            )
            markers = [m.strip() for m in response.text.split(',')]
            return markers
        except Exception as e:
            logging.error(f"Section marker generation failed: {str(e)}")
            return []