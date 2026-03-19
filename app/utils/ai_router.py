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

    # ---------------------------------------------------------------------------
    # Free-tier HuggingFace models to try in order.
    # These use the standard Serverless Inference API endpoint, which is the
    # reliable free-tier path (https://api-inference.huggingface.co/models/<id>).
    # ---------------------------------------------------------------------------
    HF_MODELS = [
        "mistralai/Mistral-7B-Instruct-v0.3",
        "HuggingFaceH4/zephyr-7b-beta",
        "Qwen/Qwen2.5-7B-Instruct",
        "meta-llama/Llama-3.2-3B-Instruct",
        "google/flan-t5-xxl",                  # smaller but always available
    ]

    HF_BASE_URL = "https://api-inference.huggingface.co/models"

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
            raise AIProviderError(
                "No AI providers configured. Please set GOOGLE_API_KEY, "
                "OPENAI_API_KEY, or HUGGINGFACE_API_KEY."
            )

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

        logging.error("All AI providers failed. Errors: " + " | ".join(errors))
        raise AIProviderError(
            f"Generation failed across all available providers. Errors: {errors}"
        )

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

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
        """
        Tries several free-tier HuggingFace models via the Serverless Inference
        API (https://api-inference.huggingface.co/models/<model_id>).

        Falls back through the model list until one succeeds.
        """
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        last_error = None

        for model_id in self.HF_MODELS:
            url = f"{self.HF_BASE_URL}/{model_id}"

            # Use chat-style input for instruct models; flan-t5 takes plain text.
            if "flan-t5" in model_id:
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 1024,
                        "temperature": 0.5,
                        "do_sample": True,
                    },
                    "options": {"wait_for_model": True},
                }
            else:
                # Instruct-tuned chat models expect the [INST] / system format
                formatted = (
                    f"<s>[INST] You are a helpful AI assistant. "
                    f"{prompt} [/INST]"
                )
                payload = {
                    "inputs": formatted,
                    "parameters": {
                        "max_new_tokens": 1024,
                        "temperature": 0.5,
                        "return_full_text": False,
                        "do_sample": True,
                    },
                    "options": {"wait_for_model": True},
                }

            try:
                logging.info(f"HuggingFace: trying model {model_id}")
                response = requests.post(
                    url, headers=headers, json=payload, timeout=90
                )

                # 503 means the model is loading — skip to next
                if response.status_code == 503:
                    logging.warning(
                        f"HuggingFace model {model_id} is loading (503), "
                        "trying next model."
                    )
                    last_error = f"{model_id} returned 503 (model loading)"
                    continue

                if response.status_code != 200:
                    err = (
                        f"{model_id} returned HTTP {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                    logging.warning(f"HuggingFace: {err}")
                    last_error = err
                    continue

                data = response.json()

                # Parse the response — different model families return different shapes
                text = self._parse_hf_response(data, model_id)

                if text and text.strip():
                    logging.info(
                        f"HuggingFace: success with model {model_id}"
                    )
                    return text.strip()

                logging.warning(
                    f"HuggingFace: empty response from {model_id}, "
                    "trying next model."
                )
                last_error = f"{model_id} returned empty text"

            except requests.exceptions.Timeout:
                last_error = f"{model_id} timed out"
                logging.warning(f"HuggingFace: {last_error}")
                continue
            except Exception as e:
                last_error = f"{model_id} raised {str(e)}"
                logging.warning(f"HuggingFace: {last_error}")
                continue

        raise Exception(
            f"All HuggingFace models failed. Last error: {last_error}"
        )

    @staticmethod
    def _parse_hf_response(data, model_id: str) -> str:
        """
        Normalise the various response shapes returned by HF Inference API.

        Shapes seen in the wild:
          - List[{"generated_text": "..."}]          (text-generation)
          - [{"generated_text": [{"role": ..., "content": "..."}]}]  (chat)
          - {"generated_text": "..."}                (some older models)
          - List[List[{"generated_text": "..."}]]    (batched)
        """
        try:
            if isinstance(data, list) and len(data) > 0:
                first = data[0]

                # Nested list (batched output)
                if isinstance(first, list) and len(first) > 0:
                    first = first[0]

                if isinstance(first, dict):
                    gen = first.get("generated_text", "")

                    # Chat-style: generated_text is a list of message dicts
                    if isinstance(gen, list):
                        for msg in reversed(gen):
                            if isinstance(msg, dict) and msg.get("role") == "assistant":
                                return msg.get("content", "")
                        # Fallback: last message content
                        if gen:
                            last = gen[-1]
                            if isinstance(last, dict):
                                return last.get("content", "")

                    return str(gen)

            elif isinstance(data, dict):
                gen = data.get("generated_text", "")
                if isinstance(gen, str):
                    return gen

        except Exception as parse_err:
            logging.warning(
                f"HuggingFace response parse error for {model_id}: {parse_err}"
            )

        return ""