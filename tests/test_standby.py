"""Standby after inactivity (as Gielz): smartMode 0 with both limits 0 once a set has been idle for N minutes."""
from test_package import Runner


def standby(pkg):
    return next(a for a in pkg["automation"] if a["id"] == "zendure_ems_standby")


def watchdog(pkg):
    return next(a for a in pkg["automation"] if a["id"] == "zendure_ems_smartmode_bewaken")


def idle_sensor(pkg, i):
    blk = next(b for b in pkg["template"] if any(s.get("unique_id") == f"zendure_ems_set{i}_inactief"
                                                for s in b.get("binary_sensor", [])))
    return next(s for s in blk["binary_sensor"] if s["unique_id"] == f"zendure_ems_set{i}_inactief")


def test_idle_sensor_follows_limits():
    r = Runner(n=2, socs=(60, 60), load=lambda t: 400).run(30)   # small load: one set active (staging)
    states = [r.hass.render(idle_sensor(r.pkg, i)["state"]) for i in (1, 2)]
    assert states.count(True) == 1 and states.count(False) == 1


def test_standby_automation_renders_and_conditions():
    r = Runner(n=2, socs=(60, 60), load=lambda t: 400).run(30)
    a = standby(r.pkg)
    assert len(a["triggers"]) == 2 and a["triggers"][0]["id"] == "1"
    assert r.hass.render(a["triggers"][0]["for"]["minutes"]) == 5
    cond = a["conditions"][-1]["value_template"]
    assert r.hass.render(cond, trigger={"id": "2"}) is True
    data = a["actions"][0]["data"]
    assert r.hass.render(data["ip"], trigger={"id": "2"}) == "192.168.1.102"
    assert data["props"] == {"smartMode": 0, "inputLimit": 0, "outputLimit": 0}
    # already in standby: nothing to do
    r.sets[1].write(r.t, {"smartMode": 0, "inputLimit": 0, "outputLimit": 0})
    r.run(10)
    assert r.hass.render(cond, trigger={"id": "2"}) is False


def test_watchdog_leaves_idle_set_in_standby_but_wakes_on_demand():
    r = Runner(n=2, socs=(60, 60), load=lambda t: 400).run(30)
    idle = 1 if r.sets[1].actual == 0 or abs(r.sets[1].actual) < 5 else 0
    r.sets[idle].write(r.t, {"smartMode": 0, "inputLimit": 0, "outputLimit": 0})
    r.run(10)
    h = r.hass
    for i in (1, 2):
        h.set(f"binary_sensor.zendure_set{i}_inactief", "on" if h.render(idle_sensor(r.pkg, i)["state"]) else "off")
    back = h.render(watchdog(r.pkg)["actions"][0]["variables"]["terug"])
    assert back == []                         # in standby on purpose: watchdog does not undo it
    h.set("input_number.zendure_ems_standby_vertraging", 0)
    back = h.render(watchdog(r.pkg)["actions"][0]["variables"]["terug"])
    assert [b["id"] for b in back] == [str(idle + 1)]   # standby feature off: back to RAM
    # demand rises: the control writes smartMode 1 again
    r.load = lambda t: 3500
    r.run(30)
    assert r.sets[idle].smart_mode == 1 and abs(r.sets[idle].actual) > 100


def test_standby_off_when_delay_zero():
    r = Runner(n=2, socs=(60, 60)).run(5)
    a = standby(r.pkg)
    assert a["conditions"][0] == {"condition": "numeric_state", "entity_id": "input_number.zendure_ems_standby_vertraging", "above": 0}
