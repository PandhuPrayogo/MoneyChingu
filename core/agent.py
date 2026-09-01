import re
import json
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
from datetime import datetime

from core.gemini_client import gemini_client
from core.prompts import format_system_prompt_with_context
from core.context_manager import context_manager
from skills import ALL_SKILLS, data_management_skill, data_processing_skill, financial_analytics_skill, rag_context_skill, hf_skill
from config import DEFAULT_CURRENCY

class FinancialAgent:
    """
    Central AI ReAct Financial Agent.
    Coordinates multimodal ingestion, tool dispatching, RAG context retrieval,
    and Human-In-The-Loop review workflows.
    """
    def __init__(self):
        self.skills_map = {skill.name: skill for skill in ALL_SKILLS}

    def process_user_turn(self, 
                          user_message: str, 
                          conversation_history: List[Dict[str, str]], 
                          display_currency: str = DEFAULT_CURRENCY,
                          images: Optional[List[Image.Image]] = None) -> Dict[str, Any]:
        """
        Execute full ReAct agent loop on user input.
        Returns response message, scratchpad CoT, executed tool result, and any HITL pending action.
        """
        # 1. Silent RAG Pipeline: Vector search across past memories & receipts
        try:
            from database.vector_store import vector_store
            retrieved_memories = vector_store.search(user_message, top_k=3)
        except Exception:
            retrieved_memories = []

        # 2. Fetch grounded live database context
        context_snapshot = context_manager.get_live_context_snapshot(display_currency=display_currency)
        
        # 3. Build Anthropic XML System Prompt with Context + Silent RAG
        system_prompt = format_system_prompt_with_context(context_snapshot, retrieved_memories=retrieved_memories)

        # 4. Call Gemini LLM
        raw_response = gemini_client.generate_chat_response(
            system_prompt=system_prompt,
            messages_history=conversation_history,
            user_input=user_message,
            images=images
        )

        # 5. Parse XML output blocks: <scratchpad>, <tool_call>, <message>
        scratchpad_content = self._extract_xml_tag(raw_response, "scratchpad")
        tool_call_json_str = self._extract_xml_tag(raw_response, "tool_call")
        message_content = self._extract_xml_tag(raw_response, "message")

        if not message_content:
            message_content = raw_response

        tool_result = None
        hitl_pending = None

        # 5. Check and execute tool call if requested
        if tool_call_json_str and tool_call_json_str.strip().lower() != "none":
            try:
                # Clean markdown backticks if any
                clean_json = tool_call_json_str.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                    
                tool_data = json.loads(clean_json.strip())
                skill_name = tool_data.get("skill")
                params = tool_data.get("parameters", {})

                if skill_name in self.skills_map:
                    skill = self.skills_map[skill_name]
                    tool_result = skill.execute(**params)
            except Exception as e:
                tool_result = {"status": "error", "error": f"Tool execution failed: {str(e)}"}

        # 6. Check if user prompt is a direct expense/income statement that should trigger HITL confirmation
        hitl_pending = self._detect_hitl_intent(user_message, tool_result, display_currency)

        return {
            "message": message_content,
            "scratchpad": scratchpad_content,
            "tool_result": tool_result,
            "hitl_pending": hitl_pending
        }

    def _extract_xml_tag(self, text: str, tag_name: str) -> Optional[str]:
        """Extract content enclosed within <tag_name>...</tag_name>."""
        pattern = rf"<{tag_name}>(.*?)</{tag_name}>"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _detect_hitl_intent(self, user_message: str, tool_result: Optional[Dict[str, Any]], current_currency: str) -> Optional[Dict[str, Any]]:
        """
        Inspect if an expense or income was mentioned so we can offer a 1-click
        editable Human-in-the-Loop confirmation card.
        """
        # If tool already added transaction, no need for redundant HITL
        if tool_result and tool_result.get("status") == "success" and "transaction_id" in tool_result:
            return None

        lower = user_message.lower()
        # Heuristic regex for amounts
        amount_match = re.search(r"(\$|rp|idr|\b)?\s*([0-9]+(?:[,.][0-9]{2,3})*(?:\.[0-9]{1,2})?)\s*(usd|idr|bucks|k)?", lower)
        
        if any(w in lower for w in ["spent", "bought", "paid", "beli", "bayar", "earned", "received", "dapet"]):
            # Extract basic components
            currency = "IDR" if any(w in lower for w in ["idr", "rp", "ribu", "k"]) else current_currency
            
            # Extract amount number
            amount = 0.0
            if amount_match:
                try:
                    num_str = amount_match.group(2).replace(",", "")
                    amount = float(num_str)
                    if "k" in lower and amount < 1000:
                        amount = amount * 1000
                except ValueError:
                    amount = 0.0

            if amount > 0:
                is_income = any(w in lower for w in ["earned", "received", "salary", "gaji", "dapet"])
                return {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "amount": amount,
                    "currency": currency,
                    "type": "income" if is_income else "expense",
                    "category": "Salary" if is_income else "Food & Dining",
                    "merchant": "Quick Log",
                    "description": user_message
                }
        return None

# Global agent singleton
financial_agent = FinancialAgent()
