"""HomeWizard P1 read by the package itself every second (1.12.2)."""

from datetime import timedelta

import yaml

from test_package import START, STATE_SENSORS, Runner


def grid_sensor(r, uid="zendure_ems_netvermogen"):
    return next(s for s in STATE_SENSORS(r.pkg) if s["unique_id"] == uid)["state"]


def p1_rest(pkg):
    return next(x for x in pkg["rest"] if x["sensor"][0]["unique_id"] == "zendure_ems_p1_vermogen")


def test_rest_sensor_polls_every_second_and_falls_back_without_ip():
    r = Runner(n=1)
    rest = p1_rest(r.pkg)
    # the resource itself polls only hourly; the per-second trigger asks for it when an IP is filled in
    assert rest["scan_interval"] >= 3600 and rest["timeout"] <= 2
    h = r.hass
    h.set("input_text.zendure_ems_p1_ip", "")
    assert h.render(rest["resource_template"]).strip() == "http://127.0.0.1:8123/manifest.json"
    h.set("input_text.zendure_ems_p1_ip", " 192.168.1.20 ")
    assert h.render(rest["resource_template"]).strip() == "http://192.168.1.20/api/v1/data"
    sens = rest["sensor"][0]
    assert sens["unit_of_measurement"] == "W" and sens["device_class"] == "power"
    data = {"active_power_w": -412.6, "total_power_import_kwh": 5633.2}
    assert h.render(sens["value_template"], value_json=data) in (-413, -413.0, "-413.0", "-413")
    assert h.render(sens["availability"], value_json=data) in (True, "True")
    # the fallback file (manifest.json) makes the sensor unavailable, without template errors
    manifest = {"name": "Home Assistant", "short_name": "Assistant"}
    assert h.render(sens["availability"], value_json=manifest) in (False, "False")
    h.render(sens["value_template"], value_json=manifest)
    h.render(sens["value_template"], value_json="")


def test_fresh_p1_is_preferred_over_the_grid_sensor():
    r = Runner(n=1)
    h = r.hass
    h.set("sensor.p1_vermogen", 900, {"unit_of_measurement": "W"})
    h.set("sensor.zendure_ems_p1_vermogen", 250, {"unit_of_measurement": "W"})
    tpl = grid_sensor(r)
    h.set("input_text.zendure_ems_p1_ip", "")
    assert float(h.render(tpl)) == 900          # no IP: the grid sensor that was filled in
    h.set("input_text.zendure_ems_p1_ip", "192.168.1.20")
    assert float(h.render(tpl)) == 250          # IP filled in and fresh: the P1 itself


def test_stale_or_unavailable_p1_falls_back_to_grid_sensor():
    r = Runner(n=1)
    h = r.hass
    h.set("input_text.zendure_ems_p1_ip", "192.168.1.20")
    h.set("sensor.zendure_ems_p1_vermogen", 250, {"unit_of_measurement": "W"})
    h.now = START + timedelta(seconds=15)       # P1 not reported for 15 s
    h.set("sensor.p1_vermogen", 900, {"unit_of_measurement": "W"})
    tpl = grid_sensor(r)
    assert float(h.render(tpl)) == 900
    h.set("sensor.zendure_ems_p1_vermogen", "unavailable")
    assert float(h.render(tpl)) == 900


def test_inversion_does_not_apply_to_the_p1():
    r = Runner(n=1, invert=True)
    h = r.hass
    h.set("input_text.zendure_ems_p1_ip", "192.168.1.20")
    h.set("sensor.zendure_ems_p1_vermogen", 300, {"unit_of_measurement": "W"})
    assert float(h.render(grid_sensor(r, "zendure_ems_netmeting"))) == 300
    h.set("input_text.zendure_ems_p1_ip", "")
    h.set("sensor.p1_vermogen", 300, {"unit_of_measurement": "W"})
    assert float(h.render(grid_sensor(r, "zendure_ems_netmeting"))) == -300


def test_control_holds_zero_with_p1_every_second():
    """Nul op de meter with the package's own P1 sensor updating every second."""
    r = Runner(n=2, socs=(60, 50), load=lambda t: 800 if t < 60 else 300)
    h = r.hass
    h.set("input_text.zendure_ems_p1_ip", "192.168.1.20")
    orig = r.publish

    def publish():
        orig()
        h.set("sensor.p1_vermogen", 5000, {"unit_of_measurement": "W"})   # slow sensor: must be ignored
        g = r.grid + r.rnd.gauss(0, 8)
        h.set("sensor.zendure_ems_p1_vermogen", round(g), {"unit_of_measurement": "W"})
        h.set("sensor.zendure_ems_netvermogen", h.render(r.netv_tpl), {"unit_of_measurement": "W"})
    r.publish = publish
    r.run(200)
    assert r.avg_abs_grid(40, 60) < 60
    assert r.avg_abs_grid(150, 200) < 60


def test_package_and_dashboard_have_the_field():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "out"
    pkg = yaml.safe_load((root / "zendure_ems.yaml").read_text(encoding="utf-8"))
    assert "zendure_ems_p1_ip" in pkg["input_text"]
    assert "zendure_ems_p1_ip" in (root / "dashboard.yaml").read_text(encoding="utf-8")


def p1_trigger(pkg):
    return next(b for b in pkg["template"]
                if b.get("triggers", [{}])[0].get("trigger") == "time_pattern" and b["triggers"][0].get("seconds") == "/1")


def test_p1_is_read_every_second_only_with_ip():
    r = Runner(n=1)
    blk = p1_trigger(r.pkg)
    step = blk["actions"][0]
    assert step["then"][0]["action"] == "homeassistant.update_entity"
    assert step["then"][0]["target"]["entity_id"] == "sensor.zendure_ems_p1_vermogen"
    cond = step["if"][0]["value_template"]
    h = r.hass
    h.set("input_text.zendure_ems_p1_ip", "")
    assert h.render(cond) is False
    h.set("input_text.zendure_ems_p1_ip", "unknown")
    assert h.render(cond) is False
    h.set("input_text.zendure_ems_p1_ip", "10.4.0.164")
    assert h.render(cond) is True


def test_meter_source_sensor():
    r = Runner(n=1)
    h = r.hass
    src = p1_trigger(r.pkg)["sensor"][0]["state"]
    h.set("input_text.zendure_ems_p1_ip", "")
    assert h.render(src) == "sensor.p1_vermogen"
    h.set("input_text.zendure_ems_p1_ip", "10.4.0.164")
    h.set("sensor.zendure_ems_p1_vermogen", 120, {"unit_of_measurement": "W"})
    assert h.render(src) == "HomeWizard P1 (elke seconde)"
