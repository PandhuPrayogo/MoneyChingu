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
        self.assertIn("<live_financial_context>", prompt)
        self.assertIn("<system_role>", prompt)
        self.assertIn("MoneyBuddy", prompt)

if __name__ == "__main__":
    unittest.main()
