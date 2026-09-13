import os
from typing import Optional, List, Dict, Any, Union
from PIL import Image
import google.generativeai as genai

from config import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL, EMBEDDING_MODEL

class GeminiClient:
    """
    Client for Google Gemini Free Tier Models.
    Supports multimodal inputs (text, image, PDF) and text embeddings.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_GEMINI_MODEL):
        self.api_key = api_key or GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name
        self._configured = False
        self._init_client()

    def set_api_key(self, api_key: str):
        """Update API key dynamically from UI."""
        self.api_key = api_key
        self._init_client()

    def set_model(self, model_name: str):
        """Update model name dynamically."""
        self.model_name = model_name

    def _init_client(self):
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self._configured = True
            except Exception as e:
                print(f"Error configuring Gemini API: {e}")
                self._configured = False
        else:
            self._configured = False

    def is_ready(self) -> bool:
        return self._configured and bool(self.api_key)

    def generate_chat_response(self, 
                               system_prompt: str, 
                               messages_history: List[Dict[str, str]], 
                               user_input: str,
                               images: Optional[List[Image.Image]] = None) -> str:
        """
        Generate conversational response with system instructions and image attachments.
        Includes automatic fallback across available Flash models.
        """
        if not self.is_ready():
            return self._mock_response(user_input)

        candidate_models = [self.model_name, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]
        # Remove duplicates while preserving order
        unique_models = []
        for m in candidate_models:
            if m and m not in unique_models:
                unique_models.append(m)

        last_error = None
        for current_model_name in unique_models:
            try:
                # Model with system instruction
                model = genai.GenerativeModel(
                    model_name=current_model_name,
                    system_instruction=system_prompt,
                    generation_config={
                        "temperature": 0.2,
                        "top_p": 0.95,
                        "max_output_tokens": 2048,
                    }
                )

                # Build content payload
                contents: List[Any] = []
                
                from core.context_manager import context_manager
                # Hybrid pruned history for context economy
                pruned_history = context_manager.prepare_history_for_injection(messages_history)
                for msg in pruned_history:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [msg["content"]]})

                # Current turn parts
                current_parts: List[Any] = [user_input]
                if images:
                    for img in images:
                        current_parts.append(img)

                contents.append({"role": "user", "parts": current_parts})

                # Run generation
                response = model.generate_content(contents)
                return response.text or ""

            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                if "ResourceExhausted" in error_msg or "429" in error_msg:
                    return "<scratchpad>\nRate limit reached on Gemini Free Tier.\n</scratchpad>\n<message>\n⚠️ Whoa chief, we hit Google Gemini's free tier rate limit for a second! Give it ~30 seconds to cool down and try again.\n</message>"
                # If 404 / NotFound, continue to next candidate model
                if "404" in error_msg or "NotFound" in error_msg or "not found" in error_msg.lower():
                    continue
                # For other errors, return formatted message
                return f"<scratchpad>\nAPI error occurred: {error_msg}\n</scratchpad>\n<message>\n⚠️ Hit an unexpected hiccup contacting Gemini API: {error_msg}\n</message>"

        return f"<scratchpad>\nAll candidate Gemini models failed. Last error: {last_error}\n</scratchpad>\n<message>\n⚠️ Could not connect to Gemini models ({', '.join(unique_models)}). Please verify your API key.\n</message>"

    def _mock_response(self, user_input: str) -> str:
        """Offline / demo mode mock assistant response."""
        return f"""<scratchpad>
Offline Mode: No Gemini API Key provided.
Intent: Echo user prompt with sample witty financial response.
</scratchpad>
<message>
Yo! I'm running in **Offline Mode** right now because no `GEMINI_API_KEY` was setting up.

I can still do manual tracking, view your dashboard, and manage budgets! To unlock full AI vision parsing and multimodal chat superpowers, pop your free API key into the settings! 🔑
</message>"""

# Global singleton
gemini_client = GeminiClient()
