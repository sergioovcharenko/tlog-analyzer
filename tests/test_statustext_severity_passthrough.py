from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "backend" / "main.py"


class StatustextSeverityPassthroughTest(unittest.TestCase):
    def test_add_event_accepts_and_persists_mavlink_severity(self):
        tree = ast.parse(MAIN.read_text(encoding="utf-8"))
        add_event = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "add_event"
        )
        arg_names = [arg.arg for arg in add_event.args.args]
        self.assertIn(
            "severity",
            arg_names,
            "process_complete_statustext passes severity=..., but add_event must accept it",
        )

        persists_severity = False
        for node in ast.walk(add_event):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "severity"
                    and isinstance(value, ast.Name)
                    and value.id == "severity"
                ):
                    persists_severity = True
                    break
        self.assertTrue(
            persists_severity,
            "raw timeline event must preserve MAVLink severity for board-message classification",
        )

    def test_statustext_handler_passes_severity_to_add_event(self):
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("severity=severity", source)
        self.assertIn('event_type = "POTENTIAL_THRUST_LOSS" if thrust_match else "SYSTEM"', source)


if __name__ == "__main__":
    unittest.main()
