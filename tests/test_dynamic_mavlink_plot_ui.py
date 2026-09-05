from pathlib import Path
import re
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

    def test_board_message_panel_lists_raw_board_messages_for_whole_flight(self):
        for marker in (
            'id="boardMessagesPanel"',
            'id="boardMessagesList"',
            'ПОВІДОМЛЕННЯ БОРТА',
            'STATUSTEXT від борта',
            'function renderBoardMessagesAtTime(timeMs)',
            'board-message-error',
            'board-message-warning',
            'board-message-info',
            'board-message-recovery',
            'board-message-current',
        ):
            self.assertIn(marker, HTML)
        body = re.search(r"function renderBoardMessagesAtTime\(timeMs\)\{.*?\n\}", HTML, re.S)
        self.assertIsNotNone(body)
        self.assertNotIn('Math.abs(Number(m.time_ms)-timeMs)<=BOARD_MESSAGE_WINDOW_MS', body.group(0))
        self.assertIn('messages.slice()', body.group(0))

    def test_graph_time_selection_updates_board_messages(self):
        self.assertIn('renderBoardMessagesAtTime(timeMs)', HTML)
        self.assertIn('renderBoardMessagesAtTime(graphViewerState.selectedTimeMs)', HTML)


if __name__ == "__main__":
    unittest.main()
