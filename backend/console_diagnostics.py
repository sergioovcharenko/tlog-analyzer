from __future__ import annotations

import re
from typing import Any


def _result(category: str, level: str, summary: str, causes=None, checks=None, values=None) -> dict[str, Any]:
    return {
        "category": category,
        "level": level,
        "summary": summary,
        "causes": list(causes or []),
        "checks": list(checks or []),
        "values": dict(values or {}),
    }


def describe_console_message(text: str | None) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    low = raw.lower()
    if not raw:
        return None

    m = re.search(r"EKF3\s+(IMU\d+)\s+(MAG\d+)\s+ground mag anomaly,\s*yaw re-aligned", raw, re.I)
    if m:
        imu, mag = m.groups()
        return _result(
            "MAG/COMPASS", "WARNING",
            f"{imu} / {mag}: EKF виявив аномальні дані магнітометра на землі та повторно вирівняв курс yaw.",
            ["магнітне поле від металевих предметів", "некоректне калібрування компаса", "електромагнітні завади від силової частини", "нестабільний магнітометр"],
            ["перевірити оточення на метал", "перевірити калібрування компаса", "перевірити повторюваність повідомлення"],
            {"imu": imu, "mag": mag},
        )

    m = re.search(r"EKF3\s+(IMU\d+)\s+(MAG\d+)\s+in-flight yaw alignment complete", raw, re.I)
    if m:
        imu, mag = m.groups()
        return _result(
            "MAG/COMPASS", "INFO",
            f"{imu} / {mag}: EKF завершив вирівнювання yaw у польоті.",
            ["попередня нестабільність або переоцінка курсу"],
            ["зіставити з попередніми MAG/Yaw повідомленнями"],
            {"imu": imu, "mag": mag},
        )

    m = re.search(r"EKF3\s+lane switch\s+(\d+)", raw, re.I)
    if m:
        lane = int(m.group(1))
        return _result(
            "EKF", "CRITICAL",
            f"EKF3 переключив основний фільтр на lane {lane}. Це перемикання між екземплярами EKF, а не просто між барометром та акселерометром.",
            ["погіршення якості одного набору IMU/сенсорів", "сильні вібрації", "некоректні покази IMU"],
            ["перевірити IMU та вібрації", "переглянути сусідні EKF-повідомлення"],
            {"lane": lane},
        )

    m = re.search(r"EKF primary changed\s+(\d+)", raw, re.I)
    if m:
        primary = int(m.group(1))
        return _result(
            "EKF", "WARNING",
            f"Основний EKF змінено на екземпляр {primary} через внутрішню оцінку якості фільтрів.",
            ["різниця якості між EKF lanes", "вібрації або нестабільні IMU-дані"],
            ["перевірити, чи повторюється перемикання", "зіставити з lane switch та IMU-повідомленнями"],
            {"primary": primary},
        )

    if "prearm: gyros not calibrated" in low:
        return _result(
            "IMU/GYRO", "CRITICAL",
            "Гіроскопи не відкалібровані або їх ініціалізація ще не завершена.",
            ["рух апарата під час запуску", "незавершена ініціалізація gyro", "проблема IMU/gyro"],
            ["залишити апарат нерухомим під час ініціалізації", "перезапустити контролер", "перевірити калібрування гіроскопів"],
        )

    m = re.search(r"PreArm:\s*AHRS:\s*EKF3 Yaw inconsistent\s+(-?\d+(?:\.\d+)?)\s*deg", raw, re.I)
    if m:
        deg = float(m.group(1))
        return _result(
            "YAW", "CRITICAL",
            f"EKF3 має неузгоджений yaw: розбіжність {deg:g}°. AHRS не має надійної оцінки курсу, тому ARM може бути заблокований.",
            ["рух апарата під час ініціалізації", "проблема компаса", "метал або магнітні завади поруч"],
            ["дочекатися завершення ініціалізації", "перезапустити контролер", "перевірити калібрування компаса на відкритій місцевості"],
            {"yaw_delta_deg": deg},
        )

    m = re.search(r"Yaw imbalance\s*\((-?\d+(?:\.\d+)?)%\)", raw, re.I)
    if m:
        pct = float(m.group(1))
        return _result(
            "YAW", "EMERGENCY",
            f"Yaw imbalance: дисбаланс керування по yaw становить {pct:g}%.",
            ["зміщений центр мас", "асиметрія або деформація рами", "різні або пошкоджені пропелери", "нестабільний крутний момент моторів"],
            ["уникати різких маневрів", "після посадки перевірити раму, промені, пропелери, мотори та кріплення"],
            {"imbalance_pct": pct},
        )

    m = re.search(r"Potential Thrust Loss\s*\((\d+)\)", raw, re.I)
    if m:
        motor = int(m.group(1))
        return _result(
            "THRUST/MOTOR", "EMERGENCY",
            f"Potential Thrust Loss: недостатня або нестабільна тяга, пов'язана з Motor {motor}.",
            ["надмірне навантаження", "різкий маневр", "низька напруга батареї", "сильний вітер", "пошкодження пропелера, мотора або ESC"],
            ["уникати різких маневрів", "після посадки перевірити Motor/ESC/пропелер і силові з'єднання"],
            {"motor": motor},
        )

    if low.startswith("terrain: clamping offset"):
        return _result(
            "TERRAIN", "INFO",
            "Terrain clamping offset — некритичне обмеження внутрішнього offset у модулі оцінки висоти/навігації.",
            ["особливість ініціалізації або роботи модуля візуальної стабілізації"],
            ["оцінювати разом з іншими навігаційними повідомленнями"],
        )

    if "bad synchronization" in low and ("lightning" in low or "lighting" in low):
        return _result(
            "VISUAL NAV", "WARNING",
            "Модуль візуальної навігації має проблеми синхронізації; імовірно камера не отримує достатньо придатного зображення.",
            ["недостатня освітленість", "забруднена камера", "низька контрастність сцени"],
            ["перевірити чистоту камери", "перевірити освітлення та контраст поверхні", "якщо повторюється — перевірити модуль"],
        )

    if "couldn't match keypoints" in low or "couldnt match keypoints" in low:
        return _result(
            "VISUAL NAV", "WARNING",
            "Візуальна навігація не змогла зіставити ключові точки між кадрами.",
            ["погане освітлення", "забруднена камера", "велика висота", "однорідна поверхня", "туман або слабкий контраст"],
            ["перевірити камеру, освітлення і контраст поверхні", "оцінити повторюваність помилки"],
        )

    if "camera restarted: use althold" in low:
        return _result(
            "CAMERA", "WARNING",
            "Модуль камери/візуальної навігації перезапустився; позиційні режими можуть бути недоступні до відновлення оцінки положення.",
            ["перезапуск або збій модуля візуальної навігації"],
            ["використовувати режим, що не залежить від position estimate, до відновлення системи", "після посадки перевірити модуль"],
        )

    if "prearm: need position estimate" in low:
        return _result(
            "PREARM", "WARNING",
            "PreArm: Need Position Estimate — автопілот ще не має надійної position estimate для режимів, що потребують позиції.",
            ["не завершена ініціалізація", "недостатні дані візуальної навігації", "погане освітлення або нестабільний position source"],
            ["дочекатися завершення ініціалізації", "перевірити джерело позиції та візуальну навігацію"],
        )

    if "mount: siyi failed to take picture" in low:
        return _result(
            "CAMERA", "INFO",
            "SIYI не виконав команду фотографування. Це не є помилкою керування польотом.",
            ["камера не прийняла команду", "проблема зв'язку або стану камери"],
            ["перевірити камеру та команду фотографування"],
        )

    return None
