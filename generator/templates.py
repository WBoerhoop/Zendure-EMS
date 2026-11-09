"""Jinja templates for the Zendure EMS package.

Kept in one module so the generator and the test harness use the exact same
text. ``__SETS__`` is replaced by the list of set numbers, e.g. ['1', '2', '3'].
The logic mirrors the tested Python reference in ../reference/core.
"""

# Calibration (full charge to 100 % so the BMS resets its SOC). Needs `i`. Sets kal, kdg, lvok, lv.
CALIB_PRE = r"""
{#- calibration: settings shared by all sets, computed once outside the set loop -#}
{%- set km = states('input_select.zendure_ems_kalibratie') -%}
{%- set t0 = as_timestamp(now().replace(hour=0, minute=0, second=0, microsecond=0)) -%}
{%- set kmax = states('input_number.zendure_ems_kalibratie_dagen') | int(28) -%}
{%- set kdn = ['maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag', 'zondag'] -%}
{%- set kds = states('input_select.zendure_ems_kalibratie_dag') -%}
{%- set kwd = (kdn.index(kds) + 1) if kds in kdn else 0 -%}
{%- set kwk = {'Wekelijks': 1, 'Elke 2 weken': 2, 'Elke 3 weken': 3}.get(km, 0) -%}
{%- set kdag = kwk > 0 and now().isoweekday() == kwd -%}
{%- set kdatum = km == 'Op datum' and states('input_datetime.zendure_ems_kalibratie_datum') == now().strftime('%Y-%m-%d') -%}
{#- a calibration day runs on until 'klaar om' (hour) the next morning, so the cheap night after it can be used;
    before that hour the calibration of yesterday is still going on -#}
{%- set kth = [[states('input_number.zendure_ems_kalibratie_tot') | int(7), 0] | max, 12] | min -%}
{%- set kgis = kth > 0 and now().hour < kth -%}
{%- set kdy = now() - timedelta(days=1) -%}
{%- set kdag_y = kgis and kwk > 0 and kdy.isoweekday() == kwd -%}
{%- set kdatum_y = kgis and km == 'Op datum' and states('input_datetime.zendure_ems_kalibratie_datum') == kdy.strftime('%Y-%m-%d') -%}
"""

# Calibration per set (full charge to 100 % so the BMS resets its SOC). Needs `i` and CALIB_PRE.
# Sets kal, kdg, lvok, lv.
CALIB = r"""
  {%- set lv = state_attr('input_datetime.zendure_set' ~ i ~ '_laatst_vol', 'timestamp') | float(0) -%}
  {%- set lvok = lv > 946684800 -%}
  {%- set kdg = (((t0 - lv) / 86400) | round(0, 'ceil') | int) if lvok and lv < t0 else 0 -%}
  {%- set kplan = (kdag and (not lvok or kdg >= 7 * kwk - 4)) or kdatum -%}
  {%- set kalv = km != 'Uit' and not (lvok and lv >= t0) and (kplan or (lvok and kdg >= kmax)) -%}
  {#- yesterday's calibration, still running until 'klaar om' -#}
  {%- set kdg_y = (((t0 - 86400 - lv) / 86400) | round(0, 'ceil') | int) if lvok and lv < t0 - 86400 else 0 -%}
  {%- set kplan_y = (kdag_y and (not lvok or kdg_y >= 7 * kwk - 4)) or kdatum_y
                    or (kgis and lvok and kdg_y >= kmax) -%}
  {%- set kaly = km != 'Uit' and kplan_y and not (lvok and lv >= t0 - 86400) -%}
  {%- set kal = kalv or kaly -%}
"""

# Reads every set into nb.list. Needs `p` and `kwh_pack` set beforehand.
BATT = r"""
{%- set sets = __SETS__ -%}
__CALIB_PRE__
{%- set nb = namespace(list=[]) -%}
{%- for i in sets -%}
  {%- set rep = 'sensor.zendure_set' ~ i ~ '_rapport' -%}
  {%- set pr = state_attr(rep, 'properties') -%}
  {%- set ok = has_value(rep) and pr is mapping and pr.electricLevel is number -%}
  {%- set soc = pr.electricLevel if ok else none -%}
  {%- set gi = pr.gridInputPower if ok and pr.gridInputPower is number else none -%}
  {%- set ho = pr.outputHomePower if ok and pr.outputHomePower is number else none -%}
  {%- if gi is not none and ho is not none -%}
    {%- set meas = gi - ho -%}
  {%- elif ok -%}
    {%- set meas = (pr.outputPackPower | float(0)) - (pr.packInputPower | float(0)) -%}
  {%- else -%}
    {%- set meas = none -%}
  {%- endif -%}
  {%- set cml = pr.chargeMaxLimit if ok and pr.chargeMaxLimit is number and pr.chargeMaxLimit > 0 else 99999 -%}
  {%- set imp = pr.inverseMaxPower if ok and pr.inverseMaxPower is number and pr.inverseMaxPower > 0 else 99999 -%}
  {%- set pre = 'input_number.zendure_set' ~ i ~ '_' -%}
  {%- set maxc = [states(pre ~ 'max_laden') | float(0), cml] | min -%}
  {%- set maxd = [states(pre ~ 'max_ontladen') | float(0), imp] | min -%}
  {%- set mins = states(pre ~ 'min_soc') | float(10) -%}
  {%- set maxs = states(pre ~ 'max_soc') | float(100) -%}
__CALIB__
  {%- set kal = kal and ok -%}
  {%- set maxn = maxs -%}
  {%- set maxs = 100 if kal else maxs -%}
  {%- set alc = is_state('input_boolean.zendure_set' ~ i ~ '_laden', 'on') -%}
  {%- set ald = is_state('input_boolean.zendure_set' ~ i ~ '_ontladen', 'on') -%}
  {%- set am = pr.acMode if ok and pr.acMode is number else none -%}
  {%- if am == 1 -%}
    {%- set cur = pr.inputLimit | float(0) -%}
  {%- elif am is not none -%}
    {%- set cur = 0 - (pr.outputLimit | float(0)) -%}
  {%- else -%}
    {%- set cur = none -%}
  {%- endif -%}
  {%- set packs = (pr.packNum | int(1)) if ok and pr.packNum is number and pr.packNum > 0 else 1 -%}
  {#- capacity: the set's own field when filled in (e.g. 2.4 kWh built in + 4 x 2.88), else packs x kWh per pack -#}
  {%- set capm = states(pre ~ 'capaciteit') | float(0) -%}
  {%- set cap = capm if capm > 0 else packs * kwh_pack -%}
  {#- reserve: kWh kept on top of the set's min SOC (the set itself keeps the plain min SOC) -#}
  {%- set res = [states(pre ~ 'reserve') | float(0), 0] | max -%}
  {%- set minhw = mins -%}
  {%- set mins = [mins + res / cap * 100, [maxn - 5, mins] | max] | min if res > 0 else mins -%}
  {%- set nb.list = nb.list + [{
      'id': i, 'online': ok, 'soc': soc, 'meas': meas,
      'maxc': maxc, 'maxd': maxd, 'mins': mins, 'maxs': maxs,
      'cc': ok and alc and soc < maxs and maxc > 0,
      'cd': ok and ald and soc > mins and maxd > 0 and not (kal and soc >= maxn),
      'cur': cur, 'am': am, 'cap': cap, 'minhw': minhw, 'res': res, 'kal': kal, 'kaly': kal and not kalv, 'maxn': maxn,
      'sn': state_attr(rep, 'sn'),
      'ip': states('input_text.zendure_set' ~ i ~ '_ip') | trim }] -%}
{%- endfor -%}
"""

# Grid meter in W (+import), or none when unavailable / stale.
GRID = r"""
{#- HomeWizard P1 read by the package itself (every second) when its IP address is filled in and the reading is
    fresh (< 10 s); otherwise the grid sensor that was filled in. The P1 is always + = import, so no inversion. -#}
{%- set p1ip = states('input_text.zendure_ems_p1_ip') | trim -%}
{%- set p1l = expand('sensor.zendure_ems_p1_vermogen') if p1ip not in ['', 'unknown', 'unavailable'] else [] -%}
{%- set p1ok = p1l | count > 0 and is_number(p1l[0].state)
               and (now() - (p1l[0].last_reported if p1l[0].last_reported is defined and p1l[0].last_reported is not none
                             else p1l[0].last_updated)).total_seconds() < 10 -%}
{%- set gs = 'sensor.zendure_ems_p1_vermogen' if p1ok else states('input_text.zendure_ems_netsensor') | trim -%}
{%- set gl = expand(gs) if gs.startswith('sensor.') else [] -%}
{%- set g = namespace(w=none, raw=none, ev=0) -%}
{#- EV charger: its power is taken out of the measurement when the car charges from the grid -#}
{%- set evs = states('input_text.zendure_ems_ev_sensor') | trim -%}
{%- if evs.startswith('sensor.') and is_number(states(evs)) -%}
  {%- set g.ev = [(states(evs) | float(0)) * (1000 if state_attr(evs, 'unit_of_measurement') == 'kW' else 1), 0] | max -%}
{%- endif -%}
{%- set eva = states('input_text.zendure_ems_ev_actief') | trim -%}
{%- set ev_excl = eva.split('.')[0] in ['input_boolean', 'switch', 'binary_sensor'] and is_state(eva, 'on') -%}
{%- if gl | count > 0 and is_number(gl[0].state) -%}
  {%- set gst = gl[0] -%}
  {%- set has_rep = gst.last_reported is defined and gst.last_reported is not none -%}
  {%- set seen = gst.last_reported if has_rep else gst.last_updated -%}
  {%- if (now() - seen).total_seconds() < (60 if has_rep else 300) -%}
    {%- set unit = gst.attributes.unit_of_measurement | default('W') -%}
    {%- set w = (gst.state | float(0)) * (1000 if unit == 'kW' else 1) -%}
    {%- set g.raw = (0 - w) if is_state('input_boolean.zendure_ems_net_omkeren', 'on') and not p1ok else w -%}
    {%- set g.w = (g.raw - g.ev) if ev_excl else g.raw -%}
  {%- endif -%}
{%- endif -%}
"""

CONTROL = r"""
{%- set p = 'input_number.zendure_ems_' -%}
{%- set kwh_pack = states(p ~ 'kwh_per_pack') | float(2.88) -%}
""" + BATT + GRID + r"""
{%- set mode = states('input_select.zendure_ems_modus') -%}
{%- set tgt = states(p ~ 'doel_net') | float(0) -%}
{%- set db = states(p ~ 'deadband') | float(25) -%}
{%- set kp = states(p ~ 'kp') | float(0.7) -%}
{%- set kd = states(p ~ 'kd') | float(0.15) -%}
{%- set mstep = states(p ~ 'max_stap') | float(1500) -%}
{%- set hyst = 60 -%}
{%- set stg = states(p ~ 'staging') | float(60) -%}
{%- set smaxc = states(p ~ 'systeem_max_laden') | float(0) -%}
{%- set smaxd = states(p ~ 'systeem_max_ontladen') | float(0) -%}
{%- set fuse = states(p ~ 'max_netafname') | float(0) -%}
{%- set minchg = 15 -%}
{%- set minw = states(p ~ 'min_vermogen') | float(50) -%}
{%- set nowts = as_timestamp(now()) -%}
{%- set rg = 'sensor.zendure_ems_regelaar' -%}
{%- set cmd0 = states(rg) | float(0) -%}
{%- set perr = state_attr(rg, 'vorige_fout') | float(99999) -%}
{%- set mis0 = state_attr(rg, 'afwijking') | float(0) -%}
{%- set prev_active = (state_attr(rg, 'actieve_sets') or '') | string -%}
{%- set prev_active = prev_active.split(',') -%}
{%- set pa = states('sensor.zendure_ems_prijsactie') -%}
{%- set kalnu = pa == 'grid_charge' and state_attr('sensor.zendure_ems_prijsactie', 'kalibratie_nu') == true -%}
{%- if mode == 'Nul op de meter' -%}
  {%- set action = 'zero' -%}
{%- elif mode == 'Prijsgestuurd' -%}
  {%- set action = pa if pa in ['zero', 'hold', 'grid_charge', 'sell'] else 'zero' -%}
{%- elif mode == 'Uit (stand-by)' -%}
  {%- set action = 'off' -%}
{%- elif mode == 'Laden (vol vermogen)' -%}
  {%- set action = 'grid_charge' -%}
{%- elif mode == 'Ontladen (vol vermogen)' -%}
  {%- set action = 'sell' -%}
{%- else -%}
  {%- set action = 'none' -%}
{%- endif -%}
{%- set vol = mode in ['Laden (vol vermogen)', 'Ontladen (vol vermogen)'] -%}
{%- set B = nb.list -%}
{%- set online = B | selectattr('online') | list -%}
{%- set sc = B | selectattr('cc') | map(attribute='maxc') | sum -%}
{%- set sd = B | selectattr('cd') | map(attribute='maxd') | sum -%}
{%- set sc = ([sc, smaxc] | min) if smaxc > 0 else sc -%}
{%- set sd = ([sd, smaxd] | min) if smaxd > 0 else sd -%}
{%- set ml = online | selectattr('meas', 'number') | map(attribute='meas') | list -%}
{%- set mt = (ml | sum) if ml | count > 0 else none -%}
{%- set r = namespace(total=0, cmd=0, err=99999, mis=0, status='', dip=0) -%}
{%- if action == 'none' -%}
  {%- set r.status = 'Niet aansturen' -%}
{%- elif action == 'off' -%}
  {%- set r.status = 'Uit (stand-by)' -%}
{%- elif g.w is none -%}
  {%- set r.status = 'Geen (verse) netmeting: stand-by' -%}
{%- elif online | count == 0 -%}
  {%- set r.status = 'Geen accuset bereikbaar' -%}
{%- elif action == 'grid_charge' -%}
  {%- set plw = 0 if vol else state_attr('sensor.zendure_ems_prijsactie', 'laadvermogen') | float(0) -%}
  {%- set tot = ([sc, plw] | min) if plw > 0 else sc -%}
  {%- if fuse > 0 -%}
    {%- set base = mt if mt is not none else cmd0 -%}
    {%- set tot = [[0, base + fuse - g.raw] | max, tot] | min -%}
  {%- endif -%}
  {%- set r.total = tot -%}
  {%- set r.cmd = tot -%}
  {%- set r.status = ('Laden met vol vermogen' if vol else 'Laden van het net') if tot > 0
                     else ('Laden met vol vermogen: accu vol' if vol else 'Laden van het net: accu vol') -%}
{%- elif action == 'sell' -%}
  {#- planned selling: the planned feed-in plus what the house takes now; otherwise full power -#}
  {%- set slw = 0 if vol else state_attr('sensor.zendure_ems_prijsactie', 'verkoopvermogen') | float(0) -%}
  {%- set huis = [g.raw - (mt if mt is not none else cmd0), 0] | max -%}
  {%- set sdw = ([sd, slw + huis] | min) if slw > 0 else sd -%}
  {%- set r.total = 0 - sdw -%}
  {%- set r.cmd = 0 - sdw -%}
  {%- set r.status = ('Ontladen met vol vermogen' if vol else 'Verkopen aan het net') if sd > 0
                     else ('Ontladen met vol vermogen: accu leeg' if vol else 'Verkopen: accu leeg') -%}
{%- else -%}
  {%- set c = cmd0 -%}
  {#- batteries clearly not delivering for 15 s (full, empty, derated): continue from the measurement -#}
  {%- if mt is not none and (c - mt) | abs > 250 -%}
    {%- set r.mis = mis0 if mis0 > 0 else nowts -%}
    {%- if nowts - r.mis >= 15 -%}
      {%- set c = mt -%}
      {%- set r.mis = 0 -%}
    {%- endif -%}
  {%- endif -%}
  {%- set err = g.w - tgt -%}
  {%- set new = c -%}
  {#- 'korte dips negeren' (switched on by e.g. a dryer automation): while discharging, a sudden surplus is
      ignored for a few seconds, so a load that briefly switches off does not make the set swing to charging -#}
  {%- set dipon = is_state('input_boolean.zendure_ems_korte_dips_negeren', 'on') and action == 'zero' -%}
  {%- set dipt = states(p ~ 'dip_tijd') | float(20) -%}
  {%- set dip0 = state_attr(rg, 'dip_sinds') | float(0) -%}
  {%- set diphold = false -%}
  {%- if dipon and c < 0 - minw and err < 0 - db -%}
    {%- set r.dip = dip0 if dip0 > 0 else nowts -%}
    {%- set diphold = nowts - r.dip < dipt -%}
  {%- endif -%}
  {%- if err | abs > db and not diphold -%}
    {%- set d = 0 if perr >= 99999 else err - perr -%}
    {%- set delta = [[kp * err + kd * d, 0 - mstep] | max, mstep] | min -%}
    {%- set new = c - delta -%}
    {%- if c != 0 and new != 0 and (new > 0) != (c > 0) and new | abs < hyst and err | abs < hyst -%}
      {%- set new = 0 -%}
    {%- elif c != 0 and new != 0 and (new > 0) != (c > 0)
             and not (perr < 99999 and (perr > 0) == (err > 0) and perr | abs > db) -%}
      {#- switching between charging and discharging only when the previous sample pointed the same way:
          the first sample stops the set at 0 W, so a load that drops out for a moment is not chased -#}
      {%- set new = 0 -%}
    {%- endif -%}
  {%- endif -%}
  {%- set lo = 0 if action == 'hold' else 0 - sd -%}
  {%- set new = [[new, lo] | max, sc] | min -%}
  {%- set r.total = new -%}
  {%- set r.cmd = new -%}
  {%- set r.err = err -%}
  {%- if diphold -%}
    {%- set r.status = 'Korte dip genegeerd' -%}
  {%- elif action == 'hold' -%}
    {%- set r.status = 'Zonne-overschot laden' if new > 0 else 'Accu vasthouden (prijs)' -%}
  {%- elif new > 0 -%}
    {%- set r.status = 'Zonne-overschot laden' -%}
  {%- elif new < 0 -%}
    {%- set r.status = 'Ontladen voor eigen verbruik' -%}
  {%- else -%}
    {%- set r.status = 'In rust' -%}
  {%- endif -%}
{%- endif -%}
{#- ---------- distribution over the sets ---------- -#}
{#- Below the minimum the inverter is inefficient. Engage at the minimum when that lands
    the meter inside the dead band (|error| >= minimum - dead band); otherwise stay idle
    and restart the command from 0, so it does not chatter around the minimum. -#}
{%- set tot = r.total -%}
{%- if r.total != 0 and r.total | abs < minw -%}
  {%- if action in ['zero', 'hold'] and cmd0 != 0 and ((cmd0 > 0) == (r.total > 0)) and cmd0 | abs >= minw - 1 and r.err | abs <= db + 15 -%}
    {#- already running at the minimum: stay there until the overshoot clearly exceeds the dead band -#}
    {%- set tot = minw if r.total > 0 else 0 - minw -%}
    {%- set r.cmd = tot -%}
  {%- elif action in ['zero', 'hold'] and r.err | abs >= minw - db and ((r.total < 0) == (r.err > 0))
         and (perr >= 99999 or (perr | abs >= minw - db and (perr > 0) == (r.err > 0))) -%}
    {#- two samples in a row above the threshold, so a single noise spike does not switch the set on -#}
    {%- set tot = minw if r.total > 0 else 0 - minw -%}
    {%- set r.cmd = tot -%}
  {%- elif action in ['zero', 'hold'] -%}
    {%- set tot = 0 -%}
    {%- set r.cmd = 0 -%}
    {%- set r.status = 'In rust (vraag onder minimaal vermogen)' -%}
  {%- endif -%}
{%- endif -%}
{#- minimum run time at small powers: a set that started keeps running at least this long (at the minimum,
    in the same direction) unless the meter clearly overshoots; after stopping it rests half that time before
    a small demand starts it again. Stops the on/off chatter (relay clicks) when the demand hovers around the
    minimum, e.g. when solar and house consumption are almost equal. Larger demands always go through. -#}
{%- set mlt = states(p ~ 'min_looptijd') | float(0) -%}
{%- set sw0 = state_attr(rg, 'geschakeld') | float(0) -%}
{%- set since_sw = nowts - sw0 -%}
{%- if action in ['zero', 'hold'] and mlt > 0 and minw > 0 and r.status != 'Korte dip genegeerd' -%}
  {%- set dir_ok = (cmd0 > 0 and sc > 0) or (cmd0 < 0 and action == 'zero' and sd > 0) -%}
  {%- if cmd0 | abs >= 1 and tot | abs < 1 and dir_ok and since_sw < mlt and r.err | abs < minw + db -%}
    {%- set tot = minw if cmd0 > 0 else 0 - minw -%}
    {%- set r.cmd = tot -%}
    {%- set r.status = 'Minimale looptijd (nog ' ~ ((mlt - since_sw) | round(0) | int) ~ ' s)' -%}
  {%- elif cmd0 | abs < 1 and tot | abs >= 1 and tot | abs <= minw + db and since_sw < mlt / 2 -%}
    {%- set tot = 0 -%}
    {%- set r.cmd = 0 -%}
    {%- set r.status = 'Rusttijd na stoppen (nog ' ~ ((mlt / 2 - since_sw) | round(0) | int) ~ ' s)' -%}
  {%- endif -%}
{%- endif -%}
{%- set charging = tot > 0 -%}
{%- set sp = namespace(list=[], active=[]) -%}
{%- if tot | abs >= 1 and action != 'none' -%}
  {%- set el = B | selectattr('cc' if charging else 'cd') | list -%}
  {%- set rk = namespace(list=[]) -%}
  {%- set need0 = tot | abs -%}
  {%- for b in el -%}
    {%- set bonus = 5 if b.id in prev_active else 0 -%}
    {#- small demand that one set handles alone: prefer a set whose acMode already points this way, so no
        acMode (flash) write is needed; above that the SOC decides (calibration charging still goes first) -#}
    {%- set lk0 = 'maxc' if charging else 'maxd' -%}
    {%- set keep = 15 if (b.am == (1 if charging else 2) and need0 <= ((stg / 100) if stg > 0 else 1) * b[lk0]) else 0 -%}
    {%- set kfirst = 1000 if (charging and kalnu and b.kal) else 0 -%}
    {%- set rk.list = rk.list + [dict(b, rank=((b.soc - bonus - keep - kfirst) if charging else (0 - b.soc - bonus - keep)))] -%}
  {%- endfor -%}
  {%- set ordered = rk.list | sort(attribute='rank') -%}
  {%- set lk = 'maxc' if charging else 'maxd' -%}
  {%- set need = tot | abs -%}
  {%- set st = namespace(n=1, go=true) -%}
  {#- calibration quarter: the calibrating sets charge first at full power; another set only takes
      what they cannot (staging does not switch it on earlier) -#}
  {%- set kc = (ordered | selectattr('kal') | list | count) if (charging and kalnu) else 0 -%}
  {%- if kc > 0 -%}
    {%- set st.n = kc -%}
    {%- for k in range(kc, ordered | count) -%}
      {%- if st.go and need > ordered[:k] | map(attribute=lk) | sum + 0.5 -%}
        {%- set st.n = k + 1 -%}
      {%- else -%}
        {%- set st.go = false -%}
      {%- endif -%}
    {%- endfor -%}
  {%- elif stg <= 0 -%}
    {%- set st.n = ordered | count -%}
  {%- else -%}
    {%- for k in range(1, ordered | count) -%}
      {%- if st.go -%}
        {%- set cap = ordered[:k] | map(attribute=lk) | sum -%}
        {%- set thr = (stg / 100 - 0.10) if ordered[k].id in prev_active else stg / 100 -%}
        {%- if need > thr * cap -%}
          {%- set st.n = k + 1 -%}
        {%- else -%}
          {%- set st.go = false -%}
        {%- endif -%}
      {%- endif -%}
    {%- endfor -%}
  {%- endif -%}
  {%- if minw > 0 -%}
    {%- set st.n = [st.n, [(need // minw) | int, 1] | max] | min -%}
  {%- endif -%}
  {%- set act = ordered[:st.n] -%}
  {%- set na = act | count -%}
  {%- set w = namespace(list=[]) -%}
  {%- for b in act -%}
    {%- set room = (b.maxs - b.soc) if charging else (b.soc - b.mins) -%}
    {%- set w.list = w.list + [b[lk] * (([room, 0] | max) + 10) * (1000 if (kc > 0 and b.kal) else 1)] -%}
  {%- endfor -%}
  {%- set al = namespace(a=[0] * na, rem=need, pool=[true] * na) -%}
  {%- for pass in range(na + 1) -%}
    {%- if al.rem > 0.5 -%}
      {%- set ws = namespace(s=0) -%}
      {%- for j in range(na) -%}
        {%- if al.pool[j] -%}{%- set ws.s = ws.s + w.list[j] -%}{%- endif -%}
      {%- endfor -%}
      {%- if ws.s > 0 -%}
        {%- set nx = namespace(a=[], pool=[], spill=0) -%}
        {%- for j in range(na) -%}
          {%- if al.pool[j] -%}
            {%- set share = al.rem * w.list[j] / ws.s -%}
            {%- set room = act[j][lk] - al.a[j] -%}
            {%- if share >= room -%}
              {%- set nx.a = nx.a + [al.a[j] + room] -%}
              {%- set nx.spill = nx.spill + share - room -%}
              {%- set nx.pool = nx.pool + [false] -%}
            {%- else -%}
              {%- set nx.a = nx.a + [al.a[j] + share] -%}
              {%- set nx.pool = nx.pool + [true] -%}
            {%- endif -%}
          {%- else -%}
            {%- set nx.a = nx.a + [al.a[j]] -%}
            {%- set nx.pool = nx.pool + [false] -%}
          {%- endif -%}
        {%- endfor -%}
        {%- set al.a = nx.a -%}
        {%- set al.pool = nx.pool -%}
        {%- set al.rem = nx.spill -%}
      {%- else -%}
        {%- set al.rem = 0 -%}
      {%- endif -%}
    {%- endif -%}
  {%- endfor -%}
  {%- set sgn = 1 if charging else -1 -%}
  {%- for j in range(na) -%}
    {%- set sp.list = sp.list + [{'id': act[j].id, 'w': (sgn * al.a[j]) | round(0) | int}] -%}
    {%- if al.a[j] > 0.5 -%}{%- set sp.active = sp.active + [act[j].id] -%}{%- endif -%}
  {%- endfor -%}
{%- endif -%}
{#- ---------- writes: only where the device setpoint differs ---------- -#}
{%- set wr = namespace(list=[], sp={}) -%}
{#- direction commanded in the last ~15 s: the report shows a new acMode only after ~2.5 s -#}
{%- set psp = state_attr('sensor.zendure_ems_regelaar', 'setpoints') -%}
{%- set fresh = nowts - (state_attr('sensor.zendure_ems_regelaar', 'geschreven') | float(0)) < 15 -%}
{%- for b in B -%}
  {%- set m = sp.list | selectattr('id', 'eq', b.id) | map(attribute='w') | list -%}
  {%- set v = m[0] if m | count > 0 else 0 -%}
  {%- set wr.sp = dict(wr.sp, **{b.id: v}) -%}
  {%- if action != 'none' and b.online and b.sn and b.ip -%}
    {%- if b.cur is none or (v - b.cur) | abs >= minchg or ((v == 0) != (b.cur == 0)) -%}
      {#- acMode only when the direction really changes (a mode change goes to flash; a limit with
          smartMode 1 only to RAM). Stopping (0 W) keeps the current mode and just zeroes its limit. -#}
      {%- set pv = psp[b.id] if psp is mapping and b.id in psp and psp[b.id] is number else 0 -%}
      {%- set em = ((1 if pv > 0 else 2) if fresh and pv != 0 else b.am) -%}
      {%- if v > 0 -%}
        {%- set props = {'inputLimit': v} if em == 1 else {'acMode': 1, 'inputLimit': v} -%}
      {%- elif v < 0 -%}
        {%- set props = {'outputLimit': 0 - v} if em == 2 else {'acMode': 2, 'outputLimit': 0 - v} -%}
      {%- elif em == 1 -%}
        {%- set props = {'inputLimit': 0} -%}
      {%- elif em == 2 -%}
        {%- set props = {'outputLimit': 0} -%}
      {%- else -%}
        {%- set props = {'inputLimit': 0, 'outputLimit': 0} -%}
      {%- endif -%}
      {%- set props = dict(props, smartMode=(0 if is_state('input_boolean.zendure_ems_flash_schrijven', 'on') else 1)) -%}
      {%- set wr.list = wr.list + [{'ip': b.ip, 'sn': b.sn, 'props': props}] -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{{ {'action': action, 'grid': g.w, 'total': r.total | round(0),
    'cmd': [[r.cmd | round(0), -20000] | max, 20000] | min,
    'err': [[r.err | round(0), -99999] | max, 99999] | min,
    'mis': r.mis, 'dip': r.dip, 'status': r.status[:100],
    'sw': nowts if ((cmd0 | abs >= 1) != (r.cmd | abs >= 1)) else sw0, 'active': sp.active | join(','),
    'sp': wr.sp, 'writes': wr.list, 'now': nowts} }}
"""

# Price plan: parses the price sensor, plans cheap charge / expensive discharge
# slots and decides the action for this moment.
PRICE = r"""
{%- set p = 'input_number.zendure_ems_' -%}
{%- set kwh_pack = states(p ~ 'kwh_per_pack') | float(2.88) -%}
""" + BATT + r"""
{%- set now_ts = as_timestamp(now()) -%}
{%- set ps = states('input_text.zendure_ems_prijssensor') | trim -%}
{%- set n = namespace(slots=[], src='geen', add=none, ats=0, fix=0) -%}
{%- if ps.startswith('sensor.') -%}
  {%- set rt = state_attr(ps, 'raw_today') -%}
  {%- set fc = state_attr(ps, 'forecast') -%}
  {%- set et = state_attr(ps, 'prices_today') -%}
  {%- if rt is not none -%}
    {%- set n.src = 'Nordpool' -%}
    {%- set scale = 0.01 if state_attr(ps, 'price_in_cents') == true else 1 -%}
    {%- set unit = (state_attr(ps, 'unit') or 'kWh') | lower -%}
    {%- set scale = scale / 1000 if unit == 'mwh' else (scale * 1000 if unit == 'wh' else scale) -%}
    {#- Nordpool right after a restart: until the next quarter its prices can lack the additional costs
        (energy tax, VAT, supplier), because its cost template ran before the entities it uses were loaded.
        The last additional costs seen (at most 2 h ago) are added back for that time. -#}
    {%- set npa = state_attr(ps, 'additional_costs_current_hour') -%}
    {%- set pa0 = 'sensor.zendure_ems_prijsactie' -%}
    {%- set add0 = state_attr(pa0, 'nordpool_opslag') | float(0) -%}
    {%- set ats0 = state_attr(pa0, 'nordpool_opslag_tijd') | float(0) -%}
    {%- if npa is number and npa | abs >= 0.0005 -%}
      {%- set n.add = npa -%}{%- set n.ats = now_ts -%}
    {%- else -%}
      {%- set n.add = add0 -%}{%- set n.ats = ats0 -%}
      {%- if npa is number and add0 | abs >= 0.005 and now_ts - ats0 < 7200 -%}{%- set n.fix = add0 -%}{%- endif -%}
    {%- endif -%}
    {%- for e in (rt or []) + (state_attr(ps, 'raw_tomorrow') or []) -%}
      {%- if e is mapping and e.value is number -%}
        {%- set s = as_timestamp(e.start, none) -%}
        {%- set en = as_timestamp(e.end, none) -%}
        {%- if s is not none and en is not none and en > s -%}
          {%- set n.slots = n.slots + [{'s': s, 'e': en, 'p': (e.value + n.fix) * scale}] -%}
        {%- endif -%}
      {%- endif -%}
    {%- endfor -%}
  {%- elif fc is not none and fc is iterable and fc is not string -%}
    {%- set n.src = 'Zonneplan' -%}
    {%- for e in fc -%}
      {%- if e is mapping -%}
        {%- set s = as_timestamp(e.start_date if e.start_date is defined else e.datetime, none) -%}
        {%- if e.price_tax_included is defined and e.price_tax_included is mapping -%}
          {%- set amt = e.price_tax_included.amount -%}
          {%- set en = as_timestamp(e.end_date, none) if e.end_date is defined else none -%}
        {%- else -%}
          {%- set amt = e.electricity_price -%}
          {%- set en = s + 3600 if s is not none else none -%}
        {%- endif -%}
        {%- if s is not none and en is not none and en > s and amt is number -%}
          {%- set n.slots = n.slots + [{'s': s, 'e': en, 'p': amt / 10000000}] -%}
        {%- endif -%}
      {%- endif -%}
    {%- endfor -%}
  {%- elif et is not none -%}
    {%- set n.src = 'ENTSO-e' -%}
    {%- set pts = namespace(list=[]) -%}
    {%- for e in (et or []) + (state_attr(ps, 'prices_tomorrow') or []) -%}
      {%- if e is mapping and e.price is number -%}
        {%- set s = as_timestamp(e.time, none) -%}
        {%- if s is not none -%}{%- set pts.list = pts.list + [{'s': s, 'p': e.price}] -%}{%- endif -%}
      {%- endif -%}
    {%- endfor -%}
    {%- set pl = pts.list | sort(attribute='s') -%}
    {%- for i in range(pl | count) -%}
      {%- set step = (pl[i].s - pl[i - 1].s) if i > 0 else 3600 -%}
      {%- set en = pl[i + 1].s if i + 1 < pl | count and pl[i + 1].s - pl[i].s <= 7200 else pl[i].s + step -%}
      {%- set n.slots = n.slots + [{'s': pl[i].s, 'e': en, 'p': pl[i].p}] -%}
    {%- endfor -%}
  {%- endif -%}
{%- endif -%}
{#- ---------- optional second sensor: bare market price for the feed-in price ---------- -#}
{%- set ps = states('input_text.zendure_ems_terugleverprijs_sensor') | trim -%}
{%- set nx = namespace(slots=[], src='geen') -%}
{%- if ps.startswith('sensor.') -%}
  {%- set rt = state_attr(ps, 'raw_today') -%}
  {%- set fc = state_attr(ps, 'forecast') -%}
  {%- set et = state_attr(ps, 'prices_today') -%}
  {%- if rt is not none -%}
    {%- set nx.src = 'Nordpool' -%}
    {%- set scale = 0.01 if state_attr(ps, 'price_in_cents') == true else 1 -%}
    {%- set unit = (state_attr(ps, 'unit') or 'kWh') | lower -%}
    {%- set scale = scale / 1000 if unit == 'mwh' else (scale * 1000 if unit == 'wh' else scale) -%}
    {%- for e in (rt or []) + (state_attr(ps, 'raw_tomorrow') or []) -%}
      {%- if e is mapping and e.value is number -%}
        {%- set s = as_timestamp(e.start, none) -%}
        {%- set en = as_timestamp(e.end, none) -%}
        {%- if s is not none and en is not none and en > s -%}
          {%- set nx.slots = nx.slots + [{'s': s, 'e': en, 'p': e.value * scale}] -%}
        {%- endif -%}
      {%- endif -%}
    {%- endfor -%}
  {%- elif fc is not none and fc is iterable and fc is not string -%}
    {%- set nx.src = 'Zonneplan' -%}
    {%- for e in fc -%}
      {%- if e is mapping -%}
        {%- set s = as_timestamp(e.start_date if e.start_date is defined else e.datetime, none) -%}
        {%- if e.price_tax_included is defined and e.price_tax_included is mapping -%}
          {%- set amt = e.price_tax_included.amount -%}
          {%- set en = as_timestamp(e.end_date, none) if e.end_date is defined else none -%}
        {%- else -%}
          {%- set amt = e.electricity_price -%}
          {%- set en = s + 3600 if s is not none else none -%}
        {%- endif -%}
        {%- if s is not none and en is not none and en > s and amt is number -%}
          {%- set nx.slots = nx.slots + [{'s': s, 'e': en, 'p': amt / 10000000}] -%}
        {%- endif -%}
      {%- endif -%}
    {%- endfor -%}
  {%- elif et is not none -%}
    {%- set nx.src = 'ENTSO-e' -%}
    {%- set pts = namespace(list=[]) -%}
    {%- for e in (et or []) + (state_attr(ps, 'prices_tomorrow') or []) -%}
      {%- if e is mapping and e.price is number -%}
        {%- set s = as_timestamp(e.time, none) -%}
        {%- if s is not none -%}{%- set pts.list = pts.list + [{'s': s, 'p': e.price}] -%}{%- endif -%}
      {%- endif -%}
    {%- endfor -%}
    {%- set pl = pts.list | sort(attribute='s') -%}
    {%- for i in range(pl | count) -%}
      {%- set step = (pl[i].s - pl[i - 1].s) if i > 0 else 3600 -%}
      {%- set en = pl[i + 1].s if i + 1 < pl | count and pl[i + 1].s - pl[i].s <= 7200 else pl[i].s + step -%}
      {%- set nx.slots = nx.slots + [{'s': pl[i].s, 'e': en, 'p': pl[i].p}] -%}
    {%- endfor -%}
  {%- endif -%}
{%- endif -%}
{%- set slots = n.slots | sort(attribute='s') -%}
{%- set fut = slots | selectattr('e', 'gt', now_ts) | list -%}
{%- set curl = fut | selectattr('s', 'le', now_ts) | list -%}
{%- set price = curl[0].p if curl | count > 0 else none -%}
{%- set mode = states('input_select.zendure_ems_modus') -%}
{%- set cb = states(p ~ 'laadprijs') | float(-0.5) -%}
{%- set da = states(p ~ 'ontlaadprijs') | float(-0.5) -%}
{%- set sa = states(p ~ 'verkoopprijs') | float(1.0) -%}
{%- set neg = is_state('input_boolean.zendure_ems_laden_negatieve_prijs', 'on') -%}
{%- set smc = is_state('input_boolean.zendure_ems_slim_laden', 'on') -%}
{%- set smd = is_state('input_boolean.zendure_ems_slim_ontladen', 'on') -%}
{%- set spread = states(p ~ 'min_spread') | float(0.10) -%}
{%- set wear = states(p ~ 'slijtage') | float(0.03) -%}
{%- set eff = [[states(p ~ 'rendement') | float(85), 50] | max, 100] | min / 100 -%}
{%- set se = eff ** 0.5 -%}
{%- set load = [states(p ~ 'verwacht_verbruik') | float(400), 50] | max -%}
{%- set fsun = [[states(p ~ 'zon_factor') | float(80), 0] | max, 150] | min / 100 -%}
{%- set zc = 'sensor.zendure_ems_zonnecorrectie' -%}
{%- set zlearn = is_state('input_boolean.zendure_ems_zon_leren', 'on') and (state_attr(zc, 'dagen') | int(0)) >= 3
                 and (state_attr(zc, 'factor') | float(0)) > 0 -%}
{%- set fsun = (state_attr(zc, 'factor') | float(fsun)) if zlearn else fsun -%}
{%- set smaxc = states(p ~ 'systeem_max_laden') | float(0) -%}
{#- ---------- feed-in price settings (saldering ends 1-1-2027) ---------- -#}
{%- set smode = states('input_select.zendure_ems_salderen') -%}
{%- set sald = smode == 'Aan' or (smode not in ['Aan', 'Uit'] and now().year <= 2026) -%}
{%- set xvast = states(p ~ 'teruglever_vast') | float(0) -%}
{%- set xbonus = states(p ~ 'teruglever_bonus') | float(0) / 100 -%}
{%- set xbtw = is_state('input_boolean.zendure_ems_teruglever_btw', 'on') -%}
{%- set xday = is_state('input_boolean.zendure_ems_bonus_overdag', 'on') -%}
{%- set eb = states(p ~ 'energiebelasting') | float(0.1065) -%}
{%- set ink = states(p ~ 'inkoop') | float(0.02) -%}
{%- set kslots = nx.slots | sort(attribute='s') -%}
{#- ---------- battery figures ---------- -#}
{%- set e = namespace(full=0, usable=0, cpow=0, cc=false, cd=false, room=0, floor=0, tot=0, deficit=0, kdef=0, kpow=0, kl=[],
                      kroom=0, kcap=0, dcap=0, dpow=0) -%}
{#- calibration per set: what each calibrating set still needs (stored kWh) and how fast it can charge;
    kroom: what the calibrating sets may still give to the house today (they only discharge below their
    normal max SOC, down to their min SOC) -#}
{%- for b in nb.list -%}
  {%- if b.kal and b.cc -%}
    {%- set e.kdef = e.kdef + (100 - b.soc) / 100 * b.cap -%}
    {%- set e.kpow = e.kpow + b.maxc -%}
    {%- set e.kl = e.kl + [[(100 - b.soc) / 100 * b.cap, b.maxc]] -%}
    {%- if b.cd -%}
      {%- set e.kroom = e.kroom + ([b.soc - b.mins, 0] | max) / 100 * b.cap -%}
      {%- set e.kcap = e.kcap + b.cap -%}
    {%- endif -%}
  {%- endif -%}
  {%- if b.cd -%}{%- set e.dcap = e.dcap + b.cap -%}{%- endif -%}
{%- endfor -%}
{%- for b in nb.list -%}
  {%- if b.cc and b.soc < b.mins -%}
    {%- set e.deficit = e.deficit + (b.mins - b.soc) / 100 * b.cap -%}
  {%- endif -%}
  {%- if b.online -%}
    {%- set e.room = e.room + ([b.maxs - b.mins, 0] | max) / 100 * b.cap -%}
    {%- set e.floor = e.floor + b.mins / 100 * b.cap -%}
    {%- set e.tot = e.tot + b.cap -%}
  {%- endif -%}
  {%- if b.cc -%}
    {%- set e.full = e.full + (b.maxs - b.soc) / 100 * b.cap -%}
    {%- set e.cpow = e.cpow + b.maxc -%}
    {%- set e.cc = true -%}
  {%- endif -%}
  {%- if b.online -%}{%- set e.dpow = e.dpow + b.maxd -%}{%- endif -%}
  {%- if b.cd -%}
    {%- set e.usable = e.usable + (b.soc - b.mins) / 100 * b.cap -%}
    {%- set e.cd = true -%}
  {%- endif -%}
{%- endfor -%}
{%- set cpow = ([e.cpow, smaxc] | min) if smaxc > 0 else e.cpow -%}
{%- set smaxd = states(p ~ 'systeem_max_ontladen') | float(0) -%}
{%- set dpow = ([e.dpow, smaxd] | min) if smaxd > 0 else e.dpow -%}
{#- ---------- quarter-hour grid (hourly prices are split in four) ---------- -#}
{%- set qg = namespace(list=[]) -%}
{%- for s in fut -%}
  {%- for q in range(((s.s // 900) * 900) | int, s.e | int, 900) -%}
    {%- if q + 900 > now_ts and qg.list | count < 144 and (qg.list | count == 0 or q > qg.list[-1].q) -%}
      {%- set qg.list = qg.list + [{'q': q, 'p': s.p}] -%}
    {%- endif -%}
  {%- endfor -%}
{%- endfor -%}
{#- ---------- solar forecast per quarter (kWh, remaining part only) ---------- -#}
{%- set sol = namespace(d={}, src='geen') -%}
{%- set nr = as_timestamp(state_attr('sun.sun', 'next_rising'), 0) -%}
{%- set nst = as_timestamp(state_attr('sun.sun', 'next_setting'), 0) -%}
{%- set day0 = as_timestamp(now().replace(hour=0, minute=0, second=0, microsecond=0)) -%}
{%- set rise0 = (nr if nr < day0 + 86400 else nr - 86400) if nr > 0 else day0 + 8 * 3600 -%}
{%- set set0 = (nst if nst < day0 + 86400 else nst - 86400) if nst > 0 else day0 + 17 * 3600 -%}
{%- set zsl = [states('input_text.zendure_ems_zon_vandaag') | trim, states('input_text.zendure_ems_zon_morgen') | trim] -%}
{%- for d in range(2) -%}
  {%- set zs = zsl[d] -%}
  {%- if zs.startswith('sensor.') -%}
    {%- set dfc = state_attr(zs, 'detailedForecast') -%}
    {%- set dh = state_attr(zs, 'detailedHourly') -%}
    {%- set det = dfc if dfc is iterable and dfc is not string and dfc | count > 0 else dh -%}
    {%- set dur = 1800 if det is sameas dfc else 3600 -%}
    {%- if det is iterable and det is not string and det | count > 0 -%}
      {%- set sol.src = 'Solcast (detail)' -%}
      {%- for x in det -%}
        {%- set st = as_timestamp(x.period_start, none) if x is mapping else none -%}
        {%- if st is not none and st + dur > now_ts -%}
          {%- for q in range(st | int, (st + dur) | int, 900) -%}
            {%- if q + 900 > now_ts -%}
              {%- set frac = (q + 900 - ([q, now_ts] | max)) / 900 -%}
              {%- set kwh = (x.pv_estimate | float(0)) * 0.25 * frac -%}
              {%- set sol.d = dict(sol.d, **{(q | string): sol.d.get(q | string, 0) + kwh}) -%}
            {%- endif -%}
          {%- endfor -%}
        {%- endif -%}
      {%- endfor -%}
    {%- elif is_number(states(zs)) -%}
      {%- set sol.src = 'Totaal per dag (sinusverdeling)' -%}
      {%- set kwh = states(zs) | float(0) / (1000 if state_attr(zs, 'unit_of_measurement') == 'Wh' else 1) -%}
      {%- set rise = rise0 + 86400 * d -%}
      {%- set sset = set0 + 86400 * d -%}
      {%- set start = [rise, now_ts] | max -%}
      {%- if sset > start and kwh > 0 -%}
        {%- set w = namespace(tot=0, list=[]) -%}
        {%- for q in range(((start // 900) * 900) | int, sset | int, 900) -%}
          {%- set ww = namespace(v=0) -%}
          {%- for m in range(3) -%}
            {%- set tm = q + 150 + 300 * m -%}
            {%- if tm >= start and tm < sset -%}
              {%- set ww.v = ww.v + ((pi * (tm - rise) / (sset - rise)) | sin) -%}
            {%- endif -%}
          {%- endfor -%}
          {%- set w.list = w.list + [[q, ww.v]] -%}
          {%- set w.tot = w.tot + ww.v -%}
        {%- endfor -%}
        {%- if w.tot > 0 -%}
          {%- for it in w.list -%}
            {%- set k = it[0] | string -%}
            {%- set sol.d = dict(sol.d, **{k: sol.d.get(k, 0) + kwh * it[1] / w.tot}) -%}
          {%- endfor -%}
        {%- endif -%}
      {%- endif -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{#- ---------- per quarter: price, load, sun, net demand ---------- -#}
{%- set rid = 'sensor.zendure_ems_verbruiksprofiel' -%}
{%- set pw = state_attr(rid, 'werkdag') -%}
{%- set pe = state_attr(rid, 'weekend') -%}
{%- set pnw = state_attr(rid, 'metingen_werkdag') -%}
{%- set pne = state_attr(rid, 'metingen_weekend') -%}
{%- set okw = pw is iterable and pw is not string and pw | count == 96 and pnw is iterable and pnw is not string and pnw | count == 96 -%}
{%- set oke = pe is iterable and pe is not string and pe | count == 96 and pne is iterable and pne is not string and pne | count == 96 -%}
{%- set okprof = okw or oke -%}
{%- set bk = namespace(list=[]) -%}
{%- set kp = namespace(j=(kslots | selectattr('e', 'le', (qg.list[0].q if qg.list | count > 0 else 0)) | list | count)) -%}
{%- for x in qg.list -%}
  {#- feed-in price for this quarter -#}
  {%- if sald -%}
    {%- set xp = x.p -%}
  {%- else -%}
    {%- for _ in range(3) -%}
      {%- if kp.j < kslots | count and kslots[kp.j].e <= x.q -%}{%- set kp.j = kp.j + 1 -%}{%- endif -%}
    {%- endfor -%}
    {%- if kp.j < kslots | count and kslots[kp.j].s <= x.q -%}
      {%- set kale = kslots[kp.j].p -%}
    {%- else -%}
      {%- set kale = (x.p - eb - ink) / 1.21 -%}
    {%- endif -%}
    {%- set base = kale * (1.21 if xbtw else 1) + xvast -%}
    {%- set dd = ((x.q - day0) // 86400) | int -%}
    {%- set mid = x.q + 450 -%}
    {%- set daylight = (rise0 + 86400 * dd) <= mid and mid < (set0 + 86400 * dd) -%}
    {%- set xp = base * (1 + xbonus) if base > 0 and (daylight or not xday) else base -%}
  {%- endif -%}
  {%- set h = (x.q + 900 - ([x.q, now_ts] | max)) / 3600 -%}
  {%- set qi = (x.q | timestamp_custom('%H') | int) * 4 + (x.q | timestamp_custom('%M') | int) // 15 -%}
  {%- set we = (x.q | timestamp_custom('%w')) in ['0', '6'] -%}
  {%- set lnw = (pw[qi] | float(load)) if okw and (pnw[qi] | int(0)) > 0 else none -%}
  {%- set lne = (pe[qi] | float(load)) if oke and (pne[qi] | int(0)) > 0 else none -%}
  {%- if we -%}
    {%- set lw = lne if lne is not none else (lnw if lnw is not none else load) -%}
  {%- else -%}
    {%- set lw = lnw if lnw is not none else (lne if lne is not none else load) -%}
  {%- endif -%}
  {%- set lk = lw / 1000 * h -%}
  {%- set sk = sol.d.get(x.q | string, 0) * fsun -%}
  {%- set bk.list = bk.list + [{'q': x.q, 'p': x.p, 'x': xp, 'h': h, 'load': lk, 'sun': sk, 'net': lk - sk}] -%}
{%- endfor -%}
{%- set nq = bk.list | count -%}
{#- ---------- simulation with deadline-aware planning ----------
    Walk forward. Solar surplus fills the battery, demand drains it. When the
    battery would run short in quarter i, pick the cheapest way to cover it from
    an earlier quarter j (cheapest first, at equal cost the latest):
      * shift ("Slim ontladen"): hold the battery in j, so the grid feeds the
        house there and the energy is kept for i.  Worth it when
        price_j + min_spread <= price_i.
      * charge ("Slim laden"): buy extra in j.  Worth it when
        price_j / efficiency + wear + min_spread <= price_i.
    The energy must fit in the battery between j and i (no overflow). Cheap
    quarters between j and i in which the battery was empty are held too, so the
    energy really reaches i. -#}
{%- set sim = namespace(E=[e.usable, e.room] | min, traj=[], ch=[0] * nq, hold=[false] * nq, hfor=[0] * nq, draw=[], uns=[]) -%}
{%- set can_c = smc and e.cc and cpow > 0 -%}
{%- for i in range(nq) -%}
  {%- set b = bk.list[i] -%}
  {%- if b.net <= 0 -%}
    {%- set sim.E = [e.room, sim.E + (0 - b.net) * se] | min -%}
    {%- set sim.draw = sim.draw + [0] -%}
    {%- set sim.uns = sim.uns + [0] -%}
  {%- else -%}
    {%- set need = b.net / se -%}
    {%- if sim.E < need and (can_c or smd) -%}
      {%- set sh = namespace(short=need - sim.E, stop=false) -%}
      {%- for it in range(4) -%}
        {%- if sh.short > 0.005 and not sh.stop -%}
          {%- set best = namespace(j=-1, cost=999, room=0, kind='') -%}
          {%- set rm = namespace(m=-1) -%}
          {%- for j in range(i - 1, -1, -1) -%}
            {%- set rm.m = [rm.m, sim.traj[j]] | max -%}
            {%- set bj = bk.list[j] -%}
            {%- set fit = e.room - rm.m -%}
            {%- if smd and sim.draw[j] > 0.005 and bj.p + spread <= b.p and bj.p < best.cost -%}
              {%- set room = [sim.draw[j], fit] | min -%}
              {%- if room > 0.005 -%}
                {%- set best.j = j -%}{%- set best.cost = bj.p -%}{%- set best.room = room -%}{%- set best.kind = 's' -%}
              {%- endif -%}
            {%- endif -%}
            {%- set cc = bj.p / eff + wear -%}
            {%- if can_c and cc + spread <= b.p and cc < best.cost -%}
              {%- set room = [cpow / 1000 * bj.h * se - sim.ch[j] * se, fit] | min -%}
              {%- if room > 0.005 -%}
                {%- set best.j = j -%}{%- set best.cost = cc -%}{%- set best.room = room -%}{%- set best.kind = 'c' -%}
              {%- endif -%}
            {%- endif -%}
          {%- endfor -%}
          {%- if best.j >= 0 -%}
            {%- set x = [sh.short, best.room] | min -%}
            {%- set j0 = best.j -%}
            {%- if best.kind == 'c' -%}
              {%- set sim.ch = sim.ch[:j0] + [sim.ch[j0] + x / se] + sim.ch[j0 + 1:] -%}
            {%- else -%}
              {%- set sim.draw = sim.draw[:j0] + [sim.draw[j0] - x] + sim.draw[j0 + 1:] -%}
              {%- set sim.uns = sim.uns[:j0] + [sim.uns[j0] + x] + sim.uns[j0 + 1:] -%}
            {%- endif -%}
            {%- set nt = namespace(t=sim.traj[:j0], h=sim.hold[:j0], f=sim.hfor[:j0]) -%}
            {%- for k in range(j0, i) -%}
              {%- set newhold = (best.kind == 's' and k == j0) or (k > j0 and sim.uns[k] > 0) -%}
              {%- set nt.t = nt.t + [sim.traj[k] + x] -%}
              {%- set nt.h = nt.h + [sim.hold[k] or newhold] -%}
              {%- set nt.f = nt.f + [b.q if (newhold and not sim.hold[k]) else sim.hfor[k]] -%}
            {%- endfor -%}
            {%- set sim.traj = nt.t -%}
            {%- set sim.hold = nt.h + sim.hold[i:] -%}
            {%- set sim.hfor = nt.f + sim.hfor[i:] -%}
            {%- set sim.E = sim.E + x -%}
            {%- set sh.short = sh.short - x -%}
          {%- else -%}
            {%- set sh.stop = true -%}
          {%- endif -%}
        {%- endif -%}
      {%- endfor -%}
    {%- endif -%}
    {%- if sim.E >= need -%}
      {%- set sim.E = sim.E - need -%}
      {%- set sim.draw = sim.draw + [need] -%}
      {%- set sim.uns = sim.uns + [0] -%}
    {%- else -%}
      {%- set sim.draw = sim.draw + [sim.E] -%}
      {%- set sim.uns = sim.uns + [need - sim.E] -%}
      {%- set sim.E = 0 -%}
    {%- endif -%}
  {%- endif -%}
  {%- set sim.traj = sim.traj + [sim.E] -%}
{%- endfor -%}
{#- reserve below its floor: restore it in the cheapest quarters of the next 12 h, also without profit -#}
{%- set rq = namespace(n=0, q=[]) -%}
{%- if e.deficit > 0.05 and e.cc and cpow > 0 and nq > 0 and mode == 'Prijsgestuurd' -%}
  {%- set per = cpow / 1000 * 0.25 -%}
  {%- set rq.n = ((e.deficit / se / per) | round(0, 'ceil')) | int -%}
  {%- set cands = namespace(l=[]) -%}
  {%- for i in range([nq, 48] | min) -%}
    {%- set cands.l = cands.l + [[bk.list[i].p, i]] -%}
  {%- endfor -%}
  {%- for pi in (cands.l | sort)[:rq.n] -%}
    {%- set j = pi[1] -%}
    {%- set add = [cpow / 1000 * bk.list[j].h - sim.ch[j], 0] | max -%}
    {%- set sim.ch = sim.ch[:j] + [sim.ch[j] + add] + sim.ch[j + 1:] -%}
    {%- set rq.q = rq.q + [bk.list[j].q] -%}
  {%- endfor -%}
{%- endif -%}
{#- calibration day: charge the sets to 100 % in the cheapest quarters before midnight -#}
{#- The quarters must deliver, in grid kWh:
      * the deficit of the calibrating sets to 100 %, divided by the charge efficiency (eff^0.5);
      * plus what those sets will still give to the house before the last calibration quarter (their share of
        the planned battery draw, at most what they can give below their normal max SOC);
    and the slowest set must get enough quarters at its own power (lowered when 'systeem max laden' is lower
    than the sum of the calibrating sets). Per quarter only the power that the normal plan does not use yet
    counts; a quarter that is fully taken by the normal plan is skipped. -#}
{%- set kq = namespace(n=0, q=[], grid=0, drain=0, need=0, kn=0, sold=0) -%}
{#- deadline: 'klaar om' the next morning; while yesterday's calibration is still running: this morning -#}
{%- set kend = t0 + kth * 3600 + (0 if (nb.list | selectattr('kaly') | list | count) > 0 else 86400) -%}
{%- if e.kdef > 0.05 and e.cc and cpow > 0 and nq > 0 and mode == 'Prijsgestuurd' -%}
  {%- set kpw = [e.kpow, cpow] | min -%}
  {%- set ksc = (kpw / e.kpow) if e.kpow > 0 else 1 -%}
  {%- for k in e.kl -%}
    {%- set pq = k[1] * ksc / 1000 * 0.25 -%}
    {%- if pq > 0 -%}{%- set kq.kn = [kq.kn, (k[0] / se / pq) | round(0, 'ceil') | int] | max -%}{%- endif -%}
  {%- endfor -%}
  {%- set cands = namespace(l=[]) -%}
  {%- for i in range(nq) -%}
    {%- if bk.list[i].q < kend -%}{%- set cands.l = cands.l + [[bk.list[i].p, i]] -%}{%- endif -%}
  {%- endfor -%}
  {%- set cl = cands.l | sort -%}
  {%- set kq.need = e.kdef / se -%}
  {%- set acc = namespace(g=0, n=0, sel=[], idx=[]) -%}
  {#- pass 1: without the house; pass 2: with what the sets give to the house before the last chosen quarter -#}
  {%- for pass in range(2) -%}
    {%- set acc.g = 0 -%}{%- set acc.n = 0 -%}{%- set acc.sel = [] -%}{%- set acc.idx = [] -%}
    {%- for pi in cl -%}
      {%- if acc.n < kq.kn or acc.g < kq.need - 0.005 -%}
        {%- set j = pi[1] -%}
        {%- set add = [[kpw / 1000 * bk.list[j].h, cpow / 1000 * bk.list[j].h - sim.ch[j]] | min, 0] | max -%}
        {%- if add > 0.005 -%}
          {%- set acc.g = acc.g + add -%}
          {%- set acc.n = acc.n + 1 -%}
          {%- set acc.sel = acc.sel + [[j, add]] -%}
          {%- set acc.idx = acc.idx + [j] -%}
        {%- endif -%}
      {%- endif -%}
    {%- endfor -%}
    {%- if pass == 0 and acc.idx | count > 0 and e.dcap > 0 and e.kcap > 0 -%}
      {%- set dr = namespace(s=0) -%}
      {%- for i in range(acc.idx | max) -%}
        {%- if i not in acc.idx -%}{%- set dr.s = dr.s + sim.draw[i] -%}{%- endif -%}
      {%- endfor -%}
      {%- set kq.drain = [dr.s * e.kcap / e.dcap, e.kroom] | min -%}
      {%- set kq.need = (e.kdef + kq.drain) / se -%}
    {%- endif -%}
  {%- endfor -%}
  {%- for s in acc.sel -%}
    {%- set j = s[0] -%}
    {%- set sim.ch = sim.ch[:j] + [sim.ch[j] + s[1]] + sim.ch[j + 1:] -%}
    {%- set kq.q = kq.q + [bk.list[j].q] -%}
  {%- endfor -%}
  {%- set kq.n = acc.n -%}
  {%- set kq.grid = acc.g -%}
{%- endif -%}
{#- ---------- trading (profiles Dynamisch Handelen with or without NOM) ----------
    Sell in the most expensive quarters (feed-in price at least 'verkopen boven'), only what pays:
      * from stock that is not needed for own use later in the plan, when
        feed-in * eff^0.5 - wear - min_spread >= cheapest later price / eff^0.5;
      * from extra energy bought in an earlier quarter, when
        feed-in * eff^0.5 - wear - min_spread >= buy price / eff^0.5.
    All in stored kWh; the battery must not overflow between buying and selling. -#}
{%- set vk = is_state('input_boolean.zendure_ems_verkoop_plannen', 'on') and mode == 'Prijsgestuurd' -%}
{%- set tr = namespace(sell=[0] * nq, buy=[0] * nq, traj=sim.traj, rev=0, cost=0) -%}
{%- if vk and nq > 0 and dpow > 0 and price is not none -%}
  {%- set sc0 = namespace(l=[]) -%}
  {%- for i in range(nq) -%}
    {%- if bk.list[i].x >= sa -%}{%- set sc0.l = sc0.l + [[0 - bk.list[i].x, i]] -%}{%- endif -%}
  {%- endfor -%}
  {%- set bc = namespace(l=[]) -%}
  {%- for j in range(nq) -%}{%- set bc.l = bc.l + [[bk.list[j].p, j]] -%}{%- endfor -%}
  {%- set buys = (bc.l | sort)[:24] -%}
  {%- for si in (sc0.l | sort)[:16] -%}
    {%- set i = si[1] -%}
    {%- set xi = bk.list[i].x -%}
    {%- set gain = xi * se - wear - spread -%}
    {#- room at the inverter: max discharge minus what the house takes from the battery then -#}
    {%- set rs = namespace(v=[dpow / 1000 * bk.list[i].h - sim.draw[i] * se, 0] | max / se) -%}
    {#- 1. stock not needed later -#}
    {%- set later = bk.list[i + 1:] | map(attribute='p') | list -%}
    {%- set pl = (later | min) if later | count > 0 else bk.list[i].p -%}
    {%- if rs.v > 0.005 and gain >= pl / se -%}
      {%- set x = [rs.v, tr.traj[i:] | min] | min -%}
      {%- if x > 0.005 -%}
        {%- set tr.sell = tr.sell[:i] + [tr.sell[i] + x * se] + tr.sell[i + 1:] -%}
        {%- set nt = namespace(t=tr.traj[:i]) -%}
        {%- for k in range(i, nq) -%}{%- set nt.t = nt.t + [tr.traj[k] - x] -%}{%- endfor -%}
        {%- set tr.traj = nt.t -%}
        {%- set rs.v = rs.v - x -%}
        {%- set tr.rev = tr.rev + x * se * xi -%}
        {%- set tr.cost = tr.cost + x * wear -%}
      {%- endif -%}
    {%- endif -%}
    {#- 2. buy extra earlier, cheapest first -#}
    {%- for bj in buys -%}
      {%- set j = bj[1] -%}
      {%- if rs.v > 0.005 and j < i and gain >= bj[0] / se -%}
        {%- set rc = (cpow / 1000 * bk.list[j].h - sim.ch[j] - tr.buy[j]) * se -%}
        {%- set rb = e.room - (tr.traj[j:i] | max) -%}
        {%- set x = [rs.v, rc, rb] | min -%}
        {%- if x > 0.005 -%}
          {%- set tr.buy = tr.buy[:j] + [tr.buy[j] + x / se] + tr.buy[j + 1:] -%}
          {%- set tr.sell = tr.sell[:i] + [tr.sell[i] + x * se] + tr.sell[i + 1:] -%}
          {%- set nt = namespace(t=tr.traj[:j]) -%}
          {%- for k in range(j, nq) -%}{%- set nt.t = nt.t + [tr.traj[k] + (x if k < i else 0)] -%}{%- endfor -%}
          {%- set tr.traj = nt.t -%}
          {%- set rs.v = rs.v - x -%}
          {%- set tr.rev = tr.rev + x * se * xi -%}
          {%- set tr.cost = tr.cost + x / se * bj[0] + x * wear -%}
        {%- endif -%}
      {%- endif -%}
    {%- endfor -%}
  {%- endfor -%}
  {%- set nc = namespace(l=[]) -%}
  {%- for j in range(nq) -%}{%- set nc.l = nc.l + [sim.ch[j] + tr.buy[j]] -%}{%- endfor -%}
  {%- set sim.ch = nc.l -%}
  {%- set sim.traj = tr.traj -%}
{%- endif -%}
{#- calibration and planned selling: what the calibrating sets sell before the last calibration quarter
    (their share of the planned sales, at most what they can still give) must be bought back too; it goes in
    the cheapest free quarters before the deadline that come after the last of those sales, so it is not sold
    again. Twice, because new quarters can move the last calibration quarter. -#}
{%- if kq.q | count > 0 and (tr.sell | sum) > 0.005 and e.dcap > 0 and e.kcap > 0 -%}
  {%- set kv = namespace(sold=0, extra=0) -%}
  {%- for rnd in range(2) -%}
    {%- set kidx = namespace(l=[]) -%}
    {%- for i in range(nq) -%}{%- if bk.list[i].q in kq.q -%}{%- set kidx.l = kidx.l + [i] -%}{%- endif -%}{%- endfor -%}
    {%- set klast = kidx.l | max -%}
    {%- set sv = namespace(s=0, last=-1) -%}
    {%- for i in range(klast) -%}
      {%- if tr.sell[i] > 0.002 -%}{%- set sv.s = sv.s + tr.sell[i] / se -%}{%- set sv.last = i -%}{%- endif -%}
    {%- endfor -%}
    {%- set sold = [sv.s * e.kcap / e.dcap, [e.kroom - kq.drain, 0] | max] | min -%}
    {%- set want = (sold - kv.sold) / se -%}
    {%- if want > 0.005 -%}
      {%- set cands = namespace(l=[]) -%}
      {%- for i in range(sv.last + 1, nq) -%}
        {%- if bk.list[i].q < kend and tr.sell[i] <= 0.002 -%}{%- set cands.l = cands.l + [[bk.list[i].p, i]] -%}{%- endif -%}
      {%- endfor -%}
      {%- set got = namespace(g=0) -%}
      {%- for pi in cands.l | sort -%}
        {%- if got.g < want - 0.005 -%}
          {%- set j = pi[1] -%}
          {%- set kpw2 = [e.kpow, cpow] | min -%}
          {%- set used = sim.ch[j] -%}
          {%- set add = [[kpw2 / 1000 * bk.list[j].h, cpow / 1000 * bk.list[j].h - used, want - got.g] | min, 0] | max -%}
          {%- if add > 0.005 -%}
            {%- set sim.ch = sim.ch[:j] + [sim.ch[j] + add] + sim.ch[j + 1:] -%}
            {%- set got.g = got.g + add -%}
            {%- if bk.list[j].q not in kq.q -%}{%- set kq.q = kq.q + [bk.list[j].q] -%}{%- endif -%}
          {%- endif -%}
        {%- endif -%}
      {%- endfor -%}
      {%- set kv.sold = sold -%}
      {%- set kv.extra = kv.extra + got.g -%}
      {%- set kq.grid = kq.grid + got.g -%}
      {%- set kq.need = kq.need + want -%}
    {%- endif -%}
  {%- endfor -%}
  {%- set kq.sold = kv.sold -%}
{%- endif -%}
{%- set sw = ([[tr.sell[0] * 1000 / bk.list[0].h, 200] | max, dpow] | min) if nq > 0 and tr.sell[0] > 0.002 else 0 -%}
{%- set ch0 = sim.ch[0] if nq > 0 else 0 -%}
{%- set chw = ([[ch0 * 1000 / bk.list[0].h, 200] | max, cpow] | min) if nq > 0 and ch0 > 0.002 else 0 -%}
{%- set xprice = bk.list[0].x if nq > 0 else none -%}
{#- ---------- decision for this moment ---------- -#}
{%- set a = namespace(act='zero', why='Nul op de meter', w=0) -%}
{%- if mode != 'Prijsgestuurd' -%}
  {%- set a.why = 'Prijssturing staat uit (modus: ' ~ mode ~ ')' -%}
{%- elif price is none -%}
  {%- set a.why = 'Geen prijsdata: nul op de meter' -%}
{%- elif vk and sw > 0 and e.cd -%}
  {%- set a.act = 'sell' -%}{%- set a.w = sw | round(0) -%}
  {%- set a.why = 'Gepland verkopen: ' ~ (tr.sell[0] | round(2)) ~ ' kWh dit kwartier tegen ' ~ ('%.3f' | format(xprice)) ~ ' €/kWh' -%}
{%- elif not vk and sa < 1.0 and xprice is not none and xprice >= sa and e.cd -%}
  {%- set a.act = 'sell' -%}{%- set a.why = 'Terugleverprijs boven verkoopdrempel' -%}
{%- elif e.cc and neg and price < 0 -%}
  {%- set a.act = 'grid_charge' -%}{%- set a.why = 'Negatieve stroomprijs' -%}
{%- elif neg and price < 0 and not e.cc and e.cd -%}
  {%- set a.act = 'hold' -%}{%- set a.why = 'Negatieve stroomprijs, accu vol: vasthouden' -%}
{%- elif e.cc and cb > -0.5 and price <= cb -%}
  {%- set a.act = 'grid_charge' -%}{%- set a.why = 'Prijs onder laaddrempel' -%}
{%- elif e.cc and chw > 0 -%}
  {%- set a.act = 'grid_charge' -%}{%- set a.w = chw | round(0) -%}
  {%- set a.why = ('Kalibratie naar 100 %: ' if (kq.q | count > 0 and bk.list[0].q in kq.q) else
                   'Reserve aanvullen: ' if (rq.q | count > 0 and bk.list[0].q in rq.q) else
                   'Inkopen voor verkoop: ' if tr.buy[0] > 0.002 else 'Gepland laden: ')
                  ~ (ch0 | round(2)) ~ ' kWh dit kwartier' -%}
{%- elif da > -0.5 and price < da -%}
  {%- set a.act = 'hold' -%}{%- set a.why = 'Prijs onder ontlaaddrempel' -%}
{%- elif nq > 0 and sim.hold[0] and bk.list[0].net > 0 -%}
  {%- set a.act = 'hold' -%}
  {%- set a.why = 'Accu bewaard voor ' ~ (sim.hfor[0] | timestamp_custom('%d-%m %H:%M')) ~ ' (gepland)' -%}
{%- endif -%}
{#- ---------- output ---------- -#}
{%- set up = namespace(list=[]) -%}
{%- for i in range(nq) -%}
  {%- set b = bk.list[i] -%}
  {%- set soc = ((e.floor + sim.traj[i]) / e.tot * 100) if e.tot > 0 else 0 -%}
  {%- set up.list = up.list + [{'s': b.q, 'p': b.p | round(4), 'x': b.x | round(4), 'c': (sim.ch[i] | round(3)), 'd': (sim.draw[i] | round(3)),
      'u': (sim.uns[i] | round(3)), 'z': (b.sun | round(3)), 'v': (b.load | round(3)), 'soc': soc | round(0) | int,
      'h': sim.hold[i], 'sv': (tr.sell[i] | round(3))}] -%}
{%- endfor -%}
{%- set svq = namespace(l=[]) -%}
{%- for i in range(nq) -%}{%- if tr.sell[i] > 0.002 -%}{%- set svq.l = svq.l + [bk.list[i].q] -%}{%- endif -%}{%- endfor -%}
{%- set chq = namespace(l=[]) -%}
{%- for i in range(nq) -%}{%- if sim.ch[i] > 0.002 -%}{%- set chq.l = chq.l + [bk.list[i].q] -%}{%- endif -%}{%- endfor -%}
{{ {'action': a.act, 'reason': a.why, 'charge_w': a.w,
    'price': (price | round(4)) if price is not none else none,
    'export_price': (xprice | round(4)) if xprice is not none else none,
    'salderen': sald,
    'export_source': ('gelijk aan afnameprijs (salderen)' if sald else
                      ((nx.src ~ ' (kale prijs)') if kslots | count > 0 else 'afgeleid uit afnameprijs')
                      ~ (', btw' if xbtw else '') ~ (', + ' ~ xvast ~ ' €/kWh' if xvast != 0 else '')
                      ~ (', bonus ' ~ ((xbonus * 100) | round(0) | int) ~ ' %' ~ (' overdag' if xday else '') if xbonus > 0 else '')),
    'source': n.src ~ (' (opslag hersteld na herstart)' if n.fix != 0 else ''),
    'np_add': n.add, 'np_ats': n.ats, 'np_fix': n.fix != 0, 'solar_source': sol.src ~ (' · correctie ' ~ ((fsun * 100) | round(0) | int) ~ ' % ' ~ ('(geleerd)' if zlearn else '(vast)')), 'profile': ('werkdag ' ~ ((pnw | select('gt', 0) | list | count) if okw else 0) ~ '/96, weekend '
                ~ ((pne | select('gt', 0) | list | count) if oke else 0) ~ '/96 kwartieren geleerd') if okprof
               else 'vast (' ~ (load | int) ~ ' W)',
    'n_slots': slots | count, 'n_quarters': nq,
    'charge_slots': chq.l, 'grid_kwh': (sim.ch | sum) | round(2),
    'sun_kwh': (bk.list | map(attribute='sun') | sum) | round(2),
    'load_kwh': (bk.list | map(attribute='load') | sum) | round(2),
    'short_kwh': (sim.uns | sum) | round(2),
    'energy_to_full': e.full | round(2), 'usable_energy': e.usable | round(2),
    'reserve_deficit': e.deficit | round(2), 'reserve_slots': rq.q,
    'calib_deficit': e.kdef | round(2), 'calib_slots': kq.q,
    'calib_house': kq.drain | round(2), 'calib_sell': kq.sold | round(2), 'calib_grid': kq.grid | round(2),
    'calib_until': kend,
    'calib_short': ([kq.need - kq.grid, 0] | max) | round(2),
    'calib_now': nq > 0 and bk.list[0].q in kq.q,
    'sell_w': (sw | round(0)) if a.act == 'sell' else 0,
    'trade': vk, 'sell_kwh': (tr.sell | sum) | round(2), 'trade_buy_kwh': (tr.buy | sum) | round(2),
    'trade_profit': (tr.rev - tr.cost) | round(2),
    'sell_slots': svq.l,
    'upcoming': up.list} }}
"""

# Writes 0 W to every reachable set (mode "Niet aansturen" and HA shutdown).
STANDBY_LIST = r"""
{%- set out = namespace(list=[]) -%}
{%- for i in __SETS__ -%}
  {%- set rep = 'sensor.zendure_set' ~ i ~ '_rapport' -%}
  {%- set sn = state_attr(rep, 'sn') -%}
  {%- set ip = states('input_text.zendure_set' ~ i ~ '_ip') | trim -%}
  {%- if sn and ip -%}{%- set out.list = out.list + [{'ip': ip, 'sn': sn}] -%}{%- endif -%}
{%- endfor -%}
{{ out.list }}
"""

# SOC limits that differ from what the device stores (written to flash).
SOC_LIMITS = r"""
__CALIB_PRE__
{%- set out = namespace(list=[]) -%}
{%- for i in __SETS__ -%}
  {%- set rep = 'sensor.zendure_set' ~ i ~ '_rapport' -%}
  {%- set pr = state_attr(rep, 'properties') -%}
  {%- set sn = state_attr(rep, 'sn') -%}
  {%- set ip = states('input_text.zendure_set' ~ i ~ '_ip') | trim -%}
  {%- if sn and ip and pr is mapping and has_value(rep) -%}
    {%- set mn = [[states('input_number.zendure_set' ~ i ~ '_min_soc') | float(10), 0] | max, 50] | min | round(0) | int -%}
__CALIB__
    {%- set mx = 100 if kal else ([[states('input_number.zendure_set' ~ i ~ '_max_soc') | float(100), 70] | max, 100] | min | round(0) | int) -%}
    {%- if (pr.minSoc | float(-1)) != mn * 10 or (pr.socSet | float(-1)) != mx * 10 -%}
      {%- set out.list = out.list + [{'ip': ip, 'sn': sn, 'props': {'minSoc': mn * 10, 'socSet': mx * 10, 'smartMode': 0}}] -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{{ out.list }}
"""


# House consumption (W) = grid - battery charge + optional solar production.
HOUSE = r"""
{%- set acc = states('sensor.zendure_ems_accuvermogen') | float(0) -%}
{%- set zp = states('input_text.zendure_ems_zonproductie') | trim -%}
{%- set zw = namespace(v=0) -%}
{%- if zp.startswith('sensor.') and is_number(states(zp)) -%}
  {%- set zw.v = (states(zp) | float(0)) * (1000 if state_attr(zp, 'unit_of_measurement') == 'kW' else 1) -%}
{%- endif -%}
{{ ([g.raw - acc + zw.v - g.ev, 0] | max) | round(0) if g.raw is not none else none }}
"""

# Learned consumption profile: 96 quarter-hour values in W.
# Runs at :00, :15, :30, :45 and stores the mean of the quarter that just ended.
# New quarters learn fast (1/n), later ones slowly (15 % per day).
PROFILE = r"""
{%- set rid = 'sensor.zendure_ems_verbruiksprofiel' -%}
{%- set base = states('input_number.zendure_ems_verwacht_verbruik') | float(400) -%}
{%- macro ok96(x) -%}{{ x is iterable and x is not string and x | count == 96 }}{%- endmacro -%}
{#- current lists; from version 1.2 there was one profile ('kwartier'): it seeds both -#}
{%- set legacy = state_attr(rid, 'kwartier') -%}
{%- set legacyn = state_attr(rid, 'metingen') -%}
{%- set w0 = state_attr(rid, 'werkdag') -%}
{%- set e0 = state_attr(rid, 'weekend') -%}
{%- set nw0 = state_attr(rid, 'metingen_werkdag') -%}
{%- set ne0 = state_attr(rid, 'metingen_weekend') -%}
{%- set W = w0 if ok96(w0) == 'True' else (legacy if ok96(legacy) == 'True' else [base] * 96) -%}
{%- set E = e0 if ok96(e0) == 'True' else (legacy if ok96(legacy) == 'True' else [base] * 96) -%}
{%- set NW = nw0 if ok96(nw0) == 'True' else (legacyn if ok96(legacyn) == 'True' else [0] * 96) -%}
{%- set NE = ne0 if ok96(ne0) == 'True' else (legacyn if ok96(legacyn) == 'True' else [0] * 96) -%}
{%- if trigger is defined and trigger.platform == 'event' -%}
  {#- start profile from history (script "startprofiel uit historie") -#}
  {%- set d = trigger.event.data -%}
  {%- set W = d.werkdag if ok96(d.werkdag) == 'True' else W -%}
  {%- set E = d.weekend if ok96(d.weekend) == 'True' else E -%}
  {%- set NW = d.metingen_werkdag if ok96(d.metingen_werkdag) == 'True' else NW -%}
  {%- set NE = d.metingen_weekend if ok96(d.metingen_weekend) == 'True' else NE -%}
  {%- set qi = -1 -%}
  {%- set wk = false -%}
  {%- set cur = 'none' -%}
{%- else -%}
  {#- runs at :00, :15, :30, :45: learn the quarter that just ended -#}
  {%- set cur = states('sensor.zendure_ems_huisverbruik_kwartiergemiddelde') -%}
  {%- set tq = now() - timedelta(minutes=1) -%}
  {%- set qi = tq.hour * 4 + tq.minute // 15 -%}
  {%- set wk = tq.weekday() >= 5 -%}
{%- endif -%}
{%- set o = namespace(w=[], e=[], nw=[], ne=[]) -%}
{%- for i in range(96) -%}
  {%- set vw = W[i] | float(base) -%}
  {%- set ve = E[i] | float(base) -%}
  {%- set cw = NW[i] | int(0) -%}
  {%- set ce = NE[i] | int(0) -%}
  {%- if i == qi and is_number(cur) -%}
    {%- if wk -%}
      {%- set ve = ve + ([1 / (ce + 1), 0.15] | max) * ((cur | float(0)) - ve) -%}
      {%- set ce = [ce + 1, 999] | min -%}
    {%- else -%}
      {%- set vw = vw + ([1 / (cw + 1), 0.15] | max) * ((cur | float(0)) - vw) -%}
      {%- set cw = [cw + 1, 999] | min -%}
    {%- endif -%}
  {%- endif -%}
  {%- set o.w = o.w + [vw | round(0)] -%}
  {%- set o.e = o.e + [ve | round(0)] -%}
  {%- set o.nw = o.nw + [cw] -%}
  {%- set o.ne = o.ne + [ce] -%}
{%- endfor -%}
{{ {'w': o.w, 'e': o.e, 'nw': o.nw, 'ne': o.ne,
    'avg': ((o.w | sum) / 96) | round(0),
    'kwh_w': ((o.w | sum) * 0.25 / 1000) | round(2), 'kwh_e': ((o.e | sum) * 0.25 / 1000) | round(2),
    'learned_w': o.nw | select('gt', 0) | list | count, 'learned_e': o.ne | select('gt', 0) | list | count} }}
"""


# Cheap gate in front of the control template. The heavy template only runs when
#  * the previous command has had time to take effect (wachttijd), and
#  * for meter triggers: the meter shows new information (it moved more than the
#    dead band away from what the previous cycle saw) and the action follows the
#    meter (zero / hold). The 5 s time trigger always passes after the wait.
PRECHECK = r"""
{%- set rg = 'sensor.zendure_ems_regelaar' -%}
{#- automatic wait: from the measured update interval of the grid meter (attributes of the regulator) -#}
{%- set wauto = state_attr(rg, 'wachttijd_auto') -%}
{%- set wait = (wauto | float(3)) if is_state('input_boolean.zendure_ems_wachttijd_auto', 'on') and wauto is number
               else states('input_number.zendure_ems_wachttijd') | float(3) -%}
{%- set since = as_timestamp(now()) - (state_attr(rg, 'geschreven') | float(0)) -%}
{%- if trigger.id == 'tijd' -%}
  {{ since >= wait }}
{%- else -%}
  {%- set err = (states('sensor.zendure_ems_netvermogen') | float(0)) - (states('input_number.zendure_ems_doel_net') | float(0)) -%}
  {%- set prev = state_attr(rg, 'vorige_fout') | float(99999) -%}
  {%- set db = states('input_number.zendure_ems_deadband') | float(25) -%}
  {{ since >= wait and state_attr(rg, 'actie') in ['zero', 'hold'] and (err - prev) | abs > db }}
{%- endif -%}
"""


# Solar production now (W): optional external inverter sensor + PV inputs of the sets.
SOLAR_NOW = r"""
{%- set zp = states('input_text.zendure_ems_zonproductie') | trim -%}
{%- set o = namespace(w=0) -%}
{%- if zp.startswith('sensor.') and is_number(states(zp)) -%}
  {%- set o.w = (states(zp) | float(0)) * (1000 if state_attr(zp, 'unit_of_measurement') == 'kW' else 1) -%}
{%- endif -%}
{%- for i in __SETS__ -%}
  {%- set pr = state_attr('sensor.zendure_set' ~ i ~ '_rapport', 'properties') -%}
  {%- if pr is mapping and pr.solarInputPower is number and pr.solarInputPower > 0 -%}
    {%- set o.w = o.w + pr.solarInputPower -%}
  {%- endif -%}
{%- endfor -%}
{{ [o.w, 0] | max | round(0) }}
"""

# Learning solar correction. At 00:10 the forecast for the whole day is stored; at
# 23:50 it is compared with the measured production of the day. The factor moves 20 %
# towards measured / forecast. Days with a small forecast or no measurement are skipped.
SOLAR_CORR = r"""
{%- set zc = 'sensor.zendure_ems_zonnecorrectie' -%}
{%- set start = ([[states('input_number.zendure_ems_zon_factor') | float(80), 0] | max, 150] | min) / 100 -%}
{%- set f = state_attr(zc, 'factor') | float(start) -%}
{%- set dagen = state_attr(zc, 'dagen') | int(0) -%}
{%- set exp = state_attr(zc, 'verwacht_vandaag') | float(0) -%}
{%- set hist = state_attr(zc, 'historie') -%}
{%- set hist = hist if hist is iterable and hist is not string else [] -%}
{%- set msg = namespace(t=state_attr(zc, 'laatste') or 'nog niets geleerd') -%}
{%- set zs = states('input_text.zendure_ems_zon_vandaag') | trim -%}
{%- if trigger.id == 'ochtend' -%}
  {%- set v = states(zs) if zs.startswith('sensor.') else 'x' -%}
  {%- set exp = ((v | float(0)) / (1000 if state_attr(zs, 'unit_of_measurement') == 'Wh' else 1)) if is_number(v) else 0 -%}
{%- elif trigger.id == 'avond' -%}
  {%- set act = states('sensor.zendure_ems_zonne_energie_vandaag') -%}
  {%- set has_src = (states('input_text.zendure_ems_zonproductie') | trim).startswith('sensor.') or (states('sensor.zendure_ems_zonne_energie') | float(0)) > 0 -%}
  {%- if exp >= 1.0 and is_number(act) and (act | float(0)) >= 0.1 and has_src -%}
    {%- set ratio = [[(act | float(0)) / exp, 0.2] | max, 1.5] | min -%}
    {%- set f = [[f + 0.2 * (ratio - f), 0.2] | max, 1.3] | min -%}
    {%- set dagen = dagen + 1 -%}
    {%- set hist = (hist + [{'datum': now().strftime('%d-%m'), 'verwacht': exp | round(1), 'gemeten': (act | float(0)) | round(1)}])[-14:] -%}
    {%- set msg.t = now().strftime('%d-%m') ~ ': verwacht ' ~ (exp | round(1)) ~ ' kWh, gemeten ' ~ ((act | float(0)) | round(1)) ~ ' kWh' -%}
  {%- else -%}
    {%- set msg.t = now().strftime('%d-%m') ~ ': overgeslagen (te weinig zon verwacht of geen productiemeting)' -%}
  {%- endif -%}
  {%- set exp = 0 -%}
{%- elif trigger.id == 'reset' -%}
  {%- set f = start -%}{%- set dagen = 0 -%}{%- set hist = [] -%}{%- set msg.t = 'teruggezet' -%}
{%- endif -%}
{{ {'factor': f | round(3), 'dagen': dagen, 'exp': exp | round(2), 'hist': hist, 'msg': msg.t} }}
"""

# Start profile from history: turns recorder.get_statistics (hourly means) into the
# werkdag / weekend profiles. House = grid - batteries + solar, per hour; every hour
# value is used for its 4 quarters. Needs `stats` (the response) and `ids`.
START_PROFILE = r"""
{%- set st = stats.statistics if stats is mapping and stats.statistics is defined else {} -%}
{%- set g = st.get(ids.grid, []) -%}
{%- set inv = is_state('input_boolean.zendure_ems_net_omkeren', 'on') -%}
{%- set acc = namespace(d={}) -%}
{#- battery power (+ charging): from Zendure EMS itself, or for older hours from the charge and discharge
    sensors of a previous controller (for example Gielz: Vermogen Import / Vermogen Export) -#}
{%- for r in st.get(ids.acc_in | default(''), []) -%}{%- set acc.d = dict(acc.d, **{r.start: r.mean | float(0)}) -%}{%- endfor -%}
{%- for r in st.get(ids.acc_out | default(''), []) -%}{%- set acc.d = dict(acc.d, **{r.start: acc.d.get(r.start, 0) - (r.mean | float(0))}) -%}{%- endfor -%}
{%- for r in st.get(ids.accu, []) -%}{%- set acc.d = dict(acc.d, **{r.start: r.mean | float(0)}) -%}{%- endfor -%}
{%- set sol = namespace(d={}) -%}
{%- for r in st.get(ids.solar, []) -%}{%- set sol.d = dict(sol.d, **{r.start: r.mean | float(0)}) -%}{%- endfor -%}
{%- set evd = namespace(d={}) -%}
{%- for r in st.get(ids.ev | default(''), []) -%}{%- set evd.d = dict(evd.d, **{r.start: r.mean | float(0)}) -%}{%- endfor -%}
{%- set s = namespace(w=[0] * 24, nw=[0] * 24, e=[0] * 24, ne=[0] * 24, used=0) -%}
{%- for r in g -%}
  {%- if r.mean is number -%}
    {%- set gm = (0 - r.mean) if inv else r.mean -%}
    {%- set house = [gm - acc.d.get(r.start, 0) + sol.d.get(r.start, 0) - evd.d.get(r.start, 0), 0] | max -%}
    {%- set ts = as_timestamp(r.start) -%}
    {%- set h = (ts | timestamp_custom('%H')) | int -%}
    {%- if (ts | timestamp_custom('%w')) in ['0', '6'] -%}
      {%- set s.e = s.e[:h] + [s.e[h] + house] + s.e[h + 1:] -%}
      {%- set s.ne = s.ne[:h] + [s.ne[h] + 1] + s.ne[h + 1:] -%}
    {%- else -%}
      {%- set s.w = s.w[:h] + [s.w[h] + house] + s.w[h + 1:] -%}
      {%- set s.nw = s.nw[:h] + [s.nw[h] + 1] + s.nw[h + 1:] -%}
    {%- endif -%}
    {%- set s.used = s.used + 1 -%}
  {%- endif -%}
{%- endfor -%}
{%- set o = namespace(w=[], e=[], nw=[], ne=[]) -%}
{%- for q in range(96) -%}
  {%- set h = q // 4 -%}
  {%- set o.w = o.w + [((s.w[h] / s.nw[h]) if s.nw[h] > 0 else (s.e[h] / s.ne[h] if s.ne[h] > 0 else fallback)) | round(0)] -%}
  {%- set o.e = o.e + [((s.e[h] / s.ne[h]) if s.ne[h] > 0 else (s.w[h] / s.nw[h] if s.nw[h] > 0 else fallback)) | round(0)] -%}
  {#- counts: number of days behind the value, capped at 5 so recent days still weigh in -#}
  {%- set o.nw = o.nw + [[s.nw[h], 5] | min] -%}
  {%- set o.ne = o.ne + [[s.ne[h], 5] | min] -%}
{%- endfor -%}
{{ {'werkdag': o.w, 'weekend': o.e, 'metingen_werkdag': o.nw, 'metingen_weekend': o.ne, 'uren': s.used,
    'kwh_w': ((o.w | sum) * 0.25 / 1000) | round(2), 'kwh_e': ((o.e | sum) * 0.25 / 1000) | round(2)} }}
"""


# Solar curtailment at negative prices. Returns true when the panels should be curtailed.
#  * "Direct":          as soon as the price is below the threshold.
#  * "Bij volle accu":  price below the threshold and every set that may charge is full
#                       (SOC >= max SOC - 1). Once curtailed it stays so until the price is no
#                       longer below the threshold or a set has dropped 5 points below its max.
CURTAIL = r"""
{%- set mode = states('input_select.zendure_ems_afschalen') -%}
{%- set thr = states('input_number.zendure_ems_afschaal_drempel') | float(0) -%}
{%- set pr0 = states('sensor.zendure_ems_terugleverprijs') -%}
{%- set neg = is_number(pr0) and (pr0 | float(0)) < thr -%}
{%- set cur = is_state('input_boolean.zendure_ems_afgeschaald', 'on') -%}
{%- set f = namespace(full=true, online=false, low=false) -%}
{%- for i in __SETS__ -%}
  {%- set rep = 'sensor.zendure_set' ~ i ~ '_rapport' -%}
  {%- set pr = state_attr(rep, 'properties') -%}
  {%- if has_value(rep) and pr is mapping and pr.electricLevel is number
        and is_state('input_boolean.zendure_set' ~ i ~ '_laden', 'on') -%}
    {%- set maxs = states('input_number.zendure_set' ~ i ~ '_max_soc') | float(100) -%}
    {%- set f.online = true -%}
    {%- if pr.electricLevel < maxs - 1 -%}{%- set f.full = false -%}{%- endif -%}
    {%- if pr.electricLevel < maxs - 5 -%}{%- set f.low = true -%}{%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- set full = f.online and f.full -%}
{%- if mode == 'Direct' -%}
  {{ neg }}
{%- elif mode == 'Bij volle accu' -%}
  {{ neg and ((not f.low) if cur else full) }}
{%- else -%}
  {{ false }}
{%- endif -%}
"""


# EV charging plan ("Goedkoop van het net"): the cheapest quarters until the departure time,
# enough to deliver what the car still needs. Needed energy comes from the car's SOC sensor
# (target % of the battery, 10 % charging losses) or, without it, from a fixed kWh per window
# minus what was already delivered since the last departure time.
# EV power (W) as measured by the charger plug.
EV_NOW = r"""
{%- set evs = states('input_text.zendure_ems_ev_sensor') | trim -%}
{{ ([(states(evs) | float(0)) * (1000 if state_attr(evs, 'unit_of_measurement') == 'kW' else 1), 0] | max | round(0))
   if evs.startswith('sensor.') and is_number(states(evs)) else 0 }}
"""


# smartMode watchdog: sets whose report shows smartMode != 1 (flash), to be put back on RAM.
SMARTMODE_BACK = r"""
{%- set out = namespace(list=[]) -%}
{%- for i in __SETS__ -%}
  {%- set rep = 'sensor.zendure_set' ~ i ~ '_rapport' -%}
  {%- set pr = state_attr(rep, 'properties') -%}
  {%- set sn = state_attr(rep, 'sn') -%}
  {%- set ip = states('input_text.zendure_set' ~ i ~ '_ip') | trim -%}
  {#- a set put in standby on purpose (idle, standby delay on) stays on smartMode 0 -#}
  {%- set idle = is_state('binary_sensor.zendure_set' ~ i ~ '_inactief', 'on')
                 and states('input_number.zendure_ems_standby_vertraging') | float(0) > 0 -%}
  {%- if sn and ip and has_value(rep) and pr is mapping and pr.smartMode is number and pr.smartMode != 1 and not idle -%}
    {%- set out.list = out.list + [{'id': i, 'ip': ip, 'sn': sn}] -%}
  {%- endif -%}
{%- endfor -%}
{{ out.list }}
"""


# Profiles: named sets of settings, applied by the automation 'Zendure EMS: profiel activeren'.
# Keys: m = modus, sl/so/np = slim laden / slim ontladen / laden bij negatieve prijs (1/0),
# lp/op/vp = laden onder / alleen ontladen boven / verkopen boven (EUR/kWh), ms = minimale winst,
# sw = slijtage, af = afschalen. A profile only sets the keys it names.
PROFILES = r"""
{%- set hp = states('input_number.zendure_ems_handel_prijs') | float(0.35) -%}
{%- set base = {'lp': -0.5, 'op': -0.5, 'np': 1} -%}
{{ {
  'Nul op de meter': {'m': 'Nul op de meter'},
  'Dynamisch NOM': dict(base, m='Prijsgestuurd', sl=1, so=0, vp=1.0, vk=0),
  'Dynamisch NOM (Duur)': dict(base, m='Prijsgestuurd', sl=1, so=1, vp=1.0, vk=0),
  'Dynamisch Handelen': dict(base, m='Prijsgestuurd', sl=1, so=1, vp=hp, vk=1),
  'Dynamisch Handelen + NOM': dict(base, m='Prijsgestuurd', sl=1, so=0, vp=hp, vk=1),
  'Stand-by': {'m': 'Uit (stand-by)'},
} | to_json }}
"""

# The settings as they are now, in profile keys.
PROFILE_NOW = r"""
{%- set p = 'input_number.zendure_ems_' -%}
{{ {'m': states('input_select.zendure_ems_modus'),
    'sl': 1 if is_state('input_boolean.zendure_ems_slim_laden', 'on') else 0,
    'so': 1 if is_state('input_boolean.zendure_ems_slim_ontladen', 'on') else 0,
    'np': 1 if is_state('input_boolean.zendure_ems_laden_negatieve_prijs', 'on') else 0,
    'vk': 1 if is_state('input_boolean.zendure_ems_verkoop_plannen', 'on') else 0,
    'lp': states(p ~ 'laadprijs') | float(-0.5), 'op': states(p ~ 'ontlaadprijs') | float(-0.5),
    'vp': states(p ~ 'verkoopprijs') | float(1.0), 'ms': states(p ~ 'min_spread') | float(0.05),
    'sw': states(p ~ 'slijtage') | float(0.03), 'af': states('input_select.zendure_ems_afschalen')} | to_json }}
"""


def inline(name, tpl):
    """Template fragment that renders `tpl` (which outputs JSON) into the variable `name`."""
    return ("{%- set " + name + "_j -%}\n" + tpl.strip("\n") + "\n{%- endset -%}\n"
            "{%- set " + name + " = " + name + "_j | trim | from_json -%}\n")


PROFILE_MATCH = inline("now", PROFILE_NOW) + inline("pr", PROFILES) + r"""
{%- set own = namespace(d={}) -%}
{%- for k in ['1', '2'] -%}
  {%- set raw = states('input_text.zendure_ems_mijn_profiel_' ~ k) -%}
  {%- if raw.startswith('{') -%}{%- set own.d = dict(own.d, **{'Mijn profiel ' ~ k: raw | from_json}) -%}{%- endif -%}
{%- endfor -%}
{%- set all = dict(own.d, **pr) -%}
{%- set f = namespace(name='Aangepast') -%}
{%- for name, prof in all.items() -%}
  {%- if f.name == 'Aangepast' and prof | count > 0 -%}
    {%- set ok = namespace(v=true) -%}
    {%- for k, v in prof.items() -%}
      {%- set c = now[k] if k in now else none -%}
      {%- if (c is number and v is number and (c - v) | abs > 0.0001) or ((c is not number or v is not number) and c != v) -%}
        {%- set ok.v = false -%}
      {%- endif -%}
    {%- endfor -%}
    {%- if ok.v -%}{%- set f.name = name -%}{%- endif -%}
  {%- endif -%}
{%- endfor -%}
{{ f.name }}
"""

PROFILE_PICK = inline("pr", PROFILES) + r"""
{%- if naam in pr -%}
  {{ pr[naam] }}
{%- else -%}
  {%- set raw = states('input_text.zendure_ems_mijn_profiel_' ~ naam[-1]) -%}
  {{ (raw | from_json) if raw.startswith('{') else {} }}
{%- endif -%}
"""


for _n in ("BATT", "CONTROL", "PRICE", "SOC_LIMITS"):
    globals()[_n] = globals()[_n].replace("__CALIB_PRE__", CALIB_PRE.strip("\n")).replace("__CALIB__", CALIB.strip("\n"))

# Calibration status for the dashboard
CALIB_STATUS = r"""
{%- set k = namespace(bezig=[], laat=[], volg=[], oud=none) -%}
__CALIB_PRE__
{%- for i in __SETS__ -%}
__CALIB__
  {%- set kip = states('input_text.zendure_set' ~ i ~ '_ip') | trim -%}
  {%- if kip not in ['', 'unknown', 'unavailable'] -%}
  {%- if kal and has_value('sensor.zendure_set' ~ i ~ '_rapport') -%}{%- set k.bezig = k.bezig + [i] -%}{%- endif -%}
  {%- if lvok and kdg >= kmax and not kal -%}{%- set k.laat = k.laat + ['set ' ~ i ~ ' (' ~ kdg ~ ' dagen)'] -%}{%- endif -%}
  {%- if lvok and (k.oud is none or kdg > k.oud) -%}{%- set k.oud = kdg -%}{%- endif -%}
  {%- if not lvok -%}{%- set k.oud = 999 -%}{%- endif -%}
  {%- if lvok and km != 'Uit' -%}{%- set k.volg = k.volg + [t0 + ([kmax - kdg, 1 if lv >= t0 else 0] | max) * 86400] -%}{%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- if kwk > 0 and kwd > 0 -%}
  {#- next chosen weekday on which the oldest set is due again (1, 2 or 3 weeks) -#}
  {%- set dl = (kwd - now().isoweekday()) % 7 -%}
  {%- set w = namespace(d=(0 if k.bezig | count > 0 else (dl if dl > 0 else 7))) -%}
  {%- if k.bezig | count == 0 and k.oud is not none -%}
    {%- for x in range(3) -%}
      {%- if k.oud + w.d < 7 * kwk - 4 -%}{%- set w.d = w.d + 7 -%}{%- endif -%}
    {%- endfor -%}
  {%- endif -%}
  {%- set k.volg = k.volg + [t0 + w.d * 86400] -%}
{%- elif km == 'Op datum' -%}
  {%- set dt = state_attr('input_datetime.zendure_ems_kalibratie_datum', 'timestamp') | float(0) -%}
  {%- if dt >= t0 + (86400 if k.bezig | count == 0 and dt < t0 + 86400 else 0) -%}{%- set k.volg = k.volg + [dt] -%}{%- endif -%}
{%- endif -%}
{%- set dagen = ['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo'] -%}
{%- if k.bezig | count > 0 -%}
  Bezig: set {{ k.bezig | join(', ') }} naar 100 %
{%- elif k.laat | count > 0 -%}
  Te laat: {{ k.laat | join(', ') }}
{%- elif km == 'Uit' -%}
  Uit
{%- elif k.volg | count > 0 -%}
  {%- set nx = k.volg | min -%}
  Volgende: {{ dagen[(nx | timestamp_custom('%u') | int) - 1] }} {{ nx | timestamp_custom('%d-%m') }}
{%- else -%}
  Wacht op eerste keer 100 %
{%- endif -%}
"""
CALIB_STATUS = CALIB_STATUS.replace("__CALIB_PRE__", CALIB_PRE.strip("\\n")).replace("__CALIB__", CALIB.strip("\\n"))
