from pathlib import Path

FILES = [
    Path("index.html"),
    Path("backend/main.py"),
    Path("tools/apply_ai_reconstruction.py"),
    Path("tools/apply_ai_expert.py"),
]

REPLACEMENTS = [
    ("<title>AI — TLOG Analyzer v1.3.3 «3D Lazy FIX»</title>", "<title>TLOG Analyzer v1.3.3 «3D Lazy FIX»</title>"),
    ("<h1>🚁 AI</h1>", "<h1>🚁 TLOG ANALYZER</h1>"),
    ("🤖 AI ВИСНОВОК", "ТЕХНІЧНИЙ ВИСНОВОК"),
    ("🧠 AI ЕКСПЕРТНИЙ ВИСНОВОК", "ПОГЛИБЛЕНИЙ АНАЛІЗ ПОЛЬОТУ"),
    ("🎥 AI — ВІДЕО + TLOG", "🎥 ВІДЕО + TLOG"),
    ("AI — TLOG Analyzer", "TLOG Analyzer"),
    ("AI-висновок у цьому аналізі відсутній.", "Технічний висновок у цьому аналізі відсутній."),
    ("<h2>AI-висновок</h2>", "<h2>Технічний висновок</h2>"),
    ("AI-висновки", "результати аналізу"),
    (
        "На цьому етапі кадри ще не інтерпретуються AI; візуальні спостереження будуть додані окремим етапом.",
        "Автоматичний аналіз кадрів на цьому етапі ще не виконується; візуальні спостереження будуть додані окремим етапом.",
    ),
    ("Експертний AI-аналіз недоступний:", "Поглиблений аналіз недоступний:"),
]


def patch_file(path: Path) -> bool:
    if not path.exists():
        return False
    source = path.read_text(encoding="utf-8")
    updated = source
    for old, new in REPLACEMENTS:
        updated = updated.replace(old, new)
    if updated == source:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


changed = [str(path) for path in FILES if patch_file(path)]
print("Updated user-facing terminology:", ", ".join(changed) if changed else "no changes")
