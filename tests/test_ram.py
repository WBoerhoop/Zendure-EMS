"""Flash wear: acMode only on a real direction change, stop keeps the mode, smartMode switch and watchdog."""
from test_package import Runner


def load_steps(t):
    # discharge 1500 W, then 900 W, then a small surplus (stop), then 1200 W again
    if t < 120:
        return 1500
    if t < 240:
        return 900
    if t < 360:
        return 10
    return 1200


def test_power_changes_do_not_rewrite_mode():
    r = Runner(n=2, socs=(60, 60), load=load_steps).run(480)
    for s in r.sets:
        assert all(w[1].get("smartMode") == 1 for w in s.writes)
        assert s.flash_writes == 0
        # the only direction change is the short overshoot to charging after the load drop (set 1)
        assert s.mode_writes <= 1, [w for w in s.writes if "acMode" in w[1]]


def test_stop_zeroes_current_limit_without_mode_change():
    r = Runner(n=2, socs=(60, 60), load=lambda t: 1500 if t < 120 else 5).run(240)
    stops = [w for s in r.sets for _, w in s.writes if w.get("outputLimit") == 0 or w.get("inputLimit") == 0]
    assert stops
    assert all("acMode" not in w for w in stops)


def test_direction_change_sends_mode():
    r = Runner(n=2, socs=(50, 50), load=lambda t: 1200 if t < 120 else -1500).run(300)
    modes = [w["acMode"] for s in r.sets for _, w in s.writes if "acMode" in w]
    assert 1 in modes                      # switched to charging when the surplus came
    assert all(s.mode_writes <= 2 for s in r.sets)


def test_flash_switch_writes_smartmode_0():
    r = Runner(n=2, socs=(60, 60), load=lambda t: 1500,
               settings={"input_boolean.zendure_ems_flash_schrijven": "on"}).run(60)
    ws = [w for s in r.sets for _, w in s.writes]
    assert ws and all(w.get("smartMode") == 0 for w in ws)


def watchdog(pkg):
    return next(a for a in pkg["automation"] if a["id"] == "zendure_ems_smartmode_bewaken")


def test_watchdog_finds_sets_on_flash():
    r = Runner(n=3, socs=(60, 60, 60)).run(10)
    r.sets[1].smart_mode = 0
    r.t = 15.0
    r.publish()
    a = watchdog(r.pkg)
    back = r.hass.render(a["actions"][0]["variables"]["terug"])
    assert [b["id"] for b in back] == ["2"]
    assert back[0]["ip"] == "192.168.1.102" and back[0]["sn"] == "SN2"
    assert r.hass.render(a["actions"][1]["value_template"], terug=back) is True
    r.sets[1].smart_mode = 1
    r.t = 20.0
    r.publish()
    assert r.hass.render(a["actions"][0]["variables"]["terug"]) == []


def test_smartmode_sensor():
    from test_package import STATE_SENSORS
    r = Runner(n=2, socs=(60, 60)).run(6)
    sens = next(s for s in STATE_SENSORS(r.pkg) if s["unique_id"] == "zendure_ems_set1_smartmode")
    assert r.hass.render(sens["state"]) == "RAM"
    r.sets[0].smart_mode = 0
    r.t = 10.0
    r.publish()
    assert r.hass.render(sens["state"]) == "flash"
