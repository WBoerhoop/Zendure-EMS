"""Quarter-hour planner: solar forecast, consumption profile, deadline-aware grid charging."""

from datetime import datetime, timedelta

from ha_sim import TZ
from test_package import Runner

NIGHT = datetime(2026, 11, 2, 1, 0, 3, tzinfo=TZ)
DAY = NIGHT.replace(hour=0, minute=0, second=0)

# 0-6 cheap night, 7-9 morning peak, 10-15 midday, 16-21 evening peak, 22-23 late
PRICES = [0.10] * 7 + [0.30] * 3 + [0.22] * 6 + [0.40] * 6 + [0.25] * 2

SMART = {"input_boolean.zendure_ems_slim_laden": "on"}


def runner(start, socs=(15, 15, 15), sun_kwh=None, prices=PRICES, extra=None, **kw):
    settings = dict(SMART)
    settings.update(extra or {})
    r = Runner(mode="Prijsgestuurd", prices=prices, socs=socs, start=start, settings=settings, **kw)
    if sun_kwh is not None:
        r.hass.set("input_text.zendure_ems_zon_vandaag", "sensor.zon_vandaag")
        r.hass.set("sensor.zon_vandaag", sun_kwh, {"unit_of_measurement": "kWh"})
    r.publish()
    return r


def at(h, m=0):
    return NIGHT.replace(hour=h, minute=m)


def test_sun_reduces_grid_charging():
    cloudy = runner(NIGHT).run_price()
    sunny = runner(NIGHT, sun_kwh=12).run_price()
    print("cloudy", cloudy["grid_kwh"], "sunny", sunny["grid_kwh"], sunny["sun_kwh"])
    assert cloudy["grid_kwh"] > 6
    assert 0 < sunny["grid_kwh"] < cloudy["grid_kwh"] - 4
    assert abs(sunny["sun_kwh"] - 12 * 0.8) < 0.2  # zon_factor 80 %
    # grid charging is planned in the cheap night, before the morning peak
    hours = {datetime.fromtimestamp(q, TZ).hour for q in cloudy["charge_slots"]}
    assert hours and max(hours) <= 6


def test_battery_used_first_charge_late_in_cheap_window():
    pp = runner(NIGHT).run_price()
    assert pp["action"] == "zero"  # 01:00: battery still serves the house
    pp = runner(at(6, 30), socs=(10, 10, 10)).run_price()
    assert pp["action"] == "grid_charge" and 0 < pp["charge_w"] <= 7200
    assert "Gepland laden" in pp["reason"]


def test_not_worth_it_no_charging():
    flat = [0.25] * 24
    pp = runner(NIGHT, prices=flat).run_price()
    assert pp["grid_kwh"] == 0 and pp["action"] == "zero"


def test_quarter_hour_prices_pick_cheap_quarter():
    r = runner(at(10), socs=(20, 20, 20))
    q = []
    for k in range(96):
        hh = k // 4
        p = 0.45 if 17 <= hh <= 21 else 0.25
        if hh == 12 and k % 4 == 1:
            p = 0.01  # 12:15-12:30
        q.append({"time": (DAY + timedelta(minutes=15 * k)).isoformat(), "price": p})
    r.hass.set("sensor.nordpool", 0.25, {"prices_today": q, "prices_tomorrow": []})
    pp = r.run_price()
    starts = [datetime.fromtimestamp(s, TZ).strftime("%H:%M") for s in pp["charge_slots"]]
    print(starts, pp["grid_kwh"])
    assert "12:15" in starts and all(s < "17:00" for s in starts)
    assert pp["n_quarters"] == 56  # 10:00 .. 24:00


def test_hourly_prices_are_split_in_quarters():
    pp = runner(NIGHT).run_price()
    assert pp["n_quarters"] == 92  # 01:00 .. 24:00
    assert len({u["s"] for u in pp["upcoming"]}) == 92


def test_smart_discharge_holds_for_evening_peak():
    prices = [0.20] * 17 + [0.45] * 5 + [0.25] * 2
    extra = {"input_boolean.zendure_ems_slim_laden": "off", "input_boolean.zendure_ems_slim_ontladen": "on"}
    pp = runner(at(10), socs=(30, 30, 30), prices=prices, extra=extra).run_price()
    held = [datetime.fromtimestamp(u["s"], TZ).hour for u in pp["upcoming"] if u["h"]]
    peak_short = sum(u["u"] for u in pp["upcoming"] if u["p"] == 0.45)
    # cheap daytime quarters are held so the evening peak is fully covered
    assert held and max(held) < 17 and peak_short < 0.01
    assert pp["action"] == "zero"  # equal prices: the latest cheap quarters are held, not now
    pp = runner(at(12), socs=(27, 27, 27), prices=prices, extra=extra).run_price()
    assert pp["action"] == "hold" and pp["reason"].startswith("Accu bewaard voor 02-11 ")
    # with a full battery there is nothing to save for
    assert runner(at(10), socs=(100, 100, 100), prices=prices, extra=extra).run_price()["action"] == "zero"


def test_shift_preferred_over_buying_when_cheaper():
    # Day 0.20, evening 0.45; buying at night 0.10 costs 0.10/0.85+0.03 = 0.148 < holding at 0.20
    prices = [0.10] * 7 + [0.20] * 10 + [0.45] * 5 + [0.25] * 2
    both = {"input_boolean.zendure_ems_slim_laden": "on", "input_boolean.zendure_ems_slim_ontladen": "on"}
    pp = runner(NIGHT, socs=(15, 15, 15), prices=prices, extra=both).run_price()
    ch_hours = {datetime.fromtimestamp(u["s"], TZ).hour for u in pp["upcoming"] if u["c"] > 0}
    assert ch_hours and max(ch_hours) <= 6  # bought in the cheap night
    # expensive night (0.19): holding at 0.20 is cheaper than buying at 0.19/0.85+0.03 = 0.254
    prices2 = [0.19] * 7 + [0.20] * 10 + [0.45] * 5 + [0.25] * 2
    pp2 = runner(NIGHT, socs=(60, 60, 60), prices=prices2, extra=both).run_price()
    assert pp2["grid_kwh"] < pp["grid_kwh"]
    assert any(u["h"] for u in pp2["upcoming"])


def test_wear_cost_blocks_marginal_charging():
    prices = [0.20] * 7 + [0.30] * 17
    base = runner(NIGHT, socs=(15, 15, 15), prices=prices).run_price()  # 0.20/0.85+0.03+0.05 = 0.315 > 0.30
    assert base["grid_kwh"] == 0
    cheap = runner(NIGHT, socs=(15, 15, 15), prices=prices,
                   extra={"input_number.zendure_ems_slijtage": 0.0}).run_price()  # 0.285 <= 0.30
    assert cheap["grid_kwh"] > 0


def test_control_follows_planned_charge_power():
    r = Runner(mode="Prijsgestuurd", prices=PRICES, socs=(10, 10, 10), start=at(6, 50), settings=SMART,
               load=lambda t: 400)
    r.run(180)
    target = r.pp["charge_w"]
    assert r.pp["action"] == "grid_charge"
    assert abs(sum(r.log[-1][2]) - min(target, 7200)) < 300, (target, r.log[-1][2])


def test_solcast_detailed_forecast():
    r = runner(at(10))
    det = [{"period_start": (at(10) + timedelta(minutes=30 * k)).replace(second=0).isoformat(), "pv_estimate": 2.0,
            "pv_estimate10": 1.0} for k in range(8)]
    r.hass.set("input_text.zendure_ems_zon_vandaag", "sensor.solcast_today")
    r.hass.set("sensor.solcast_today", 30, {"detailedForecast": det})
    pp = r.run_price()
    assert pp["solar_source"].startswith("Solcast")
    assert abs(pp["sun_kwh"] - 2.0 * 4 * 0.8) < 0.1  # 4 h of 2 kW, 80 %


def test_house_consumption_sensor():
    r = Runner(load=lambda t: 1500).run(60)
    from test_package import STATE_SENSORS
    s = next(x for x in STATE_SENSORS(r.pkg) if x["unique_id"] == "zendure_ems_huisverbruik")
    tot = sum(float(r.hass.render(x["state"])) for x in STATE_SENSORS(r.pkg)
              if x["unique_id"].startswith("zendure_ems_set") and x["unique_id"].endswith("_vermogen"))
    r.hass.set("sensor.zendure_ems_accuvermogen", tot)
    house = r.hass.render(s["state"])
    assert abs(house - 1500) < 60, house


def test_planner_render_time():
    import time
    r = runner(NIGHT)
    q = [{"time": (DAY + timedelta(minutes=15 * k)).isoformat(), "price": PRICES[(k // 4) % 24]} for k in range(192)]
    r.hass.set("sensor.nordpool", 0.1, {"prices_today": q[:96], "prices_tomorrow": q[96:]})
    r.hass.set("input_text.zendure_ems_zon_morgen", "sensor.zon_morgen")
    r.hass.set("sensor.zon_morgen", 10, {"unit_of_measurement": "kWh"})
    t = time.perf_counter()
    pp = r.run_price()
    dt = time.perf_counter() - t
    print("render s", dt, pp["n_quarters"], pp["grid_kwh"])
    assert pp["n_quarters"] == 144 and dt < 3


def test_forecast_solar_prefill_and_distribution():
    r = runner(at(10))
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_standaardwaarden")
    sets = [x for x in auto["actions"] if x.get("action") == "input_text.set_value"]
    r.hass.set("input_text.zendure_ems_zon_vandaag", "")
    assert r.hass.render(sets[0]["data"]["value"]) == ""  # sensor does not exist yet
    r.hass.set("sensor.energy_production_today_remaining", 6.5, {"unit_of_measurement": "kWh"})
    r.hass.set("sensor.energy_production_tomorrow", 9.0, {"unit_of_measurement": "kWh"})
    v0 = r.hass.render(sets[0]["data"]["value"])
    v1 = r.hass.render(sets[1]["data"]["value"])
    assert v0 == "sensor.energy_production_today_remaining" and v1 == "sensor.energy_production_tomorrow"
    r.hass.set("input_text.zendure_ems_zon_vandaag", v0)
    r.hass.set("input_text.zendure_ems_zon_morgen", v1)
    pp = r.run_price()
    sun_by_hour = {}
    for u in pp["upcoming"]:
        hh = datetime.fromtimestamp(u["s"], TZ).hour
        sun_by_hour[hh] = sun_by_hour.get(hh, 0) + u["z"]
    print(sun_by_hour)
    assert abs(pp["sun_kwh"] - 6.5 * 0.8) < 0.1  # tomorrow is beyond the price horizon here
    assert sun_by_hour[12] > sun_by_hour[15] > sun_by_hour.get(17, 0) == 0
    assert sun_by_hour[10] > 0
