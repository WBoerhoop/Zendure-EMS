# Zendure EMS: Home Assistant-package in YAML

Nul op de meter en sturing op dynamische prijzen voor **1, 2, 3 of 4 Zendure SolarFlow-sets**
(2400 AC+ / 2400 Pro / 4000 Mix; andere SolarFlow-modellen werken via dezelfde lokale API).
Alles in YAML: geen Python, geen HACS en geen extra kaarten.

Gebaseerd op de regelaanpak en de Zendure-API-kennis van
[Omnibattery](https://github.com/ffunes/omnibattery) (GPL-3.0). Dit package valt daarom ook onder GPL-3.0.

> **Let op:** dit package stuurt het laad- en ontlaadvermogen van je batterijen. Gebruik het op eigen risico
> en begin altijd met lage vermogens (zie *Eerste keer testen*).

## Nieuw in versie 1.19.2: geen "onbekende attributen" meer (Spook)

* *Werkdag of vrij* en *Zon per kwartier* worden nu altijd bijgewerkt, ook als de functie uit staat of de integratie
  ontbreekt; alleen de aanroep van Workday of Forecast.Solar gebeurt dan niet. Daardoor bestaan hun attributen altijd
  en meldt Spook ze niet meer als onbekend. Staat de functie uit, dan toont *Werkdag of vrij* **Uit**.
  Nodig: Home Assistant 2025.4 of nieuwer voor deze twee functies.
* Bij *Laden beperken bij kou* toont de kaart *Grenzen set N* nu de temperatuursensor van de set (per accupack in de
  details), zodat het dashboard geen attribuut leest van sets zonder IP-adres.
* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor. Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.19.1: geen "onbekende actie" zonder Workday of Forecast.Solar

* Zonder de Workday-integratie meldde Spook `workday.check_date` als onbekende actie in
  `sensor.zendure_ems_werkdagen`. Dat was onschuldig, maar is nu opgelost: de actienamen van de optionele integraties
  Workday en Forecast.Solar staan er als template in en worden pas ingevuld als de actie echt draait.
* Vervang `packages/zendure_ems.yaml` en herstart Home Assistant. Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.19.0: zon per uur, minimale winst bijleren, feestdagen, kou

Vier nieuwe mogelijkheden, elk met een eigen schakelaar:

* **Zonneverwachting per uur** (*Planner*, staat na de update aan): de planner gebruikt de uurverwachting van
  Forecast.Solar in plaats van een vaste zonneboog over het dagtotaal. Er hoeft niets ingesteld te worden: de
  Forecast.Solar-integratie wordt vanzelf gevonden (ook twee koppelingen, bv. twee daken). Open-Meteo Solar Forecast
  (HACS) werkt ook: vul de sensor met het attribuut `watts` in bij *Zonneverwachting vandaag/morgen*.
* **Minimale winst bijleren** (*Prijssturing*, staat uit): valt de werkelijke besparing over 14 dagen onder 80 % van
  gepland, dan verhoogt de EMS de minimale winst elke dag met 0,005 €/kWh (tot 0,05); valt hij hoger uit, dan gaat
  hij weer omlaag. Je eigen waarde, het profiel en het seizoen blijven staan; de correctie komt erbovenop.
* **Feestdagen als weekend** (*Aansluiting*, alleen bij Bloktarief, staat uit): installeer de integratie
  *Workday* (Instellingen → Apparaten & diensten → Integratie toevoegen → Workday, land Nederland) en vul de
  binary_sensor in. Op een feestdag geldt dan de regel *Bloktarief weekend* (die moet dus ingevuld zijn). Stap voor
  stap: [Feestdagen als weekend](#feestdagen-als-weekend-vanaf-1190).
* **Laden beperken bij kou** (*Grenzen set N*, per set, staat uit): voor sets op een koude plek. Het laadvermogen
  volgt de koudste accupack: 100 % vanaf 10 °C, lineair omlaag tot 30 % bij 0 °C en kouder (beide instelbaar).
* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor. Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.18.1: zuiniger uitlezen, rustigere status

* **Gepland tegenover werkelijk** telt nu aan beide kanten precies dezelfde kwartieren. In 1.18.0 telde werkelijk
  de hele maand mee, ook van vóór de update. Na deze update beginnen beide voor deze maand opnieuw bij 0; de kaart
  toont vanaf wanneer er geteld wordt.
* **Sets zonder IP-adres** maken geen verzoeken meer elke 5 s; alleen sets met een IP-adres worden uitgelezen.
* **Netmeter-bron** wordt elke 30 s bijgewerkt in plaats van elke seconde (de P1 zelf blijft elke seconde).
* **Status zonder aftellers**: *Minimale looptijd* en *Rusttijd na stoppen* zonder seconden in de tekst; de
  resterende tijd staat onder Status op het dashboard (attribuut `nog_seconden` van de regelaar).
* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor. Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.18.0: verkopen en terugkopen, ruimte voor goedkoop laden, lerende zonmarge

* **Verkopen en later goedkoper terugkopen** (bij *Verkopen plannen*). De planner verkoopt nu ook voorraad die
  later nog nodig is, als hij die tussendoor goedkoper kan terugkopen. Voorbeeld: volle accu, ochtendpiek
  € 0,38, 's middags een negatieve prijs, 's avonds € 0,40. Hij verkoopt 's ochtends, vult de accu 's middags
  tegen de negatieve prijs en heeft 's avonds weer genoeg. Reden op het dashboard: *Terugkopen na verkoop*.
* **Ruimte voor laden bij een lage of negatieve prijs**, ook zonder *Verkopen plannen*. De planner rekent nu mee
  dat de sets bij een negatieve prijs (of onder *Laden van het net onder*) op vol vermogen laden. *Slim ontladen*
  houdt de accu daardoor 's ochtends niet meer vast als hij 's middags toch goedkoop wordt gevuld.
* **Lerende veiligheidsmarge op de zonneverwachting**: in plaats van vast 75 % leert de planner uit de
  zonnecorrectie hoe betrouwbaar de verwachting is (tussen 50 en 90 %). Zie *De planner*, punt 7.
* **Gepland tegenover werkelijk**: op het tabblad Statistieken zie je per dag en per maand wat de planner
  verwachtte te besparen naast wat de accu echt bespaarde, met de laatste 12 maanden. Zie
  *Gepland tegenover werkelijk* verderop.
* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor. Er zijn geen nieuwe instellingen. Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.17.1: grafieken alleen met de sets die je gebruikt

De grafieken *Laadtoestand (24 uur)* en *Vermogen (laatste 3 uur)* op Overzicht tonen nu alleen de sets waarvan
een IP-adres is ingevuld. Ongebruikte sets staan niet meer als *Niet beschikbaar* in de legenda. Dat werkt voor
elke combinatie van sets (ook set 1 en 3 zonder set 2). Plak `dashboards/dashboard.yaml` opnieuw in de
Raw-configuratie-editor. Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.17.0: prijsbron Bloktarief

Heb je een contract met vaste prijzen in tijdsblokken, zoals Eneco *VoordeelMomenten* (dal 10–17 en 22–05 uur)?
Kies dan op **Instellingen → Aansluiting** bij *Prijsbron* **Bloktarief** en vul de blokken in:

```
05:00=0,35; 10:00=0,27; 17:00=0,35; 22:00=0,27
```

Per blok staat de begintijd en de prijs die je per kWh betaalt, inclusief belastingen. Een blok loopt tot het
volgende begint. Daarna rekent de planner er gewoon mee, en hij kent de prijzen van morgen meteen. Alles staat in
[Bloktarief (vaste prijzen in tijdsblokken)](#bloktarief-vaste-prijzen-in-tijdsblokken).
Na de update staat de prijsbron op *Prijssensor*: er verandert niets. Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.16.1: profielen Snel laden en Snel ontladen

In *Profiel activeren* staan twee nieuwe profielen:

* **Snel laden** zet de modus op *Laden (vol vermogen)*: alle sets laden van het net, elk op zijn eigen
  *Max laden*.
* **Snel ontladen** zet de modus op *Ontladen (vol vermogen)*: alle sets ontladen naar het net, elk op zijn eigen
  *Max ontladen*.

*Systeem max laden / ontladen* (als die niet 0 is), *Laden / Ontladen toegestaan* en de SOC-grenzen per set
blijven gelden. Is de accu vol of leeg, dan gaat de modus terug naar de modus van daarvoor. Andere instellingen
veranderen niet. Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.16.0: seizoensinstelling

Kies een profiel, bijvoorbeeld *Dynamisch NOM*, en combineer het met een **seizoen**. Het profiel bepaalt de
strategie. Het seizoen bepaalt alleen hoe gevoelig de planner is: *Minimale winst per kWh* en *Slijtagekosten per kWh*.

* **In de winter** zijn de prijsverschillen klein en vult de zon de accu niet. Met lage drempels (standaard
  0,02 en 0,01 €/kWh) laadt de planner dan vaker goedkoop van het net en is de accu vaker vol voor de dure uren.
* **In de zomer** vult de zon de accu. Hogere drempels (standaard 0,05 en 0,03 €/kWh) voorkomen dat de accu voor
  een paar cent extra cycli maakt.
* **Automatisch**: elke dag om 20:00 kiest de EMS zelf winter of zomer. Dat gaat op het verwachte zonoverschot
  morgen, in procent van je eigen accu. Daardoor werkt het bij een kleine en een grote installatie.
* Op **Overzicht** staat de keuzelijst *Seizoen* tussen *Modus* en *Profiel activeren*. Onder *Actief profiel*
  staat nu *Profiel + seizoen*, bijvoorbeeld *Dynamisch NOM · Winter (automatisch)*.
* Op **Instellingen** staat een nieuwe kaart *Seizoen (minimale winst en slijtage)*, direct onder *Prijssturing*.
* Na de update staat het seizoen op **Uit**: er verandert niets tot je het aanzet.

Alles over de werking, de instellingen en de keuze van de grenzen staat in het hoofdstuk
[Seizoen (winter en zomer)](#seizoen-winter-en-zomer).

* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor. Zie [CHANGELOG.md](CHANGELOG.md).
* Heb je de seizoensfunctie eerder als losse helpers aangemaakt? Lees dan eerst
  [Overstappen van losse helpers](#overstappen-van-losse-helpers).

## Versie 1.15.5: slimmer verdienmodel in de prijsplanner

Drie verbeteringen in de planner van de modus *Prijsgestuurd*. Ze leveren vooral iets op op zonnige dagen waarop
de accu vol raakt en de rest van de zon het net op gaat, en dat wordt belangrijker nu salderen op 1 januari 2027
stopt.

* **Zon slim verdelen** (nieuwe schakelaar, staat na de update aan). Verwacht de planner dat de accu vol raakt en
  de rest van de zon het net op gaat, dan kijkt hij naar de terugleverprijs. Is die nu duidelijk hoger dan op het
  moment dat de accu vol zou raken, dan levert hij de zon nu terug en vult hij de accu later met het overschot.
  Er gaat evenveel zon de accu in en het net op, maar het teruggeleverde deel brengt meer op.
  Voorbeeld: om 9:00 levert terugleveren 0,35 €/kWh op, rond het middaguur 0,05 €/kWh. 5 kWh eerder terugleveren
  levert dan ≈ € 1,50 extra op, en de accu is 's middags toch vol. De prijsactie heet dan
  *Zon terugleveren, accu later vullen*. De sets laden in dat kwartier hooguit het geplande vermogen en blijven
  gewoon ontladen als het huis stroom vraagt.
* **Verkopen telt de zon mee** (bij *Verkopen plannen*, profielen *Dynamisch Handelen*). Verkopen uit de accu
  in een ochtendpiek kan nu ook als de accu 's avonds anders leeg zou raken, mits de zon hem ertussen weer vult met
  overschot dat anders het net op zou gaan. Dat bijvullen kost wat die zon op het net zou hebben opgebracht, en dat
  telt de planner als kosten. Andersom verkoopt hij niet meer terwijl de zon nog volop schijnt: elke verkochte kWh
  wordt dan meteen met zon bijgevuld die anders tegen dezelfde prijs het net op was gegaan.
* **Eigen minimale winst voor vasthouden** (nieuw veld *Minimale winst bij vasthouden en zon verdelen*, standaard
  0,02 €/kWh). Vasthouden (*Slim ontladen*) en zon verdelen kosten geen extra laadcyclus en geen extra
  rendementsverlies: dezelfde kWh wordt alleen op een duurder moment gebruikt. Daardoor hoeft het verschil niet
  meer de volle *Minimale winst per kWh* (standaard 0,05 €/kWh) te zijn. Prijsverschillen van 2 tot 5 cent, die in
  de winter heel gewoon zijn, worden nu ook benut. Laden van het net en verkopen houden *Minimale winst per kWh*.
* **Veiligheidsmarge:** van het verwachte overschot telt de planner hooguit **75 %** mee (voor zon verdelen en
  verkopen samen). Valt de zon tegen, dan raakt de accu toch nog vol.
* Op het dashboard: in de planner *☀️ terugleveren* per uur, in de kop de verwachte extra opbrengst, en op het
  tabblad Statistieken de regel *Zon terugleveren, accu later vullen*. Op Instellingen → Prijssturing staan de
  nieuwe schakelaar en het nieuwe veld.
* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor. Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.15.4: lichter voor Home Assistant en de database, HomeWizard Instant

* **Snellere kwartierplanner.** Met *Slim laden* of *Slim ontladen* aan was de planner het zwaarste deel van het
  package: elke 5 minuten honderden milliseconden rekenen, op een Raspberry Pi of HA Green langer. Zolang een template
  rekent, wacht de rest van Home Assistant. De zoekloop stopt nu zodra geen eerder kwartier nog goedkoper of de moeite
  waard kan zijn, of zodra de accu ertussen vol zou raken. Gemiddeld ongeveer 15 % en in het zwaarste geval ongeveer
  25 % sneller, met **precies dezelfde planning** (getest in 144 scenario's tegen 1.15.3).
* **Kwartiergemiddelde huisverbruik** gebruikt nu de rustige 5-s-sensor `sensor.zendure_ems_grafiek_huisverbruik`
  in plaats van de sensor die met een snelle P1 elke seconde verandert. Dat is tot 5× minder schrijven naar de
  database, en omdat die bron wel bewaard wordt, is het gemiddelde na een herstart meteen gevuld.
* **kWh-tellers afgerond op 10 Wh** (was 1 Wh). Ze werkten bijna elke 5 s een nieuwe waarde bij; nu veel minder vaak.
  De totalen en de statistieken blijven exact, alleen de weergegeven stap is 0,01 kWh.
* **Recorder-exclude uitgebreid (aanbevolen):** het event `zendure_ems_regelaar` en `automation.zendure_ems_regeling`
  veranderen bij elke regelstap (tot elke seconde). Zie stap 3 van *Installatie*.
* **HomeWizard Instant als aanbevolen netmeter.** Deze HACS-integratie (domein `homewizard_instant`) geeft elke
  seconde een nieuwe meterwaarde van de P1; de officiële integratie elke 5 s. Vul de vermogensensor ervan in als *Netmeter-sensor*; *Netmeter-bron* toont dan
  *HomeWizard Instant (elke seconde)*. Het veld *P1 IP-adres* is alleen nog nodig zonder HomeWizard Instant (zie
  *Vereisten*). Op het tabblad Instellingen heten de twee velden nu *Netmeter-sensor (bv. HomeWizard Instant, elke
  seconde)* en *HomeWizard P1 IP-adres (alleen zonder HomeWizard Instant)*.
* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor (twee veldnamen op Instellingen zijn gewijzigd). Zie [CHANGELOG.md](CHANGELOG.md).

## Versie 1.15.3: Nordpool-prijssensor zonder `end`

* De planner werkt nu ook met een prijssensor waarvan de blokken in `raw_today` / `raw_tomorrow` alleen `start` en
  `value` hebben, zonder `end`. Dat is bijvoorbeeld zo bij een template-sensor die de officiële *Nord Pool*-integratie
  omzet naar de vorm van de HACS-integratie, en `end` weglaat om onder de recorderlimiet van 16 KB te blijven.
  Eerder bleef de prijsactie dan op *Geen prijsdata* staan.
* Een blok zonder `end` loopt tot het volgende begint (binnen 2 uur); het laatste blok duurt even lang als het blok
  ervoor. Met `end` verandert er niets. Zie [CHANGELOG.md](CHANGELOG.md).
* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor (alleen het versienummer is gewijzigd).

## Versie 1.15.2: max vermogen per set boven 2400 W

* *Max laadvermogen* en *Max ontlaadvermogen* per set (tabblad Instellingen, kaart *Grenzen set N*) kunnen nu tot
  **8000 W** (was 2400 W), voor nieuwere sets zoals de SolarFlow 4000 Mix. De standaardwaarde blijft 2400 W en je
  eigen waarde blijft bij elke update bewaard.
* Het werkelijke vermogen is per set het laagste van dit veld en wat de set zelf rapporteert (`chargeMaxLimit` /
  `inverseMaxPower`). Een 2400 W-set blijft dus op 2400 W, ook als je een hogere waarde invult.
* Wil je meer dan 2400 W per set, verhoog dan ook *Max stap per cyclus* (en eventueel *Systeem max laden/ontladen*).

## Versie 1.15.1: kalibratie dichter bij het gekozen aantal weken

* Bij *Wekelijks*, *Elke 2 weken* en *Elke 3 weken* is een set op de gekozen dag nu pas aan de beurt na minstens
  **6, 13 of 20 dagen** zonder 100 % (was 3, 10 of 17). Bij *Elke 3 weken* laadt een set dus niet meer al na
  17 dagen opnieuw vol. Eén dag marge blijft, omdat een kalibratie vaak pas in de nacht na de gekozen dag klaar is.
* De gekozen dag valt nooit meer op of na *Uiterlijk na*: zou de volgende gekozen dag te laat zijn, dan doet de set al
  mee op de laatste gekozen dag daarvoor. Zie [Kalibratie: een set haalt tussendoor al 100 %](#kalibratie-een-set-haalt-tussendoor-al-100-).
* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor (alleen het versienummer is gewijzigd).

## Versie 1.15.0: per set de volgende kalibratie

* **Per set zie je nu wanneer hij weer naar 100 % gaat.** De kaart *Kalibratie (volladen naar 100 %)* (tabblad
  Instellingen) heeft per set een regel *Set N volgende 100 %*, bijvoorbeeld *zo 06-12 (over 21 dagen)*, *Bezig*
  of *Uit*. De gezamenlijke *Status* blijft de eerstvolgende datum van alle sets samen tonen.
* Elke set telt vanaf zijn eigen *laatst 100 %*. Haalt een set tussendoor al 100 %, dan schuift alleen zijn eigen
  ronde op. Zie [Kalibratie: een set haalt tussendoor al 100 %](#kalibratie-een-set-haalt-tussendoor-al-100-).
* Nieuwe sensoren `sensor.zendure_setN_volgende_kalibratie`; aan de regeling en de planner is niets gewijzigd.
  Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor.

## Versie 1.14.5: geen laad- of verkoopactie meer voor een paar Wh

* **Een set schakelde soms om voor bijna niets.** Bij *Verkoop plannen* verdeelt de planner de inkoop over de
  goedkoopste kwartieren. Een restje van bijvoorbeeld 0,01 kWh kon zo in een eigen kwartier terechtkomen. De
  prijsactie werd dan *Laden van het net* (of *Verkopen aan het net*) met het minimum van 200 W, en de set
  schakelde twee keer om (ontladen → laden → ontladen) voor een paar Wh.
* **Een nieuwe laad- of verkoopactie start nu pas vanaf 0,05 kWh in het kwartier**, het minimum van 200 W
  gedurende een heel kwartier. Een actie die al loopt gaat gewoon door zolang er nog iets gepland staat, zodat hij
  niet aan het eind van een kwartier wordt afgebroken en een kwartier later weer gestart.
* Bij het plannen van inkoop voor verkoop komt een restje onder 0,05 kWh niet meer in een kwartier dat nog niet laadt.
  *Laadmomenten* en *Verkoopmomenten* tonen alleen nog kwartieren met minstens 0,05 kWh.
* Alleen de prijsplanner is gewijzigd; nieuwe helpers en instellingen zijn er niet. Vervang
  `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor (alleen het versienummer is gewijzigd).

## Versie 1.14.4: standby na inactiviteit werkt nu altijd

* **Een set in rust ging vaak niet in standby.** Een set telde alleen als inactief als de laadlimiet én de
  ontlaadlimiet allebei 0 waren. Bij het stoppen zet de regeling alleen de limiet van de huidige richting op 0, en de
  set blijft de oude limiet van de andere richting melden. Een set die eerder had geladen en daarna ontladen (of
  andersom) bleef daardoor aan staan in plaats van na *Standby na inactiviteit* in standby te gaan.
* Nu telt alleen de limiet van de richting waarin de set staat (laden of ontladen). De limiet van de andere richting
  doet in die stand niets en telt niet meer mee.
* Alleen de sensoren *Zendure setN inactief* zijn gewijzigd; nieuwe helpers en instellingen zijn er niet. Vervang
  `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor (alleen het versienummer is gewijzigd).

## Versie 1.14.3: na verkopen of netladen meteen terug naar nul op de meter

* **Na een kwartier verkopen of laden van het net gaan de sets meteen terug naar het huisverbruik.** Voorheen zag
  *Korte dips negeren* het einde van het verkopen aan als een korte dip, waardoor de sets nog tot de dip-tijd (bijvoorbeeld
  30 s) op vol vermogen bleven terugleveren.
* *Korte dips negeren* geldt nu alleen nog tijdens nul op de meter, en het vermogen springt na verkopen of netladen in
  één stap naar wat het huis nodig heeft in plaats van in stappen van *Max stap per cyclus*.
* Alleen de regeling is gewijzigd. Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak
  `dashboards/dashboard.yaml` opnieuw in de Raw-configuratie-editor (alleen het versienummer is gewijzigd).

## Versie 1.14.2: Modus en profiel inklapbaar, nieuwe kaart Energie vandaag

* Op het tabblad Overzicht staan **Modus, Profiel activeren en Actief profiel** nu in een eigen inklapbare groep
  **Modus en profiel**, net als *Laadtoestand per set*. Tik op de kop om in of uit te klappen; na de update staat de
  groep open. Status en de regel met Net, Accu's, SOC, Opgeslagen en Prijs blijven altijd zichtbaar.
* Nieuwe kaart **Energie vandaag** (ook inklapbaar): geladen, ontladen, zon, huis, net ingevoerd, net teruggeleverd en
  verwacht verbruik in kWh, met een gekleurde balk per regel. De nieuwe dagtellers beginnen bij de update op 0.
* De kaart **Energiestroom** heeft geen kop meer: de tekening begint bovenaan de kaart.
* De **Planner (per kwartier)** staat nu bovenaan de rechterkolom van Overzicht.
* EMS op een **wandtablet** of als extra tab in een bestaand dashboard (bijvoorbeeld Kiosk): zie hoofdstuk 5.4 van de
  handleiding. Kort: voeg in dat dashboard een tab toe met één Webpagina-kaart (type `panel`, kaart `iframe`) met als
  adres `/dashboard-ems/overzicht?hide_sidebar`.
* Vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor.

## Versie 1.14.1: zonnecorrectie leert ook bij een late Forecast.Solar-update

* **De lerende zonnecorrectie sloeg de meeste dagen over.** De verwachting voor de dag werd alleen om 00:10
  onthouden, maar Forecast.Solar ververst na middernacht op een wisselend moment (bijvoorbeeld 00:07, 00:19 of
  00:54). Was dat na 00:10, dan werd 0 kWh onthouden en werd de dag om 23:50 overgeslagen.
* Nu wordt **tussen 00:00 en 05:00 elke 10 minuten** de nieuwste verwachting onthouden. Een tijdelijke 0 of
  `unavailable` overschrijft een al onthouden waarde niet. De vergelijking om 23:50 is ongewijzigd.
* Je geleerde correctie en historie blijven bewaard. Plak `dashboards/dashboard.yaml` opnieuw in de
  Raw-configuratie-editor (alleen het versienummer is gewijzigd).

## Versie 1.14.0: ondersteuning voor 4 sets

* **Eén package en één dashboard voor 1, 2, 3 of 4 sets.** Set 4 heeft alles wat sets 1 tot 3 hebben: IP-adres,
  min/max SOC, max laad- en ontlaadvermogen, capaciteit, reserve, laden/ontladen toegestaan, eigen modus,
  kalibratie (laatst 100 %), relaisschakelingen, rendement en een eigen kaart op Overzicht, Instellingen en
  Statistieken. Bijschakelen (*Volgende set inzetten vanaf*), minimale aan- en uittijd, planner, kalibratie,
  standby en de modi Alleen slim opladen/ontladen werken met 4 sets precies zoals met 3.
* Vul alleen de IP-adressen in van de sets die je hebt: een set zonder IP-adres wordt niet aangestuurd en niet getoond.
* **De opdrachten aan de sets gaan tegelijk de deur uit** in plaats van na elkaar. Een extra set, of een set die even
  niet antwoordt (tot 4 s time-out), houdt de andere sets daardoor niet meer op: de regelcyclus is met 4 sets niet
  trager dan voorheen met 3, en met een haperende set juist sneller.
* *Max stap per cyclus* kan nu tot 9600 W (4 × 2400 W; was 7200 W). De standaardwaarde blijft 1500 W en wordt bij
  de update niet aangepast: **met 4 sets ben je zelf verantwoordelijk voor de juiste instelling** van *Max stap per
  cyclus* en, als je die gebruikt, *Systeem max laden* en *Systeem max ontladen* (maximaal 4 × 2400 = 9600 W, of
  lager als je aansluiting of groepen dat vragen).
* Energiestroom-tekening: vier vaste plekken voor de accutorens, met de omvormer boven de vierde toren.
* Na de update krijgen de velden van set 4 eenmalig hun standaardwaarde (max SOC 100 %, 2400 W, laden en ontladen
  toegestaan). Je bestaande instellingen van sets 1 tot 3 blijven ongewijzigd.
* Plak `dashboards/dashboard.yaml` opnieuw in de Raw-configuratie-editor.

## Eerdere versies

Alle wijzigingen per versie staan in [CHANGELOG.md](CHANGELOG.md).

## Inhoud

| Bestand | Wat |
|---|---|
| `packages/zendure_ems.yaml` | Package voor 1, 2, 3 of 4 sets |
| `dashboards/dashboard.yaml` | Dashboard voor 1, 2, 3 of 4 sets |
| `Zendure-EMS-handleiding.docx` | Volledige handleiding met alle velden |
| `CHANGELOG.md` | Alle wijzigingen per versie |
| `docs/` | Afbeeldingen bij deze LEESMIJ |

Vul alleen de IP-adressen in van de sets die je hebt: een set zonder IP-adres wordt niet aangestuurd en niet getoond.

## Vereisten

* Home Assistant **2025.1 of nieuwer**.
* Elke SolarFlow is lokaal bereikbaar. Test dit in je browser: `http://IP-VAN-DE-SET/properties/report`
  moet JSON tonen met `"properties"`. Geef elke set een **vast IP-adres** (DHCP-reservering in je router).
* In de Zendure-app staat **HEMS UIT** op elke set. Met HEMS aan overschrijft de set de opdrachten na ~10 s.
* **Eén** sensor voor het netvermogen in W of kW, met positief = afname en negatief = teruglevering.
  Voorbeelden: HomeWizard P1 `sensor.p1_meter_power`, of een eigen template (zie hieronder).
  **Heb je een HomeWizard P1, gebruik dan bij voorkeur de HACS-integratie
  [HomeWizard Instant](https://github.com/taurgis/homeassistant-homewizard-instant)** (domein `homewizard_instant`).
  Die geeft elke seconde een nieuwe meterwaarde in plaats van elke 5 s, zonder dat het package de P1 zelf hoeft uit te
  lezen. Vul de vermogensensor ervan in als *Netmeter-sensor* (de sensor met het totale
  vermogen, niet die per fase) en laat het *P1 IP-adres* leeg. *Netmeter-bron* toont dan
  *HomeWizard Instant (elke seconde)*. De officiële HomeWizard-integratie kan ernaast blijven draaien.
  Zonder HomeWizard Instant kun je het **IP-adres van de P1** invullen: het package leest hem dan zelf uit
  (zie versie 1.12.2 in [CHANGELOG.md](CHANGELOG.md)).
  Kan het nettovermogen alleen omgekeerd worden gemeten? Zet dan *Netmeter omkeren* aan.
* Voor de prijssturing: een prijssensor met de prijzen als attributen:
  * **Nordpool (HACS)**: attributen `raw_today` / `raw_tomorrow`, elk blok met `start`, `value` en meestal `end`
  * **Zonneplan ONE**: attribuut `forecast` (bv. `sensor.zonneplan_current_electricity_tariff`)
  * **ENTSO-e**: attributen `prices_today` / `prices_tomorrow`

  De officiële *Nord Pool*-integratie van HA heeft die attributen niet en werkt daarom niet direct. Wel werkt een
  **template-sensor** die met de actie `nordpool.get_prices_for_date` dezelfde attributen `raw_today` /
  `raw_tomorrow` opbouwt (elk blok met `start` als ISO-tijd en `value` in €/kWh). `end` mag daarbij ontbreken
  (vanaf 1.15.3): een blok loopt dan tot het volgende begint. Laat je `end` weg, dan blijven de attributen met
  kwartierprijzen onder de recorderlimiet van 16 KB.
  Kwartierprijzen en uurprijzen werken allebei; uurprijzen worden in vier kwartieren gesplitst.

  Heb je geen dynamisch contract maar **vaste prijzen in tijdsblokken**? Dan heb je geen prijssensor nodig: zie
  [Bloktarief](#bloktarief-vaste-prijzen-in-tijdsblokken).
* Optioneel voor de planner: een **zonneverwachting** via de integratie **Forecast.Solar**
  (*Instellingen → Apparaten & diensten → Integratie toevoegen → Forecast.Solar*). De planner gebruikt:
  * `sensor.energy_production_today_remaining`: verwachte opbrengst voor de rest van vandaag (kWh)
  * `sensor.energy_production_tomorrow`: verwachte opbrengst morgen (kWh)

  Bestaan die sensoren bij de eerste start, dan worden ze automatisch ingevuld. Die sensoren geven
  dagtotalen; die gebruikt de zonnecorrectie. Voor de verdeling over de kwartieren haalt de EMS vanaf 1.19.0
  zelf de uurverwachting op met de actie `forecast_solar.get_forecast` (*Zonneverwachting per uur*, zie
  [De planner](#de-planner-per-kwartier), punt 2). Staat die uit of lukt dat niet, dan verdeelt de planner het
  dagtotaal over de kwartieren tussen zonsopkomst en zonsondergang (uit `sun.sun`), met een zonneboog die rond
  het middaguur het hoogst is.

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
       event_types:
         - zendure_ems_regelaar
       entity_globs:
         - sensor.zendure_set*_rapport
         - sensor.zendure_ems_weergave_*
       entities:
         - automation.zendure_ems_regeling
         - sensor.zendure_ems_regelaar
         - sensor.zendure_ems_planning
         - sensor.zendure_ems_netmeting
         - sensor.zendure_ems_p1_vermogen
         - sensor.zendure_ems_netvermogen
         - sensor.zendure_ems_huisverbruik
   ```
   (Het event `zendure_ems_regelaar` en `automation.zendure_ems_regeling` veranderen bij elke regelstap, tot elke
   seconde; sinds 1.15.4 in deze lijst. Het dashboard heeft van de automatisering alleen de aan/uit-stand nodig.
   Gebruik je HomeWizard Instant én de officiële HomeWizard-integratie, dan kun je ook de vermogensensoren van
   HomeWizard Instant (totaal en per fase) hier toevoegen: die veranderen elke seconde, en de officiële integratie
   bewaart hetzelfde vermogen al elke 5 s. Het package gebruikt de waarde live en heeft geen geschiedenis nodig.
   `sensor.zendure_ems_netmeting` is een kopie van je P1-meter die elke seconde verandert; de P1-meter zelf wordt al
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
   * de prijssensor (optioneel), of bij *Prijsbron* **Bloktarief** met je blokken
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
| **Laden / Ontladen (vol vermogen)** | Alle sets laden van of ontladen naar het net op hun eigen *Max laden* / *Max ontladen*. Met één keuze: profiel *Snel laden* of *Snel ontladen*. |

Per set kun je ook een **eigen modus** kiezen (*Alleen slim opladen* of *Alleen slim ontladen*, op de setkaart);
*Volgt EMS-modus* = de set doet wat de modus hierboven zegt. Zie versie 1.13.0 in [CHANGELOG.md](CHANGELOG.md).

### Bloktarief (vaste prijzen in tijdsblokken)

Sommige leveranciers hebben een vast contract met een goedkoop en een duur tarief in vaste blokken. Een voorbeeld
is Eneco *VoordeelMomenten*: dal van 10:00 tot 17:00 en van 22:00 tot 05:00, de rest normaal. Kies daarvoor op
**Instellingen → Aansluiting** bij *Prijsbron* **Bloktarief**.

| Veld | Voorbeeld | Betekenis |
|---|---|---|
| **Bloktarief** | `05:00=0,35; 10:00=0,27; 17:00=0,35; 22:00=0,27` | Per blok begintijd=prijs, gescheiden door `;`. De prijs is wat je per kWh betaalt, inclusief belastingen. Komma of punt; 2 of meer telt als cent (`27` = 0,27). |
| **Bloktarief weekend** | `00:00=0,27` | Eigen blokken voor zaterdag en zondag, hier de hele dag dal. Leeg = zoals werkdagen. |
| **Bloktarief nu** | *Nu 0.27 €/kWh tot 17:00, daarna 0.35 €/kWh* | Controle: het blok van nu en het volgende. Bij een tikfout: *Geen geldige blokken ingevuld*. |

* Een blok loopt tot de volgende begintijd. Het laatste blok van de dag (bij Eneco 22:00) loopt door tot het eerste
  blok van de volgende dag (05:00). De volgorde waarin je ze typt maakt niet uit.
* De planner werkt er precies zo mee als met dynamische prijzen. Hij kent de prijzen van morgen meteen en kijkt
  zoals altijd 36 uur vooruit.
* **Wat de accu doet**: hij ontlaadt voor het huis, zoals bij nul op de meter. Met *Slim ontladen* aan (bijvoorbeeld
  profiel *Dynamisch NOM (Duur)*) houdt hij in het dal de lading vast als die anders niet tot het eind van de
  volgende piek reikt. Je gebruikt dan in het dal stroom van het net en de accu in de piek (*minimale winst bij
  vasthouden*). Is er genoeg lading, dan hoeft dat niet. Laden van het net in het dal gebeurt alleen als het loont: *dalprijs ÷ rendement + slijtage + minimale winst* moet onder de piekprijs
  liggen. Bij 0,27 en 0,35 €/kWh met 85 % rendement is dat 0,318 + slijtage + minimale winst. Met de winterwaarden
  van het [seizoen](#seizoen-winter-en-zomer) (0,02 + 0,01) loont het net, met de zomerwaarden (0,05 + 0,03) niet.
  Op een zonnige dag vult de zon de accu toch al.
* **Teruglevering**: zolang je saldeert, is de terugleverprijs gelijk aan de blokprijs. Daarna (*Salderen* op
  *Uit* of *Automatisch* vanaf 2027) is hij bij Bloktarief de **vaste vergoeding** op de kaart *Teruglevering*,
  bijvoorbeeld 0,06 €/kWh, of negatief bij terugleverkosten.
* Wisselen van contract? Zet *Prijsbron* terug op *Prijssensor*; de ingevulde blokken blijven bewaard.

#### Feestdagen als weekend (vanaf 1.19.0)

Zonder deze instelling is een feestdag op een werkdag (bijvoorbeeld eerste kerstdag op een vrijdag) voor de planner
een gewone werkdag: hij rekent met de werkdagblokken. Rekent je leverancier op feestdagen het weekendtarief (vraag dat
na, dat verschilt per contract), zet dan deze instelling aan. De EMS gebruikt daarvoor de integratie **Workday** van
Home Assistant, die weet welke dagen in Nederland feestdagen zijn.

**Instellen, stap voor stap**

1. **Weekendregel invullen.** Vul op **Instellingen → Aansluiting** het veld *Bloktarief weekend* in, bijvoorbeeld
   `00:00=0,27`. Een feestdag krijgt precies deze regel. Is het veld leeg, dan gelden in het weekend en op feestdagen
   de werkdagblokken en heeft deze instelling geen effect.
2. **Workday-integratie toevoegen.** Ga naar *Instellingen → Apparaten & diensten → Integratie toevoegen*, zoek
   **Workday** en kies:
   * *Land*: **Nederland** (NL);
   * *Werkdagen*: maandag tot en met vrijdag;
   * *Uitsluiten*: zaterdag, zondag en **Feestdagen** (standaard al zo).

   Home Assistant maakt dan een binary_sensor, meestal `binary_sensor.workday_sensor`. Die staat *Aan* op een werkdag
   en *Uit* in het weekend en op een feestdag. Wil je een dag extra vrij of juist niet, dan kun je dat in de opties van
   Workday aanpassen (*Feestdagen toevoegen* / *verwijderen*).
3. **Koppelen aan de EMS.** Zet op **Instellingen → Aansluiting** (zichtbaar zodra *Prijsbron* op *Bloktarief* staat)
   **Feestdagen als weekend (Workday-integratie)** aan. Er verschijnt het veld **Werkdag-sensor**: vul daar de
   binary_sensor uit stap 2 in, bijvoorbeeld `binary_sensor.workday_sensor`.
4. **Controleren.** De regel *Werkdag of vrij* (`sensor.zendure_ems_werkdagen`) toont *Vandaag werkdag* of
   *Vandaag vrij* (*Uit* zolang de schakelaar uit staat). In het attribuut `vrij` staan gisteren, vandaag en morgen, bijvoorbeeld
   `{'2026-12-24': false, '2026-12-25': true}`. Staat er *Onbekend*, controleer dan de naam van de binary_sensor.

**Hoe het werkt**

* Elk uur (en bij de start of na een wijziging) vraagt `sensor.zendure_ems_werkdagen` met de actie
  `workday.check_date` aan Workday of gisteren, vandaag en morgen werkdagen zijn. Gisteren is nodig omdat het laatste
  blok van een dag doorloopt tot het eerste blok van de volgende dag.
* Een dag die Workday *vrij* noemt, gebruikt de regel *Bloktarief weekend*, net als een zaterdag of zondag.
* Is de informatie ouder dan 26 uur (bijvoorbeeld omdat Workday is verwijderd), dan negeert de planner haar en gelden
  weer de gewone regels: werkdagblokken op maandag tot en met vrijdag.
* Uitzetten kan altijd: met de schakelaar uit rekent de planner weer zoals vóór 1.19.0.
* Dit geldt alleen voor de prijsbron *Bloktarief*. Bij een dynamische prijssensor staat de feestdag al in de prijzen.

### Prijsacties (modus Prijsgestuurd)

Het package kiest elke minuut één actie, in deze volgorde:

1. **Verkopen aan het net**: als de prijs ≥ *Verkopen aan het net boven* (1,00 = uit). Alle sets op vol vermogen ontladen.
2. **Laden van het net**:
   * bij een negatieve prijs (schakelaar *Laden bij negatieve prijs*), of
   * als de prijs ≤ *Laden van het net onder* (‑0,50 = uit), of
   * in een kwartier dat de **planner** heeft gekozen (schakelaar *Slim laden*, zie hieronder), ook om terug
     te kopen na een verkoop (vanaf 1.18.0, bij *Verkopen plannen*).
3. **Accu vasthouden** (niet ontladen, wel zonne-overschot laden):
   * als de prijs < *Alleen ontladen boven* (‑0,50 = altijd ontladen), of
   * in een kwartier waarin de planner de energie bewaart voor een duurder kwartier (*Slim laden* of *Slim ontladen*).
4. **Zon terugleveren, accu later vullen** (vanaf 1.15.5, schakelaar *Zon slim verdelen*): in een kwartier waarin
   de planner de zon liever nu teruglevert en de accu later met overschot vult. De sets laden hooguit het geplande
   vermogen (onder het *Minimaal vermogen per set*: niet) en ontladen gewoon voor het huis.
5. Anders: **nul op de meter**.

### De planner (per kwartier)

Elke 5 minuten (en bij elke wijziging van een instelling) rekent de planner alle kwartieren door waarvoor
prijzen bekend zijn (tot maximaal 36 uur vooruit):

1. **Verbruik per kwartier**: uit het **geleerde verbruiksprofiel**, apart voor werkdagen en weekend (elk
   96 kwartierwaarden). Het profiel leert elk kwartier van het gemeten huisverbruik. Een nieuw kwartier
   leert snel, daarna weegt elke dag voor 15 % mee. Een nog niet geleerd kwartier neemt de waarde uit het
   andere profiel, en anders *Verwacht verbruik*.
2. **Zon per kwartier**: uit de zonneverwachting, vermenigvuldigd met de geleerde zonnecorrectie (of, de
   eerste 3 dagen en zonder leren, *Zonneverwachting meetellen voor*, standaard 80 %). De correctie leert
   elke dag: tussen 00:00 en 05:00 wordt de verwachting voor de hele dag onthouden, om 23:50 vergeleken met
   de gemeten opbrengst. Hoe de verwachting over de kwartieren wordt verdeeld, hangt af van de bron
   (attribuut `zonbron` van `sensor.zendure_ems_prijsactie`, op het dashboard *Zonbron van de planner*):
   * **Forecast.Solar per uur** (vanaf 1.19.0, *Zonneverwachting per uur* aan, standaard na de update): de sensor
     `sensor.zendure_ems_zon_per_kwartier` haalt elke 15 minuten met de actie `forecast_solar.get_forecast` de
     uurverwachting op (per kwartier met een betaald Forecast.Solar-account) en verdeelt elk uur over zijn
     kwartieren. Je hoeft niets in te vullen: alle geladen Forecast.Solar-koppelingen worden vanzelf gevonden en
     opgeteld (hoogstens twee, bijvoorbeeld twee daken). Zijn de gegevens ouder dan 3 uur (Forecast.Solar niet
     geladen), dan valt de planner terug op de verdeling hieronder.
   * **Open-Meteo (watts)** (vanaf 1.19.0): staat bij *Zonneverwachting vandaag/morgen* een sensor van de
     HACS-integratie Open-Meteo Solar Forecast met het attribuut `watts`, dan gebruikt de planner die
     kwartierwaarden (alleen die van de dag van de sensor).
   * **Solcast (detail)**: een Solcast-sensor met `detailedForecast` (per half uur) of `detailedHourly`.
   * **Totaal per dag (sinusverdeling)**: alleen een dagtotaal (bijvoorbeeld de gewone Forecast.Solar-sensoren,
     of *Zonneverwachting per uur* uit): verdeeld over een zonneboog tussen zonsopkomst en zonsondergang.
3. **Simulatie**: de opgeslagen energie wordt kwartier voor kwartier doorgerekend. Zonne-overschot laadt
   de accu (tot de max SOC), verbruik trekt hem leeg (tot de min SOC). Rendementsverlies telt mee: met het
   gemeten rendement per set (capaciteitsgewogen, zie hieronder), of met het vaste *Rendement heen en terug*.
   **Laden bij een lage prijs** (vanaf 1.18.0): in een kwartier met een negatieve prijs (*Laden bij negatieve
   prijs* aan) of een prijs onder *Laden van het net onder* laden de sets in de simulatie op vol vermogen tot
   de accu vol is, en voedt het net het huis. Zo weet de planner dat de accu daar toch wordt gevuld: hij houdt
   hem ervoor niet vast, en verkopen ervoor kan daar worden teruggekocht.
4. **Tekort oplossen op de goedkoopste manier**: raakt de accu in een kwartier te kort, dan kiest de planner
   uit alle eerdere kwartieren de goedkoopste oplossing:
   * **vasthouden** (*Slim ontladen*): in een goedkoper kwartier ontlaadt de accu niet, het net voedt daar het
     huis en de energie blijft bewaard. Loont als *prijs dan + minimale winst bij vasthouden* ≤ prijs van het
     tekortkwartier (vanaf 1.15.5; daarvoor gold de gewone *minimale winst*).
   * **laden van het net** (*Slim laden*): loont als *prijs dan ÷ rendement + slijtagekosten + minimale winst*
     ≤ prijs van het tekortkwartier.

   **Minimale winst bijleren** (vanaf 1.19.0, *Prijssturing*, staat uit): met deze schakelaar aan telt de planner
   een geleerde correctie op bij beide minimale winsten (netladen/verkopen en vasthouden/zon verdelen). Eén keer
   per dag, net na middernacht, bekijkt de EMS de laatste 14 dagen van
   [Gepland tegenover werkelijk](#gepland-tegenover-werkelijk):
   * werkelijk minder dan 80 % van gepland: de correctie gaat 0,005 €/kWh omhoog;
   * werkelijk meer dan gepland: de correctie gaat 0,005 €/kWh omlaag;
   * daartussen: ongewijzigd.

   De correctie blijft tussen 0 en 0,05 €/kWh. Er is pas iets te leren met minstens 7 dagen en samen minstens
   € 0,50 gepland. Je eigen *Minimale winst*, het profiel en het seizoen worden niet overschreven: de correctie
   komt er alleen bovenop, en met de schakelaar uit is ze 0. Op het dashboard staan *Geleerde extra minimale winst*
   en *Laatste aanpassing* (attributen `drempel_correctie` en `drempel_reden`).

   **Rendement:** met *Gemeten rendement per set gebruiken* aan neemt de planner het capaciteitsgewogen gemiddelde
   van de retourrendementen die de sets via de Zendure-integratie melden (`sensor.zendure_ems_rendement`). De energie
   wordt in de planning over de sets verdeeld naar hun capaciteit, dus dat gemiddelde is het verlies van een
   gemiddelde kWh. Een set zonder geldige meting telt met het vaste *Rendement heen en terug*.

   De energie moet tussen bron- en tekortkwartier in de accu passen: vult de zon de accu toch al, dan wordt
   er niet van het net geladen. Bij gelijke kosten kiest hij het laatste kwartier. Goedkope kwartieren
   daartussen waarin de accu leeg zou zijn, worden ook vastgehouden.
5. **Zon slim verdelen** (vanaf 1.15.5): de simulatie houdt per kwartier bij hoeveel zon er niet meer in de accu
   past en het net op gaat (*overschot*). Bij een overschot in kwartier B kijkt de planner naar eerdere kwartieren A
   waarin de accu zon opslaat. Is *terugleverprijs A − terugleverprijs B* ≥ *minimale winst bij vasthouden*, dan levert
   hij in A terug en slaat hij in B op. De beste paren komen eerst. De accu mag tussen A en B niet leeg raken, en
   bij gelijke prijzen begint het opslaan bij het eerste kwartier met overschot. Ligt er tussen A en B een
   overschotkwartier met een nog lagere prijs, dan slaat hij juist daar op.
6. **Verkopen plannen** (*Verkopen plannen* aan): verkopen in de duurste kwartieren (terugleverprijs ≥
   *Verkopen aan het net boven*), alleen als het loont: *terugleverprijs × √rendement − slijtage − minimale winst*
   moet hoger zijn dan wat die kWh anders kost. Voor voorraad die later niet nodig is, is dat de goedkoopste latere
   prijs ÷ √rendement. Voor energie die eerst wordt ingekocht, is het de inkoopprijs ÷ √rendement. Voor voorraad die
   de zon later weer bijvult (vanaf 1.15.5) is het de terugleverprijs van het overschotkwartier ÷ √rendement.
   **Verkopen en terugkopen** (vanaf 1.18.0): voorraad die later nog nodig is, mag ook weg als hij in een later,
   goedkoper kwartier wordt teruggekocht vóór hij nodig is. Dan is het de terugkoopprijs ÷ √rendement. Tussen
   verkoop en terugkoop mag de accu niet leeg raken. Eerder inkopen en later terugkopen worden samen afgewogen,
   goedkoopste kwartier eerst, en in één kwartier wordt nooit tegelijk ingekocht en verkocht. De planner bekijkt
   de 32 duurste kwartieren om te verkopen.
7. **Veiligheidsmarge** (vanaf 1.15.5, lerend vanaf 1.18.0): voor zon verdelen en verkopen samen telt de planner
   maar een deel van het verwachte overschot mee. Wat overblijft is het overschot aan het eind van de zonnige uren,
   en dat vangt een tegenvallende zon op. Met *Zonnecorrectie leren* aan en minstens 5 bruikbare dagen in de
   historie (dagen met minstens 1 kWh verwacht) leert de planner die marge: per dag *gemeten ÷ (verwacht ×
   correctie)*, en de marge is het gemiddelde min één standaardafwijking, tussen 50 en 90 %. Anders is het 75 %.
   De actuele marge staat in de attributen `zonmarge` en `zonmarge_bron` van `sensor.zendure_ems_prijsactie`.
8. Het resultaat is een vast plan per kwartier (laden, vasthouden of accu laten leveren), dus geen
   heen-en-weer schakelen. Het laadvermogen wordt zo gekozen dat precies de geplande kWh geladen wordt
   (minstens 200 W).
9. **Minimum per kwartier** (vanaf 1.14.5): een nieuwe laad- of verkoopactie start pas als er in het kwartier
   minstens 0,05 kWh gepland staat (200 W gedurende een kwartier). Een kleiner restje laat de sets op nul op de
   meter, zodat ze niet twee keer omschakelen voor een paar Wh. Een actie die al loopt, gaat door zolang er nog
   iets gepland staat.

De tabel **Planner** op het dashboard laat per uur zien: prijs, verwachte zon, verwacht verbruik, verwachte SOC
aan het eind van het uur, en het plan (🔌 laden, 💶 verkopen, ⏸ vasthouden, ☀️ terugleveren, 🔋 accu levert,
🏠 net levert).

Voor een goed verbruiksprofiel moet het huisverbruik kloppen: *huisverbruik = netmeter − accu + zonneproductie*.
Heb je zonnepanelen die niet via de Zendure lopen? Vul dan bij *Zonneproductie-sensor* de omvormer-sensor in.
Zonder die sensor leert het profiel overdag het verbruik **na aftrek van de zon**. Zet dan
*Zonneverwachting meetellen voor* lager (bv. 30 %), of laat de zonneverwachting leeg.

Met *Max netafname bij netladen* bescherm je je hoofdzekering: tijdens netladen wordt het laadvermogen
verlaagd zodra huis + laden boven deze waarde komt (bijvoorbeeld 3 × 25 A ≈ 17.000 W, of lager voor 1-fase).

## Seizoen (winter en zomer)

Vanaf versie 1.16.0.

### Waarom een seizoen

Twee instellingen op *Prijssturing* bepalen hoe snel de planner iets doet:

* **Minimale winst per kWh**: zoveel moet laden van het net (of verkopen) per kWh minimaal opleveren.
* **Slijtagekosten per kWh**: zoveel kost een kWh door de accu aan slijtage.

De planner laadt in een goedkoop kwartier van het net voor een duurder kwartier als:

> prijs goedkoop ÷ rendement + slijtage + minimale winst ≤ prijs duur

Met 85 % rendement, 0,03 slijtage en 0,05 minimale winst moet het prijsverschil al snel 10 tot 13 cent zijn. In de
winter is dat zelden zo, en dan blijft de accu half leeg terwijl er wel wat te verdienen was. Met 0,01 slijtage en
0,02 minimale winst is ongeveer 6 cent genoeg. In de zomer is het omgekeerd: de zon vult de accu toch al, en met lage
drempels kan de accu voor een paar cent extra cycli maken. Met de seizoensinstelling hoef je dat niet twee keer per
jaar met de hand te veranderen.

### Seizoen en profiel

Het seizoen is een **laag bovenop elk profiel**:

| | Bepaalt | Voorbeelden |
|---|---|---|
| **Profiel** | De strategie | Modus, slim laden/ontladen, verkopen plannen, prijsdrempels |
| **Seizoen** | Hoe gevoelig de planner is | Minimale winst per kWh, slijtagekosten per kWh |

De ingebouwde profielen raken minimale winst en slijtage niet aan. Je kunt dus elk profiel met elk seizoen combineren:
*Dynamisch NOM · Winter*, *Dynamisch Handelen + NOM · Zomer*, enzovoort. Onder *Actief profiel* zie je de
combinatie op de regel **Profiel + seizoen**, bijvoorbeeld *Dynamisch NOM · Winter (automatisch)*.

### De keuzelijst Seizoen

Je vindt de keuzelijst op **Overzicht** (tussen *Modus* en *Profiel activeren*) en op **Instellingen** → *Seizoen*.

| Stand | Wat er gebeurt |
|---|---|
| **Uit** | Het seizoen doet niets. Minimale winst en slijtage blijven zoals je ze op *Prijssturing* zet. Dit is de standaard na een installatie of update. |
| **Automatisch** | Elke dag op de controletijd kiest de EMS winter of zomer met het verwachte zonoverschot morgen (zie hieronder). |
| **Winter** | Altijd de winterwaarden. |
| **Zomer** | Altijd de zomerwaarden. |

Kies je *Automatisch*, dan beslist de EMS meteen en daarna elke dag op de controletijd.

### De instellingen (Instellingen → Seizoen)

| Veld | Standaard | Betekenis |
|---|---|---|
| **Seizoen** | Uit | Zie hierboven. |
| **Actief seizoen** | Winter | Het seizoen waarvan de waarden nu gelden. De automatisering zet dit veld; je hoeft het niet zelf te veranderen. |
| **Profiel + seizoen** | – | Het actieve profiel met het seizoen, bijvoorbeeld *Dynamisch NOM · Winter (automatisch)*. |
| Winter: **Minimale winst per kWh** | 0,02 €/kWh | Wordt *Minimale winst per kWh* in de winter. |
| Winter: **Slijtagekosten per kWh** | 0,01 €/kWh | Wordt *Slijtagekosten per kWh* in de winter. |
| Zomer: **Minimale winst per kWh** | 0,05 €/kWh | Wordt *Minimale winst per kWh* in de zomer (gelijk aan de gewone standaardwaarde). |
| Zomer: **Slijtagekosten per kWh** | 0,03 €/kWh | Wordt *Slijtagekosten per kWh* in de zomer (gelijk aan de gewone standaardwaarde). |
| **Dagelijks controleren om** | 20:00 | Wanneer *Automatisch* beslist. Om 20:00 heeft Forecast.Solar de verwachting voor morgen al. |
| **Winter als zonoverschot onder** | 0 % | Onder deze waarde wordt het winter. |
| **Zomer als zonoverschot boven** | 50 % | Boven deze waarde wordt het zomer. |
| **Verwacht zonoverschot morgen** | – | De berekende waarde (zie hieronder). |
| **Automatisering seizoen** | aan | De aan/uit-schakelaar van de automatisering *Zendure EMS: seizoen*. |

Verander je een winter- of zomerwaarde terwijl dat seizoen actief is, dan geldt de nieuwe waarde meteen.

### Automatisch: het verwachte zonoverschot morgen

De sensor `sensor.zendure_ems_zonoverschot_morgen` rekent uit hoeveel de zon de accu morgen kan vullen, in procent
van de bruikbare accucapaciteit:

> zonoverschot = (zonneverwachting morgen × zonnecorrectie − verbruik overdag) ÷ bruikbare capaciteit × 100 %

* **Zonneverwachting morgen**: het veld *Zonneverwachting morgen* (Forecast.Solar of Solcast, kWh of Wh).
* **Zonnecorrectie**: dezelfde factor die de planner gebruikt. Dat is de geleerde zonnecorrectie (na minstens 3 dagen
  leren), anders *Zonneverwachting meetellen voor*.
* **Verbruik overdag**: het geleerde verbruiksprofiel (werkdag of weekend, afhankelijk van morgen), opgeteld van
  zonsopkomst tot zonsondergang (uit `sun.sun`). Is het profiel nog niet geleerd, dan telt *Verwacht verbruik*.
* **Bruikbare capaciteit**: per set die meedoet capaciteit × (max SOC − min SOC). Een set die uit staat of niet
  bereikbaar is, telt niet mee.

Wat de uitkomst betekent:

| Zonoverschot | Betekenis | Seizoen (standaard) |
|---|---|---|
| onder 0 % | De zon dekt overdag niet eens het verbruik. De accu moet van het net komen. | Winter |
| 0 – 50 % | De zon vult de accu deels. | Blijft wat het was |
| boven 50 % | Het overschot vult minstens de halve accu. | Zomer |
| 100 % of meer | De zon kan de hele accu vullen. | Zomer |

**Voorbeeld:** morgen 2,3 kWh zon (na correctie), 3,7 kWh verbruik tussen zonsopkomst en zonsondergang en 11,8 kWh
bruikbare accu geven (2,3 − 3,7) ÷ 11,8 = **−12 %**, dus winter. Een zonnige meidag met 13 kWh zon en 6,8 kWh verbruik
geeft (13 − 6,8) ÷ 11,8 = **53 %**, dus zomer.

**Waarom een percentage en geen kWh?** Of de zon de accu vult, hangt af van je panelen, je verbruik én de grootte
van je accu. 8 kWh zon is veel voor 2 kWp met een kleine accu, en weinig voor 10 kWp met een grote. In procent van je
eigen accu werken dezelfde grenzen overal.

**Waarom 0 en 50 %?** Met een jaar meetgegevens van een installatie met 11,8 kWh bruikbare accu gaven deze grenzen:
van april tot en met augustus vrijwel elke dag zomer, in maart en september een paar zomerdagen, en van oktober tot en
met februari steeds winter, met ongeveer 22 wissels per jaar. Strengere grenzen (bijvoorbeeld 30/80 %) gaven midden in
de zomer steeds winterdagen. Wissel je naar jouw smaak te vaak, maak het gat tussen de grenzen dan groter
(bijvoorbeeld −10 % en 60 %).

**Daartussen blijft het staan.** Ligt het zonoverschot tussen de twee grenzen, dan blijft het huidige seizoen staan.
Zo wisselt het niet bij elke wolk. Is er geen zonneverwachting (sensor *niet beschikbaar*), dan blijft het seizoen ook
staan.

### Wanneer de waarden gezet worden

De automatisering **Zendure EMS: seizoen** zet *Minimale winst per kWh* en *Slijtagekosten per kWh* op de waarden van
het actieve seizoen:

* als je een andere stand kiest in *Seizoen*;
* elke dag op de controletijd;
* als je een winter- of zomerwaarde verandert;
* nadat je een profiel hebt geactiveerd;
* bij het starten van Home Assistant.

Alleen bij een andere keuze en op de controletijd kan het seizoen zelf wisselen. Bij de andere drie worden alleen de
waarden van het actieve seizoen opnieuw gezet. De automatisering schrijft alleen als de waarde echt anders is. Een
wissel van seizoen zie je in het logboek, bijvoorbeeld *Seizoen Zomer (automatisch, zonoverschot morgen 63 %):
minimale winst 0.05 en slijtage 0.03 €/kWh*.

### Mijn profiel 1 en 2 met het seizoen

Een eigen profiel (*Opslaan als mijn profiel*) bewaart ook minimale winst en slijtage. Staat het seizoen aan, dan
zet de EMS direct na het activeren van een eigen profiel de seizoenswaarden terug. Met het seizoen aan bepaalt dus
het seizoen deze twee waarden, ook bij een eigen profiel.

Let op bij een eigen profiel dat dezelfde strategie heeft als een ingebouwd profiel, plus de minimale winst en
slijtage van het seizoen. Dan past het eigen profiel precies op je instellingen, en *Actief profiel* toont dan
*Mijn profiel 1* in plaats van bijvoorbeeld *Dynamisch NOM (Duur)*: de EMS vergelijkt eerst met de eigen profielen.
Met het seizoen heb je zo'n eigen profiel niet meer nodig. Maak een eigen profiel daarom echt anders dan de ingebouwde,
of laat het leeg.

### Zelf minimale winst of slijtage veranderen

Staat het seizoen aan, dan kun je *Minimale winst per kWh* en *Slijtagekosten per kWh* op *Prijssturing* nog steeds
veranderen. Bij de volgende controle (of na het activeren van een profiel) zet de EMS ze terug op de seizoenswaarde.
Wil je een andere vaste waarde, verander dan de winter- of zomerwaarde op de kaart *Seizoen*, of zet het seizoen op
*Uit*.

### Overstappen van losse helpers

Heb je de seizoensfunctie al eerder zelf (of met hulp) als helpers en automatisering in de UI aangemaakt, met
dezelfde namen als in deze versie? Verwijder die dan **vóór** je het nieuwe package installeert. Anders bestaan de
ID's twee keer en geeft Home Assistant een fout of maakt het een tweede helper met `_2` erachter.

1. Noteer je eigen waarden (winter/zomer, grenzen, tijd).
2. Verwijder onder *Instellingen → Apparaten & diensten → Helpers*: *Zendure EMS seizoen*, *seizoen actief*,
   *seizoen controletijd*, *seizoen winter als overschot onder*, *seizoen zomer als overschot boven*,
   *winter minimale winst*, *winter slijtage*, *zomer minimale winst*, *zomer slijtage*, *toon seizoen*,
   *profiel en seizoen* en *zonoverschot morgen*.
3. Verwijder onder *Instellingen → Automatiseringen* je eigen seizoensautomatisering.
4. Installeer het package, herstart Home Assistant en plak het dashboard opnieuw.
5. Zet je waarden terug en kies *Seizoen* → *Automatisch* (de update zet het seizoen op *Uit*).

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
* **Minimale looptijd en rusttijd:** de status toont dan *Minimale looptijd* of *Rusttijd na stoppen*; de
  resterende seconden staan sinds 1.18.1 in het attribuut `nog_seconden` van `sensor.zendure_ems_regelaar` en op
  het dashboard onder Status (*Nog*). Zo verandert de status niet elke seconde.
* **Laden beperken bij kou** (vanaf 1.19.0, per set op de kaart *Grenzen set N*, staat uit): voor sets op een
  koude plek (schuur, garage). Het maximale laadvermogen van die set volgt de koudste accupack (`maxTemp` in het
  rapport; zonder packgegevens de temperatuur van de hub):
  * vanaf *Volle laadkracht vanaf* (standaard 10 °C): 100 %;
  * daaronder lineair omlaag naar *Laadvermogen bij 0 °C* (standaard 30 %);
  * bij 0 °C en kouder: dat minimum.

  Voorbeeld met de standaardwaarden: bij 5 °C laadt een set van 2400 W met hoogstens 1560 W (65 %). Het geldt voor
  de regeling én de planner, die dan minder snel laden van het net plant. Ontladen wordt niet beperkt. Welke sets
  beperkt worden staat in het attribuut `koudebeperking` van `sensor.zendure_ems_prijsactie`, bijvoorbeeld
  *Set 1: 65 % (5.0 °C)*. De twee temperatuurgrenzen gelden voor alle sets met de schakelaar aan.
* Opdrachten gaan alleen naar een set als zijn vermogen meer dan 15 W moet veranderen, en worden
  in het RAM gezet (`smartMode=1`): dat geeft geen slijtage van het flashgeheugen.
* **Min/max SOC** per set wordt ook in de set zelf opgeslagen (minSoc 5–50 %, socSet 70–100 %), maar alleen als
  de waarde afwijkt.
* De set-eigen grenzen uit de Zendure-app (max uitgangsvermogen, max laadvermogen) blijven gelden:
  het package neemt steeds de laagste van die grenzen en de grenzen in het dashboard.
* **Veiligheid:** is de netmeter weg of al meer dan 60 s niet bijgewerkt, dan gaan alle sets naar 0 W.
  Bij het afsluiten van Home Assistant krijgen alle sets 0 W.

## Kalibratie: een set haalt tussendoor al 100 %

Met *Volladen naar 100 %* kies je wanneer de sets naar 100 % laden, zodat het BMS zijn SOC kan ijken. Elke set wordt
apart bekeken, met zijn eigen datum *Set N laatst 100 %*. Bij *Wekelijks*, *Elke 2 weken* of *Elke 3 weken* is een set
op de gekozen dag aan de beurt als hij minstens 7 × aantal weken − 1 dag geen 100 % heeft gehaald (6, 13 of 20
dagen). Die ene dag marge is er omdat een kalibratie vaak pas in de nacht na de gekozen dag klaar is (tot *Klaar om*):
zo blijft een vaste ronde precies 1, 2 of 3 weken. Het aantal dagen telt tot het begin van die dag en wordt naar boven
afgerond. De gekozen dag valt nooit op of na *Uiterlijk na* (standaard 28 dagen): zou de volgende gekozen dag te laat
zijn, dan doet de set al mee op de laatste gekozen dag daarvoor. *Uiterlijk na* blijft het vangnet als een kalibratie
mislukt.

**Voorbeeld:** *Elke 3 weken* op *zondag*, *Uiterlijk na* 28 dagen. Beide sets waren op vrijdag 13 november voor het
laatst vol. Set 2 haalt op woensdag 2 december door de zon al 100 %.

![Tijdlijn: set 2 haalt op 2 december 100 % door de zon, slaat daardoor de kalibratie van 6 december over en doet op 27 december weer mee](docs/kalibratie-voorbeeld.png)

* **Set 1** volgt het schema. Op 15, 22 en 29 november is hij te vroeg (2, 9 en 16 dagen). Op zondag 6 december zijn
  het 23 dagen: hij laadt naar 100 % en is in de nacht naar maandag 7 december klaar. Daarna is hij op 13 en
  20 december te vroeg (6 en 13 dagen) en op 27 december (20 dagen) weer aan de beurt.
* **Set 2** haalt op 2 december 100 %. De automatisering *100 % bereikt bijhouden* zet *Set 2 laatst 100 %* binnen
  2 minuten op 2 december; het maakt niet uit hoe de 100 % ontstond. Dat telt als kalibratie. Op 6 december zijn het
  pas 4 dagen: set 2 slaat deze ronde over en alleen set 1 laadt. Op 13 en 20 december zijn het 11 en 18 dagen (te
  weinig), op 27 december 25 dagen: dan is set 2 aan de beurt, nog voor *Uiterlijk na* (28 dagen).
* **Gevolg:** set 2 slaat één ronde over en loopt op 27 december weer gelijk met set 1. De *Status* toont steeds de
  eerstvolgende datum van alle sets samen (hier *Volgende: zo 06-12*). Per set staat het op de regel
  *Set N volgende 100 %*: op 2 december *zo 06-12 (over 4 dagen)* voor set 1 en *zo 27-12 (over 25 dagen)* voor set 2.
* **Toch op 6 december laten meedoen:** zet *Set 2 laatst 100 %* met de hand terug op 13 november. Dan doet set 2 op
  6 december weer mee (hij is dan al bijna vol, dus dat kost weinig).
* **Waar ligt de grens?** Een set doet mee op de eerste gekozen dag die minstens 20 dagen na zijn laatste 100 % ligt.
  Vol op maandag 16 november of eerder (bijvoorbeeld de kalibratie van zondag 15 november, klaar om 04:46):
  6 december. Vol tussen 17 en 23 november: 13 december. Vol tussen 24 en 30 november: 20 december.

## Automatiseringen in het package

`packages/zendure_ems.yaml` maakt de volgende 13 automatiseringen aan. Je vindt ze onder
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
| **sets in standby na inactiviteit** | Een set staat langer dan *standby na inactiviteit* (minuten) op 0 W (de limiet van zijn huidige richting is 0) | Zet die set eenmalig in standby (smartMode 0, beide limieten 0) zodat hij minder verbruikt. Vraagt de regeling weer vermogen, dan gaat de set met smartMode 1 weer aan. |
| **profiel activeren** | Je kiest een profiel in de keuzelijst | Zet de instellingen van dat profiel (modus, slim laden/ontladen, prijsdrempels, minimale winst, slijtage, afschalen; een eigen profiel ook *minimale winst bij vasthouden* en *zon slim verdelen*) en zet de keuzelijst terug op *Kies een profiel*. |
| **zonnepanelen afschalen bij negatieve prijs** | Bij wijziging van terugleverprijs, gemiddelde SOC of afschaalinstellingen, elke minuut en bij het starten | Schaalt bij een negatieve prijs de omvormer af naar het huisverbruik en zet een extra apparaat op zijn afgeschaalde limiet (direct, of pas als alle sets vol zijn). Zet alles terug zodra de prijs weer boven de drempel komt. |
| **seizoen** | Bij een andere keuze in *Seizoen*, dagelijks op de controletijd (standaard 20:00), na het activeren van een profiel, bij een gewijzigde seizoenswaarde en bij het starten | Zet *Minimale winst per kWh* en *Slijtagekosten per kWh* op de waarden van het actieve seizoen. Op *Automatisch* kiest ze winter of zomer met het verwachte zonoverschot morgen. Doet niets als *Seizoen* op *Uit* staat. Zie [Seizoen (winter en zomer)](#seizoen-winter-en-zomer). |

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

## Gepland tegenover werkelijk

Vanaf 1.18.0 houdt `sensor.zendure_ems_gepland_tegenover_werkelijk` bij wat de planner verwachtte te besparen,
naast wat de accu echt bespaarde. Elk kwartier, 40 seconden na het begin, telt hij de
geplande waarde van dat kwartier op: wat de accu volgens het plan aan het huis geeft (tegen de afnameprijs) en
verkoopt (tegen de terugleverprijs), min wat laden van het net (afnameprijs) en laden met zon (terugleverprijs)
kost. Dat is dezelfde weging als de besparingsteller. Werkelijk is (vanaf 1.18.1) wat de besparingsteller in
precies die kwartieren veranderde; een kwartier zonder plan, of dat door een herstart niet afgesloten kon worden,
telt aan geen van beide kanten mee.

* Status: de geplande besparing deze maand. Attributen: `gepland_vandaag`, `werkelijk_vandaag`, `gepland_maand`,
  `werkelijk_maand`, `verschil_maand`, `werkelijk_in_procent_van_gepland`, `maanden` (de laatste 12 maanden),
  `sinds` (vanaf 1.18.1) en `dagen` (de laatste 14 dagen, vanaf 1.19.0). Met *Minimale winst bijleren* aan
  gebruikt de EMS die 14 dagen om de minimale winst bij te stellen (zie [De planner](#de-planner-per-kwartier),
  punt 4); `drempel_correctie` en `drempel_reden` laten zien wat hij deed.
* Op het tabblad Statistieken, onder *Besparing door de accu*, staat de kaart *Gepland tegenover werkelijk*.
* Valt werkelijk steeds lager uit dan gepland, dan staat *Minimale winst* of *Slijtagekosten* waarschijnlijk te
  laag, of kloppen de verbruiks- of zonverwachting niet. Valt werkelijk hoger uit, dan rekent de planner te
  voorzichtig. Een paar dagen verschil is normaal: het weer en het verbruik wijken altijd wat af.
* De telling begint opnieuw bij de installatie van 1.18.1, ook in de lopende maand (attribuut `sinds`; de kaart
  toont dan *Deze maand geteld vanaf …*).

## Energiedashboard

`sensor.zendure_ems_energie_geladen` en `sensor.zendure_ems_energie_ontladen` (kWh) kun je bij
*Instellingen → Dashboards → Energie → Thuisbatterij* toevoegen.

## Problemen

| Symptoom | Oorzaak / oplossing |
|---|---|
| Rapport-sensor blijft *onbekend* | IP klopt niet, of de lokale API is niet bereikbaar: test `http://IP/properties/report` |
| Set volgt opdrachten na 10 s niet meer | HEMS staat nog aan in de Zendure-app |
| Status *Geen (verse) netmeting* | Verkeerde netsensor-naam, of de sensor werkt niet meer bij |
| Ontladen blijft steken op 800 W | Max uitgangsvermogen staat in de Zendure-app op 800 W |
| Prijsactie blijft *Geen prijsdata* | Prijssensor heeft geen `raw_today`, `forecast` of `prices_today`-attribuut. Met een versie vóór 1.15.3 ook als de blokken in `raw_today` geen `end` hebben (log: *has no attribute 'end'*): werk bij naar 1.15.3. Bij *Prijsbron* *Bloktarief*: de regel *Bloktarief* is leeg of onleesbaar (*Bloktarief nu* toont *Geen geldige blokken ingevuld*) |
| Log: *State attributes … exceed maximum size of 16384 bytes* voor de prijssensor | Onschuldig: alleen de attributen worden dan niet in de database bewaard. Bij een eigen template-sensor kun je `end` weglaten (werkt vanaf 1.15.3) |
| Accu laadt 's ochtends geen zon, terwijl er overschot is | Bedoeld als de prijsactie *Zon terugleveren, accu later vullen* is: de planner levert nu terug tegen een betere prijs en vult de accu later. Wil je dat niet, zet dan *Zon slim verdelen* uit (Instellingen → Prijssturing) |
| Planner houdt de accu vast voor een klein prijsverschil | Verhoog *Minimale winst bij vasthouden en zon verdelen* (standaard 0,02 €/kWh) |
| Planner laadt nooit van het net | *Slim laden* staat uit, de prijsverschillen zijn kleiner dan *minimale winst* plus verlies en slijtage, of de zon dekt het tekort |
| Set springt bij heel kleine vraag aan en uit | Verhoog *Minimaal vermogen per set* of de *dode zone* |
| Veel relaisschakelingen bij een waterkoker of droger | Zet *Korte dips negeren* aan (bijvoorbeeld 30 s); vanaf 1.13.1 schakelt een extra set ook niet meer steeds bij en af. Verhoog eventueel *Volgende set inzetten vanaf* |
| Planner laadt terwijl de zon het zou doen | Controleer *zonbron* in de prijsactie-attributen; staat *Zonneverwachting meetellen voor* niet te laag? |
| *Minimale winst* of *Slijtagekosten* springt terug na een wijziging | Het seizoen staat aan en zet de seizoenswaarde terug. Verander de winter- of zomerwaarde op *Instellingen → Seizoen*, of zet *Seizoen* op *Uit* |
| *Actief profiel* toont *Mijn profiel 1* terwijl je een ingebouwd profiel koos | Je eigen profiel heeft dezelfde strategie en dezelfde minimale winst en slijtage als het seizoen. De EMS vergelijkt eerst met de eigen profielen. Maak het eigen profiel anders of laat het leeg (zie [Mijn profiel 1 en 2 met het seizoen](#mijn-profiel-1-en-2-met-het-seizoen)) |
| Seizoen wisselt niet op *Automatisch* | Kijk naar *Verwacht zonoverschot morgen*: is die *niet beschikbaar*, controleer dan *Zonneverwachting morgen* bij Aansluiting. Ligt de waarde tussen de twee grenzen, dan blijft het seizoen bewust staan. Staat de *Automatisering seizoen* aan? |
| Seizoen wisselt te vaak | Maak het gat tussen *Winter als zonoverschot onder* en *Zomer als zonoverschot boven* groter, bijvoorbeeld −10 % en 60 % |
| Na de update dubbele seizoenshelpers (`_2`) of een fout over dubbele ID's | De seizoensfunctie bestond al als losse helpers. Zie [Overstappen van losse helpers](#overstappen-van-losse-helpers) |
| Melding over te grote attributen in het log | Zet `sensor.zendure_ems_planning` in de recorder-exclude (zie installatie) |
