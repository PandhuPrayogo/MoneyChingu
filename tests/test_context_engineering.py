import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.intent_router import intent_router
from core.context_manager import context_manager
from core.memory_store import memory_store
from core.prompts import build_system_prompt, AUTHORITY_BLOCK
from core.agent import financial_agent
from database.db import db

class TestContextEngineering(unittest.TestCase):
    """
    Unit Tests for 4-Pillar Context Engineering Architecture:
    1. WRITE: External State Persistence (MemoryStore & SQLite)
    2. SELECT: JIT Context Assembly & Dynamic Tool RAG (IntentRouter)
    3. COMPRESS: Token Pruning & Lifecycle Eviction (ContextManager)
    4. ISOLATE: Anti-Poisoning Validation & Authority Ordering
    """

    def setUp(self):
        db.clear_memories()

    # ================= 1. WRITE: EXTERNAL STATE PERSISTENCE ================= #

    def test_typed_memory_store_and_retrieve(self):
        # Store episodic
        ep_id = memory_store.store_episodic("get_accounts", "User checked balances. 4 accounts found.")
        self.assertTrue(ep_id.startswith("mem_"))

        # Store semantic
        sem_id = memory_store.store_semantic("User prefers IDR for daily transactions", category="currency")
        self.assertTrue(sem_id.startswith("mem_"))

        # Store procedural
        proc_id = memory_store.store_procedural("Always include category breakdown in monthly reports")
        self.assertTrue(proc_id.startswith("mem_"))

        # Retrieve semantic
        sem_memories = memory_store.retrieve_memories(query="currency", memory_types=["semantic"], top_k=2)
        self.assertTrue(any("IDR" in m["content"] for m in sem_memories))

        # Format memories for prompt
        formatted = memory_store.format_memories_for_prompt(sem_memories)
        self.assertIn("<memories>", formatted)
        self.assertIn("[SEMANTIC]", formatted)

    def test_memory_eviction_preserves_procedural_rules(self):
        memory_store.store_episodic("old_action", "Old episodic data from past week")
        memory_store.store_procedural("Never hallucinate credit card balances")

        # Evicting with max_age_days = 0 should remove episodic but preserve procedural
        evicted_count = memory_store.evict_stale(max_age_days=0)
        procedural_mems = db.get_memories_by_type("procedural")
        self.assertGreaterEqual(len(procedural_mems), 1)
        self.assertEqual(procedural_mems[0]["content"], "Never hallucinate credit card balances")

    # ================= 2. SELECT: JIT ASSEMBLY & DYNAMIC TOOL RAG ================= #

    def test_bilingual_intent_classification(self):
        # English queries
        intents_en1 = intent_router.classify_intent("How much money is left in my bank account?")
        self.assertIn("query_balance", intents_en1)

        intents_en2 = intent_router.classify_intent("I spent $45 on dinner at Chipotle")
        self.assertIn("add_expense", intents_en2)

        intents_en3 = intent_router.classify_intent("Give me my monthly financial health report")
        self.assertIn("financial_report", intents_en3)

        # Indonesian queries
        intents_id1 = intent_router.classify_intent("Tolong cek sisa saldo rekening saya")
        self.assertIn("query_balance", intents_id1)

        intents_id2 = intent_router.classify_intent("Kemarin beli bensin 50rb di Pertamina")
        self.assertIn("add_expense", intents_id2)

        intents_id3 = intent_router.classify_intent("Tampilkan laporan evaluasi keuangan bulan ini")
        self.assertIn("financial_report", intents_id3)

    def test_dynamic_tool_pruning_reduces_schemas(self):
        # Check balances intent: only balance tools should be injected, NOT delete_account or transfer
        intents = ["query_balance"]
        candidate_tools = intent_router.get_candidate_tools(intents)
        self.assertLessEqual(len(candidate_tools), 4)
        self.assertTrue(any("get_accounts" in t for t in candidate_tools))
        self.assertFalse(any("delete_account" in t for t in candidate_tools))

        # Financial report intent: only reporting tools injected
        rep_intents = ["financial_report"]
        rep_tools = intent_router.get_candidate_tools(rep_intents)
        self.assertTrue(any("generate_full_report" in t for t in rep_tools))
        self.assertFalse(any("delete_transaction" in t for t in rep_tools))

    # ================= 3. COMPRESS: TOKEN PRUNING & EVICTION ================= #

    def test_pre_injection_pruning_strips_scratchpads(self):
        bloated_history = [
            {"role": "user", "content": "Check my balance"},
            {
                "role": "assistant",
                "content": "<scratchpad>Need to inspect bank balances in SQLite</scratchpad>\nHere is your balance: $500"
            }
        ]
        pruned = context_manager.prepare_history_for_injection(bloated_history)
        self.assertEqual(len(pruned), 2)
        self.assertNotIn("<scratchpad>", pruned[1]["content"])
        self.assertIn("Here is your balance: $500", pruned[1]["content"])

    def test_rolling_conversation_summarizer(self):
        # Create a conversation with 12 turns (24 messages)
        long_history = []
        for i in range(10):
            long_history.append({"role": "user", "content": f"Logged expense #{i}"})
            long_history.append({"role": "assistant", "content": f"Confirmed and saved EXPENSE: USD {i*10:.2f} for Groceries."})

        # Recent verbatim is 4 turns (8 msgs), older turns (16 msgs) should be summarized
        summary = context_manager.get_conversation_summary(long_history)
        self.assertIn("<conversation_summary>", summary)
        self.assertIn("System logged:", summary)

    def test_post_action_eviction(self):
        huge_table = "### 💳 Your Account Balances\n| Account | Type | Balance |\n| Cash | cash | $500 |\n| Bank | bank | $2000 |"
        condensed = context_manager.evict_tool_output(huge_table)
        self.assertEqual(condensed, "💳 [Displayed live account balances]")

    # ================= 4. ISOLATE & ANTI-PATTERNS ================= #

    def test_anti_context_poisoning_validation(self):
        # Invalid JSON / non-dict
        valid, err, payload = financial_agent._parse_and_validate_tool_call("not a json string")
        self.assertFalse(valid)
        self.assertIn("Malformed JSON", err)

        # Missing skill
        valid, err, payload = financial_agent._parse_and_validate_tool_call('{"parameters": {}}')
        self.assertFalse(valid)
        self.assertIn("Missing 'skill'", err)

        # Unknown skill name
        valid, err, payload = financial_agent._parse_and_validate_tool_call('{"skill": "hack_system", "parameters": {}}')
        self.assertFalse(valid)
        self.assertIn("Unknown skill", err)

        # Valid payload
        valid, err, payload = financial_agent._parse_and_validate_tool_call('{"skill": "data_management", "parameters": {"action": "get_accounts"}}')
        self.assertTrue(valid)
        self.assertIsNone(err)
        self.assertEqual(payload["skill"], "data_management")

    def test_anti_context_clash_authority_hierarchy(self):
        self.assertIn("<authority>", AUTHORITY_BLOCK)
        self.assertIn("1. <rules>", AUTHORITY_BLOCK)
        self.assertIn("2. <context>", AUTHORITY_BLOCK)
        self.assertIn("3. <user_profile>", AUTHORITY_BLOCK)
        self.assertIn("4. <memories>", AUTHORITY_BLOCK)
        self.assertIn("5. <conversation_summary>", AUTHORITY_BLOCK)

        # Build sample prompt
        prompt = build_system_prompt(
            context_snapshot={"accounts": [], "recent_transactions": [], "monthly_summary": {}, "user_preferences": {"user_name": "Pandhu"}},
            candidate_tools=["- data_management: action='get_accounts'"],
            conversation_summary="<conversation_summary>- User logged spending</conversation_summary>"
        )
        self.assertIn("<authority>", prompt)
        self.assertIn("User Name: Pandhu", prompt)
        self.assertIn("<conversation_summary>", prompt)

if __name__ == "__main__":
    unittest.main()
