# Zendure EMS: Home Assistant-package in YAML

Nul op de meter en sturing op dynamische prijzen voor **1, 2 of 3 Zendure SolarFlow-sets**
(2400 AC+ / 2400 AC Pro; andere SolarFlow-modellen werken via dezelfde lokale API).
Alles in YAML: geen Python, geen HACS en geen extra kaarten.

Gebaseerd op de regelaanpak en de Zendure-API-kennis van
[Omnibattery](https://github.com/ffunes/omnibattery) (GPL-3.0). Dit package valt daarom ook onder GPL-3.0.

> **Let op:** dit package stuurt het laad- en ontlaadvermogen van je batterijen. Gebruik het op eigen risico
> en begin altijd met lage vermogens (zie *Eerste keer testen*).

## Nieuw in versie 1.13.1: minder relaisschakelingen bij het bijschakelen van een extra set

* **Minimale aan- en uittijd per set bij het bijschakelen.** Tot en met 1.13.0 kon een tweede of derde set om de paar
  seconden aan en uit gaan als de vraag rond de drempel *Volgende set inzetten vanaf* schommelde (een waterkoker, een
  droger met een element dat aan- en uitslaat, of het even doorschieten van de regeling na zo'n piek). Elke keer is
  dat een relaisklik in die set. Nu geldt:
  * een set die erbij komt, blijft **minstens 2 minuten** meedoen, zolang de richting (laden of ontladen) gelijk blijft;
  * een set die afvalt, komt **pas na 1 minuut** terug, tenzij de sets die nog draaien de vraag niet aankunnen
    (dan direct, zoals voorheen);
  * slaat de richting om (bijvoorbeeld van ontladen naar laden van zonne-overschot), dan houdt de minimale aantijd de
    set niet vast: die zou anders juist een extra relaisschakeling maken.
* In een simulatie met een vraag die elke 20 s tussen 900 en 1700 W schommelt (twee sets, drempel 60 %), daalt het
  aantal schakelingen in 10 minuten van 57 naar 9.
* De tijden van de laatste wissel per set staan in het nieuwe attribuut `set_wissel` van `sensor.zendure_ems_regelaar`.
* Er zijn geen nieuwe instellingen; je bestaande instellingen blijven ongewijzigd. Het dashboard is alleen in het
  versienummer veranderd: plak `dashboards/dashboard.yaml` toch opnieuw, anders meldt het dashboard dat package en
  dashboard niet dezelfde versie hebben.
* Tip bij veel schakelingen door een droger of waterkoker: zet ook *Korte dips negeren* aan (Instellingen → Regeling,
  bijvoorbeeld 30 s). Dan schakelt een set na zo'n piek niet een paar seconden naar laden.

## Eerdere versies

Alle wijzigingen per versie staan in [CHANGELOG.md](CHANGELOG.md).

## Inhoud

| Bestand | Wat |
|---|---|
| `packages/zendure_ems.yaml` | Package voor 1, 2 of 3 sets |
| `dashboards/dashboard.yaml` | Dashboard voor 1, 2 of 3 sets |
| `Zendure-EMS-handleiding.docx` | Volledige handleiding met alle velden |
| `CHANGELOG.md` | Alle wijzigingen per versie |
| `generator/`, `tests/` | Generator en tests (alleen nodig als je het package wilt aanpassen) |

Vul alleen de IP-adressen in van de sets die je hebt: een set zonder IP-adres wordt niet aangestuurd en niet getoond.

## Vereisten

* Home Assistant **2025.1 of nieuwer**.
* Elke SolarFlow is lokaal bereikbaar. Test dit in je browser: `http://IP-VAN-DE-SET/properties/report`
  moet JSON tonen met `"properties"`. Geef elke set een **vast IP-adres** (DHCP-reservering in je router).
* In de Zendure-app staat **HEMS UIT** op elke set. Met HEMS aan overschrijft de set de opdrachten na ~10 s.
* **Eén** sensor voor het netvermogen in W of kW, met positief = afname en negatief = teruglevering.
  Voorbeelden: HomeWizard P1 `sensor.p1_meter_power`, of een eigen template (zie hieronder).
  Heb je een HomeWizard P1? Vul dan ook het **IP-adres van de P1** in: het package leest hem dan zelf elke seconde
  uit in plaats van elke 5 s (zie versie 1.12.2 in [CHANGELOG.md](CHANGELOG.md)).
  Kan het nettovermogen alleen omgekeerd worden gemeten? Zet dan *Netmeter omkeren* aan.
* Voor de prijssturing: een prijssensor met de prijzen als attributen:
  * **Nordpool (HACS)**: attributen `raw_today` / `raw_tomorrow`
  * **Zonneplan ONE**: attribuut `forecast` (bv. `sensor.zonneplan_current_electricity_tariff`)
  * **ENTSO-e**: attributen `prices_today` / `prices_tomorrow`

  De officiële *Nord Pool*-integratie van HA heeft die attributen niet en werkt daarom niet.
  Kwartierprijzen en uurprijzen werken allebei; uurprijzen worden in vier kwartieren gesplitst.
* Optioneel voor de planner: een **zonneverwachting** via de integratie **Forecast.Solar**
  (*Instellingen → Apparaten & diensten → Integratie toevoegen → Forecast.Solar*). De planner gebruikt:
  * `sensor.energy_production_today_remaining`: verwachte opbrengst voor de rest van vandaag (kWh)
  * `sensor.energy_production_tomorrow`: verwachte opbrengst morgen (kWh)

  Bestaan die sensoren bij de eerste start, dan worden ze automatisch ingevuld. Forecast.Solar geeft in
  Home Assistant alleen dagtotalen. De planner verdeelt die over de kwartieren tussen zonsopkomst en
  zonsondergang (uit `sun.sun`), met een zonneboog die rond het middaguur het hoogst is.

  **Twee of meer panelenvelden** (bv. oost en west) geven aparte sensoren (`..._2`). Maak dan per dag één som-sensor
  met de helper *Combineer de status van verschillende sensoren* (type *Som*), of met deze template, en vul die in:
  ```yaml
  template:
    - sensor:
        - name: "Zon resterend vandaag totaal"
          unit_of_measurement: "kWh"
          state: >-
            {{ states('sensor.energy_production_today_remaining') | float(0)
             + states('sensor.energy_production_today_remaining_2') | float(0) }}
        - name: "Zon morgen totaal"
          unit_of_measurement: "kWh"
          state: >-
            {{ states('sensor.energy_production_tomorrow') | float(0)
             + states('sensor.energy_production_tomorrow_2') | float(0) }}
  ```
  Solcast werkt ook: de verwachting per halfuur (`detailedForecast`) wordt dan automatisch herkend.

### Netsensor maken uit DSMR (afname en teruglevering apart)

Zet dit in `configuration.yaml` (namen aanpassen aan jouw sensoren) en gebruik daarna `sensor.netvermogen`:

```yaml
template:
  - sensor:
      - name: "Netvermogen"
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        state: >-
          {{ ((states('sensor.electricity_meter_power_consumption') | float(0))
            - (states('sensor.electricity_meter_power_production') | float(0))) * 1000 }}
```

Een snelle meter (1 seconde) werkt het best. Een meter die maar elke 10 s bijwerkt, werkt ook, maar reageert trager.

## Installatie

1. Zet in `configuration.yaml` (als dat er nog niet staat):
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
2. Kopieer `zendure_ems.yaml` naar `config/packages/`. Staat daar nog `zendure_ems_2sets.yaml` of
   `zendure_ems_3sets.yaml` van een oudere versie, verwijder die dan.
3. **Aanbevolen:** houd de grote rapport-sensoren en de regelaar uit de database (die veranderen elke 5 s).
   Voeg in `configuration.yaml` toe (of vul je bestaande `recorder:`-blok aan):
   ```yaml
   recorder:
     exclude:
       entity_globs:
         - sensor.zendure_set*_rapport
         - sensor.zendure_ems_weergave_*
       entities:
         - sensor.zendure_ems_regelaar
         - sensor.zendure_ems_planning
         - sensor.zendure_ems_netmeting
         - sensor.zendure_ems_p1_vermogen
         - sensor.zendure_ems_netvermogen
         - sensor.zendure_ems_huisverbruik
   ```
   (`sensor.zendure_ems_netmeting` is een kopie van je P1-meter die elke seconde verandert; de P1-meter zelf wordt al
   bewaard. `sensor.zendure_ems_p1_vermogen` is de P1 die het package zelf elke seconde uitleest
   (alleen als je het IP-adres van de P1 invult). `sensor.zendure_ems_netvermogen` en `sensor.zendure_ems_huisverbruik`
   veranderen met een snelle meter ook elke seconde; de grafieken gebruiken sinds 1.12.3 de rustige kopieën
   `sensor.zendure_ems_grafiek_net` en `_huis` (elke 5 s), die wel bewaard blijven. `sensor.zendure_ems_planning` heeft de hele kwartierplanning als attribuut. Vanaf 1.8.2 staat die niet meer
   in `sensor.zendure_ems_stroomprijs`; die blijft bewaard voor de grafieken op het tabblad Statistieken.
   Had je `sensor.zendure_ems_stroomprijs` in de exclude staan, vervang hem dan door `sensor.zendure_ems_planning`.)
4. Controleer de configuratie (*Ontwikkelaarshulpmiddelen → YAML → Configuratie controleren*) en **herstart** Home Assistant.
5. Na de herstart zet het package alle instellingen eenmalig op hun standaardwaarde. De modus staat dan op **Niet aansturen**.
6. Dashboard: *Instellingen → Dashboards → Dashboard toevoegen → Nieuw dashboard*. Open het, kies het potlood →
   ⋮ → *Raw-configuratie-editor* en plak de inhoud van `dashboard.yaml`.
7. Vul op het tabblad **Instellingen** van het dashboard in:
   * het IP-adres van elke set
   * de netmeter-sensor, bijvoorbeeld `sensor.p1_meter_power`
   * de prijssensor (optioneel)
   * de capaciteit per accupack (AB3000 = 2,88 kWh; het aantal packs leest het package zelf uit)
   * optioneel: de zonneverwachting voor vandaag en morgen, en een zonneproductie-sensor

Tot de IP-adressen zijn ingevuld, meldt het logboek dat de rapporten niet opgehaald kunnen worden. Dat is normaal.

## Modi

| Modus | Wat er gebeurt |
|---|---|
| **Niet aansturen** | Het package stuurt niets. Bij het kiezen van deze modus krijgen alle sets eenmalig 0 W. |
| **Uit (stand-by)** | Alle sets op 0 W. |
| **Nul op de meter** | De sets laden van zonne-overschot en ontladen voor eigen verbruik, zodat het net rond 0 W blijft. |
| **Prijsgestuurd** | Als nul op de meter, maar met prijsacties (zie hieronder). |
| **Alleen slim opladen** | Nul op de meter zonder ontladen: alleen zonne-overschot laden. |
| **Alleen slim ontladen** | Nul op de meter zonder laden: alleen ontladen voor eigen verbruik. |
| **Laden / Ontladen (vol vermogen)** | Alle sets laden van of ontladen naar het net op hun maximale vermogen. |

Per set kun je ook een **eigen modus** kiezen (*Alleen slim opladen* of *Alleen slim ontladen*, op de setkaart);
*Volgt EMS-modus* = de set doet wat de modus hierboven zegt. Zie versie 1.13.0 in [CHANGELOG.md](CHANGELOG.md).

### Prijsacties (modus Prijsgestuurd)

Het package kiest elke minuut één actie, in deze volgorde:

1. **Verkopen aan het net**: als de prijs ≥ *Verkopen aan het net boven* (1,00 = uit). Alle sets op vol vermogen ontladen.
2. **Laden van het net**:
   * bij een negatieve prijs (schakelaar *Laden bij negatieve prijs*), of
   * als de prijs ≤ *Laden van het net onder* (‑0,50 = uit), of
   * in een kwartier dat de **planner** heeft gekozen (schakelaar *Slim laden*, zie hieronder).
3. **Accu vasthouden** (niet ontladen, wel zonne-overschot laden):
   * als de prijs < *Alleen ontladen boven* (‑0,50 = altijd ontladen), of
   * in een kwartier waarin de planner de energie bewaart voor een duurder kwartier (*Slim laden* of *Slim ontladen*).
4. Anders: **nul op de meter**.

### De planner (per kwartier)

Elke 5 minuten (en bij elke wijziging van een instelling) rekent de planner alle kwartieren door waarvoor
prijzen bekend zijn (tot maximaal 36 uur vooruit):

1. **Verbruik per kwartier**: uit het **geleerde verbruiksprofiel**, apart voor werkdagen en weekend (elk
   96 kwartierwaarden). Het profiel leert elk kwartier van het gemeten huisverbruik. Een nieuw kwartier
   leert snel, daarna weegt elke dag voor 15 % mee. Een nog niet geleerd kwartier neemt de waarde uit het
   andere profiel, en anders *Verwacht verbruik*.
2. **Zon per kwartier**: uit de zonneverwachting, vermenigvuldigd met de geleerde zonnecorrectie (of, de
   eerste 3 dagen en zonder leren, *Zonneverwachting meetellen voor*, standaard 80 %).
3. **Simulatie**: de opgeslagen energie wordt kwartier voor kwartier doorgerekend. Zonne-overschot laadt
   de accu (tot de max SOC), verbruik trekt hem leeg (tot de min SOC). Rendementsverlies telt mee: met het
   gemeten rendement per set (capaciteitsgewogen, zie hieronder), of met het vaste *Rendement heen en terug*.
4. **Tekort oplossen op de goedkoopste manier**: raakt de accu in een kwartier te kort, dan kiest de planner
   uit alle eerdere kwartieren de goedkoopste oplossing:
   * **vasthouden** (*Slim ontladen*): in een goedkoper kwartier ontlaadt de accu niet, het net voedt daar het
     huis en de energie blijft bewaard. Loont als *prijs dan + minimale winst* ≤ prijs van het tekortkwartier.
   * **laden van het net** (*Slim laden*): loont als *prijs dan ÷ rendement + slijtagekosten + minimale winst*
     ≤ prijs van het tekortkwartier.

   **Rendement:** met *Gemeten rendement per set gebruiken* aan neemt de planner het capaciteitsgewogen gemiddelde
   van de retourrendementen die de sets via de Zendure-integratie melden (`sensor.zendure_ems_rendement`). De energie
   wordt in de planning over de sets verdeeld naar hun capaciteit, dus dat gemiddelde is het verlies van een
   gemiddelde kWh. Een set zonder geldige meting telt met het vaste *Rendement heen en terug*.

   De energie moet tussen bron- en tekortkwartier in de accu passen: vult de zon de accu toch al, dan wordt
   er niet van het net geladen. Bij gelijke kosten kiest hij het laatste kwartier. Goedkope kwartieren
   daartussen waarin de accu leeg zou zijn, worden ook vastgehouden.
5. Het resultaat is een vast plan per kwartier (laden, vasthouden of accu laten leveren), dus geen
   heen-en-weer schakelen. Het laadvermogen wordt zo gekozen dat precies de geplande kWh geladen wordt.

De tabel **Planner** op het dashboard laat per uur zien: prijs, verwachte zon, verwacht verbruik, verwachte SOC
aan het eind van het uur, en het plan (🔌 laden, ⏸ vasthouden, 🔋 accu levert, 🏠 net levert).

Voor een goed verbruiksprofiel moet het huisverbruik kloppen: *huisverbruik = netmeter − accu + zonneproductie*.
Heb je zonnepanelen die niet via de Zendure lopen? Vul dan bij *Zonneproductie-sensor* de omvormer-sensor in.
Zonder die sensor leert het profiel overdag het verbruik **na aftrek van de zon**. Zet dan
*Zonneverwachting meetellen voor* lager (bv. 30 %), of laat de zonneverwachting leeg.

Met *Max netafname bij netladen* bescherm je je hoofdzekering: tijdens netladen wordt het laadvermogen
verlaagd zodra huis + laden boven deze waarde komt (bijvoorbeeld 3 × 25 A ≈ 17.000 W, of lager voor 1-fase).

## Hoe de regeling werkt

* De automatisering **Zendure EMS: regeling** rekent het totale vermogen uit met een PD-regelaar op de
  netmeter (*Kp*, *Kd*, *dode zone*, *max stap*): bij elke nieuwe meterwaarde en in elk geval elke 5 s.
  Een Zendure voert een opdracht pas na ~2,5 s uit, en een netmeter laat het effect pas bij zijn volgende meting
  zien; daarom wacht de regeling na een opdracht eerst. Met *Wachttijd automatisch* (standaard aan) volgt die
  wachttijd uit het gemeten meterinterval: 2,5 s + 0,7 × interval, minimaal 3 s, hoogstens 10 s. Anders geldt
  *Wachttijd na opdracht* (standaard 3 s). Een snelle voorcontrole zorgt dat er alleen gerekend wordt
  als de meter echt iets nieuws laat zien.
* **Minimaal vermogen per set** (standaard 100 W): kleinere vragen laat de regeling aan het net. Is de vraag
  groot genoeg (minimaal vermogen − dode zone, dus standaard 65 W, twee metingen op rij), dan start een set direct op
  het minimum en blijft daar rustig staan.
* **Verdeling:** bij weinig vermogen werkt één set (bij ontladen de volste, bij laden de leegste; een set die al in
  de goede richting staat krijgt voorrang tot 15 % SOC-verschil, zodat er geen acMode naar het flashgeheugen hoeft). Een
  volgende set doet mee zodra de vraag boven *Volgende set inzetten vanaf* (standaard 60 %) van de actieve sets komt.
  0 % = altijd alle sets. Tussen actieve sets wordt zo verdeeld dat hun SOC naar elkaar toe groeit.
  Een bijgeschakelde set blijft minstens 2 minuten meedoen (zolang de richting gelijk blijft) en een afgevallen set
  komt pas na 1 minuut terug, tenzij de andere sets de vraag niet aankunnen. Zo gaat een set niet steeds aan en uit
  als de vraag rond de drempel schommelt (sinds 1.13.1).
* **Rendement bij de keuze van de set:** met een gemeten rendement per set (Zendure-integratie, *Gemeten rendement per
  set gebruiken*) krijgt de zuinigere set voorrang: per % rendement boven het gemiddelde van de sets die mogen meedoen
  telt hij alsof hij 2 SOC-punten voller (bij ontladen) of leger (bij laden) is, hoogstens 10. Bij een klein
  SOC-verschil doet dus de zuinige set het werk; bij een groter verschil beslist de SOC, zodat de sets niet uit elkaar
  lopen. Zonder meting, of met maar één gemeten set, verandert er niets.
* Een set die vol, leeg, uitgeschakeld of onbereikbaar is, doet niet mee. De rest neemt het over.
* Opdrachten gaan alleen naar een set als zijn vermogen meer dan 15 W moet veranderen, en worden
  in het RAM gezet (`smartMode=1`): dat geeft geen slijtage van het flashgeheugen.
* **Min/max SOC** per set wordt ook in de set zelf opgeslagen (minSoc 5–50 %, socSet 70–100 %), maar alleen als
  de waarde afwijkt.
* De set-eigen grenzen uit de Zendure-app (max uitgangsvermogen, max laadvermogen) blijven gelden:
  het package neemt steeds de laagste van die grenzen en de grenzen in het dashboard.
* **Veiligheid:** is de netmeter weg of al meer dan 60 s niet bijgewerkt, dan gaan alle sets naar 0 W.
  Bij het afsluiten van Home Assistant krijgen alle sets 0 W.

## Automatiseringen in het package

`packages/zendure_ems.yaml` maakt de volgende 12 automatiseringen aan. Je vindt ze onder
*Instellingen → Automatiseringen en scènes*; ze beginnen allemaal met *Zendure EMS:*. Omdat ze in het package
staan, kun je ze daar niet bewerken (wel aan- en uitzetten en de traces bekijken). Dit overzicht staat ook in hoofdstuk 13 van de handleiding.

| Automatisering | Wanneer | Wat ze doet |
|---|---|---|
| **regeling** | Bij elke nieuwe meterwaarde en in elk geval elke 5 s | Het hart van het package: rekent met de PD-regelaar het vermogen per set uit (nul op de meter en prijsacties) en stuurt de opdrachten naar de sets. |
| **sets op 0 W bij vrijgeven of afsluiten** | Modus wordt *Niet aansturen*, of Home Assistant stopt | Geeft alle sets eenmalig 0 W, zodat ze niet op het laatste vermogen blijven doorlopen. |
| **SOC-grenzen naar de sets schrijven** | 5 s na het wijzigen van een min/max SOC, en elke 10 min | Schrijft min/max SOC naar de sets zelf (blijft bewaard na een herstart), alleen als de waarde in de set afwijkt. |
| **standaardwaarden instellen** | Bij het starten van Home Assistant, of als je *standaardwaarden ingesteld* uitzet | Zet bij de eerste installatie eenmalig alle instellingen op hun standaardwaarde. Uitzetten van de schakelaar = opnieuw beginnen. |
| **velden na een update instellen** | Bij het starten van Home Assistant en elke 10 min | Geeft na een update alleen de nieuwe velden eenmalig hun standaardwaarde en toont een melding met de wijzigingen. Bestaande instellingen blijven ongewijzigd. |
| **modus vóór laden/ontladen met vol vermogen onthouden** | Modus wordt *Laden (vol vermogen)* of *Ontladen (vol vermogen)* | Onthoudt de modus van daarvoor, zodat het package daar later naar terug kan. |
| **na laden/ontladen met vol vermogen terug naar de vorige modus** | Accu 2 minuten vol (bij laden) of leeg tot min SOC + reserve (bij ontladen) | Zet de modus terug op de onthouden modus, of op *Nul op de meter*. |
| **100 % bereikt bijhouden** | Elke 2 min | Legt per set de datum vast waarop de accu voor het laatst 100 % bereikte (BMS-kalibratie). Je kunt de datum ook zelf invullen. |
| **smartMode (RAM) bewaken** | Elke minuut, en als *limieten naar flash schrijven* uitgaat | Zet smartMode weer op 1 als de firmware hem op 0 heeft gezet terwijl de regeling actief is, zodat limieten naar het RAM gaan en niet naar het flashgeheugen. |
| **sets in standby na inactiviteit** | Een set staat langer dan *standby na inactiviteit* (minuten) op 0 W | Zet die set eenmalig in standby (smartMode 0, beide limieten 0) zodat hij minder verbruikt. Vraagt de regeling weer vermogen, dan gaat de set met smartMode 1 weer aan. |
| **profiel activeren** | Je kiest een profiel in de keuzelijst | Zet de instellingen van dat profiel (modus, slim laden/ontladen, prijsdrempels, minimale winst, slijtage, afschalen) en zet de keuzelijst terug op *Kies een profiel*. |
| **zonnepanelen afschalen bij negatieve prijs** | Bij wijziging van terugleverprijs, gemiddelde SOC of afschaalinstellingen, elke minuut en bij het starten | Schaalt bij een negatieve prijs de omvormer af naar het huisverbruik en zet een extra apparaat op zijn afgeschaalde limiet (direct, of pas als alle sets vol zijn). Zet alles terug zodra de prijs weer boven de drempel komt. |

Zet je een van deze automatiseringen uit, dan valt de bijbehorende functie weg. Zet **regeling** alleen uit als je
de sets tijdelijk helemaal niet wilt aansturen; de modus *Niet aansturen* is daarvoor meestal de betere keuze.

## Eerste keer testen

1. Laat de modus op **Niet aansturen** en vul de instellingen in. Controleer op het dashboard dat SOC,
   vermogen en temperatuur van elke set kloppen.
2. Zet bij elke set *Max laadvermogen* en *Max ontlaadvermogen* op bijvoorbeeld 300 W.
3. Kies **Nul op de meter** en kijk een paar minuten naar de grafiek *Vermogen*: het netvermogen moet
   rond 0 W gaan liggen en de status moet kloppen.
4. Verhoog daarna stap voor stap de vermogens. Slingert het netvermogen? Verlaag dan *Kp*
   (bijvoorbeeld 0,5), of zet *Wachttijd automatisch* uit en verhoog *Wachttijd na opdracht* (bijvoorbeeld 6 s).
   Reageert het te traag? Verhoog *Kp* (max ~0,8).
5. Pas daarna **Prijsgestuurd** inschakelen. De tabel *Prijzen en plan* toont per uur de prijs en de geplande acties.

Klopt het teken van de netmeter niet (de accu ontlaadt bij teruglevering)? Zet dan direct de modus op
**Uit (stand-by)** en schakel *Netmeter omkeren* in.

## Energiedashboard

`sensor.zendure_ems_energie_geladen` en `sensor.zendure_ems_energie_ontladen` (kWh) kun je bij
*Instellingen → Dashboards → Energie → Thuisbatterij* toevoegen.

## Aanpassen

De YAML is gegenereerd. Wil je iets in de logica aanpassen, wijzig dan `ontwikkeling/templates.py` of
`generate.py` en draai `python3 generate.py out`. De tests (`ontwikkeling/tests`, met pytest, jinja2 en pyyaml)
draaien de templates tegen gesimuleerde sets.

## Problemen

| Symptoom | Oorzaak / oplossing |
|---|---|
| Rapport-sensor blijft *onbekend* | IP klopt niet, of de lokale API is niet bereikbaar: test `http://IP/properties/report` |
| Set volgt opdrachten na 10 s niet meer | HEMS staat nog aan in de Zendure-app |
| Status *Geen (verse) netmeting* | Verkeerde netsensor-naam, of de sensor werkt niet meer bij |
| Ontladen blijft steken op 800 W | Max uitgangsvermogen staat in de Zendure-app op 800 W |
| Prijsactie blijft *Geen prijsdata* | Prijssensor heeft geen `raw_today`, `forecast` of `prices_today`-attribuut |
| Planner laadt nooit van het net | *Slim laden* staat uit, de prijsverschillen zijn kleiner dan *minimale winst* plus verlies en slijtage, of de zon dekt het tekort |
| Set springt bij heel kleine vraag aan en uit | Verhoog *Minimaal vermogen per set* of de *dode zone* |
| Veel relaisschakelingen bij een waterkoker of droger | Zet *Korte dips negeren* aan (bijvoorbeeld 30 s); vanaf 1.13.1 schakelt een extra set ook niet meer steeds bij en af. Verhoog eventueel *Volgende set inzetten vanaf* |
| Planner laadt terwijl de zon het zou doen | Controleer *zonbron* in de prijsactie-attributen; staat *Zonneverwachting meetellen voor* niet te laag? |
| Melding over te grote attributen in het log | Zet `sensor.zendure_ems_planning` in de recorder-exclude (zie installatie) |
