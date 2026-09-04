from pathlib import Path

path = Path("index.html")
html = path.read_text(encoding="utf-8")

old_css = '''#attitudeHorizon{width:250px;height:250px;max-width:100%;aspect-ratio:1;border:7px solid #27364a;border-radius:50%;overflow:hidden;position:relative;margin:0 auto 12px;background:#111827;box-shadow:inset 0 0 0 2px #0f172a}
#attitudeScene{position:absolute;left:50%;top:50%;width:180%;height:180%;transform:translate(-50%,-50%);transform-origin:50% 50%;background:linear-gradient(to bottom,#2b78c5 0%,#4f9ad7 49.4%,#f5f5f4 49.5%,#f5f5f4 50.5%,#8a5a36 50.6%,#5f3b27 100%);will-change:transform}
.attitude-pitch-line{position:absolute;left:50%;top:50%;width:34%;height:1px;background:rgba(255,255,255,.82);transform:translate(-50%,-50%)}
.attitude-pitch-line::before,.attitude-pitch-line::after{content:'';position:absolute;top:-44px;width:50%;height:1px;background:rgba(255,255,255,.45)}
.attitude-pitch-line::before{left:25%}.attitude-pitch-line::after{left:25%;top:44px}
.attitude-aircraft{position:absolute;left:50%;top:50%;width:54%;height:4px;background:#facc15;transform:translate(-50%,-50%);z-index:3;box-shadow:0 0 0 1px #111827}
.attitude-aircraft::before,.attitude-aircraft::after{content:'';position:absolute;top:-5px;width:22px;height:14px;border-top:4px solid #facc15}
.attitude-aircraft::before{left:-2px;transform:rotate(18deg)}.attitude-aircraft::after{right:-2px;transform:rotate(-18deg)}
.attitude-center-dot{position:absolute;left:50%;top:50%;width:8px;height:8px;border-radius:50%;background:#facc15;transform:translate(-50%,-50%);z-index:4}
.attitude-values{display:grid;grid-template-columns:1fr 1fr;gap:7px;font:12px monospace}
.attitude-value{border:1px solid #253246;border-radius:6px;padding:8px;background:#080d13}.attitude-value b{display:block;color:#7dd3fc;margin-bottom:2px}'''

new_css = '''#attitudeHorizon{width:264px;height:264px;max-width:100%;aspect-ratio:1;border:7px solid #27364a;border-radius:50%;overflow:hidden;position:relative;margin:0 auto 12px;background:#111827;box-shadow:inset 0 0 0 2px #0f172a,0 0 24px rgba(56,189,248,.08)}
#attitudeScene{position:absolute;left:50%;top:50%;width:190%;height:190%;transform:translate(-50%,-50%);transform-origin:50% 50%;background:linear-gradient(to bottom,#2b78c5 0%,#4f9ad7 49.4%,#f5f5f4 49.5%,#f5f5f4 50.5%,#8a5a36 50.6%,#5f3b27 100%);will-change:transform}
.attitude-pitch-line{position:absolute;left:50%;top:50%;width:42%;height:2px;background:rgba(255,255,255,.94);transform:translate(-50%,-50%);box-shadow:0 1px 1px rgba(0,0,0,.45)}
#attitudePitchLadder{position:absolute;inset:0;z-index:1;pointer-events:none}
.attitude-pitch-mark{position:absolute;left:50%;top:calc(50% + var(--y));width:52%;height:14px;transform:translate(-50%,-50%);color:rgba(255,255,255,.9);font:700 9px/14px monospace;text-shadow:0 1px 2px #000}
.attitude-pitch-mark::before{content:'';position:absolute;left:27%;right:27%;top:50%;height:1px;background:rgba(255,255,255,.70);box-shadow:0 1px 1px rgba(0,0,0,.5)}
.attitude-pitch-mark span{position:absolute;top:0}.attitude-pitch-mark span:first-child{left:4%}.attitude-pitch-mark span:last-child{right:4%}
.attitude-pitch-major{font-size:10px;color:#fff}.attitude-pitch-major::before{left:20%;right:20%;height:2px;background:rgba(255,255,255,.96)}
.attitude-roll-scale{position:absolute;inset:0;z-index:5;pointer-events:none}
.attitude-roll-mark{position:absolute;left:50%;top:50%;width:24px;height:12px;margin-left:-12px;margin-top:-6px;transform-origin:12px 6px;transform:rotate(var(--a)) translateY(-111px);color:#f8fafc;font:800 9px/12px monospace;text-align:center;text-shadow:0 1px 2px #000}
.attitude-roll-mark::after{content:'';position:absolute;left:50%;top:13px;width:2px;height:7px;background:rgba(255,255,255,.9);transform:translateX(-50%);border-radius:2px}
.attitude-roll-mark.major::after{height:10px;background:#fff}
.attitude-roll-pointer{position:absolute;left:50%;top:7px;z-index:7;width:0;height:0;transform:translateX(-50%);border-left:7px solid transparent;border-right:7px solid transparent;border-top:0;border-bottom:13px solid #facc15;filter:drop-shadow(0 1px 2px #000);pointer-events:none}
.attitude-aircraft{position:absolute;left:50%;top:50%;width:58%;height:4px;background:#facc15;transform:translate(-50%,-50%);z-index:6;box-shadow:0 0 0 1px #111827,0 0 4px rgba(250,204,21,.35)}
.attitude-aircraft::before,.attitude-aircraft::after{content:'';position:absolute;top:-5px;width:22px;height:14px;border-top:4px solid #facc15}
.attitude-aircraft::before{left:-2px;transform:rotate(18deg)}.attitude-aircraft::after{right:-2px;transform:rotate(-18deg)}
.attitude-center-dot{position:absolute;left:50%;top:50%;width:9px;height:9px;border-radius:50%;background:#facc15;transform:translate(-50%,-50%);z-index:7;box-shadow:0 0 0 2px #111827}
.attitude-values{display:grid;grid-template-columns:1fr 1fr;gap:7px;font:12px monospace}
.attitude-value{border:1px solid #253246;border-radius:6px;padding:8px;background:#080d13}.attitude-value b{display:block;color:#7dd3fc;margin-bottom:2px}
.attitude-value:nth-child(1),.attitude-value:nth-child(2){font-size:16px;font-weight:900;border-color:#334e68}.attitude-value:nth-child(1) b,.attitude-value:nth-child(2) b{font-size:10px;letter-spacing:.08em}'''

if old_css not in html:
    if ".attitude-roll-scale" not in html:
        raise SystemExit("attitude CSS anchor not found")
else:
    html = html.replace(old_css, new_css, 1)

old_markup = '''        <div id="attitudeHorizon" aria-label="Авіагоризонт">
          <div id="attitudeScene"><div class="attitude-pitch-line"></div></div>
          <div class="attitude-aircraft"></div><div class="attitude-center-dot"></div>
        </div>'''

new_markup = '''        <div id="attitudeHorizon" aria-label="Авіагоризонт з шкалою крену і тангажу">
          <div id="attitudeScene">
            <div class="attitude-pitch-line"></div>
            <div id="attitudePitchLadder">
              <div class="attitude-pitch-mark attitude-pitch-major" data-angle="30" style="--y:-66px"><span>30</span><span>30</span></div>
              <div class="attitude-pitch-mark" data-angle="20" style="--y:-44px"><span>20</span><span>20</span></div>
              <div class="attitude-pitch-mark" data-angle="10" style="--y:-22px"><span>10</span><span>10</span></div>
              <div class="attitude-pitch-mark" data-angle="-10" style="--y:22px"><span>-10</span><span>-10</span></div>
              <div class="attitude-pitch-mark" data-angle="-20" style="--y:44px"><span>-20</span><span>-20</span></div>
              <div class="attitude-pitch-mark attitude-pitch-major" data-angle="-30" style="--y:66px"><span>-30</span><span>-30</span></div>
            </div>
          </div>
          <div class="attitude-roll-scale" aria-hidden="true">
            <span class="attitude-roll-mark major" style="--a:-60deg">60</span>
            <span class="attitude-roll-mark" style="--a:-45deg">45</span>
            <span class="attitude-roll-mark major" style="--a:-30deg">30</span>
            <span class="attitude-roll-mark" style="--a:-20deg">20</span>
            <span class="attitude-roll-mark" style="--a:-10deg">10</span>
            <span class="attitude-roll-mark major" style="--a:0deg">0</span>
            <span class="attitude-roll-mark" style="--a:10deg">10</span>
            <span class="attitude-roll-mark" style="--a:20deg">20</span>
            <span class="attitude-roll-mark major" style="--a:30deg">30</span>
            <span class="attitude-roll-mark" style="--a:45deg">45</span>
            <span class="attitude-roll-mark major" style="--a:60deg">60</span>
          </div>
          <div class="attitude-roll-pointer" aria-hidden="true"></div>
          <div class="attitude-aircraft"></div><div class="attitude-center-dot"></div>
        </div>'''

if old_markup not in html:
    if 'id="attitudePitchLadder"' not in html:
        raise SystemExit("attitude markup anchor not found")
else:
    html = html.replace(old_markup, new_markup, 1)

path.write_text(html, encoding="utf-8")
print("Applied attitude horizon v2: roll scale, pitch ladder, larger angle readouts")
