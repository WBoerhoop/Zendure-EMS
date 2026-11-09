"""Savings: cost of charging and value of discharging, weighted with the price of that moment."""
from test_package import Runner


class _S:
    def __init__(self, state):
        self.state = state


def block(pkg):
    return next(b for b in pkg["template"] if any(s.get("unique_id") == "zendure_ems_kosten_laden"
                                                 for s in b.get("sensor", [])))


def step(r, trig_id, frm, to, this_cost, this_value):
    blk = block(r.pkg)
    trig = {"id": trig_id, "from_state": _S(str(frm)), "to_state": _S(str(to))}
    ctx = {"trigger": trig}
    for k, tpl in blk["variables"].items():
        ctx[k] = r.hass.render(tpl, **ctx)
    cost = float(r.hass.render(blk["sensor"][0]["state"], this=_S(str(this_cost)), **ctx))
    value = float(r.hass.render(blk["sensor"][1]["state"], this=_S(str(this_value)), **ctx))
    return cost, value, ctx


def runner(imp=0.30, exp=0.10, net=0):
    r = Runner(n=2, socs=(60, 60))
    h = r.hass
    h.set("sensor.zendure_ems_stroomprijs", imp)
    h.set("sensor.zendure_ems_terugleverprijs", exp)
    h.set("sensor.zendure_ems_netmeting", net)
    return r


def test_grid_charging_costs_import_price():
    r = runner(imp=0.20, exp=0.08, net=2000)
    cost, value, ctx = step(r, "laden", 10.0, 11.0, 1.0, 5.0)
    assert abs(cost - 1.20) < 1e-9 and value == 5.0 and ctx["prijs"] == 0.20


def test_solar_charging_costs_feed_in_price():
    r = runner(imp=0.20, exp=0.08, net=-5)
    cost, value, _ = step(r, "laden", 10.0, 10.5, 1.0, 5.0)
    assert abs(cost - 1.04) < 1e-9


def test_discharge_to_house_is_worth_import_price_and_selling_feed_in():
    r = runner(imp=0.40, exp=0.12, net=0)
    _, value, _ = step(r, "ontladen", 3.0, 4.0, 1.0, 5.0)
    assert abs(value - 5.40) < 1e-9
    r = runner(imp=0.40, exp=0.12, net=-1500)
    _, value, _ = step(r, "ontladen", 3.0, 4.0, 1.0, 5.0)
    assert abs(value - 5.12) < 1e-9


def test_negative_price_charging_earns_and_counter_jumps_are_ignored():
    r = runner(imp=-0.05, exp=-0.10, net=2000)
    cost, _, _ = step(r, "laden", 10.0, 12.0, 1.0, 0.0)
    assert abs(cost - 0.90) < 1e-9
    cost, _, _ = step(r, "laden", 12.0, 500.0, 1.0, 0.0)     # counter reset / jump: ignored
    assert cost == 1.0


def test_totals_and_month_price():
    r = runner()
    h = r.hass
    h.set("sensor.zendure_ems_waarde_ontladen", 12.5)
    h.set("sensor.zendure_ems_kosten_laden", 8.2)
    h.set("input_number.zendure_ems_besparing_start", 4.29)
    h.set("sensor.zendure_ems_kosten_laden_maand", 3.0)
    h.set("sensor.zendure_ems_geladen_maand", 10.0)
    blk = next(b for b in r.pkg["template"] if any(s.get("unique_id") == "zendure_ems_besparing_totaal"
                                                  for s in b.get("sensor", [])))
    s = {x["unique_id"]: x for x in blk["sensor"]}
    assert float(h.render(s["zendure_ems_besparing_totaal"]["state"])) == 8.59
    assert float(h.render(s["zendure_ems_gem_laadprijs"]["state"])) == 0.3


def test_chart_counter_ignores_start_value_and_update_resets_it():
    r = runner()
    h = r.hass
    h.set("sensor.zendure_ems_waarde_ontladen", 12.5)
    h.set("sensor.zendure_ems_kosten_laden", 8.2)
    blk = next(b for b in r.pkg["template"] if any(s.get("unique_id") == "zendure_ems_besparing_teller"
                                                  for s in b.get("sensor", [])))
    s = {x["unique_id"]: x for x in blk["sensor"]}
    assert s["zendure_ems_besparing_teller"]["state_class"] == "total"
    assert "state_class" not in s["zendure_ems_besparing_totaal"]
    for start in (-1000, 4.29):
        h.set("input_number.zendure_ems_besparing_start", start)
        assert float(h.render(s["zendure_ems_besparing_teller"]["state"])) == 4.3
    import yaml
    upd = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_update")
    br = next(a for a in upd["actions"] if "if" in a and "besparing_start" in yaml.safe_dump(a.get("then", [])))
    h.set("input_text.zendure_ems_versie", "1.9.1")
    assert h.render(br["if"][0]["value_template"]) is True
    h.set("input_text.zendure_ems_versie", "1.9.9")
    assert h.render(br["if"][0]["value_template"]) is False
