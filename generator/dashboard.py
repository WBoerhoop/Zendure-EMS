"""Lovelace dashboard (built-in cards only) for the Zendure EMS package."""

PRICE_TABLE = r"""{%- set up = state_attr('sensor.zendure_ems_planning', 'komende') or [] -%}
{%- set pa = 'sensor.zendure_ems_prijsactie' -%}
{%- if up | count == 0 -%}
<ha-icon icon="mdi:alert-circle-outline"></ha-icon> Geen prijsdata. Vul bij **Instellingen** een prijssensor in (Nordpool, Zonneplan of ENTSO-e).
{%- else -%}
{%- macro tijden(qs, eerst=false) -%}
{%- set n = namespace(o=[], a=0, e=0) -%}
{%- for q in qs | sort -%}{%- if q != n.e -%}{%- if n.a -%}{%- set n.o = n.o + [[n.a, n.e]] -%}{%- endif -%}{%- set n.a = q -%}{%- endif -%}{%- set n.e = q + 900 -%}{%- endfor -%}
{%- if n.a -%}{%- set n.o = n.o + [[n.a, n.e]] -%}{%- endif -%}
{%- for r in (n.o[:1] if eerst else n.o) -%}{{ ', ' if not loop.first else '' }}{{ ('morgen ' if eerst and (r[0] | timestamp_custom('%d')) != now().strftime('%d') else '') ~ r[0] | timestamp_custom('%H:%M') ~ '–' ~ r[1] | timestamp_custom('%H:%M') }}{%- endfor -%}
{%- endmacro -%}
{%- set act = states(pa) -%}
{%- set icons = {'grid_charge': 'mdi:transmission-tower-import', 'hold': 'mdi:pause-circle-outline', 'sell': 'mdi:cash-plus', 'zero': 'mdi:scale-balance'} -%}
{%- set hs = namespace(l=[]) -%}
{%- for s in up -%}
  {%- set k = (s.s // 3600) * 3600 -%}
  {%- if k not in hs.l -%}{%- set hs.l = hs.l + [k] -%}{%- endif -%}
{%- endfor -%}
{%- set hp = namespace(l=[]) -%}
{%- for k in hs.l[:36] -%}
  {%- set g = up | selectattr('s', 'ge', k) | selectattr('s', 'lt', k + 3600) | list -%}
  {%- set hp.l = hp.l + [{'k': k, 'p': (g | map(attribute='p') | sum) / (g | count)}] -%}
{%- endfor -%}
{%- set pmin = hp.l | map(attribute='p') | min -%}
{%- set pmax = hp.l | map(attribute='p') | max -%}
{%- set kmin = (hp.l | sort(attribute='p') | first).k -%}
{%- set kmax = (hp.l | sort(attribute='p') | last).k -%}
{%- set nowh = (as_timestamp(now()) // 3600) * 3600 -%}
{%- set today = now().strftime('%d') -%}
{%- set deel = deel | default('alles') -%}
{#KOP#}{%- if deel in ['kop', 'alles'] %}
### <ha-icon icon="{{ icons.get(act, 'mdi:scale-balance') }}"></ha-icon> {{ state_attr(pa, 'omschrijving') }}
{%- if state_attr(pa, 'reden') != state_attr(pa, 'omschrijving') %}
<sub>{{ state_attr(pa, 'reden') }}</sub>
{%- endif %}

<ha-icon icon="mdi:transmission-tower-import"></ha-icon> **{{ state_attr(pa, 'gepland_netladen_kwh') }} kWh** netladen &nbsp;·&nbsp;
<ha-icon icon="mdi:white-balance-sunny"></ha-icon> {{ state_attr(pa, 'verwachte_zon_kwh') }} kWh zon &nbsp;·&nbsp;
<ha-icon icon="mdi:home-lightning-bolt-outline"></ha-icon> {{ state_attr(pa, 'verwacht_verbruik_kwh') }} kWh verbruik &nbsp;·&nbsp;
<ha-icon icon="mdi:transmission-tower"></ha-icon> {{ state_attr(pa, 'verwacht_tekort_kwh') }} kWh van het net
{%- if state_attr(pa, 'verkopen_gepland') == true %} &nbsp;·&nbsp;
<ha-icon icon="mdi:cash-plus"></ha-icon> {{ state_attr(pa, 'gepland_verkopen_kwh') }} kWh verkopen (≈ € {{ state_attr(pa, 'verwachte_handelswinst') }} winst)
{%- endif %}
{%- set q_sv = up | selectattr('sv', 'number') | selectattr('sv', 'gt', 0.01) | map(attribute='s') | list -%}
{%- set q_c = up | selectattr('c', 'gt', 0.01) | map(attribute='s') | list -%}
{%- if q_sv or q_c %}
<br><ha-icon icon="mdi:clock-start"></ha-icon> **Volgende:**
{%- if q_sv %} <font color="#8e44ad">💶 verkopen {{ tijden(q_sv, true) }}</font>{% endif %}
{%- if q_sv and q_c %} &nbsp;·&nbsp;{% endif %}
{%- if q_c %} <font color="#1e88e5">🔌 laden {{ tijden(q_c, true) }}</font>{% endif %}
{%- endif %}
<br><sub>tot {{ (up[-1].s + 900) | timestamp_custom('%d-%m %H:%M') }} · per kwartier gepland, hier per uur · <font color="#2e9e4f">■</font> goedkoop <font color="#e0a106">■</font> gemiddeld <font color="#d64541">■</font> duur</sub>
{%- endif %}
{#/KOP#}{% set days = namespace(l=[]) -%}
{%- for h in hp.l -%}{%- set dd = h.k | timestamp_custom('%d-%m') -%}{%- if dd not in days.l -%}{%- set days.l = days.l + [dd] -%}{%- endif -%}{%- endfor -%}
{%- set sel = days.l if deel == 'alles' else (days.l[deel:deel + 1] if deel is number else []) -%}
{%- if deel is number and sel | count == 0 %}
#### Morgen
<sub>De prijzen voor morgen komen meestal rond 13:00.</sub>
{%- endif %}
{%- for day in sel %}

#### {{ 'Vandaag' if day[:2] == today else 'Morgen' }} <sub>{{ day }}</sub>
| Uur | Prijs | | Plan (kWh) | SOC |
|:--|--:|:--|:--|--:|
{% for h in hp.l if (h.k | timestamp_custom('%d-%m')) == day -%}
{%- set k = h.k -%}
{%- set g = up | selectattr('s', 'ge', k) | selectattr('s', 'lt', k + 3600) | list -%}
{%- set p = h.p -%}
{%- set f = ((p - pmin) / (pmax - pmin)) if pmax > pmin else 0.5 -%}
{%- set col = '#2e9e4f' if f < 0.34 else ('#e0a106' if f < 0.67 else '#d64541') -%}
{%- set bar = (f * 4) | round(0) | int + 1 -%}
{%- set c = g | map(attribute='c') | sum -%}
{%- set dd = g | map(attribute='d') | sum -%}
{%- set u = g | map(attribute='u') | sum -%}
{%- set z = g | map(attribute='z') | sum -%}
{%- set v = g | map(attribute='v') | sum -%}
{%- set hold = g | selectattr('h') | list | count > 0 -%}
{%- set plan = namespace(t=[]) -%}
{%- set qc = g | selectattr('c', 'gt', 0.01) | map(attribute='s') | list -%}
{%- set qv = g | selectattr('sv', 'number') | selectattr('sv', 'gt', 0.01) | map(attribute='s') | list -%}
{%- set qh = g | selectattr('h') | map(attribute='s') | list -%}
{%- if c > 0.01 -%}{%- set plan.t = plan.t + ['<font color="#1e88e5">🔌 laden ' ~ ('%.1f' | format(c)) ~ (' <sub>' ~ tijden(qc) ~ '</sub>' if qc | count < 4 else '') ~ '</font>'] -%}{%- endif -%}
{%- set sv = g | map(attribute='sv') | select('number') | sum -%}
{%- if sv > 0.01 -%}{%- set plan.t = plan.t + ['<font color="#8e44ad">💶 verkopen ' ~ ('%.1f' | format(sv)) ~ (' <sub>' ~ tijden(qv) ~ '</sub>' if qv | count < 4 else '') ~ '</font>'] -%}{%- endif -%}
{%- if hold -%}{%- set plan.t = plan.t + ['⏸ vasthouden' ~ (' <sub>' ~ tijden(qh) ~ '</sub>' if qh | count < 4 else '')] -%}{%- endif -%}
{%- if dd > 0.02 and not hold -%}{%- set plan.t = plan.t + ['<font color="#2e9e4f">🔋 accu ' ~ ('%.1f' | format(dd)) ~ '</font>'] -%}{%- endif -%}
{%- if z > v + 0.05 -%}{%- set plan.t = plan.t + ['☀️ zon over ' ~ ('%.1f' | format(z - v))] -%}{%- endif -%}
{%- if u > 0.02 and not hold and c <= 0.01 -%}{%- set plan.t = plan.t + ['🏠 net ' ~ ('%.1f' | format(u))] -%}{%- endif -%}
{%- if plan.t | count == 0 and z > 0.01 and z >= v - 0.05 -%}{%- set plan.t = ['☀️ zon dekt huis'] -%}{%- endif -%}
{%- if plan.t | count == 0 -%}{%- set plan.t = ['<font color="#9e9e9e">— rust</font>'] -%}{%- endif -%}
{%- set soc = g[-1].soc -%}
{%- set bi = 'mdi:battery-outline' if soc < 5 else ('mdi:battery' if soc >= 95 else 'mdi:battery-' ~ ((soc / 10) | round(0) | int * 10)) -%}
{%- set mark = ' ⬇' if k == kmin else (' ⬆' if k == kmax else '') -%}
{%- set b1 = '**' if k == nowh else '' -%}
| {{ b1 }}{{ k | timestamp_custom('%H:%M') }}{{ b1 }}{{ ' ◀' if k == nowh else '' }} | {{ b1 }}<font color="{{ col }}">{{ '%.3f' | format(p) }}</font>{{ b1 }}{{ mark }} | <font color="{{ col }}">{{ '▰' * bar }}</font> | {{ plan.t | join(' · ') }} | <ha-icon icon="{{ bi }}"></ha-icon> {{ soc }}% |
{% endfor -%}
{%- endfor -%}
{%- endif -%}"""


def svg_uri(svg: str) -> str:
    """SVG as a small data URI: minified and percent-encoded instead of base64 (about a third smaller)."""
    import re
    from urllib.parse import quote
    s = re.sub(r">\s+<", "><", svg.strip())
    s = re.sub(r"\s{2,}", " ", s).replace('"', "'")
    return "data:image/svg+xml;charset=utf-8," + quote(s, safe=" '/:=;,.-_()!*~+?@$&")


def flow_picture(n: int) -> str:
    """picture-elements card: background house + animated flows (conditional) + live values."""
    import base64
    from www import LABELS, files

    svgs = files((1,))

    def src(name):
        """The SVG embedded as a data URI: no files to copy to /config/www."""
        return svg_uri(svgs[name])

    def pos(x, y):
        return f"left: {x / 10:.1f}%\n          top: {y / 7:.1f}%"

    label_style = ("color: white\n          font-weight: 600\n          font-size: clamp(11px, 2.3vw, 22px)\n"
                   "          text-shadow: 0 1px 3px black\n          white-space: nowrap")
    out = [f"""      - type: picture-elements
        title: Energiestroom
        image: "{src("huis_1sets.svg")}"
        elements:
"""]
    # one dashboard for 1 to 3 sets: the drawing with 2 or 3 battery towers lies on top once that set has an IP
    for k in range(2, n + 1):
        out.append(f"""          - type: conditional
            conditions:
              - condition: state
                entity: input_text.zendure_set{k}_ip
                state_not:
                  - ""
                  - unknown
                  - unavailable
            elements:
              - type: image
                image: "{src(f"toren_{k}.svg")}"
                tap_action:
                  action: none
                hold_action:
                  action: none
                style:
                  left: 50%
                  top: 50%
                  width: 100%
                  pointer-events: none
""")

    def flow(img, ent, cond):
        out.append(f"""          - type: conditional
            conditions:
              - condition: numeric_state
                entity: {ent}
                {cond}
            elements:
              - type: image
                image: "{src(img)}"
                tap_action:
                  action: none
                hold_action:
                  action: none
                style:
                  left: 50%
                  top: 50%
                  width: 100%
                  pointer-events: none
""")
    flow("flow_net_afname.svg", "sensor.zendure_ems_weergave_net", "above: 0")
    flow("flow_net_teruglevering.svg", "sensor.zendure_ems_weergave_net", "below: 0")
    flow("flow_zon.svg", "sensor.zendure_ems_weergave_zon", "above: 0")
    flow("flow_huis.svg", "sensor.zendure_ems_weergave_huis", "above: 0")
    flow("flow_accu_laden.svg", "sensor.zendure_ems_weergave_accu", "above: 0")
    flow("flow_accu_ontladen.svg", "sensor.zendure_ems_weergave_accu", "below: 0")
    flow("flow_ev.svg", "sensor.zendure_ems_weergave_ev", "above: 0")
    ents = {k: f"sensor.zendure_ems_weergave_{k}" for k in ("net", "zon", "huis", "accu", "ev")}
    for k, (x, y, _) in LABELS.items():
        out.append(f"""          - type: state-label
            entity: {ents[k]}
            style:
              {pos(x, y).replace(chr(10) + '          ', chr(10) + '              ')}
              {label_style.replace(chr(10) + '          ', chr(10) + '              ')}
""")
    out.append(f"""          - type: state-label
            entity: sensor.zendure_ems_gemiddelde_soc
            style:
              {pos(290, 442).replace(chr(10) + '          ', chr(10) + '              ')}
              color: "#51cf66"
              font-weight: 600
              font-size: clamp(10px, 1.8vw, 17px)
              text-shadow: 0 1px 3px black
""")
    return "".join(out)


def statistics_view() -> str:
    """Tab Statistieken (ApexCharts), kept as plain YAML next to this file."""
    import yaml
    from pathlib import Path
    view = yaml.safe_load((Path(__file__).with_name("statistieken.yaml")).read_text(encoding="utf-8"))
    tile = lambda e, n, icon: {"type": "tile", "entity": e, "name": n, "icon": icon, "vertical": True}
    savings = {"type": "grid", "cards": [
        {"type": "heading", "heading": "Besparing door de accu", "icon": "mdi:piggy-bank"},
        tile("sensor.zendure_ems_besparing_vandaag", "Vandaag", "mdi:piggy-bank"),
        tile("sensor.zendure_ems_besparing_maand", "Deze maand", "mdi:piggy-bank"),
        tile("sensor.zendure_ems_besparing_totaal", "Totaal", "mdi:piggy-bank"),
        tile("sensor.zendure_ems_gemiddelde_laadprijs", "Gem. laadprijs (maand)", "mdi:cash-clock"),
        tile("sensor.zendure_ems_gemiddelde_ontlaadwaarde", "Gem. ontlaadwaarde (maand)", "mdi:cash-check"),
        {"type": "statistics-graph", "title": "Besparing per dag (EUR)", "entities": ["sensor.zendure_ems_besparing_teller"],
         "stat_types": ["change"], "period": "day", "chart_type": "bar", "days_to_show": 14, "hide_legend": True},
        {"type": "statistics-graph", "title": "Opgebouwde besparing sinds installatie (EUR)", "entities": ["sensor.zendure_ems_besparing_teller"],
         "stat_types": ["state"], "period": "hour", "chart_type": "line", "days_to_show": 30, "hide_legend": True},
        {"type": "entities", "entities": [
            {"entity": "sensor.zendure_ems_kosten_laden", "name": "Kosten laden (totaal)"},
            {"entity": "sensor.zendure_ems_waarde_ontladen", "name": "Waarde ontladen (totaal)"},
            {"entity": "input_number.zendure_ems_besparing_start",
             "name": "Startwaarde (bv. besparing uit batterij planner)"}]},
        {"type": "markdown", "content":
            "Waarde van wat de accu leverde min wat het laden kostte, gewogen met de prijs van dat moment. "
            "Laden uit het net telt tegen de afnameprijs, laden met zonne-overschot tegen de terugleverprijs; "
            "leveren aan het huis tegen de afnameprijs, verkopen aan het net tegen de terugleverprijs. "
            "Tot en met 2026 (salderen) zijn die gelijk. Alle sets samen; de teller start bij installatie van 1.9.2."},
    ]}
    view["sections"] = view["sections"][:1] + [savings] + view["sections"][1:]
    text = yaml.safe_dump([view], allow_unicode=True, sort_keys=False, width=4096)
    return "".join("  " + line + "\n" for line in text.splitlines())


# Collapsible groups on the Instellingen tab: (title prefix, helper key, icon)
SETTING_GROUPS = [
    ("Aansluiting", "aansluiting", "mdi:lan-connect"),
    ("Planner", "planner", "mdi:chart-timeline-variant"),
    ("Teruglevering", "teruglevering", "mdi:transmission-tower-export"),
    ("Zonnepanelen afschalen", "afschalen", "mdi:solar-power-variant"),
    ("EV laden", "ev", "mdi:car-electric"),
    ("Zonnecorrectie", "zonnecorrectie", "mdi:white-balance-sunny"),
    ("Prijssturing", "prijssturing", "mdi:cash-multiple"),
    ("Grenzen set", "grenzen", "mdi:battery-heart-variant"),
    ("Regeling", "regeling", "mdi:tune"),
    ("Kalibratie", "kalibratie", "mdi:battery-sync"),
]
GROUP_TITLES = {"grenzen": "Grenzen per set"}


class _Lit(str):
    pass


def _dump(data) -> str:
    import yaml

    class D(yaml.SafeDumper):
        pass

    def lit(dumper, s):
        style = "|" if "\n" in s else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", s, style=style)

    D.add_representer(str, lit)
    return yaml.dump(data, Dumper=D, allow_unicode=True, sort_keys=False, width=4096)


# Collapsible groups on the Overzicht tab (open by default)
OVERVIEW_GROUPS = [
    ("__gauges", "o_laadtoestand", "mdi:gauge", "Laadtoestand per set"),
    ("Vermogen", "o_vermogen", "mdi:chart-line", None),
    ("Planner", "o_planner", "mdi:calendar-clock", None),
    ("EV laden", "o_ev", "mdi:car-electric", None),
    ("Kalibratie", "o_kalibratie", "mdi:battery-sync", "Kalibratie (100 %)"),
    ("Set ", "o_sets", "mdi:home-battery", "Sets"),
    ("Laadtoestand (24", "o_soc", "mdi:chart-bell-curve", None),
]
# Collapsible sections on the Statistieken tab (open by default): heading -> helper key
STAT_GROUPS = {"Dagplanning": "s_dagplanning", "Besparing door de accu": "s_besparing",
               "Plan over de dag": "s_plan", "Geleerd verbruik": "s_geleerd", "Historie": "s_historie",
               "Relais en kalibratie": "s_relais"}
OVERVIEW_KEYS = [g[1] for g in OVERVIEW_GROUPS] + list(STAT_GROUPS.values())


def _group_cards(cards, groups, titles):
    out, done = [], {}
    for card in cards:
        title = card.get("title") or ""
        if card.get("type") == "horizontal-stack" and all(c.get("type") == "gauge" for c in card.get("cards", [])):
            title = "__gauges"
        grp = next((g for g in groups if title.startswith(g[0])), None)
        if grp is None:
            out.append(card)
            continue
        key, icon = grp[1], grp[2]
        name = titles.get(key) or title
        ent = f"input_boolean.zendure_ems_toon_{key}"
        if key in done:                      # e.g. second and third set: into the same group
            done[key]["card"]["cards"].append(card)
            continue
        cond = {"type": "conditional", "conditions": [{"condition": "state", "entity": ent, "state": "on"}],
                "card": {"type": "vertical-stack", "cards": [card]}}
        if key not in ("grenzen", "o_sets"):
            card.pop("title", None)
        done[key] = cond
        out.append({"type": "vertical-stack", "cards": [
            {"type": "tile", "entity": ent, "name": name, "icon": icon,
             "hide_state": True, "tap_action": {"action": "toggle"}, "icon_tap_action": {"action": "toggle"}},
            cond]})
    return out


def _hide_offline_sets(card):
    """Gauges and cards of a set that is not connected (yet) are hidden instead of showing warnings."""
    import re
    if card.get("type") in ("horizontal-stack", "vertical-stack"):
        card["cards"] = [_hide_offline_sets(c) for c in card["cards"]]
        return card
    if card.get("type") == "conditional" and "card" in card:
        card["card"] = _hide_offline_sets(card["card"])
        return card
    m = None
    if card.get("type") == "gauge":
        m = re.fullmatch(r"sensor\.zendure_set(\d+)_soc", card.get("entity", ""))
    elif card.get("type") == "entities":
        m = re.fullmatch(r"Set (\d+)", card.get("title", ""))
    if not m:
        return card
    return {"type": "conditional",
            "conditions": [{"condition": "state", "entity": f"sensor.zendure_set{m.group(1)}_soc",
                            "state_not": "unavailable"}],
            "card": card}


def _ip_set(i):
    return f"input_text.zendure_set{i}_ip"


def _unconfigured_conditions(i):
    """Card conditions: set i has an IP address filled in."""
    return [{"condition": "state", "entity": _ip_set(i), "state_not": ["", "unknown", "unavailable"]}]


def _hide_unconfigured(card):
    """One package for 1 to 3 sets: what belongs to set 2 or 3 is only shown once its IP address is filled in.
    The IP fields themselves always stay visible."""
    import re
    for key in ("cards",):
        for c in card.get(key, []) or []:
            _hide_unconfigured(c)
    if isinstance(card.get("card"), dict):
        _hide_unconfigured(card["card"])
    m = re.fullmatch(r"(?:Grenzen set|Set) (\d+)", str(card.get("title", "")))
    if m and m.group(1) != "1":
        card["visibility"] = (card.get("visibility") or []) + _unconfigured_conditions(m.group(1))
    if card.get("type") == "entities":
        rows = []
        for e in card.get("entities", []):
            ent = e if isinstance(e, str) else e.get("entity", "")
            m = re.search(r"zendure_set(\d+)_", ent)
            if m and m.group(1) != "1" and not ent.endswith("_ip"):
                ip = _ip_set(m.group(1))
                e = {"type": "conditional",
                     "conditions": [{"entity": ip, "state_not": ""}, {"entity": ip, "state_not": "unknown"}],
                     "row": e if isinstance(e, dict) else {"entity": e}}
            rows.append(e)
        card["entities"] = rows
    if card.get("type") == "history-graph":
        pass                                     # an unused set simply has no line
    return card


def collapsible_settings(text: str) -> str:
    """Cards on the Instellingen and Overzicht tabs get a header tile; tapping it shows or hides the card."""
    import yaml
    header = "".join(line + "\n" for line in text.splitlines() if line.startswith("#"))
    dash = yaml.safe_load(text)
    view = next(v for v in dash["views"] if v.get("path") == "overzicht")
    view["cards"] = _group_cards(view["cards"], [(g[0], g[1], g[2]) for g in OVERVIEW_GROUPS],
                                 {g[1]: g[3] for g in OVERVIEW_GROUPS if g[3]})
    view["cards"] = [_hide_offline_sets(c) for c in view["cards"]]
    # sections layout (4 columns on a wide screen):
    #   left: energy flow + mode/status/profile | middle: SOC per set + sets | right (2 wide): planner
    #   next row: power, EV charging, SOC history
    cards = view.pop("cards")

    def key_of(card):
        if card.get("type") == "picture-elements":
            return "flow"
        head = card.get("cards", [{}])[0] if card.get("type") == "vertical-stack" else {}
        ent = head.get("entity", "")
        return ent.replace("input_boolean.zendure_ems_toon_", "") if "toon_o_" in ent else "mode"

    by = {key_of(c): c for c in cards}
    # three columns: [flow, mode] | [SOC per set, sets, planner] | [SOC 24 h, power, EV]
    used = set()

    def planner_cards():
        """Planner as separate cards: header tile, status, today, tomorrow (each hidden when collapsed)."""
        grp = by["o_planner"]
        tile = grp["cards"][0]
        md = next(c for c in grp["cards"][1]["card"]["cards"] if c.get("type") == "markdown")["content"]
        vis = [{"condition": "state", "entity": tile["entity"], "state": "on"}]
        def strip(deel):
            """Only the part this card shows: the header for 'kop', the day table otherwise (keeps the dashboard small)."""
            i, j = md.index("{#KOP#}"), md.index("{#/KOP#}")
            if deel == "'kop'":
                return md[:j] + "{%- endif -%}"
            return md[:i] + md[j:]
        part = lambda deel: {"type": "markdown", "content": "{%- set deel = " + deel + " -%}\n" + strip(deel), "visibility": vis}
        tile["grid_options"] = {"columns": "full"}
        return [tile, part("'kop'"), part("0"), part("1")]

    columns = [["flow", "mode"], ["o_laadtoestand", "o_sets", "o_planner"], ["o_soc", "o_vermogen", "o_ev", "o_kalibratie"]]
    sections = []
    for keys in columns:
        cards = []
        for k in keys:
            if k not in by:
                continue
            cards += planner_cards() if k == "o_planner" else [by[k]]
        used.update(keys)
        if cards:
            sections.append({"type": "grid", "cards": cards})
    sections += [{"type": "grid", "cards": [c]} for k, c in by.items() if k not in used]
    view["type"] = "sections"
    view["max_columns"] = 3
    view["sections"] = sections
    view = next(v for v in dash["views"] if v.get("path") == "instellingen")
    view["cards"] = _group_cards(view["cards"], SETTING_GROUPS, GROUP_TITLES)
    view = next(v for v in dash["views"] if v.get("path") == "statistieken")
    for sec in view["sections"]:
        head = sec["cards"][0]
        key = STAT_GROUPS.get(head.get("heading"))
        if head.get("type") != "heading" or key is None:
            continue
        if key == "s_dagplanning":
            sec["column_span"] = 2               # wide, so the table rows do not wrap
        ent = f"input_boolean.zendure_ems_toon_{key}"
        # same header tile as the collapsible groups on Instellingen and Overzicht
        sec["cards"][0] = {"type": "tile", "entity": ent, "name": head["heading"], "icon": head.get("icon"),
                           "hide_state": True, "tap_action": {"action": "toggle"},
                           "icon_tap_action": {"action": "toggle"}, "grid_options": {"columns": "full"}}
        for c in sec["cards"][1:]:
            c["visibility"] = [{"condition": "state", "entity": ent, "state": "on"}]
    for v in dash["views"]:
        for c in v.get("cards", []) or []:
            _hide_unconfigured(c)
        for sec in v.get("sections", []) or []:
            for c in sec.get("cards", []) or []:
                _hide_unconfigured(c)
    return header + _dump(dash)


def ind(text: str, n: int) -> str:
    pad = " " * n
    return "\n".join(pad + line if line else "" for line in text.splitlines())


def dashboard(n: int) -> str:
    from version import VERSION
    flow_card = flow_picture(n)
    smart_rows = "".join(f"          - entity: sensor.zendure_set{i}_smartmode\n            name: Set {i} schrijft naar\n"
                         for i in range(1, n + 1))
    statistieken = statistics_view()
    sets = [str(i) for i in range(1, n + 1)]
    gauges = "".join(
        f"""          - type: gauge
            entity: sensor.zendure_set{i}_soc
            name: Set {i}
            min: 0
            max: 100
            severity:
              red: 0
              yellow: 20
              green: 40
"""
        for i in sets
    )
    set_cards = "".join(
        f"""      - type: entities
        title: Set {i}
        state_color: true
        entities:
          - entity: sensor.zendure_set{i}_vermogen
            name: Vermogen (+ laden / - ontladen)
          - entity: sensor.zendure_set{i}_soc
            name: Laadtoestand
          - entity: sensor.zendure_set{i}_temperatuur
            name: Temperatuur
          - entity: input_boolean.zendure_set{i}_laden
            name: Laden toegestaan
          - entity: input_boolean.zendure_set{i}_ontladen
            name: Ontladen toegestaan
"""
        for i in sets
    )
    kal_rows = "".join(f"""          - entity: sensor.zendure_set{i}_dagen_sinds_vol
            name: Set {i}, dagen sinds 100 %
""" for i in sets)
    kal_set = "".join(f"""          - entity: input_datetime.zendure_set{i}_laatst_vol
            name: Set {i} laatst 100 % (zelf aan te passen)
""" for i in sets)
    history = "".join(f"          - entity: sensor.zendure_set{i}_vermogen\n            name: Set {i}\n" for i in sets)
    ips = "".join(f"          - entity: input_text.zendure_set{i}_ip\n            name: IP-adres set {i}\n" for i in sets)
    limits = "".join(
        f"""      - type: entities
        title: Grenzen set {i}
        entities:
          - entity: input_number.zendure_set{i}_min_soc
            name: Minimale SOC
          - entity: input_number.zendure_set{i}_capaciteit
            name: Accucapaciteit (0 = packs × kWh per pack)
          - entity: input_number.zendure_set{i}_reserve
            name: Reserve boven min SOC (kWh)
          - entity: input_number.zendure_set{i}_max_soc
            name: Maximale SOC
          - entity: input_number.zendure_set{i}_max_laden
            name: Max laadvermogen
          - entity: input_number.zendure_set{i}_max_ontladen
            name: Max ontlaadvermogen
"""
        for i in sets
    )
    return collapsible_settings(f"""# Zendure EMS dashboard {VERSION} ({n} sets). Tabblad Statistieken vereist de HACS-kaart ApexCharts Card.
# Gebruik: Instellingen > Dashboards > Dashboard toevoegen > Nieuw dashboard,
# open het, kies het potlood > drie puntjes > Raw-configuratie-editor en plak dit.
title: Zendure EMS {VERSION}
views:
  - title: Overzicht
    path: overzicht
    icon: mdi:home-battery
    cards:
{flow_card}      - type: vertical-stack
        cards:
          - type: tile
            entity: input_select.zendure_ems_modus
            name: Modus
            features:
              - type: select-options
          - type: tile
            entity: input_select.zendure_ems_profiel
            name: Profiel activeren
            features:
              - type: select-options
          - type: entities
            entities:
              - entity: sensor.zendure_ems_actief_profiel
                name: Actief profiel
              - type: buttons
                entities:
                  - entity: script.zendure_ems_profiel_opslaan
                    name: Opslaan als mijn profiel 1
                    icon: mdi:numeric-1-box
                    tap_action:
                      action: perform-action
                      perform_action: script.zendure_ems_profiel_opslaan
                      data:
                        slot: 1
                      confirmation:
                        text: Huidige instellingen opslaan als mijn profiel 1?
                  - entity: script.zendure_ems_profiel_opslaan
                    name: Opslaan als mijn profiel 2
                    icon: mdi:numeric-2-box
                    tap_action:
                      action: perform-action
                      perform_action: script.zendure_ems_profiel_opslaan
                      data:
                        slot: 2
                      confirmation:
                        text: Huidige instellingen opslaan als mijn profiel 2?
          - type: entities
            entities:
              - entity: sensor.zendure_ems_status
                name: Status
              - type: attribute
                entity: sensor.zendure_ems_prijsactie
                attribute: omschrijving
                name: Prijsactie
              - type: attribute
                entity: sensor.zendure_ems_regelaar
                attribute: actieve_sets
                name: Actieve sets
                icon: mdi:battery-sync
              - entity: input_text.zendure_ems_versie
                name: Versie package (dashboard {VERSION})
                icon: mdi:tag-outline
          - type: glance
            show_state: true
            entities:
              - entity: sensor.zendure_ems_grafiek_net
                name: Net
              - entity: sensor.zendure_ems_accuvermogen
                name: Accu's
              - entity: sensor.zendure_ems_gemiddelde_soc
                name: SOC
              - entity: sensor.zendure_ems_opgeslagen_energie
                name: Opgeslagen
              - entity: sensor.zendure_ems_stroomprijs
                name: Prijs
      - type: horizontal-stack
        cards:
{gauges}      - type: history-graph
        title: Vermogen (laatste 3 uur)
        hours_to_show: 3
        entities:
          - entity: sensor.zendure_ems_grafiek_net
            name: Net (+ afname)
          - entity: sensor.zendure_ems_accuvermogen
            name: Accu's totaal (+ laden)
{history}      - type: markdown
        title: Planner (per kwartier)
        content: |-
{ind(PRICE_TABLE, 10)}
      - type: entities
        title: EV laden
        state_color: true
        entities:
          - entity: switch.zendure_ems_ev_laden_van_het_net
            name: EV laden van het net
          - entity: binary_sensor.zendure_ems_ev_laadt
            name: Auto laadt
          - entity: sensor.zendure_ems_ev_vermogen
            name: Autolader vermogen
          - entity: sensor.zendure_ems_ev_energie_vandaag
            name: kWh naar auto vandaag
          - entity: sensor.zendure_ems_ev_laadtijd_vandaag
            name: Laadtijd vandaag
          - entity: sensor.zendure_ems_ev_kosten_vandaag
            name: Kosten vandaag
          - entity: sensor.zendure_ems_grafiek_net
            name: Net zoals de accu's het zien
      - type: entities
        title: Kalibratie (100 %)
        state_color: true
        entities:
          - entity: sensor.zendure_ems_kalibratie
            name: Status
{kal_rows}{set_cards}      - type: history-graph
        title: Laadtoestand (24 uur)
        hours_to_show: 24
        entities:
{"".join(f"          - entity: sensor.zendure_set{i}_soc{chr(10)}            name: Set {i}{chr(10)}" for i in sets)}
  - title: Instellingen
    path: instellingen
    icon: mdi:cog
    cards:
      - type: markdown
        content: >-
          **Eerst doen:** zet in de Zendure-app bij elke set **HEMS uit** en zet de
          **lokale API (HTTP)** aan. Vul hieronder de IP-adressen, de netmeter en de
          prijssensor in. Kies daarna op het Overzicht een modus.
          **Niet aansturen** = deze regeling doet niets. **Uit (stand-by)** = alle sets 0 W.
          **Laden / Ontladen (vol vermogen)** = alle sets laden van of ontladen naar het net op hun
          maximale vermogen; als de accu vol of leeg is, gaat de modus terug naar de vorige modus.
          Tik op een onderdeel hieronder om het open of dicht te klappen.

          Dashboard **{VERSION}** · package **{{{{ states('input_text.zendure_ems_versie') }}}}**
          {{% if states('input_text.zendure_ems_versie') != '{VERSION}' %}}

          ⚠️ **Package en dashboard hebben niet dezelfde versie.** Plaats het package en het dashboard uit
          dezelfde zip en herstart Home Assistant.
          {{% endif %}}
      - type: entities
        title: Aansluiting
        entities:
{ips}          - entity: input_text.zendure_ems_netsensor
            name: Netmeter-sensor (bv. sensor.p1_meter_power)
          - entity: input_text.zendure_ems_p1_ip
            name: HomeWizard P1 IP-adres (optioneel, meting elke seconde)
          - type: conditional
            conditions:
              - entity: input_text.zendure_ems_p1_ip
                state_not: ["", "unknown", "unavailable"]
            row:
              entity: sensor.zendure_ems_p1_vermogen
              name: P1 vermogen (elke seconde)
          - entity: sensor.zendure_ems_netmeter_bron
            name: Regeling gebruikt
          - entity: input_boolean.zendure_ems_net_omkeren
            name: Netmeter omkeren (als teruglevering positief is)
          - entity: input_text.zendure_ems_prijssensor
            name: Prijssensor
          - entity: input_number.zendure_ems_kwh_per_pack
            name: Capaciteit per accupack
      - type: entities
        title: Planner (zon en verbruik)
        entities:
          - entity: input_text.zendure_ems_zon_vandaag
            name: Zonneverwachting vandaag (sensor.energy_production_today_remaining)
          - entity: input_text.zendure_ems_zon_morgen
            name: Zonneverwachting morgen (sensor.energy_production_tomorrow)
          - entity: input_number.zendure_ems_zon_factor
            name: Zonneverwachting meetellen voor
          - entity: input_text.zendure_ems_zonproductie
            name: Zonneproductie-sensor (optioneel, voor het verbruiksprofiel)
          - entity: sensor.zendure_ems_grafiek_huisverbruik
            name: Huisverbruik nu
          - entity: sensor.zendure_ems_verbruiksprofiel
            name: Geleerd gemiddeld verbruik (werkdag)
          - type: attribute
            entity: sensor.zendure_ems_verbruiksprofiel
            attribute: dagverbruik_werkdag_kwh
            name: Geleerd dagverbruik werkdag
            suffix: kWh
          - type: attribute
            entity: sensor.zendure_ems_verbruiksprofiel
            attribute: dagverbruik_weekend_kwh
            name: Geleerd dagverbruik weekend
            suffix: kWh
          - type: attribute
            entity: sensor.zendure_ems_verbruiksprofiel
            attribute: geleerd
            name: Geleerd
            icon: mdi:school
          - entity: input_text.zendure_ems_historie_laden
            name: Historie laadvermogen accu (oud, bv. Gielz Vermogen Import)
          - entity: input_text.zendure_ems_historie_ontladen
            name: Historie ontlaadvermogen accu (oud, bv. Gielz Vermogen Export)
          - type: button
            name: Startprofiel uit historie opbouwen
            icon: mdi:history
            action_name: Starten
            tap_action:
              action: perform-action
              perform_action: script.zendure_ems_startprofiel
              data:
                dagen: 28
              confirmation:
                text: >-
                  Het geleerde verbruiksprofiel wordt overschreven met een profiel uit de laatste 28 dagen
                  historie. Doe dit pas als alle sets zijn aangesloten. Doorgaan?
      - type: entities
        title: Teruglevering (salderen en terugleverprijs)
        entities:
          - entity: input_select.zendure_ems_salderen
            name: Salderen
          - entity: input_text.zendure_ems_terugleverprijs_sensor
            name: Kale-prijssensor (bv. sensor.nordpool_kwh_nl_eur_3_10_0)
          - entity: input_boolean.zendure_ems_teruglever_btw
            name: Btw over terugleververgoeding
          - entity: input_number.zendure_ems_teruglever_vast
            name: Vaste vergoeding (+) of terugleverkosten (−)
          - entity: input_number.zendure_ems_teruglever_bonus
            name: Terugleverbonus (Zonneplan-zonnebonus 10 %)
          - entity: input_boolean.zendure_ems_bonus_overdag
            name: Bonus alleen overdag
          - entity: input_number.zendure_ems_energiebelasting
            name: Energiebelasting (alleen zonder kale-prijssensor)
          - entity: input_number.zendure_ems_inkoop
            name: Inkoopvergoeding (alleen zonder kale-prijssensor)
          - entity: sensor.zendure_ems_terugleverprijs
            name: Terugleverprijs nu
          - type: attribute
            entity: sensor.zendure_ems_terugleverprijs
            attribute: opbouw
            name: Opbouw
            icon: mdi:information-outline
      - type: entities
        title: Zonnepanelen afschalen (negatieve prijs)
        entities:
          - entity: input_select.zendure_ems_afschalen
            name: Afschalen
          - entity: input_boolean.zendure_ems_afgeschaald
            name: Nu afgeschaald (status)
          - entity: input_number.zendure_ems_afschaal_drempel
            name: Afschalen onder terugleverprijs
          - entity: input_text.zendure_ems_export_entiteit
            name: Exportlimiet-entiteit (bv. number.goodwe_net_exportlimiet)
          - entity: input_number.zendure_ems_export_normaal
            name: Exportlimiet normaal
          - entity: input_number.zendure_ems_export_afgeschaald
            name: Exportlimiet afgeschaald
          - entity: input_number.zendure_ems_afschaal_stap
            name: Exportlimiet in stappen van (0 = in één keer)
          - entity: input_number.zendure_ems_afschaal_interval
            name: Tijd tussen stappen
          - entity: input_text.zendure_ems_export_schakelaar
            name: Limiter-schakelaar (optioneel)
          - entity: input_text.zendure_ems_extra_entiteit
            name: Extra apparaat-limiet (optioneel)
          - entity: input_number.zendure_ems_extra_normaal
            name: Extra apparaat normaal
          - entity: input_number.zendure_ems_extra_afgeschaald
            name: Extra apparaat afgeschaald
      - type: entities
        title: EV laden (granny-lader)
        entities:
          - entity: input_text.zendure_ems_ev_sensor
            name: Vermogenssensor lader (bv. sensor.autolader_power)
          - entity: input_text.zendure_ems_ev_actief
            name: EV laden van het net (bv. input_boolean.ev_laden_actief)
          - entity: sensor.zendure_ems_ev_vermogen
            name: EV-vermogen nu
      - type: entities
        title: Kalibratie (volladen naar 100 %)
        entities:
          - entity: input_select.zendure_ems_kalibratie
            name: Volladen naar 100 %
          - entity: input_select.zendure_ems_kalibratie_dag
            name: Dag (bij Wekelijks / Elke 2 of 3 weken)
          - entity: input_datetime.zendure_ems_kalibratie_datum
            name: Datum (bij Op datum)
          - entity: input_number.zendure_ems_kalibratie_dagen
            name: Uiterlijk na (dagen)
          - entity: input_number.zendure_ems_kalibratie_tot
            name: Klaar om (uur, volgende ochtend)
{kal_set}          - entity: sensor.zendure_ems_kalibratie
            name: Status
      - type: entities
        title: Zonnecorrectie
        entities:
          - entity: input_boolean.zendure_ems_zon_leren
            name: Zonnecorrectie leren
          - entity: sensor.zendure_ems_zonnecorrectie
            name: Geleerde correctie
          - type: attribute
            entity: sensor.zendure_ems_zonnecorrectie
            attribute: dagen
            name: Geleerde dagen (gebruikt vanaf 3)
            icon: mdi:calendar-check
          - type: attribute
            entity: sensor.zendure_ems_zonnecorrectie
            attribute: laatste
            name: Laatste vergelijking
            icon: mdi:compare
          - entity: sensor.zendure_ems_zonneproductie
            name: Zonneproductie nu
          - entity: sensor.zendure_ems_zonne_energie_vandaag
            name: Zonne-energie vandaag (gemeten)
          - type: button
            name: Zonnecorrectie opnieuw leren
            icon: mdi:restore
            action_name: Terugzetten
            tap_action:
              action: perform-action
              perform_action: script.zendure_ems_zonnecorrectie_reset
              confirmation:
                text: De geleerde zonnecorrectie wordt teruggezet naar de vaste factor. Doorgaan?
      - type: entities
        title: Prijssturing (modus Prijsgestuurd)
        entities:
          - entity: input_boolean.zendure_ems_verkoop_plannen
            name: Verkopen plannen (aan bij de profielen Handelen)
          - entity: input_boolean.zendure_ems_laden_negatieve_prijs
            name: Laden van het net bij negatieve prijs
          - entity: input_number.zendure_ems_laadprijs
            name: Laden van het net onder (-0,50 = uit)
          - entity: input_number.zendure_ems_ontlaadprijs
            name: Alleen ontladen boven (-0,50 = altijd)
          - entity: input_number.zendure_ems_verkoopprijs
            name: Verkopen aan het net boven (1,00 = uit)
          - entity: input_number.zendure_ems_handel_prijs
            name: Profielen Handelen verkopen boven
          - entity: input_boolean.zendure_ems_slim_laden
            name: Slim laden (planner, per kwartier)
          - entity: input_boolean.zendure_ems_slim_ontladen
            name: Slim ontladen (accu bewaren voor dure kwartieren)
          - entity: input_number.zendure_ems_min_spread
            name: Minimale winst per kWh
          - entity: input_number.zendure_ems_slijtage
            name: Slijtagekosten per kWh
          - entity: input_number.zendure_ems_rendement
            name: Rendement heen en terug
          - entity: input_number.zendure_ems_verwacht_verbruik
            name: Verwacht verbruik (tot het profiel geleerd is)
          - entity: input_number.zendure_ems_max_netafname
            name: Max netafname bij netladen (hoofdzekering, 0 = uit)
{limits}      - type: entities
        title: Regeling (geavanceerd)
        entities:
          - entity: input_number.zendure_ems_doel_net
            name: Doel netvermogen
          - entity: input_number.zendure_ems_deadband
            name: Dode zone
          - entity: input_number.zendure_ems_kp
            name: Kp (reactiesnelheid)
          - entity: input_number.zendure_ems_kd
            name: Kd (demping)
          - entity: input_number.zendure_ems_max_stap
            name: Max stap per cyclus
          - entity: input_boolean.zendure_ems_wachttijd_auto
            name: Wachttijd automatisch (volgens meterinterval)
          - type: attribute
            entity: sensor.zendure_ems_regelaar
            attribute: meterinterval
            name: Gemeten meterinterval
            suffix: s
            icon: mdi:timer-outline
          - type: attribute
            entity: sensor.zendure_ems_regelaar
            attribute: wachttijd_auto
            name: Automatische wachttijd
            suffix: s
            icon: mdi:timer-cog-outline
          - entity: input_number.zendure_ems_wachttijd
            name: Wachttijd na opdracht (als automatisch uit staat)
          - entity: input_number.zendure_ems_min_vermogen
            name: Minimaal vermogen per set
          - entity: input_number.zendure_ems_min_looptijd
            name: Minimale looptijd bij klein vermogen (0 = uit)
          - entity: input_boolean.zendure_ems_korte_dips_negeren
            name: Korte dips negeren (bv. droger)
          - entity: input_number.zendure_ems_dip_tijd
            name: Korte dips negeren tot
          - entity: input_number.zendure_ems_staging
            name: Volgende set inzetten vanaf
          - entity: input_number.zendure_ems_systeem_max_laden
            name: Systeem max laden (0 = geen)
          - entity: input_number.zendure_ems_systeem_max_ontladen
            name: Systeem max ontladen (0 = geen)
          - entity: input_boolean.zendure_ems_standaard_ingesteld
            name: Standaardwaarden ingesteld (uitzetten = alles terugzetten)
          - entity: automation.zendure_ems_regeling
            name: Regeling actief
          - type: section
            label: Flashgeheugen sparen
          - entity: input_boolean.zendure_ems_flash_schrijven
            name: Limieten naar flash schrijven (uit = RAM, aanbevolen)
          - entity: input_number.zendure_ems_standby_vertraging
            name: Standby na inactiviteit (0 = uit)
{smart_rows}          - entity: automation.zendure_ems_smartmode_ram_bewaken
            name: smartMode bewaken
{statistieken}""")
