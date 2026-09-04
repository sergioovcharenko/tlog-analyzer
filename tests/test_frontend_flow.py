from pathlib import Path

html = Path("index.html").read_text(encoding="utf-8")

assert "await pingServerAsync();" not in html, "Аналіз усе ще блокується окремим /health перед POST /analyze"
assert "async function pingServerAsync()" not in html, "Старий блокуючий health-check усе ще присутній"
assert "const result=await analyzeOnServer(selectedFile);" in html, "Прямий POST /analyze не знайдено"
assert "Підключення та передача TLOG" in html, "Новий текст прогресу не знайдено"

print("frontend flow OK")
