# Data Management API Reference

## Actions & Parameters

| Action | Required Parameters | Optional Parameters | Description |
| :--- | :--- | :--- | :--- |
| `add_transaction` | `amount`, `category`, `type` | `date`, `currency`, `account_id`, `merchant`, `description` | Record an expense/income |
| `edit_transaction` | `tx_id` | `amount`, `category`, `type`, `date`, `merchant`, `description` | Modify existing transaction |
| `delete_transaction` | `tx_id` | None | Remove transaction & reverse balance |
| `list_transactions` | None | `limit`, `category`, `month` | Fetch transaction list |
| `search_transactions` | None | `query`, `category`, `min_amount`, `max_amount` | Filter transactions |
| `transfer_funds` | `from_account_id`, `to_account_id`, `amount` | `currency`, `description` | Transfer balance between accounts |
| `add_account` | None | `account_name`, `account_type`, `currency`, `balance` | Create financial account |
| `delete_account` | `account_id` | None | Delete account & unlink transactions |
| `set_budget` | `category`, `monthly_limit` | `currency`, `date` | Set monthly budget target |
| `get_budgets` | None | `month` | Query category budgets |
| `clear_database` | None | None | Reset database to zero state |
| `export_csv` | None | None | Generate CSV file of transactions |
