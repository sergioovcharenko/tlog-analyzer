from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


class AttitudeDbmColorsContract(unittest.TestCase):
    """Contract for live graph dBm quality coloring in the avionics panel."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_threshold_helper_exists(self):
        self.assertIn("function attitudeDbmClass(dbm)", self.html)
        self.assertIn("if(v>=-85)return 'attitude-dbm-good'", self.html)
        self.assertIn("if(v>=-99)return 'attitude-dbm-warning'", self.html)
        self.assertIn("return 'attitude-dbm-danger'", self.html)

    def test_three_visual_states_exist(self):
        self.assertIn(".attitude-dbm-good", self.html)
        self.assertIn(".attitude-dbm-warning", self.html)
        self.assertIn(".attitude-dbm-danger", self.html)
        self.assertIn("#22c55e", self.html)
        self.assertIn("#f59e0b", self.html)
        self.assertIn("#ef4444", self.html)

    def test_attitude_dbm_is_recolored_each_graph_update(self):
        self.assertIn("dbmEl.classList.remove('attitude-dbm-good','attitude-dbm-warning','attitude-dbm-danger')", self.html)
        self.assertIn("const dbmClass=attitudeDbmClass(dbm);", self.html)
        self.assertIn("if(dbmClass)dbmEl.classList.add(dbmClass);", self.html)


if __name__ == "__main__":
    unittest.main()
