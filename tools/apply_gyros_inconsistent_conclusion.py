from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / 'backend' / 'main.py'
AI = ROOT / 'backend' / 'ai_reconstruction.py'

main = MAIN.read_text(encoding='utf-8')
ai = AI.read_text(encoding='utf-8')

# 1) Add reusable AI augmentation helper.
if 'def augment_ai_reconstruction_with_prearm_diagnostics' not in ai:
    ai += r'''


def augment_ai_reconstruction_with_prearm_diagnostics(ai: dict[str, Any], timeline) -> dict[str, Any]:
    """Add factual PreArm Gyros inconsistent diagnostics to the AI conclusion."""
    rows = [row for row in (timeline or []) if isinstance(row, dict)]
    gyro_rows = []
    for row in rows:
        text = str(row.get("systemText") or row.get("system_text") or "")
        if "gyros inconsistent" in text.lower():
            gyro_rows.append(row)

    if not gyro_rows:
        return ai

    out = dict(ai or {})
    for key in ("what_happened", "likely_sequence", "pilot_actions", "possible_alternatives", "evidence"):
        out[key] = list(out.get(key) or [])

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
    if times:
        out["evidence"].append(
            f'Gyros inconsistent: {len(gyro_rows)} повідомлень; перше о {times[0]}.'
        )
    else:
        out["evidence"].append(f'Gyros inconsistent: {len(gyro_rows)} повідомлень у TLOG.')

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
    return out
'''

# 2) Import the helper in backend/main.py.
old_import = 'from backend.ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts'
new_import = 'from backend.ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts, augment_ai_reconstruction_with_prearm_diagnostics'
main = main.replace(old_import, new_import)
old_import_fallback = 'from ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts'
new_import_fallback = 'from ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts, augment_ai_reconstruction_with_prearm_diagnostics'
main = main.replace(old_import_fallback, new_import_fallback)

# 3) Promote Gyros inconsistent to a serious board message.
if '"gyros inconsistent"' not in main:
    anchor = '                "ekf variance",\n'
    if anchor not in main:
        raise SystemExit('serious_patterns anchor not found')
    main = main.replace(anchor, anchor + '                "gyros inconsistent",\n', 1)

# 4) Add it to the final AI conclusion.
call = '        ai_reconstruction = build_ai_reconstruction(ai_reconstruction_facts)\n'
if 'ai_reconstruction = augment_ai_reconstruction_with_prearm_diagnostics(' not in main:
    if call not in main:
        raise SystemExit('AI reconstruction call anchor not found')
    main = main.replace(
        call,
        call + '        ai_reconstruction = augment_ai_reconstruction_with_prearm_diagnostics(\n'
               '            ai_reconstruction, timeline\n'
               '        )\n',
        1,
    )

AI.write_text(ai, encoding='utf-8')
MAIN.write_text(main, encoding='utf-8')
