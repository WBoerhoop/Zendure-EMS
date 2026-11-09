"""Nordpool right after a restart: prices briefly without the additional costs; the planner adds them back."""
from datetime import timedelta

from test_package import START, Runner, nordpool_attrs

PR = [0.25] * 7 + [0.30] * 10 + [0.45] * 4 + [0.30] * 3 + [0.25] * 24
ADD = 0.20


def attrs(add, prices):
    a = nordpool_attrs(prices, day=START.replace(hour=0, minute=0, second=0))
    a["additional_costs_current_hour"] = add
    return a


def keep(r, pp):
    r.hass.set("sensor.zendure_ems_prijsactie", pp["action"],
               {"nordpool_opslag": pp["np_add"], "nordpool_opslag_tijd": pp["np_ats"]})


def test_missing_costs_restored_after_restart():
    full = [p + ADD for p in PR]
    r = Runner(n=1, socs=(50,), prices=full, mode="Prijsgestuurd")
    r.hass.set("sensor.nordpool", full[10], attrs(ADD, full))
    pp = r.run_price()
    assert abs(pp["price"] - full[10]) < 1e-6 and not pp["np_fix"]
    keep(r, pp)
    # restart: Nordpool now gives the bare prices and 0 additional costs
    r.hass.now = START + timedelta(minutes=10)
    r.hass.set("sensor.nordpool", PR[10], attrs(0.0, PR))
    pp = r.run_price()
    assert pp["np_fix"] and abs(pp["price"] - full[10]) < 1e-6
    assert all(abs(u["p"] - (PR[0] + ADD)) < 0.31 for u in pp["upcoming"][:1])


def test_no_correction_when_costs_never_seen_or_stale():
    r = Runner(n=1, socs=(50,), prices=PR, mode="Prijsgestuurd")
    r.hass.set("sensor.nordpool", PR[10], attrs(0.0, PR))
    pp = r.run_price()
    assert not pp["np_fix"] and abs(pp["price"] - PR[10]) < 1e-6
    # costs seen 3 h ago: too old, no correction
    r.hass.set("sensor.zendure_ems_prijsactie", "zero",
               {"nordpool_opslag": ADD, "nordpool_opslag_tijd": (START - timedelta(hours=3)).timestamp()})
    pp = r.run_price()
    assert not pp["np_fix"]


def test_sensor_without_attribute_unchanged():
    r = Runner(n=1, socs=(50,), prices=PR, mode="Prijsgestuurd")
    r.hass.set("sensor.zendure_ems_prijsactie", "zero",
               {"nordpool_opslag": ADD, "nordpool_opslag_tijd": START.timestamp()})
    pp = r.run_price()
    assert not pp["np_fix"] and abs(pp["price"] - PR[10]) < 1e-6
