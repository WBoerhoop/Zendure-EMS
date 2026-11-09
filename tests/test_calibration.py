"""Calibration: charge the sets to 100 % weekly / on a date / after max days, in the cheapest quarters of that day."""
from datetime import datetime, timedelta

from ha_sim import TZ
from test_package import Runner
from test_planner import NIGHT, PRICES, runner   # NIGHT = Monday 2 Nov 2026 01:00

DAY = 86400


def lv(r, i, days_ago, hour=14):
    t = (r.hass.now - timedelta(days=days_ago)).replace(hour=hour, minute=0, second=0, microsecond=0)
    r.hass.set(f"input_datetime.zendure_set{i}_laatst_vol", t.strftime("%Y-%m-%d %H:%M:%S"), {"timestamp": t.timestamp()})


def cal(mode="Wekelijks", dag="maandag", **kw):
    extra = {"input_select.zendure_ems_kalibratie": mode, "input_select.zendure_ems_kalibratie_dag": dag,
             "input_number.zendure_ems_kalibratie_dagen": 28}
    extra.update({f"input_number.zendure_set{i}_max_soc": 90 for i in (1, 2, 3)})
    extra.update(kw.pop("extra", {}))
    return runner(kw.pop("start", NIGHT), socs=kw.pop("socs", (80, 80, 80)), extra=extra, **kw)


def test_weekly_day_charges_to_100_in_cheapest_quarters_of_the_day():
    r = cal()
    for i in (1, 2, 3):
        lv(r, i, 10)
    pp = r.run_price()
    assert abs(pp["calib_deficit"] - 3 * 0.2 * 5.76) < 0.05
    hours = {datetime.fromtimestamp(q, TZ).hour for q in pp["calib_slots"]}
    assert hours and hours <= set(range(1, 7))          # the cheap night (0.10), not the peaks
    ends = max(pp["calib_slots"])
    assert datetime.fromtimestamp(ends, TZ).date() == NIGHT.date()


def test_calibration_also_without_profit():
    r = cal(prices=[0.25] * 24)
    for i in (1, 2, 3):
        lv(r, i, 10)
    pp = r.run_price()
    assert pp["calib_slots"] and pp["grid_kwh"] >= pp["calib_deficit"] * 0.9


def test_other_day_or_recently_full_does_nothing():
    r = cal(dag="dinsdag")
    for i in (1, 2, 3):
        lv(r, i, 10)
    assert r.run_price()["calib_deficit"] == 0
    r = cal()
    for i in (1, 2, 3):
        lv(r, i, 1)                                      # reached 100 % yesterday: weekly round skipped
    assert r.run_price()["calib_deficit"] == 0


def test_max_days_and_date():
    r = cal(mode="Alleen na max. aantal dagen")
    lv(r, 1, 30)
    lv(r, 2, 10)
    lv(r, 3, 27)
    pp = r.run_price()
    assert abs(pp["calib_deficit"] - 0.2 * 5.76) < 0.05   # only set 1
    r = cal(mode="Op datum")
    r.hass.set("input_datetime.zendure_ems_kalibratie_datum", NIGHT.strftime("%Y-%m-%d"))
    assert r.run_price()["calib_deficit"] > 3
    r = cal(mode="Uit")
    for i in (1, 2, 3):
        lv(r, i, 40)
    assert r.run_price()["calib_deficit"] == 0


def test_unknown_last_full_never_starts_by_itself():
    r = cal(mode="Alleen na max. aantal dagen")         # input_datetime still at 1970
    assert r.run_price()["calib_deficit"] == 0


def STATE_SENSORS(pkg):
    return [s for b in pkg["template"] if "triggers" not in b for s in b.get("sensor", [])]


def status(r):
    s = next(x for x in STATE_SENSORS(r.pkg) if x["unique_id"] == "zendure_ems_kalibratie")
    return r.hass.render(s["state"])


def test_status_texts():
    r = cal()
    for i in (1, 2, 3):
        lv(r, i, 10)
    assert status(r) == "Bezig: set 1, 2, 3 naar 100 %"
    r = cal(dag="woensdag")
    for i in (1, 2, 3):
        lv(r, i, 2)
    assert status(r) == "Volgende: wo 04-11"         # weekly: 4 days later is enough
    r = cal(mode="Uit")
    lv(r, 1, 3)
    lv(r, 2, 35)
    lv(r, 3, 3)
    assert status(r) == "Te laat: set 2 (35 dagen)"
    days = next(x for x in STATE_SENSORS(r.pkg) if x["unique_id"] == "zendure_set2_dagen_sinds_vol")
    assert int(r.hass.render(days["state"])) == 35


def test_device_max_soc_lifted_only_while_calibrating():
    r = cal(mode="Alleen na max. aantal dagen")
    lv(r, 1, 30)
    lv(r, 2, 3)
    lv(r, 3, 3)
    for s in r.sets:
        s.soc_set = 900
    r.publish()
    a = next(x for x in r.pkg["automation"] if x["id"] == "zendure_ems_soc_grenzen")
    out = {w["sn"]: w["props"]["socSet"] for w in r.hass.render(a["actions"][0]["repeat"]["for_each"])}
    assert out == {"SN1": 1000}


def test_calibrating_set_holds_above_normal_max():
    r = Runner(n=2, socs=(95, 60), load=lambda t: 1500,
               settings={"input_select.zendure_ems_kalibratie": "Alleen na max. aantal dagen",
                         "input_number.zendure_ems_kalibratie_dagen": 28,
                         "input_number.zendure_set1_max_soc": 90, "input_number.zendure_set2_max_soc": 90})
    lv(r, 1, 30)
    lv(r, 2, 3)
    r.run(60)
    assert abs(r.sets[0].actual) < 5                     # set 1 on its way to 100 %: not discharged
    assert r.sets[1].actual < -1300


def test_tracking_automation_records_100_percent():
    r = cal(socs=(100, 80, 100))
    lv(r, 1, 3)
    lv(r, 2, 3)
    lv(r, 3, 0)                                          # already recorded today
    a = next(x for x in r.pkg["automation"] if x["id"] == "zendure_ems_kalibratie_vol")
    assert r.hass.render(a["actions"][0]["variables"]["vol"]) == ["1"]


def test_every_two_or_three_weeks():
    # Monday: due when the last 100 % is at least 10 (2 weeks) or 17 (3 weeks) days ago
    r = cal(mode="Elke 2 weken")
    for i in (1, 2, 3):
        lv(r, i, 7)
    assert r.run_price()["calib_deficit"] == 0
    assert status(r) == "Volgende: ma 09-11"          # today 7 days (< 10), next Monday 14 days
    for i in (1, 2, 3):
        lv(r, i, 12)
    assert r.run_price()["calib_deficit"] > 3
    r = cal(mode="Elke 3 weken", dag="woensdag")
    for i in (1, 2, 3):
        lv(r, i, 2)
    assert status(r) == "Volgende: wo 18-11"          # wo 4-11 = 4 days, 11-11 = 11, 18-11 = 18 >= 17


def test_each_set_on_its_own():
    # set 1 overdue and nearly empty-ish, set 2 just above its max, set 3 not calibrating
    r = cal(mode="Alleen na max. aantal dagen", socs=(50, 92, 30))
    lv(r, 1, 30)
    lv(r, 2, 29)
    lv(r, 3, 3)
    pp = r.run_price()
    assert abs(pp["calib_deficit"] - (0.5 + 0.08) * 5.76) < 0.05      # set 3 is not part of it
    # set 1 needs 2.88 kWh / 0.92 / 0.6 kWh per quarter (2400 W) -> 6 quarters; set 2 charges alongside
    assert len(pp["calib_slots"]) == 6


def test_calibrating_set_charges_first_in_a_calibration_quarter():
    r = Runner(n=2, socs=(85, 30), mode="Prijsgestuurd", load=lambda t: 300,
               settings={"input_select.zendure_ems_kalibratie": "Alleen na max. aantal dagen",
                         "input_number.zendure_ems_kalibratie_dagen": 28,
                         "input_number.zendure_set1_max_soc": 90, "input_number.zendure_set2_max_soc": 90,
                         "input_number.zendure_ems_staging": 100})
    lv(r, 1, 30)
    lv(r, 2, 3)
    r.hass.set("sensor.zendure_ems_prijsactie", "grid_charge", {"laadvermogen": 1200, "kalibratie_nu": True})
    r.run_price = lambda: None                            # keep the price action fixed
    r.run(40)
    assert r.sets[0].actual > 1000 and abs(r.sets[1].actual) < 50


# ---------- 1.12.4: calibration planned on the shared power, the normal plan and the house ----------

def test_system_max_charge_gives_more_quarters():
    def slots(extra):
        r = cal(mode="Alleen na max. aantal dagen", socs=(50, 50, 50), extra=extra)
        for i in (1, 2, 3):
            lv(r, i, 30)
        return r.run_price()
    free = slots({})
    capped = slots({"input_number.zendure_ems_systeem_max_laden": 2400})
    # 3 x 2.88 kWh to 100 % = 8.64 kWh stored = 9.4 kWh from the grid; at 2400 W (0.6 kWh per quarter) 16 quarters
    assert len(free["calib_slots"]) == 6
    assert len(capped["calib_slots"]) >= 16
    assert capped["calib_grid"] >= capped["calib_deficit"] / 0.92 - 0.05
    assert capped["calib_short"] == 0


def test_house_use_before_the_cheap_quarters_is_planned_in():
    # 17:00, evening peak until 22:00, cheapest quarters before midnight at 22-24 (0.25)
    r = cal(mode="Alleen na max. aantal dagen", start=NIGHT.replace(hour=17), socs=(60, 60, 60))
    lv(r, 1, 30)
    lv(r, 2, 3)
    lv(r, 3, 3)
    pp = r.run_price()
    assert pp["calib_house"] > 0.1                     # set 1 still gives to the house during the peak
    assert pp["calib_house"] <= (60 - 10) / 100 * 2.88 + 0.01
    assert pp["calib_grid"] >= (pp["calib_deficit"] + pp["calib_house"]) / 0.92 - 0.05


def test_calibrating_set_gets_full_power_with_default_staging():
    r = Runner(n=2, socs=(85, 30), mode="Prijsgestuurd", load=lambda t: 300,
               settings={"input_select.zendure_ems_kalibratie": "Alleen na max. aantal dagen",
                         "input_number.zendure_ems_kalibratie_dagen": 28,
                         "input_number.zendure_set1_max_soc": 90, "input_number.zendure_set2_max_soc": 90})
    lv(r, 1, 30)
    lv(r, 2, 3)
    r.hass.set("sensor.zendure_ems_prijsactie", "grid_charge", {"laadvermogen": 2400, "kalibratie_nu": True})
    r.run_price = lambda: None
    r.run(40)
    assert r.sets[0].actual > 2300 and abs(r.sets[1].actual) < 50


def test_other_set_takes_only_the_rest_in_a_calibration_quarter():
    r = Runner(n=2, socs=(85, 30), mode="Prijsgestuurd", load=lambda t: 300,
               settings={"input_select.zendure_ems_kalibratie": "Alleen na max. aantal dagen",
                         "input_number.zendure_ems_kalibratie_dagen": 28,
                         "input_number.zendure_set1_max_soc": 90, "input_number.zendure_set2_max_soc": 90})
    lv(r, 1, 30)
    lv(r, 2, 3)
    r.hass.set("sensor.zendure_ems_prijsactie", "grid_charge", {"laadvermogen": 3400, "kalibratie_nu": True})
    r.run_price = lambda: None
    r.run(40)
    assert r.sets[0].actual > 2300 and 800 < r.sets[1].actual < 1200


# ---------- 1.12.4: deadline the next morning, planned selling counted ----------

TWO_DAYS = PRICES + [0.08] * 7 + [0.30] * 17          # Monday as before, Tuesday night 00-07 even cheaper
TRADE = {"input_boolean.zendure_ems_verkoop_plannen": "on", "input_number.zendure_ems_verkoopprijs": 0.35,
         "input_number.zendure_ems_min_spread": 0.05, "input_number.zendure_ems_slijtage": 0.03}


def at_hours(pp):
    return [datetime.fromtimestamp(q, TZ) for q in pp["calib_slots"]]


def test_deadline_next_morning_uses_the_night_after():
    r = cal(mode="Alleen na max. aantal dagen", start=NIGHT.replace(hour=17), socs=(60, 60, 60), prices=TWO_DAYS)
    lv(r, 1, 30)
    lv(r, 2, 3)
    lv(r, 3, 3)
    pp = r.run_price()
    slots = at_hours(pp)
    assert slots and all(s.date() == NIGHT.date() + timedelta(days=1) and s.hour < 7 for s in slots)
    assert pp["calib_short"] == 0
    assert datetime.fromtimestamp(pp["calib_until"], TZ).hour == 7


def test_deadline_zero_keeps_midnight():
    r = cal(mode="Alleen na max. aantal dagen", start=NIGHT.replace(hour=17), socs=(60, 60, 60), prices=TWO_DAYS,
            extra={"input_number.zendure_ems_kalibratie_tot": 0})
    lv(r, 1, 30)
    lv(r, 2, 3)
    lv(r, 3, 3)
    pp = r.run_price()
    assert pp["calib_slots"] and all(s.date() == NIGHT.date() for s in at_hours(pp))


def test_calibration_day_runs_on_until_the_morning():
    # weekly on Monday; it is Tuesday 02:00 and set 1 has not reached 100 % yet
    tue = NIGHT.replace(hour=2) + timedelta(days=1)
    r = cal(start=tue, socs=(70, 80, 80), prices=[0.08] * 7 + [0.30] * 17)
    lv(r, 1, 11)                                       # 10 days before Monday
    lv(r, 2, 1)                                        # reached 100 % on Monday: done
    lv(r, 3, 1)
    pp = r.run_price()
    assert abs(pp["calib_deficit"] - 0.3 * 5.76) < 0.05
    assert all(s.hour < 7 for s in at_hours(pp))
    assert datetime.fromtimestamp(pp["calib_until"], TZ) == tue.replace(hour=7, minute=0, second=0)
    # after 07:00 it is over
    r = cal(start=tue.replace(hour=8), socs=(70, 80, 80), prices=[0.08] * 7 + [0.30] * 17)
    lv(r, 1, 11)
    lv(r, 2, 1)
    lv(r, 3, 1)
    assert r.run_price()["calib_deficit"] == 0


def test_planned_selling_is_bought_back_after_the_sales():
    # 13:00, sell peak 16-22, then the cheap night: what set 1 sells before its last calibration quarter is planned in
    def plan(extra):
        r = cal(mode="Alleen na max. aantal dagen", start=NIGHT.replace(hour=13), socs=(90, 90, 90),
                prices=PRICES + [0.08] * 7, extra=extra)
        lv(r, 1, 30)
        lv(r, 2, 3)
        lv(r, 3, 3)
        return r.run_price()
    own = {"input_number.zendure_set1_max_soc": 100}       # like most installs: no lower max, so set 1 sells too
    pp = plan(dict(TRADE, **own))
    assert pp["sell_kwh"] > 1
    assert pp["calib_sell"] > 0.1
    last_sale = max(pp["sell_slots"])
    assert any(q > last_sale for q in pp["calib_slots"])
    need = (pp["calib_deficit"] + pp["calib_house"] + pp["calib_sell"]) / 0.92
    assert pp["calib_grid"] >= need - 0.1 and pp["calib_short"] == 0
    assert plan(own)["calib_sell"] == 0
    assert plan(TRADE)["calib_sell"] == 0                  # max SOC 90: set 1 holds above it and does not sell


def test_update_sets_klaar_om_to_seven_once():
    r = cal()
    assert float(r.hass.states["input_number.zendure_ems_kalibratie_tot"].state) == 7     # new install
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_update")
    br = next(x for x in auto["actions"] if "if" in x and any(
        t.get("target", {}).get("entity_id") == "input_number.zendure_ems_kalibratie_tot" for t in x["then"]))
    cond = br["if"][0]["value_template"]
    for v, exp in (("1.12.4", True), ("1.9.11", True), ("1.12.5", False), ("1.13.0", False), ("", False)):
        r.hass.set("input_text.zendure_ems_versie", v)
        assert r.hass.render(cond) is exp, v
