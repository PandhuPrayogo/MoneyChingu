# Financial Analytics API Reference

## Operations & Parameters

| Operation (`analysis_type`) | Parameters | Output Structure |
| :--- | :--- | :--- |
| `generate_full_report` | `month_year`, `currency` | Complete JSON object with net worth, income, expense, savings rate, budgets, and recommendations |
| `monthly_summary` | `month_year`, `currency` | Total income, expense, savings, and category breakdown map |
| `budget_status` | `month_year`, `currency` | Array of category budgets with spent, remaining, and burn-rate % |
| `net_worth` | `currency` | Aggregated balance across all Cash, Bank, and E-Wallet accounts |
| `convert_currency` | `amount`, `from_currency`, `to_currency` | Converted amount and active exchange rate |
| `spending_insights` | `month_year`, `currency` | Top spending categories and actionable alerts |
