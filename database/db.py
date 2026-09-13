import sqlite3
import uuid
import json
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

            # User Preferences / Profile Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Persistent Chat History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL DEFAULT 'default',
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Agent Memory Table (Context Engineering: Episodic, Semantic, Procedural)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL, -- 'episodic', 'semantic', 'procedural'
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0
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

    def delete_account(self, account_id: str) -> bool:
        """Delete an account and optionally cascade delete or nullify transactions."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("UPDATE transactions SET account_id = NULL WHERE account_id = ?", (account_id,))
            cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            return True

    def transfer_funds(self, from_account_id: str, to_account_id: str, amount: float, currency: str = "USD", description: str = "Fund Transfer") -> Dict[str, Any]:
        """Transfer money between two accounts with balance reconciliation."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._connection() as conn:
            cursor = conn.cursor()
            # Deduct from source
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
            # Add to destination
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))
            
            # Record outgoing transfer transaction
            tx1 = f"tx_{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO transactions (id, date, amount, currency, type, category, account_id, description, status)
                VALUES (?, ?, ?, ?, 'transfer', 'Transfer Out', ?, ?, 'confirmed')
            """, (tx1, today, amount, currency, from_account_id, f"Transfer to {to_account_id}: {description}"))
            
            # Record incoming transfer transaction
            tx2 = f"tx_{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO transactions (id, date, amount, currency, type, category, account_id, description, status)
                VALUES (?, ?, ?, ?, 'transfer', 'Transfer In', ?, ?, 'confirmed')
            """, (tx2, today, amount, currency, to_account_id, f"Transfer from {from_account_id}: {description}"))
            
            return {"status": "success", "from_tx": tx1, "to_tx": tx2, "message": f"Transferred {amount:,.2f} {currency} successfully."}

    def edit_transaction(self, tx_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Edit fields of an existing transaction and update account balances if amount/type/account changed."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
            old_tx = cursor.fetchone()
            if not old_tx:
                return None
            old = dict(old_tx)
            
            # Revert old balance
            if old["status"] == "confirmed" and old["account_id"]:
                old_mult = -1.0 if old["type"] == "income" else 1.0
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (old["amount"] * old_mult, old["account_id"]))
                
            new_amount = float(updates.get("amount", old["amount"]))
            new_type = updates.get("type", old["type"])
            new_category = updates.get("category", old["category"])
            new_merchant = updates.get("merchant", old["merchant"])
            new_desc = updates.get("description", old["description"])
            new_date = updates.get("date", old["date"])
            new_acc_id = updates.get("account_id", old["account_id"])
            new_curr = updates.get("currency", old["currency"]).upper()
            
            cursor.execute("""
                UPDATE transactions 
                SET amount = ?, type = ?, category = ?, merchant = ?, description = ?, date = ?, account_id = ?, currency = ?
                WHERE id = ?
            """, (new_amount, new_type, new_category, new_merchant, new_desc, new_date, new_acc_id, new_curr, tx_id))
            
            # Apply new balance
            if new_acc_id:
                new_mult = 1.0 if new_type == "income" else -1.0
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (new_amount * new_mult, new_acc_id))
                
            return {
                "id": tx_id,
                "amount": new_amount,
                "type": new_type,
                "category": new_category,
                "merchant": new_merchant,
                "description": new_desc,
                "date": new_date,
                "currency": new_curr
            }

    def search_transactions(self, query_text: Optional[str] = None, category: Optional[str] = None, 
                            min_amount: Optional[float] = None, max_amount: Optional[float] = None,
                            start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Filter and search transactions with multi-field queries."""
        with self._connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT t.*, a.name as account_name FROM transactions t LEFT JOIN accounts a ON t.account_id = a.id WHERE 1=1"
            params: List[Any] = []
            
            if query_text:
                sql += " AND (t.merchant LIKE ? OR t.description LIKE ? OR t.category LIKE ?)"
                kw = f"%{query_text}%"
                params.extend([kw, kw, kw])
            if category:
                sql += " AND t.category = ?"
                params.append(category)
            if min_amount is not None:
                sql += " AND t.amount >= ?"
                params.append(min_amount)
            if max_amount is not None:
                sql += " AND t.amount <= ?"
                params.append(max_amount)
            if start_date:
                sql += " AND t.date >= ?"
                params.append(start_date)
            if end_date:
                sql += " AND t.date <= ?"
                params.append(end_date)
                
            sql += " ORDER BY t.date DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

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
            cursor.execute("DELETE FROM chat_history;")
            cursor.execute("DELETE FROM user_preferences;")
            cursor.execute("DELETE FROM agent_memory;")
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

    # ================= USER PREFERENCES & IDENTITY ================= #

    def set_preference(self, key: str, value: str) -> None:
        """Store or update a user preference key-value pair."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP;
            """, (key, value))

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a specific user preference value."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = ?;", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def get_all_preferences(self) -> Dict[str, str]:
        """Return all user preferences as a key-value dictionary."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_preferences;")
            rows = cursor.fetchall()
            return {r["key"]: r["value"] for r in rows}

    # ================= PERSISTENT CHAT HISTORY ================= #

    def save_chat_message(self, role: str, content: str, session_id: str = "default") -> None:
        """Persist a chat message to the database."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_history (session_id, role, content)
                VALUES (?, ?, ?);
            """, (session_id, role, content))

    def get_chat_history(self, session_id: str = "default", limit: int = 50) -> List[Dict[str, str]]:
        """Retrieve recent chat history ordered chronologically."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content FROM chat_history
                WHERE session_id = ?
                ORDER BY id ASC
                LIMIT ?;
            """, (session_id, limit))
            rows = cursor.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in rows]

    def clear_chat_history(self, session_id: str = "default") -> None:
        """Clear chat messages for a specific session."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history WHERE session_id = ?;", (session_id,))

    # ================= AGENT MEMORY (CONTEXT ENGINEERING) ================= #

    def store_memory(self, memory_type: str, content: str, metadata: Optional[Dict[str, Any]] = None, mem_id: Optional[str] = None) -> str:
        """Persist typed memory (episodic, semantic, or procedural) into SQLite."""
        memory_id = mem_id or f"mem_{uuid.uuid4().hex[:8]}"
        meta_json = json.dumps(metadata or {})
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_memory (id, memory_type, content, metadata_json, accessed_at, access_count)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    metadata_json = excluded.metadata_json,
                    accessed_at = CURRENT_TIMESTAMP,
                    access_count = access_count + 1;
            """, (memory_id, memory_type, content, meta_json))
        return memory_id

    def get_memories_by_type(self, memory_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent memories filtered by type."""
        with self._connection() as conn:
            cursor = conn.cursor()
            if memory_type:
                cursor.execute("""
                    SELECT id, memory_type, content, metadata_json, created_at, accessed_at, access_count
                    FROM agent_memory
                    WHERE memory_type = ?
                    ORDER BY accessed_at DESC
                    LIMIT ?;
                """, (memory_type, limit))
            else:
                cursor.execute("""
                    SELECT id, memory_type, content, metadata_json, created_at, accessed_at, access_count
                    FROM agent_memory
                    ORDER BY accessed_at DESC
                    LIMIT ?;
                """, (limit,))
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "memory_type": r["memory_type"],
                    "content": r["content"],
                    "metadata": json.loads(r["metadata_json"] or "{}"),
                    "created_at": r["created_at"],
                    "accessed_at": r["accessed_at"],
                    "access_count": r["access_count"]
                }
                for r in rows
            ]

    def search_memories(self, query: str, memory_types: Optional[List[str]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Keyword search over stored memories with access tracking."""
        tokens = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]
        all_memories = self.get_memories_by_type(limit=100)
        
        filtered = []
        for mem in all_memories:
            if memory_types and mem["memory_type"] not in memory_types:
                continue
            content_lower = mem["content"].lower()
            match_score = sum(1 for t in tokens if t in content_lower)
            if match_score > 0 or not tokens:
                mem["relevance_score"] = match_score
                filtered.append(mem)

        filtered.sort(key=lambda x: (x.get("relevance_score", 0), x.get("accessed_at", "")), reverse=True)
        top_results = filtered[:limit]

        # Touch matched memories
        for r in top_results:
            self.touch_memory(r["id"])

        return top_results

    def touch_memory(self, memory_id: str) -> None:
        """Update last accessed timestamp and increment access count."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_memory
                SET accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE id = ?;
            """, (memory_id,))

    def evict_stale_memories(self, max_age_days: int = 30) -> int:
        """Evict memories older than max_age_days (except procedural rules)."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM agent_memory
                WHERE memory_type != 'procedural'
                AND julianday('now') - julianday(created_at) > ?;
            """, (max_age_days,))
            return cursor.rowcount

    def clear_memories(self) -> None:
        """Wipe all agent memories."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM agent_memory;")

# Global singleton
db = DatabaseManager()
