import re
import json
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
from datetime import datetime

from core.gemini_client import gemini_client
from core.prompts import build_system_prompt, format_system_prompt_with_context
from core.context_manager import context_manager
from core.intent_router import intent_router
from core.memory_store import memory_store
from skills import ALL_SKILLS, data_management_skill, data_processing_skill, financial_analytics_skill, rag_context_skill, hf_skill
from config import DEFAULT_CURRENCY

class FinancialAgent:
    """
    Central AI ReAct Financial Agent with Google-Standard Context Engineering.
    Coordinates JIT tool routing, layered prompt assembly with strict authority hierarchy,
    in-flight token compression, anti-poisoning tool validation, and typed memory persistence.
    """
    def __init__(self):
        self.skills_map = {skill.name: skill for skill in ALL_SKILLS}
        self.DESTRUCTIVE_ACTIONS = {"clear_database", "delete_transaction", "delete_account", "transfer_funds"}

    def _is_destructive_action(self, tool_data: Dict[str, Any]) -> bool:
        """Check if tool call targets a destructive or irreversible operation."""
        params = tool_data.get("parameters", {})
        action = params.get("action", "")
        return action in self.DESTRUCTIVE_ACTIONS

    def _detect_destructive_intent(self, user_message: str) -> Optional[Dict[str, Any]]:
        """Detect intent to wipe, reset, or delete all transactions/database."""
        lower = user_message.lower()
        has_wipe_verb = any(p in lower for p in [
            "remove all", "delete all", "clear all", "wipe", "reset database", 
            "hapus semua", "bersihkan semua", "kosongkan", "clear database", 
            "clear history", "remove history", "hapus riwayat", "delete history",
            "remove all history", "hapus semua transaksi", "delete all transactions"
        ])
        if has_wipe_verb:
            return {
                "type": "destructive_confirmation",
                "action": "clear_database",
                "skill": "data_management",
                "parameters": {"action": "clear_database"},
                "description": "Reset all ledger transactions, accounts, and chat history back to zero."
            }
        return None

    def process_user_turn(self, 
                          user_message: str, 
                          conversation_history: List[Dict[str, str]], 
                          display_currency: str = DEFAULT_CURRENCY,
                          images: Optional[List[Image.Image]] = None) -> Dict[str, Any]:
        """
        Execute Context Engineering ReAct agent loop on user input.
        Phases:
        1. SELECT: JIT Intent Classification & Candidate Tool Pruning (anti-Confusion)
        2. RETRIEVE: Live SQLite Context & Long-term Memory Fetch
        3. COMPRESS: In-Flight History Pruning & Rolling Summary (anti-Distraction)
        4. ASSEMBLE: Layered Prompt with Strict Authority Hierarchy (anti-Clash)
        5. GENERATE: LLM Inference with Pristine Window
        6. EXECUTE & VALIDATE: Safe Tool Validation & Error Sanitization (anti-Poisoning)
        7. WRITE: Episodic & Semantic Memory Externalization
        """
        # Phase 1: SELECT (JIT Intent & Dynamic Tool Schema Assembly)
        intents = intent_router.classify_intent(user_message)
        candidate_tools = intent_router.get_candidate_tools(intents)
        required_memory_types = intent_router.get_required_memory_types(intents)

        # Phase 2: RETRIEVE (Live SQLite Grounding + Typed Memories + Vector RAG)
        context_snapshot = context_manager.get_live_context_snapshot(display_currency=display_currency)
        typed_memories = memory_store.retrieve_memories(user_message, memory_types=required_memory_types, top_k=2)

        try:
            from database.vector_store import vector_store
            vector_memories = vector_store.search(user_message, top_k=2)
        except Exception:
            vector_memories = []
        combined_memories = typed_memories + vector_memories

        # Phase 3: COMPRESS (In-Flight History Pruning & Extractive Rolling Summary)
        conversation_summary = context_manager.get_conversation_summary(conversation_history)
        pruned_history = context_manager.prepare_history_for_injection(conversation_history)

        # Phase 4: ASSEMBLE (Layered System Prompt with Strict Authority Hierarchy)
        system_prompt = build_system_prompt(
            context_snapshot=context_snapshot,
            candidate_tools=candidate_tools,
            conversation_summary=conversation_summary,
            retrieved_memories=combined_memories
        )

        # Phase 5: GENERATE (LLM Inference)
        raw_response = gemini_client.generate_chat_response(
            system_prompt=system_prompt,
            messages_history=pruned_history,
            user_input=user_message,
            images=images
        )

        # Phase 6: EXECUTE & VALIDATE (Parse XML & Run Safe Validation)
        scratchpad_content = self._extract_xml_tag(raw_response, "scratchpad")
        tool_call_json_str = self._extract_xml_tag(raw_response, "tool_call")
        message_content = self._extract_xml_tag(raw_response, "message")

        if not message_content:
            message_content = raw_response

        tool_result = None
        hitl_pending = None

        if tool_call_json_str and tool_call_json_str.strip().lower() != "none":
            # Sanitize and validate tool call payload (Anti-Context Poisoning)
            is_valid, error_msg, validated_payload = self._parse_and_validate_tool_call(tool_call_json_str)

            if is_valid and validated_payload:
                skill_name = validated_payload["skill"]
                params = validated_payload["parameters"]
                action_name = params.get("action", "")

                # Action Permission Gate: Intercept destructive / irreversible actions before execution
                if self._is_destructive_action(validated_payload):
                    hitl_pending = {
                        "type": "destructive_confirmation",
                        "action": action_name,
                        "skill": skill_name,
                        "parameters": params,
                        "description": f"Are you sure you want to execute '{action_name}'? This action modifies or clears financial data permanently."
                    }
                    message_content = f"⚠️ **Action Permission Required**\n\nYou requested: **{action_name}**. This action is irreversible. Please review and confirm in the card below."
                else:
                    try:
                        skill = self.skills_map[skill_name]
                        tool_result = skill.execute(**params)

                        # Format rich tool data response
                        formatted_tool_output = self._format_tool_response(skill_name, tool_result, display_currency)

                        if formatted_tool_output:
                            clean_msg = message_content.strip() if message_content else ""
                            is_placeholder = (
                                not clean_msg
                                or clean_msg.startswith("<tool_call>")
                                or any(p in clean_msg.lower() for p in [
                                    "let me pull", "pulling up", "let me get", "checking your", 
                                    "one moment", "right away", "here are your", "here's your",
                                    "i will pull", "fetching", "on it"
                                ])
                            )
                            if is_placeholder:
                                message_content = f"{clean_msg}\n\n{formatted_tool_output}".strip() if clean_msg and not clean_msg.startswith("<tool_call>") else formatted_tool_output
                            else:
                                message_content = f"{clean_msg}\n\n{formatted_tool_output}"

                        # Phase 7: WRITE (Episodic Memory Externalization)
                        if tool_result.get("status") == "success":
                            action_summary = str(tool_result.get("message", f"Executed {skill_name}"))[:120]
                            memory_store.store_episodic(skill_name, action_summary)

                    except Exception as e:
                        # Sanitize error to prevent Context Poisoning
                        tool_result = {"status": "error", "message": f"Execution error in {skill_name}."}
                        message_content = f"⚠️ Tool execution encountered an issue: {str(e)}"
            else:
                # Malformed schema caught before poisoning context
                tool_result = {"status": "error", "message": error_msg}
                message_content = f"⚠️ {error_msg}"

        # Phase 7: WRITE (User Preference / Identity Extraction)
        self._detect_preference_intent(user_message)

        # Destructive Intent Detection (fallback when model did not emit tool_call for wipe/delete prompt)
        if not hitl_pending:
            destructive_hitl = self._detect_destructive_intent(user_message)
            if destructive_hitl:
                hitl_pending = destructive_hitl
                message_content = f"⚠️ **Action Permission Required**\n\nYou requested to clear or delete financial records. This action cannot be undone. Please confirm below to proceed."
            else:
                # Human-in-the-Loop Intent Detection for expenses/income
                hitl_pending = self._detect_hitl_intent(user_message, tool_result, display_currency)

        return {
            "message": message_content,
            "scratchpad": scratchpad_content,
            "tool_result": tool_result,
            "hitl_pending": hitl_pending
        }

    def _parse_and_validate_tool_call(self, raw_tool_json: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Anti-Context Poisoning:
        Strictly parse and validate tool structure before execution.
        Prevents cascading error loops from malformed tool outputs.
        """
        try:
            clean_json = raw_tool_json.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]

            tool_data = json.loads(clean_json.strip())
            if not isinstance(tool_data, dict):
                return False, "Tool call must be a JSON object with 'skill' and 'parameters'.", None

            skill_name = tool_data.get("skill")
            if not skill_name:
                return False, "Missing 'skill' attribute in tool call.", None

            if skill_name not in self.skills_map:
                return False, f"Unknown skill '{skill_name}'.", None

            params = tool_data.get("parameters", {})
            if not isinstance(params, dict):
                params = {}

            return True, None, {"skill": skill_name, "parameters": params}

        except json.JSONDecodeError:
            return False, "Malformed JSON syntax in tool call.", None
        except Exception as e:
            return False, f"Validation failure: {str(e)}", None

    def _detect_preference_intent(self, user_message: str) -> None:
        """Detect and store user's name or custom AI persona nickname into SQLite and MemoryStore."""
        try:
            from database.db import db
            # Detect user name: "My name is Bob", "Call me Bob", "Namaku Bob", "Nama saya Bob"
            user_name_match = re.search(r"\b(?:my name is|call me|namaku|nama saya)\s+([A-Za-z0-9_-]+)", user_message, re.IGNORECASE)
            if user_name_match:
                name = user_name_match.group(1).strip()
                if name.lower() not in ["a", "an", "the", "moneychingu"]:
                    db.set_preference("user_name", name)
                    memory_store.store_semantic(f"User name is {name}", category="identity")

            # Detect AI name: "Your name is Friday", "Call yourself Friday", "Namamu Friday"
            ai_name_match = re.search(r"\b(?:your name is|call yourself|nama kamu|namamu)\s+([A-Za-z0-9_-]+)", user_message, re.IGNORECASE)
            if ai_name_match:
                ai_name = ai_name_match.group(1).strip()
                db.set_preference("ai_name", ai_name)
                memory_store.store_semantic(f"AI persona nickname is {ai_name}", category="identity")
        except Exception:
            pass

    def _format_tool_response(self, skill_name: str, result: Dict[str, Any], currency: str) -> str:
        """Format raw skill output into a readable markdown response with clean tables."""
        sym = "$" if currency == "USD" else "Rp "
        if not result or not isinstance(result, dict):
            return ""

        if result.get("status") == "error":
            return f"⚠️ {result.get('message', 'Operation encountered an issue.')}"

        # 1. Full Financial Health Report
        if "report" in result:
            rep = result["report"]
            net = rep.get("net_worth", 0.0)
            inc = rep.get("income", 0.0)
            exp = rep.get("expense", 0.0)
            sav = rep.get("net_savings", 0.0)
            rate = rep.get("savings_rate", 0.0)
            month = rep.get("month", "")
            
            lines = [
                f"### 📊 Full Financial Health Report ({month})",
                f"| Metric | Amount ({currency}) |",
                f"| :--- | :--- |",
                f"| 💼 **Total Net Worth** | **{sym}{net:,.2f}** |",
                f"| 💵 **Monthly Inflow** | {sym}{inc:,.2f} |",
                f"| 💳 **Monthly Outflow** | {sym}{exp:,.2f} |",
                f"| 🏦 **Net Savings** | **{sym}{sav:,.2f}** |",
                f"| 📈 **Savings Rate** | **{rate:.1f}%** |"
            ]
            cats = rep.get("category_breakdown", {})
            if cats:
                lines.append("\n**Top Category Outflows:**")
                for c, a in sorted(cats.items(), key=lambda x: x[1], reverse=True)[:5]:
                    lines.append(f"- **{c}**: {sym}{a:,.2f}")
            rec = rep.get("recommendations", [])
            if rec:
                lines.append("\n**💡 Recommendations:**")
                for r in rec:
                    lines.append(f"- {r}")
            return "\n".join(lines)

        # 2. Monthly Summary
        if "total_income" in result and "total_expense" in result:
            inc = result.get("total_income", 0.0)
            exp = result.get("total_expense", 0.0)
            sav = result.get("net_savings", 0.0)
            rate = result.get("savings_rate_pct", 0.0)
            m = result.get("month_year", "")
            lines = [
                f"### 📈 Monthly Financial Summary ({m})",
                f"| Metric | Amount ({currency}) |",
                f"| :--- | :--- |",
                f"| 💵 **Income** | {sym}{inc:,.2f} |",
                f"| 💳 **Expense** | {sym}{exp:,.2f} |",
                f"| 🏦 **Net Savings** | **{sym}{sav:,.2f}** |",
                f"| 📊 **Savings Rate** | **{rate:.1f}%** |"
            ]
            return "\n".join(lines)

        # 3. Accounts & Balances
        if "accounts" in result:
            accs = result["accounts"]
            if not accs:
                return "You don't have any accounts set up yet."
            lines = [f"| **{a['name']}** | `{a['account_type']}` | **{a['currency']} {a['balance']:,.2f}** |" for a in accs]
            return "### 💳 Your Account Balances\n| Account | Type | Balance |\n| :--- | :--- | :--- |\n" + "\n".join(lines)

        # 4. Total Net Worth
        if "total_net_worth" in result:
            nw = result["total_net_worth"]
            lines = [f"### 💼 Total Net Worth: **{sym}{nw:,.2f} {currency}**\n"]
            if "accounts" in result and result["accounts"]:
                lines.append("| Account | Type | Balance | Converted |")
                lines.append("| :--- | :--- | :--- | :--- |")
                for a in result["accounts"]:
                    lines.append(f"| **{a['account_name']}** | `{a['account_type']}` | {a['currency']} {a['original_balance']:,.2f} | {sym}{a['converted_balance']:,.2f} |")
            return "\n".join(lines)

        # 5. Transactions
        if "transactions" in result:
            txs = result["transactions"]
            if not txs:
                return "No transactions found in this ledger."
            lines = [f"| {t['date']} | **{t['type'].upper()}** | {t['currency']} {t['amount']:,.2f} | {t['category']} | {t.get('merchant', '-')} |" for t in txs[:10]]
            return "### 📒 Recent Transactions\n| Date | Type | Amount | Category | Merchant |\n| :--- | :--- | :--- | :--- | :--- |\n" + "\n".join(lines)

        # 6. Budgets
        if "budgets" in result:
            bgs = result["budgets"]
            if not bgs:
                return "No budgets configured for this month."
            has_spent = any("spent" in b for b in bgs)
            if has_spent:
                lines = [
                    "### 🎯 Monthly Budget Status",
                    "| Category | Limit | Spent | Remaining | Burn Rate |",
                    "| :--- | :--- | :--- | :--- | :--- |"
                ]
                for b in bgs:
                    burn = b.get("burn_rate_pct", 0)
                    status_icon = "🟢" if burn < 75 else ("🟡" if burn < 100 else "🔴")
                    lines.append(f"| **{b['category']}** | {sym}{b['monthly_limit']:,.2f} | {sym}{b.get('spent', 0):,.2f} | {sym}{b.get('remaining', 0):,.2f} | {status_icon} {burn:.1f}% |")
            else:
                lines = [
                    "### 🎯 Monthly Budgets",
                    "| Category | Monthly Limit |",
                    "| :--- | :--- |"
                ]
                for b in bgs:
                    lines.append(f"| **{b['category']}** | {b['currency']} {b['monthly_limit']:,.2f} |")
            return "\n".join(lines)

        # 7. User Preferences
        if "preferences" in result:
            prefs = result["preferences"]
            lines = [f"- **{k}**: `{v}`" for k, v in prefs.items()]
            return "### ⚙️ User Profile & Preferences\n" + "\n".join(lines)

        if "message" in result:
            return f"✅ {result['message']}"

        return "✅ Done! Operation completed successfully."

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
