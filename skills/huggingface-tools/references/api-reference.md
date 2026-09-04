# Hugging Face Tools API Reference

## Operations & Parameters

| Operation (`action` or `task`) | Parameters | Returns |
| :--- | :--- | :--- |
| `classify_expense` / `categorize_text` | `text` (str) | `predicted_category`, `suggested_category`, `status` |
| `financial_sentiment` | `text` (str) | `sentiment` ("positive" / "negative" / "neutral"), `score` |
