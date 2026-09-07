from pathlib import Path

BACKEND = Path('backend/main.py')
INDEX = Path('index.html')


def patch_backend():
    s = BACKEND.read_text(encoding='utf-8')

    if 'AI_RECONSTRUCTION_IMPORT_V1' not in s:
        anchor = 'app = FastAPI()'
        block = '''# AI_RECONSTRUCTION_IMPORT_V1\ntry:\n    from backend.ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts\nexcept ImportError:\n    from ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts\n\n'''
        if anchor not in s:
            raise SystemExit('backend app anchor not found')
        s = s.replace(anchor, block + anchor, 1)

    if 'AI_RECONSTRUCTION_BACKEND_V1' not in s:
        anchor = '        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)\n'
        block = '''        # AI_RECONSTRUCTION_BACKEND_V1\n        _ai_radio_episodes = []\n        for _ep in communication_loss_episodes:\n            _start = _ep.get("startTimestamp")\n            if not valid_number(_start):\n                continue\n            _ai_radio_episodes.append({\n                "time_s": float(_start) - float(base_t),\n                "dbm": _ep.get("startDbm", -128),\n                "recovered": bool(_ep.get("recovered")),\n                "vtx_changed": bool(_ep.get("vtxChangedAcrossBlindZone")),\n            })\n\n        _ai_mode_transitions = []\n        _ai_altitude_samples = []\n        _ai_vtx_events = []\n        _ai_home_distance_samples = []\n        _ai_prev_mode = None\n        _ai_prev_mode_start = None\n        _ai_prev_vtx = None\n\n        for _row in timeline:\n            if not isinstance(_row, dict) or _row.get("eventType") != "SNAPSHOT":\n                continue\n            _t_ms = _timeline_graph_time_ms(_row.get("time"))\n            if _t_ms is None:\n                continue\n            _t_s = float(_t_ms) / 1000.0\n\n            _mode = str(_row.get("mode") or "").strip()\n            if _mode and _mode != _ai_prev_mode:\n                if _ai_prev_mode is not None and _ai_prev_mode_start is not None:\n                    _ai_mode_transitions.append({\n                        "from": _ai_prev_mode,\n                        "to": _mode,\n                        "time_s": _t_s,\n                        "delta_s": max(0.0, _t_s - _ai_prev_mode_start),\n                    })\n                _ai_prev_mode = _mode\n                _ai_prev_mode_start = _t_s\n\n            _alt = _graph_numeric(_row.get("alt"))\n            if valid_number(_alt):\n                _ai_altitude_samples.append({"time_s": _t_s, "altitude_m": float(_alt)})\n\n            _freq = _graph_numeric(_row.get("videoFreq"))\n            if valid_number(_freq):\n                _freq = int(round(float(_freq)))\n                if _ai_prev_vtx is not None and _freq != _ai_prev_vtx:\n                    _ai_vtx_events.append({"time_s": _t_s, "frequency": _freq})\n                _ai_prev_vtx = _freq\n\n            _dist_raw = _row.get("dist")\n            _dist = _graph_numeric(_dist_raw)\n            if valid_number(_dist):\n                _dist = float(_dist)\n                _dist_text = str(_dist_raw or "").lower()\n                if "km" in _dist_text or "км" in _dist_text:\n                    _dist *= 1000.0\n                _ai_home_distance_samples.append({"time_s": _t_s, "distance_m": _dist})\n\n        _ai_power_metrics = {\n            "potential_thrust_loss_count": len(potential_thrust_loss_events),\n            "rpm_asymmetry_pct": max(\n                [float(e.get("differencePct")) for e in rpm_drop_events if valid_number(e.get("differencePct"))] or [0.0]\n            ),\n            "min_voltage_v": float(min_voltage) if valid_number(min_voltage) and float(min_voltage) > 0 else None,\n            "max_current_a": float(max_current) if valid_number(max_current) else None,\n        }\n\n        ai_reconstruction_facts = build_ai_reconstruction_facts(\n            radio_loss_episodes=_ai_radio_episodes,\n            mode_transitions=_ai_mode_transitions,\n            altitude_samples=_ai_altitude_samples,\n            vtx_events=_ai_vtx_events,\n            home_distance_samples=_ai_home_distance_samples,\n            ended_armed=log_ended_armed,\n            power_metrics=_ai_power_metrics,\n        )\n        ai_reconstruction = build_ai_reconstruction(ai_reconstruction_facts)\n\n'''
        if anchor not in s:
            raise SystemExit('backend graph_data anchor not found')
        s = s.replace(anchor, block + anchor, 1)

    # Upgrade an already-generated V1 block without duplicating it.
    old = '                "recovered": bool(_ep.get("recovered")),\n            })'
    new = '                "recovered": bool(_ep.get("recovered")),\n                "vtx_changed": bool(_ep.get("vtxChangedAcrossBlindZone")),\n            })'
    if old in s and '"vtx_changed": bool(_ep.get("vtxChangedAcrossBlindZone"))' not in s:
        s = s.replace(old, new, 1)

    if '"ai_reconstruction": ai_reconstruction,' not in s:
        anchor = '            "board_messages": board_messages,\n            "ai": {'
        replacement = '            "board_messages": board_messages,\n            "ai_reconstruction": ai_reconstruction,\n            "ai": {'
        if anchor not in s:
            raise SystemExit('backend response anchor not found')
        s = s.replace(anchor, replacement, 1)

    BACKEND.write_text(s, encoding='utf-8')


def patch_frontend():
    s = INDEX.read_text(encoding='utf-8')

    if 'AI_RECONSTRUCTION_V1' not in s:
        anchor = '''    <div id="aiBlock" class="ai-box">\n      <h3 id="aiTitle" class="ai-title"></h3>\n      <ul id="aiAlerts" class="ai-list"></ul>\n    </div>\n'''
        block = '''\n    <!-- AI_RECONSTRUCTION_V1 -->\n    <section id="aiReconstructionBlock" class="ai-reconstruction" hidden>\n      <h3>🤖 AI ВИСНОВОК</h3>\n      <div id="aiReconWhat"></div>\n      <div id="aiReconSequence"></div>\n      <div id="aiReconActions"></div>\n      <div id="aiReconAlternatives"></div>\n      <div id="aiReconConfidence"></div>\n    </section>\n'''
        if anchor not in s:
            raise SystemExit('frontend aiBlock anchor not found')
        s = s.replace(anchor, anchor + block, 1)

    if 'AI_RECONSTRUCTION_STYLE_V1' not in s:
        css = '''\n<style>\n/* AI_RECONSTRUCTION_STYLE_V1 */\n.ai-reconstruction{background:var(--bg-card);border:1px solid var(--border-color);border-left:4px solid #38bdf8;border-radius:8px;padding:20px 22px;margin:-14px 0 30px}\n.ai-reconstruction[hidden]{display:none!important}\n.ai-reconstruction h3{margin:0 0 12px;color:#7dd3fc;font-size:18px}\n.ai-reconstruction h4{margin:12px 0 5px;color:var(--text-muted);font-size:12px;text-transform:uppercase;letter-spacing:.35px}\n.ai-reconstruction ul{margin:0;padding-left:20px;line-height:1.5}\n.ai-reconstruction li{margin:3px 0}\n#aiReconConfidence{margin-top:13px;padding-top:10px;border-top:1px solid var(--border-color);font-weight:800;color:#cbd5e1}\n</style>\n'''
        if '</head>' not in s:
            raise SystemExit('frontend head anchor not found')
        s = s.replace('</head>', css + '\n</head>', 1)

    if 'function renderAiReconstruction(recon)' not in s:
        anchor = 'function renderResults(data){'
        renderer = '''function renderAiReconstruction(recon){\n  const block=document.getElementById('aiReconstructionBlock');\n  if(!block||!recon){if(block)block.hidden=true;return;}\n  const sections=[\n    ['aiReconWhat','Що сталося',recon.what_happened],\n    ['aiReconSequence','Ймовірна послідовність',recon.likely_sequence],\n    ['aiReconActions','Дії, зафіксовані в TLOG',recon.pilot_actions],\n    ['aiReconAlternatives','Що могло допомогти',recon.possible_alternatives],\n  ];\n  sections.forEach(([id,title,items])=>{\n    const host=document.getElementById(id);if(!host)return;\n    host.replaceChildren();\n    if(!Array.isArray(items)||!items.length)return;\n    const h=document.createElement('h4');h.textContent=title;\n    const ul=document.createElement('ul');\n    items.forEach(text=>{const li=document.createElement('li');li.textContent=String(text);ul.appendChild(li);});\n    host.append(h,ul);\n  });\n  const confidence=document.getElementById('aiReconConfidence');\n  if(confidence)confidence.textContent=`Впевненість аналізу: ${recon.confidence||'Низька'}`;\n  block.dataset.scenario=String(recon.dominant_scenario||'none');\n  block.hidden=false;\n}\n\n'''
        if anchor not in s:
            raise SystemExit('frontend renderResults anchor not found')
        s = s.replace(anchor, renderer + anchor, 1)

    if 'renderAiReconstruction(data.ai_reconstruction);' not in s:
        anchor = "  aiTitle.textContent=data.ai?.verdict||'Результати';"
        if anchor not in s:
            raise SystemExit('frontend aiTitle render anchor not found')
        s = s.replace(anchor, anchor + '\n  renderAiReconstruction(data.ai_reconstruction);', 1)

    INDEX.write_text(s, encoding='utf-8')


patch_backend()
patch_frontend()
print('Applied AI reconstruction backend + frontend integration')
