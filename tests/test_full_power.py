"""Modes 'Laden (vol vermogen)' and 'Ontladen (vol vermogen)', and the way back to the previous mode."""
from test_package import Runner


def test_charge_full_power_from_grid():
    r = Runner(n=2, socs=(40, 40), mode="Laden (vol vermogen)", load=lambda t: 300).run(60)
    assert sum(s.actual for s in r.sets) > 4500           # 2 x 2400 W
    assert r.hass.states["sensor.zendure_ems_status"].state == "Laden met vol vermogen"


def test_discharge_full_power_to_grid():
    r = Runner(n=2, socs=(80, 80), mode="Ontladen (vol vermogen)", load=lambda t: 300).run(60)
    assert sum(s.actual for s in r.sets) < -4500
    assert r.grid < -4000


def test_stops_at_limits():
    r = Runner(n=2, socs=(100, 100), mode="Laden (vol vermogen)",
               settings={"input_number.zendure_set1_max_soc": 100, "input_number.zendure_set2_max_soc": 100}).run(30)
    assert abs(sum(s.actual for s in r.sets)) < 50
    assert r.hass.states["sensor.zendure_ems_status"].state == "Laden met vol vermogen: accu vol"
    r = Runner(n=2, socs=(10, 10), mode="Ontladen (vol vermogen)").run(30)
    assert abs(sum(s.actual for s in r.sets)) < 50
    assert r.hass.states["sensor.zendure_ems_status"].state == "Ontladen met vol vermogen: accu leeg"


def test_back_to_previous_mode():
    r = Runner(n=2, socs=(60, 60))
    a = next(x for x in r.pkg["automation"] if x["id"] == "zendure_ems_vol_vermogen_klaar")
    terug = a["actions"][0]["variables"]["terug"]
    r.hass.set("input_text.zendure_ems_vorige_modus", "Prijsgestuurd")
    assert r.hass.render(terug) == "Prijsgestuurd"
    r.hass.set("input_text.zendure_ems_vorige_modus", "")
    assert r.hass.render(terug) == "Nul op de meter"
    s = next(x for x in r.pkg["automation"] if x["id"] == "zendure_ems_vol_vermogen_onthouden")
    assert "Laden (vol vermogen)" in s["triggers"][0]["to"]
