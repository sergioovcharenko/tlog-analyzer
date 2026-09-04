from pathlib import Path
import unittest


class AttitudeDashboardV22ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("index.html").read_text(encoding="utf-8")
        cls.backend = Path("backend/main.py").read_text(encoding="utf-8")

    def test_dashboard_has_requested_live_readouts(self):
        for marker in (
            'id="attitudeRssi"',
            'id="attitudeDbm"',
            'ТЕМПЕРАТУРА FC',
            'СПОЖИВАННЯ СТРУМУ',
            'ENGINE LOAD',
        ):
            self.assertIn(marker, self.html)

    def test_horizon_ground_is_green(self):
        self.assertIn('#2f7d32', self.html)

    def test_attitude_update_reads_requested_series(self):
        for marker in (
            'rssi_pct',
            'radio_dbm',
            'fc_temp_c',
            'current_a',
            'engine_load_pct',
        ):
            self.assertIn(marker, self.html)

    def test_backend_exports_rssi_and_fc_temperature_graph_series(self):
        for marker in (
            '"rssi_time_ms", "rssi_pct"',
            '"fc_temp_time_ms", "fc_temp_c"',
        ):
            self.assertIn(marker, self.backend)

    def test_roll_pointer_moves_with_bank_angle(self):
        self.assertIn('id="attitudeRollPointer"', self.html)
        self.assertIn("document.getElementById('attitudeRollPointer')", self.html)
        self.assertIn("pointer.style.transform=`translate(-50%,-50%) rotate(${-roll}deg) translateY(-112px)`", self.html)


if __name__ == "__main__":
    unittest.main()
