from pathlib import Path
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")


class SdShActivityAlertContract(unittest.TestCase):
    def test_sd_and_sh_activity_is_reported_even_without_confirmed_emergency_stop(self):
        required = [
            "const sdTransitions=[];",
            "const shActivations=[];",
            "let prevSf=null, prevSh=null, prevScPos=null, prevSdPos=null;",
            "sdTransitions.push({time:row.time||'',from:prevSdPos,to:sdPos});",
            "shActivations.push({time:row.time||'',sdPos,pwm:rcPwmValue(row,6)});",
            "SD: зафіксовано",
            "SH: зафіксовано",
            "SD/SH активувались, але одночасну команду EMERGENCY STOP не підтверджено",
            "SD+SH — EMERGENCY STOP",
        ]
        for marker in required:
            self.assertIn(marker, HTML, marker)

        # Existing safety gate must stay unchanged: Emergency Stop is confirmed only
        # when SH rises while SD is in the armed/allowed position.
        self.assertIn("if(prevSh===false && sh===true && sdPos===3)", HTML)
        self.assertIn("EMERGENCY STOP АКТИВОВАНО", HTML)


if __name__ == "__main__":
    unittest.main()
