import os
import base64
import logging
import nltk
import google.generativeai as genai
from flask import current_app
from PIL import Image

nltk.download('punkt', quiet=True)

class FileProcessor:
    def __init__(self):
        google_key = current_app.config.get('GOOGLE_API_KEY', '').strip()
        if not google_key:
            logging.error("Google API key is missing or empty")
            raise ValueError("Google API key not configured")

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

            suggested_title = self._generate_title(summary, config['title_length'])
            display_format = self._suggest_display_format(summary)

            return {
                'summary': summary,
                'title': suggested_title,
                'display_format': display_format
            }

        except Exception as e:
            logging.error(f"File processing error: {str(e)}")
            raise

    def _gemini_summarization(self, file_content, file_type, summary_depth):
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
                'jpeg': 'image/jpeg'
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
            prompt = f"{depth_prompts[closest_depth]} Analyze this {file_type.upper()} file:"

            if file_type in ['txt', 'md']:
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

    def _generate_title(self, text, max_words=4):
        sentences = nltk.sent_tokenize(text)
        if not sentences:
            return "Document Summary"

        first_sentence = sentences[0]
        words = first_sentence.split()

        if len(words) <= max_words:
            title = ' '.join(words)
        else:
            title = ' '.join(words[:max_words])

        return title.strip().title()

    def _suggest_display_format(self, text):
        sentences = nltk.sent_tokenize(text)
        words_per_sentence = len(text.split()) / len(sentences) if sentences else 0

        if words_per_sentence < 10:
            return {
                'type': 'bullet_points',
                'points': sentences,
                'style': {
                    'font': 'ComingSoon',
                    'colors': {
                        'primary': '#6A11CB',
                        'secondary': '#BC4E9C'
                    }
                },
                'image_query': 'concise notes visualization'
            }
        elif any(marker in text.lower() for marker in ['first', 'second', 'finally', 'next']):
            sections = self._extract_sections(text)
            return {
                'type': 'sections',
                'sections': sections,
                'style': {
                    'font': 'ComingSoon',
                    'colors': {
                        'primary': '#6A11CB',
                        'headers': '#BC4E9C'
                    }
                },
                'image_query': 'structured document organization'
            }
        else:
            return {
                'type': 'paragraph',
                'style': {
                    'font': 'ComingSoon',
                    'colors': {
                        'text': '#000000',
                        'background': '#FFFFFF'
                    }
                },
                'image_query': 'clean document layout'
            }

    def _extract_sections(self, text):
        sentences = nltk.sent_tokenize(text)
        sections = []
        current_section = {'title': 'Overview', 'content': []}

        for sentence in sentences:
            lower_sentence = sentence.lower()
            is_new_section = any(marker in lower_sentence for marker in 
                               ['first', 'second', 'third', 'finally', 'next', 'moreover', 'furthermore'])

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