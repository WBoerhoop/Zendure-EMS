# Changelog

Alle noemenswaardige wijzigingen in Zendure EMS staan in dit bestand, de nieuwste bovenaan.
Versienummers volgen het schema `MAJOR.MINOR.PATCH`.

**Na elke update:** vervang `packages/zendure_ems.yaml`, herstart Home Assistant en plak
`dashboards/dashboard.yaml` opnieuw in de Raw-configuratie-editor van je dashboard.
Je bestaande instellingen blijven bewaard.

## [1.13.1] – Minder relaisschakelingen bij het bijschakelen van een extra set

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

## [1.13.0] – Alleen slim opladen en Alleen slim ontladen, ook per set

* **Twee nieuwe modi**, zoals *Alleen slim opladen* en *Alleen slim ontladen* in
  [Gielz' Zendure-HA-zenSDK](https://github.com/Gielz1986/Zendure-HA-zenSDK/wiki/NL-%E2%80%90-Modussen): nul op de
  meter in één richting.
  * **Alleen slim opladen**: de sets laden van zonne-overschot (net rond 0 W), maar ontladen nooit. Status
    *Alleen slim opladen: niet ontladen* als het huis stroom vraagt.
  * **Alleen slim ontladen**: de sets ontladen voor het eigen verbruik (net rond 0 W), maar laden nooit, ook niet van
    de zon. Status *Alleen slim ontladen: niet laden* bij zonne-overschot.
  * Prijzen en de planner spelen in deze modi geen rol (zoals bij *Nul op de meter*). Beide staan ook als profiel in
    *Profiel activeren*.
* **Eigen modus per set** (`input_select.zendure_setN_setmodus`, op de setkaart onder *Eigen modus*):
  * **Volgt EMS-modus** (standaard): de set doet wat de modus zegt, zoals tot en met 1.12.8.
  * **Alleen slim opladen**: deze set laadt alleen van zonne-overschot en ontlaadt nooit.
  * **Alleen slim ontladen**: deze set ontlaadt alleen voor het eigen verbruik en laadt nooit.

  Zo kun je bijvoorbeeld set 1 de zon laten opvangen en set 2 's avonds het huis laten voeden. Een set in een eigen
  modus doet alleen mee aan nul op de meter: hij **laadt niet van het net** (netladen, *Laden (vol vermogen)*) en
  **verkoopt niet** (verkopen, *Ontladen (vol vermogen)*). De andere sets nemen dat over, en de planner rekent die set
  niet mee voor netladen en verkopen. De eigen modus werkt in alle modi die de sets aansturen (dus niet bij *Niet
  aansturen* en *Uit*). *Laden toegestaan* en *Ontladen toegestaan* blijven daarnaast gelden.
* Een set in *Alleen slim ontladen* doet niet mee aan de **kalibratie** (hij laadt nooit naar 100 %).
* Na de update staat elke set op *Volgt EMS-modus*: er verandert niets tot je zelf een eigen modus kiest.
* Plak na de update het nieuwe `dashboards/dashboard.yaml` in je dashboard.

## [1.12.8] – Gemeten rendement per set

* **Rendement per set uit de Zendure-integratie.** Heb je naast Zendure EMS ook de integratie *Zendure Home Assistant*
  (`zendure_ha`) draaien, dan gebruikt de EMS de **retourrendementen die die integratie per set meet** (de sensoren
  `…_roundtrip_efficiency`). Je hoeft niets in te vullen: de EMS zoekt per set de sensor van het apparaat met
  **hetzelfde serienummer**. Zonder integratie, of als een meting ontbreekt of buiten 50–100 % valt, telt die set met
  het vaste *Rendement heen en terug* (standaard 85 %), zoals tot en met 1.12.7.
* **Waarom?** Sets verschillen echt. Gemeten bij een 2400 AC+ en een 2400 AC (beide 5 packs): 85,4 % en 81,9 %. Elke kWh
  die via de minder zuinige set heen en terug gaat, verliest zo'n 3,5 % meer. Een vast rendement voor alle sets laat dat
  liggen op twee plekken:
  * **De planner** rekent met één rendement voor het hele systeem (laden loont als *prijs ÷ rendement + slijtage +
    minimale winst* ≤ latere prijs; verkopen met √rendement aan beide kanten). Dat is nu het **capaciteitsgewogen
    gemiddelde** van de gemeten sets, omdat de energie in de planning over de sets verdeeld wordt naar hun capaciteit.
    Een te hoog vast rendement laat de planner laden en verkopen bij een te klein prijsverschil; een te laag laat
    winst liggen.
  * **De regeling** koos bij een kleine vraag (één set aan het werk) puur op SOC. Nu weegt het rendement mee als
    kleine voorkeur: een set die zuiniger is dan het gemiddelde van de sets die mogen meedoen, telt alsof zijn SOC
    **2 punten hoger is per % rendement** (bij laden: lager), **hoogstens 10 punten**. Bij 85,4 % tegen 81,9 % is
    dat 7 SOC-punten: tot dat verschil doet de AC+ het werk, daarboven neemt de AC het weer over. Zo gaan zoveel
    mogelijk kWh via de zuinige set, terwijl de sets niet blijvend uit elkaar lopen (de SOC blijft leidend). De
    bestaande voorkeuren (een set die al draait, of al in de goede richting staat) blijven gelden. Werken meerdere
    sets tegelijk, dan verandert de verdeling tussen hen niet.
* **Nieuw:** `input_boolean.zendure_ems_rendement_meten` (*Gemeten rendement per set gebruiken*, Instellingen →
  *Prijssturing*, na de update aan; uit = het vaste rendement zoals vroeger), `sensor.zendure_ems_rendement` (het
  rendement dat de planner gebruikt, met de attributen `gemeten`, `bron` en `vast`, elke 5 minuten bijgewerkt) en per
  set `sensor.zendure_setN_rendement` (op de setkaart onder *Instellingen*, met attribuut `bron`: de sensor, of
  *vast*). De prijsactie heeft het nieuwe attribuut `rendement`.
* *Rendement heen en terug* heet op het dashboard nu *Rendement heen en terug (vast, zonder meting)*: het is de
  terugvalwaarde.
* **Na het bijwerken (vanaf 1.12.7 of eerder), zelf doen:**
  1. Had je een eigen automatisering (of script) die *Rendement heen en terug* op een gemeten waarde zet, **verwijder
     die**. De EMS doet dit nu zelf, en per set. Blijft hij staan, dan overschrijft hij het vaste terugvalrendement.
  2. Zet daarna *Rendement heen en terug (vast, zonder meting)* terug op **85 %**, of op je eigen gemeten waarde als
     je de Zendure-integratie niet hebt. Dit getal geldt nu alleen nog voor een set zonder meting.
  3. Kijk op de setkaarten (Instellingen) bij *Rendement heen en terug* of elke set een gemeten waarde heeft. Het
     attribuut `bron` toont de sensor, of *vast* als er geen meting gevonden is.
* Plak na de update het nieuwe `dashboards/dashboard.yaml` in je dashboard.

## [1.12.7] – Energiestroom overdag en 's nachts

* **Dag- en nachtversie van de Energiestroom.** Zolang de zon op is (`sun.sun` = *above_horizon*) toont de kaart
  een lichte dagversie van het huis: blauwe lucht met zon, groen gras, glazen ramen in plaats van verlichte, en de
  tuinlampjes uit. 's Nachts (en als `sun.sun` ontbreekt) blijft de bekende donkere versie staan. Het is dezelfde
  tekening: de accutorens van set 2 en 3, de bewegende lijnen en de waarden liggen er op dezelfde plek overheen.
  De lucht is overdag bewust middenblauw, zodat de witte tekst leesbaar blijft.
* **Beter leesbare waarden.** De namen onder de waarden (NET, ZON, HUIS, ACCU'S, AUTO) zijn helemaal wit in plaats
  van lichtgrijs, de waarden staan iets verder van hun naam en alle waarden (ook de SOC) hebben een donkere rand.
* Het dashboard wordt daardoor ongeveer 40 kB groter (de dagversie zit, net als de nachtversie, in het bestand
  zelf; je hoeft nog steeds niets naar `/config/www` te kopiëren). Geen nieuwe velden, het package verandert alleen
  van versienummer. Plak na de update het nieuwe `dashboards/dashboard.yaml` in je dashboard.

## [1.12.6] – Rustiger bij klein vermogen, sneller met een meter van 1 s, juiste prijs na een herstart

* **Minimale looptijd bij klein vermogen** (`input_number.zendure_ems_min_looptijd`, Instellingen → *Regeling*,
  standaard 60 s, ook na de update; 0 = uit). Schommelt de vraag rond het *minimaal vermogen per set* (bijvoorbeeld
  als zon en huisverbruik bijna gelijk zijn), dan ging een set steeds aan en uit. Nu blijft een set die start
  minstens deze tijd op het minimum lopen, en rust hij na het stoppen de helft van die tijd voordat een kleine vraag
  hem weer start. Een grote vraag of een duidelijk overschot (meer dan *minimaal vermogen + dode zone*) gaat altijd
  direct door. In de simulatie: 28 → 11 schakelingen in 10 minuten. De status toont *Minimale looptijd (nog … s)* of
  *Rusttijd na stoppen (nog … s)*. Nieuw attribuut `geschakeld` van `sensor.zendure_ems_regelaar`.
* **Nordpool na een herstart:** de Nordpool-integratie geeft na een herstart van Home Assistant tot het volgende
  kwartier soms prijzen zonder opslag (energiebelasting, btw, leverancier), omdat haar kostentemplate te vroeg draait.
  De afnameprijs lag dan ongeveer € 0,20 te laag, en de planner zag verkopen of laden als winstgevend terwijl dat niet
  zo was. Nu onthoudt de planner de laatste opslag (`nordpool_opslag`, `nordpool_opslag_tijd` van
  `sensor.zendure_ems_prijsactie`) en telt die erbij zolang Nordpool 0 opslag meldt, hooguit 2 uur
  (`nordpool_opslag_hersteld` = true, prijsbron *Nordpool (opslag hersteld na herstart)*).
* **Wachttijd automatisch klopt nu ook bij een meter van 1 s.** De regeling schatte het meterinterval uit de tijd
  tussen twee *veranderingen* van de meterwaarde. Blijft het vermogen een paar seconden gelijk, dan leek een DSMR
  5-meter (elke seconde) daardoor veel trager: bij een Kaifa-meter met HomeWizard P1 kwam de schatting op 10 s en de
  wachttijd op 9,5 s. Nu volgt de schatting de korte tussenpozen snel (halverwege per meting) en de lange maar
  langzaam (5 %), dus de ondergrens: het echte meterinterval. Bij een meter van 1 s wordt de wachttijd zo ongeveer
  3–3,5 s; een meter van 10 s (DSMR 4) houdt zijn lange wachttijd. Kijk op de kaart *Regeling* bij *Gemeten meterinterval* hoe snel je meter echt
  bijwerkt.
* **HomeWizard P1: gebruik homewizard-instant als het interval rond 10 s blijft.** Sommige P1-meters geven via de
  oude lokale API (`/api/v1/data`, het *HomeWizard P1 IP-adres* in het package, of een eigen REST-sensor met
  `scan_interval: 1`) maar elke 10 s een nieuwe waarde, ook bij een DSMR 5-meter. De integratie
  [homewizard-instant](https://github.com/taurgis/homeassistant-homewizard-instant) (HACS) leest de P1 elke seconde
  via de nieuwere API. Vul de vermogenssensor daarvan in bij *Netmeter-sensor* en maak *HomeWizard P1 IP-adres*
  leeg, zodat de P1 niet dubbel wordt bevraagd. Gemeten bij een Kaifa DSMR 5-meter: meterinterval van 10 s naar
  1 s, wachttijd van 9,5 s naar 3 s.
* **Planner toont starttijden:** in de uurtabel van de planner staan bij laden, verkopen en vasthouden de kwartieren
  als die niet het hele uur beslaan, bijvoorbeeld *verkopen 1,1 (16:30–17:00)*. Bovenaan staat **Volgende:** met de
  eerstvolgende tijden voor verkopen en laden, bijvoorbeeld *verkopen 16:30–19:15 · laden morgen 01:45–02:00*. De
  kaarten op *Overzicht* bevatten alleen het deel dat ze tonen, zodat het dashboard klein blijft.
* **Dashboard:** de rijen *Net* (Overzicht en EV) en *Huisverbruik* (Instellingen) gebruiken nu de 5-secondensensoren
  `sensor.zendure_ems_grafiek_net` en `sensor.zendure_ems_grafiek_huisverbruik`: minder verkeer naar de browser en
  een werkende geschiedenis als je de snelle sensoren in de recorder-exclude hebt staan.
* De tests vinden de generator nu ook zonder `PYTHONPATH`.

## [1.12.5] – Kalibratie tot de volgende ochtend, verkopen telt mee

* **Klaar de volgende ochtend** (`input_number.zendure_ems_kalibratie_tot`, Instellingen → kaart *Kalibratie*,
  standaard 7 uur, ook na de update). De kalibratiedag loopt door tot dat uur de volgende ochtend, zodat de
  goedkope nacht erna gebruikt kan worden, juist na een avondpiek waarin verkocht wordt. Tot dat uur blijft de set
  *Bezig* (max SOC 100 %). Met 0 is het weer middernacht, zoals tot en met 1.12.4.
* **Gepland verkopen telt mee.** Wat de kalibrerende set vóór zijn laatste kalibratiekwartier verkoopt (zijn deel van
  de geplande verkoop), plant de planner er na de laatste verkoop bij, in de goedkoopste kwartieren tot *Klaar om*.
  Verkopen blijft voorgaan; de kalibratie past zich eromheen aan.
* **Nieuwe attributen** van `sensor.zendure_ems_prijsactie`: `kalibratie_verkoop_kwh` (wat de set vooraf verkoopt)
  en `kalibratie_klaar_om` (tot wanneer de planner kalibratiekwartieren kiest).
* Paragraaf 8.5 van de handleiding is bijgewerkt, met een rekenvoorbeeld voor verkopen in de avondpiek.

## [1.12.4] – Betere kalibratieplanning

* **Aantal kwartieren klopt nu ook met meerdere sets.** De planner telde de kwartieren per set met het eigen
  max laadvermogen van die set. Nu telt hij ook:
  * *Systeem max laden*: is dat lager dan de som van de kalibrerende sets, dan krijgt elke set naar verhouding
    minder vermogen en plant hij meer kwartieren;
  * laden dat de gewone planning al in een kwartier had gezet (bijvoorbeeld voor de andere set): alleen het vrije
    vermogen telt mee, een vol kwartier wordt overgeslagen;
  * het **huisverbruik**: wat de kalibrerende set vóór het laatste kalibratiekwartier nog aan het huis geeft
    (zijn deel van de geplande ontlading, hooguit tot zijn min SOC), wordt er goedkoop bij ingekocht.
* **Voorrang betekent nu echt vol vermogen.** In een kalibratiekwartier laadt de kalibrerende set eerst op zijn
  volle vermogen; een andere set krijgt alleen wat daarboven overblijft. Voorheen schakelde *Staging* (standaard
  60 %) de tweede set er al bij en kreeg die een deel van de kalibratie-energie.
* **Nieuwe attributen** van `sensor.zendure_ems_prijsactie`: `kalibratie_tekort_kwh` (opgeslagen kWh tot 100 %),
  `kalibratie_huis_kwh` (wat de set vooraf nog aan het huis geeft), `kalibratie_netladen_kwh` (ingepland van het
  net) en `kalibratie_niet_ingepland_kwh` (wat vóór de deadline niet meer past; normaal 0).
* De handleiding heeft een aparte paragraaf **8.5 Kalibratie** met de berekening, rekenvoorbeelden en de gevolgen.

## [1.12.3] – Rustiger regelen, minder slijtage, kleinere database

* **Wachttijd automatisch** (`input_boolean.zendure_ems_wachttijd_auto`, Instellingen → *Regeling*, staat na de
  update aan). De regeling meet hoe vaak je netmeter een nieuwe waarde geeft (attribuut `meterinterval` van
  `sensor.zendure_ems_regelaar`) en wacht na een opdracht 2,5 s + 0,7 × dat interval, met minimaal 3 s en hoogstens
  10 s (attribuut `wachttijd_auto`): een meter die elke seconde bijwerkt geeft 3 s, een meter van 5 s geeft 6 s.
  Een te korte wachttijd bij een trage meter liet de regeling doorschieten en de sets steeds wisselen tussen laden en
  ontladen. Zolang er nog niets gemeten is, en als je de schakelaar uitzet, geldt *Wachttijd na opdracht*.
* **Minder flash-schrijfacties bij kleine vermogens:** werkt één set alleen, dan krijgt een set die al in de goede
  richting staat (acMode laden of ontladen) voorrang, zodat er geen nieuwe acMode naar het flashgeheugen hoeft. Het
  verschil in SOC weegt pas mee boven 15 %; bij grotere vermogens verdeelt de regeling zoals voorheen.
* **Kleinere database:** met een P1 die elke seconde bijwerkt, veranderen `sensor.zendure_ems_netvermogen` en
  `sensor.zendure_ems_huisverbruik` ook elke seconde. De grafiek *Vermogen* gebruikt nu
  `sensor.zendure_ems_grafiek_net` (elke 5 s; ook `sensor.zendure_ems_grafiek_huis` is er). Zet
  `sensor.zendure_ems_netvermogen` en `sensor.zendure_ems_huisverbruik` in de recorder-exclude (zie *Installatie*).
  De regeling zelf blijft op de snelle waarden werken.
* **P1 alleen elke seconde met IP-adres:** zonder IP-adres van de HomeWizard P1 doet het package geen verzoek per seconde
  meer (de REST-bron vraagt zichzelf alleen elk uur op). Met IP-adres vraagt een trigger elke seconde een nieuwe meting
  op. Nieuwe sensor `sensor.zendure_ems_netmeter_bron` (kaart *Aansluiting*): welke meter de regeling nu gebruikt.
* **Nieuwe standaardwaarden** (alleen bij een nieuwe installatie; je eigen instellingen blijven): *Kp* 0,6 (was 0,7),
  *Kd* 0 (was 0,15), *dode zone* 35 W (was 25 W), *minimaal vermogen per set* 100 W (was 50 W). Rustiger, met minder
  relaisschakelingen; vragen tot ongeveer 60 W gaan naar het net.

## [1.12.2] – HomeWizard P1 elke seconde

* **HomeWizard P1 rechtstreeks uitlezen** (`input_text.zendure_ems_p1_ip`, Instellingen → *Aansluiting*). De
  HomeWizard-integratie van Home Assistant vraagt de P1 maar elke 5 s uit, terwijl een DSMR 5-meter elke seconde een
  nieuwe meting geeft. Vul het IP-adres van je P1 in, dan leest het package de meter zelf elke seconde uit via de
  lokale API v1 (`http://IP/api/v1/data`) in de nieuwe sensor `sensor.zendure_ems_p1_vermogen`.
* Zolang die meting vers is (minder dan 10 s oud), gebruikt de regeling de P1; anders valt hij vanzelf terug op de
  *Netmeter-sensor* die je had ingevuld. Laat die dus gewoon staan. *Netmeter omkeren* geldt niet voor de P1
  (die meet altijd + = afname).
* **Voorwaarden:** zet in de HomeWizard Energy-app bij de P1 de **lokale API** aan en geef de P1 een **vast
  IP-adres** in je router. Zet `sensor.zendure_ems_p1_vermogen` in de recorder-exclude (hij werkt elke seconde bij).
* Met een meting elke seconde kan de regeling sneller: *Wachttijd na opdracht* 3–4 s en een *dode zone* van
  ongeveer 30–35 W. Met de meting van 5 s is 6 s wachttijd en 50 W dode zone rustiger (minder relaisschakelingen).
  Vanaf 1.12.3 stelt *Wachttijd automatisch* de wachttijd zelf in.
* Zonder IP-adres verandert er niets.

## [1.12.1] – Relais, kalibratie en overzicht automatiseringen

* **Overzicht van alle automatiseringen** die het package aanmaakt, met per automatisering wanneer ze start en wat
  ze doet: zie *Automatiseringen in het package* in de LEESMIJ en **hoofdstuk 13** van de handleiding.
* **Tabblad Statistieken, sectie *Relais en kalibratie*** (voor elke set, set 2 en 3 alleen met IP-adres):
  relaisschakelingen per dag (hoe vaak de set is gaan laden of ontladen, stippellijn bij 100) en kalibraties
  (hoogste SOC per dag, groen bij 100 %), zoals bij Gielz. Vereist ApexCharts Card. Na het bijwerken staat de sectie
  dicht: tik op de kop om hem te openen.
* Nieuwe sensoren per set: `sensor.zendure_setN_modus` (Opladen/Ontladen/Standby, onder 20 W = Standby),
  `sensor.zendure_setN_relais_opladen_vandaag`, `sensor.zendure_setN_relais_ontladen_vandaag` en
  `sensor.zendure_setN_relais_schakelingen_vandaag`. De kalibratiekaart gebruikt de bestaande
  `sensor.zendure_setN_soc` en `sensor.zendure_setN_dagen_sinds_vol`.
* Handleiding, **bijlage E**: omvormertemperatuur van een SolarFlow 2400 AC+ (I2400) in een automatisering.
* Plak `dashboard.yaml` opnieuw in de Raw-configuratie-editor en herstart Home Assistant voor het package.

## [1.12.0] – Geoptimaliseerd

* **Regeling rustiger:** wisselen tussen laden en ontladen gebeurt pas als ook de vorige meting (5 s eerder) die
  kant op wees; de eerste meting zet de set op 0 W. Een apparaat dat even uitvalt wordt zo niet meer achterna gejaagd.
* **Lichter voor de database:** `sensor.zendure_setN_vermogen` heeft geen snel wisselende attributen meer (`commando`,
  `zonnevermogen`); de status toont bij een genegeerde dip geen lopende secondenteller meer. Aanbevolen: zet
  `sensor.zendure_ems_netmeting` (kopie van je P1-meter, elke seconde) in de recorder-exclude.
* **Rekenwerk:** de kalibratie-instellingen worden één keer per ronde berekend in plaats van per set.
* **Dashboard bijna half zo groot** (242 → 135 kB): accutorens 2 en 3 zijn kleine losse afbeeldingen over het huis, en
  de afbeeldingen zijn compacter gecodeerd. Plak `dashboard.yaml` opnieuw in de Raw-configuratie-editor.
* **Herstel:** *Korte dips negeren tot* begon na de update van 1.11.1 op 5 s (het minimum); de update zet hem op 20 s.
* De updatemelding toont alleen de laatste versies; de volledige lijst staat in deze CHANGELOG.

## [1.11.1]

* **Korte dips negeren** (`input_boolean.zendure_ems_korte_dips_negeren`, met *Korte dips negeren tot*, standaard
  20 s). Zet hem aan en uit vanuit de automatisering van een apparaat dat steeds even uitvalt, zoals een droger.
  Ontlaadt de accu en ontstaat er plotseling overschot, dan blijft de accu die tijd doorleveren; pas als het overschot
  langer aanhoudt, regelt het EMS terug. Voorbeeld in een droger-automatisering:
  ```yaml
  - action: input_boolean.turn_on     # bij de start van het programma (turn_off bij programma klaar)
    target:
      entity_id: input_boolean.zendure_ems_korte_dips_negeren
  ```

## [1.11.0]

* **Eén package en één dashboard** voor 1, 2 of 3 sets (`packages/zendure_ems.yaml`, `dashboards/dashboard.yaml`).
  Alles van set 2 en 3 (meters, kaarten, grenzen, kalibratie, de accutorens in de Energiestroom) verschijnt pas als
  het IP-adres van die set is ingevuld. Een set zonder IP-adres vraagt Home Assistant zelf om een klein bestand
  (`/manifest.json`), zodat de rapportsensor gewoon bestaat en er geen herhaalde waarschuwingen in het logboek komen.
* **Bijwerken:** verwijder `zendure_ems_2sets.yaml` of `zendure_ems_3sets.yaml` uit `config/packages/` en zet
  `zendure_ems.yaml` ervoor in de plaats. Alle namen zijn gelijk; je instellingen blijven bewaard. Plak daarna
  `dashboard.yaml` in de Raw-configuratie-editor.

## [1.10.3]

* Twee modi: **Laden (vol vermogen)** en **Ontladen (vol vermogen)**. Alle sets laden van het net op hun max
  laadvermogen tot de max SOC (de maximale netafname blijft gelden), of ontladen op hun max ontlaadvermogen tot min SOC
  + reserve, ook naar het net. Is de accu 2 minuten vol of leeg, dan gaat de modus vanzelf terug naar de modus van
  daarvoor (`input_text.zendure_ems_vorige_modus`, anders Nul op de meter) en krijg je een melding.
* Herstel: *Profielen Handelen verkopen boven* die bij de vorige update op 0 bleef staan, wordt op 0,35 gezet.

## [1.10.2]

* **Verkopen plannen** (`input_boolean.zendure_ems_verkoop_plannen`, aangezet door de profielen *Dynamisch Handelen*
  en *Dynamisch Handelen + NOM*). De planner kiest de verkoopkwartieren (terugleverprijs ≥ *verkopen boven*, duurste
  eerst) en verkoopt alleen als terugleverprijs × √rendement − slijtage − minimale winst ≥ inkoopprijs ÷ √rendement.
  Energie komt uit de accu voor zover die niet meer nodig is voor eigen verbruik in de rest van de planning, of wordt
  bewust extra ingekocht op de goedkoopste eerdere kwartieren (zonder dat de accu overloopt). Het vermogen volgt uit
  de geplande kWh plus het huisverbruik op dat moment.
* Nieuwe attributen van de prijsactie: `verkoopvermogen`, `gepland_verkopen_kwh`, `inkopen_voor_verkoop_kwh`,
  `verwachte_handelswinst`, `verkoopmomenten`. In de planner-tabel: 💶 verkopen.
* Na de update het profiel Handelen één keer opnieuw activeren, zodat Verkopen plannen aan gaat.

## [1.10.1]

* Profiel **Dynamisch Handelen + NOM** (zoals bij Gielz): Prijsgestuurd, slim laden aan, slim ontladen uit, verkopen
  aan het net boven *Profielen Handelen verkopen boven*. Laadt in de goedkope kwartieren, verkoopt boven die prijs op vol
  vermogen en houdt de rest van de tijd de meter op 0. Bij *Dynamisch Handelen* blijft slim ontladen aan: de accu wordt
  dan buiten het verkopen bewaard voor de dure kwartieren.

## [1.10.0]

* **Kalibratie (volladen naar 100 %)**: het BMS laadt de accu zelf vol als hij ongeveer een maand geen 100 % heeft
  gehaald, ook als de stroom dan duur is. Kies nu zelf het moment (Instellingen, kaart *Kalibratie*):
  *Wekelijks*, *Elke 2 weken* of *Elke 3 weken* op een gekozen dag, *Op datum*, of *Alleen na max. aantal dagen*.
  Op de kalibratiedag mag de set tot 100 % laden, en in de modus Prijsgestuurd plant de planner het netladen in de
  goedkoopste kwartieren tot middernacht (ook zonder winst). Daarboven ontlaadt de set die dag niet meer tot hij 100 %
  heeft bereikt. *Uiterlijk na* (standaard 28 dagen) werkt altijd als vangnet.
* Elke set apart: alleen de sets die aan de beurt zijn, gaan naar 100 %. Het aantal kwartieren volgt uit de set die
  het langst nodig heeft (met zijn eigen max laadvermogen), en in een kalibratiekwartier krijgen die sets voorrang bij
  het laden (attributen `kalibratie_nu` en `kalibratie_kwartieren` van de prijsactie).
* Per set wordt bijgehouden wanneer hij voor het laatst 100 % bereikte (`input_datetime.zendure_setN_laatst_vol`,
  zelf aan te passen, bijvoorbeeld met de datum uit Gielz) en hoeveel dagen dat geleden is
  (`sensor.zendure_setN_dagen_sinds_vol`). Op het Overzicht staat de kaart *Kalibratie (100 %)* met de status
  (Bezig / Volgende / Te laat).

## [1.9.11]

* Rustige energiestroom: de afbeelding gebruikt nu afgevlakte sensoren (`sensor.zendure_ems_weergave_net`, `_zon`,
  `_huis`, `_accu`, `_ev`), elke 5 s bijgewerkt met een glijdend gemiddelde (~15 s). Kleine waarden rond 0 tonen als 0,
  zodat de lijnen niet steeds aan/uit springen. De regeling werkt nog steeds op de snelle metingen.
* Voeg `sensor.zendure_ems_weergave_*` toe aan `entity_globs` in je recorder-exclude.

## [1.9.10]

* Herstel besparing: de grafieken *Besparing per dag* en *Opgebouwde besparing* gebruiken nu
  `sensor.zendure_ems_besparing_teller` (waarde ontladen − kosten laden, zonder startwaarde). Het invullen van de
  startwaarde gaf eerder een sprong van ruim € 1.000 (het nieuwe veld begon op −1.000). *Totaal* toont nog steeds de
  besparing inclusief startwaarde, maar heeft geen statistiek meer. Bij een update vanaf vóór 1.9.2 wordt de
  startwaarde eerst op 0 gezet.
* Opruimen (eenmalig): Ontwikkelaarshulpmiddelen → Statistieken → bij `sensor.zendure_ems_besparing_totaal` de
  melding oplossen met *Verwijderen*.

## [1.9.9]

* **Indeling van het Overzicht in drie kolommen**: links energiestroom en modus/status/profiel; in het midden
  laadtoestand per set, sets en de planner; rechts laadtoestand (24 uur), vermogen en EV laden.
* **Compactere planner**: *kWh* staat in de kolomkop, kortere prijsbalk; vandaag en morgen als aparte kaarten
  (voor morgen staat een melding tot de prijzen er zijn, meestal rond 13:00).

## [1.9.8]

* Herstel: de planner op het Overzicht gebruikt nu echt de volle breedte van twee kolommen (de kaart kreeg in
  1.9.7 maar de helft van de brede sectie).
* Een set die (nog) niet is aangesloten, krijgt op het Overzicht geen meter en geen kaart meer met
  "Entiteit is momenteel niet beschikbaar"; ze verschijnen vanzelf zodra de set gegevens levert.

## [1.9.7]

* **Nieuwe indeling van het Overzicht** (4 kolommen op een breed scherm): links de energiestroom met daaronder modus,
  status en profiel; in het midden de laadtoestand per set met daaronder de sets; rechts de planner, twee kolommen
  breed. Daaronder vermogen, EV laden en laadtoestand (24 uur). Op een smaller scherm schuift alles in dezelfde
  volgorde onder elkaar.

## [1.9.6]

* De **dagplanning** op het tabblad *Statistieken* is twee kolommen breed, net als de planner op het Overzicht.

## [1.9.5]

* Dagplanning (Statistieken) en planner (Overzicht): een kwartier waarin de zon ongeveer precies het verbruik dekt,
  heet nu **☀️ Zon dekt verbruik** in plaats van *Rust*. *Rust* blijft alleen over voor kwartieren zonder zon en
  (bijna) zonder verbruik.
* **Tabblad Statistieken inklapbaar**: tik op de kop van een blok om het te openen of te sluiten (standaard open).
* **Planner twee kolommen breed**: het Overzicht gebruikt nu de sectie-indeling van Home Assistant, zodat de planner
  per kwartier over twee kolommen loopt en de tabel niet meer afbreekt. Op een telefoon is alles één kolom.

## [1.9.4]

* **Planner per kwartier in een nieuwe opmaak**: bovenaan wat de regeling nu doet en de totalen; daaronder per dag
  een tabel met de prijs in kleur (groen/oranje/rood) en een balk, ⬇ goedkoopste en ⬆ duurste uur, het plan met
  pictogrammen en de laadtoestand met een batterijpictogram. Het huidige uur staat vet met ◀.
* **Inklapbare onderdelen op het Overzicht** (standaard open): laadtoestand per set, vermogen, planner, EV laden,
  sets en laadtoestand (24 uur). Energiestroom en modus blijven altijd zichtbaar.

## [1.9.3]

* **Inklapbare onderdelen** op het tabblad *Instellingen*: tik op de kop van een onderdeel om het te openen of te
  sluiten. Alleen standaardkaarten (tegel + voorwaardelijke kaart); de stand wordt onthouden in
  `input_boolean.zendure_ems_toon_…`. Bij de eerste keer staat alles ingeklapt.

## [1.9.2]

* **Besparing door de accu** (tabblad *Statistieken*): kosten laden en waarde ontladen van alle sets samen,
  gewogen met de prijs van dat moment. Laden uit het net = afnameprijs, laden met zonne-overschot =
  terugleverprijs; leveren aan het huis = afnameprijs, verkopen aan het net = terugleverprijs (t/m 2026 gelijk).
  Vandaag, deze maand, totaal, gemiddelde laadprijs/ontlaadwaarde, staafgrafiek per dag en opgebouwde besparing.
  Met *Besparing startwaarde* neem je de stand van je batterij planner mee.

## [1.9.1]

* **Standby na inactiviteit** (zoals Gielz' *Standby Vertraging*): staat een set langer dan 5 minuten op 0 W, dan
  krijgt hij eenmalig `smartMode: 0` met beide limieten op 0 en gaat hij helemaal in standby. De smartMode-bewaking
  laat die set dan met rust; zodra de regeling weer vermogen vraagt, gaat hij met `smartMode: 1` weer aan.
  Instelbaar op de kaart *Regeling (geavanceerd)* → *Standby na inactiviteit* (0 = uit). Nieuwe sensoren
  *Zendure setN inactief*.
* **Startprofiel met historie van je vorige aansturing**: kaart *Planner* → *Historie laadvermogen/ontlaadvermogen
  accu*. Voor Gielz: `sensor.zendure_2400_ac_vermogen_import` en `sensor.zendure_2400_ac_vermogen_export`. Daarna
  *Startprofiel uit historie opbouwen*. Zonder deze sensoren rekent het profiel op uren waarin de oude aansturing de
  accu liet leveren met (bijna) 0 W verbruik, en toont de dagplanning daar *Rust*.
* Energiestroom: grotere, beter leesbare bijschriften.

## [1.9.0]

* **Profielen** (Overzicht): kies *Nul op de meter*, *Dynamisch NOM*, *Dynamisch NOM (Duur)*, *Dynamisch Handelen*, *Dynamisch Handelen + NOM*
  of *Stand-by* en alle prijsinstellingen worden in één keer gezet (namen zoals bij Gielz). Met de knoppen
  *Opslaan als mijn profiel 1/2* bewaar je je eigen instellingen (inclusief minimale winst, slijtage en afschalen)
  en zet je ze later met één keuze terug. Sensor *Actief profiel* laat zien welk profiel geldt, of *Aangepast*.

## [1.8.2]

* De kwartierplanning (attribuut *komende*) staat in een eigen sensor: `sensor.zendure_ems_planning`. Die gaat
  uit de database (recorder-exclude); `sensor.zendure_ems_stroomprijs` blijft bewaard, zodat de prijsgrafieken op
  het tabblad Statistieken historie hebben. **Pas je recorder-exclude aan** als daar de stroomprijs in stond.

## [1.8.1]

* **Accucapaciteit per set** (kaart *Grenzen set N*): vul de totale capaciteit in als die afwijkt van
  aantal packs × capaciteit per pack, bv. een 2400 AC+ met 2,4 kWh ingebouwd + 4 × 2,88 kWh = **13,92 kWh**.
  0 = automatisch (zoals voorheen). Gebruikt voor opgeslagen energie, gemiddelde SOC, reserve en planner.
* **Versienummer in het dashboard**: in de titel, op het Overzicht (*Versie package*) en bovenaan Instellingen,
  met een waarschuwing als package en dashboard verschillen.

## [1.8.0]

* **Reserve per set** (kaart *Grenzen set N*, veld *Reserve boven min SOC*, standaard 0 kWh): Zendure EMS
  ontlaadt een set niet onder minimale SOC + reserve. In de set zelf blijft de gewone minimale SOC staan, zodat
  de reserve in een noodgeval (off-grid-stopcontact) bruikbaar is. Zakt een set onder de reserve, dan laadt de
  planner (Prijsgestuurd) het tekort bij in het goedkoopste kwartier van de komende 12 uur, ook zonder winst.
* **Nieuwe energiestroom-afbeelding**: moderne woning in isometrische weergave (platte daken, zonnepanelen,
  gevelbekleding, netaansluitkast, accu's aan de gevel, auto aan de laadkabel). Alleen het dashboard opnieuw plakken.

## [1.7.1]

Bevat alle aanpassingen uit de lokale versie 1.7.0-ram, plus:

* **Flashgeheugen sparen**: limieten gaan met `smartMode: 1` naar het RAM. De laad/ontlaadstand (`acMode`)
  gaat alleen mee als een set echt van richting wisselt; stoppen (0 W) zet alleen de limiet van de huidige
  richting op 0, zonder standwissel. Direct na een opdracht wordt de stand niet nog eens verstuurd, ook niet
  als het rapport van de set nog de oude stand laat zien.
* Schakelaar *Limieten naar flash schrijven* (uit = RAM, aanbevolen), sensoren *Zendure setN smartMode* en
  automatisering *smartMode (RAM) bewaken*.
* **Tabblad Statistieken**: dagplanning, grafieken en geleerd verbruik. Vereist de HACS-kaart
  **ApexCharts Card**. Overzicht en Instellingen werken ook zonder.
* **Afbeeldingen in het dashboard zelf**: de map `/config/www/zendure_ems` is niet meer nodig. Verwijder
  hem nadat het nieuwe dashboard werkt. **Laat de map `www` zelf staan**: HACS bewaart daar zijn kaarten.

## [1.7.0]

* **Afschalen in stappen**: bij een negatieve prijs gaat de exportlimiet van de omvormer stap voor stap
  naar 0 (standaard 500 W per 10 s, instelbaar op de kaart *Zonnepanelen afschalen*) en daarna op dezelfde
  manier terug naar normaal. Een omvormer met eigen meter (zoals de GoodWe) levert met limiet 0 traploos
  precies het huisverbruik.
* **Bewaking**: zet een andere automatisering de exportlimiet of het extra apparaat terug terwijl er is
  afgeschaald, dan schaalt het package binnen een minuut opnieuw af (met melding in het logboek).

## [1.6.4]

* Energiestroom: de laadlijn naar de auto stopt bij de laadklep; AUTO staat onder de auto.
* Handleiding: dashboardinstallatie stap voor stap (paragraaf 4.2).

## [1.6.3]

* Verfijnde energiestroom-afbeelding: zachte schaduwen, dakpanelen met cellen, ramen met gloed, nieuwe auto
  en gloeiende stroomlijnen. Kopieer de map `www/zendure_ems` opnieuw en plak het dashboard opnieuw.

## [1.6.2]

* **Energiestroom-afbeelding** bovenaan het Overzicht: een huis met bewegende lijnen voor net
  (afname of teruglevering), zon, huisverbruik, accu's (laden of ontladen) en de auto, met de actuele
  waarden. Alleen standaardkaarten (picture-elements) en SVG-bestanden, geen HACS.
* (Vanaf 1.7.1 zitten de afbeeldingen in het dashboard zelf; kopiëren naar `/config/www` is niet meer nodig.)
* Nieuwe sensor *Netmeting* (`sensor.zendure_ems_netmeting`): de echte P1-waarde, inclusief de auto.

## [1.6.1]

* **Kaart EV laden op het Overzicht**: schakelaar *EV laden van het net* (zet je eigen laadschakelaar om),
  *Auto laadt*, laadvermogen, kWh, laadtijd en kosten van vandaag (kWh × huidige stroomprijs), en het
  netvermogen zoals de accu's het zien.

## [1.6.0]

* **EV laden van het net** (kaart *EV laden* op Instellingen), voor een granny-lader op een slimme stekker.
  Vul de vermogenssensor van de stekker in (bv. `sensor.energy_socket_vermogen`) en de schakelaar die je
  omzet als je gaat laden (bv. `input_boolean.ev_laden_actief`). Staat die aan, dan trekt het package het
  laadvermogen van de netmeting af: de sets ontladen niet voor de auto. Staat hij uit, dan is de auto
  gewoon verbruik en mogen de sets hem voeden.
* Gebruik als netmeter je **echte P1-sensor**, niet een eigen "P1 gecorrigeerd": de hoofdzekering-bewaking
  blijft zo de echte afname zien.
* De auto telt nooit mee in het verbruiksprofiel (ook niet in *Startprofiel uit historie*).

## [1.5.0]

* **Aparte terugleverprijs per kwartier** (kaart *Teruglevering*). Tot en met 2026 gelijk aan de afnameprijs
  (salderen). Vanaf 1 januari 2027: kale marktprijs (uit een tweede prijssensor, bv.
  `sensor.nordpool_kwh_nl_eur_3_10_0`), eventueel met btw, een vaste vergoeding of terugleverkosten, en een
  bonus. Voor de **Zonneplan-zonnebonus**: btw aan, vaste vergoeding 0,02, bonus 10 %, alleen overdag aan.
  De bonus wordt alleen gegeven als marktprijs + vaste vergoeding positief is.
* **Afschalen en verkopen gebruiken de terugleverprijs.** In 2027 is de afnameprijs door de energiebelasting
  (€ 0,1065/kWh incl. btw) vaak nog positief terwijl terugleveren geld kost; daarom wordt op de
  terugleverprijs afgeschaald.
* De vermindering energiebelasting is een vast bedrag per jaar en speelt geen rol bij de beslissingen.
* De planner-tabel heeft een kolom *Terug* met de terugleverprijs.

## [1.4.0]

* **Zonnepanelen afschalen bij negatieve prijs** (kaart *Zonnepanelen afschalen*, staat standaard op *Uit*):
  * *Bij volle accu*: de sets laden eerst op vol vermogen van het net; zijn ze allemaal vol, dan gaat een
    limiter-schakelaar aan, de exportlimiet van de omvormer naar 0 (de omvormer levert alleen nog het
    huisverbruik) en een extra apparaat naar zijn afgeschaalde limiet. *Direct*: meteen bij een negatieve prijs.
  * Bij een positieve prijs (boven *Afschalen onder prijs*) gaat alles terug naar de normale waarden.
  * Instelbaar: exportlimiet-entiteit (bv. `number.goodwe_net_exportlimiet`, normaal 3000 / afgeschaald 0),
    limiter-schakelaar (bv. `input_boolean.goodwe_net_limiter_inschakelen`) en extra apparaat
    (bv. `number.solarflow_800_output_limit`, normaal 800 / afgeschaald 0).
* Bij een negatieve prijs met volle sets wordt de accu vastgehouden in plaats van ontladen.
* **Zet je eigen automatisering voor negatieve prijzen uit**, en alles wat de 2400 via een eigen
  keuzelijst aanstuurt: Zendure EMS stuurt de sets zelf aan.

## [1.3.0]

* **Aparte verbruiksprofielen voor werkdagen en weekend** (elk 96 kwartieren). Je huidige profiel wordt
  bij de update voor beide overgenomen.
* **Lerende zonnecorrectie** (*Zonnecorrectie leren*, standaard aan): om 00:10 wordt de verwachting voor
  de hele dag onthouden, om 23:50 vergeleken met de gemeten opbrengst. De correctie schuift 20 % richting
  gemeten ÷ verwacht en wordt na 3 dagen door de planner gebruikt. Vereist een productiemeting
  (*Zonneproductie-sensor* of zonnepanelen op de sets).
* **Startprofiel uit historie** (knop op het dashboard, script `script.zendure_ems_startprofiel`): leest
  met `recorder.get_statistics` de uurgemiddelden van netmeter, accu's en zonneproductie (standaard 28
  dagen) en bouwt daaruit beide profielen. Gebruik dit pas als alle sets zijn aangesloten.

## [1.2.0]

* **Snellere, rustigere regeling**: reageert op elke nieuwe meterwaarde en wacht daarna tot de opdracht is
  uitgevoerd (nieuw: *Wachttijd na opdracht*). Standaard *Kp* is nu 0,7. In de simulatie is het net na een
  verandering gemiddeld in 7,9 s weer rond 0 W (was 24,5 s), met 46 % minder uitwisseling door naregelen.
* **Minimaal vermogen per set** (nieuw): geen inefficiënte mini-vermogens en geen aan-uit-gespring.
* **Slimmere planner**: kiest per tekort tussen eerder vasthouden en eerder laden, met een vast plan per
  kwartier. In de geteste scenario's 3–9 % lagere voorspelde kosten dan versie 1.1.
* **Slijtagekosten per kWh** (nieuw, standaard 0,03). *Minimale winst* gaat daarom standaard van 0,10 naar 0,05.
* **Bijwerken vanaf 1.1**: vervang het package-bestand en herstart. De nieuwe velden krijgen automatisch
  eenmalig hun standaardwaarde; je bestaande instellingen blijven ongewijzigd en je krijgt een melding.
  Zet daarna zelf *Kp* op 0,7 en *Minimale winst per kWh* op 0,05 als je de nieuwe standaarden wilt.
