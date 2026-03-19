import logging
from flask import current_app
from google import genai
from openai import OpenAI

# Custom Exceptions
class AIProviderError(Exception):
    pass

class AIRouter:
    def __init__(self):
        # Clients are not initialised here because current_app may not be ready
        pass

    # ---------------------------------------------------------------------------
    # HuggingFace Inference Router — OpenAI-compatible endpoint:
    #   https://router.huggingface.co/v1
    #
    # Model suffix rules (as of 2025):
    #   :fastest  — router auto-picks the highest-throughput provider (free tier OK)
    #   :auto     — first available provider in user's preference order
    #   :cerebras / :together / :sambanova etc — force a specific backend
    #
    # NOTE: ":hf-inference" is now CPU-only (BERT/GPT-2 era models) and does NOT
    # support modern instruct LLMs.  Use :fastest for free-tier chat completions.
    #
    # Tried in order; first successful response wins.
    # ---------------------------------------------------------------------------
    HF_ROUTER_BASE = "https://router.huggingface.co/v1"

    HF_MODELS = [
        "meta-llama/Llama-3.1-8B-Instruct:fastest",        # llama 8B — very widely available
        "Qwen/Qwen2.5-7B-Instruct:fastest",                 # Qwen 7B instruct
        "mistralai/Mistral-7B-Instruct-v0.3:fastest",       # Mistral 7B
        "microsoft/Phi-3.5-mini-instruct:fastest",          # Phi 3.5 mini — lightweight
        "google/gemma-2-2b-it:fastest",                     # Gemma 2B — smallest fallback
    ]

    # ------------------------------------------------------------------
    # Provider registration
    # ------------------------------------------------------------------

    def _init_providers(self):
        providers = []

        google_key = current_app.config.get('GOOGLE_API_KEY')
        if google_key:
            providers.append({
                'name': 'gemini',
                'func': self._generate_with_gemini,
                'key': google_key
            })

        openai_key = current_app.config.get('OPENAI_API_KEY')
        if openai_key:
            providers.append({
                'name': 'openai',
                'func': self._generate_with_openai,
                'key': openai_key
            })

        hf_key = current_app.config.get('HUGGINGFACE_API_KEY')
        if hf_key:
            providers.append({
                'name': 'huggingface',
                'func': self._generate_with_huggingface,
                'key': hf_key
            })

        return providers

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

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
                logging.info(f"Attempting generation with: {provider['name']}")
                result = provider['func'](prompt, provider['key'])
                if result:
                    logging.info(f"Success with provider: {provider['name']}")
                    return result
            except Exception as e:
                msg = f"{provider['name']} failed: {str(e)}"
                logging.warning(msg)
                errors.append(msg)

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
        Uses the HuggingFace Inference Router (OpenAI-compatible).
          Base URL : https://router.huggingface.co/v1
          Auth     : Bearer <HF token>
          Model fmt: "org/model-name:provider"
                     ":fastest" lets the router pick the best available
                     free-tier backend automatically.

        Iterates through HF_MODELS until one succeeds.
        """
        client = OpenAI(
            base_url=self.HF_ROUTER_BASE,
            api_key=key,
        )

        last_error = None

        for model_id in self.HF_MODELS:
            try:
                logging.info(f"HuggingFace router: trying '{model_id}'")
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful AI assistant."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=1024,
                    temperature=0.5,
                    timeout=90,
                )
                text = response.choices[0].message.content
                if text and text.strip():
                    logging.info(f"HuggingFace router: success with '{model_id}'")
                    return text.strip()

                last_error = f"{model_id} returned empty content"
                logging.warning(f"HuggingFace router: {last_error}")

            except Exception as e:
                last_error = f"{model_id} raised: {str(e)}"
                logging.warning(f"HuggingFace router: {last_error}")
                continue

        raise Exception(
            f"All HuggingFace models failed. Last error: {last_error}"
        )