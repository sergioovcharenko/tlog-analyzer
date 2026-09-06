from pathlib import Path
import unittest

class Contract(unittest.TestCase):
    def test_layout_contract(self):
        s=Path('index.html').read_text(encoding='utf-8')
        self.assertIn('GRAPH_HORIZON_BOARD_MESSAGES_V1', s)
        self.assertIn("const messages=document.getElementById('boardMessagesPanel');", s)
        self.assertIn("messages.classList.add('attitude-board-messages');", s)
        self.assertIn("attitudePanel.appendChild(messages)", s)
        self.assertIn("messages.hidden=false", s)
        self.assertIn('#attitudePanel .attitude-board-messages', s)
        self.assertIn('#attitudePanel .attitude-board-messages #boardMessagesList', s)

if __name__=='__main__':
    unittest.main()
