from datetime import datetime, timedelta
from database.db import db
from database.vector_store import vector_store

def seed_initial_data():
    """Ensure baseline accounts exist with zero balance if database is brand new."""
    accounts = db.get_accounts()
    if not accounts:
        db.add_account(name="Cash (USD)", account_type="cash", currency="USD", initial_balance=0.0)
        db.add_account(name="Checking Bank (USD)", account_type="bank", currency="USD", initial_balance=0.0)
        db.add_account(name="GoPay / E-Wallet (IDR)", account_type="e_wallet", currency="IDR", initial_balance=0.0)
        db.add_account(name="Bank Account (IDR)", account_type="bank", currency="IDR", initial_balance=0.0)
        print("Initialized clean zero-balance accounts.")

if __name__ == "__main__":
    seed_initial_data()
