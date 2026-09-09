import unittest

from backend.console_diagnostics import describe_console_message


class ConsoleDiagnosticsKnowledgeTests(unittest.TestCase):
    def test_mag_anomaly_and_alignment(self):
        d = describe_console_message('EKF3 IMU0 MAG0 ground mag anomaly, yaw re-aligned')
        self.assertEqual(d['category'], 'MAG/COMPASS')
        self.assertEqual(d['level'], 'WARNING')
        self.assertIn('IMU0', d['summary'])
        self.assertIn('MAG0', d['summary'])
        self.assertIn('повторно вирівняв курс', d['summary'])

        d = describe_console_message('EKF3 IMU1 MAG0 in-flight yaw alignment complete')
        self.assertEqual(d['category'], 'MAG/COMPASS')
        self.assertEqual(d['level'], 'INFO')
        self.assertIn('IMU1', d['summary'])

    def test_lane_switch_and_primary_change(self):
        d = describe_console_message('EKF3 lane switch 1')
        self.assertEqual(d['category'], 'EKF')
        self.assertEqual(d['level'], 'CRITICAL')
        self.assertIn('lane 1', d['summary'])
        self.assertNotIn('перемикався між барометром та акселерометром', d['summary'])

        d = describe_console_message('EKF primary changed 0')
        self.assertEqual(d['category'], 'EKF')
        self.assertEqual(d['level'], 'WARNING')
        self.assertIn('0', d['summary'])

    def test_gyro_not_calibrated_is_gyro_not_accel(self):
        d = describe_console_message('PreArm: Gyros not calibrated')
        self.assertEqual(d['category'], 'IMU/GYRO')
        self.assertIn('гіроскоп', d['summary'].lower())
        self.assertNotIn('калібрування акселерометра', d['summary'].lower())

    def test_yaw_inconsistent_extracts_degrees(self):
        d = describe_console_message('PreArm: AHRS: EKF3 Yaw inconsistent 37 deg. Wait or reboot.')
        self.assertEqual(d['category'], 'YAW')
        self.assertEqual(d['level'], 'CRITICAL')
        self.assertEqual(d['values']['yaw_delta_deg'], 37.0)
        self.assertIn('37', d['summary'])

    def test_yaw_imbalance_extracts_percent(self):
        d = describe_console_message('Yaw imbalance (46%)')
        self.assertEqual(d['category'], 'YAW')
        self.assertEqual(d['level'], 'EMERGENCY')
        self.assertEqual(d['values']['imbalance_pct'], 46.0)

    def test_potential_thrust_loss_extracts_motor(self):
        d = describe_console_message('Potential Thrust Loss (3)')
        self.assertEqual(d['category'], 'THRUST/MOTOR')
        self.assertEqual(d['level'], 'EMERGENCY')
        self.assertEqual(d['values']['motor'], 3)
        self.assertIn('Motor 3', d['summary'])

    def test_visual_navigation_and_camera_messages(self):
        for text in (
            'Bad synchronization. Probably due to poor lightning.',
            "couldn't match keypoints",
            'Camera restarted: use AltHold',
        ):
            d = describe_console_message(text)
            self.assertIn(d['category'], ('VISUAL NAV', 'CAMERA'))
            self.assertTrue(d['summary'])

    def test_terrain_and_need_position(self):
        d = describe_console_message('Terrain: clamping offset -58 to -30')
        self.assertEqual(d['category'], 'TERRAIN')
        self.assertEqual(d['level'], 'INFO')
        self.assertIn('некрит', d['summary'].lower())

        d = describe_console_message('PreArm: Need Position Estimate')
        self.assertEqual(d['category'], 'PREARM')
        self.assertIn('position', d['summary'].lower())

    def test_unknown_message_returns_none(self):
        self.assertIsNone(describe_console_message('some completely unknown message'))


if __name__ == '__main__':
    unittest.main()
