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

    def test_drop_system_selector_is_removed(self):
        self.assertNotIn('id="dropSystemType"', HTML)
        self.assertNotIn('name="dropSystemType"', HTML)

    def test_dual_drop_sc_states_are_named_by_safety_function(self):
        self.assertIn("function tx16DualDropSafetyState", HTML)
        self.assertIn("ЗАПОБІЖНИК АКТИВОВАНИЙ", HTML)
        self.assertIn("ЗНЯТО З ЗАПОБІЖНИКА (R)", HTML)
        self.assertIn("ЗНЯТО З ЗАПОБІЖНИКА (L)", HTML)

    def test_single_drop_sc_requires_toward_position(self):
        self.assertIn("function tx16SingleDropSafetyState", HTML)
        self.assertIn("if(pos===1||pos===2)return 'ЗАПОБІЖНИК АКТИВОВАНИЙ';", HTML)
        self.assertIn("if(pos===3)return 'ЗНЯТО З ЗАПОБІЖНИКА';", HTML)

    def test_drop_system_type_is_inferred_from_sc_sf_usage(self):
        self.assertIn("function inferDropSystemType", HTML)
        self.assertIn("middleSfActivations", HTML)
        self.assertIn("towardSfActivations", HTML)
        self.assertIn("type:'dual'", HTML)
        self.assertIn("type:'single'", HTML)
        self.assertIn("type:'unknown'", HTML)
        self.assertIn("ЙМОВІРНИЙ ТИП СИСТЕМИ СКИДУ", HTML)
        self.assertIn("ТИП СИСТЕМИ СКИДУ НЕМОЖЛИВО ВИЗНАЧИТИ ОДНОЗНАЧНО", HTML)

    def test_drop_activation_uses_inferred_system_type(self):
        self.assertIn("const inferredDropSystem=inferDropSystemType(rows);", HTML)
        self.assertIn("if(inferredDropSystem.type==='single')", HTML)
        self.assertIn("if(scPos===3)", HTML)
        self.assertIn("ОДИНОЧНИЙ СКИД", HTML)
        self.assertIn("if(scPos===2||scPos===3)", HTML)
        self.assertIn("const side=scPos===2?'R':'L';", HTML)
        self.assertIn("СКИД ${ev.side}", HTML)

    def test_sc_sf_activity_is_reported_even_without_valid_drop(self):
        self.assertIn("scTransitions", HTML)
        self.assertIn("sfActivations", HTML)
        self.assertIn("SC: зафіксовано", HTML)
        self.assertIn("SF: зафіксовано", HTML)
        self.assertIn("валідний скид не підтверджено", HTML)

    def test_sd_sh_are_emergency_stop_not_single_drop(self):
        self.assertIn("EMERGENCY STOP", HTML)
        self.assertIn("function tx16EmergencyStopSafetyState", HTML)
        self.assertIn("sd:tx16EmergencyStopSafetyState(r.sd)", HTML)
        self.assertIn("if(prevSh===false && sh===true && sdPos===3)", HTML)
        self.assertIn("EMERGENCY STOP АКТИВОВАНО", HTML)
        self.assertNotIn("ОДИНОЧНИЙ СКИД — SD + SH", HTML)
        self.assertNotIn("single-drop-control", HTML)
        self.assertIn("emergency-control", HTML)

    def test_drop_and_emergency_groups_keep_distinct_colors(self):
        self.assertIn("chip('SC','sc','drop-control')", HTML)
        self.assertIn("chip('SF','sf','drop-control'+sfActive)", HTML)
        self.assertIn("chip('SD','sd','emergency-control')", HTML)
        self.assertIn("chip('SH','sh','emergency-control'+shActive)", HTML)
        self.assertIn(".tx16-chip.drop-control", HTML)
        self.assertIn(".tx16-chip.emergency-control", HTML)

    def test_sa_sb_use_blue_rf_control_highlight(self):
        self.assertIn("chip('SA','sa','rf-control')", HTML)
        self.assertIn("chip('SB','sb','rf-control')", HTML)
        self.assertIn(".tx16-chip.rf-control", HTML)
        self.assertIn("#7dd3fc", HTML)
        self.assertIn("#38bdf8", HTML)

    def test_sb_timeline_chip_includes_vtx_frequency_from_sa_sb_matrix(self):
        self.assertIn("function tx16VtxFrequency", HTML)
        for freq in (5180, 5240, 5300, 5520, 5580, 5640, 5700, 5765, 5825):
            self.assertIn(str(freq), HTML)
        self.assertIn("sb:sbPos?`K${sbPos} • ${tx16VtxFrequency(saPos,sbPos)} MHz`:'—'", HTML)

    def test_disarmed_physical_movement_is_conditional(self):
        self.assertIn("function detectDisarmedPhysicalMovement", HTML)
        self.assertIn("DISARMED_PHYSICAL_MOVEMENT", HTML)
        self.assertIn("Ознаки фізичного переміщення заживленого БПЛА при DISARMED", HTML)
        self.assertIn("if(sessionCount>0)return {events:[],alerts:[]};", HTML)

    def test_beta_version_badge(self):
        self.assertIn(">BETA v1.0</div>", HTML)


if __name__ == "__main__":
    unittest.main()
