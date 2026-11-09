"""Zendure EMS 1.12.3: automatic wait, acMode preference, calm graph sensors, P1 only with IP."""

import yaml
from pathlib import Path

from ha_sim import State
from test_package import START, STATE_SENSORS, Runner


def regelaar(pkg):
    blk = next(b for b in pkg["template"] if b["triggers"][0].get("event_type") == "zendure_ems_regelaar")
    return blk["sensor"][0]


def fire(r, iv, this=None):
    sens = regelaar(r.pkg)
    trig = {"platform": "event", "event": {"data": {"cmd": 0, "err": 0, "mis": 0, "dip": 0, "active": "",
                                                   "action": "zero", "setpoints": {}, "written": 0, "iv": iv}}}
    return {k: r.hass.render(v, trigger=trig, this=this) for k, v in sens["attributes"].items()}


def test_meter_interval_is_averaged_and_gives_the_wait():
    r = Runner(n=1)
    a = fire(r, 5.0)
    assert a["meterinterval"] == 5.0 and a["wachttijd_auto"] == 6.0
    prev = State("sensor.zendure_ems_regelaar", "0", a)
    a2 = fire(r, 1.0, prev)                      # a shorter gap moves the estimate halfway down
    assert a2["meterinterval"] == 3.0
    prev = State("sensor.zendure_ems_regelaar", "0", a2)
    a3 = fire(r, None, prev)                     # no sample (time trigger): keep the value
    assert a3["meterinterval"] == 3.0 and a3["wachttijd_auto"] == a2["wachttijd_auto"]
    a4 = fire(r, 13.0, State("sensor.zendure_ems_regelaar", "0", a3))   # a longer gap only 5 %
    assert a4["meterinterval"] == 3.5
    for _ in range(30):                          # a 1-second meter: wait settles at 3 s
        prev = State("sensor.zendure_ems_regelaar", "0", fire(r, 1.0, prev).copy())
    assert prev.attributes["wachttijd_auto"] == 3.0
    big = fire(r, 120.0)                         # long gaps (meter value unchanged) are capped
    assert big["meterinterval"] == 15 and big["wachttijd_auto"] == 10


def test_precheck_uses_automatic_or_manual_wait():
    r = Runner(n=1)
    h = r.hass
    h.set("input_number.zendure_ems_wachttijd", 3)
    h.set("sensor.zendure_ems_regelaar", "0", {"geschreven": START.timestamp() - 4, "actie": "zero",
                                               "vorige_fout": 0, "wachttijd_auto": 6.0})
    h.set("input_boolean.zendure_ems_wachttijd_auto", "off")
    assert h.render(r.precheck_tpl, trigger={"id": "tijd"}) is True     # 4 s >= manual 3 s
    h.set("input_boolean.zendure_ems_wachttijd_auto", "on")
    assert h.render(r.precheck_tpl, trigger={"id": "tijd"}) is False    # 4 s < automatic 6 s
    h.set("sensor.zendure_ems_regelaar", "0", {"geschreven": START.timestamp() - 4, "actie": "zero",
                                               "vorige_fout": 0})
    assert h.render(r.precheck_tpl, trigger={"id": "tijd"}) is True     # nothing measured yet: manual


def test_control_event_reports_meter_interval():
    r = Runner(n=1)
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_regeling")
    ev = next(x for x in auto["actions"] if "event" in x)
    tpl = ev["event_data"]["iv"]
    f = State("sensor.zendure_ems_netvermogen", "120", {}, START, START)
    from datetime import timedelta
    t = State("sensor.zendure_ems_netvermogen", "80", {}, START + timedelta(seconds=5), START + timedelta(seconds=5))
    f.last_changed, t.last_changed = f.last_updated, t.last_updated
    assert r.hass.render(tpl, trigger={"id": "meter", "from_state": f, "to_state": t}) == 5.0
    assert r.hass.render(tpl, trigger={"id": "tijd"}) is None
    u = State("sensor.zendure_ems_netvermogen", "unavailable", {}, START, START)
    u.last_changed = START
    assert r.hass.render(tpl, trigger={"id": "meter", "from_state": u, "to_state": t}) is None


def test_small_demand_prefers_set_already_in_that_direction():
    """Set 1 is fuller but already charging (acMode 1): a small charge demand stays with set 1,
    so set 2 does not need an acMode (flash) write."""
    r = Runner(n=2, socs=(55, 50), load=lambda t: -300)
    r.sets[0].ac_mode = 1
    r.sets[1].ac_mode = 2
    r.run(120)
    assert r.sets[1].mode_writes == 0
    assert r.sets[0].mode_writes == 0
    assert abs(r.sets[0].actual) > 200 and abs(r.sets[1].actual) < 5


def test_large_demand_still_balances_soc():
    r = Runner(n=2, socs=(80, 40), load=lambda t: -1800)
    r.sets[0].ac_mode = 1
    r.run(120)
    # the emptier set charges more
    assert r.sets[1].actual > r.sets[0].actual


def test_graph_sensors_every_5_s_and_used_by_dashboard():
    r = Runner(n=1)
    blk = next(b for b in r.pkg["template"]
               if b.get("triggers", [{}])[0].get("trigger") == "time_pattern" and b["triggers"][0].get("seconds") == "/5"
               and any(s["unique_id"] == "zendure_ems_grafiek_net" for s in b.get("sensor", [])))
    ids = {s["unique_id"]: s for s in blk["sensor"]}
    h = r.hass
    h.set("sensor.zendure_ems_netvermogen", "123.4")
    h.set("sensor.zendure_ems_huisverbruik", "unavailable")
    assert h.render(ids["zendure_ems_grafiek_net"]["state"]) == 123
    assert h.render(ids["zendure_ems_grafiek_huis"]["availability"]) is False
    root = Path(__file__).resolve().parents[1] / "out"
    d = yaml.safe_load((root / "dashboard.yaml").read_text(encoding="utf-8"))
    graphs = []

    def walk(c):
        if isinstance(c, dict):
            if c.get("type") == "history-graph":
                graphs.extend(e["entity"] if isinstance(e, dict) else e for e in c.get("entities", []))
            for v in c.values():
                walk(v)
        elif isinstance(c, list):
            for v in c:
                walk(v)
    walk(d)
    assert "sensor.zendure_ems_grafiek_net" in graphs
    assert "sensor.zendure_ems_netvermogen" not in graphs and "sensor.zendure_ems_huisverbruik" not in graphs


def test_update_switches_automatic_wait_on_once():
    r = Runner(n=1)
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_update")
    br = next(x for x in auto["actions"] if "if" in x and any(
        t.get("target", {}).get("entity_id") == "input_boolean.zendure_ems_wachttijd_auto" for t in x["then"]))
    cond = br["if"][0]["value_template"]
    for v, exp in (("1.12.2", True), ("1.9.11", True), ("1.12.3", False), ("1.13.0", False), ("", False)):
        r.hass.set("input_text.zendure_ems_versie", v)
        assert r.hass.render(cond) is exp, v
    init = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_standaardwaarden")
    on = [x for x in init["actions"] if x.get("action") == "input_boolean.turn_on"]
    assert any("input_boolean.zendure_ems_wachttijd_auto" in x["target"]["entity_id"] for x in on)


def run_gaps(r, gaps):
    prev = None
    for g in gaps:
        prev = State("sensor.zendure_ems_regelaar", "0", fire(r, g, prev).copy())
    return prev.attributes


def test_one_second_meter_with_steady_power_keeps_a_short_wait():
    # DSMR 5 (1 s) where the power often stays the same for a few seconds: gaps of 1 s mixed with 4-12 s
    r = Runner(n=1)
    a = run_gaps(r, [6, 1, 1, 8, 1, 2, 12, 1, 1, 5, 1, 9, 1, 1, 4, 1, 10, 1, 2, 1] * 3)
    assert a["meterinterval"] < 2.5 and a["wachttijd_auto"] <= 4.0


def test_ten_second_meter_keeps_a_long_wait():
    # DSMR 4 (10 s): no gap is ever shorter than 10 s
    r = Runner(n=1)
    a = run_gaps(r, [10, 10, 20, 10, 30, 10, 10, 15] * 5)
    assert a["meterinterval"] >= 10 and a["wachttijd_auto"] >= 9.5
