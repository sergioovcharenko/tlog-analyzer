import unittest
from pathlib import Path


class LazyMavlinkPlotContractTest(unittest.TestCase):
    def test_initial_analyze_does_not_build_dynamic_catalog(self):
        text = Path('backend/main.py').read_text(encoding='utf-8')
        self.assertIn('@app.post("/analyze")', text)
        self.assertIn('# LAZY_MAVLINK_PLOT_ENDPOINT', text)
        analyze_part = text.split('@app.post("/analyze")', 1)[1].split('# LAZY_MAVLINK_PLOT_ENDPOINT', 1)[0]
        self.assertNotIn('mavlink_plot_collector', analyze_part)
        self.assertNotIn('"mavlink_plot": mavlink_plot', analyze_part)

    def test_backend_throttles_dynamic_plot_sampling(self):
        text = Path('backend/main.py').read_text(encoding='utf-8')
        self.assertIn('@app.post("/mavlink-plot")', text)
        self.assertIn('PLOT_SAMPLE_INTERVAL_SEC = 0.10', text)
        self.assertIn('last_plot_sample = {}', text)
        self.assertIn('should_collect =', text)
        self.assertIn('t_stamp - last_sample >= PLOT_SAMPLE_INTERVAL_SEC', text)
        self.assertIn('collector.add(msg_type, msg.to_dict(), t_stamp)', text)
        self.assertIn('"mavlink_plot": collector.build(base_timestamp)', text)
        self.assertIn('async def mavlink_plot_on_demand(token: str)', text)

    def test_frontend_prefetches_once_and_reuses_same_request_on_click(self):
        text = Path('index.html').read_text(encoding='utf-8')
        self.assertIn('async function ensureDynamicMavlinkPlot(result)', text)
        self.assertIn("fetch(API_BASE_URL+'/mavlink-plot?token='", text)
        self.assertIn('result?.plotToken', text)
        self.assertIn('result._mavlinkPlotPromise', text)
        self.assertIn('prefetchDynamicMavlinkPlot(data)', text)
        self.assertIn("graphBtn.onclick=async()=>", text)
        self.assertIn('await ensureDynamicMavlinkPlot(data)', text)
        self.assertIn('Завантаження графіків...', text)
        self.assertNotIn("formData.append('file',selectedFile", text)


if __name__ == '__main__':
    unittest.main()
