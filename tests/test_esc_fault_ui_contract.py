from pathlib import Path
import unittest

HTML = Path('index.html').read_text(encoding='utf-8')


class EscFaultUiContractTests(unittest.TestCase):
    def test_has_persistent_esc_fault_detector(self):
        self.assertIn('function buildEscPowertrainAlerts', HTML)
        self.assertIn('ESC_FAULT_MIN_PERSIST_SEC', HTML)

    def test_single_zero_rpm_is_not_treated_as_failure(self):
        self.assertIn('rpmZeroIsTelemetryOnly', HTML)
        self.assertIn('короткочасна втрата RPM-телеметрії', HTML)

    def test_fault_requires_persistence_and_corroboration(self):
        self.assertIn('currentCorroborated', HTML)
        self.assertIn('persistentRpmDeficit', HTML)
        self.assertIn('ЙМОВІРНА НЕСПРАВНІСТЬ MOTOR/ESC', HTML)

    def test_alert_reports_first_manifestation_phase(self):
        self.assertIn('firstAnomalyTime', HTML)
        self.assertIn('на початку польоту', HTML)
        self.assertIn('у середині польоту', HTML)
        self.assertIn('наприкінці польоту', HTML)


if __name__ == '__main__':
    unittest.main()
