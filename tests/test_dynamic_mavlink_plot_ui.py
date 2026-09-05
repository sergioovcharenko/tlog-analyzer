from pathlib import Path
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")


class DynamicMavlinkPlotUiTest(unittest.TestCase):
    def test_field_browser_exists(self):
        for marker in (
            'id="mavlinkPlotPanel"',
            'id="mavlinkPlotSearch"',
            'id="mavlinkPlotGroups"',
            'id="mavlinkPlotClear"',
            'function buildDynamicMavlinkCatalog()',
            'function renderMavlinkFieldBrowser()',
            'function setMavlinkSeriesSelected(id,checked)',
        ):
            self.assertIn(marker, HTML)

    def test_multiseries_renderer_has_deterministic_colors_and_unit_groups(self):
        for marker in (
            'selectedSeries:new Set()',
            'seriesColors:new Map()',
            'function seriesColorFor(id)',
            'function groupSeriesByUnit(series)',
            'function activeGraphSeries()',
            'MAX_DYNAMIC_UNIT_GROUPS=4',
        ):
            self.assertIn(marker, HTML)

    def test_board_message_panel_exists_and_is_time_bounded(self):
        for marker in (
            'id="boardMessagesPanel"',
            'id="boardMessagesList"',
            'ПОВІДОМЛЕННЯ БОРТА',
            'const BOARD_MESSAGE_WINDOW_MS=5000',
            'function renderBoardMessagesAtTime(timeMs)',
            'board-message-error',
            'board-message-warning',
            'board-message-info',
            'board-message-recovery',
        ):
            self.assertIn(marker, HTML)

    def test_graph_time_selection_updates_board_messages(self):
        self.assertIn('renderBoardMessagesAtTime(timeMs)', HTML)
        self.assertIn('renderBoardMessagesAtTime(graphViewerState.selectedTimeMs)', HTML)


if __name__ == "__main__":
    unittest.main()
