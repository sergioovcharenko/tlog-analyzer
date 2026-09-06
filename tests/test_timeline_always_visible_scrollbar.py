from pathlib import Path
import unittest

HTML = Path('index.html').read_text(encoding='utf-8')


class TimelineAlwaysVisibleScrollbarContract(unittest.TestCase):
    def test_fixed_scrollbar_overlay_contract(self):
        self.assertIn('/* TIMELINE_ALWAYS_VISIBLE_SCROLLBAR_V1 */', HTML)
        self.assertIn('.timeline-scrollbar-fixed{position:fixed!important', HTML.replace('\n',''))
        self.assertIn('function updateTimelineFloatingScrollbar()', HTML)
        self.assertIn("window.addEventListener('scroll',updateTimelineFloatingScrollbar", HTML)
        self.assertIn("fixedBar.style.left=rect.left+'px'", HTML)
        self.assertIn("fixedBar.style.width=rect.width+'px'", HTML)
        self.assertIn('rect.top<window.innerHeight&&rect.bottom>0', HTML.replace(' ',''))
        self.assertIn('fixedBar.scrollLeft=timeline.scrollLeft', HTML)
        self.assertIn('timeline.scrollLeft=fixedBar.scrollLeft', HTML)


if __name__ == '__main__':
    unittest.main()
