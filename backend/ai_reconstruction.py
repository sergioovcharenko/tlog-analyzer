from __future__ import annotations

from typing import Any

STABLE_ALTITUDE_SPREAD_M = 5.0
SHORT_RTL_LAND_S = 2.0
LAND_AWAY_HOME_M = 100.0


def _confidence(label_points: int) -> str:
    if label_points >= 4:
        return "Висока"
    if label_points >= 2:
        return "Середня"
    return "Низька"


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
        out["what_happened"].append(
            f"Зафіксовано повторні епізоди нестабільної радіолінії ({len(radio)})."
        )
        points += 1
        if radio and radio[-1].get("recovered") is False:
            out["what_happened"].append(
                "Останнє відновлення зв’язку після критичного епізоду не підтверджене TLOG."
            )
            points += 1

        if episode:
            alt = episode.get("altitude_m")
            amin = episode.get("altitude_window_min_m")
            amax = episode.get("altitude_window_max_m")
            if (
                alt is not None
                and amin is not None
                and amax is not None
                and (amax - amin) <= STABLE_ALTITUDE_SPREAD_M
            ):
                out["pilot_actions"].append(
                    f"Висота утримувалась приблизно біля {alt:.1f} м; вираженого набору висоти після втрати зв’язку не зафіксовано."
                )
                out["possible_alternatives"].append(
                    "Набір висоти інколи може покращити радіогоризонт, але TLOG не дозволяє стверджувати, що це гарантовано відновило б зв’язок."
                )
                points += 1
            if episode.get("vtx_changed") is False:
                out["pilot_actions"].append(
                    "Зміна VTX/відеоканалу після критичного епізоду не зафіксована."
                )
                out["possible_alternatives"].append(
                    "Зміна відеоканалу могла бути одним із варіантів перевірки якості відеолінії, але її ефект за цим TLOG наперед невідомий."
                )
                points += 1

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

    if facts.get("ended_armed"):
        out["what_happened"].append(
            "Лог завершився при ARMED без підтвердженого DISARM."
        )
        points += 1

    out["confidence"] = _confidence(points)
    return out
