from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd

from skills.base import BaseSkill
from database.db import db
from database.vector_store import vector_store

class DataManagementSkill(BaseSkill):
    """
    Data Management Skill: Responsible for direct CRUD operations on the SQLite ledger,
    updating account balances, and recording RAG embeddings for new entries.
    """
    name = "data_management"
    description = "Executes transactions creation, balance reconciliation, deletions, and ledger exports in SQLite."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "add_transaction", "delete_transaction", "edit_transaction", "list_transactions", "search_transactions",
                    "get_accounts", "add_account", "delete_account", "transfer_funds",
                    "set_budget", "get_budgets", "clear_database", "export_csv"
                ],
                "description": "The data management action to execute"
            },
            "date": {"type": "string", "description": "Date in YYYY-MM-DD"},
            "amount": {"type": "number", "description": "Transaction amount"},
            "currency": {"type": "string", "enum": ["USD", "IDR"], "description": "Transaction currency"},
            "category": {"type": "string", "description": "Expense or Income category"},
            "type": {"type": "string", "enum": ["expense", "income", "transfer"], "description": "Transaction type"},
            "account_id": {"type": "string", "description": "Target account ID"},
            "from_account_id": {"type": "string", "description": "Source account ID for fund transfers"},
            "to_account_id": {"type": "string", "description": "Destination account ID for fund transfers"},
            "account_name": {"type": "string", "description": "Account name (e.g. Cash, PayPal)"},
            "account_type": {"type": "string", "enum": ["cash", "bank", "e_wallet", "credit_card"], "description": "Type of account"},
            "monthly_limit": {"type": "number", "description": "Budget monthly limit"},
            "merchant": {"type": "string", "description": "Payee or merchant name"},
            "description": {"type": "string", "description": "Additional notes or search query"},
            "tx_id": {"type": "string", "description": "Transaction ID for deletion or editing"},
            "query": {"type": "string", "description": "Search keyword for merchant/description"}
        },
        "required": ["action"]
    }

    def execute(self, **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action")
        
        if action == "add_transaction":
            return self._add_transaction(kwargs)
        elif action == "delete_transaction":
            return self._delete_transaction(kwargs)
        elif action == "edit_transaction":
            tx_id = kwargs.get("tx_id")
            if not tx_id:
                return {"status": "error", "message": "tx_id is required to edit a transaction."}
            res = db.edit_transaction(tx_id, **kwargs)
            if res:
                return {"status": "success", "message": f"Updated transaction {tx_id}.", "transaction": res}
            return {"status": "error", "message": f"Transaction {tx_id} not found."}
        elif action == "list_transactions":
            return self._list_transactions(kwargs)
        elif action == "search_transactions":
            q = kwargs.get("query") or kwargs.get("description") or kwargs.get("merchant")
            cat = kwargs.get("category")
            min_a = kwargs.get("min_amount")
            max_a = kwargs.get("max_amount")
            results = db.search_transactions(query_text=q, category=cat, min_amount=min_a, max_amount=max_a)
            return {"status": "success", "count": len(results), "transactions": results}
        elif action == "get_accounts":
            return {"status": "success", "accounts": db.get_accounts()}
        elif action == "add_account":
            name = kwargs.get("account_name") or "New Account"
            acc_type = kwargs.get("account_type") or "bank"
            curr = (kwargs.get("currency") or "USD").upper()
            bal = float(kwargs.get("amount") or kwargs.get("balance") or 0.0)
            acc_id = db.add_account(name=name, account_type=acc_type, currency=curr, initial_balance=bal)
            return {"status": "success", "account_id": acc_id, "message": f"Created account '{name}' ({acc_type}, {curr}) with balance {bal:,.2f}."}
        elif action == "delete_account":
            acc_id = kwargs.get("account_id")
            if not acc_id:
                return {"status": "error", "message": "account_id required."}
            ok = db.delete_account(acc_id)
            return {"status": "success", "message": f"Account {acc_id} deleted."} if ok else {"status": "error", "message": "Account not found."}
        elif action == "transfer_funds":
            from_id = kwargs.get("from_account_id")
            to_id = kwargs.get("to_account_id")
            amt = float(kwargs.get("amount", 0.0))
            curr = kwargs.get("currency", "USD")
            desc = kwargs.get("description", "Transfer")
            if not from_id or not to_id or amt <= 0:
                return {"status": "error", "message": "from_account_id, to_account_id, and positive amount required."}
            return db.transfer_funds(from_id, to_id, amt, curr, desc)
        elif action == "set_budget":
            cat = kwargs.get("category") or "Food & Dining"
            limit = float(kwargs.get("monthly_limit") or kwargs.get("amount") or 100.0)
            curr = (kwargs.get("currency") or "USD").upper()
            month = kwargs.get("date")[:7] if kwargs.get("date") else datetime.now().strftime("%Y-%m")
            b_id = db.set_budget(category=cat, monthly_limit=limit, currency=curr, month_year=month)
            return {"status": "success", "budget_id": b_id, "message": f"Set budget for '{cat}' to {limit:,.2f} {curr} for {month}."}
        elif action == "get_budgets":
            month = kwargs.get("month") or datetime.now().strftime("%Y-%m")
            return {"status": "success", "budgets": db.get_budgets(month_year=month)}
        elif action == "clear_database":
            db.clear_all_data(create_default_empty_accounts=True)
            vector_store.clear_all()
            return {"status": "success", "message": "Database and semantic memory have been reset to clean zero state."}
        elif action == "export_csv":
            return self._export_csv()
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def _add_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        date = params.get("date") or datetime.now().strftime("%Y-%m-%d")
        amount = float(params.get("amount", 0.0))
        currency = (params.get("currency") or "USD").upper()
        category = params.get("category") or "Other Expense"
        tx_type = params.get("type") or "expense"
        account_id = params.get("account_id")
        merchant = params.get("merchant") or "General"
        description = params.get("description") or ""
        raw_source = params.get("raw_source") or "manual"
        
        # If account_id is not specified, pick default matching account
        if not account_id:
            accounts = db.get_accounts()
            for acc in accounts:
                if acc["currency"] == currency:
                    account_id = acc["id"]
                    break
            if not account_id and accounts:
                account_id = accounts[0]["id"]

        tx_id = db.add_transaction(
            date=date,
            amount=amount,
            category=category,
            currency=currency,
            tx_type=tx_type,
            account_id=account_id,
            merchant=merchant,
            description=description,
            raw_source=raw_source,
            status="confirmed"
        )

        # Index in RAG vector store for semantic memory
        doc_text = f"{merchant} {category} {tx_type} amount {amount} {currency} on {date}. {description}"
        vector_store.add_document(
            text=doc_text,
            metadata={
                "tx_id": tx_id,
                "amount": amount,
                "currency": currency,
                "category": category,
                "merchant": merchant,
                "date": date
            },
            doc_type="transaction",
            ref_id=tx_id
        )

        return {
            "status": "success",
            "transaction_id": tx_id,
            "message": f"Recorded {tx_type} of {amount:,.2f} {currency} for '{category}' ({merchant}).",
            "date": date,
            "amount": amount,
            "currency": currency,
            "category": category
        }

    def _delete_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tx_id = params.get("tx_id")
        if not tx_id:
            return {"status": "error", "message": "Transaction ID (tx_id) required for deletion."}
        success = db.delete_transaction(tx_id)
        if success:
            return {"status": "success", "message": f"Transaction {tx_id} deleted and account balance updated."}
        else:
            return {"status": "error", "message": f"Transaction {tx_id} not found."}

    def _list_transactions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(params.get("limit", 20))
        category = params.get("category")
        month = params.get("month")
        txs = db.get_transactions(limit=limit, category=category, month=month)
        return {"status": "success", "count": len(txs), "transactions": txs}

    def _export_csv(self) -> Dict[str, Any]:
        txs = db.get_transactions(limit=1000)
        df = pd.DataFrame(txs)
        csv_data = df.to_csv(index=False)
        return {"status": "success", "csv": csv_data, "filename": f"ledger_export_{datetime.now().strftime('%Y%m%d')}.csv"}

data_management_skill = DataManagementSkill()
