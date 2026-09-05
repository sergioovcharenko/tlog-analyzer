from pathlib import Path
import unittest


class FastSingleUploadPlotContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = Path('backend/main.py').read_text(encoding='utf-8')
        cls.frontend = Path('index.html').read_text(encoding='utf-8')

    def test_main_analyzer_uses_filtered_mavlink_messages(self):
        self.assertIn('needed_messages = [', self.backend)
        self.assertIn('mav.recv_match(type=needed_messages, blocking=False)', self.backend)

    def test_analyze_returns_server_side_plot_token(self):
        self.assertIn('"plotToken": plot_token', self.backend)
        self.assertIn('PLOT_FILE_CACHE', self.backend)

    def test_plot_endpoint_uses_token_not_second_file_upload(self):
        self.assertIn('async def mavlink_plot_on_demand(token: str)', self.backend)
        endpoint = self.backend.split('# LAZY_MAVLINK_PLOT_ENDPOINT', 1)[1]
        self.assertNotIn('file: UploadFile', endpoint)

    def test_frontend_requests_plot_by_token(self):
        self.assertIn("result?.plotToken", self.frontend)
        self.assertIn("'/mavlink-plot?token='", self.frontend)
        self.assertNotIn("formData.append('file',selectedFile", self.frontend)


if __name__ == '__main__':
    unittest.main()
