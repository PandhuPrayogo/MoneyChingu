"""
Data Processing Helper Script:
Validates and extracts financial documents.
"""
from pathlib import Path
from skills.data_processing import data_processing_skill

def parse_file(file_path: str):
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(p, "rb") as f:
        if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
            return data_processing_skill.process_receipt_image(f)
        elif p.suffix.lower() == ".pdf":
            return data_processing_skill.process_bank_pdf(f)
        elif p.suffix.lower() == ".csv":
            return data_processing_skill.process_csv_statement(f)
        else:
            return {"status": "error", "message": f"Unsupported format: {p.suffix}"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(parse_file(sys.argv[1]))
    else:
        print("Provide a file path to parse.")
