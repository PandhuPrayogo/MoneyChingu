"""
Financial Analytics Helper Script:
Runs calculations for cash flow, budgets, and net worth.
"""
from datetime import datetime
from skills.financial_analytics import financial_analytics_skill

def run_quick_report(currency: str = "USD"):
    now = datetime.now().strftime("%Y-%m")
    return financial_analytics_skill.execute(
        analysis_type="generate_full_report",
        month_year=now,
        currency=currency
    )

if __name__ == "__main__":
    print(run_quick_report())
