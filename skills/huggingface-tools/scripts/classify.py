"""
Hugging Face Tools Helper Script:
Categorizes expense text and analyzes sentiment.
"""
from skills.hf_skills import hf_skill

def classify(text: str):
    return hf_skill.execute(action="classify_expense", text=text)

if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "Coffee at cafe"
    print(classify(t))
