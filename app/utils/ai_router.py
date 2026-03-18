import logging
import json
import requests
from flask import current_app
from google import genai
from openai import OpenAI

# Custom Exceptions
class AIProviderError(Exception):
    pass

class AIRouter:
    def __init__(self):
        # We don't initialize clients in __init__ because current_app might not be ready
        pass
        
    def _init_providers(self):
        providers = []
        
        # 1. Google Gemini
        google_key = current_app.config.get('GOOGLE_API_KEY')
        if google_key:
            providers.append({
                'name': 'gemini',
                'func': self._generate_with_gemini,
                'key': google_key
            })
            
        # 2. OpenAI
        openai_key = current_app.config.get('OPENAI_API_KEY')
        if openai_key:
            providers.append({
                'name': 'openai',
                'func': self._generate_with_openai,
                'key': openai_key
            })
            
        # 3. Hugging Face
        hf_key = current_app.config.get('HUGGINGFACE_API_KEY')
        if hf_key:
            providers.append({
                'name': 'huggingface',
                'func': self._generate_with_huggingface,
                'key': hf_key
            })
            
        return providers

    def generate_content(self, prompt: str) -> str:
        providers = self._init_providers()
        
        if not providers:
            raise AIProviderError("No AI providers configured. Please set GOOGLE_API_KEY, OPENAI_API_KEY, or HUGGINGFACE_API_KEY.")
            
        errors = []
        
        for provider in providers:
            try:
                logging.info(f"Attempting to generate content using: {provider['name']}")
                result = provider['func'](prompt, provider['key'])
                if result:
                    logging.info(f"Successfully generated content using: {provider['name']}")
                    return result
            except Exception as e:
                error_msg = f"{provider['name']} failed: {str(e)}"
                logging.warning(error_msg)
                errors.append(error_msg)
                continue
                
        # If we got here, all enabled providers failed
        logging.error("All AI providers failed. Errors: " + " | ".join(errors))
        raise AIProviderError(f"Generation failed across all available providers. Errors: {errors}")

    def _generate_with_gemini(self, prompt: str, key: str) -> str:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return response.text

    def _generate_with_openai(self, prompt: str, key: str) -> str:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an intelligent assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    def _generate_with_huggingface(self, prompt: str, key: str) -> str:
        # Using mistralai/Mistral-7B-Instruct-v0.2 as a reliable standard model
        API_URL = "https://router.huggingface.co/hf-inference/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {"Authorization": f"Bearer {key}"}
        
        payload = {
            "inputs": f"[INST] {prompt} [/INST]",
            "parameters": {
                "max_new_tokens": 1024,
                "temperature": 0.5,
                "return_full_text": False
            }
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Hugging Face API returned status {response.status_code}: {response.text}")
            
        return response.json()[0]['generated_text'].strip()
