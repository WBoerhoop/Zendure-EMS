"""EV via a granny charger: when the user's 'EV laden actief' switch is on, the EV is ignored by the batteries."""
from test_package import Runner, STATE_SENSORS

HOUSE_W, EV_W = 500, 2300


def ev_runner(active, socs=(80, 80, 80)):
    r = Runner(socs=socs, load=lambda t: HOUSE_W + EV_W)
    h = r.hass
    h.set("input_text.zendure_ems_ev_sensor", "sensor.autolader_power")
    h.set("input_text.zendure_ems_ev_actief", "input_boolean.ev_laden_actief")
    h.set("input_boolean.ev_laden_actief", "on" if active else "off")
    h.set("sensor.autolader_power", EV_W, {"unit_of_measurement": "W"})
    return r


def test_switch_off_battery_covers_ev():
    r = ev_runner(False).run(90)
    assert r.avg_abs_grid(60, 90) < 120


def test_switch_on_ev_stays_on_grid():
    r = ev_runner(True).run(90)
    grid = [g for t, g, _, _ in r.log if t >= 60]
    assert abs(sum(grid) / len(grid) - EV_W) < 150
    assert abs(sum(s.actual for s in r.sets) + HOUSE_W) < 150


def test_no_switch_configured_means_no_exclusion():
    r = ev_runner(True)
    r.hass.set("input_text.zendure_ems_ev_actief", "")
    r.run(90)
    assert r.avg_abs_grid(60, 90) < 120


def test_kw_sensor():
    r = ev_runner(True)
    r.hass.set("sensor.autolader_power", 2.3, {"unit_of_measurement": "kW"})
    sens = next(s for s in STATE_SENSORS(r.pkg) if s["unique_id"] == "zendure_ems_ev_vermogen")
    assert float(r.hass.render(sens["state"])) == 2300


def test_house_consumption_excludes_ev():
    r = ev_runner(False).run(60)
    r.hass.set("sensor.zendure_ems_accuvermogen", sum(s.actual for s in r.sets))
    sens = next(s for s in STATE_SENSORS(r.pkg) if s["unique_id"] == "zendure_ems_huisverbruik")
    assert abs(float(r.hass.render(sens["state"])) - HOUSE_W) < 120


def ev_block(pkg, key):
    return next(b for b in pkg["template"] if key in b or
                any(s.get("unique_id") == key for s in b.get("sensor", [])))


def test_dashboard_switch_follows_configured_entity():
    r = ev_runner(True)
    sw = ev_block(r.pkg, "switch")["switch"][0]
    h = r.hass
    assert h.render(sw["availability"]) is True
    assert h.render(sw["state"]) is True
    assert h.render(sw["turn_off"][0]["target"]["entity_id"]) == "input_boolean.ev_laden_actief"
    h.set("input_text.zendure_ems_ev_actief", "")
    assert h.render(sw["availability"]) is False


def test_charging_binary_and_minutes():
    r = ev_runner(True)
    blk = ev_block(r.pkg, "switch")
    r.hass.set("sensor.zendure_ems_ev_vermogen", 2300)
    assert r.hass.render(blk["binary_sensor"][0]["state"]) is True
    r.hass.set("sensor.zendure_ems_ev_vermogen", 0)
    assert r.hass.render(blk["binary_sensor"][0]["state"]) is False
    r.hass.set("sensor.zendure_ems_ev_laadtijd_vandaag_uren", 1.5)
    assert float(r.hass.render(blk["sensor"][0]["state"])) == 90


class _S:
    def __init__(self, state):
        self.state = state


def test_cost_today_accumulates_and_resets():
    r = ev_runner(True)
    sens = ev_block(r.pkg, "zendure_ems_ev_kosten_vandaag")["sensor"][0]
    h = r.hass
    h.set("sensor.zendure_ems_stroomprijs", 0.25)
    trig = {"id": "energie", "from_state": _S("10.0"), "to_state": _S("10.4")}
    v = float(h.render(sens["state"], trigger=trig, this=_S("1.0")))
    assert abs(v - 1.1) < 1e-9
    v = float(h.render(sens["state"], trigger=trig, this=_S("unknown")))
    assert abs(v - 0.1) < 1e-9
    big = {"id": "energie", "from_state": _S("0"), "to_state": _S("500")}   # counter restart: ignored
    assert float(h.render(sens["state"], trigger=big, this=_S("1.0"))) == 1.0
    assert float(h.render(sens["state"], trigger={"id": "reset"}, this=_S("3.2"))) == 0
