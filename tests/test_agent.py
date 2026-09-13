import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.agent import financial_agent
from core.prompts import format_system_prompt_with_context
from core.context_manager import context_manager

class TestAgentCore(unittest.TestCase):
    def test_xml_tag_extraction(self):
        sample_output = """
        <scratchpad>
        Reasoning about user request...
        </scratchpad>
        <message>
        Recorded your $20 expense!
        </message>
        """
        scratchpad = financial_agent._extract_xml_tag(sample_output, "scratchpad")
        message = financial_agent._extract_xml_tag(sample_output, "message")

        self.assertEqual(scratchpad, "Reasoning about user request...")
        self.assertEqual(message, "Recorded your $20 expense!")

    def test_hitl_intent_detection(self):
        # Expense in USD
        intent_usd = financial_agent._detect_hitl_intent("Spent $45 on groceries at Trader Joe's", None, "USD")
        self.assertIsNotNone(intent_usd)
        self.assertEqual(intent_usd["amount"], 45.0)
        self.assertEqual(intent_usd["currency"], "USD")
        self.assertEqual(intent_usd["type"], "expense")

        # Expense in IDR
        intent_idr = financial_agent._detect_hitl_intent("Beli kopi 50k di Kopi Kenangan", None, "IDR")
        self.assertIsNotNone(intent_idr)
        self.assertEqual(intent_idr["amount"], 50000.0)
        self.assertEqual(intent_idr["currency"], "IDR")

    def test_system_prompt_grounding(self):
        snapshot = context_manager.get_live_context_snapshot("USD")
        prompt = format_system_prompt_with_context(snapshot)
        self.assertIn("<context>", prompt)
        self.assertIn("<role>", prompt)
        self.assertIn("MoneyChingu", prompt)

    def test_tool_response_formatting_delivery(self):
        # 1. Accounts formatting
        acc_result = {"status": "success", "accounts": [{"name": "Cash Wallet", "account_type": "cash", "currency": "USD", "balance": 250.0}]}
        acc_fmt = financial_agent._format_tool_response("data_management", acc_result, "USD")
        self.assertIn("Your Account Balances", acc_fmt)
        self.assertIn("Cash Wallet", acc_fmt)
        self.assertIn("250.00", acc_fmt)

        # 2. Full report formatting
        rep_result = {
            "status": "success",
            "report": {
                "month": "2026-09",
                "net_worth": 1200.0,
                "income": 3000.0,
                "expense": 1500.0,
                "net_savings": 1500.0,
                "savings_rate": 50.0
            }
        }
        rep_fmt = financial_agent._format_tool_response("financial_analytics", rep_result, "USD")
        self.assertIn("Full Financial Health Report", rep_fmt)
        self.assertIn("3,000.00", rep_fmt)
        self.assertIn("1,500.00", rep_fmt)

    def test_preference_intent_detection(self):
        from database.db import db
        financial_agent._detect_preference_intent("My name is Alex and your name is Jarvis")
        self.assertEqual(db.get_preference("user_name"), "Alex")
        self.assertEqual(db.get_preference("ai_name"), "Jarvis")

    def test_destructive_action_permission_gate(self):
        # 1. Test _is_destructive_action recognition
        destructive_call = {"skill": "data_management", "parameters": {"action": "clear_database"}}
        safe_call = {"skill": "data_management", "parameters": {"action": "get_accounts"}}
        self.assertTrue(financial_agent._is_destructive_action(destructive_call))
        self.assertFalse(financial_agent._is_destructive_action(safe_call))

        # 2. Test _detect_destructive_intent for prompts like "remove all history transactions"
        res1 = financial_agent._detect_destructive_intent("remove all history transactions")
        self.assertIsNotNone(res1)
        self.assertEqual(res1["type"], "destructive_confirmation")
        self.assertEqual(res1["action"], "clear_database")

        res2 = financial_agent._detect_destructive_intent("hapus semua riwayat transaksi")
        self.assertIsNotNone(res2)
        self.assertEqual(res2["type"], "destructive_confirmation")

        # 3. Test non-destructive prompt does not trigger destructive confirmation
        res3 = financial_agent._detect_destructive_intent("List my balance")
        self.assertIsNone(res3)

    def test_destructive_prompt_triggers_hitl_permission(self):
        turn_res = financial_agent.process_user_turn(
            user_message="remove all history transactions",
            conversation_history=[]
        )
        self.assertIsNotNone(turn_res.get("hitl_pending"))
        self.assertEqual(turn_res["hitl_pending"]["type"], "destructive_confirmation")
        self.assertIn("Action Permission Required", turn_res["message"])

if __name__ == "__main__":
    unittest.main()
