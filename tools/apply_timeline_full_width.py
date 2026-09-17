from pathlib import Path

INDEX = Path("index.html")
MARKER = "TIMELINE_FULL_WIDTH_COMPACT_V1"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if old not in source:
        raise SystemExit(f"Timeline layout anchor not found: {label}")
    return source.replace(old, new, 1)


def main() -> None:
    source = INDEX.read_text(encoding="utf-8")
    if MARKER in source:
        return

    timeline_old = """.timeline{\n  position:relative;\n  background:var(--bg-card);\n  border:1px solid var(--border-color);\n  border-radius:8px;\n  overflow-x:auto;\n  margin-bottom:30px\n}\n"""
    timeline_new = """/* TIMELINE_FULL_WIDTH_COMPACT_V1 */\n.timeline{\n  position:relative;\n  width:calc(100vw - 24px);\n  margin-left:calc(50% - 50vw + 12px);\n  margin-right:calc(50% - 50vw + 12px);\n  background:var(--bg-card);\n  border:1px solid var(--border-color);\n  border-radius:8px;\n  overflow-x:auto;\n  margin-bottom:30px\n}\n"""
    source = replace_once(source, timeline_old, timeline_new, "timeline full width")

    source = replace_once(source, "  column-gap:14px;\n  row-gap:5px;\n  min-width:2060px\n", "  column-gap:8px;\n  row-gap:5px;\n  min-width:1970px\n", "desktop column gap")
    source = replace_once(source, "    column-gap:12px;\n    row-gap:4px;\n    min-width:2110px;\n", "    column-gap:7px;\n    row-gap:4px;\n    min-width:2035px;\n", "compact column gap")

    highlight_old = """.timeline-jump-highlight{\n  outline:2px solid #60a5fa;\n  outline-offset:-2px;\n  animation:timelineJumpPulse 1.6s ease-out;\n}\n@keyframes timelineJumpPulse{\n  0%{box-shadow:inset 4px 0 0 #60a5fa,0 0 0 6px rgba(96,165,250,.24)}\n  100%{box-shadow:inset 4px 0 0 #60a5fa,0 0 0 0 rgba(96,165,250,0)}\n}\n"""
    highlight_new = """.timeline-jump-highlight{\n  background:rgba(96,165,250,.16)!important;\n  box-shadow:inset 0 2px 0 #60a5fa,inset 0 -2px 0 #60a5fa,inset 5px 0 0 #60a5fa!important;\n}\n"""
    source = replace_once(source, highlight_old, highlight_new, "jump highlight")

    scrollbar_old = ".timeline-scrollbar-fixed{\n  position:sticky;\n"
    scrollbar_new = ".timeline-scrollbar-fixed{\n  width:calc(100vw - 24px);\n  margin-left:calc(50% - 50vw + 12px);\n  position:sticky;\n"
    source = replace_once(source, scrollbar_old, scrollbar_new, "fixed scrollbar full width")

    INDEX.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
