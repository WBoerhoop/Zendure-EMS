"""Runs the generated package's templates against simulated Zendure sets."""

import random
from datetime import datetime, timedelta

import pytest

from ha_sim import TZ, Hass, SimSet, defaults, load_package

START = datetime(2026, 11, 2, 10, 0, 3, tzinfo=TZ)


def nordpool_attrs(prices, day=START.replace(hour=0, minute=0, second=0), cents=False):
    raw = []
    for h, p in enumerate(prices):
        s = day + timedelta(hours=h)
        raw.append({"start": s, "end": s + timedelta(hours=1), "value": p * (100 if cents else 1)})
    return {"raw_today": raw[:24], "raw_tomorrow": raw[24:], "price_in_cents": cents, "unit": "kWh"}


class Runner:
    def __init__(self, n=3, socs=(60, 50, 40), mode="Nul op de meter", load=lambda t: 1500,
                 prices=None, settings=None, seed=1, meter_kw=False, invert=False, start=START):
        self.pkg = load_package(n)
        self.start = start
        self.hass = Hass(start)
        self.sets = [SimSet(f"SN{i + 1}", socs[i]) for i in range(n)]
        self.load = load
        self.rnd = random.Random(seed)
        self.meter_kw = meter_kw
        self.invert = invert
        h = self.hass
        for eid, v in defaults(self.pkg).items():
            h.set(eid, float(v))
        h.set("input_select.zendure_ems_modus", mode)
        h.set("input_boolean.zendure_ems_standaard_ingesteld", "on")
        h.set("input_boolean.zendure_ems_laden_negatieve_prijs", "on")
        for b in ("slim_laden", "slim_ontladen"):
            h.set(f"input_boolean.zendure_ems_{b}", "off")
        h.set("input_boolean.zendure_ems_net_omkeren", "on" if invert else "off")
        h.set("input_text.zendure_ems_netsensor", "sensor.p1_vermogen")
        h.set("input_text.zendure_ems_prijssensor", "sensor.nordpool" if prices else "")
        for i in range(n):
            h.set(f"input_text.zendure_set{i + 1}_ip", f"192.168.1.{101 + i}")
            h.set(f"input_boolean.zendure_set{i + 1}_laden", "on")
            h.set(f"input_boolean.zendure_set{i + 1}_ontladen", "on")
        for k, v in (settings or {}).items():
            h.set(k, v)
        h.set("sun.sun", "below_horizon", {
            "next_rising": (start.replace(hour=7, minute=45, second=0) + timedelta(days=1 if start.hour >= 8 else 0)).isoformat(),
            "next_setting": (start.replace(hour=16, minute=55, second=0) + timedelta(days=1 if start.hour >= 17 else 0)).isoformat()})
        if prices:
            h.set("sensor.nordpool", prices[0], nordpool_attrs(prices, day=start.replace(hour=0, minute=0, second=0)))
        self.h_price = h.set
        self.t = 0.0
        self.log = []
        auto = next(a for a in self.pkg["automation"] if a["id"] == "zendure_ems_regeling")
        self.control_tpl = auto["actions"][0]["variables"]["plan"]
        self.precheck_tpl = auto["conditions"][-1]["value_template"]
        self.netv_tpl = next(s for s in STATE_SENSORS(self.pkg) if s["unique_id"] == "zendure_ems_netvermogen")["state"]
        self.plan = {"status": ""}
        self.runs = 0
        self.price_tpl = self.pkg["template"][0]["actions"][0]["variables"]["pp"]
        self.prijsactie_states = []

    @property
    def grid(self):
        return self.load(self.t) + sum(s.actual for s in self.sets)

    def publish(self):
        h = self.hass
        g = self.grid + self.rnd.gauss(0, 8)
        if self.invert:
            g = -g
        if self.meter_kw:
            h.set("sensor.p1_vermogen", round(g / 1000, 3), {"unit_of_measurement": "kW"})
        else:
            h.set("sensor.p1_vermogen", round(g), {"unit_of_measurement": "W"})
        for i, s in enumerate(self.sets):
            eid = f"sensor.zendure_set{i + 1}_rapport"
            if int(self.t) % 5 != 0 and eid in h.states and getattr(self, "realistic_poll", True):
                continue  # the REST sensors poll every 5 s
            if not s.online:
                h.set(eid, "unavailable")
                continue
            rep = s.report()
            h.set(eid, rep["properties"]["electricLevel"],
                  {"sn": rep["sn"], "product": rep["product"], "properties": rep["properties"], "packData": rep["packData"]})
        nv = h.render(self.netv_tpl)
        h.set("sensor.zendure_ems_netvermogen", "unavailable" if nv in (None, "None") else nv,
              {"unit_of_measurement": "W"})

    def run_price(self):
        pp = self.hass.render(self.price_tpl)
        assert isinstance(pp, dict), pp
        self.hass.set("sensor.zendure_ems_prijsactie", pp["action"],
                      {"laadvermogen": pp["charge_w"], "kalibratie_nu": pp.get("calib_now", False)})
        self.prijsactie_states.append((self.t, pp["action"], pp["reason"]))
        self.pp = pp
        return pp

    def run_control(self):
        h = self.hass
        plan = h.render(self.control_tpl)
        assert isinstance(plan, dict), plan
        ips = {f"192.168.1.{101 + i}": s for i, s in enumerate(self.sets)}
        for w in plan["writes"]:
            ips[w["ip"]].write(self.t, w["props"])
        self.fire_regelaar(plan)
        self.plan = plan
        return plan

    def fire_regelaar(self, plan):
        """Emulate the event -> trigger-based template sensors."""
        auto = next(a for a in self.pkg["automation"] if a["id"] == "zendure_ems_regeling")
        ev = next(x for x in auto["actions"] if "event" in x)
        data = {k: self.hass.render(v, plan=plan) for k, v in ev["event_data"].items()}
        blk = next(b for b in self.pkg["template"] if b["triggers"][0].get("event_type") == "zendure_ems_regelaar")
        trig = {"platform": "event", "event": {"data": data}}
        for sens in blk["sensor"]:
            eid = "sensor." + sens["unique_id"]
            this = self.hass.states.get(eid)   # like HA: the entity's own previous state
            state = self.hass.render(sens["state"], trigger=trig, this=this)
            attrs = {k: self.hass.render(v, trigger=trig, this=this) for k, v in (sens.get("attributes") or {}).items()}
            self.hass.set(eid, state, attrs)

    def try_control(self, trigger_id):
        """Emulates the automation: triggers + the cheap template condition."""
        if self.hass.render(self.precheck_tpl, trigger={"id": trigger_id}) is True:
            self.runs += 1
            return self.run_control()
        return None

    def run(self, seconds):
        end = self.t + seconds
        while self.t < end:
            for s in self.sets:
                s.tick(self.t, 1.0)
            self.publish()
            if int(self.t) % 60 == 0:
                self.run_price()
            self.try_control("tijd" if int(self.t) % 5 == 0 else "meter")
            self.log.append((self.t, self.grid, [s.actual for s in self.sets], self.plan["status"]))
            self.t += 1
            self.hass.now = self.start + timedelta(seconds=self.t)
        return self

    def avg_abs_grid(self, t0, t1):
        xs = [abs(g) for t, g, _, _ in self.log if t0 <= t < t1]
        return sum(xs) / len(xs)


def test_zero_meter_three_sets_converges():
    r = Runner(load=lambda t: 1800).run(300)
    assert r.avg_abs_grid(120, 300) < 60


@pytest.mark.parametrize("n", [2, 3])
def test_steps_and_solar_surplus(n):
    def load(t):
        return 500 if t < 200 else (4000 if t < 400 else -3000)
    r = Runner(n=n, socs=(60, 55, 50)[:n], load=load).run(600)
    for lo, hi in ((150, 200), (340, 400), (540, 600)):
        assert r.avg_abs_grid(lo, hi) < 90, (lo, r.avg_abs_grid(lo, hi))


def test_kw_meter_and_inverted_meter():
    r = Runner(load=lambda t: 1200, meter_kw=True).run(200)
    assert r.avg_abs_grid(100, 200) < 60
    r = Runner(load=lambda t: 1200, invert=True).run(200)
    assert r.avg_abs_grid(100, 200) < 60


def test_staging_single_set_for_small_load():
    r = Runner(socs=(70, 50, 40), load=lambda t: 600).run(150)
    powers = r.log[-1][2]
    assert powers[0] < -450 and abs(powers[1]) < 5 and abs(powers[2]) < 5


def test_write_rate_is_limited_in_steady_state():
    r = Runner(load=lambda t: 1000).run(400)
    writes = sum(len([w for w in s.writes if w[0] >= 200]) for s in r.sets)
    assert writes < 40  # 40 cycles in 200 s; steady state should hardly write


def test_meter_stale_goes_to_standby():
    r = Runner(load=lambda t: 1500).run(100)
    r.hass.states["sensor.p1_vermogen"].last_reported = r.hass.now - timedelta(seconds=120)
    plan = r.run_control()
    assert plan["status"].startswith("Geen (verse) netmeting")
    assert all(v == 0 for v in plan["sp"].values())
    assert any(w["props"].get("outputLimit") == 0 for w in plan["writes"])


def test_set_offline_others_take_over():
    r = Runner(load=lambda t: 3000).run(150)
    r.sets[0].online = False
    r.sets[0].actual = 0
    r.run(150)
    assert r.avg_abs_grid(240, 300) < 80


def test_disallow_discharge_on_one_set():
    r = Runner(load=lambda t: 5000, settings={"input_boolean.zendure_set1_ontladen": "off"}).run(200)
    assert abs(r.log[-1][2][0]) < 5 and sum(r.log[-1][2]) < -4500


def test_off_mode_writes_zero_once():
    r = Runner(load=lambda t: 1500).run(100)
    r.hass.set("input_select.zendure_ems_modus", "Uit (stand-by)")
    r.run(30)
    assert all(abs(s.actual) < 5 for s in r.sets)
    before = sum(len(s.writes) for s in r.sets)
    r.run(30)
    assert sum(len(s.writes) for s in r.sets) == before


def test_niet_aansturen_produces_no_writes():
    r = Runner(load=lambda t: 1500, mode="Niet aansturen")
    plan = r.run(10).plan
    assert plan["writes"] == [] and plan["status"] == "Niet aansturen"


# ------------------------------------------------------------ prices
PRICES = [0.22, 0.18, 0.15, 0.14, 0.16, 0.20, 0.28, 0.33, 0.30, 0.25, 0.20, 0.12, 0.08, 0.10, 0.15, 0.22,
          0.30, 0.38, 0.42, 0.36, 0.30, 0.26, 0.24, 0.22]


def test_price_parse_and_current_price():
    r = Runner(mode="Prijsgestuurd", prices=PRICES)
    r.publish()
    pp = r.run_price()
    assert pp["source"] == "Nordpool" and pp["price"] == 0.20 and pp["n_slots"] == 24
    assert pp["action"] == "zero"


def test_price_in_cents_nordpool():
    r = Runner(mode="Prijsgestuurd", prices=PRICES)
    r.hass.set("sensor.nordpool", 25, nordpool_attrs(PRICES, cents=True))
    r.publish()
    assert r.run_price()["price"] == 0.20


def test_negative_price_charges_from_grid():
    prices = list(PRICES)
    prices[10] = -0.05
    r = Runner(mode="Prijsgestuurd", prices=prices, load=lambda t: 800, socs=(40, 40, 40),
               settings={"input_number.zendure_ems_max_netafname": 6000.0})
    r.run(240)
    assert r.pp["action"] == "grid_charge"
    assert sum(r.log[-1][2]) > 4500  # charging hard
    assert max(g for t, g, _, _ in r.log if t > 60) < 6400  # fuse guard


def test_sell_above_threshold():
    r = Runner(mode="Prijsgestuurd", prices=PRICES, socs=(80, 80, 80),
               settings={"input_number.zendure_ems_verkoopprijs": 0.19})
    r.run(120)
    assert r.pp["action"] == "sell" and sum(r.log[-1][2]) < -6500


def test_hold_below_discharge_threshold():
    r = Runner(mode="Prijsgestuurd", prices=PRICES, load=lambda t: 1500,
               settings={"input_number.zendure_ems_ontlaadprijs": 0.30})
    r.run(120)
    assert r.pp["action"] == "hold" and all(abs(p) < 5 for p in r.log[-1][2])


def test_zonneplan_and_entsoe_sources():
    r = Runner(mode="Prijsgestuurd", prices=PRICES)
    day = START.replace(hour=0, minute=0, second=0)
    fc = [{"datetime": (day + timedelta(hours=h)).astimezone().isoformat(), "electricity_price": int(p * 1e7)}
          for h, p in enumerate(PRICES)]
    r.hass.set("sensor.nordpool", 0.25, {"forecast": fc})
    r.publish()
    pp = r.run_price()
    assert pp["source"] == "Zonneplan" and pp["price"] == 0.20
    q = [{"time": (day + timedelta(minutes=15 * k)).isoformat(), "price": PRICES[k // 4]} for k in range(96)]
    r.hass.set("sensor.nordpool", 0.25, {"prices_today": q, "prices_tomorrow": []})
    pp = r.run_price()
    assert pp["source"] == "ENTSO-e" and pp["price"] == 0.20 and pp["n_slots"] == 96


# ------------------------------------------------------------ other templates
def test_state_sensors_render():
    r = Runner().run(30)
    for sens in STATE_SENSORS(r.pkg):
        for key in ("state", "availability"):
            if key in sens:
                r.hass.render(sens[key])
        for tpl in (sens.get("attributes") or {}).values():
            r.hass.render(tpl)
    soc = STATE_SENSORS(r.pkg)[0]
    assert r.hass.render(soc["state"]) == 60
    temp = next(s for s in STATE_SENSORS(r.pkg) if s["unique_id"] == "zendure_ems_set1_temperatuur")
    assert r.hass.render(temp["state"]) == 25.0
    grid = next(s for s in STATE_SENSORS(r.pkg) if s["unique_id"] == "zendure_ems_netvermogen")
    assert r.hass.render(grid["availability"]) is True


def test_price_sensor_attribute_templates():
    r = Runner(mode="Prijsgestuurd", prices=PRICES, settings={"input_boolean.zendure_ems_slim_laden": "on"}, socs=(20, 20, 20))
    r.publish()
    pp = r.run_price()
    for sens in r.pkg["template"][0]["sensor"]:
        for key in ("state", "availability", "icon"):
            if key in sens:
                r.hass.render(sens[key], pp=pp)
        for tpl in (sens.get("attributes") or {}).values():
            r.hass.render(tpl, pp=pp)


def test_soc_limit_writes_only_when_different():
    r = Runner().run(10)
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_soc_grenzen")
    tpl = auto["actions"][0]["repeat"]["for_each"]
    lst = r.hass.render(tpl)
    assert lst == []  # defaults 10 / 100 equal the device
    r.hass.set("input_number.zendure_set2_max_soc", 90.0)
    lst = r.hass.render(tpl)
    assert len(lst) == 1 and lst[0]["props"] == {"minSoc": 100, "socSet": 900, "smartMode": 0}


def test_standby_list():
    r = Runner().run(10)
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_vrijgeven")
    lst = r.hass.render(auto["actions"][0]["repeat"]["for_each"])
    assert [x["sn"] for x in lst] == ["SN1", "SN2", "SN3"]


def test_rest_command_payload():
    r = Runner()
    tpl = r.pkg["rest_command"]["zendure_ems_write"]["payload"]
    out = r.hass.env().from_string(tpl).render(sn="SN1", props={"acMode": 2, "outputLimit": 300, "smartMode": 1})
    assert out == '{"sn": "SN1", "properties": {"acMode": 2, "outputLimit": 300, "smartMode": 1}}'


def test_regelaar_sensor_roundtrip():
    r = Runner(load=lambda t: 2000).run(60)
    st = r.hass.states["sensor.zendure_ems_regelaar"]
    assert float(st.state) < -1500 and st.attributes["actieve_sets"]
    assert r.hass.states["sensor.zendure_ems_status"].state == "Ontladen voor eigen verbruik"


def test_vrijgeven_event_data_renders():
    r = Runner()
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_vrijgeven")
    ev = next(x for x in auto["actions"] if "event" in x)
    st = r.hass.render(ev["event_data"]["status"], trigger={"platform": "homeassistant"})
    assert st.startswith("Home Assistant stopt")


def STATE_SENSORS(pkg):
    return next(b for b in pkg["template"] if "triggers" not in b)["sensor"]


OLD_MIN = {"input_number.zendure_ems_min_vermogen": 50, "input_number.zendure_ems_deadband": 25}


def test_min_power_no_chatter():
    # (settings of before 1.12.3: minimum 50 W, dead band 25 W)
    # 12 W demand: below minimum - dead band (50 - 25): stays idle, grid takes it, no writes
    r = Runner(n=2, socs=(60, 50), load=lambda t: 12,
               settings=dict(OLD_MIN, **{"input_number.zendure_ems_min_looptijd": 0})).run(300)
    on = sum(1 for t, _, ps, _ in r.log if abs(sum(ps)) > 5)
    assert on < 15 and all(abs(p) < 1 for p in r.log[-1][2])
    # with the minimum run time (1.12.6) a start caused by meter noise lasts longer, but there is still
    # at most one start and one stop
    r = Runner(n=2, socs=(60, 50), load=lambda t: 12, settings=OLD_MIN).run(300)
    st = [abs(sum(ps)) > 5 for t, _, ps, _ in r.log]
    assert sum(1 for x, y in zip(st, st[1:]) if x != y) <= 2 and all(abs(p) < 1 for p in r.log[-1][2])
    # 30 and 40 W demand (with meter noise): engages at 50 W and stays there
    for w in (30, 40):
        r = Runner(n=2, socs=(60, 50), load=lambda t, w=w: w, settings=OLD_MIN).run(240)
        tail = [sum(ps) for t, _, ps, _ in r.log if t > 60]
        assert all(abs(x + 50) < 6 for x in tail), (w, min(tail), max(tail))
        assert sum(1 for s in r.sets for wr in s.writes if wr[0] > 60) == 0


def test_waits_for_previous_command():
    r = Runner(n=2, socs=(60, 50), load=lambda t: 400 if t < 60 else 2400).run(61)
    # one big step: at most one heavy run while the command is still on its way (wait 3 s)
    r.run(3)
    write_times = sorted(w[0] for s in r.sets for w in s.writes if w[0] >= 60)
    gaps = [b - a for a, b in zip(write_times, write_times[1:]) if b - a > 0]
    assert all(g >= 3 for g in gaps)


def test_meter_trigger_reacts_faster_than_5s():
    r = Runner(n=2, socs=(60, 50), load=lambda t: 400 if t < 61 else 2400).run(70)
    first = min(w[0] for s in r.sets for w in s.writes if w[0] >= 61)
    assert first <= 62  # reacts to the next meter value, not to the next 5-second tick


def test_steady_state_is_light():
    r = Runner(n=2, socs=(60, 50), load=lambda t: 800).run(300)
    runs_before = r.runs
    r.run(300)
    assert r.runs - runs_before <= 75  # ~1 per 5 s, not 1 per second


def test_update_sets_only_new_fields():
    r = Runner()
    auto = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_update")
    cond = auto["conditions"][1]["value_template"]
    br11 = auto["actions"][0]["if"][0]["value_template"]
    br12 = auto["actions"][1]["if"][0]["value_template"]
    vals = {x["target"]["entity_id"]: x["data"]["value"] for x in auto["actions"][0]["then"]}
    assert vals == {"input_number.zendure_ems_wachttijd": 3, "input_number.zendure_ems_min_vermogen": 50,
                    "input_number.zendure_ems_slijtage": 0.03}
    assert auto["actions"][1]["then"][0]["target"]["entity_id"] == "input_boolean.zendure_ems_zon_leren"
    r.hass.set("input_text.zendure_ems_versie", "")  # 1.1 install
    assert r.hass.render(cond) is True and r.hass.render(br11) is True and r.hass.render(br12) is True
    r.hass.set("input_text.zendure_ems_versie", "1.2.0")
    assert r.hass.render(cond) is True and r.hass.render(br11) is False and r.hass.render(br12) is True
    br13 = auto["actions"][2]["if"][0]["value_template"]
    v13 = {x["target"]["entity_id"]: x["data"]["value"] for x in auto["actions"][2]["then"]}
    assert v13["input_number.zendure_ems_export_normaal"] == 3000 and v13["input_number.zendure_ems_extra_normaal"] == 800
    r.hass.set("input_text.zendure_ems_versie", "1.3.0")
    assert r.hass.render(cond) is True and r.hass.render(br12) is False and r.hass.render(br13) is True
    br14 = auto["actions"][3]["if"][0]["value_template"]
    r.hass.set("input_text.zendure_ems_versie", "1.4.0")
    assert r.hass.render(cond) is True and r.hass.render(br13) is False and r.hass.render(br14) is True
    br17 = auto["actions"][4]["if"][0]["value_template"]
    r.hass.set("input_text.zendure_ems_versie", "1.6.4")
    assert r.hass.render(cond) is True and r.hass.render(br17) is True
    r.hass.set("input_text.zendure_ems_versie", "1.7.0")   # also the local 1.7.0-ram install
    assert r.hass.render(cond) is True and r.hass.render(br17) is False and r.hass.render(br14) is False
    r.hass.set("input_text.zendure_ems_versie", "1.7.1")
    assert r.hass.render(cond) is True and r.hass.render(br17) is False
    r.hass.set("input_text.zendure_ems_versie", "1.12.1")
    assert r.hass.render(cond) is True
    r.hass.set("input_text.zendure_ems_versie", "1.12.2")
    assert r.hass.render(cond) is True
    r.hass.set("input_text.zendure_ems_versie", "1.12.3")
    assert r.hass.render(cond) is True
    r.hass.set("input_text.zendure_ems_versie", "1.12.4")
    assert r.hass.render(cond) is True
    r.hass.set("input_text.zendure_ems_versie", "1.12.5")
    assert r.hass.render(cond) is True
    r.hass.set("input_text.zendure_ems_versie", "1.12.6")
    assert r.hass.render(cond) is False
    init = next(a for a in r.pkg["automation"] if a["id"] == "zendure_ems_standaardwaarden")
    assert any(x.get("target", {}).get("entity_id") == "input_text.zendure_ems_versie" for x in init["actions"])



def test_new_defaults_leave_small_demand_to_the_grid():
    """1.12.3 defaults (minimum 100 W, dead band 35 W): up to ~50 W stays with the grid (switch-on threshold 65 W), 90 W engages at 100 W."""
    for w in (12, 40):
        r = Runner(n=2, socs=(60, 50), load=lambda t, w=w: w).run(240)
        assert sum(1 for s in r.sets for wr in s.writes if wr[0] > 30) == 0, w
        assert all(abs(p) < 1 for p in r.log[-1][2])
    # 50 W with meter noise: at most one short switch-on in 10 minutes
    r = Runner(n=2, socs=(60, 50), load=lambda t: 50).run(600)
    assert sum(1 for s in r.sets for wr in s.writes) <= 4
    r = Runner(n=2, socs=(60, 50), load=lambda t: 90).run(240)
    tail = [sum(ps) for t, _, ps, _ in r.log if t > 60]
    assert all(abs(x + 100) < 6 for x in tail), (min(tail), max(tail))


def test_defaults_of_1_12_3():
    r = Runner(n=1)
    d = {k: float(v) for k, v in __import__("ha_sim").defaults(r.pkg).items()}
    assert d["input_number.zendure_ems_kp"] == 0.6 and d["input_number.zendure_ems_kd"] == 0
    assert d["input_number.zendure_ems_deadband"] == 35 and d["input_number.zendure_ems_min_vermogen"] == 100
