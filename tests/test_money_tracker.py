import os
import sys
import unittest
import uuid
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from database.db import DatabaseManager
from database.vector_store import VectorStore
from skills import data_management_skill, financial_analytics_skill, rag_context_skill, hf_skill
from config import USD_TO_IDR_RATE

class TestMoneyTracker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        unique_id = uuid.uuid4().hex[:6]
        cls.test_db_path = BASE_DIR / "data" / f"test_tracker_{unique_id}.db"
        cls.test_vec_path = BASE_DIR / "data" / f"test_vec_{unique_id}.json"
        cls.db = DatabaseManager(db_path=cls.test_db_path)
        cls.vector_store = VectorStore(storage_path=cls.test_vec_path)

    @classmethod
    def tearDownClass(cls):
        if cls.test_db_path.exists():
            try:
                cls.test_db_path.unlink()
            except Exception:
                pass
        if cls.test_vec_path.exists():
            try:
                cls.test_vec_path.unlink()
            except Exception:
                pass

    def test_account_creation_and_balance_update(self):
        acc_id = self.db.add_account("Test Bank USD", "bank", "USD", 1000.0)
        self.assertTrue(acc_id.startswith("acc_"))
        
        acc = self.db.get_account_by_id(acc_id)
        self.assertEqual(acc["balance"], 1000.0)
        self.assertEqual(acc["currency"], "USD")

    def test_transaction_crud_and_balance_reconciliation(self):
        acc_id = self.db.add_account("Checking USD", "bank", "USD", 500.0)
        
        # Add expense of $50
        tx_id = self.db.add_transaction(
            date="2026-08-31",
            amount=50.0,
            category="Food & Dining",
            currency="USD",
            tx_type="expense",
            account_id=acc_id,
            merchant="Super Burger"
        )
        self.assertTrue(tx_id.startswith("tx_"))
        
        acc = self.db.get_account_by_id(acc_id)
        self.assertEqual(acc["balance"], 450.0)

        # Add income of $200
        tx_inc_id = self.db.add_transaction(
            date="2026-08-31",
            amount=200.0,
            category="Freelance / Gig",
            currency="USD",
            tx_type="income",
            account_id=acc_id,
            merchant="Client XYZ"
        )
        acc = self.db.get_account_by_id(acc_id)
        self.assertEqual(acc["balance"], 650.0)

        # Delete income transaction -> should revert balance to 450.0
        deleted = self.db.delete_transaction(tx_inc_id)
        self.assertTrue(deleted)
        acc = self.db.get_account_by_id(acc_id)
        self.assertEqual(acc["balance"], 450.0)

    def test_budget_setting_and_burn_rate(self):
        self.db.set_budget("Food & Dining", 200.0, currency="USD", month_year="2026-08")
        budgets = self.db.get_budgets("2026-08")
        self.assertEqual(len(budgets), 1)
        self.assertEqual(budgets[0]["monthly_limit"], 200.0)

    def test_currency_conversion(self):
        res = financial_analytics_skill.execute(
            analysis_type="convert_currency",
            amount=10.0,
            from_currency="USD",
            to_currency="IDR"
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["converted_amount"], 10.0 * USD_TO_IDR_RATE)

    def test_vector_store_rag(self):
        doc_id = self.vector_store.add_document(
            text="Sushi dinner at Tokyo Japanese restaurant 35 USD",
            metadata={"merchant": "Tokyo Japanese", "category": "Food & Dining"},
            doc_type="receipt"
        )
        self.assertTrue(doc_id.startswith("doc_"))
        
        results = self.vector_store.search("sushi dinner", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], doc_id)

    def test_huggingface_categorization(self):
        res = hf_skill.execute(task="categorize_text", text="Purchased hot cappuccino at Starbucks cafe")
        self.assertEqual(res["suggested_category"], "Food & Dining")

if __name__ == "__main__":
    unittest.main()
