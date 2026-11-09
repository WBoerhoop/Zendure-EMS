"""Profiles: preset and own settings, applied by an automation; sensor shows which one is active."""
import json

from test_package import Runner, STATE_SENSORS


def auto(pkg):
    return next(a for a in pkg["automation"] if a["id"] == "zendure_ems_profiel")


def vars_for(r, naam):
    v = auto(r.pkg)["actions"][0]["variables"]
    ctx = {"trigger": {"to_state": {"state": naam}}}
    for k, tpl in v.items():
        ctx[k] = r.hass.render(tpl, **ctx)
    return ctx


def apply(r, naam):
    """Emulate the automation's actions on the simulated states."""
    ctx = vars_for(r, naam)
    prof = ctx["prof"]
    for it in ctx["getallen"]:
        r.hass.set(it["e"], float(it["v"]))
    for it in ctx["schakelaars"]:
        r.hass.set(it["e"], "on" if it["v"] == 1 else "off")
    if "af" in prof:
        r.hass.set("input_select.zendure_ems_afschalen", prof["af"])
    if "m" in prof:
        r.hass.set("input_select.zendure_ems_modus", prof["m"])
    return ctx


def active(r):
    s = next(x for x in STATE_SENSORS(r.pkg) if x["unique_id"] == "zendure_ems_actief_profiel")
    return r.hass.render(s["state"])


def base_runner():
    r = Runner()
    h = r.hass
    h.set("input_select.zendure_ems_afschalen", "Uit")
    h.set("input_text.zendure_ems_mijn_profiel_1", "")
    h.set("input_text.zendure_ems_mijn_profiel_2", "")
    return r


def test_dynamisch_nom_sets_everything():
    r = base_runner()
    r.hass.set("input_boolean.zendure_ems_slim_ontladen", "on")
    r.hass.set("input_number.zendure_ems_verkoopprijs", 0.4)
    ctx = apply(r, "Dynamisch NOM")
    assert ctx["prof"]["m"] == "Prijsgestuurd"
    h = r.hass
    assert h.states["input_select.zendure_ems_modus"].state == "Prijsgestuurd"
    assert h.states["input_boolean.zendure_ems_slim_laden"].state == "on"
    assert h.states["input_boolean.zendure_ems_slim_ontladen"].state == "off"
    assert float(h.states["input_number.zendure_ems_verkoopprijs"].state) == 1.0
    assert active(r) == "Dynamisch NOM"


def test_duur_and_handelen():
    r = base_runner()
    apply(r, "Dynamisch NOM (Duur)")
    assert r.hass.states["input_boolean.zendure_ems_slim_ontladen"].state == "on"
    assert active(r) == "Dynamisch NOM (Duur)"
    r.hass.set("input_number.zendure_ems_handel_prijs", 0.38)
    apply(r, "Dynamisch Handelen")
    assert float(r.hass.states["input_number.zendure_ems_verkoopprijs"].state) == 0.38
    assert active(r) == "Dynamisch Handelen"


def test_manual_change_shows_aangepast():
    r = base_runner()
    apply(r, "Dynamisch NOM")
    r.hass.set("input_number.zendure_ems_laadprijs", 0.05)
    assert active(r) == "Aangepast"


def test_own_profile_save_and_restore():
    r = base_runner()
    apply(r, "Dynamisch NOM")
    r.hass.set("input_number.zendure_ems_min_spread", 0.02)
    r.hass.set("input_select.zendure_ems_afschalen", "Bij volle accu")
    script = r.pkg["script"]["zendure_ems_profiel_opslaan"]["sequence"]
    nu = r.hass.render(script[0]["variables"]["nu"])
    val = r.hass.render(script[1]["data"]["value"], nu=nu)
    saved = val if isinstance(val, str) else json.dumps(val)
    assert len(saved) < 255
    r.hass.set("input_text.zendure_ems_mijn_profiel_1", saved)
    assert active(r) == "Mijn profiel 1"
    # change things, then restore profile 1
    apply(r, "Stand-by")
    assert r.hass.states["input_select.zendure_ems_modus"].state == "Uit (stand-by)"
    apply(r, "Mijn profiel 1")
    assert float(r.hass.states["input_number.zendure_ems_min_spread"].state) == 0.02
    assert r.hass.states["input_select.zendure_ems_afschalen"].state == "Bij volle accu"
    assert r.hass.states["input_select.zendure_ems_modus"].state == "Prijsgestuurd"
    assert active(r) == "Mijn profiel 1"


def test_empty_own_profile_does_nothing():
    r = base_runner()
    ctx = vars_for(r, "Mijn profiel 2")
    assert ctx["prof"] == {} and ctx["getallen"] == [] and ctx["schakelaars"] == []
    a = auto(r.pkg)
    assert r.hass.render(a["actions"][1]["if"][0]["value_template"], **ctx) is True


def test_handelen_plus_nom():
    r = base_runner()
    r.hass.set("input_number.zendure_ems_handel_prijs", 0.38)
    r.hass.set("input_boolean.zendure_ems_slim_ontladen", "on")
    apply(r, "Dynamisch Handelen + NOM")
    h = r.hass
    assert h.states["input_select.zendure_ems_modus"].state == "Prijsgestuurd"
    assert h.states["input_boolean.zendure_ems_slim_laden"].state == "on"
    assert h.states["input_boolean.zendure_ems_slim_ontladen"].state == "off"   # NOM the rest of the time
    assert float(h.states["input_number.zendure_ems_verkoopprijs"].state) == 0.38
    assert active(r) == "Dynamisch Handelen + NOM"
    apply(r, "Dynamisch Handelen")
    assert active(r) == "Dynamisch Handelen"
