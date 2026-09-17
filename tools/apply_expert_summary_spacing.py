from pathlib import Path

BACKEND = Path("backend/ai_expert.py")
FRONTEND = Path("index.html")


def patch_backend() -> None:
    source = BACKEND.read_text(encoding="utf-8")
    old = '''            return (\n                "Виявлено декілька незалежних відхилень. "\n                + " ".join(special_parts)\n                + " Причинний зв'язок між цими відхиленнями за самим TLOG не встановлено."\n            )\n        return " ".join(special_parts)\n'''
    new = '''            return (\n                "Виявлено декілька незалежних відхилень.\\n\\n"\n                + "\\n\\n".join(special_parts)\n                + "\\n\\nПричинний зв'язок між цими відхиленнями за самим TLOG не встановлено."\n            )\n        return "\\n\\n".join(special_parts)\n'''
    if old in source:
        source = source.replace(old, new, 1)
    elif '"\\n\\n".join(special_parts)' not in source:
        raise SystemExit("backend summary anchor not found")
    BACKEND.write_text(source, encoding="utf-8")


def patch_frontend() -> None:
    source = FRONTEND.read_text(encoding="utf-8")
    marker = "/* EXPERT_SUMMARY_SECTIONS_V1 */"
    if marker not in source:
        anchor = ".ai-box{\n"
        if anchor not in source:
            raise SystemExit("frontend CSS anchor not found")
        css = '''/* EXPERT_SUMMARY_SECTIONS_V1 */\n.ai-expert-conclusion{\n  white-space:pre-line;\n  margin:14px 0 18px;\n  line-height:1.55;\n}\n\n'''
        source = source.replace(anchor, css + anchor, 1)
    FRONTEND.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    patch_backend()
    patch_frontend()
