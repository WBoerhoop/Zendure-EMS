"""Werkdag/weekend profiles, learning solar correction and the start profile from history."""
from datetime import datetime, timedelta

from ha_sim import TZ
from test_package import Runner
from test_planner import runner

MON = datetime(2026, 11, 2, 10, 15, 3, tzinfo=TZ)  # Monday
SAT = datetime(2026, 11, 7, 10, 15, 3, tzinfo=TZ)  # Saturday


def block(pkg, pred):
    return next(b for b in pkg["template"] if b.get("triggers") and pred(b["triggers"]))


def profile_tpl(pkg):
    return block(pkg, lambda tr: tr[0].get("minutes") == "/15")["actions"][0]["variables"]["prof"]


def corr_block(pkg):
    return block(pkg, lambda tr: any(x.get("id") == "avond" for x in tr))


def set_profile(r, prof):
    r.hass.set("sensor.zendure_ems_verbruiksprofiel", prof["avg"], {
        "werkdag": prof["w"], "weekend": prof["e"], "metingen_werkdag": prof["nw"], "metingen_weekend": prof["ne"]})


# ------------------------------------------------------------- profiles
def test_weekday_and_weekend_learn_separately():
    r = Runner(start=MON)
    tpl = profile_tpl(r.pkg)
    r.hass.set("sensor.zendure_ems_huisverbruik_kwartiergemiddelde", 800)
    prof = r.hass.render(tpl, trigger={"platform": "time_pattern"})
    assert prof["w"][40] == 800 and prof["nw"][40] == 1 and prof["e"][40] == 400 and prof["ne"][40] == 0
    set_profile(r, prof)
    r.hass.now = SAT
    r.hass.set("sensor.zendure_ems_huisverbruik_kwartiergemiddelde", 1200)
    prof = r.hass.render(tpl, trigger={"platform": "time_pattern"})
    assert prof["e"][40] == 1200 and prof["ne"][40] == 1 and prof["w"][40] == 800
    assert prof["learned_w"] == 1 and prof["learned_e"] == 1


def test_migration_from_single_profile():
    r = Runner(start=MON)
    r.hass.set("sensor.zendure_ems_verbruiksprofiel", 500, {"kwartier": [500] * 96, "metingen": [7] * 96})
    r.hass.set("sensor.zendure_ems_huisverbruik_kwartiergemiddelde", "unavailable")
    prof = r.hass.render(profile_tpl(r.pkg), trigger={"platform": "time_pattern"})
    assert prof["w"] == [500] * 96 and prof["e"] == [500] * 96 and prof["nw"] == [7] * 96 and prof["ne"] == [7] * 96


def test_start_profile_event_overwrites():
    r = Runner(start=MON)
    data = {"werkdag": [300] * 96, "weekend": [600] * 96, "metingen_werkdag": [5] * 96, "metingen_weekend": [4] * 96}
    prof = r.hass.render(profile_tpl(r.pkg), trigger={"platform": "event", "event": {"data": data}})
    assert prof["w"] == [300] * 96 and prof["e"] == [600] * 96 and prof["ne"] == [4] * 96


def test_planner_uses_weekend_profile_on_weekend_quarters():
    fri = datetime(2026, 11, 6, 20, 0, 3, tzinfo=TZ)  # Friday evening, horizon into Saturday
    prices = [0.25] * 48
    r = runner(fri, prices=prices)
    from test_package import nordpool_attrs
    r.hass.set("sensor.nordpool", 0.25, nordpool_attrs(prices, day=fri.replace(hour=0, minute=0, second=0)))
    r.hass.set("sensor.zendure_ems_verbruiksprofiel", 400, {
        "werkdag": [400] * 96, "weekend": [1000] * 96, "metingen_werkdag": [3] * 96, "metingen_weekend": [3] * 96})
    pp = r.run_price()
    fr = [u["v"] for u in pp["upcoming"] if datetime.fromtimestamp(u["s"], TZ).weekday() == 4]
    sa = [u["v"] for u in pp["upcoming"] if datetime.fromtimestamp(u["s"], TZ).weekday() == 5]
    assert abs(fr[1] - 0.1) < 0.001 and abs(sa[1] - 0.25) < 0.001
    assert "weekend 96/96" in pp["profile"]


def test_unlearned_weekend_falls_back_to_weekday():
    fri = datetime(2026, 11, 6, 20, 0, 3, tzinfo=TZ)
    prices = [0.25] * 48
    r = runner(fri, prices=prices)
    from test_package import nordpool_attrs
    r.hass.set("sensor.nordpool", 0.25, nordpool_attrs(prices, day=fri.replace(hour=0, minute=0, second=0)))
    r.hass.set("sensor.zendure_ems_verbruiksprofiel", 400, {
        "werkdag": [800] * 96, "weekend": [400] * 96, "metingen_werkdag": [3] * 96, "metingen_weekend": [0] * 96})
    pp = r.run_price()
    sa = [u["v"] for u in pp["upcoming"] if datetime.fromtimestamp(u["s"], TZ).weekday() == 5]
    assert abs(sa[1] - 0.2) < 0.001  # 800 W from the weekday profile


# ------------------------------------------------------------- solar correction
def corr(r, trig_id):
    blk = corr_block(r.pkg)
    zc = r.hass.render(blk["actions"][0]["variables"]["zc"], trigger={"id": trig_id})
    sens = blk["sensor"][0]
    attrs = {k: r.hass.render(v, zc=zc) for k, v in sens["attributes"].items()}
    r.hass.set("sensor.zendure_ems_zonnecorrectie", r.hass.render(sens["state"], zc=zc), attrs)
    return zc


def test_solar_correction_learns_from_measurement():
    r = Runner(start=MON)
    r.hass.set("input_text.zendure_ems_zon_vandaag", "sensor.energy_production_today_remaining")
    r.hass.set("input_text.zendure_ems_zonproductie", "sensor.omvormer")
    r.hass.set("sensor.zendure_ems_zonne_energie", 120.0)
    for day in range(5):
        r.hass.set("sensor.energy_production_today_remaining", 10.0, {"unit_of_measurement": "kWh"})
        zc = corr(r, "ochtend")
        assert zc["exp"] == 10.0
        r.hass.set("sensor.zendure_ems_zonne_energie_vandaag", 6.0)  # forecast 40 % too optimistic
        zc = corr(r, "avond")
    assert zc["dagen"] == 5 and 0.6 < zc["factor"] < 0.72  # 0.8 -> towards 0.6
    assert len(zc["hist"]) == 5 and zc["hist"][-1]["gemeten"] == 6.0
    zc = corr(r, "reset")
    assert zc["dagen"] == 0 and zc["factor"] == 0.8


def test_solar_correction_skips_without_measurement_or_sun():
    r = Runner(start=MON)
    r.hass.set("input_text.zendure_ems_zon_vandaag", "sensor.zv")
    r.hass.set("sensor.zv", 10.0, {"unit_of_measurement": "kWh"})
    corr(r, "ochtend")
    r.hass.set("sensor.zendure_ems_zonne_energie_vandaag", 0.0)
    zc = corr(r, "avond")  # no production source at all
    assert zc["dagen"] == 0 and zc["factor"] == 0.8 and "overgeslagen" in zc["msg"]
    r.hass.set("input_text.zendure_ems_zonproductie", "sensor.omvormer")
    r.hass.set("sensor.zv", 0.5, {"unit_of_measurement": "kWh"})
    corr(r, "ochtend")
    r.hass.set("sensor.zendure_ems_zonne_energie_vandaag", 0.4)
    assert corr(r, "avond")["dagen"] == 0  # forecast below 1 kWh: too noisy


def test_planner_uses_learned_factor_after_3_days():
    r = runner(datetime(2026, 11, 2, 7, 0, 3, tzinfo=TZ), sun_kwh=10)
    base = r.run_price()["sun_kwh"]
    assert abs(base - 8.0) < 0.1  # fixed 80 %
    r.hass.set("input_boolean.zendure_ems_zon_leren", "on")
    r.hass.set("sensor.zendure_ems_zonnecorrectie", 60, {"factor": 0.6, "dagen": 2})
    assert abs(r.run_price()["sun_kwh"] - 8.0) < 0.1  # fewer than 3 days: still fixed
    r.hass.set("sensor.zendure_ems_zonnecorrectie", 60, {"factor": 0.6, "dagen": 3})
    pp = r.run_price()
    assert abs(pp["sun_kwh"] - 6.0) < 0.1 and "60 % (geleerd)" in pp["solar_source"]


def test_solar_production_sensor():
    r = Runner(start=MON).run(10)
    from test_package import STATE_SENSORS
    s = next(x for x in STATE_SENSORS(r.pkg) if x["unique_id"] == "zendure_ems_zonneproductie")
    assert r.hass.render(s["state"]) == 0
    r.hass.set("input_text.zendure_ems_zonproductie", "sensor.omvormer")
    r.hass.set("sensor.omvormer", 1.5, {"unit_of_measurement": "kW"})
    assert r.hass.render(s["state"]) == 1500


# ------------------------------------------------------------- start profile from history
def fake_stats(days=14, accu=True, solar=True):
    end = datetime(2026, 11, 3, 0, 0, tzinfo=TZ)
    g, a, z = [], [], []
    for hh in range(days * 24):
        st = end - timedelta(hours=days * 24 - hh)
        we = st.weekday() >= 5
        h = st.hour
        house = (900 if we else 500) if h == 12 else 300
        sun = 1000 if h == 12 else 0
        bat = -200 if h == 20 else 0  # battery discharging in the evening
        grid = house - sun + bat
        iso = st.astimezone(TZ).isoformat()
        g.append({"start": iso, "end": iso, "mean": grid})
        a.append({"start": iso, "end": iso, "mean": bat})
        z.append({"start": iso, "end": iso, "mean": sun})
    out = {"statistics": {"sensor.p1_vermogen": g}}
    if accu:
        out["statistics"]["sensor.zendure_ems_accuvermogen"] = a
    if solar:
        out["statistics"]["sensor.omvormer"] = z
    return out


def script(pkg):
    return pkg["script"]["zendure_ems_startprofiel"]["sequence"]


def test_start_profile_from_history():
    r = Runner(start=MON)
    seq = script(r.pkg)
    r.hass.set("input_text.zendure_ems_zonproductie", "sensor.omvormer")
    ids = r.hass.render(seq[0]["variables"]["ids"])
    assert ids == {"grid": "sensor.p1_vermogen", "accu": "sensor.zendure_ems_accuvermogen", "solar": "sensor.omvormer",
                   "ev": "unknown", "acc_in": "unknown", "acc_out": "unknown"}
    call = seq[1]
    assert call["action"] == "recorder.get_statistics" and call["data"]["units"] == {"power": "W"}
    sid = r.hass.render(call["data"]["statistic_ids"], ids=ids)
    assert sid == ["sensor.p1_vermogen", "sensor.zendure_ems_accuvermogen", "sensor.omvormer"]
    n = r.hass.render(seq[0]["variables"]["n"], dagen=500)
    assert n == 90
    start = r.hass.render(call["data"]["start_time"], n=28)
    assert start.startswith("2026-10-05T10:00:00")
    prof = r.hass.render(seq[2]["variables"]["prof"], stats=fake_stats(), ids=ids, fallback=400)
    assert prof["uren"] == 14 * 24
    assert prof["werkdag"][48:52] == [500] * 4 and prof["weekend"][48] == 900  # 12:00, sun added back
    assert prof["werkdag"][80] == 300  # 20:00, battery taken out again
    assert prof["metingen_werkdag"][48] == 5 and prof["metingen_weekend"][48] == 4
    # event data renders to lists
    ev = next(x for x in seq if "event" in x)
    assert r.hass.render(ev["event_data"]["werkdag"], prof=prof) == prof["werkdag"]


def test_start_profile_too_little_history():
    r = Runner(start=MON)
    seq = script(r.pkg)
    ids = r.hass.render(seq[0]["variables"]["ids"])
    prof = r.hass.render(seq[2]["variables"]["prof"], stats={"statistics": {}}, ids=ids, fallback=400)
    cond = seq[3]["if"][0]["value_template"]
    assert prof["uren"] == 0 and r.hass.render(cond, prof=prof) is True


def test_start_profile_takes_ev_out():
    r = Runner(start=MON)
    seq = script(r.pkg)
    r.hass.set("input_text.zendure_ems_zonproductie", "sensor.omvormer")
    r.hass.set("input_text.zendure_ems_ev_sensor", "sensor.autolader_power")
    ids = r.hass.render(seq[0]["variables"]["ids"])
    sid = r.hass.render(seq[1]["data"]["statistic_ids"], ids=ids)
    assert sid[-1] == "sensor.autolader_power"
    stats = fake_stats()
    ev = []
    for row in stats["statistics"]["sensor.p1_vermogen"]:
        h = datetime.fromisoformat(row["start"]).hour
        e = 2300 if h == 3 else 0
        row["mean"] += e
        ev.append({"start": row["start"], "end": row["end"], "mean": e})
    stats["statistics"]["sensor.autolader_power"] = ev
    prof = r.hass.render(seq[2]["variables"]["prof"], stats=stats, ids=ids, fallback=400)
    assert prof["werkdag"][12] == 300  # 03:00 night charging is not house consumption


def test_start_profile_uses_old_battery_sensors_before_ems():
    """Before Zendure EMS a previous controller (Gielz) ran the battery: its import/export sensors fill the gap."""
    r = Runner(start=MON)
    seq = script(r.pkg)
    h = r.hass
    h.set("input_text.zendure_ems_zonproductie", "sensor.omvormer")
    h.set("input_text.zendure_ems_historie_laden", "sensor.zendure_2400_ac_vermogen_import")
    h.set("input_text.zendure_ems_historie_ontladen", "sensor.zendure_2400_ac_vermogen_export")
    ids = h.render(seq[0]["variables"]["ids"])
    sid = h.render(seq[1]["data"]["statistic_ids"], ids=ids)
    assert sid[-2:] == ["sensor.zendure_2400_ac_vermogen_import", "sensor.zendure_2400_ac_vermogen_export"]
    # old battery discharged 400 W at 09:00 and P1 showed 0: the house used 400 W, not 0
    stats = fake_stats(accu=False)
    exp = []
    for row in stats["statistics"]["sensor.p1_vermogen"]:
        hh = datetime.fromisoformat(row["start"]).hour
        e = 400 if hh == 9 else 0
        row["mean"] -= e
        exp.append({"start": row["start"], "end": row["end"], "mean": e})
    stats["statistics"]["sensor.zendure_2400_ac_vermogen_export"] = exp
    prof = h.render(seq[2]["variables"]["prof"], stats=stats, ids=ids, fallback=400)
    assert prof["werkdag"][36] == 300                     # 09:00 = the real house load
    # once Zendure EMS has its own battery history, that one wins
    stats["statistics"]["sensor.zendure_ems_accuvermogen"] = [
        {"start": r_["start"], "end": r_["end"], "mean": -400 if datetime.fromisoformat(r_["start"]).hour == 9 else 0}
        for r_ in stats["statistics"]["sensor.p1_vermogen"]]
    prof = h.render(seq[2]["variables"]["prof"], stats=stats, ids=ids, fallback=400)
    assert prof["werkdag"][36] == 300
