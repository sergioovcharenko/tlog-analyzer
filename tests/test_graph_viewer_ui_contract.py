from pathlib import Path
import unittest


class GraphViewerUIContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("index.html").read_text(encoding="utf-8")

    def test_viewer_entry_points_exist(self):
        for marker in (
            'id="graphViewerBtn"',
            'id="graphViewerOverlay"',
            'id="graphMetricSelect"',
            'id="graphCanvas"',
            'id="attitudeHorizon"',
            'id="attitudeScene"',
        ):
            self.assertIn(marker, self.html)

    def test_viewer_functions_exist(self):
        for marker in (
            "function openGraphViewer",
            "function closeGraphViewer",
            "function buildGraphMetricRegistry",
            "function setGraphMetric",
            "function renderGraphSeries",
            "function selectGraphTime",
            "function nearestSampleIndex",
            "function updateAttitudeAtTime",
        ):
            self.assertIn(marker, self.html)

    def test_graph_viewer_does_not_reanalyze_tlog(self):
        start = self.html.index("function openGraphViewer")
        block = self.html[start:start + 9000]
        self.assertNotIn("analyzeOnServer(", block)

    def test_reset_hides_graph_viewer(self):
        start = self.html.index("function resetForm")
        block = self.html[start:start + 1500]
        self.assertIn("closeGraphViewer()", block)
        self.assertIn("graphViewerBtn", block)

    def test_attitude_horizon_v2_has_roll_scale_and_pitch_ladder(self):
        for marker in (
            'class="attitude-roll-scale"',
            'class="attitude-roll-pointer"',
            'id="attitudePitchLadder"',
            'class="attitude-pitch-mark attitude-pitch-major"',
            'data-angle="30"',
            'data-angle="-30"',
        ):
            self.assertIn(marker, self.html)

    def test_attitude_horizon_v2_keeps_numeric_roll_pitch_readouts(self):
        self.assertIn("ROLL", self.html)
        self.assertIn("PITCH", self.html)
        start = self.html.index("function updateAttitudeAtTime")
        block = self.html[start:start + 5000]
        self.assertIn("roll.toFixed(1)", block)
        self.assertIn("pitch.toFixed(1)", block)


if __name__ == "__main__":
    unittest.main()
