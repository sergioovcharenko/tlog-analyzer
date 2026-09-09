from pathlib import Path

# Backend AI integration: replace the existing final prearm augmentation function.
p = Path('backend/ai_reconstruction.py')
s = p.read_text(encoding='utf-8')
if 'from backend.console_diagnostics import describe_console_message' not in s:
    s = s.replace(
        'from typing import Any\n',
        'from typing import Any\n\ntry:\n    from backend.console_diagnostics import describe_console_message\nexcept ImportError:\n    from console_diagnostics import describe_console_message\n',
        1,
    )
marker = 'def augment_ai_reconstruction_with_prearm_diagnostics(ai: dict[str, Any], timeline) -> dict[str, Any]:'
if marker not in s:
    raise SystemExit('AI augmentation marker missing')
head = s.split(marker, 1)[0]
func = r'''def augment_ai_reconstruction_with_prearm_diagnostics(ai: dict[str, Any], timeline) -> dict[str, Any]:
    """Add known console/PreArm diagnostics to the AI conclusion without inventing causality."""
    rows = [row for row in (timeline or []) if isinstance(row, dict)]
    gyro_rows = []
    known = []
    seen = set()
    for row in rows:
        text = str(row.get("systemText") or row.get("system_text") or "").strip()
        if not text:
            continue
        if "gyros inconsistent" in text.lower():
            gyro_rows.append(row)
        diag = describe_console_message(text)
        if diag:
            signature = (diag.get("category"), diag.get("level"), diag.get("summary"))
            if signature not in seen:
                seen.add(signature)
                known.append((row, diag))

    if not gyro_rows and not known:
        return ai

    out = dict(ai or {})
    for key in ("what_happened", "likely_sequence", "pilot_actions", "possible_alternatives", "evidence"):
        out[key] = list(out.get(key) or [])

    if gyro_rows:
        out["what_happened"].append(
            'Перед ARM зафіксовано "PreArm: Gyros inconsistent" — автопілот виявив '
            'розбіжність між показами гіроскопів/IMU.'
        )
        out["what_happened"].append(
            'Gyros inconsistent означає, що покази гіроскопів не узгоджуються між собою. '
            'Можливі причини: рух апарата під час ініціалізації, вібрації, різна температура IMU, '
            'некоректне калібрування або несправність одного з IMU/гіроскопів.'
        )
        times = [str(row.get("time") or "").strip() for row in gyro_rows if str(row.get("time") or "").strip()]
        out["evidence"].append(
            f'Gyros inconsistent: {len(gyro_rows)} повідомлень' + (f'; перше о {times[0]}.' if times else ' у TLOG.')
        )
        arm_rows = [
            row for row in rows
            if row.get("eventType") == "FLIGHT_SESSION_START"
            or "двигуни запущено" in str(row.get("systemText") or row.get("system_text") or "").lower()
        ]
        if arm_rows:
            last_gyro_index = max(rows.index(row) for row in gyro_rows)
            first_arm_index = min(rows.index(row) for row in arm_rows)
            if last_gyro_index < first_arm_index:
                out["evidence"].append(
                    'Повідомлення Gyros inconsistent було до ARM; після ARM повторів у цьому TLOG не знайдено.'
                )
        out["possible_alternatives"].append(
            'Перед наступним запуском залишити апарат нерухомим під час ініціалізації, перезапустити FC, '
            'перевірити калібрування IMU та повторюваність помилки. Якщо Gyros inconsistent з’являється '
            'регулярно — перевірити вібрації, живлення та стан IMU/гіроскопів.'
        )

    for row, diag in known:
        time_text = str(row.get("time") or "").strip()
        prefix = f"{time_text} • " if time_text else ""
        out["evidence"].append(
            f"{prefix}{diag['category']} / {diag['level']}: {diag['summary']}"
        )
        if diag.get("level") in ("CRITICAL", "EMERGENCY"):
            out["what_happened"].append(diag["summary"])
        checks = diag.get("checks") or []
        if checks:
            check_text = "; ".join(checks[:3])
            if check_text not in out["possible_alternatives"]:
                out["possible_alternatives"].append(check_text)

    return out
'''
s = head + func
p.write_text(s, encoding='utf-8')

# Frontend: explain known messages when backend analysisText is empty; reuse same result in report.
p = Path('index.html')
s = p.read_text(encoding='utf-8')
js_marker = 'function renderTimelineTable(items,containerId){'
if js_marker not in s:
    raise SystemExit('timeline marker missing')
if 'function describeKnownConsoleDiagnostic(text)' not in s:
    helper = r'''function describeKnownConsoleDiagnostic(text){
  const raw=String(text||'').trim(), low=raw.toLowerCase();
  if(!raw)return null;
  let m;
  if((m=raw.match(/EKF3\s+(IMU\d+)\s+(MAG\d+)\s+ground mag anomaly,\s*yaw re-aligned/i)))return `MAG/COMPASS • ${m[1]} / ${m[2]}: EKF виявив аномальні дані магнітометра на землі та повторно вирівняв курс yaw. Можливі причини: метал поруч, калібрування компаса, електромагнітні завади або нестабільний магнітометр.`;
  if((m=raw.match(/EKF3\s+(IMU\d+)\s+(MAG\d+)\s+in-flight yaw alignment complete/i)))return `MAG/COMPASS • ${m[1]} / ${m[2]}: EKF завершив вирівнювання yaw у польоті.`;
  if((m=raw.match(/EKF3\s+lane switch\s+(\d+)/i)))return `EKF • CRITICAL: EKF3 переключив основний фільтр на lane ${m[1]}. Це перемикання між екземплярами EKF; перевірити IMU, вібрації та сусідні EKF-повідомлення.`;
  if((m=raw.match(/EKF primary changed\s+(\d+)/i)))return `EKF • WARNING: основний EKF змінено на екземпляр ${m[1]} через внутрішню оцінку якості фільтрів.`;
  if(low.includes('prearm: gyros not calibrated'))return 'IMU/GYRO • CRITICAL: гіроскопи не відкалібровані або ініціалізація gyro не завершена. Це не помилка калібрування акселерометра.';
  if((m=raw.match(/PreArm:\s*AHRS:\s*EKF3 Yaw inconsistent\s+(-?\d+(?:\.\d+)?)\s*deg/i)))return `YAW • CRITICAL: розбіжність yaw ${m[1]}°. AHRS не має надійної оцінки курсу, тому ARM може бути заблокований.`;
  if((m=raw.match(/Yaw imbalance\s*\((-?\d+(?:\.\d+)?)%\)/i)))return `YAW • EMERGENCY: дисбаланс керування по yaw ${m[1]}%. Перевірити центр мас, раму, пропелери та мотори.`;
  if((m=raw.match(/Potential Thrust Loss\s*\((\d+)\)/i)))return `THRUST/MOTOR • EMERGENCY: недостатня або нестабільна тяга, пов'язана з Motor ${m[1]}. Перевірити Motor/ESC/пропелер і силові з'єднання.`;
  if(low.startsWith('terrain: clamping offset'))return 'TERRAIN • INFO: некритичне обмеження внутрішнього offset у модулі оцінки висоти/навігації.';
  if(low.includes('bad synchronization')&&(low.includes('lightning')||low.includes('lighting')))return 'VISUAL NAV • WARNING: камера/візуальна навігація не отримує достатньо придатного зображення; перевірити освітлення, контраст і чистоту камери.';
  if(low.includes("couldn't match keypoints")||low.includes('couldnt match keypoints'))return 'VISUAL NAV • WARNING: не вдалося зіставити ключові точки між кадрами. Причини: освітлення, забруднена камера, велика висота, однорідна поверхня, туман або слабкий контраст.';
  if(low.includes('camera restarted: use althold'))return 'CAMERA • WARNING: модуль камери/візуальної навігації перезапустився; позиційні режими можуть бути недоступні до відновлення position estimate.';
  if(low.includes('prearm: need position estimate'))return 'PREARM • WARNING: автопілот ще не має надійної position estimate для режимів, що потребують позиції.';
  if(low.includes('mount: siyi failed to take picture'))return 'CAMERA • INFO: SIYI не виконав команду фотографування; це не є помилкою керування польотом.';
  return null;
}
function knownConsoleDiagnosticText(systemText,analysisText){return analysisText||describeKnownConsoleDiagnostic(systemText)||'';}

'''
    s = s.replace(js_marker, helper + js_marker, 1)

old = "<div class=\"tl-analysis\">${item.analysisText?`<span class=\"analysis-msg\">${item.analysisText}</span>`:''}</div>"
new = "<div class=\"tl-analysis\">${knownConsoleDiagnosticText(item.systemText,item.analysisText)?`<span class=\"analysis-msg\">${knownConsoleDiagnosticText(item.systemText,item.analysisText)}</span>`:''}</div>"
if old in s:
    s = s.replace(old, new, 1)

old_report = "const explanation=row?.analysisText??row?.analysis??row?.explanation??'';"
new_report = "const explanation=row?.analysisText??row?.analysis??row?.explanation??describeKnownConsoleDiagnostic(raw)??'';"
if old_report in s:
    s = s.replace(old_report, new_report, 1)

p.write_text(s, encoding='utf-8')
