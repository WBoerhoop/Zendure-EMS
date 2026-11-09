"""'Korte dips negeren': a dryer element that switches off for ~15 s every few minutes."""
from test_package import Runner


def dryer(t):
    # house 2850 W; the dryer element (2450 W) is off from t=60 to t=75 and from t=180 to t=195
    return 400 if (60 <= t < 75 or 180 <= t < 195) else 2850


def run(on, dip=20, load=dryer, secs=240):
    r = Runner(n=1, socs=(70,), load=load,
               settings={"input_boolean.zendure_ems_korte_dips_negeren": "on" if on else "off",
                         "input_number.zendure_ems_dip_tijd": dip})
    return r.run(secs)


def batt(r, t0):
    return [a[0] for t, g, a, s in r.log if t >= t0]


def test_switch_on_keeps_discharging_through_short_dips():
    off, on = run(False), run(True)
    assert max(batt(off, 40)) > -1000                             # without: the set throttles back hard
    assert max(batt(on, 40)) <= 0                                 # with: it never charges
    assert max(a[0] for t, g, a, s in on.log if 60 <= t < 75) < -2000   # and keeps delivering during the dip
    assert any(s.startswith("Korte dip genegeerd") for t, g, a, s in on.log)
    peak_off = max(g for t, g, a, s in off.log if t >= 70)
    peak_on = max(g for t, g, a, s in on.log if t >= 70)
    assert peak_on < peak_off - 1000                              # much smaller import spike when the dryer resumes


def test_long_surplus_still_handled():
    r = run(True, load=lambda t: 2850 if t < 60 else 400, secs=150)
    assert abs(r.sets[0].actual + 400) < 120                      # after the 20 s the control follows again
