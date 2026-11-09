"""Planned selling for the profiles Dynamisch Handelen (+ NOM): sell only what pays, buy extra when cheap."""
from datetime import datetime

from ha_sim import TZ
from test_package import Runner
from test_planner import NIGHT, PRICES, runner   # 0.10 at 00-07, 0.40 at 16-22

TRADE = {"input_boolean.zendure_ems_verkoop_plannen": "on", "input_number.zendure_ems_verkoopprijs": 0.35,
         "input_number.zendure_ems_min_spread": 0.05, "input_number.zendure_ems_slijtage": 0.03}


def hours(ts):
    return {datetime.fromtimestamp(q, TZ).hour for q in ts}


def test_buys_cheap_and_sells_in_the_peak():
    base = runner(NIGHT, socs=(30, 30, 30)).run_price()
    pp = runner(NIGHT, socs=(30, 30, 30), extra=TRADE).run_price()
    assert pp["trade"] and pp["sell_kwh"] > 1 and pp["trade_buy_kwh"] > 1
    assert hours(pp["sell_slots"]) <= set(range(16, 22))
    assert pp["trade_profit"] > 0
    # charging now (01:00, 0.10) is partly for the sale
    assert pp["action"] == "grid_charge" and pp["grid_kwh"] > base["grid_kwh"]
    # own use stays covered: the house takes no more from the grid in the expensive hours than without trading
    def grid_peak(p):
        return sum(q["u"] for q in p["upcoming"] if datetime.fromtimestamp(q["s"], TZ).hour in range(16, 22))
    assert grid_peak(pp) <= grid_peak(base) + 0.01


def test_no_sale_when_it_does_not_pay():
    flat = [0.30] * 24                                   # 0.30 * 0.92 - 0.03 - 0.05 < 0.30 / 0.92
    pp = runner(NIGHT, socs=(80, 80, 80), prices=flat,
                extra=dict(TRADE, **{"input_number.zendure_ems_verkoopprijs": 0.25})).run_price()
    assert pp["sell_kwh"] == 0 and pp["action"] != "sell"


def test_threshold_rule_when_not_trading():
    pp = runner(NIGHT, socs=(80, 80, 80), prices=[0.40] * 24,
                extra={"input_number.zendure_ems_verkoopprijs": 0.35}).run_price()
    assert not pp["trade"] and pp["action"] == "sell" and pp["sell_w"] == 0


def test_sells_now_in_peak_with_planned_power():
    peak = NIGHT.replace(hour=17)
    pp = runner(peak, socs=(90, 90, 90), extra=TRADE).run_price()
    assert pp["action"] == "sell" and 200 <= pp["sell_w"] <= 3 * 2400
    assert pp["reason"].startswith("Gepland verkopen")


def test_control_discharges_planned_power_plus_house():
    r = Runner(n=2, socs=(80, 80), mode="Prijsgestuurd", load=lambda t: 300)
    r.hass.set("sensor.zendure_ems_prijsactie", "sell", {"verkoopvermogen": 800, "laadvermogen": 0})
    r.run_price = lambda: None
    r.run(40)
    total = sum(s.actual for s in r.sets)
    assert abs(total + 1100) < 120
    assert abs(r.grid + 800) < 120
