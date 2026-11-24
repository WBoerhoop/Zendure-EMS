# Zendure EMS voor Home Assistant (v1.19.1)

Nul op de meter en sturing op dynamische prijzen voor **1 tot 4 Zendure SolarFlow-sets**,
volledig in YAML: geen Python, geen HACS, geen extra kaarten.

## Mogelijkheden

- **Nul op de meter**: sets laden van zonne-overschot en ontladen voor eigen verbruik (PD-regelaar, reageert op elke meterwaarde).
- **1, 2, 3 of 4 sets** tegelijk, met een eigen modus per set.
- **Zeven modi**: Niet aansturen, Uit (stand-by), Nul op de meter, Prijsgestuurd, Alleen slim opladen, Alleen slim ontladen, Laden/Ontladen met vol vermogen.
- **Prijsgestuurd**: verkopen aan het net bij hoge prijs, laden van het net bij lage of negatieve prijs, accu vasthouden voor een duurder moment.
- **Planner per kwartier**: kiest de beste laad- en ontlaadkwartieren op basis van dynamische prijzen (Nordpool via HACS of een template-sensor op de officiële Nord Pool-integratie, Zonneplan ONE of ENTSO-e), verwacht verbruik en zonneverwachting.
- **Slim verdienmodel**: zon terugleveren als dat meer oplevert en de accu later vullen met overschot, verkopen die rekening houden met zon die de accu weer bijvult, en een eigen (lagere) minimale winst voor vasthouden. Vanaf 1.18.0 ook verkopen en later goedkoper terugkopen, ruimte maken voor laden bij een negatieve prijs, en een veiligheidsmarge op de zonneverwachting die zich aanpast aan hoe betrouwbaar de verwachting is.
- **Gepland tegenover werkelijk** (vanaf 1.18.0): per dag en per maand wat de planner verwachtte te besparen naast wat de accu echt bespaarde, met de laatste 12 maanden.
- **Bloktarief** (vanaf 1.17.0): vaste prijzen in tijdsblokken, zoals Eneco VoordeelMomenten, als prijsbron voor de planner, zonder prijssensor.
- **Lerende zonnecorrectie** op de Forecast.Solar-verwachting.
- **Zonneverwachting per uur** (vanaf 1.19.0): de uurverwachting van Forecast.Solar (of de kwartierwaarden van Open-Meteo) in plaats van een vaste zonneboog over het dagtotaal.
- **Minimale winst bijleren** (vanaf 1.19.0, schakelbaar): valt de werkelijke besparing structureel lager uit dan gepland, dan verhoogt de EMS zelf de minimale winst.
- **Feestdagen in het bloktarief** (vanaf 1.19.0, schakelbaar): via de Workday-integratie gebruikt een feestdag het weekendrooster.
- **Laden beperken bij kou** (vanaf 1.19.0, per set schakelbaar): lager laadvermogen als de koudste accupack koud is.
- **Zonnepanelen afschalen** bij een negatieve terugleverprijs.
- **Profielen**: sla instellingen op en activeer ze met één keuze; met *Snel laden* en *Snel ontladen* (vanaf 1.16.1) laden of ontladen alle sets direct op hun eigen max vermogen.
- **Seizoen** (vanaf 1.16.0): winter- en zomerwaarden voor minimale winst en slijtage bovenop elk profiel, bijvoorbeeld *Dynamisch NOM · Winter*. Op *Automatisch* kiest de EMS elke dag zelf, op basis van het verwachte zonoverschot in procent van je eigen accu.
- **Standby na inactiviteit**: een set zonder werk gaat vanzelf in standby om stroom te besparen.
- **SOC-grenzen** (min/max) per set, geschreven naar de set zelf.
- **Beveiligingen**: sets op 0 W bij vrijgeven of afsluiten, bewaking van smartMode (RAM, spaart het flashgeheugen), automatische terugkeer naar de vorige modus na vol laden of ontladen.
- **BMS-kalibratie**: houdt per set bij wanneer de accu voor het laatst 100 % bereikte en laat per set zien wanneer de volgende keer volladen is.
- **Dashboard** met overzicht, energiestroom, planner, laadtoestand per set en energie van vandaag; ook bruikbaar op een wandtablet. Alleen de sets met een IP-adres verschijnen, ook in de grafieken (vanaf 1.17.1).
- **Energiedashboard-integratie** en 13 automatiseringen, allemaal met het voorvoegsel *Zendure EMS:*.
- **Updatemelding** met wat er nieuw is; bestaande instellingen blijven bij een update behouden.

## Inhoud van het pakket

| Bestand | Doel |
|---|---|
| `packages/zendure_ems.yaml` | Het package zelf (in `config/packages/` plaatsen) |
| `dashboards/dashboard.yaml` | Dashboard (plakken in de Raw-configuratie-editor) |
| `LEESMIJ.md` | Installatie, modi, werking en problemen |
| `Zendure-EMS-handleiding.docx` | Volledige handleiding |
| `CHANGELOG.md` | Wijzigingen per versie |

## Snel starten

1. Zet `zendure_ems.yaml` in `config/packages/` (en zet `packages:` aan in `configuration.yaml`).
2. Herstart Home Assistant.
3. Plak `dashboards/dashboard.yaml` in een nieuw dashboard (Raw-configuratie-editor).
4. Begin met lage vermogens, zie *Eerste keer testen* in `LEESMIJ.md`.

> **Let op:** dit package stuurt het laad- en ontlaadvermogen van je batterijen. Gebruik het op eigen risico.

Gebaseerd op [Omnibattery](https://github.com/ffunes/omnibattery)  en GielZ. Licentie: GPL-3.0.
