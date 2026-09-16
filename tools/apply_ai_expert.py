from pathlib import Path

BACKEND = Path("backend/main.py")


def patch_backend():
    source = BACKEND.read_text(encoding="utf-8")

    if "AI_EXPERT_IMPORT_V1" not in source:
        anchor = "app = FastAPI()"
        block = '''# AI_EXPERT_IMPORT_V1\ntry:\n    from backend.ai_expert import build_ai_expert_analysis\nexcept ImportError:\n    from ai_expert import build_ai_expert_analysis\n\n'''
        if anchor not in source:
            raise SystemExit("backend app anchor not found")
        source = source.replace(anchor, block + anchor, 1)

    if "AI_EXPERT_BACKEND_V1" not in source:
        anchor = '''        ai_reconstruction = augment_ai_reconstruction_with_prearm_diagnostics(\n            ai_reconstruction, timeline\n        )\n'''
        block = '''\n        # AI_EXPERT_BACKEND_V1\n        ai_expert = None\n        ai_expert_warning = None\n        try:\n            _expert_radio_events = []\n            for _ep in communication_loss_episodes:\n                _start = _ep.get("startTimestamp")\n                if not valid_number(_start):\n                    continue\n                _expert_radio_events.append({\n                    "time_s": float(_start) - float(base_t),\n                    "dbm": _ep.get("startDbm"),\n                    "recovered": bool(_ep.get("recovered")),\n                    "vtx_changed": bool(_ep.get("vtxChangedAcrossBlindZone")),\n                })\n\n            # RADIO/GCS failsafe is a separate evidence class from a raw MAVLink gap.\n            for _row in timeline:\n                if not isinstance(_row, dict):\n                    continue\n                _text = str(_row.get("systemText") or _row.get("system_text") or "").strip()\n                _lower = _text.lower()\n                if "failsafe" not in _lower or not ("radio" in _lower or "gcs" in _lower):\n                    continue\n                _t_ms = _timeline_graph_time_ms(_row.get("time"))\n                if _t_ms is None:\n                    continue\n                _expert_radio_events.append({\n                    "time_s": float(_t_ms) / 1000.0,\n                    "type": "failsafe",\n                    "text": _text,\n                })\n\n            _expert_thrust_events = []\n            for _event in potential_thrust_loss_events:\n                _ts = _event.get("timestamp")\n                if not valid_number(_ts):\n                    continue\n                _expert_thrust_events.append({\n                    "time_s": float(_ts) - float(base_t),\n                    "text": _event.get("text") or "Potential Thrust Loss",\n                    "motors": _event.get("motors"),\n                    "mode": _event.get("mode"),\n                })\n\n            _expert_rpm_events = []\n            for _event in rpm_drop_events:\n                _ts = _event.get("timestamp")\n                if not valid_number(_ts):\n                    continue\n                _expert_rpm_events.append({\n                    "time_s": float(_ts) - float(base_t),\n                    "differencePct": _event.get("differencePct"),\n                    "lowerMotor": _event.get("lowerMotor"),\n                    "higherMotor": _event.get("higherMotor"),\n                    "type": "rpm_drop",\n                    "drop": True,\n                })\n\n            ai_expert = build_ai_expert_analysis(\n                timeline=timeline,\n                radio_events=_expert_radio_events,\n                thrust_events=_expert_thrust_events,\n                rpm_events=_expert_rpm_events,\n            )\n        except Exception as exc:\n            ai_expert_warning = f"Експертний AI-аналіз недоступний: {exc}"\n'''
        if anchor not in source:
            raise SystemExit("AI reconstruction augmentation anchor not found")
        source = source.replace(anchor, anchor + block, 1)

    if '"ai_expert": ai_expert,' not in source:
        anchor = '            "ai_reconstruction": ai_reconstruction,\n'
        replacement = (
            anchor
            + '            "ai_expert": ai_expert,\n'
            + '            "ai_expert_warning": ai_expert_warning,\n'
        )
        if anchor not in source:
            raise SystemExit("AI reconstruction response anchor not found")
        source = source.replace(anchor, replacement, 1)

    BACKEND.write_text(source, encoding="utf-8")


patch_backend()
print("Applied AI flight expert backend integration")
