"""Dashboard references only entities the package creates; the markdown renders."""
import re
from pathlib import Path

import pytest
import yaml

from ha_sim import load_package
from test_package import PRICES, Runner


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def package_entities(pkg):
    ids = set()
    for dom in ("input_select", "input_text", "input_boolean", "input_number", "input_datetime"):
        ids |= {f"{dom}.{k}" for k in pkg[dom]}
    for block in pkg["template"]:
        for dom in ("sensor", "switch", "binary_sensor"):
            ids |= {f"{dom}.{slug(s['name'])}" for s in block.get(dom, [])}
    for r in pkg["rest"]:
        ids |= {f"sensor.{slug(s['name'])}" for s in r["sensor"]}
    ids |= {f"sensor.{slug(s['name'])}" for s in pkg["sensor"]}
    ids |= {f"automation.{slug(a['alias'])}" for a in pkg["automation"]}
    ids |= {f"script.{k}" for k in pkg.get("script", {})}
    ids |= {f"sensor.{k}" for k in pkg.get("utility_meter", {})}
    return ids


def overview_cards(view):
    """Top-level cards of the Overzicht tab (sections layout)."""
    return [c for sec in view.get("sections", []) for c in sec["cards"]] if "sections" in view else view["cards"]


def walk_cards(cards):
    for c in cards:
        yield c
        yield from walk_cards(c.get("cards", []))
        if "card" in c:
            yield from walk_cards([c["card"]])


def walk(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "entity" and isinstance(v, str):
                yield v
            if k == "perform_action" and isinstance(v, str) and v.startswith("script."):
                yield v
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


@pytest.mark.parametrize("n", [3])
def test_dashboard_entities_exist(n):
    pkg = load_package(n)
    dash = yaml.safe_load((Path(__file__).resolve().parents[1] / "out" / "dashboard.yaml").read_text())
    known = package_entities(pkg)
    used = set(walk(dash))
    assert used and used <= known, used - known


def test_price_markdown_renders():
    from datetime import datetime
    from ha_sim import TZ
    r = Runner(mode="Prijsgestuurd", prices=PRICES, socs=(20, 20, 20), start=datetime(2026, 11, 2, 1, 0, 3, tzinfo=TZ),
               settings={"input_boolean.zendure_ems_slim_laden": "on"})
    r.publish()
    pp = r.run_price()
    pkg = r.pkg
    blk = pkg["template"][0]
    for sens in blk["sensor"]:
        attrs = {k: r.hass.render(v, pp=pp) for k, v in (sens.get("attributes") or {}).items()}
        r.hass.set("sensor." + sens["unique_id"], r.hass.render(sens["state"], pp=pp), attrs)
    dash = yaml.safe_load((Path(__file__).resolve().parents[1] / "out" / "dashboard.yaml").read_text())
    mds = [c["content"] for c in walk_cards(overview_cards(dash["views"][0])) if c.get("type") == "markdown"]
    out = "\n".join(r.hass.env().from_string(m).render() for m in mds)
    print(out)
    assert "| Uur | Prijs |" in out and "🔌 laden" in out and "⏸ vasthouden" in out and out.count("\n|") >= 20
    assert "#### Vandaag" in out and '<font color="#2e9e4f">' in out and "◀" in out


@pytest.mark.parametrize("n", [3])
def test_flow_picture_images_embedded(n):
    import base64
    root = Path(__file__).resolve().parents[1] / "out"
    text = (root / "dashboard.yaml").read_text(encoding="utf-8")
    assert "/local/" not in text                      # no files in /config/www needed
    d = yaml.safe_load(text)
    card = overview_cards(d["views"][0])[0]
    imgs = [card["image"]] + [e["elements"][0]["image"] for e in card["elements"] if e["type"] == "conditional"]
    assert len(imgs) == 10                     # house (1 tower) + towers 2 and 3 + 7 flows
    from urllib.parse import unquote
    svgs = []
    for src in imgs:
        assert src.startswith("data:image/svg+xml;charset=utf-8,")
        svg = unquote(src.split(",", 1)[1])
        assert "viewBox='0 0 1000 700'" in svg and "<" not in src and "#" not in src
        svgs.append(svg)
    towers = [s.count("fill='url(#batt)'") for s in svgs[:3]]
    assert towers == [1, 1, 1]                 # the house with tower 1, then only tower 2, only tower 3
    assert len(svgs[1]) < 2000                 # the extra towers are tiny overlays
    assert len(text) < 150_000


def test_netmeting_is_real_grid_including_ev():
    r = Runner()
    from test_package import STATE_SENSORS
    h = r.hass
    h.set("sensor.p1_vermogen", 2800, {"unit_of_measurement": "W"})
    h.set("input_text.zendure_ems_ev_sensor", "sensor.autolader_power")
    h.set("sensor.autolader_power", 2300)
    h.set("input_text.zendure_ems_ev_actief", "input_boolean.ev_laden_actief")
    h.set("input_boolean.ev_laden_actief", "on")
    sens = {s["unique_id"]: s for s in STATE_SENSORS(r.pkg)}
    assert float(h.render(sens["zendure_ems_netmeting"]["state"])) == 2800
    assert float(h.render(sens["zendure_ems_netvermogen"]["state"])) == 500


@pytest.mark.parametrize("n", [3])
def test_settings_groups_collapsible(n):
    root = Path(__file__).resolve().parents[1] / "out"
    d = yaml.safe_load((root / "dashboard.yaml").read_text(encoding="utf-8"))
    view = next(v for v in d["views"] if v.get("path") == "instellingen")
    assert view["cards"][0]["type"] == "markdown"
    groups = view["cards"][1:]
    assert len(groups) == 10 and all(g["type"] == "vertical-stack" for g in groups)
    for g in groups:
        head, cond = g["cards"]
        assert head["type"] == "tile" and head["tap_action"] == {"action": "toggle"}
        assert cond["type"] == "conditional"
        assert cond["conditions"][0]["entity"] == head["entity"] and cond["conditions"][0]["state"] == "on"
    grenzen = next(g for g in groups if g["cards"][0]["name"] == "Grenzen per set")
    assert len(grenzen["cards"][1]["card"]["cards"]) == n


def test_overview_groups_collapsible_and_open_by_default():
    root = Path(__file__).resolve().parents[1] / "out"
    d = yaml.safe_load((root / "dashboard.yaml").read_text(encoding="utf-8"))
    view = d["views"][0]
    cards = overview_cards(view)
    assert view["type"] == "sections" and cards[0]["type"] == "picture-elements"   # energy flow stays visible
    assert view["max_columns"] == 3
    secs = view["sections"]
    name = lambda c: (c["cards"][0].get("entity", "") if c["type"] == "vertical-stack" else c.get("entity", c["type"]))
    col1, col2, col3 = [[name(c) for c in s["cards"]] for s in secs[:3]]
    assert col1 == ["picture-elements", "input_select.zendure_ems_modus"]
    assert col2[:3] == ["input_boolean.zendure_ems_toon_o_laadtoestand", "input_boolean.zendure_ems_toon_o_sets",
                        "input_boolean.zendure_ems_toon_o_planner"]
    planner_md = [c for c in secs[1]["cards"] if c["type"] == "markdown"]
    assert len(planner_md) == 3 and all(c["visibility"][0]["entity"].endswith("toon_o_planner") for c in planner_md)
    assert [c["content"].split("\n")[0] for c in planner_md] == ["{%- set deel = 'kop' -%}", "{%- set deel = 0 -%}",
                                                                 "{%- set deel = 1 -%}"]
    assert secs[1]["cards"][2]["grid_options"] == {"columns": "full"}
    assert col3 == ["input_boolean.zendure_ems_toon_o_soc", "input_boolean.zendure_ems_toon_o_vermogen",
                    "input_boolean.zendure_ems_toon_o_ev", "input_boolean.zendure_ems_toon_o_kalibratie"]
    heads = [c["cards"][0] for c in cards if c["type"] == "vertical-stack" and c["cards"][0].get("type") == "tile"
             and "toon_o_" in c["cards"][0].get("entity", "")]
    heads.append(secs[1]["cards"][2])
    assert sorted(h["name"] for h in heads) == sorted(["Laadtoestand per set", "Sets", "Planner (per kwartier)",
                                                     "Vermogen (laatste 3 uur)", "EV laden", "Laadtoestand (24 uur)",
                                                     "Kalibratie (100 %)"])
    pkg = load_package(3)
    init = next(a for a in pkg["automation"] if a["id"] == "zendure_ems_standaardwaarden")
    txt = yaml.safe_dump(init)
    upd = yaml.safe_dump(next(a for a in pkg["automation"] if a["id"] == "zendure_ems_update"))
    for h in heads:
        assert h["entity"] in txt and h["entity"] in upd


def test_dagplanning_sun_covers_load_is_not_rust():
    from datetime import datetime
    from ha_sim import TZ
    r = Runner(start=datetime(2026, 11, 5, 9, 0, 3, tzinfo=TZ))
    t0 = int(datetime(2026, 11, 5, 9, 0, tzinfo=TZ).timestamp())
    q = lambda i, **kw: dict({"s": t0 + i * 900, "p": 0.25, "x": 0.25, "c": 0, "d": 0, "u": 0, "z": 0, "v": 0.1,
                              "soc": 53, "h": False}, **kw)
    up = [q(0, d=0.1), q(1, d=0.1), q(2, z=0.1), q(3, z=0.11), q(4, z=0.1), q(5, v=0.0), q(6, v=0.0)]
    r.hass.set("sensor.zendure_ems_planning", len(up), {"komende": up})
    r.hass.set("sensor.zendure_ems_prijsactie", "zero", {"verwacht_verbruik_kwh": 1, "verwachte_zon_kwh": 1,
                                                       "gepland_netladen_kwh": 0, "verwacht_tekort_kwh": 0})
    r.hass.set("input_select.zendure_ems_modus", "Prijsgestuurd")
    d = yaml.safe_load((Path(__file__).resolve().parents[1] / "out" / "dashboard.yaml").read_text())
    stats = next(v for v in d["views"] if v.get("path") == "statistieken")
    md = stats["sections"][0]["cards"][1]["content"]
    out = r.hass.env().from_string(md).render()
    assert "☀️ Zon dekt verbruik" in out and "Accu levert" in out
    assert "— Rust" in out                     # nothing at all (no load, no sun) stays "Rust"
    out2 = "\n".join(r.hass.env().from_string(c["content"]).render()
                      for c in walk_cards(overview_cards(d["views"][0])) if c.get("type") == "markdown")
    assert "zon dekt huis" in out2


def test_statistics_sections_collapsible():
    root = Path(__file__).resolve().parents[1] / "out"
    d = yaml.safe_load((root / "dashboard.yaml").read_text(encoding="utf-8"))
    view = next(v for v in d["views"] if v.get("path") == "statistieken")
    pkg = load_package(2)
    upd = yaml.safe_dump(next(a for a in pkg["automation"] if a["id"] == "zendure_ems_update"))
    init = yaml.safe_dump(next(a for a in pkg["automation"] if a["id"] == "zendure_ems_standaardwaarden"))
    for sec in view["sections"]:
        head = sec["cards"][0]
        # header is a tile of the input_boolean that shows/hides the section; tapping it toggles that boolean
        assert head["type"] == "tile" and head["entity"].startswith("input_boolean.zendure_ems_toon_s_")
        ent = head["entity"]
        assert head["tap_action"]["action"] == "toggle" and head["icon_tap_action"]["action"] == "toggle"
        assert all(c["visibility"][0]["entity"] == ent for c in sec["cards"][1:])
        assert ent in upd and ent in init and ent.split(".")[1] in pkg["input_boolean"]
    assert next(s for s in view["sections"] if s["cards"][0]["name"] == "Dagplanning").get("column_span") == 2
    # users coming from 1.9.4 get the statistics sections opened
    branch = next(a for a in next(x for x in pkg["automation"] if x["id"] == "zendure_ems_update")["actions"]
                  if "if" in a and "toon_s_" in yaml.safe_dump(a.get("then", [])))
    assert "'1.9.4'" in branch["if"][0]["value_template"]


def test_offline_set_gauge_and_card_hidden():
    root = Path(__file__).resolve().parents[1] / "out"
    d = yaml.safe_load((root / "dashboard.yaml").read_text(encoding="utf-8"))
    conds = [c for c in walk_cards(overview_cards(d["views"][0])) if c.get("type") == "conditional"
             and c["conditions"][0].get("state_not") == "unavailable"]
    kinds = sorted((c["card"]["type"], c["conditions"][0]["entity"]) for c in conds)
    assert kinds == [("entities", "sensor.zendure_set1_soc"), ("entities", "sensor.zendure_set2_soc"),
                     ("entities", "sensor.zendure_set3_soc"),
                     ("gauge", "sensor.zendure_set1_soc"), ("gauge", "sensor.zendure_set2_soc"),
                     ("gauge", "sensor.zendure_set3_soc")]


def test_one_dashboard_hides_sets_without_ip():
    root = Path(__file__).resolve().parents[1] / "out"
    assert sorted(p.name for p in root.glob("*.yaml")) == ["dashboard.yaml", "zendure_ems.yaml"]
    d = yaml.safe_load((root / "dashboard.yaml").read_text(encoding="utf-8"))
    ok = ["", "unknown", "unavailable"]
    found = {"rows": set(), "cards": set(), "ip": set()}

    def walk(c):
        for x in c.get("cards", []) or []:
            walk(x)
        if isinstance(c.get("card"), dict):
            walk(c["card"])
        for v in c.get("visibility", []) or []:
            if v.get("entity", "").endswith("_ip"):
                assert v["state_not"] == ok
                found["cards"].add(c.get("title"))
        for e in c.get("entities", []) or []:
            if isinstance(e, dict) and e.get("type") == "conditional":
                assert e["conditions"][0]["entity"].endswith("_ip")
                found["rows"].add(e["row"]["entity"])
            elif isinstance(e, dict) and e.get("entity", "").endswith("_ip"):
                found["ip"].add(e["entity"])
            elif isinstance(e, dict) and c.get("type") == "entities":
                assert "zendure_set2_" not in e.get("entity", "") and "zendure_set3_" not in e.get("entity", "")
    for v in d["views"]:
        for c in v.get("cards", []) or []:
            walk(c)
        for s in v.get("sections", []) or []:
            for c in s["cards"]:
                walk(c)
    assert found["ip"] == {"input_text.zendure_set1_ip", "input_text.zendure_set2_ip", "input_text.zendure_set3_ip",
                           "input_text.zendure_ems_p1_ip"}
    assert "sensor.zendure_ems_p1_vermogen" in found["rows"]
    assert {"Grenzen set 2", "Grenzen set 3", "Set 2", "Set 3"} <= found["cards"]
    assert "input_datetime.zendure_set3_laatst_vol" in found["rows"]
    # the flow picture: drawing with 1 tower, 2 and 3 towers on top once that set has an IP
    flow = next(c for v in d["views"] for s in v.get("sections", []) for c in s["cards"]
                if c.get("type") == "picture-elements")
    over = [e for e in flow["elements"] if e.get("type") == "conditional"
            and e["conditions"][0]["entity"].endswith("_ip")]
    assert [e["conditions"][0]["entity"] for e in over] == ["input_text.zendure_set2_ip", "input_text.zendure_set3_ip"]


def test_set_without_ip_polls_home_assistant_itself():
    from test_package import load_package
    pkg = load_package(3)
    from test_package import Runner
    r = Runner(n=3)
    res = pkg["rest"][2]["resource_template"]
    r.hass.set("input_text.zendure_set3_ip", "")
    assert r.hass.render(res) == "http://127.0.0.1:8123/manifest.json"
    r.hass.set("input_text.zendure_set3_ip", " 192.168.1.50 ")
    assert r.hass.render(res) == "http://192.168.1.50/properties/report"


class _T:
    def __init__(self, ruw):
        self.state = "0"
        self.attributes = {} if ruw is None else {"ruw": ruw}


def test_flow_picture_uses_smoothed_sensors():
    from test_package import Runner
    r = Runner()
    blk = next(b for b in r.pkg["template"] if any(s.get("unique_id") == "zendure_ems_weergave_net"
                                                  for s in b.get("sensor", [])))
    assert blk["triggers"][0]["seconds"] == "/5"
    s = {x["unique_id"]: x for x in blk["sensor"]}["zendure_ems_weergave_net"]
    assert "state_class" not in s
    h = r.hass

    def step(src, ruw):
        h.set("sensor.zendure_ems_netmeting", src)
        this = _T(ruw)
        return int(h.render(s["state"], this=this)), float(h.render(s["attributes"]["ruw"], this=this))

    # a spike of 1000 W after 0: only about a third shows, then it fades away
    v, ruw = step(1000, 0)
    assert 300 <= v <= 400
    v2, ruw = step(0, ruw)
    assert v2 < v
    # noise around zero shows as 0 (no flow line)
    assert step(30, 0)[0] == 0
    # a steady 100 W climbs out of the dead band (not stuck at 0)
    ruw = 0
    for _ in range(6):
        v, ruw = step(100, ruw)
    assert v >= 90
    # first run: starts at the measured value
    assert step(-500, None)[0] == -500
    import os
    dash = open(os.path.join(os.path.dirname(__file__), "..", "out", "dashboard.yaml")).read()
    i = dash.index("title: Energiestroom")
    part = dash[i:i + dash[i:].index("gemiddelde_soc")]
    assert "zendure_ems_netmeting" not in part and "zendure_ems_weergave_net" in part
