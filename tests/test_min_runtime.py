"""Minimum run time at small powers: no on/off chatter when the demand hovers around the minimum."""
import math

from test_package import Runner


def hover(t):
    # house minus solar swings between about 10 W and 110 W every 40 s (cloudy morning, house ≈ solar)
    return 60 + 50 * math.sin(2 * math.pi * t / 40)


def switches(r, t0=30):
    on = [abs(a[0]) >= 20 for t, g, a, s in r.log if t >= t0]
    return sum(1 for x, y in zip(on, on[1:]) if x != y)


def run(mlt, load=hover, secs=600):
    return Runner(n=1, socs=(70,), load=load,
                  settings={"input_number.zendure_ems_min_looptijd": mlt}).run(secs)


def test_min_runtime_reduces_switching():
    off, on = run(0), run(60)
    assert switches(on) < switches(off)
    assert switches(on) <= 600 / 60 * 2 + 2          # at most one start and one stop per minute


def test_min_runtime_status_shown():
    r = run(60)
    assert any(s.startswith("Minimale looptijd") or s.startswith("Rusttijd") for t, g, a, s in r.log)


def test_large_demand_not_delayed():
    # idle, then a kettle: the set must follow at once, whatever the run time
    r = run(120, load=lambda t: 30 if t < 100 else 2000, secs=160)
    assert min(a[0] for t, g, a, s in r.log if 120 <= t < 160) < -1500


def test_large_surplus_stops_running_set():
    # discharging at the minimum, then strong solar: the set must not keep discharging into the grid
    r = run(300, load=lambda t: 150 if t < 120 else -800, secs=200)
    assert max(a[0] for t, g, a, s in r.log if 170 <= t < 200) > -20


def test_update_sets_min_runtime_once():
    r = Runner(n=1, socs=(70,))
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_update")
    br = next(x for x in auto["actions"] if "if" in x and x["then"][0].get("target", {}).get("entity_id")
              == "input_number.zendure_ems_min_looptijd")
    assert br["then"][0]["data"]["value"] == 60
    tpl = br["if"][0]["value_template"]
    for v, exp in (("1.12.5", True), ("1.11.0", True), ("1.12.6", False), ("1.13.0", False), ("", False)):
        r.hass.set("input_text.zendure_ems_versie", v)
        assert r.hass.render(tpl) is exp, v
