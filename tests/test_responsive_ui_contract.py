from pathlib import Path
import unittest

HTML = Path('index.html').read_text(encoding='utf-8')


class ResponsiveUIContract(unittest.TestCase):
    def test_has_responsive_v1_layer_and_breakpoints(self):
        for marker in (
            'RESPONSIVE V1',
            '@media (max-width:1199px)',
            '@media (max-width:767px)',
            '@media (max-width:430px)',
        ):
            self.assertIn(marker, HTML)

    def test_mobile_timeline_becomes_cards_not_1940px_table(self):
        for marker in (
            '.timeline .tl-header{display:none}',
            '.timeline .tl-item{',
            'grid-template-columns:repeat(2,minmax(0,1fr))',
            '.tl-item>div::before',
            'content:attr(data-mobile-label)',
            '.timeline .sticks-detail{',
            '.timeline-floating-header,.timeline-scrollbar-fixed{display:none!important}',
        ):
            self.assertIn(marker, HTML)

    def test_mobile_labels_match_real_timeline_column_order(self):
        self.assertIn('applyMobileTimelineLabels()', HTML)
        self.assertIn('cell.dataset.mobileLabel', HTML)
        for label in (
            'ЧАС', 'MODE', 'ALT', 'ДАЛЬНІСТЬ', 'АЗИМУТ', 'VTX / VIDEO',
            'BAT', 'CURRENT', 'RSSI', 'dBm', 'ENGINE LOAD', 'TEMP FC / ESC',
            'ПОВІДОМЛЕННЯ', 'АНАЛІЗ', 'TX16S', 'ДІЯ ПІЛОТА'
        ):
            self.assertIn(label, HTML)

    def test_graph_map_tx16_and_mavlink_have_mobile_overrides(self):
        for marker in (
            '.graph-viewer-layout{grid-template-columns:1fr}',
            '#attitudePanel{width:100%',
            '#mavlinkPlotGroups{grid-template-columns:1fr}',
            '.responsive-map-layout{grid-template-columns:1fr!important}',
            'class="responsive-map-layout"',
            '.tx16-panel',
            'bindResponsiveGraphTouch()',
        ):
            self.assertIn(marker, HTML)

    def test_touch_targets_and_no_page_horizontal_overflow(self):
        for marker in (
            'html,body{max-width:100%;overflow-x:hidden}',
            'min-height:44px',
            'touch-action:manipulation',
            '#graphViewerBtn{left:8px!important;right:8px!important',
        ):
            self.assertIn(marker, HTML)


if __name__ == '__main__':
    unittest.main()
