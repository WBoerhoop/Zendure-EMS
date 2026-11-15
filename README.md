[README.md](https://github.com/user-attachments/files/34856266/README.md)
# Zendure EMS voor Home Assistant (v1.14.5)

Nul op de meter en sturing op dynamische prijzen voor **1 tot 4 Zendure SolarFlow-sets**,
volledig in YAML: geen Python, geen HACS, geen extra kaarten.

## Mogelijkheden

- **Nul op de meter**: sets laden van zonne-overschot en ontladen voor eigen verbruik (PD-regelaar, reageert op elke meterwaarde).
- **1, 2, 3 of 4 sets** tegelijk, met een eigen modus per set.
- **Zeven modi**: Niet aansturen, Uit (stand-by), Nul op de meter, Prijsgestuurd, Alleen slim opladen, Alleen slim ontladen, Laden/Ontladen met vol vermogen.
- **Prijsgestuurd**: verkopen aan het net bij hoge prijs, laden van het net bij lage of negatieve prijs, accu vasthouden voor een duurder moment.
- **Planner per kwartier**: kiest de beste laad- en ontlaadkwartieren op basis van dynamische prijzen (o.a. Nordpool), verwacht verbruik en zonneverwachting.
- **Lerende zonnecorrectie** op de Forecast.Solar-verwachting.
- **Zonnepanelen afschalen** bij een negatieve terugleverprijs.
- **Profielen**: sla instellingen op en activeer ze met één keuze.
- **Standby na inactiviteit**: een set zonder werk gaat vanzelf in standby om stroom te besparen.
- **SOC-grenzen** (min/max) per set, geschreven naar de set zelf.
- **Beveiligingen**: sets op 0 W bij vrijgeven of afsluiten, bewaking van smartMode (RAM, spaart het flashgeheugen), automatische terugkeer naar de vorige modus na vol laden of ontladen.
- **BMS-kalibratie**: houdt per set bij wanneer de accu voor het laatst 100 % bereikte.
- **Dashboard** met overzicht, energiestroom, planner, laadtoestand per set en energie van vandaag; ook bruikbaar op een wandtablet.
- **Energiedashboard-integratie** en 12 automatiseringen, allemaal met het voorvoegsel *Zendure EMS:*.
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

Gebaseerd op [Omnibattery](https://github.com/ffunes/omnibattery) en Gielz
Licentie: GPL-3.0.
