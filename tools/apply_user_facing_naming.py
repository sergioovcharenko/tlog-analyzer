from pathlib import Path


INDEX = Path("index.html")

REPLACEMENTS = [
    ("<title>AI — TLOG Analyzer", "<title>TLOG Analyzer"),
    ("<h1>🚁 AI</h1>", "<h1>🚁 TLOG ANALYZER</h1>"),
    ("🤖 AI ВИСНОВОК", "ТЕХНІЧНИЙ ВИСНОВОК"),
    ("🧠 AI ЕКСПЕРТНИЙ ВИСНОВОК", "ПОГЛИБЛЕНИЙ АНАЛІЗ ПОЛЬОТУ"),
    ("🎥 AI — ВІДЕО + TLOG", "🎥 ВІДЕО + TLOG"),
    ("AI-висновок у цьому аналізі відсутній.", "Технічний висновок у цьому аналізі відсутній."),
    ("<h2>AI-висновок</h2>", "<h2>Технічний висновок</h2>"),
    ("кадри ще не інтерпретуються AI; візуальні спостереження будуть додані окремим етапом.", "автоматичний аналіз кадрів на цьому етапі ще не виконується; візуальні спостереження будуть додані окремим етапом."),
    ("На цьому етапі автоматичний аналіз кадрів на цьому етапі ще не виконується", "Автоматичний аналіз кадрів на цьому етапі ще не виконується"),
    ("AI-висновки або будь-які розрахунки", "результати аналізу або будь-які розрахунки"),
    ("title:'AI — TLOG Analyzer'", "title:'TLOG Analyzer'"),
]


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")
    updated = text
    changed = 0
    for old, new in REPLACEMENTS:
        if old in updated:
            updated = updated.replace(old, new)
            changed += 1
    if updated != text:
        INDEX.write_text(updated, encoding="utf-8")
    print(f"user-facing naming replacements applied: {changed}")


if __name__ == "__main__":
    main()
