"""Reserve per set: kWh kept on top of the min SOC, restored at the cheapest moment when below."""
from datetime import datetime

from ha_sim import TZ
from test_package import Runner
from test_planner import NIGHT, PRICES, runner

RES = {"input_number.zendure_set1_reserve": 1.152, "input_number.zendure_set2_reserve": 1.152}  # 20 % of 5.76 kWh


def test_control_keeps_reserve():
    # set at 25 %: min 10 % + reserve 20 % = 30 %: no discharge
    r = Runner(n=2, socs=(25, 25), load=lambda t: 1500, settings=RES).run(60)
    assert all(abs(s.actual) < 5 for s in r.sets)
    # at 35 % it may discharge again
    r2 = Runner(n=2, socs=(35, 35), load=lambda t: 1500, settings=RES).run(60)
    assert sum(s.actual for s in r2.sets) < -1300


def test_reserve_zero_changes_nothing():
    r = Runner(n=2, socs=(25, 25), load=lambda t: 1500).run(60)
    assert sum(s.actual for s in r.sets) < -1300


def test_device_min_soc_stays_plain():
    r = Runner(n=2, socs=(60, 60), settings=RES).run(5)
    soc_auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_soc_grenzen")
    tpl = soc_auto["actions"][0]["repeat"]["for_each"]
    assert r.hass.render(tpl) == []          # the device keeps min SOC 10 %: nothing to write


def test_planner_restores_reserve_in_cheapest_quarter():
    # 01:00, sets at 20 % (below 30 % floor); cheapest quarters of the next 12 h are 01:00-06:59 (0.10)
    prices = [0.10] * 3 + [0.05] * 1 + [0.10] * 3 + [0.30] * 3 + [0.22] * 6 + [0.40] * 6 + [0.25] * 2
    r = runner(NIGHT, socs=(20, 20, 20), prices=prices, n=3,
               extra={"input_number.zendure_set%d_reserve" % i: 1.152 for i in (1, 2, 3)})
    pp = r.run_price()
    assert pp["reserve_deficit"] > 1.5          # 3 x 10 % x 5.76 kWh = 1.73 kWh
    hours = {datetime.fromtimestamp(q, TZ).hour for q in pp["reserve_slots"]}
    assert hours == {3}                          # the 0.05 hour
    assert pp["grid_kwh"] >= pp["reserve_deficit"]


def test_restore_also_without_profit():
    flat = [0.20] * 48
    r = runner(NIGHT, socs=(20, 20, 20), prices=flat, n=3,
               extra={"input_number.zendure_set%d_reserve" % i: 1.152 for i in (1, 2, 3)})
    pp = r.run_price()
    assert pp["reserve_slots"] and pp["grid_kwh"] > 1.5
    # the first quarter is one of the (equal) cheapest: charging now, with the reason shown
    if pp["action"] == "grid_charge":
        assert pp["reason"].startswith("Reserve aanvullen") or pp["reason"].startswith("Gepland laden")


def test_no_restore_outside_price_mode_or_without_deficit():
    r = runner(NIGHT, socs=(50, 50, 50), n=3, extra={"input_number.zendure_set1_reserve": 1.152})
    assert r.run_price()["reserve_slots"] == []
