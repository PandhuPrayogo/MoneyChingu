from typing import Dict, Any, List, Optional
from skills.base import BaseSkill
from config import DEFAULT_EXPENSE_CATEGORIES

class HuggingFaceSkill(BaseSkill):
    """
    HuggingFace Ecosystem Skill: Integrates open-source models & datasets
    from Hugging Face for financial categorization and sentiment analysis.
    """
    name = "huggingface_tools"
    description = "Provides access to HuggingFace ecosystem tools for zero-shot transaction categorization and financial sentiment."
    parameters = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "enum": ["categorize_text", "financial_sentiment"],
                "description": "The NLP task to perform"
            },
            "text": {"type": "string", "description": "Text to analyze"}
        },
        "required": ["task", "text"]
    }

    def execute(self, **kwargs) -> Dict[str, Any]:
        task = kwargs.get("task")
        text = kwargs.get("text", "")

        if task == "categorize_text":
            return self._categorize_text(text)
        elif task == "financial_sentiment":
            return self._financial_sentiment(text)
        else:
            return {"status": "error", "message": f"Unknown HuggingFace task: {task}"}

    def _categorize_text(self, text: str) -> Dict[str, Any]:
        """Simple rule-assisted zero-shot categorization matching."""
        lower = text.lower()
        matched_cat = "Other Expense"
        
        keywords = {
            "Food & Dining": ["coffee", "lunch", "dinner", "burger", "pizza", "starbucks", "kopi", "makan", "restoran", "food", "cafe"],
            "Groceries": ["supermarket", "groceries", "walmart", "costco", "indomaret", "alfamart", "vegetables", "milk"],
            "Transport & Fuel": ["uber", "grab", "gojek", "taxi", "gas", "fuel", "pertamina", "shell", "subway", "train", "flight"],
            "Bills & Utilities": ["electricity", "water", "internet", "wifi", "pln", "telkom", "rent", "insurance"],
            "Entertainment & Subs": ["netflix", "spotify", "youtube", "cinema", "game", "steam", "playstation"],
            "Health & Fitness": ["gym", "doctor", "pharmacy", "medicine", "apotek", "dentist", "hospital"]
        }

        for cat, words in keywords.items():
            if any(w in lower for w in words):
                matched_cat = cat
                break

        return {
            "status": "success",
            "text": text,
            "suggested_category": matched_cat
        }

    def _financial_sentiment(self, text: str) -> Dict[str, Any]:
        """Classifies financial health sentiment."""
        lower = text.lower()
        if any(w in lower for w in ["broke", "overspent", "debt", "expensive", "loss", "deficit"]):
            sentiment = "warning_urgent"
        elif any(w in lower for w in ["saving", "profit", "invest", "bonus", "cheap", "discount", "surplus"]):
            sentiment = "positive_wealth_building"
        else:
            sentiment = "neutral"

        return {
            "status": "success",
            "sentiment": sentiment
        }

hf_skill = HuggingFaceSkill()
