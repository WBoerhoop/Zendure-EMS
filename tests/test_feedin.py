"""Feed-in price: saldering until 2026, bare price + fixed fee + bonus (Zonneplan) from 2027."""
from datetime import datetime, timedelta

from ha_sim import TZ
from test_package import Runner, nordpool_attrs

D27 = datetime(2027, 1, 11, 12, 5, 3, tzinfo=TZ)  # Monday, midday
KALE = [0.10] * 7 + [0.15] * 4 + [-0.05] * 3 + [0.12] * 4 + [0.25] * 6
IMPORT = [round(k * 1.21 + 0.1065 + 0.02, 4) for k in KALE]


def runner27(start=D27, zonneplan=True, kale_sensor=True, **settings):
    s = {"input_number.zendure_ems_teruglever_vast": 0.02 if zonneplan else 0.0,
         "input_number.zendure_ems_teruglever_bonus": 10.0 if zonneplan else 0.0,
         "input_boolean.zendure_ems_teruglever_btw": "on", "input_boolean.zendure_ems_bonus_overdag": "on",
         "input_select.zendure_ems_salderen": "Automatisch (t/m 2026)",
         "input_number.zendure_ems_energiebelasting": 0.1065, "input_number.zendure_ems_inkoop": 0.02}
    s.update(settings)
    r = Runner(mode="Prijsgestuurd", prices=IMPORT, socs=(60, 60, 60), start=start, settings=s)
    day = start.replace(hour=0, minute=0, second=0)
    r.hass.set("sensor.nordpool", IMPORT[start.hour], nordpool_attrs(IMPORT, day=day))
    if kale_sensor:
        r.hass.set("input_text.zendure_ems_terugleverprijs_sensor", "sensor.kale")
        r.hass.set("sensor.kale", KALE[start.hour], nordpool_attrs(KALE, day=day))
    r.publish()
    return r


def xp(pp, hour):
    return next(u["x"] for u in pp["upcoming"] if datetime.fromtimestamp(u["s"], TZ).hour == hour)


def test_2026_saldering_feed_in_equals_import():
    r = runner27(start=datetime(2026, 11, 2, 12, 5, 3, tzinfo=TZ))
    pp = r.run_price()
    assert pp["salderen"] is True and pp["export_price"] == pp["price"]
    assert all(u["x"] == u["p"] for u in pp["upcoming"])


def test_2027_zonneplan_bonus_daylight_and_positive_only():
    pp = runner27().run_price()
    assert pp["salderen"] is False
    # 15:00 kale 0.12 (daylight): (0.12 * 1.21 + 0.02) * 1.10
    assert abs(xp(pp, 15) - (0.12 * 1.21 + 0.02) * 1.10) < 1e-4
    # 20:00 kale 0.25 (after sunset): no bonus
    assert abs(xp(pp, 20) - (0.25 * 1.21 + 0.02)) < 1e-4
    # 12:00 kale -0.05: base -0.0405 is negative, no bonus
    assert abs(xp(pp, 12) - (-0.05 * 1.21 + 0.02)) < 1e-4
    assert pp["price"] > 0 and pp["export_price"] < 0  # import positive, feed-in negative
    assert "bonus 10 % overdag" in pp["export_source"]


def test_2027_without_kale_sensor_derives_from_import():
    pp = runner27(kale_sensor=False, zonneplan=False).run_price()
    assert abs(xp(pp, 15) - 0.12 * 1.21) < 1e-3  # (import - eb - inkoop) / 1.21 * 1.21
    assert pp["export_source"].startswith("afgeleid uit afnameprijs")


def test_salderen_forced():
    pp = runner27(**{"input_select.zendure_ems_salderen": "Aan"}).run_price()
    assert pp["salderen"] is True and pp["export_price"] == pp["price"]
    pp = runner27(start=datetime(2026, 11, 2, 12, 5, 3, tzinfo=TZ), **{"input_select.zendure_ems_salderen": "Uit"}).run_price()
    assert pp["salderen"] is False


def test_curtail_uses_feed_in_price_in_2027():
    r = runner27(start=D27)
    pp = r.run_price()
    for sens in r.pkg["template"][0]["sensor"]:
        attrs = {k: r.hass.render(v, pp=pp) for k, v in (sens.get("attributes") or {}).items()}
        r.hass.set("sensor." + sens["unique_id"], r.hass.render(sens["state"], pp=pp), attrs)
    assert float(r.hass.states["sensor.zendure_ems_stroomprijs"].state) > 0
    assert float(r.hass.states["sensor.zendure_ems_terugleverprijs"].state) < 0
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_afschalen")
    r.hass.set("input_select.zendure_ems_afschalen", "Direct")
    assert r.hass.render(auto["actions"][0]["variables"]["want"]) is True
    # charging from the grid is not triggered: the import price is still positive
    assert pp["action"] != "grid_charge" or pp["reason"] != "Negatieve stroomprijs"


def test_sell_uses_feed_in_price():
    r = runner27(start=D27.replace(hour=18), **{"input_number.zendure_ems_verkoopprijs": 0.40})
    pp = r.run_price()  # import 0.43 >= 0.40, but feed-in (0.25*1.21+0.02) = 0.3225 < 0.40
    assert pp["price"] >= 0.40 and pp["action"] != "sell"
    r = runner27(start=D27.replace(hour=18), **{"input_number.zendure_ems_verkoopprijs": 0.30})
    assert r.run_price()["action"] == "sell"
