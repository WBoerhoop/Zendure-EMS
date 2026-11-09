"""A small emulation of Home Assistant's template engine plus simulated Zendure sets.

Only what the package uses is emulated. HA semantics that matter are kept:
float/int filters raise without a default, results are parsed with literal_eval,
the environment is an ImmutableSandboxedEnvironment.
"""

from __future__ import annotations

import ast
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jinja2
import yaml
from jinja2.sandbox import ImmutableSandboxedEnvironment

TZ = timezone(timedelta(hours=1))
_SENTINEL = object()


@dataclass
class State:
    entity_id: str
    state: str
    attributes: dict = field(default_factory=dict)
    last_updated: datetime = None
    last_reported: datetime = None


class Hass:
    def __init__(self, now: datetime):
        self.now = now
        self.states: dict[str, State] = {}
        self.warnings: list[str] = []

    def set(self, eid, state, attrs=None):
        old = self.states.get(eid)
        st = State(eid, str(state), dict(attrs or {}), self.now, self.now)
        if old and old.state == st.state and old.attributes == st.attributes:
            st.last_updated = old.last_updated
        self.states[eid] = st

    # ---- template environment
    def env(self):
        hass = self
        env = ImmutableSandboxedEnvironment(undefined=jinja2.Undefined, extensions=["jinja2.ext.loopcontrols"])

        def states(eid):
            st = hass.states.get(eid)
            return st.state if st else "unknown"

        def state_attr(eid, name):
            st = hass.states.get(eid)
            return st.attributes.get(name) if st else None

        def is_state(eid, value):
            st = hass.states.get(eid)
            return st is not None and st.state == value

        def has_value(eid):
            st = hass.states.get(eid)
            return st is not None and st.state not in ("unknown", "unavailable")

        def expand(*eids):
            out = []
            for e in eids:
                if isinstance(e, str) and e in hass.states:
                    out.append(hass.states[e])
            return out

        def is_number(v):
            try:
                f = float(v)
            except (TypeError, ValueError):
                return False
            return math.isfinite(f)

        def as_timestamp(v, default=_SENTINEL):
            try:
                if isinstance(v, datetime):
                    return v.timestamp()
                if isinstance(v, str):
                    d = datetime.fromisoformat(v.replace("Z", "+00:00"))
                    if d.tzinfo is None:
                        d = d.replace(tzinfo=TZ)
                    return d.timestamp()
                if isinstance(v, (int, float)):
                    return float(v)
            except ValueError:
                pass
            if default is _SENTINEL:
                raise ValueError(f"as_timestamp got invalid input {v!r}")
            return default

        def ffloat(v, default=_SENTINEL):
            try:
                return float(v)
            except (TypeError, ValueError):
                if default is _SENTINEL:
                    raise ValueError(f"float got invalid input {v!r} without default")
                return default

        def fint(v, default=_SENTINEL, base=10):
            try:
                if isinstance(v, str) and "." in v:
                    return int(float(v))
                return int(v)
            except (TypeError, ValueError):
                if default is _SENTINEL:
                    raise ValueError(f"int got invalid input {v!r} without default")
                return default

        def fround(v, precision=0, method="common", default=_SENTINEL):
            try:
                v = float(v)
            except (TypeError, ValueError):
                if default is _SENTINEL:
                    raise ValueError(f"round got invalid input {v!r}")
                return default
            if method in ("ceil", "floor"):
                import math
                f = 10 ** precision
                return (math.ceil if method == "ceil" else math.floor)(v * f) / f
            return round(v, precision)

        def timestamp_custom(v, fmt="%Y-%m-%d %H:%M:%S", local=True, default=_SENTINEL):
            return datetime.fromtimestamp(float(v), TZ).strftime(fmt)

        env.globals.update(
            states=states, state_attr=state_attr, is_state=is_state, has_value=has_value,
            expand=expand, is_number=is_number, as_timestamp=as_timestamp, now=lambda: hass.now,
            float=ffloat, int=fint, dict=dict, pi=math.pi, timedelta=timedelta,
        )
        env.filters.update(
            float=ffloat, int=fint, round=fround, timestamp_custom=timestamp_custom,
            to_json=lambda v: json.dumps(v), from_json=lambda v: json.loads(v), states=states, has_value=has_value,
            sin=lambda v: math.sin(float(v)),
            regex_match=lambda v, pat, ignorecase=False: bool(re.match(pat, str(v), re.I if ignorecase else 0)),
        )
        env.tests.update(has_value=has_value)
        return env

    def render(self, template: str, **variables):
        # like Home Assistant: compile once, render many times (globals are bound to this hass)
        if not hasattr(self, "_env"):
            self._env = self.env()
            self._tpl = {}
        tpl = self._tpl.get(template)
        if tpl is None:
            tpl = self._tpl[template] = self._env.from_string(template)
        out = tpl.render(**variables)
        s = out.strip()
        try:
            return ast.literal_eval(s)
        except (ValueError, SyntaxError):
            return s


_PKG = {}


def load_package(n: int) -> dict:
    """The package as generated for n sets (the released file is the one for 3; fewer sets behave the same,
    because a set without IP address is ignored)."""
    if n not in _PKG:
        import sys
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "generator"))
        sys.path.insert(0, str(root))
        from generate import generate
        _PKG[n] = generate(n)
    return yaml.safe_load(_PKG[n])


def defaults(pkg) -> dict:
    """input_number defaults as set by the init automation."""
    auto = next(a for a in pkg["automation"] if a["id"] == "zendure_ems_standaardwaarden")
    vals = {}
    for step in auto["actions"]:
        for sub in step.get("parallel", []):
            vals[sub["target"]["entity_id"]] = sub["data"]["value"]
    return vals


class SimSet:
    """One SolarFlow 2400 AC+ as seen through /properties/report."""

    def __init__(self, sn, soc, packs=2, kwh_pack=2.88, max_w=2400, latency=2.5):
        self.sn, self.soc, self.packs = sn, soc, packs
        self.cap_wh = packs * kwh_pack * 1000
        self.max_w = max_w
        self.ac_mode, self.input_limit, self.output_limit = 2, 0, 0
        self.min_soc, self.soc_set = 100, 1000  # deci-percent
        self.pending = []
        self.actual = 0.0
        self.latency = latency
        self.writes = []
        self.flash_writes = 0
        self.mode_writes = 0
        self.smart_mode = 1
        self.online = True

    def write(self, t, props):
        self.writes.append((t, dict(props)))
        if props.get("smartMode") == 0:
            self.flash_writes += 1
        if "acMode" in props:
            self.mode_writes += 1
        self.pending.append((t + self.latency, dict(props)))

    def tick(self, t, dt):
        while self.pending and self.pending[0][0] <= t:
            props = self.pending.pop(0)[1]
            for k, v in props.items():
                if k == "acMode":
                    self.ac_mode = v
                elif k == "inputLimit":
                    self.input_limit = v
                elif k == "outputLimit":
                    self.output_limit = v
                elif k == "minSoc":
                    self.min_soc = v
                elif k == "socSet":
                    self.soc_set = v
                elif k == "smartMode":
                    self.smart_mode = v
        target = self.input_limit if self.ac_mode == 1 else -self.output_limit
        if target > 0 and self.soc >= self.soc_set / 10:
            target = 0
        if target < 0 and self.soc <= self.min_soc / 10:
            target = 0
        self.actual += (target - self.actual) * 0.7
        self.soc = max(0.0, min(100.0, self.soc + self.actual * dt / 3600 / self.cap_wh * 100))

    def report(self):
        a = self.actual
        return {
            "sn": self.sn, "product": "SolarFlow 2400 AC+",
            "properties": {
                "electricLevel": int(round(self.soc)), "gridInputPower": max(0, int(a)),
                "outputHomePower": max(0, int(-a)), "packInputPower": max(0, int(-a)),
                "outputPackPower": max(0, int(a)), "acMode": self.ac_mode, "smartMode": self.smart_mode,
                "inputLimit": self.input_limit, "outputLimit": self.output_limit,
                "minSoc": self.min_soc, "socSet": self.soc_set, "hyperTmp": 2981,
                "packNum": self.packs, "chargeMaxLimit": 2400, "inverseMaxPower": self.max_w,
            },
            "packData": [{"sn": f"{self.sn}-P{k}", "socLevel": int(self.soc), "maxTemp": 2961} for k in range(self.packs)],
        }
