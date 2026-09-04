from pathlib import Path

html = Path("index.html").read_text(encoding="utf-8")

assert "await pingServerAsync();" not in html, "Аналіз усе ще блокується окремим /health перед POST /analyze"
assert "async function pingServerAsync()" not in html, "Старий блокуючий health-check усе ще присутній"
assert "const result=await analyzeOnServer(selectedFile);" in html, "Прямий POST /analyze не знайдено"
assert "Підключення та передача TLOG" in html, "Новий текст прогресу не знайдено"

# Тимчасовий wait-overlay: показуємо одразу після натискання Аналіз,
# ховаємо, коли з'явились результати або помилка.
assert "TEMP_ANALYSIS_WAIT_OVERLAY_START" in html, "Тимчасовий overlay не знайдено"
assert "https://i.imgur.com/CduyK.jpeg" in html, "Картинка wait-overlay не знайдена"
assert "НЕ ТОРОПИСЬ!" in html, "Текст wait-overlay не знайдений"
assert "showTemporaryAnalysisWaitOverlay" in html, "Функція показу overlay не знайдена"
assert "hideTemporaryAnalysisWaitOverlay" in html, "Функція приховування overlay не знайдена"
assert "closest('.analyze')" in html, "Overlay не прив'язаний до натискання кнопки аналізу"
assert "MutationObserver" in html, "Overlay не відстежує завершення аналізу"

print("frontend flow OK")
