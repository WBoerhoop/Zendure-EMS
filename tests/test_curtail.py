"""Solar curtailment at negative prices."""
from datetime import datetime

from ha_sim import TZ
from test_package import Runner

T = datetime(2026, 11, 2, 13, 0, 3, tzinfo=TZ)


def auto(pkg):
    return next(a for a in pkg["automation"] if a["id"] == "zendure_ems_afschalen")


def setup(socs=(100, 100, 100), price=-0.05, mode="Bij volle accu", cur=False):
    r = Runner(socs=socs, start=T)
    r.publish()
    r.hass.set("sensor.zendure_ems_terugleverprijs", price)
    r.hass.set("input_select.zendure_ems_afschalen", mode)
    r.hass.set("input_boolean.zendure_ems_afgeschaald", "on" if cur else "off")
    r.hass.set("input_text.zendure_ems_export_entiteit", "number.goodwe_net_exportlimiet")
    r.hass.set("input_text.zendure_ems_export_schakelaar", "input_boolean.goodwe_net_limiter_inschakelen")
    r.hass.set("input_text.zendure_ems_extra_entiteit", "number.solarflow_800_output_limit")
    return r


def want(r):
    return r.hass.render(auto(r.pkg)["actions"][0]["variables"]["want"])


def test_full_batteries_negative_price_curtails():
    assert want(setup()) is True


def test_not_full_keeps_panels_running():
    assert want(setup(socs=(100, 97, 100))) is False


def test_direct_mode_ignores_battery():
    assert want(setup(socs=(40, 40, 40), mode="Direct")) is True


def test_positive_price_or_off_restores():
    assert want(setup(price=0.02, cur=True)) is False
    assert want(setup(mode="Uit", cur=True)) is False
    assert want(setup(price="unavailable")) is False


def test_hysteresis_stays_curtailed_until_5_points_below_max():
    assert want(setup(socs=(97, 100, 100), cur=True)) is True
    assert want(setup(socs=(94, 100, 100), cur=True)) is False


def test_threshold_and_disallowed_set():
    r = setup(price=0.03)
    r.hass.set("input_number.zendure_ems_afschaal_drempel", 0.05)
    assert want(r) is True
    r = setup(socs=(100, 60, 100))
    r.hass.set("input_boolean.zendure_set2_laden", "off")  # set 2 may not charge: does not count
    assert want(r) is True


def ctx_of(r, trigger_id="1"):
    """Render the variables block in order, as Home Assistant does."""
    v = auto(r.pkg)["actions"][0]["variables"]
    ctx = {"trigger": {"id": trigger_id}}
    for k, tpl in v.items():
        ctx[k] = r.hass.render(tpl, **ctx)
    return ctx


def ramp_values(r, ctx):
    """Values the repeat loop writes to the export limit, in order."""
    a = auto(r.pkg)
    ent_if = a["actions"][5]
    rep = ent_if["then"][0]["repeat"]
    n = int(r.hass.render(rep["count"], **ctx))
    out = []
    for i in range(1, n + 1):
        out.append(float(r.hass.render(rep["sequence"][0]["data"]["value"], repeat={"index": i}, **ctx)))
    return out


def test_actions_render_with_user_entities():
    r = setup()
    r.hass.set("number.goodwe_net_exportlimiet", 4000)
    r.hass.set("number.solarflow_800_output_limit", 800)
    a = auto(r.pkg)
    ctx = ctx_of(r)
    assert ctx["want"] is True and ctx["cur"] is False
    assert ctx["v1"] == 0 and ctx["v2"] == 0
    cond = a["actions"][1]["value_template"]
    assert r.hass.render(cond, **ctx) is True
    sw_if, ent2_if, ent_if = a["actions"][3], a["actions"][4], a["actions"][5]
    assert r.hass.render(sw_if["if"][0]["value_template"], **ctx) is True
    assert r.hass.render(sw_if["then"][0]["action"], **ctx) == "homeassistant.turn_on"
    assert r.hass.render(ent2_if["then"][0]["target"]["entity_id"], **ctx) == "number.solarflow_800_output_limit"
    assert r.hass.render(ent_if["if"][0]["value_template"], **ctx) is True
    step = ent_if["then"][0]["repeat"]["sequence"][0]
    assert r.hass.render(step["action"], **ctx) == "number.set_value"
    assert r.hass.render(step["target"]["entity_id"], **ctx) == "number.goodwe_net_exportlimiet"
    # 4000 -> 0 in steps of 500
    assert ramp_values(r, ctx) == [3500, 3000, 2500, 2000, 1500, 1000, 500, 0]
    # nothing to do when the state is already right
    r.hass.set("input_boolean.zendure_ems_afgeschaald", "on")
    r.hass.set("number.goodwe_net_exportlimiet", 0)
    r.hass.set("number.solarflow_800_output_limit", 0)
    assert r.hass.render(cond, **ctx_of(r)) is False


def test_ramp_back_up_and_single_step():
    r = setup(price=0.10, cur=True)
    r.hass.set("input_number.zendure_ems_export_normaal", 4000)
    r.hass.set("number.goodwe_net_exportlimiet", 0)
    ctx = ctx_of(r)
    assert ctx["want"] is False and ctx["v1"] == 4000
    vals = ramp_values(r, ctx)
    assert vals[0] == 500 and vals[-1] == 4000 and len(vals) == 8
    r.hass.set("input_number.zendure_ems_afschaal_stap", 0)
    assert ramp_values(r, ctx_of(r)) == [4000]
    r.hass.set("input_number.zendure_ems_afschaal_stap", 1500)
    assert ramp_values(r, ctx_of(r)) == [1500, 3000, 4000]


def test_watchdog_reapplies_when_limit_changed_by_other_automation():
    r = setup(cur=True)
    r.hass.set("number.goodwe_net_exportlimiet", 4000)   # morning automation set it back
    r.hass.set("number.solarflow_800_output_limit", 0)
    a = auto(r.pkg)
    ctx = ctx_of(r)
    assert ctx["want"] is True and ctx["cur"] is True and ctx["bewaken"] is True
    assert r.hass.render(a["actions"][1]["value_template"], **ctx) is True
    assert ramp_values(r, ctx)[-1] == 0
    # inverter offline at night: no watchdog action
    r.hass.set("number.goodwe_net_exportlimiet", "unavailable")
    ctx = ctx_of(r)
    assert ctx["bewaken"] is False and r.hass.render(a["actions"][1]["value_template"], **ctx) is False


def test_planner_holds_full_battery_at_negative_price():
    from test_planner import runner
    prices = [0.20] * 13 + [-0.03] * 3 + [0.30] * 8
    r = runner(T, socs=(100, 100, 100), prices=prices)
    pp = r.run_price()
    assert pp["action"] == "hold" and "accu vol" in pp["reason"]
    r = runner(T, socs=(70, 70, 70), prices=prices)
    assert r.run_price()["action"] == "grid_charge"
