import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database paths
DB_PATH = DATA_DIR / "money_tracker.db"
VECTOR_DB_PATH = DATA_DIR / "vectors.json"

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Default model: gemini-3.6-flash
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = "models/text-embedding-004"

# Supported Currencies & Default Conversion Rate (1 USD = ~16,000 IDR)
DEFAULT_CURRENCY = "USD"
SUPPORTED_CURRENCIES = ["USD", "IDR"]
USD_TO_IDR_RATE = float(os.getenv("USD_TO_IDR_RATE", "16000.0"))

# Persona Configuration
AGENT_NAME = "MoneyChingu"
AGENT_STYLE = "witty_buddy" # Friendly, witty, uses realistic slang & gentle sarcasm on reckless spending

# Default Expense/Income Categories
DEFAULT_EXPENSE_CATEGORIES = [
    "Food & Dining",
    "Groceries",
    "Transport & Fuel",
    "Shopping & Lifestyle",
    "Bills & Utilities",
    "Entertainment & Subs",
    "Health & Fitness",
    "Education & Work",
    "Investments",
    "Other Expense"
]

DEFAULT_INCOME_CATEGORIES = [
    "Salary",
    "Freelance / Gig",
    "Investment Return",
    "Gift & Bonus",
    "Other Income"
]
