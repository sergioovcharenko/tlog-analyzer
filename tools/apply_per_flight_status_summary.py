from pathlib import Path

BACKEND_PATH = Path("backend/main.py")
FRONTEND_PATH = Path("index.html")
MARKER = "PER_FLIGHT_STATUS_SUMMARY_V1"

backend = BACKEND_PATH.read_text(encoding="utf-8")
frontend = FRONTEND_PATH.read_text(encoding="utf-8")

if MARKER not in backend:
    # The last session ending ARMED must outrank any earlier DISARM in the file.
    disarm_marker = "\n        elif disarm_detected:\n"
    armed_marker = "\n        elif log_ended_armed:\n"
    critical_marker = "\n        elif is_critical:\n"
    disarm_pos = backend.index(disarm_marker)
    armed_pos = backend.index(armed_marker, disarm_pos)
    critical_pos = backend.index(critical_marker, armed_pos)
    disarm_block = backend[disarm_pos:armed_pos]
    armed_block = backend[armed_pos:critical_pos]
    backend = backend[:disarm_pos] + armed_block + disarm_block + backend[critical_pos:]

    old_status = '''                if s.get("endedArmed"):\n                    icon="🚨"; status="TLOG завершився при ARMED; DISARM не зафіксовано"\n                else:\n                    icon="✅"; status="DISARM "+format_timeline_time(s["disarmTimestamp"],base_t)\n                n=s.get("takeoffEpisodeCount",0)\n'''
    new_status = '''                # PER_FLIGHT_STATUS_SUMMARY_V1\n                n=s.get("takeoffEpisodeCount",0)\n                _session_start=float(s.get("armTimestamp") or 0.0)\n                _session_end=s.get("disarmTimestamp")\n                _session_radio=[]\n                for _radio_ep in communication_loss_episodes:\n                    _radio_start=_radio_ep.get("startTimestamp")\n                    if not valid_number(_radio_start):\n                        continue\n                    if float(_radio_start) < _session_start:\n                        continue\n                    if valid_number(_session_end) and float(_radio_start) > float(_session_end):\n                        continue\n                    _session_radio.append(_radio_ep)\n                _session_unrecovered=any(not _ep.get("recovered") for _ep in _session_radio)\n\n                if s.get("endedArmed") and _session_unrecovered:\n                    icon="🔴"\n                    status_class="flight-session-status-critical"\n                    status="Втрата зв'язку — TLOG завершився при ARMED; DISARM не зафіксовано"\n                elif s.get("endedArmed"):\n                    icon="🔴"\n                    status_class="flight-session-status-critical"\n                    status="Потребує уваги — TLOG завершився при ARMED; DISARM не зафіксовано"\n                elif n==0:\n                    icon="🔵"\n                    status_class="flight-session-status-info"\n                    status="ARM-сесія / зліт не підтверджено; DISARM "+format_timeline_time(s["disarmTimestamp"],base_t)\n                elif _session_radio:\n                    icon="🟡"\n                    status_class="flight-session-status-warning"\n                    status="Потребує уваги — були втрати зв'язку, відновлено; DISARM "+format_timeline_time(s["disarmTimestamp"],base_t)\n                else:\n                    icon="🟢"\n                    status_class="flight-session-status-ok"\n                    status="Завершено штатно; DISARM "+format_timeline_time(s["disarmTimestamp"],base_t)\n'''
    if old_status not in backend:
        raise SystemExit("flight-session status block not found")
    backend = backend.replace(old_status, new_status, 1)

    old_span = '''                ai_alerts.append(\n                    f'<span class="ai-jump" data-jump-time="{arm_t}">'\n                    f"{icon} <b>Політ №{s['number']}:</b> ARM {arm_t}; {status}. "\n'''
    new_span = '''                ai_alerts.append(\n                    f'<span class="ai-jump flight-session-status {status_class}" data-jump-time="{arm_t}">'\n                    f"{icon} <b>Політ №{s['number']}:</b> ARM {arm_t}; {status}. "\n'''
    if old_span not in backend:
        raise SystemExit("flight-session alert span not found")
    backend = backend.replace(old_span, new_span, 1)

if MARKER not in frontend:
    anchor = '.ai-jump{display:inline-block;width:100%;cursor:pointer}\n'
    styles = '''.ai-jump{display:inline-block;width:100%;cursor:pointer}\n/* PER_FLIGHT_STATUS_SUMMARY_V1 */\n.flight-session-status{\n  display:block;\n  width:100%;\n  padding:9px 11px;\n  border-left:4px solid transparent;\n  border-radius:6px;\n}\n.flight-session-status-ok{border-left-color:#22c55e;background:rgba(34,197,94,.10)}\n.flight-session-status-info{border-left-color:#64748b;background:rgba(100,116,139,.12)}\n.flight-session-status-warning{border-left-color:#f59e0b;background:rgba(245,158,11,.11)}\n.flight-session-status-critical{border-left-color:#ef4444;background:rgba(239,68,68,.13)}\n'''
    if anchor not in frontend:
        raise SystemExit("frontend ai-jump style anchor not found")
    frontend = frontend.replace(anchor, styles, 1)

BACKEND_PATH.write_text(backend, encoding="utf-8")
FRONTEND_PATH.write_text(frontend, encoding="utf-8")
