# Data Processing API Reference

## Methods & Supported File Formats

| Method | Supported Formats | Engine | Output Format |
| :--- | :--- | :--- | :--- |
| `process_receipt_image(file)` | PNG, JPG, JPEG, WEBP | Gemini Vision Multimodal (`gemini-3.6-flash`, fallback `gemini-2.0-flash`) | Structured JSON (date, amount, currency, category, merchant, items) |
| `process_bank_pdf(file)` | PDF | `PyPDF2` + Gemini text parsing | List of transaction dictionaries |
| `process_csv_statement(file)` | CSV, TSV | `pandas` dataframe parser | Normalized transaction list |
