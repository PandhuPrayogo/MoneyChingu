import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import contextmanager
import sys

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DB_PATH, USD_TO_IDR_RATE

class DatabaseManager:
    """
    SQLite Database Manager for Financial Ledger, Accounts, and Budgets.
    Thread-safe connection handling with guaranteed connection closing.
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema tables."""
        with self._connection() as conn:
            cursor = conn.cursor()
            
            # Accounts Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    account_type TEXT NOT NULL, -- 'cash', 'bank', 'e_wallet', 'credit_card'
                    currency TEXT NOT NULL DEFAULT 'USD', -- 'USD' or 'IDR'
                    balance REAL NOT NULL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Transactions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL, -- 'YYYY-MM-DD'
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    type TEXT NOT NULL, -- 'expense', 'income', 'transfer'
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    account_id TEXT,
                    merchant TEXT,
                    description TEXT,
                    raw_source TEXT DEFAULT 'manual', -- 'manual', 'receipt_image', 'pdf_statement', 'csv'
                    status TEXT DEFAULT 'confirmed', -- 'pending_review', 'confirmed', 'discarded'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(account_id) REFERENCES accounts(id)
                );
            """)

            # Budgets Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    monthly_limit REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    month_year TEXT NOT NULL, -- 'YYYY-MM'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, month_year, currency)
                );
            """)

            # Audit / Activity Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Semantic / RAG Documents Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS semantic_documents (
                    id TEXT PRIMARY KEY,
                    reference_id TEXT,
                    doc_type TEXT NOT NULL, -- 'receipt', 'transaction', 'note'
                    content TEXT NOT NULL,
                    embedding_json TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    # ================= ACCOUNTS MANAGEMENT ================= #

    def add_account(self, name: str, account_type: str, currency: str = "USD", initial_balance: float = 0.0) -> str:
        account_id = f"acc_{uuid.uuid4().hex[:8]}"
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounts (id, name, account_type, currency, balance)
                VALUES (?, ?, ?, ?, ?)
            """, (account_id, name, account_type, currency.upper(), initial_balance))
        return account_id

    def get_accounts(self) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts ORDER BY name ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_account_balance(self, account_id: str, amount_delta: float):
        """Update account balance by delta (positive for income, negative for expense)."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts SET balance = balance + ? WHERE id = ?
            """, (amount_delta, account_id))

    # ================= TRANSACTIONS MANAGEMENT ================= #

    def add_transaction(self, 
                        date: str, 
                        amount: float, 
                        category: str, 
                        currency: str = "USD", 
                        tx_type: str = "expense", 
                        account_id: Optional[str] = None, 
                        merchant: Optional[str] = None, 
                        description: Optional[str] = None, 
                        subcategory: Optional[str] = None,
                        raw_source: str = "manual", 
                        status: str = "confirmed") -> str:
        
        tx_id = f"tx_{uuid.uuid4().hex[:8]}"
        currency = currency.upper()
        
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions 
                (id, date, amount, currency, type, category, subcategory, account_id, merchant, description, raw_source, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (tx_id, date, amount, currency, tx_type, category, subcategory, account_id, merchant, description, raw_source, status))
            
            # If confirmed and account provided, update account balance
            if status == "confirmed" and account_id:
                multiplier = 1.0 if tx_type == "income" else -1.0
                cursor.execute("""
                    UPDATE accounts SET balance = balance + ? WHERE id = ?
                """, (amount * multiplier, account_id))
                
            # Log action
            cursor.execute("""
                INSERT INTO audit_logs (id, action, details)
                VALUES (?, ?, ?)
            """, (f"log_{uuid.uuid4().hex[:8]}", "ADD_TRANSACTION", f"Added {tx_type} of {amount} {currency} ({category})"))
            
        return tx_id

    def get_transactions(self, limit: int = 100, status: str = "confirmed", category: Optional[str] = None, month: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT t.*, a.name as account_name 
                FROM transactions t
                LEFT JOIN accounts a ON t.account_id = a.id
                WHERE t.status = ?
            """
            params: List[Any] = [status]
            
            if category:
                query += " AND t.category = ?"
                params.append(category)
            if month:
                query += " AND t.date LIKE ?"
                params.append(f"{month}%")
                
            query += " ORDER BY t.date DESC, t.created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_transaction(self, tx_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.cursor()
            # Fetch tx first to reverse balance
            cursor.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
            tx = cursor.fetchone()
            if not tx:
                return False
                
            tx_dict = dict(tx)
            if tx_dict["status"] == "confirmed" and tx_dict["account_id"]:
                multiplier = -1.0 if tx_dict["type"] == "income" else 1.0
                cursor.execute("""
                    UPDATE accounts SET balance = balance + ? WHERE id = ?
                """, (tx_dict["amount"] * multiplier, tx_dict["account_id"]))
                
            cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
            return True

    # ================= BUDGETS MANAGEMENT ================= #

    def set_budget(self, category: str, monthly_limit: float, currency: str = "USD", month_year: Optional[str] = None) -> str:
        if not month_year:
            month_year = datetime.now().strftime("%Y-%m")
        budget_id = f"bg_{uuid.uuid4().hex[:8]}"
        currency = currency.upper()
        
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO budgets (id, category, monthly_limit, currency, month_year)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(category, month_year, currency) DO UPDATE SET
                monthly_limit = excluded.monthly_limit
            """, (budget_id, category, monthly_limit, currency, month_year))
        return budget_id

    def get_budgets(self, month_year: Optional[str] = None) -> List[Dict[str, Any]]:
        if not month_year:
            month_year = datetime.now().strftime("%Y-%m")
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM budgets WHERE month_year = ? ORDER BY category ASC", (month_year,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # ================= AGGREGATIONS & SUMMARY ================= #

    def get_monthly_summary(self, month_year: Optional[str] = None, display_currency: str = "USD") -> Dict[str, Any]:
        """
        Calculate total income, expenses, net savings, and category breakdown for a given month.
        Converts between USD and IDR as needed for unified display.
        """
        if not month_year:
            month_year = datetime.now().strftime("%Y-%m")
            
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT type, category, amount, currency
                FROM transactions
                WHERE date LIKE ? AND status = 'confirmed'
            """, (f"{month_year}%",))
            rows = cursor.fetchall()
            
        total_income = 0.0
        total_expense = 0.0
        category_breakdown: Dict[str, float] = {}
        
        for r in rows:
            amount = r["amount"]
            curr = r["currency"]
            # Convert to display currency if needed
            converted_amount = amount
            if display_currency == "USD" and curr == "IDR":
                converted_amount = amount / USD_TO_IDR_RATE
            elif display_currency == "IDR" and curr == "USD":
                converted_amount = amount * USD_TO_IDR_RATE
                
            tx_type = r["type"]
            cat = r["category"]
            
            if tx_type == "income":
                total_income += converted_amount
            elif tx_type == "expense":
                total_expense += converted_amount
                category_breakdown[cat] = category_breakdown.get(cat, 0.0) + converted_amount
                
        net_savings = total_income - total_expense
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0
        
        return {
            "month_year": month_year,
            "currency": display_currency,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_savings": net_savings,
            "savings_rate_pct": round(savings_rate, 1),
            "category_breakdown": category_breakdown
        }

    def clear_all_data(self, create_default_empty_accounts: bool = True):
        """Reset all tables in database to clean zero state."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions;")
            cursor.execute("DELETE FROM budgets;")
            cursor.execute("DELETE FROM audit_logs;")
            cursor.execute("DELETE FROM semantic_documents;")
            cursor.execute("DELETE FROM accounts;")
            
            if create_default_empty_accounts:
                # Create clean zero-balance accounts
                cursor.execute("""
                    INSERT INTO accounts (id, name, account_type, currency, balance) VALUES
                    ('acc_cash_usd', 'Cash (USD)', 'cash', 'USD', 0.0),
                    ('acc_bank_usd', 'Checking Bank (USD)', 'bank', 'USD', 0.0),
                    ('acc_gopay_idr', 'GoPay / E-Wallet (IDR)', 'e_wallet', 'IDR', 0.0),
                    ('acc_bank_idr', 'Bank Account (IDR)', 'bank', 'IDR', 0.0);
                """)
                cursor.execute("""
                    INSERT INTO audit_logs (id, action, details)
                    VALUES ('log_init', 'DATABASE_RESET', 'Database reset to zero state.');
                """)

    def get_total_balance_summary(self, display_currency: str = "USD") -> Dict[str, Any]:
        """Compute aggregated net worth across all accounts."""
        accounts = self.get_accounts()
        total_net_worth = 0.0
        breakdown = []
        
        for acc in accounts:
            bal = acc["balance"]
            curr = acc["currency"]
            conv = bal
            if display_currency == "USD" and curr == "IDR":
                conv = bal / USD_TO_IDR_RATE
            elif display_currency == "IDR" and curr == "USD":
                conv = bal * USD_TO_IDR_RATE
                
            total_net_worth += conv
            breakdown.append({
                "account_name": acc["name"],
                "account_type": acc["account_type"],
                "original_balance": bal,
                "currency": curr,
                "converted_balance": conv
            })
            
        return {
            "display_currency": display_currency,
            "total_net_worth": total_net_worth,
            "accounts": breakdown
        }

# Global singleton
db = DatabaseManager()
