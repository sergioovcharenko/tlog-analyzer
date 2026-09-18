from __future__ import annotations

from typing import Any

try:
    from backend.console_diagnostics import describe_console_message
except ImportError:
    from console_diagnostics import describe_console_message

STABLE_ALTITUDE_SPREAD_M = 5.0
ALTITUDE_CLIMB_M = 8.0
SHORT_RTL_LAND_S = 2.0
LAND_AWAY_HOME_M = 100.0
AI_REACTION_WINDOW_S = 10.0


def _confidence(label_points: int) -> str:
    if label_points >= 4:
        return "Висока"
    if label_points >= 2:
        return "Середня"
    return "Низька"


def _nearest_sample(samples: list[dict[str, Any]], time_s: float, value_key: str) -> dict[str, Any] | None:
    valid = [s for s in samples if s.get("time_s") is not None and s.get(value_key) is not None]
    if not valid:
        return None
    return min(valid, key=lambda s: abs(float(s["time_s"]) - float(time_s)))


def build_ai_reconstruction_facts(
    *,
    radio_loss_episodes,
    mode_transitions,
    altitude_samples,
    vtx_events,
    home_distance_samples,
    ended_armed,
    power_metrics,
) -> dict[str, Any]:
    radio = list(radio_loss_episodes or [])
    critical = radio[-1] if radio else None
    critical_episode = None

    if critical is not None:
        t = float(critical.get("time_s", 0.0))
        alt_sample = _nearest_sample(list(altitude_samples or []), t, "altitude_m")
        window = [
            s for s in (altitude_samples or [])
            if s.get("time_s") is not None
            and s.get("altitude_m") is not None
            and abs(float(s["time_s"]) - t) <= AI_REACTION_WINDOW_S
        ]
        alt_values = [float(s["altitude_m"]) for s in window]
        structured_vtx_changed = critical.get("vtx_changed")
        if structured_vtx_changed is None:
            vtx_changed = any(
                e.get("time_s") is not None
                and 0.0 <= float(e["time_s"]) - t <= AI_REACTION_WINDOW_S
                for e in (vtx_events or [])
            )
        else:
            vtx_changed = bool(structured_vtx_changed)
        critical_episode = {
            "time_s": t,
            "altitude_m": float(alt_sample["altitude_m"]) if alt_sample else None,
            "altitude_window_min_m": min(alt_values) if alt_values else None,
            "altitude_window_max_m": max(alt_values) if alt_values else None,
            "vtx_changed": bool(vtx_changed),
        }

    land_transition = next(
        (
            tr for tr in (mode_transitions or [])
            if tr.get("from") == "RTL" and tr.get("to") == "LAND"
        ),
        None,
    )
    land_distance_home_m = None
    if land_transition and land_transition.get("time_s") is not None:
        nearest_home = _nearest_sample(
            list(home_distance_samples or []), float(land_transition["time_s"]), "distance_m"
        )
        if nearest_home:
            land_distance_home_m = float(nearest_home["distance_m"])

    return {
        "radio_loss_episodes": radio,
        "critical_radio_episode": critical_episode,
        "mode_transitions": list(mode_transitions or []),
        "land_distance_home_m": land_distance_home_m,
        "ended_armed": bool(ended_armed),
        "power": dict(power_metrics or {}),
    }


def build_ai_reconstruction(facts: dict[str, Any]) -> dict[str, Any]:
    radio = facts.get("radio_loss_episodes") or []
    episode = facts.get("critical_radio_episode")
    power = facts.get("power") or {}
    transitions = facts.get("mode_transitions") or []

    radio_score = len(radio)
    power_score = 0
    if power.get("potential_thrust_loss_count", 0):
        power_score += 2
    if (power.get("rpm_asymmetry_pct") or 0) >= 20:
        power_score += 2
    if power.get("min_voltage_v") is not None:
        power_score += 1
    if (power.get("max_current_a") or 0) >= 80:
        power_score += 1

    if power_score >= max(3, radio_score + 1):
        dominant = "power"
    elif radio_score >= 2 or episode:
        dominant = "radio"
    else:
        dominant = "none"

    out: dict[str, Any] = {
        "what_happened": [],
        "likely_sequence": [],
        "pilot_actions": [],
        "possible_alternatives": [],
        "confidence": "Низька",
        "evidence": [],
        "dominant_scenario": dominant,
    }

    points = 0

    if dominant == "radio":
        if len(radio) == 1:
            out["what_happened"].append("Зафіксовано критичний епізод нестабільної радіолінії.")
        else:
            out["what_happened"].append(
                f"Зафіксовано повторні епізоди нестабільної радіолінії ({len(radio)})."
            )
        points += 1

        dbm_values = [float(x["dbm"]) for x in radio if x.get("dbm") is not None]
        if dbm_values:
            worst_dbm = min(dbm_values)
            critical_count = sum(1 for value in dbm_values if value <= -128)
            if critical_count:
                out["evidence"].append(
                    f"Критичний рівень до {worst_dbm:.0f} dBm зафіксовано у {critical_count} епізодах."
                )
            else:
                out["evidence"].append(f"Найгірший зафіксований рівень: {worst_dbm:.0f} dBm.")
            points += 1

        if radio and radio[-1].get("recovered") is False:
            out["what_happened"].append(
                "Останнє відновлення зв’язку після критичного епізоду не підтверджене TLOG."
            )
            points += 1
        elif radio and radio[-1].get("recovered") is True:
            out["what_happened"].append("Після останнього критичного епізоду відновлення зв’язку підтверджене TLOG.")
            points += 1

        if episode:
            alt = episode.get("altitude_m")
            amin = episode.get("altitude_window_min_m")
            amax = episode.get("altitude_window_max_m")
            if alt is not None and amin is not None and amax is not None:
                spread = float(amax) - float(amin)
                if spread <= STABLE_ALTITUDE_SPREAD_M:
                    out["pilot_actions"].append(
                        f"Висота утримувалась приблизно біля {float(alt):.1f} м; вираженого набору висоти після втрати зв’язку не зафіксовано."
                    )
                    out["possible_alternatives"].append(
                        "Набір висоти інколи може покращити радіогоризонт, але TLOG не дозволяє стверджувати, що це гарантовано відновило б зв’язок."
                    )
                    points += 1
                elif float(alt) - float(amin) >= ALTITUDE_CLIMB_M:
                    out["pilot_actions"].append(
                        f"Набір висоти зафіксовано: у критичному вікні висота змінювалась приблизно від {float(amin):.1f} до {float(amax):.1f} м."
                    )
                    points += 1
                else:
                    out["pilot_actions"].append(
                        f"Висота в критичному вікні помітно змінювалась ({float(amin):.1f}–{float(amax):.1f} м), тому стверджувати про її стабільне утримання не можна."
                    )

            if episode.get("vtx_changed") is False:
                out["pilot_actions"].append(
                    "Зміна VTX/відеоканалу після критичного епізоду не зафіксована."
                )
                out["possible_alternatives"].append(
                    "Зміна відеоканалу могла бути одним із варіантів перевірки якості відеолінії, але її ефект за цим TLOG наперед невідомий."
                )
                points += 1
            elif episode.get("vtx_changed") is True:
                out["pilot_actions"].append(
                    "Зміну VTX/відеоканалу зафіксовано як реакцію в районі критичного епізоду."
                )
                points += 1

    elif dominant == "power":
        out["what_happened"].append(
            "Сукупність телеметрії більше відповідає проблемі силової установки або живлення, ніж радіолінії."
        )
        if power.get("potential_thrust_loss_count", 0):
            out["evidence"].append(
                f"Potential Thrust Loss: {power['potential_thrust_loss_count']} подій"
            )
            points += 1
        if power.get("rpm_asymmetry_pct") is not None:
            out["evidence"].append(
                f"Максимальна асиметрія RPM: {float(power['rpm_asymmetry_pct']):.1f}%"
            )
            points += 1
        if power.get("min_voltage_v") is not None:
            out["evidence"].append(
                f"Мінімальна напруга: {float(power['min_voltage_v']):.2f} V"
            )
            points += 1
        if power.get("max_current_a") is not None:
            out["evidence"].append(
                f"Піковий струм: {float(power['max_current_a']):.1f} A"
            )
            points += 1

    else:
        out["what_happened"].append(
            "За даними TLOG не виявлено одного домінуючого механізму відмови, підтвердженого кількома незалежними ознаками."
        )

    # Mode sequence is factual and useful regardless of the dominant scenario.
    for tr in transitions:
        delta = tr.get("delta_s")
        if (
            tr.get("from") == "RTL"
            and tr.get("to") == "LAND"
            and delta is not None
            and float(delta) <= SHORT_RTL_LAND_S
        ):
            out["likely_sequence"].append(
                f"RTL змінився на LAND приблизно через {float(delta):.1f} с, тому RTL мав дуже мало часу для продовження повернення."
            )
            points += 1
            break

    dist = facts.get("land_distance_home_m")
    if dist is not None and float(dist) >= LAND_AWAY_HOME_M:
        out["likely_sequence"].append(
            f"LAND розпочався приблизно за {float(dist):.0f} м від HOME."
        )
        points += 1

    if facts.get("ended_armed"):
        out["what_happened"].append(
            "Лог завершився при ARMED без підтвердженого DISARM."
        )
        points += 1

    out["confidence"] = _confidence(points)
    return out



def augment_ai_reconstruction_with_prearm_diagnostics(ai: dict[str, Any], timeline) -> dict[str, Any]:
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
