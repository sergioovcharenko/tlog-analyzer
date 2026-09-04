from pathlib import Path
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")


class Tx16UiContractTests(unittest.TestCase):
    def test_confirmed_tx16_channel_labels_are_present_without_camera_controls(self):
        for label in (
            "SA — CH7", "SB — CH8", "SC — CH15", "SF — CH10",
            "SD — CH13", "SH — CH6",
        ):
            self.assertIn(label, HTML)
        self.assertNotIn("LS — CH12", HTML)
        self.assertNotIn("RS — CH9", HTML)
        self.assertNotIn("chip('LS','ls')", HTML)
        self.assertNotIn("chip('RS','rs')", HTML)

    def test_obsolete_fc_fs_labels_are_removed(self):
        self.assertNotIn("FC — CH15", HTML)
        self.assertNotIn("FS — CH11", HTML)

    def test_dual_drop_sc_states_are_named_by_safety_function(self):
        self.assertIn("function tx16DualDropSafetyState", HTML)
        self.assertIn("ЗАПОБІЖНИК АКТИВОВАНИЙ", HTML)
        self.assertIn("ЗНЯТО З ЗАПОБІЖНИКА (R)", HTML)
        self.assertIn("ЗНЯТО З ЗАПОБІЖНИКА (L)", HTML)
        self.assertIn("sc:tx16DualDropSafetyState(r.sc)", HTML)

    def test_single_drop_sd_states_and_sh_activation(self):
        self.assertIn("function tx16SingleDropSafetyState", HTML)
        self.assertIn("sd:tx16SingleDropSafetyState(r.sd)", HTML)
        self.assertIn("if(prevSh===false && sh===true && sdPos===3)", HTML)
        self.assertIn("ОДИНОЧНИЙ СКИД", HTML)

    def test_dual_drop_requires_sc_r_or_l_before_sf_rising_edge(self):
        self.assertIn("if(prevSf===false && sf===true)", HTML)
        self.assertIn("if(scPos===2||scPos===3)", HTML)
        self.assertIn("const side=scPos===2?'R':'L';", HTML)
        self.assertIn("<b>СКИД ${ev.side}", HTML)

    def test_sc_sf_activity_is_reported_even_without_valid_drop(self):
        self.assertIn("scTransitions", HTML)
        self.assertIn("sfActivations", HTML)
        self.assertIn("SC: зафіксовано", HTML)
        self.assertIn("SF: зафіксовано", HTML)
        self.assertIn("валідний скид не підтверджено", HTML)

    def test_old_emergency_stop_semantics_are_removed(self):
        self.assertNotIn("EMERGENCY STOP", HTML)
        self.assertNotIn("SD=ДО СЕБЕ + SH", HTML)
        self.assertNotIn("emergency-control", HTML)
        self.assertIn("single-drop-control", HTML)

    def test_drop_groups_keep_distinct_colors(self):
        self.assertIn("chip('SC','sc','drop-control')", HTML)
        self.assertIn("chip('SF','sf','drop-control'+sfActive)", HTML)
        self.assertIn("chip('SD','sd','single-drop-control')", HTML)
        self.assertIn("chip('SH','sh','single-drop-control'+shActive)", HTML)
        self.assertIn(".tx16-chip.drop-control", HTML)
        self.assertIn(".tx16-chip.single-drop-control", HTML)

    def test_disarmed_physical_movement_is_conditional(self):
        self.assertIn("function detectDisarmedPhysicalMovement", HTML)
        self.assertIn("DISARMED_PHYSICAL_MOVEMENT", HTML)
        self.assertIn("Ознаки фізичного переміщення заживленого БПЛА при DISARMED", HTML)
        self.assertIn("if(sessionCount>0)return {events:[],alerts:[]};", HTML)

    def test_beta_version_badge(self):
        self.assertIn(">BETA v1.0</div>", HTML)


if __name__ == "__main__":
    unittest.main()
