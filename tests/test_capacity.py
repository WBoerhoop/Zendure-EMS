"""Capacity per set: built-in battery + packs, or packs of another size."""
from test_package import Runner, STATE_SENSORS

CAPS = {"input_number.zendure_set1_capaciteit": 13.92,   # 2.4 built in + 4 x 2.88
        "input_number.zendure_set2_capaciteit": 0}       # automatic: packs x 2.88


def sensor(r, uid):
    return next(s for s in STATE_SENSORS(r.pkg) if s["unique_id"] == uid)


def test_stored_energy_and_average_soc_use_capacity():
    r = Runner(n=2, socs=(50, 100), settings=CAPS).run(6)
    stored = float(r.hass.render(sensor(r, "zendure_ems_opgeslagen_energie")["state"]))
    auto = 2 * 2.88                     # simulated set reports 2 packs
    assert abs(stored - (0.5 * 13.92 + 1.0 * auto)) < 0.05
    avg = float(r.hass.render(sensor(r, "zendure_ems_gemiddelde_soc")["state"]))
    assert abs(avg - (50 * 13.92 + 100 * auto) / (13.92 + auto)) < 0.2


def test_reserve_uses_capacity():
    # 1.392 kWh reserve on 13.92 kWh = 10 %: min 10 % + 10 % = 20 % floor
    s = dict(CAPS, **{"input_number.zendure_set1_reserve": 1.392})
    r = Runner(n=2, socs=(18, 50), load=lambda t: 600, settings=s).run(60)
    assert abs(r.sets[0].actual) < 5           # set 1 below its 20 % floor: idle
    r2 = Runner(n=2, socs=(22, 50), load=lambda t: 600, settings=s,
                ).run(60)
    assert sum(x.actual for x in r2.sets) < -500


def test_planner_usable_energy():
    r = Runner(n=2, socs=(60, 60), mode="Prijsgestuurd", prices=[0.2] * 48, settings=CAPS)
    r.run(6)
    pp = r.run_price()
    assert abs(pp["usable_energy"] - (0.5 * 13.92 + 0.5 * 5.76)) < 0.05
