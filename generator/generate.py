"""Generate the Zendure EMS Home Assistant package (pure YAML) for N sets.

Usage: python3 generate.py OUTDIR
Writes zendure_ems_2sets.yaml and zendure_ems_3sets.yaml.
"""

import sys
import textwrap
from pathlib import Path

from templates import (  # noqa: F401
    BATT, CONTROL, CURTAIL, PROFILE_MATCH, PROFILE_NOW, PROFILE_PICK, SMARTMODE_BACK, EV_NOW, GRID, HOUSE, PRECHECK, PRICE, PROFILE, SOC_LIMITS, CALIB_STATUS, SOLAR_CORR, SOLAR_NOW, STANDBY_LIST, START_PROFILE,
)

from version import VERSION  # noqa: E402
from dashboard import OVERVIEW_KEYS  # noqa: E402  (single source for package and dashboard)


def block(tpl: str, sets: list[str], indent: int) -> str:
    """A Jinja template as a YAML literal block, indented."""
    body = tpl.replace("__SETS__", repr(sets)).strip("\n")
    pad = " " * indent
    return "|-\n" + "\n".join((pad + line) if line.strip() else "" for line in body.splitlines())


def num(key, name, mn, mx, step, unit=None, icon=None, mode="box"):
    out = f"""  {key}:
    name: "{name}"
    min: {mn}
    max: {mx}
    step: {step}
    mode: {mode}
"""
    if unit:
        out += f'    unit_of_measurement: "{unit}"\n'
    if icon:
        out += f"    icon: {icon}\n"
    return out


# (key, name, min, max, step, unit, icon, default)
GLOBAL_NUMBERS = [
    ("zendure_ems_doel_net", "Zendure EMS doel netvermogen", -500, 500, 5, "W", "mdi:target", 0),
    ("zendure_ems_deadband", "Zendure EMS dode zone", 0, 200, 5, "W", "mdi:arrow-collapse-horizontal", 35),
    ("zendure_ems_kp", "Zendure EMS Kp", 0.05, 1.0, 0.05, None, "mdi:tune", 0.6),
    ("zendure_ems_kd", "Zendure EMS Kd", 0, 1.0, 0.05, None, "mdi:tune", 0),
    ("zendure_ems_max_stap", "Zendure EMS max stap per cyclus", 100, 7200, 50, "W", "mdi:stairs-up", 1500),
    ("zendure_ems_wachttijd", "Zendure EMS wachttijd na opdracht", 1, 10, 0.5, "s", "mdi:timer-sand", 3),
    ("zendure_ems_min_vermogen", "Zendure EMS minimaal vermogen per set", 0, 300, 10, "W", "mdi:power-plug-off", 100),
    ("zendure_ems_min_looptijd", "Zendure EMS minimale looptijd bij klein vermogen (0 = uit)", 0, 300, 5, "s", "mdi:timer-lock-outline", 60),
    ("zendure_ems_staging", "Zendure EMS extra set inzetten vanaf", 0, 100, 5, "%", "mdi:battery-plus", 60),
    ("zendure_ems_systeem_max_laden", "Zendure EMS systeem max laden (0 = geen)", 0, 20000, 100, "W", "mdi:battery-arrow-up", 0),
    ("zendure_ems_systeem_max_ontladen", "Zendure EMS systeem max ontladen (0 = geen)", 0, 20000, 100, "W", "mdi:battery-arrow-down", 0),
    ("zendure_ems_max_netafname", "Zendure EMS max netafname bij netladen (0 = uit)", 0, 30000, 100, "W", "mdi:fuse", 0),
    ("zendure_ems_kwh_per_pack", "Zendure EMS capaciteit per accupack", 0.5, 10, 0.01, "kWh", "mdi:battery", 2.88),
    ("zendure_ems_laadprijs", "Zendure EMS laden van net onder (-0,50 = uit)", -0.5, 1.0, 0.01, "€/kWh", "mdi:cash-minus", -0.5),
    ("zendure_ems_ontlaadprijs", "Zendure EMS alleen ontladen boven (-0,50 = altijd)", -0.5, 1.0, 0.01, "€/kWh", "mdi:cash", -0.5),
    ("zendure_ems_verkoopprijs", "Zendure EMS verkopen aan net boven (1,00 = uit)", -0.5, 1.0, 0.01, "€/kWh", "mdi:cash-plus", 1.0),
    ("zendure_ems_min_spread", "Zendure EMS minimale winst per kWh", 0, 0.5, 0.01, "€/kWh", "mdi:chart-line-variant", 0.05),
    ("zendure_ems_slijtage", "Zendure EMS slijtagekosten per kWh", 0, 0.2, 0.005, "€/kWh", "mdi:battery-heart-variant", 0.03),
    ("zendure_ems_rendement", "Zendure EMS rendement heen en terug", 50, 100, 1, "%", "mdi:percent", 85),
    ("zendure_ems_verwacht_verbruik", "Zendure EMS verwacht verbruik huis", 50, 5000, 50, "W", "mdi:home-lightning-bolt", 400),
    ("zendure_ems_zon_factor", "Zendure EMS zonneverwachting meetellen", 0, 150, 5, "%", "mdi:weather-partly-cloudy", 80),
    ("zendure_ems_teruglever_vast", "Zendure EMS vaste terugleververgoeding (+) of -kosten (-)", -0.2, 0.2, 0.005, "€/kWh", "mdi:cash-plus", 0.0),
    ("zendure_ems_teruglever_bonus", "Zendure EMS terugleverbonus", 0, 50, 1, "%", "mdi:white-balance-sunny", 0),
    ("zendure_ems_energiebelasting", "Zendure EMS energiebelasting (incl. btw)", 0, 0.3, 0.0001, "€/kWh", "mdi:bank", 0.1065),
    ("zendure_ems_inkoop", "Zendure EMS inkoopvergoeding (incl. btw)", 0, 0.1, 0.001, "€/kWh", "mdi:cart", 0.02),
    ("zendure_ems_afschaal_drempel", "Zendure EMS panelen afschalen onder", -0.5, 0.5, 0.01, "€/kWh", "mdi:solar-power-variant", 0.0),
    ("zendure_ems_export_normaal", "Zendure EMS exportlimiet normaal", 0, 30000, 50, "W", "mdi:transmission-tower-export", 3000),
    ("zendure_ems_export_afgeschaald", "Zendure EMS exportlimiet afgeschaald", 0, 30000, 50, "W", "mdi:transmission-tower-off", 0),
    ("zendure_ems_extra_normaal", "Zendure EMS extra apparaat normaal", 0, 5000, 10, "W", "mdi:solar-panel", 800),
    ("zendure_ems_handel_prijs", "Zendure EMS profielen Handelen: verkopen boven", 0.0, 1.0, 0.01, "€/kWh", "mdi:cash-plus", 0.35),
    ("zendure_ems_standby_vertraging", "Zendure EMS standby na inactiviteit (0 = uit)", 0, 60, 1, "min", "mdi:sleep", 5),
    ("zendure_ems_besparing_start", "Zendure EMS besparing startwaarde (bv. uit batterij planner)", -1000, 10000, 0.01, "EUR", "mdi:piggy-bank-outline", 0),
    ("zendure_ems_afschaal_stap", "Zendure EMS exportlimiet in stappen van (0 = in één keer)", 0, 5000, 50, "W", "mdi:stairs-down", 500),
    ("zendure_ems_afschaal_interval", "Zendure EMS tijd tussen stappen", 2, 120, 1, "s", "mdi:timer-sand", 10),
    ("zendure_ems_extra_afgeschaald", "Zendure EMS extra apparaat afgeschaald", 0, 5000, 10, "W", "mdi:solar-panel", 0),
    ("zendure_ems_dip_tijd", "Zendure EMS korte dips negeren tot", 5, 120, 5, "s", "mdi:timer-sand", 20),
    ("zendure_ems_kalibratie_dagen", "Zendure EMS kalibratie uiterlijk na", 7, 31, 1, "dagen", "mdi:calendar-alert", 28),
    ("zendure_ems_kalibratie_tot", "Zendure EMS kalibratie klaar om (volgende ochtend, 0 = middernacht)", 0, 12, 1, "uur", "mdi:clock-end", 7),
]


def set_numbers(i):
    return [
        (f"zendure_set{i}_min_soc", f"Zendure set{i} min SOC", 5, 50, 1, "%", "mdi:battery-10", 10),
        (f"zendure_set{i}_max_soc", f"Zendure set{i} max SOC", 70, 100, 1, "%", "mdi:battery-90", 100),
        (f"zendure_set{i}_max_laden", f"Zendure set{i} max laadvermogen", 0, 2400, 50, "W", "mdi:battery-arrow-up", 2400),
        (f"zendure_set{i}_max_ontladen", f"Zendure set{i} max ontlaadvermogen", 0, 2400, 50, "W", "mdi:battery-arrow-down", 2400),
        (f"zendure_set{i}_capaciteit", f"Zendure set{i} accucapaciteit (0 = packs x kWh per pack)", 0, 60, 0.01, "kWh", "mdi:battery-high", 0),
        (f"zendure_set{i}_reserve", f"Zendure set{i} reserve boven min SOC", 0, 10, 0.1, "kWh", "mdi:battery-lock", 0),
    ]


def standby_trigger(i):
    return f"""      - trigger: state
        entity_id: binary_sensor.zendure_set{i}_inactief
        to: "on"
        for:
          minutes: "{{{{ [states('input_number.zendure_ems_standby_vertraging') | int(5), 1] | max }}}}"
        id: "{i}"
"""


def generate(n: int) -> str:
    sets = [str(i) for i in range(1, n + 1)]
    S = []
    S.append(f"""# =============================================================================
# Zendure EMS {VERSION}: nul-op-de-meter + dynamische prijzen voor {n} Zendure
# SolarFlow-sets (2400 AC+ / 2400 AC Pro), volledig in YAML.
#
# Gebaseerd op de regelaanpak en de Zendure-API-kennis van Omnibattery
# (https://github.com/ffunes/omnibattery, GPL-3.0). Dit package valt daarom
# ook onder GPL-3.0. Gebruik op eigen risico.
#
# Installatie (zie LEESMIJ.md):
#   1. Zet in configuration.yaml:  homeassistant:  packages: !include_dir_named packages
#   2. Kopieer dit bestand naar config/packages/zendure_ems.yaml
#   3. Herstart Home Assistant
#   4. Vul op het dashboard de IP-adressen, netmeter en prijssensor in
#   5. Zet HEMS UIT in de Zendure-app en kies daarna een modus
#
# Gegenereerd bestand: pas liever generate.py aan dan dit bestand.
# =============================================================================
""")

    # ---------------- input helpers
    S.append("input_select:\n")
    S.append("""  zendure_ems_salderen:
    name: "Zendure EMS salderen"
    icon: mdi:scale-balance
    options:
      - "Automatisch (t/m 2026)"
      - "Aan"
      - "Uit"
  zendure_ems_afschalen:
    name: "Zendure EMS zonnepanelen afschalen bij negatieve prijs"
    icon: mdi:solar-power-variant
    options:
      - "Uit"
      - "Bij volle accu"
      - "Direct"
  zendure_ems_modus:
    name: "Zendure EMS modus"
    icon: mdi:home-battery
    options:
      - "Niet aansturen"
      - "Uit (stand-by)"
      - "Nul op de meter"
      - "Prijsgestuurd"
      - "Laden (vol vermogen)"
      - "Ontladen (vol vermogen)"
  zendure_ems_kalibratie:
    name: "Zendure EMS kalibratie (volladen naar 100 %)"
    icon: mdi:battery-sync
    options:
      - "Uit"
      - "Wekelijks"
      - "Elke 2 weken"
      - "Elke 3 weken"
      - "Op datum"
      - "Alleen na max. aantal dagen"
  zendure_ems_kalibratie_dag:
    name: "Zendure EMS kalibratiedag"
    icon: mdi:calendar-week
    options:
      - "maandag"
      - "dinsdag"
      - "woensdag"
      - "donderdag"
      - "vrijdag"
      - "zaterdag"
      - "zondag"
  zendure_ems_profiel:
    name: "Zendure EMS profiel activeren"
    icon: mdi:tune-variant
    options:
      - "Kies een profiel"
      - "Nul op de meter"
      - "Dynamisch NOM"
      - "Dynamisch NOM (Duur)"
      - "Dynamisch Handelen"
      - "Dynamisch Handelen + NOM"
      - "Stand-by"
      - "Mijn profiel 1"
      - "Mijn profiel 2"
""")
    S.append("""
input_datetime:
  zendure_ems_kalibratie_datum:
    name: "Zendure EMS kalibratiedatum"
    has_date: true
    has_time: false
    icon: mdi:calendar-check
""")
    S.append("".join(f"""  zendure_set{i}_laatst_vol:
    name: "Zendure set{i} laatst 100 %"
    has_date: true
    has_time: true
    icon: mdi:battery-check
""" for i in sets))
    S.append("\ninput_text:\n")
    S.append("""  zendure_ems_vorige_modus:
    name: "Zendure EMS vorige modus"
    icon: mdi:history
    max: 40
""")
    S.append("""  zendure_ems_historie_laden:
    name: "Zendure EMS historie: laadvermogen accu van vóór Zendure EMS (optioneel)"
    max: 100
    icon: mdi:battery-arrow-up
  zendure_ems_historie_ontladen:
    name: "Zendure EMS historie: ontlaadvermogen accu van vóór Zendure EMS (optioneel)"
    max: 100
    icon: mdi:battery-arrow-down
""")
    S.append("""  zendure_ems_mijn_profiel_1:
    name: "Zendure EMS mijn profiel 1 (opgeslagen instellingen)"
    max: 255
    icon: mdi:content-save-cog
  zendure_ems_mijn_profiel_2:
    name: "Zendure EMS mijn profiel 2 (opgeslagen instellingen)"
    max: 255
    icon: mdi:content-save-cog
""")
    S.append("""  zendure_ems_versie:
    name: "Zendure EMS versie (intern)"
    max: 20
    icon: mdi:tag-outline
  zendure_ems_ev_sensor:
    name: "Zendure EMS EV-vermogenssensor (W of kW)"
    max: 100
    icon: mdi:ev-plug-type2
  zendure_ems_ev_actief:
    name: "Zendure EMS EV laden van het net (schakelaar)"
    max: 100
    icon: mdi:ev-station
  zendure_ems_terugleverprijs_sensor:
    name: "Zendure EMS kale-prijssensor voor teruglevering (optioneel)"
    max: 100
    icon: mdi:currency-eur-off
  zendure_ems_export_entiteit:
    name: "Zendure EMS exportlimiet-entiteit (number)"
    max: 100
    icon: mdi:transmission-tower-export
  zendure_ems_export_schakelaar:
    name: "Zendure EMS limiter-schakelaar (optioneel)"
    max: 100
    icon: mdi:toggle-switch
  zendure_ems_extra_entiteit:
    name: "Zendure EMS extra apparaat-limiet (optioneel, number)"
    max: 100
    icon: mdi:solar-panel
  zendure_ems_netsensor:
    name: "Zendure EMS netmeter-sensor (W of kW, + = afname)"
    max: 100
    icon: mdi:transmission-tower
  zendure_ems_p1_ip:
    name: "Zendure EMS HomeWizard P1 IP-adres (optioneel, meting elke seconde)"
    max: 40
    icon: mdi:ip-network-outline
  zendure_ems_prijssensor:
    name: "Zendure EMS prijssensor (Nordpool, Zonneplan of ENTSO-e)"
    max: 100
    icon: mdi:currency-eur
  zendure_ems_zon_vandaag:
    name: "Zendure EMS zonneverwachting vandaag (resterend, Forecast.Solar)"
    max: 100
    icon: mdi:solar-power-variant
  zendure_ems_zon_morgen:
    name: "Zendure EMS zonneverwachting morgen (Forecast.Solar)"
    max: 100
    icon: mdi:solar-power-variant-outline
  zendure_ems_zonproductie:
    name: "Zendure EMS zonneproductie-sensor (optioneel, W of kW)"
    max: 100
    icon: mdi:solar-power
""")
    for i in sets:
        S.append(f"""  zendure_set{i}_ip:
    name: "Zendure set{i} IP-adres"
    max: 40
    icon: mdi:ip-network
""")
    S.append("\ninput_boolean:\n")
    S.append("".join(f"""  zendure_ems_toon_{k}:
    name: "Zendure EMS toon {k}"
    icon: mdi:chevron-down-circle-outline
""" for k in ("aansluiting", "planner", "teruglevering", "afschalen", "ev", "zonnecorrectie", "prijssturing",
              "grenzen", "regeling", "kalibratie") + tuple(OVERVIEW_KEYS)))
    S.append("""  zendure_ems_flash_schrijven:
    name: "Zendure EMS limieten naar flash schrijven (smartMode uit)"
    icon: mdi:memory
""")
    S.append("""  zendure_ems_net_omkeren:
    name: "Zendure EMS netmeter omkeren"
    icon: mdi:swap-vertical
  zendure_ems_laden_negatieve_prijs:
    name: "Zendure EMS laden bij negatieve prijs"
    icon: mdi:cash-minus
  zendure_ems_slim_laden:
    name: "Zendure EMS slim laden (goedkoopste uren)"
    icon: mdi:calendar-clock
  zendure_ems_korte_dips_negeren:
    name: "Zendure EMS korte dips negeren"
    icon: mdi:tumble-dryer
  zendure_ems_wachttijd_auto:
    name: "Zendure EMS wachttijd automatisch (volgens meterinterval)"
    icon: mdi:timer-cog-outline
  zendure_ems_verkoop_plannen:
    name: "Zendure EMS verkopen plannen (handelen)"
    icon: mdi:cash-clock
  zendure_ems_slim_ontladen:
    name: "Zendure EMS slim ontladen (duurste uren)"
    icon: mdi:calendar-star
  zendure_ems_teruglever_btw:
    name: "Zendure EMS btw over terugleververgoeding"
    icon: mdi:percent
  zendure_ems_bonus_overdag:
    name: "Zendure EMS bonus alleen overdag"
    icon: mdi:weather-sunset
  zendure_ems_afgeschaald:
    name: "Zendure EMS zonnepanelen afgeschaald (status)"
    icon: mdi:solar-power-variant-outline
  zendure_ems_zon_leren:
    name: "Zendure EMS zonnecorrectie leren"
    icon: mdi:weather-sunny-alert
  zendure_ems_standaard_ingesteld:
    name: "Zendure EMS standaardwaarden ingesteld"
    icon: mdi:check-circle-outline
""")
    for i in sets:
        S.append(f"""  zendure_set{i}_laden:
    name: "Zendure set{i} laden toegestaan"
    icon: mdi:battery-charging
  zendure_set{i}_ontladen:
    name: "Zendure set{i} ontladen toegestaan"
    icon: mdi:battery-minus
""")
    S.append("\ninput_number:\n")
    for k, name, mn, mx, st, unit, icon, _ in GLOBAL_NUMBERS:
        S.append(num(k, name, mn, mx, st, unit, icon))
    for i in sets:
        for k, name, mn, mx, st, unit, icon, _ in set_numbers(i):
            S.append(num(k, name, mn, mx, st, unit, icon))

    # ---------------- REST: one report per set (whole report kept as attributes)
    S.append("\nrest:\n")
    for i in sets:
        # a set without IP address asks Home Assistant itself for a small file: the sensor then exists (unknown)
        # instead of failing its setup and retrying with warnings in the log
        S.append(f"""  - resource_template: >-
      {{%- set ip = states('input_text.zendure_set{i}_ip') | trim -%}}
      {{{{ 'http://' ~ ip ~ '/properties/report' if ip not in ['', 'unknown', 'unavailable'] else 'http://127.0.0.1:8123/manifest.json' }}}}
    scan_interval: 5
    timeout: 4
    sensor:
      - name: "Zendure set{i} rapport"
        unique_id: zendure_ems_set{i}_rapport
        icon: mdi:home-battery-outline
        value_template: "{{{{ value_json.properties.electricLevel if value_json is mapping and value_json.properties is mapping else 'unknown' }}}}"
        json_attributes:
          - sn
          - product
          - properties
          - packData
""")
    # HomeWizard P1 (local API v1) every second: the HomeWizard integration only polls every 5 s, while a
    # DSMR 5 meter gives a new value every second. Without IP address it asks HA itself for a small file
    # (like a set without IP) and stays unavailable; the grid sensor that was filled in is then used.
    S.append("""  - resource_template: >-
      {%- set ip = states('input_text.zendure_ems_p1_ip') | trim -%}
      {{ 'http://' ~ ip ~ '/api/v1/data' if ip not in ['', 'unknown', 'unavailable'] else 'http://127.0.0.1:8123/manifest.json' }}
    scan_interval: 3600
    timeout: 2
    sensor:
      - name: "Zendure EMS P1 vermogen"
        unique_id: zendure_ems_p1_vermogen
        icon: mdi:transmission-tower
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        availability: "{{ value_json is mapping and value_json.active_power_w is number }}"
        value_template: "{{ value_json.active_power_w | round(0) if value_json is mapping and value_json.active_power_w is number else 0 }}"
""")

    # ---------------- rest_command
    S.append("""
rest_command:
  zendure_ems_write:
    url: "http://{{ ip }}/properties/write"
    method: POST
    content_type: "application/json"
    timeout: 4
    payload: '{{ {"sn": sn, "properties": props} | to_json }}'
""")

    # ---------------- template sensors
    S.append("\ntemplate:\n")
    # trigger based price plan
    S.append(f"""  - triggers:
      - trigger: time_pattern
        minutes: "/5"
      - trigger: homeassistant
        event: start
      - trigger: state
        entity_id:
          - input_select.zendure_ems_modus
          - input_boolean.zendure_ems_slim_laden
          - input_boolean.zendure_ems_slim_ontladen
          - input_boolean.zendure_ems_laden_negatieve_prijs
          - input_boolean.zendure_ems_verkoop_plannen
          - input_number.zendure_ems_laadprijs
          - input_number.zendure_ems_ontlaadprijs
          - input_number.zendure_ems_verkoopprijs
          - input_number.zendure_ems_min_spread
          - input_number.zendure_ems_slijtage
          - input_text.zendure_ems_prijssensor
          - input_text.zendure_ems_zon_vandaag
          - input_text.zendure_ems_zon_morgen
          - input_number.zendure_ems_zon_factor
          - input_select.zendure_ems_salderen
          - input_text.zendure_ems_terugleverprijs_sensor
          - input_number.zendure_ems_teruglever_vast
          - input_number.zendure_ems_teruglever_bonus
          - input_boolean.zendure_ems_teruglever_btw
          - input_boolean.zendure_ems_bonus_overdag
    actions:
      - variables:
          pp: {block(PRICE, sets, 12)}
    sensor:
      - name: "Zendure EMS prijsactie"
        unique_id: zendure_ems_prijsactie
        icon: >-
          {{{{ {{'zero': 'mdi:scale-balance', 'hold': 'mdi:pause-circle', 'grid_charge': 'mdi:transmission-tower-import',
              'sell': 'mdi:transmission-tower-export'}}.get(pp.action, 'mdi:help') }}}}
        state: "{{{{ pp.action }}}}"
        attributes:
          omschrijving: >-
            {{{{ {{'zero': 'Nul op de meter', 'hold': 'Accu vasthouden', 'grid_charge': 'Laden van het net',
              'sell': 'Verkopen aan het net'}}.get(pp.action, pp.action) }}}}
          reden: "{{{{ pp.reason }}}}"
          prijsbron: "{{{{ pp.source }}}}"
          nordpool_opslag: "{{{{ pp.np_add | default(none) }}}}"
          nordpool_opslag_tijd: "{{{{ pp.np_ats | default(0) }}}}"
          nordpool_opslag_hersteld: "{{{{ pp.np_fix | default(false) }}}}"
          aantal_prijsblokken: "{{{{ pp.n_slots }}}}"
          kwartieren_gepland: "{{{{ pp.n_quarters }}}}"
          laadvermogen: "{{{{ pp.charge_w }}}}"
          verkoopvermogen: "{{{{ pp.sell_w | default(0) }}}}"
          verkopen_gepland: "{{{{ pp.trade | default(false) }}}}"
          gepland_verkopen_kwh: "{{{{ pp.sell_kwh | default(0) }}}}"
          inkopen_voor_verkoop_kwh: "{{{{ pp.trade_buy_kwh | default(0) }}}}"
          verwachte_handelswinst: "{{{{ pp.trade_profit | default(0) }}}}"
          verkoopmomenten: "{{{{ (pp.sell_slots | default([])) | map('timestamp_custom', '%d-%m %H:%M') | list }}}}"
          kalibratie_nu: "{{{{ pp.calib_now | default(false) }}}}"
          kalibratie_kwartieren: "{{{{ (pp.calib_slots | default([])) | map('timestamp_custom', '%d-%m %H:%M') | list }}}}"
          kalibratie_tekort_kwh: "{{{{ pp.calib_deficit | default(0) }}}}"
          kalibratie_huis_kwh: "{{{{ pp.calib_house | default(0) }}}}"
          kalibratie_verkoop_kwh: "{{{{ pp.calib_sell | default(0) }}}}"
          kalibratie_klaar_om: "{{{{ (pp.calib_until | timestamp_custom('%d-%m %H:%M')) if pp.calib_until is defined else '' }}}}"
          kalibratie_netladen_kwh: "{{{{ pp.calib_grid | default(0) }}}}"
          kalibratie_niet_ingepland_kwh: "{{{{ pp.calib_short | default(0) }}}}"
          laadmomenten: "{{{{ pp.charge_slots | map('timestamp_custom', '%d-%m %H:%M') | list }}}}"
          gepland_netladen_kwh: "{{{{ pp.grid_kwh }}}}"
          verwachte_zon_kwh: "{{{{ pp.sun_kwh }}}}"
          verwacht_verbruik_kwh: "{{{{ pp.load_kwh }}}}"
          verwacht_tekort_kwh: "{{{{ pp.short_kwh }}}}"
          zonbron: "{{{{ pp.solar_source }}}}"
          verbruiksprofiel: "{{{{ pp.profile }}}}"
          kwh_tot_vol: "{{{{ pp.energy_to_full }}}}"
          kwh_bruikbaar: "{{{{ pp.usable_energy }}}}"
      - name: "Zendure EMS stroomprijs"
        unique_id: zendure_ems_stroomprijs
        icon: mdi:currency-eur
        unit_of_measurement: "€/kWh"
        availability: "{{{{ pp.price is not none }}}}"
        state: "{{{{ pp.price }}}}"
      - name: "Zendure EMS planning"
        unique_id: zendure_ems_planning
        icon: mdi:calendar-clock
        state: "{{{{ pp.upcoming | count }}}}"
        attributes:
          komende: "{{{{ pp.upcoming }}}}"
      - name: "Zendure EMS terugleverprijs"
        unique_id: zendure_ems_terugleverprijs
        icon: mdi:transmission-tower-export
        unit_of_measurement: "€/kWh"
        availability: "{{{{ pp.export_price is not none }}}}"
        state: "{{{{ pp.export_price }}}}"
        attributes:
          salderen: "{{{{ pp.salderen }}}}"
          opbouw: "{{{{ pp.export_source }}}}"
""")
    # learned consumption profile: 96 quarter-hour values (W), updated every quarter
    S.append(f"""  - triggers:
      - trigger: time_pattern
        minutes: "/15"
        seconds: 5
      - trigger: event
        event_type: zendure_ems_startprofiel
    actions:
      - variables:
          prof: {block(PROFILE, sets, 12)}
    sensor:
      - name: "Zendure EMS verbruiksprofiel"
        unique_id: zendure_ems_verbruiksprofiel
        unit_of_measurement: "W"
        icon: mdi:chart-bell-curve
        state: "{{{{ prof.avg }}}}"
        attributes:
          werkdag: "{{{{ prof.w }}}}"
          weekend: "{{{{ prof.e }}}}"
          metingen_werkdag: "{{{{ prof.nw }}}}"
          metingen_weekend: "{{{{ prof.ne }}}}"
          dagverbruik_werkdag_kwh: "{{{{ prof.kwh_w }}}}"
          dagverbruik_weekend_kwh: "{{{{ prof.kwh_e }}}}"
          geleerd: "werkdag {{{{ prof.learned_w }}}}/96, weekend {{{{ prof.learned_e }}}}/96 kwartieren"
""")
    # learning solar correction (forecast at 00:10 vs measured at 23:50)
    S.append(f"""  - triggers:
      - trigger: time
        at: "00:10:00"
        id: ochtend
      - trigger: time
        at: "23:50:00"
        id: avond
      - trigger: event
        event_type: zendure_ems_zonnecorrectie_reset
        id: reset
    actions:
      - variables:
          zc: {block(SOLAR_CORR, sets, 12)}
    sensor:
      - name: "Zendure EMS zonnecorrectie"
        unique_id: zendure_ems_zonnecorrectie
        unit_of_measurement: "%"
        icon: mdi:weather-sunny-alert
        state: "{{{{ (zc.factor * 100) | round(0) }}}}"
        attributes:
          factor: "{{{{ zc.factor }}}}"
          dagen: "{{{{ zc.dagen }}}}"
          verwacht_vandaag: "{{{{ zc.exp }}}}"
          historie: "{{{{ zc.hist }}}}"
          laatste: "{{{{ zc.msg }}}}"
""")
    # controller state, written by the control automation through an event.
    # Sensors with a unit stay out of the logbook; the status only logs changes.
    S.append("""  - triggers:
      - trigger: event
        event_type: zendure_ems_regelaar
    sensor:
      - name: "Zendure EMS regelaar"
        unique_id: zendure_ems_regelaar
        unit_of_measurement: "W"
        device_class: power
        icon: mdi:sine-wave
        state: "{{ trigger.event.data.cmd | float(0) }}"
        attributes:
          vorige_fout: "{{ trigger.event.data.err | float(99999) }}"
          afwijking: "{{ trigger.event.data.mis | float(0) }}"
          dip_sinds: "{{ trigger.event.data.dip | default(0) | float(0) }}"
          geschakeld: "{{ trigger.event.data.sw | default(0) | float(0) }}"
          actieve_sets: "{{ trigger.event.data.active | default('') }}"
          meterinterval: >-
            {%- set old = (this.attributes.get('meterinterval') if this is defined and this and this.attributes is defined else none) -%}
            {%- set d = trigger.event.data.iv | default(none) -%}
            {#- time between two changes of the meter value. A meter that sends every second still shows
                long gaps when the power stays the same, so the estimate follows the short gaps (the real
                interval) quickly and the long ones only slowly: it tracks the lower envelope. -#}
            {%- set d = ([[d, 0.5] | max, 15] | min) if d is number and d > 0 else none -%}
            {%- set iv = (d if old is not number else (old * 0.5 + d * 0.5 if d < old else old * 0.95 + d * 0.05))
                         if d is not none else old -%}
            {{ iv | round(2) if iv is number else none }}
          wachttijd_auto: >-
            {%- set old = (this.attributes.get('meterinterval') if this is defined and this and this.attributes is defined else none) -%}
            {%- set d = trigger.event.data.iv | default(none) -%}
            {#- time between two changes of the meter value. A meter that sends every second still shows
                long gaps when the power stays the same, so the estimate follows the short gaps (the real
                interval) quickly and the long ones only slowly: it tracks the lower envelope. -#}
            {%- set d = ([[d, 0.5] | max, 15] | min) if d is number and d > 0 else none -%}
            {%- set iv = (d if old is not number else (old * 0.5 + d * 0.5 if d < old else old * 0.95 + d * 0.05))
                         if d is not none else old -%}
            {{ (([[3, 2.5 + 0.7 * iv] | max, 10] | min) * 2) | round(0) / 2 if iv is number else none }}
          actie: "{{ trigger.event.data.action | default('') }}"
          setpoints: "{{ trigger.event.data.setpoints | default({}) }}"
          geschreven: "{{ trigger.event.data.written | default(0) | float(0) }}"
      - name: "Zendure EMS status"
        unique_id: zendure_ems_status
        icon: mdi:information-outline
        state: "{{ (trigger.event.data.status | default(''))[:250] }}"
""")
    # HomeWizard P1 every second, only when its IP address is filled in (the REST resource itself polls
    # hourly, so an installation without P1 does not make a request every second). The sensor shows which
    # meter the control uses; it only changes when the source changes.
    S.append("""  - triggers:
      - trigger: time_pattern
        seconds: "/1"
    actions:
      - if:
          - condition: template
            value_template: "{{ (states('input_text.zendure_ems_p1_ip') | trim) not in ['', 'unknown', 'unavailable'] }}"
        then:
          - action: homeassistant.update_entity
            continue_on_error: true
            target:
              entity_id: sensor.zendure_ems_p1_vermogen
    sensor:
      - name: "Zendure EMS netmeter-bron"
        unique_id: zendure_ems_netmeter_bron
        icon: mdi:transmission-tower
        state: >-
          {%- set p1ip = states('input_text.zendure_ems_p1_ip') | trim -%}
          {%- set p1l = expand('sensor.zendure_ems_p1_vermogen') if p1ip not in ['', 'unknown', 'unavailable'] else [] -%}
          {%- set p1ok = p1l | count > 0 and is_number(p1l[0].state)
                         and (now() - (p1l[0].last_reported if p1l[0].last_reported is defined and p1l[0].last_reported is not none
                                       else p1l[0].last_updated)).total_seconds() < 10 -%}
          {%- set gs = states('input_text.zendure_ems_netsensor') | trim -%}
          {{ 'HomeWizard P1 (elke seconde)' if p1ok else (gs if gs.startswith('sensor.') else 'Geen netmeter ingevuld') }}
""")
    # state based sensors
    S.append("  - sensor:\n")
    for i in sets:
        rep = f"sensor.zendure_set{i}_rapport"
        S.append(f"""      - name: "Zendure set{i} SOC"
        unique_id: zendure_ems_set{i}_soc
        unit_of_measurement: "%"
        device_class: battery
        state_class: measurement
        availability: "{{{{ has_value('{rep}') and (state_attr('{rep}', 'properties') or {{}}).electricLevel is number }}}}"
        state: "{{{{ (state_attr('{rep}', 'properties') or {{}}).electricLevel | default(none) }}}}"
      - name: "Zendure set{i} vermogen"
        unique_id: zendure_ems_set{i}_vermogen
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        icon: mdi:battery-charging-medium
        availability: "{{{{ has_value('{rep}') and state_attr('{rep}', 'properties') is mapping }}}}"
        state: >-
          {{%- set pr = state_attr('{rep}', 'properties') or {{}} -%}}
          {{%- if pr.gridInputPower is number and pr.outputHomePower is number -%}}
            {{{{ pr.gridInputPower - pr.outputHomePower }}}}
          {{%- else -%}}
            {{{{ (pr.outputPackPower | float(0)) - (pr.packInputPower | float(0)) }}}}
          {{%- endif -%}}
        attributes:
          uitleg: "+ = laden, - = ontladen (AC-zijde)"
      - name: "Zendure set{i} temperatuur"
        unique_id: zendure_ems_set{i}_temperatuur
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement
        availability: "{{{{ has_value('{rep}') and (state_attr('{rep}', 'properties') or {{}}).hyperTmp is number }}}}"
        state: >-
          {{%- set t = (state_attr('{rep}', 'properties') or {{}}).hyperTmp | float(0) -%}}
          {{{{ ((t - 2731) / 10) | round(1) if t > 1000 else t }}}}
        attributes:
          accupacks: >-
            {{%- set o = namespace(l=[]) -%}}
            {{%- for pk in state_attr('{rep}', 'packData') or [] -%}}
              {{%- set mt = pk.maxTemp | float(0) -%}}
              {{%- set o.l = o.l + [{{'sn': pk.sn, 'soc': pk.socLevel, 'temp': ((mt - 2731) / 10) | round(1) if mt > 1000 else mt}}] -%}}
            {{%- endfor -%}}
            {{{{ o.l }}}}
      - name: "Zendure set{i} smartMode"
        unique_id: zendure_ems_set{i}_smartmode
        icon: mdi:memory
        availability: "{{{{ has_value('{rep}') and (state_attr('{rep}', 'properties') or {{}}).smartMode is number }}}}"
        state: "{{{{ 'RAM' if (state_attr('{rep}', 'properties') or {{}}).smartMode == 1 else 'flash' }}}}"
      - name: "Zendure set{i} modus"
        unique_id: zendure_ems_set{i}_modus
        icon: mdi:battery-sync
        availability: "{{{{ has_value('sensor.zendure_set{i}_vermogen') }}}}"
        state: >-
          {{%- set p = states('sensor.zendure_set{i}_vermogen') | float(0) -%}}
          {{{{ 'Opladen' if p > 20 else ('Ontladen' if p < -20 else 'Standby') }}}}
        attributes:
          uitleg: "Onder 20 W telt als Standby, zodat meetruis rond 0 W geen relaisschakeling telt"
      - name: "Zendure set{i} relais schakelingen vandaag"
        unique_id: zendure_ems_set{i}_relais_vandaag
        icon: mdi:swap-vertical-bold
        state: >-
          {{%- set t = states('sensor.zendure_set{i}_relais_opladen_vandaag') | int(0)
                    + states('sensor.zendure_set{i}_relais_ontladen_vandaag') | int(0) - 1 -%}}
          {{{{ t if t > 0 else 0 }}}}
""")
    soc_ids = ", ".join(f"'{i}'" for i in sets)
    S.append(f"""      - name: "Zendure EMS netvermogen"
        unique_id: zendure_ems_netvermogen
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        icon: mdi:transmission-tower
        availability: {block(GRID + "{{ g.w is not none }}", sets, 10)}
        state: {block(GRID + "{{ g.w | round(0) if g.w is not none else none }}", sets, 10)}
      - name: "Zendure EMS netmeting"
        unique_id: zendure_ems_netmeting
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        icon: mdi:transmission-tower
        availability: {block(GRID + "{{ g.raw is not none }}", sets, 10)}
        state: {block(GRID + "{{ g.raw | round(0) if g.raw is not none else none }}", sets, 10)}
      - name: "Zendure EMS actief profiel"
        unique_id: zendure_ems_actief_profiel
        icon: mdi:tune-variant
        state: {block(PROFILE_MATCH, sets, 10)}
      - name: "Zendure EMS EV-vermogen"
        unique_id: zendure_ems_ev_vermogen
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        icon: mdi:car-electric
        state: {block(EV_NOW, sets, 10)}
      - name: "Zendure EMS zonneproductie"
        unique_id: zendure_ems_zonneproductie
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        icon: mdi:solar-power
        state: {block(SOLAR_NOW, sets, 10)}
      - name: "Zendure EMS huisverbruik"
        unique_id: zendure_ems_huisverbruik
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        icon: mdi:home-lightning-bolt
        availability: {block(GRID + "{{ g.w is not none }}", sets, 10)}
        state: {block(GRID + HOUSE, sets, 10)}
      - name: "Zendure EMS accuvermogen"
        unique_id: zendure_ems_accuvermogen
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        icon: mdi:home-battery
        state: >-
          {{%- set o = namespace(w=0) -%}}
          {{%- for e in [{", ".join(f"'sensor.zendure_set{i}_vermogen'" for i in sets)}] -%}}
            {{%- set o.w = o.w + (states(e) | float(0)) -%}}
          {{%- endfor -%}}
          {{{{ o.w | round(0) }}}}
      - name: "Zendure EMS laadvermogen"
        unique_id: zendure_ems_laadvermogen
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        state: "{{{{ [states('sensor.zendure_ems_accuvermogen') | float(0), 0] | max }}}}"
      - name: "Zendure EMS ontlaadvermogen"
        unique_id: zendure_ems_ontlaadvermogen
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        state: "{{{{ [0 - states('sensor.zendure_ems_accuvermogen') | float(0), 0] | max }}}}"
      - name: "Zendure EMS gemiddelde SOC"
        unique_id: zendure_ems_gemiddelde_soc
        unit_of_measurement: "%"
        device_class: battery
        state_class: measurement
        state: >-
          {{%- set o = namespace(e=0, c=0) -%}}
          {{%- for i in [{soc_ids}] -%}}
            {{%- set pr = state_attr('sensor.zendure_set' ~ i ~ '_rapport', 'properties') -%}}
            {{%- if has_value('sensor.zendure_set' ~ i ~ '_rapport') and pr is mapping and pr.electricLevel is number -%}}
              {{%- set capm = states('input_number.zendure_set' ~ i ~ '_capaciteit') | float(0) -%}}
              {{%- set cap = capm if capm > 0 else ((pr.packNum | int(1)) if pr.packNum is number and pr.packNum > 0 else 1) * (states('input_number.zendure_ems_kwh_per_pack') | float(2.88)) -%}}
              {{%- set o.e = o.e + pr.electricLevel * cap -%}}
              {{%- set o.c = o.c + cap -%}}
            {{%- endif -%}}
          {{%- endfor -%}}
          {{{{ (o.e / o.c) | round(1) if o.c > 0 else none }}}}
        availability: >-
          {{{{ {" or ".join(f"has_value('sensor.zendure_set{i}_soc')" for i in sets)} }}}}
      - name: "Zendure EMS opgeslagen energie"
        unique_id: zendure_ems_opgeslagen_energie
        unit_of_measurement: "kWh"
        device_class: energy_storage
        state_class: measurement
        state: >-
          {{%- set o = namespace(e=0) -%}}
          {{%- for i in [{soc_ids}] -%}}
            {{%- set pr = state_attr('sensor.zendure_set' ~ i ~ '_rapport', 'properties') -%}}
            {{%- if has_value('sensor.zendure_set' ~ i ~ '_rapport') and pr is mapping and pr.electricLevel is number -%}}
              {{%- set capm = states('input_number.zendure_set' ~ i ~ '_capaciteit') | float(0) -%}}
              {{%- set cap = capm if capm > 0 else ((pr.packNum | int(1)) if pr.packNum is number and pr.packNum > 0 else 1) * (states('input_number.zendure_ems_kwh_per_pack') | float(2.88)) -%}}
              {{%- set o.e = o.e + pr.electricLevel / 100 * cap -%}}
            {{%- endif -%}}
          {{%- endfor -%}}
          {{{{ o.e | round(2) }}}}
""")

    # ---------------- energy counters for the Energy dashboard
    S.append("""
  - switch:
      - name: "Zendure EMS EV laden van het net"
        unique_id: zendure_ems_ev_laden_van_het_net
        icon: mdi:ev-station
        availability: "{{ (states('input_text.zendure_ems_ev_actief') | trim).split('.')[0] in ['input_boolean', 'switch'] }}"
        state: "{{ is_state(states('input_text.zendure_ems_ev_actief') | trim, 'on') }}"
        turn_on:
          - action: homeassistant.turn_on
            target:
              entity_id: "{{ states('input_text.zendure_ems_ev_actief') | trim }}"
        turn_off:
          - action: homeassistant.turn_off
            target:
              entity_id: "{{ states('input_text.zendure_ems_ev_actief') | trim }}"
    binary_sensor:
      - name: "Zendure EMS EV laadt"
        unique_id: zendure_ems_ev_laadt
        device_class: battery_charging
        icon: mdi:car-electric
        delay_off:
          seconds: 30
        state: "{{ states('sensor.zendure_ems_ev_vermogen') | float(0) > 50 }}"
    sensor:
      - name: "Zendure EMS EV-laadtijd vandaag"
        unique_id: zendure_ems_ev_laadtijd_vandaag
        unit_of_measurement: "min"
        device_class: duration
        icon: mdi:timer-outline
        state: "{{ (states('sensor.zendure_ems_ev_laadtijd_vandaag_uren') | float(0) * 60) | round(0) }}"
  - triggers:
      - trigger: state
        entity_id: sensor.zendure_ems_ev_energie
        id: energie
      - trigger: time
        at: "00:00:00"
        id: reset
    sensor:
      - name: "Zendure EMS EV-kosten vandaag"
        unique_id: zendure_ems_ev_kosten_vandaag
        unit_of_measurement: "€"
        device_class: monetary
        state_class: total
        icon: mdi:cash
        state: >-
          {%- set old = (this.state | float(0)) if this is defined and this.state is defined else 0 -%}
          {%- if trigger.id == 'reset' -%}
            0
          {%- else -%}
            {%- set d = ((trigger.to_state.state | float(0)) - (trigger.from_state.state | float(0)))
                        if trigger.from_state is not none and trigger.to_state is not none else 0 -%}
            {%- set d = d if 0 < d < 5 else 0 -%}
            {{ (old + d * (states('sensor.zendure_ems_stroomprijs') | float(0))) | round(3) }}
          {%- endif -%}
""")
    # per set: is the set idle (both limits 0)? used for the standby after inactivity
    S.append("  - binary_sensor:\n")
    for i in sets:
        rep_ = f"sensor.zendure_set{i}_rapport"
        S.append(f"""      - name: "Zendure set{i} inactief"
        unique_id: zendure_ems_set{i}_inactief
        icon: mdi:sleep
        availability: "{{{{ has_value('{rep_}') and state_attr('{rep_}', 'properties') is mapping }}}}"
        state: >-
          {{%- set pr = state_attr('{rep_}', 'properties') or {{}} -%}}
          {{{{ (pr.inputLimit | float(0)) == 0 and (pr.outputLimit | float(0)) == 0 if pr.acMode is number else false }}}}
""")
    # savings: cost of charging and value of discharging, weighted with the price of that moment
    S.append("""  - triggers:
      - trigger: state
        entity_id: sensor.zendure_ems_energie_geladen
        id: laden
      - trigger: state
        entity_id: sensor.zendure_ems_energie_ontladen
        id: ontladen
    variables:
      delta: >-
        {%- set a = trigger.from_state.state | float(none) if trigger.from_state else none -%}
        {%- set b = trigger.to_state.state | float(none) if trigger.to_state else none -%}
        {{ (b - a) if (a is not none and b is not none and b >= a and (b - a) < 5) else 0 }}
      prijs: >-
        {#- from the grid: import price; solar surplus or selling to the grid: feed-in price -#}
        {%- set imp = states('sensor.zendure_ems_stroomprijs') | float(none) -%}
        {%- set exp = states('sensor.zendure_ems_terugleverprijs') | float(none) -%}
        {%- set net = states('sensor.zendure_ems_netmeting') | float(0) -%}
        {%- if trigger.id == 'laden' -%}
          {{ imp if net > 50 or exp is none else exp }}
        {%- else -%}
          {{ exp if net < -50 and exp is not none else imp }}
        {%- endif -%}
    sensor:
      - name: "Zendure EMS kosten laden"
        unique_id: zendure_ems_kosten_laden
        unit_of_measurement: "EUR"
        device_class: monetary
        state_class: total
        icon: mdi:cash-minus
        state: >-
          {%- set oud = this.state | float(0) if this is defined and this.state is defined else 0 -%}
          {{ (oud + (delta * prijs if (trigger.id == 'laden' and prijs is number) else 0)) | round(4) }}
      - name: "Zendure EMS waarde ontladen"
        unique_id: zendure_ems_waarde_ontladen
        unit_of_measurement: "EUR"
        device_class: monetary
        state_class: total
        icon: mdi:cash-plus
        state: >-
          {%- set oud = this.state | float(0) if this is defined and this.state is defined else 0 -%}
          {{ (oud + (delta * prijs if (trigger.id == 'ontladen' and prijs is number) else 0)) | round(4) }}
  - sensor:
      - name: "Zendure EMS besparing teller"
        unique_id: zendure_ems_besparing_teller
        unit_of_measurement: "EUR"
        device_class: monetary
        state_class: total
        icon: mdi:piggy-bank-outline
        state: >-
          {{ (states('sensor.zendure_ems_waarde_ontladen') | float(0)
              - states('sensor.zendure_ems_kosten_laden') | float(0)) | round(2) }}
      - name: "Zendure EMS besparing totaal"
        unique_id: zendure_ems_besparing_totaal
        unit_of_measurement: "EUR"
        device_class: monetary
        icon: mdi:piggy-bank
        state: >-
          {{ (states('sensor.zendure_ems_waarde_ontladen') | float(0) - states('sensor.zendure_ems_kosten_laden') | float(0)
              + states('input_number.zendure_ems_besparing_start') | float(0)) | round(2) }}
      - name: "Zendure EMS besparing vandaag"
        unique_id: zendure_ems_besparing_vandaag
        unit_of_measurement: "EUR"
        device_class: monetary
        icon: mdi:piggy-bank
        state: >-
          {{ (states('sensor.zendure_ems_waarde_ontladen_vandaag') | float(0)
              - states('sensor.zendure_ems_kosten_laden_vandaag') | float(0)) | round(2) }}
      - name: "Zendure EMS besparing maand"
        unique_id: zendure_ems_besparing_maand
        unit_of_measurement: "EUR"
        device_class: monetary
        icon: mdi:piggy-bank
        state: >-
          {{ (states('sensor.zendure_ems_waarde_ontladen_maand') | float(0)
              - states('sensor.zendure_ems_kosten_laden_maand') | float(0)) | round(2) }}
      - name: "Zendure EMS gemiddelde laadprijs"
        unique_id: zendure_ems_gem_laadprijs
        unit_of_measurement: "EUR/kWh"
        icon: mdi:cash-clock
        state: >-
          {%- set kwh = states('sensor.zendure_ems_geladen_maand') | float(0) -%}
          {{ (states('sensor.zendure_ems_kosten_laden_maand') | float(0) / kwh) | round(3) if kwh > 0.05 else 0 }}
      - name: "Zendure EMS gemiddelde ontlaadwaarde"
        unique_id: zendure_ems_gem_ontlaadwaarde
        unit_of_measurement: "EUR/kWh"
        icon: mdi:cash-check
        state: >-
          {%- set kwh = states('sensor.zendure_ems_ontladen_maand') | float(0) -%}
          {{ (states('sensor.zendure_ems_waarde_ontladen_maand') | float(0) / kwh) | round(3) if kwh > 0.05 else 0 }}
""")
    # smoothed values for the energy-flow picture only (the control keeps using the fast values)
    S.append("""  - triggers:
      - trigger: time_pattern
        seconds: "/5"
    sensor:
""")
    for key, naam, bron in (("net", "net", "sensor.zendure_ems_netvermogen"), ("huis", "huisverbruik", "sensor.zendure_ems_huisverbruik")):
        S.append(f"""      - name: "Zendure EMS grafiek {naam}"
        unique_id: zendure_ems_grafiek_{key}
        unit_of_measurement: W
        device_class: power
        state_class: measurement
        icon: mdi:chart-line
        availability: "{{{{ is_number(states('{bron}')) }}}}"
        state: "{{{{ states('{bron}') | float(0) | round(0) }}}}"
""")
    for key, naam, bron, dode in (("net", "net", "sensor.zendure_ems_netmeting", 40),
                                  ("zon", "zon", "sensor.zendure_ems_zonneproductie", 25),
                                  ("huis", "huis", "sensor.zendure_ems_huisverbruik", 25),
                                  ("accu", "accu", "sensor.zendure_ems_accuvermogen", 40),
                                  ("ev", "EV", "sensor.zendure_ems_ev_vermogen", 50)):
        S.append(f"""      - name: "Zendure EMS weergave {naam}"
        unique_id: zendure_ems_weergave_{key}
        unit_of_measurement: W
        device_class: power
        icon: mdi:chart-bell-curve-cumulative
        state: >-
          {{% set n = states('{bron}') | float(0) %}}
          {{% set o = (this.attributes.get('ruw', n) | float(n)) if this is defined and this.attributes is defined else n %}}
          {{% set v = o * 0.65 + n * 0.35 %}}
          {{{{ 0 if v | abs < {dode} else ((v / 10) | round(0) * 10) | int }}}}
        attributes:
          ruw: >-
            {{% set n = states('{bron}') | float(0) %}}
            {{% set o = (this.attributes.get('ruw', n) | float(n)) if this is defined and this.attributes is defined else n %}}
            {{{{ (o * 0.65 + n * 0.35) | round(1) }}}}
""")
    # calibration status (non-trigger: follows now() once a minute)
    S.append(f"""  - sensor:
      - name: "Zendure EMS kalibratie"
        unique_id: zendure_ems_kalibratie
        icon: mdi:battery-sync
        state: {block(CALIB_STATUS, sets, 10)}
""")
    for i in sets:
        S.append(f"""      - name: "Zendure set{i} dagen sinds vol"
        unique_id: zendure_set{i}_dagen_sinds_vol
        unit_of_measurement: dagen
        icon: mdi:battery-clock
        availability: "{{{{ (state_attr('input_datetime.zendure_set{i}_laatst_vol', 'timestamp') | float(0)) > 946684800 }}}}"
        state: >-
          {{%- set t0 = as_timestamp(now().replace(hour=0, minute=0, second=0, microsecond=0)) -%}}
          {{%- set lv = state_attr('input_datetime.zendure_set{i}_laatst_vol', 'timestamp') | float(0) -%}}
          {{{{ (((t0 - lv) / 86400) | round(0, 'ceil') | int) if lv < t0 else 0 }}}}
""")
    S.append("""
sensor:
""" + "".join(f"""  - platform: history_stats
    name: "Zendure set{i} relais opladen vandaag"
    unique_id: zendure_ems_set{i}_relais_opladen_vandaag
    entity_id: sensor.zendure_set{i}_modus
    state: "Opladen"
    type: count
    start: "{{{{ today_at() }}}}"
    end: "{{{{ now() }}}}"
  - platform: history_stats
    name: "Zendure set{i} relais ontladen vandaag"
    unique_id: zendure_ems_set{i}_relais_ontladen_vandaag
    entity_id: sensor.zendure_set{i}_modus
    state: "Ontladen"
    type: count
    start: "{{{{ today_at() }}}}"
    end: "{{{{ now() }}}}"
""" for i in sets) + """  - platform: history_stats
    name: "Zendure EMS EV-laadtijd vandaag uren"
    unique_id: zendure_ems_ev_laadtijd_vandaag_uren
    entity_id: binary_sensor.zendure_ems_ev_laadt
    state: "on"
    type: time
    start: "{{ today_at() }}"
    end: "{{ now() }}"
  - platform: integration
    source: sensor.zendure_ems_ev_vermogen
    name: "Zendure EMS EV-energie"
    unique_id: zendure_ems_ev_energie
    unit_prefix: k
    round: 3
    method: left
    max_sub_interval:
      minutes: 1
  - platform: integration
    source: sensor.zendure_ems_zonneproductie
    name: "Zendure EMS zonne-energie"
    unique_id: zendure_ems_zonne_energie
    unit_prefix: k
    round: 3
    method: left
    max_sub_interval:
      minutes: 1
  - platform: statistics
    name: "Zendure EMS huisverbruik kwartiergemiddelde"
    unique_id: zendure_ems_huisverbruik_kwartier
    entity_id: sensor.zendure_ems_huisverbruik
    state_characteristic: mean
    max_age:
      minutes: 15
    sampling_size: 5000
    precision: 0
  - platform: integration
    source: sensor.zendure_ems_laadvermogen
    name: "Zendure EMS energie geladen"
    unique_id: zendure_ems_energie_geladen
    unit_prefix: k
    round: 3
    method: left
    max_sub_interval:
      minutes: 1
  - platform: integration
    source: sensor.zendure_ems_ontlaadvermogen
    name: "Zendure EMS energie ontladen"
    unique_id: zendure_ems_energie_ontladen
    unit_prefix: k
    round: 3
    method: left
    max_sub_interval:
      minutes: 1
""")

    # ---------------- automations
    set_defaults = []
    for k, _n, _a, _b, _c, _u, _i, d in GLOBAL_NUMBERS:
        set_defaults.append(
            f"""          - action: input_number.set_value
            target:
              entity_id: input_number.{k}
            data:
              value: {d}
"""
        )
    for i in sets:
        for k, _n, _a, _b, _c, _u, _i, d in set_numbers(i):
            set_defaults.append(
                f"""          - action: input_number.set_value
            target:
              entity_id: input_number.{k}
            data:
              value: {d}
"""
            )
    bool_on = [f"input_boolean.zendure_ems_toon_{k}" for k in OVERVIEW_KEYS] + ["input_boolean.zendure_ems_laden_negatieve_prijs", "input_boolean.zendure_ems_zon_leren",
               "input_boolean.zendure_ems_teruglever_btw", "input_boolean.zendure_ems_bonus_overdag",
               "input_boolean.zendure_ems_wachttijd_auto"] + [
        f"input_boolean.zendure_set{i}_{x}" for i in sets for x in ("laden", "ontladen")
    ]
    S.append("""
utility_meter:
  zendure_ems_ev_energie_vandaag:
    name: "Zendure EMS EV-energie vandaag"
    unique_id: zendure_ems_ev_energie_vandaag
    source: sensor.zendure_ems_ev_energie
    cycle: daily
  zendure_ems_zonne_energie_vandaag:
    name: "Zendure EMS zonne-energie vandaag"
    unique_id: zendure_ems_zonne_energie_vandaag
    source: sensor.zendure_ems_zonne_energie
    cycle: daily
  zendure_ems_kosten_laden_vandaag:
    name: "Zendure EMS kosten laden vandaag"
    unique_id: zendure_ems_kosten_laden_vandaag
    source: sensor.zendure_ems_kosten_laden
    cycle: daily
  zendure_ems_kosten_laden_maand:
    name: "Zendure EMS kosten laden maand"
    unique_id: zendure_ems_kosten_laden_maand
    source: sensor.zendure_ems_kosten_laden
    cycle: monthly
  zendure_ems_waarde_ontladen_vandaag:
    name: "Zendure EMS waarde ontladen vandaag"
    unique_id: zendure_ems_waarde_ontladen_vandaag
    source: sensor.zendure_ems_waarde_ontladen
    cycle: daily
  zendure_ems_waarde_ontladen_maand:
    name: "Zendure EMS waarde ontladen maand"
    unique_id: zendure_ems_waarde_ontladen_maand
    source: sensor.zendure_ems_waarde_ontladen
    cycle: monthly
  zendure_ems_geladen_maand:
    name: "Zendure EMS geladen maand"
    unique_id: zendure_ems_geladen_maand
    source: sensor.zendure_ems_energie_geladen
    cycle: monthly
  zendure_ems_ontladen_maand:
    name: "Zendure EMS ontladen maand"
    unique_id: zendure_ems_ontladen_maand
    source: sensor.zendure_ems_energie_ontladen
    cycle: monthly
""")
    S.append(f"""
script:
  zendure_ems_profiel_opslaan:
    alias: "Zendure EMS: huidige instellingen opslaan als mijn profiel"
    icon: mdi:content-save-cog
    mode: single
    fields:
      slot:
        name: Profiel
        description: "1 of 2"
        default: 1
        selector:
          number:
            min: 1
            max: 2
            mode: box
    sequence:
      - variables:
          nu: {block(PROFILE_NOW, sets, 12)}
      - action: input_text.set_value
        target:
          entity_id: "input_text.zendure_ems_mijn_profiel_{{{{ slot | int(1) }}}}"
        data:
          value: "{{{{ nu if nu is string else (nu | to_json) }}}}"
      - action: logbook.log
        data:
          name: "Zendure EMS"
          message: "Huidige instellingen opgeslagen als mijn profiel {{{{ slot | int(1) }}}}"
  zendure_ems_startprofiel:
    alias: "Zendure EMS: startprofiel uit historie opbouwen"
    icon: mdi:history
    description: >-
      Leest de uurgemiddelden van netmeter, accu's en zonneproductie uit de statistiek van Home Assistant
      en bouwt daaruit de verbruiksprofielen voor werkdagen en weekend. Overschrijft het geleerde profiel.
    mode: single
    fields:
      dagen:
        name: Aantal dagen terug
        description: Hoeveel dagen historie gebruiken (7 tot 90).
        default: 28
        selector:
          number:
            min: 7
            max: 90
            step: 1
    sequence:
      - variables:
          n: "{{{{ [[dagen | default(28) | int(28), 7] | max, 90] | min }}}}"
          ids: >-
            {{{{ {{'grid': states('input_text.zendure_ems_netsensor') | trim,
                 'accu': 'sensor.zendure_ems_accuvermogen',
                 'solar': states('input_text.zendure_ems_zonproductie') | trim,
                 'ev': states('input_text.zendure_ems_ev_sensor') | trim,
                 'acc_in': states('input_text.zendure_ems_historie_laden') | trim,
                 'acc_out': states('input_text.zendure_ems_historie_ontladen') | trim}} }}}}
          fallback: "{{{{ states('input_number.zendure_ems_verwacht_verbruik') | float(400) }}}}"
      - action: recorder.get_statistics
        data:
          statistic_ids: >-
            {{{{ [ids.grid, ids.accu] + ([ids.solar] if ids.solar.startswith('sensor.') else [])
                 + ([ids.ev] if ids.ev.startswith('sensor.') else [])
                 + ([ids.acc_in] if ids.acc_in.startswith('sensor.') else [])
                 + ([ids.acc_out] if ids.acc_out.startswith('sensor.') else []) }}}}
          start_time: "{{{{ (now() - timedelta(days=n)).replace(minute=0, second=0, microsecond=0).isoformat() }}}}"
          end_time: "{{{{ now().replace(minute=0, second=0, microsecond=0).isoformat() }}}}"
          period: hour
          types:
            - mean
          units:
            power: W
        response_variable: stats
      - variables:
          prof: {block(START_PROFILE, sets, 12)}
      - if:
          - condition: template
            value_template: "{{{{ prof.uren < 24 }}}}"
        then:
          - action: persistent_notification.create
            data:
              notification_id: zendure_ems_startprofiel
              title: "Zendure EMS: startprofiel niet opgebouwd"
              message: >-
                Te weinig historie gevonden ({{{{ prof.uren }}}} uur) voor {{{{ ids.grid }}}}. De netmeter-sensor
                moet een state_class hebben (meestal measurement) en minstens een dag in de statistiek staan.
          - stop: "Te weinig historie"
      - event: zendure_ems_startprofiel
        event_data:
          werkdag: "{{{{ prof.werkdag }}}}"
          weekend: "{{{{ prof.weekend }}}}"
          metingen_werkdag: "{{{{ prof.metingen_werkdag }}}}"
          metingen_weekend: "{{{{ prof.metingen_weekend }}}}"
      - action: persistent_notification.create
        data:
          notification_id: zendure_ems_startprofiel
          title: "Zendure EMS: startprofiel opgebouwd"
          message: >-
            Uit {{{{ prof.uren }}}} uur historie ({{{{ n }}}} dagen): werkdag {{{{ prof.kwh_w }}}} kWh per dag,
            weekend {{{{ prof.kwh_e }}}} kWh per dag. Het profiel leert vanaf nu gewoon verder.
            {{{{ '' if ids.solar.startswith('sensor.') else 'Let op: er is geen zonneproductie-sensor ingevuld; overdag is het verbruik na aftrek van de zon gebruikt.' }}}}

  zendure_ems_zonnecorrectie_reset:
    alias: "Zendure EMS: zonnecorrectie opnieuw leren"
    icon: mdi:restore
    mode: single
    sequence:
      - event: zendure_ems_zonnecorrectie_reset
""")
    soc_helpers = "\n".join(
        f"          - input_number.zendure_set{i}_{x}" for i in sets for x in ("min_soc", "max_soc")
    )
    S.append(f"""
automation:
  - id: zendure_ems_regeling
    alias: "Zendure EMS: regeling"
    description: >-
      Nul op de meter en prijsacties. Rekent het vermogen per set uit bij elke nieuwe meterwaarde
      (zodra de vorige opdracht is uitgevoerd) en in elk geval elke 5 s.
    mode: single
    max_exceeded: silent
    triggers:
      - trigger: time_pattern
        seconds: "/5"
        id: tijd
      - trigger: state
        entity_id: sensor.zendure_ems_netvermogen
        id: meter
    conditions:
      - condition: state
        entity_id: input_boolean.zendure_ems_standaard_ingesteld
        state: "on"
      - condition: not
        conditions:
          - condition: state
            entity_id: input_select.zendure_ems_modus
            state: "Niet aansturen"
      - condition: template
        value_template: {block(PRECHECK, sets, 10)}
    actions:
      - variables:
          plan: {block(CONTROL, sets, 12)}
      - repeat:
          for_each: "{{{{ plan.writes }}}}"
          sequence:
            - action: rest_command.zendure_ems_write
              continue_on_error: true
              data:
                ip: "{{{{ repeat.item.ip }}}}"
                sn: "{{{{ repeat.item.sn }}}}"
                props: "{{{{ repeat.item.props }}}}"
      - event: zendure_ems_regelaar
        event_data:
          cmd: "{{{{ plan.cmd }}}}"
          err: "{{{{ plan.err }}}}"
          mis: "{{{{ plan.mis }}}}"
          dip: "{{{{ plan.dip }}}}"
          sw: "{{{{ plan.sw }}}}"
          active: "{{{{ plan.active }}}}"
          status: "{{{{ plan.status }}}}"
          action: "{{{{ plan.action }}}}"
          setpoints: "{{{{ plan.sp }}}}"
          iv: >-
            {{{{ ((trigger.to_state.last_changed - trigger.from_state.last_changed).total_seconds() | round(2))
                 if trigger is defined and trigger.id is defined and trigger.id == 'meter'
                    and trigger.from_state is defined and trigger.from_state and trigger.to_state
                    and is_number(trigger.from_state.state) and is_number(trigger.to_state.state)
                 else none }}}}
          written: >-
            {{{{ plan.now if plan.writes | count > 0
                 else state_attr('sensor.zendure_ems_regelaar', 'geschreven') | float(0) }}}}

  - id: zendure_ems_vrijgeven
    alias: "Zendure EMS: sets op 0 W bij vrijgeven of afsluiten"
    description: "Bij modus 'Niet aansturen' of het stoppen van Home Assistant krijgen alle sets 0 W."
    mode: queued
    triggers:
      - trigger: state
        entity_id: input_select.zendure_ems_modus
        to: "Niet aansturen"
      - trigger: homeassistant
        event: shutdown
    actions:
      - repeat:
          for_each: {block(STANDBY_LIST, sets, 12)}
          sequence:
            - action: rest_command.zendure_ems_write
              continue_on_error: true
              data:
                ip: "{{{{ repeat.item.ip }}}}"
                sn: "{{{{ repeat.item.sn }}}}"
                props:
                  acMode: 2
                  outputLimit: 0
                  smartMode: "{{{{ 0 if is_state('input_boolean.zendure_ems_flash_schrijven', 'on') else 1 }}}}"
      - event: zendure_ems_regelaar
        event_data:
          cmd: 0
          err: 99999
          mis: 0
          active: ""
          status: "{{{{ 'Home Assistant stopt: sets op 0 W' if trigger.platform == 'homeassistant' else 'Niet aansturen' }}}}"
          action: "none"
          setpoints: {{}}

  - id: zendure_ems_soc_grenzen
    alias: "Zendure EMS: SOC-grenzen naar de sets schrijven"
    description: "Schrijft min/max SOC naar de sets (blijft bewaard na herstart). Alleen als ze afwijken."
    mode: queued
    triggers:
      - trigger: state
        entity_id:
{soc_helpers}
        for:
          seconds: 5
      - trigger: time_pattern
        minutes: "/10"
    conditions:
      - condition: state
        entity_id: input_boolean.zendure_ems_standaard_ingesteld
        state: "on"
    actions:
      - repeat:
          for_each: {block(SOC_LIMITS, sets, 12)}
          sequence:
            - action: rest_command.zendure_ems_write
              continue_on_error: true
              data:
                ip: "{{{{ repeat.item.ip }}}}"
                sn: "{{{{ repeat.item.sn }}}}"
                props: "{{{{ repeat.item.props }}}}"

  - id: zendure_ems_standaardwaarden
    alias: "Zendure EMS: standaardwaarden instellen"
    description: "Zet eenmalig alle instellingen op hun standaardwaarde. Zet de schakelaar 'standaardwaarden ingesteld' uit om opnieuw te beginnen."
    mode: single
    triggers:
      - trigger: homeassistant
        event: start
      - trigger: state
        entity_id: input_boolean.zendure_ems_standaard_ingesteld
        to: "off"
    conditions:
      - condition: state
        entity_id: input_boolean.zendure_ems_standaard_ingesteld
        state: "off"
    actions:
      - action: input_select.select_option
        target:
          entity_id: input_select.zendure_ems_modus
        data:
          option: "Niet aansturen"
      - parallel:
{"".join(set_defaults)}      - action: input_text.set_value
        target:
          entity_id: input_text.zendure_ems_zon_vandaag
        data:
          value: >-
            {{{{ 'sensor.energy_production_today_remaining'
                 if expand('sensor.energy_production_today_remaining') | count > 0
                 else states('input_text.zendure_ems_zon_vandaag') | replace('unknown', '') }}}}
      - action: input_text.set_value
        target:
          entity_id: input_text.zendure_ems_zon_morgen
        data:
          value: >-
            {{{{ 'sensor.energy_production_tomorrow'
                 if expand('sensor.energy_production_tomorrow') | count > 0
                 else states('input_text.zendure_ems_zon_morgen') | replace('unknown', '') }}}}
      - action: input_boolean.turn_on
        target:
          entity_id:
{chr(10).join("            - " + b for b in bool_on)}
      - action: input_boolean.turn_off
        target:
          entity_id:
            - input_boolean.zendure_ems_slim_laden
            - input_boolean.zendure_ems_slim_ontladen
            - input_boolean.zendure_ems_net_omkeren
      - action: input_text.set_value
        target:
          entity_id: input_text.zendure_ems_versie
        data:
          value: "{VERSION}"
      - action: input_boolean.turn_on
        target:
          entity_id: input_boolean.zendure_ems_standaard_ingesteld

  - id: zendure_ems_update
    alias: "Zendure EMS: velden na een update instellen"
    description: >-
      Na een update krijgen alleen de nieuwe velden eenmalig hun standaardwaarde (een nieuw veld begint
      anders op zijn minimum). Bestaande instellingen blijven ongewijzigd.
    mode: single
    triggers:
      - trigger: homeassistant
        event: start
      - trigger: time_pattern
        minutes: "/10"
    conditions:
      - condition: state
        entity_id: input_boolean.zendure_ems_standaard_ingesteld
        state: "on"
      - condition: template
        value_template: "{{{{ states('input_text.zendure_ems_versie') != '{VERSION}' }}}}"
    actions:
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0'] }}}}"
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_wachttijd
            data:
              value: 3
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_min_vermogen
            data:
              value: 50
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_slijtage
            data:
              value: 0.03
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0', '1.2.0'] }}}}"
        then:
          - action: input_boolean.turn_on
            target:
              entity_id: input_boolean.zendure_ems_zon_leren
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0', '1.2.0', '1.3.0'] }}}}"
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_afschaal_drempel
            data:
              value: 0
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_export_normaal
            data:
              value: 3000
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_export_afgeschaald
            data:
              value: 0
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_extra_normaal
            data:
              value: 800
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_extra_afgeschaald
            data:
              value: 0
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0'] }}}}"
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_energiebelasting
            data:
              value: 0.1065
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_inkoop
            data:
              value: 0.02
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_teruglever_vast
            data:
              value: 0
          - action: input_boolean.turn_on
            target:
              entity_id:
                - input_boolean.zendure_ems_teruglever_btw
                - input_boolean.zendure_ems_bonus_overdag
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0', '1.5.0', '1.6.0', '1.6.1', '1.6.2', '1.6.3', '1.6.4'] }}}}"
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_afschaal_stap
            data:
              value: 500
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_afschaal_interval
            data:
              value: 10
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0', '1.5.0', '1.6.0', '1.6.1', '1.6.2', '1.6.3', '1.6.4', '1.7.0', '1.7.1', '1.8.0', '1.8.1', '1.8.2', '1.9.0'] }}}}"
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_standby_vertraging
            data:
              value: 5
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0', '1.5.0', '1.6.0', '1.6.1', '1.6.2', '1.6.3', '1.6.4', '1.7.0', '1.7.1', '1.8.0', '1.8.1', '1.8.2', '1.9.0', '1.9.1'] }}}}"
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_besparing_start
            data:
              value: 0
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0', '1.5.0', '1.6.0', '1.6.1', '1.6.2', '1.6.3', '1.6.4', '1.7.0', '1.7.1', '1.8.0', '1.8.1', '1.8.2', '1.9.0', '1.9.1', '1.9.2', '1.9.3'] }}}}"
        then:
          - action: input_boolean.turn_on
            target:
              entity_id:
{"".join(f"                - input_boolean.zendure_ems_toon_{k}" + chr(10) for k in OVERVIEW_KEYS if not k.startswith("s_"))}      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0', '1.5.0', '1.6.0', '1.6.1', '1.6.2', '1.6.3', '1.6.4', '1.7.0', '1.7.1', '1.8.0', '1.8.1', '1.8.2', '1.9.0', '1.9.1', '1.9.2', '1.9.3', '1.9.4'] }}}}"
        then:
          - action: input_boolean.turn_on
            target:
              entity_id:
{"".join(f"                - input_boolean.zendure_ems_toon_{k}" + chr(10) for k in OVERVIEW_KEYS if k.startswith("s_"))}
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0', '1.5.0', '1.6.0', '1.6.1', '1.6.2', '1.6.3', '1.6.4', '1.7.0', '1.7.1', '1.8.0', '1.8.1', '1.8.2', '1.9.0', '1.9.1', '1.9.2', '1.9.3', '1.9.4', '1.9.5', '1.9.6', '1.9.7', '1.9.8', '1.9.9', '1.9.10', '1.9.11'] }}}}"
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_kalibratie_dagen
            data:
              value: 28
          - action: input_boolean.turn_on
            target:
              entity_id: input_boolean.zendure_ems_toon_o_kalibratie
      - if:
          - condition: template
            value_template: "{{{{ states('input_text.zendure_ems_versie') in ['', 'unknown', '1.11.0', '1.11.1'] and states('input_number.zendure_ems_dip_tijd') | float(0) <= 5 }}}}"
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_dip_tijd
            data:
              value: 20
      - if:
          - condition: numeric_state
            entity_id: input_number.zendure_ems_handel_prijs
            below: 0.01
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_handel_prijs
            data:
              value: 0.35
      - if:
          - condition: template
            value_template: >-
              {{%- set v = states('input_text.zendure_ems_versie') -%}}
              {{{{ v | regex_match('^\\d+\\.\\d+\\.\\d+$') and (v.split('.') | map('int') | list) < [1, 12, 5] }}}}
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_kalibratie_tot
            data:
              value: 7
      - if:
          - condition: template
            value_template: >-
              {{%- set v = states('input_text.zendure_ems_versie') -%}}
              {{{{ v | regex_match('^\\d+\\.\\d+\\.\\d+$') and (v.split('.') | map('int') | list) < [1, 12, 6] }}}}
        then:
          - action: input_number.set_value
            target:
              entity_id: input_number.zendure_ems_min_looptijd
            data:
              value: 60
      - if:
          - condition: template
            value_template: >-
              {{%- set v = states('input_text.zendure_ems_versie') -%}}
              {{{{ v | regex_match('^\\d+\\.\\d+\\.\\d+$') and (v.split('.') | map('int') | list) < [1, 12, 3] }}}}
        then:
          - action: input_boolean.turn_on
            target:
              entity_id: input_boolean.zendure_ems_wachttijd_auto
      - action: input_text.set_value
        target:
          entity_id: input_text.zendure_ems_versie
        data:
          value: "{VERSION}"
      - action: persistent_notification.create
        data:
          notification_id: zendure_ems_update
          title: "Zendure EMS bijgewerkt naar {VERSION}"
          message: >-
            Nieuw in 1.12.6: minimale looptijd bij klein vermogen (Instellingen → Regeling, staat na de update op
            60 s): een set die bij een kleine vraag start, blijft minstens zo lang lopen en rust na het stoppen de
            helft van die tijd, zodat hij niet steeds aan en uit gaat (minder relaisschakelingen). Grote vragen gaan
            altijd direct door. Wachttijd automatisch schat het meterinterval nu goed bij een meter van 1 s (DSMR 5),
            ook als het vermogen even gelijk blijft: de wachttijd wordt daar ongeveer 3,5 s in plaats van 9,5 s.
            Herstart Nordpool en mist het daardoor even de opslag (energiebelasting, btw), dan telt
            de planner de laatst bekende opslag erbij (prijsactie-attribuut nordpool_opslag_hersteld).
            Nieuw in 1.12.5: de kalibratie mag doorlopen tot de volgende ochtend (Instellingen → Kalibratie →
            Klaar om, staat na de update op 7 uur), zodat de goedkope nacht gebruikt kan worden. Wat de set vóór
            zijn laatste kalibratiekwartier verkoopt, plant de planner na de verkoop erbij.
            Nieuw in 1.12.4: betere kalibratieplanning. Het aantal kwartieren houdt rekening met systeem max laden,
            met laden dat al voor de andere set gepland stond en met wat de set vooraf nog aan het huis geeft. In een kalibratiekwartier laadt de kalibrerende set eerst op
            vol vermogen; een andere set krijgt alleen de rest. Nieuwe attributen van de prijsactie:
            kalibratie_tekort_kwh, kalibratie_huis_kwh, kalibratie_verkoop_kwh, kalibratie_netladen_kwh,
            kalibratie_niet_ingepland_kwh, kalibratie_klaar_om.
            Uitleg met rekenvoorbeeld: hoofdstuk Kalibratie van de handleiding.
            Nieuw in 1.12.3: rustiger en zuiniger. De wachttijd na een opdracht past zich automatisch aan
            aan hoe vaak je netmeter bijwerkt (Instellingen → Regeling, staat na de update aan). Bij kleine
            vermogens blijft dezelfde set werken als de richting wisselt (minder relaisschakelingen). De
            grafiek Vermogen gebruikt sensor.zendure_ems_grafiek_net (elke 5 s): zet nu ook
            sensor.zendure_ems_netvermogen en sensor.zendure_ems_huisverbruik in de recorder-exclude.
            Nieuwe standaardwaarden (alleen bij een nieuwe installatie): Kp 0,6, Kd 0, dode zone 35 W,
            minimaal vermogen 100 W.
            Nieuw in 1.12.2: HomeWizard P1 elke seconde. Vul bij Instellingen → Aansluiting het IP-adres van
            je P1 in (lokale API aan in de HomeWizard Energy-app); het package leest de meter dan zelf elke
            seconde uit in plaats van elke 5 s. Zet sensor.zendure_ems_p1_vermogen in de recorder-exclude.
            Nieuw in 1.12.1: tabblad Statistieken met relaisschakelingen en kalibraties per set (ApexCharts Card),
            en een overzicht van alle automatiseringen in LEESMIJ.md en hoofdstuk 13 van de handleiding.
            Plak dashboard.yaml opnieuw in de Raw-configuratie-editor.
            Nieuw in 1.12.0: geoptimaliseerd. Regeling wisselt pas na een tweede meting tussen laden en
            ontladen, minder schrijfacties naar de database, dashboard bijna half zo groot, korte-dip-tijd
            staat na de update op 20 s. Aanbevolen: zet sensor.zendure_ems_netmeting in de recorder-exclude.
            Nieuw in 1.11.1: schakelaar Korte dips negeren (bijvoorbeeld aan/uit vanuit je droger-automatisering):
            valt een groot apparaat even uit, dan blijft de accu een paar seconden doorleveren in plaats van naar
            laden te schakelen.
            Nieuw in 1.11.0: één package en één dashboard voor 1 tot 3 sets. Een set zonder IP-adres wordt niet
            gebruikt en niet getoond. Verwijder het oude bestand zendure_ems_2sets.yaml of zendure_ems_3sets.yaml uit
            de map packages.
            Eerdere wijzigingen: zie LEESMIJ.md in de zip.

  - id: zendure_ems_vol_vermogen_onthouden
    alias: "Zendure EMS: modus vóór laden/ontladen met vol vermogen onthouden"
    mode: queued
    triggers:
      - trigger: state
        entity_id: input_select.zendure_ems_modus
        to:
          - "Laden (vol vermogen)"
          - "Ontladen (vol vermogen)"
    conditions:
      - condition: template
        value_template: >-
          {{{{ trigger.from_state is not none
               and trigger.from_state.state not in ['Laden (vol vermogen)', 'Ontladen (vol vermogen)', 'unknown', 'unavailable'] }}}}
    actions:
      - action: input_text.set_value
        target:
          entity_id: input_text.zendure_ems_vorige_modus
        data:
          value: "{{{{ trigger.from_state.state }}}}"

  - id: zendure_ems_vol_vermogen_klaar
    alias: "Zendure EMS: na laden/ontladen met vol vermogen terug naar de vorige modus"
    description: >-
      Is de accu vol (bij Laden) of leeg tot min SOC + reserve (bij Ontladen) gedurende 2 minuten, dan gaat de
      modus terug naar de modus van daarvoor (of Nul op de meter).
    mode: single
    triggers:
      - trigger: state
        entity_id: sensor.zendure_ems_status
        to:
          - "Laden met vol vermogen: accu vol"
          - "Ontladen met vol vermogen: accu leeg"
        for: "00:02:00"
    conditions:
      - condition: state
        entity_id: input_select.zendure_ems_modus
        state:
          - "Laden (vol vermogen)"
          - "Ontladen (vol vermogen)"
    actions:
      - variables:
          terug: >-
            {{{{ states('input_text.zendure_ems_vorige_modus')
                 if states('input_text.zendure_ems_vorige_modus') in ['Niet aansturen', 'Uit (stand-by)', 'Nul op de meter', 'Prijsgestuurd']
                 else 'Nul op de meter' }}}}
      - action: input_select.select_option
        target:
          entity_id: input_select.zendure_ems_modus
        data:
          option: "{{{{ terug }}}}"
      - action: persistent_notification.create
        data:
          notification_id: zendure_ems_vol_vermogen
          title: "Zendure EMS"
          message: "{{{{ trigger.to_state.state }}}}. De modus staat weer op {{{{ terug }}}}."

  - id: zendure_ems_kalibratie_vol
    alias: "Zendure EMS: 100 % bereikt bijhouden"
    description: >-
      Houdt per set bij wanneer de accu voor het laatst 100 % bereikte (kalibratie van het BMS). Je kunt de datum
      ook zelf invullen, bijvoorbeeld uit het overzicht van Gielz.
    mode: single
    triggers:
      - trigger: time_pattern
        minutes: "/2"
    actions:
      - variables:
          vol: >-
            {{%- set t0 = as_timestamp(now().replace(hour=0, minute=0, second=0, microsecond=0)) -%}}
            {{%- set out = namespace(l=[]) -%}}
            {{%- for i in {sets!r} -%}}
              {{%- set pr = state_attr('sensor.zendure_set' ~ i ~ '_rapport', 'properties') -%}}
              {{%- set lv = state_attr('input_datetime.zendure_set' ~ i ~ '_laatst_vol', 'timestamp') | float(0) -%}}
              {{%- if pr is mapping and pr.electricLevel is number and pr.electricLevel >= 100 and lv < t0 -%}}
                {{%- set out.l = out.l + [i] -%}}
              {{%- endif -%}}
            {{%- endfor -%}}
            {{{{ out.l }}}}
      - condition: template
        value_template: "{{{{ vol | count > 0 }}}}"
      - repeat:
          for_each: "{{{{ vol }}}}"
          sequence:
            - action: input_datetime.set_datetime
              target:
                entity_id: "input_datetime.zendure_set{{{{ repeat.item }}}}_laatst_vol"
              data:
                timestamp: "{{{{ now().timestamp() }}}}"

  - id: zendure_ems_smartmode_bewaken
    alias: "Zendure EMS: smartMode (RAM) bewaken"
    description: >-
      De firmware zet smartMode soms zelf terug op 0 (bijvoorbeeld na een spanningsdip), en het schrijven
      van de SOC-grenzen zet hem bewust even op 0. Staat een set dan op 0 terwijl de regeling actief is, dan
      wordt smartMode weer op 1 gezet, zodat limieten naar het RAM gaan en niet naar het flashgeheugen.
    mode: single
    triggers:
      - trigger: time_pattern
        minutes: "/1"
      - trigger: state
        entity_id: input_boolean.zendure_ems_flash_schrijven
        to: "off"
    conditions:
      - condition: state
        entity_id: input_boolean.zendure_ems_standaard_ingesteld
        state: "on"
      - condition: state
        entity_id: input_boolean.zendure_ems_flash_schrijven
        state: "off"
      - condition: not
        conditions:
          - condition: state
            entity_id: input_select.zendure_ems_modus
            state: "Niet aansturen"
    actions:
      - variables:
          terug: {block(SMARTMODE_BACK, sets, 12)}
      - condition: template
        value_template: "{{{{ terug | count > 0 }}}}"
      - repeat:
          for_each: "{{{{ terug }}}}"
          sequence:
            - action: rest_command.zendure_ems_write
              continue_on_error: true
              data:
                ip: "{{{{ repeat.item.ip }}}}"
                sn: "{{{{ repeat.item.sn }}}}"
                props:
                  smartMode: 1
      - action: logbook.log
        data:
          name: "Zendure EMS"
          message: "smartMode weer op 1 (RAM) gezet voor set {{{{ terug | map(attribute='id') | join(', ') }}}}"

  - id: zendure_ems_standby
    alias: "Zendure EMS: sets in standby na inactiviteit"
    description: >-
      Staat een set langer dan de standby-vertraging op 0 W, dan krijgt hij eenmalig smartMode 0 met beide limieten
      op 0 (zoals Gielz): de set gaat helemaal in standby en verbruikt dan minder. Zodra de regeling weer vermogen
      vraagt, gaat de set met smartMode 1 (RAM) weer aan.
    mode: queued
    max: 5
    triggers:
{"".join(standby_trigger(i) for i in sets)}    conditions:
      - condition: numeric_state
        entity_id: input_number.zendure_ems_standby_vertraging
        above: 0
      - condition: state
        entity_id: input_boolean.zendure_ems_flash_schrijven
        state: "off"
      - condition: not
        conditions:
          - condition: state
            entity_id: input_select.zendure_ems_modus
            state: "Niet aansturen"
      - condition: template
        value_template: >-
          {{{{ (state_attr('sensor.zendure_set' ~ trigger.id ~ '_rapport', 'properties') or {{}}).smartMode == 1
               and (states('input_text.zendure_set' ~ trigger.id ~ '_ip') | trim) not in ['', 'unknown']
               and state_attr('sensor.zendure_set' ~ trigger.id ~ '_rapport', 'sn') is not none }}}}
    actions:
      - action: rest_command.zendure_ems_write
        continue_on_error: true
        data:
          ip: "{{{{ states('input_text.zendure_set' ~ trigger.id ~ '_ip') | trim }}}}"
          sn: "{{{{ state_attr('sensor.zendure_set' ~ trigger.id ~ '_rapport', 'sn') }}}}"
          props:
            smartMode: 0
            inputLimit: 0
            outputLimit: 0
      - action: logbook.log
        data:
          name: "Zendure EMS"
          message: >-
            Set {{{{ trigger.id }}}} na {{{{ states('input_number.zendure_ems_standby_vertraging') | int(5) }}}} minuten
            inactiviteit in standby gezet

  - id: zendure_ems_profiel
    alias: "Zendure EMS: profiel activeren"
    description: >-
      Zet de instellingen van het gekozen profiel (modus, slim laden/ontladen, prijsdrempels, minimale winst,
      slijtage, afschalen) en zet de keuzelijst daarna terug op 'Kies een profiel'.
    mode: queued
    triggers:
      - trigger: state
        entity_id: input_select.zendure_ems_profiel
    conditions:
      - condition: template
        value_template: "{{{{ trigger.to_state.state not in ['Kies een profiel', 'unknown', 'unavailable'] }}}}"
    actions:
      - variables:
          naam: "{{{{ trigger.to_state.state }}}}"
          prof: {block(PROFILE_PICK, sets, 12)}
          getallen: >-
            {{%- set m = {{'lp': 'laadprijs', 'op': 'ontlaadprijs', 'vp': 'verkoopprijs', 'ms': 'min_spread', 'sw': 'slijtage'}} -%}}
            {{%- set o = namespace(l=[]) -%}}
            {{%- for k, e in m.items() if k in prof -%}}
              {{%- set o.l = o.l + [{{'e': 'input_number.zendure_ems_' ~ e, 'v': prof[k]}}] -%}}
            {{%- endfor -%}}
            {{{{ o.l }}}}
          schakelaars: >-
            {{%- set m = {{'sl': 'slim_laden', 'so': 'slim_ontladen', 'np': 'laden_negatieve_prijs', 'vk': 'verkoop_plannen'}} -%}}
            {{%- set o = namespace(l=[]) -%}}
            {{%- for k, e in m.items() if k in prof -%}}
              {{%- set o.l = o.l + [{{'e': 'input_boolean.zendure_ems_' ~ e, 'v': prof[k] | int(0)}}] -%}}
            {{%- endfor -%}}
            {{{{ o.l }}}}
      - if:
          - condition: template
            value_template: "{{{{ prof | count == 0 }}}}"
        then:
          - action: persistent_notification.create
            data:
              notification_id: zendure_ems_profiel
              title: "Zendure EMS"
              message: "{{{{ naam }}}} is nog leeg. Sla eerst je instellingen op met het script 'huidige instellingen opslaan als mijn profiel'."
        else:
          - repeat:
              for_each: "{{{{ getallen }}}}"
              sequence:
                - action: input_number.set_value
                  target:
                    entity_id: "{{{{ repeat.item.e }}}}"
                  data:
                    value: "{{{{ repeat.item.v }}}}"
          - repeat:
              for_each: "{{{{ schakelaars }}}}"
              sequence:
                - action: "input_boolean.turn_{{{{ 'on' if repeat.item.v == 1 else 'off' }}}}"
                  target:
                    entity_id: "{{{{ repeat.item.e }}}}"
          - if:
              - condition: template
                value_template: "{{{{ 'af' in prof }}}}"
            then:
              - action: input_select.select_option
                target:
                  entity_id: input_select.zendure_ems_afschalen
                data:
                  option: "{{{{ prof.af }}}}"
          - if:
              - condition: template
                value_template: "{{{{ 'm' in prof }}}}"
            then:
              - action: input_select.select_option
                target:
                  entity_id: input_select.zendure_ems_modus
                data:
                  option: "{{{{ prof.m }}}}"
          - action: logbook.log
            data:
              name: "Zendure EMS"
              entity_id: sensor.zendure_ems_actief_profiel
              message: "Profiel {{{{ naam }}}} geactiveerd"
      - action: input_select.select_option
        target:
          entity_id: input_select.zendure_ems_profiel
        data:
          option: "Kies een profiel"

  - id: zendure_ems_afschalen
    alias: "Zendure EMS: zonnepanelen afschalen bij negatieve prijs"
    description: >-
      Schaalt bij een negatieve prijs de omvormer af naar het huisverbruik (exportlimiet) en zet een
      extra apparaat op zijn afgeschaalde limiet; direct, of pas als alle sets vol zijn. Zet alles terug
      zodra de prijs weer boven de drempel komt.
    mode: queued
    max: 3
    max_exceeded: silent
    triggers:
      - trigger: state
        entity_id:
          - sensor.zendure_ems_terugleverprijs
          - sensor.zendure_ems_gemiddelde_soc
          - input_select.zendure_ems_afschalen
          - input_number.zendure_ems_afschaal_drempel
      - trigger: time_pattern
        minutes: "/1"
      - trigger: homeassistant
        event: start
        id: start
    conditions:
      - condition: state
        entity_id: input_boolean.zendure_ems_standaard_ingesteld
        state: "on"
    actions:
      - variables:
          want: {block(CURTAIL, sets, 12)}
          cur: "{{{{ is_state('input_boolean.zendure_ems_afgeschaald', 'on') }}}}"
          ent: "{{{{ states('input_text.zendure_ems_export_entiteit') | trim }}}}"
          sw: "{{{{ states('input_text.zendure_ems_export_schakelaar') | trim }}}}"
          ent2: "{{{{ states('input_text.zendure_ems_extra_entiteit') | trim }}}}"
          v1: "{{{{ states('input_number.zendure_ems_export_' ~ ('afgeschaald' if want else 'normaal')) | float(0) }}}}"
          v2: "{{{{ states('input_number.zendure_ems_extra_' ~ ('afgeschaald' if want else 'normaal')) | float(0) }}}}"
          numeric: "{{{{ ent.split('.')[0] in ['number', 'input_number'] }}}}"
          start: "{{{{ states(ent) | float(v1) if numeric else v1 }}}}"
          stap: "{{{{ states('input_number.zendure_ems_afschaal_stap') | float(0) }}}}"
          stappen: >-
            {{{{ 1 if stap <= 0 or (start - v1) | abs <= stap else (((start - v1) | abs) / stap) | round(0, 'ceil') | int }}}}
          bewaken: >-
            {{{{ cur and want and
                 ((numeric and is_number(states(ent)) and (states(ent) | float(0) - v1) | abs > 1) or
                  (ent2.split('.')[0] in ['number', 'input_number'] and is_number(states(ent2))
                   and (states(ent2) | float(0) - v2) | abs > 1)) }}}}
      - condition: template
        value_template: "{{{{ want != cur or (trigger.id == 'start' and cur) or bewaken }}}}"
      - action: "input_boolean.turn_{{{{ 'on' if want else 'off' }}}}"
        target:
          entity_id: input_boolean.zendure_ems_afgeschaald
      - if:
          - condition: template
            value_template: "{{{{ sw.split('.')[0] in ['input_boolean', 'switch'] }}}}"
        then:
          - action: "homeassistant.turn_{{{{ 'on' if want else 'off' }}}}"
            continue_on_error: true
            target:
              entity_id: "{{{{ sw }}}}"
      - if:
          - condition: template
            value_template: "{{{{ ent2.split('.')[0] in ['number', 'input_number'] }}}}"
        then:
          - action: "{{{{ ent2.split('.')[0] }}}}.set_value"
            continue_on_error: true
            target:
              entity_id: "{{{{ ent2 }}}}"
            data:
              value: "{{{{ v2 }}}}"
      - if:
          - condition: template
            value_template: "{{{{ numeric }}}}"
        then:
          - repeat:
              count: "{{{{ stappen }}}}"
              sequence:
                - action: "{{{{ ent.split('.')[0] }}}}.set_value"
                  continue_on_error: true
                  target:
                    entity_id: "{{{{ ent }}}}"
                  data:
                    value: >-
                      {{{{ v1 if repeat.index >= stappen
                           else (start - stap * repeat.index if start > v1 else start + stap * repeat.index) | round(0) }}}}
                - if:
                    - condition: template
                      value_template: "{{{{ repeat.index < stappen }}}}"
                  then:
                    - delay:
                        seconds: "{{{{ states('input_number.zendure_ems_afschaal_interval') | int(10) }}}}"
      - action: logbook.log
        data:
          name: "Zendure EMS"
          entity_id: input_boolean.zendure_ems_afgeschaald
          message: >-
            {{{{ ('exportlimiet opnieuw afgeschaald (was gewijzigd)' if bewaken and want == cur
                  else 'zonnepanelen afgeschaald (terugleverprijs ' ~ states('sensor.zendure_ems_terugleverprijs') ~ ' €/kWh)') if want
                 else 'zonnepanelen weer normaal' }}}}
""")
    return "".join(S)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    # one package and one dashboard for 1 to 3 sets: a set without IP address is simply not used or shown
    from dashboard import dashboard

    for old in ("zendure_ems_2sets.yaml", "zendure_ems_3sets.yaml", "dashboard_2sets.yaml", "dashboard_3sets.yaml"):
        (out / old).unlink(missing_ok=True)
    (out / "zendure_ems.yaml").write_text(generate(3), encoding="utf-8")
    (out / "dashboard.yaml").write_text(dashboard(3), encoding="utf-8")
    print("written", out / "zendure_ems.yaml", out / "dashboard.yaml")
    # the energy-flow images are embedded in the dashboards (data URIs): no files for /config/www
