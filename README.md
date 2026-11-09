Installatie
Het pakket bevat één package (packages/zendure_ems.yaml) en één dashboard (dashboards/dashboard.yaml) voor 1, 2 of 3 sets. Je vult alleen de IP-adressen in van de sets die je hebt; een set zonder IP-adres wordt niet aangestuurd en niet getoond.
4.1 Package plaatsen
1.	Zet in configuration.yaml (als dat er nog niet staat) de regels hieronder.

homeassistant:
  packages: !include_dir_named packages
2.	Maak in de configuratiemap de map packages aan en kopieer zendure_ems.yaml erin. Had je een oudere versie met zendure_ems_2sets.yaml of zendure_ems_3sets.yaml, verwijder dat bestand dan; er mag maar één Zendure EMS-package in de map staan. Je instellingen blijven bewaard, want de namen van alle velden zijn gelijk.
3.	Voeg de recorder-uitzonderingen toe in configuration.yaml. Die houden de grote, snel veranderende sensoren uit de database. Bijlage C beschrijft stap voor stap hoe.
4.	Ga naar Ontwikkelaarshulpmiddelen → YAML → Configuratie controleren. Zie je geen fouten, herstart dan Home Assistant.
5.	Na de herstart zet het package alle instellingen eenmalig op hun standaardwaarde. De modus staat op Niet aansturen; er gebeurt nog niets.

4.2 Dashboard installeren
Het dashboard is één tekstbestand dat je in Home Assistant plakt: dashboards/dashboard.yaml. De afbeeldingen van de Energiestroom-kaart zitten in dat bestand zelf; je hoeft geen map of bestanden te kopiëren. Het dashboard heeft drie tabbladen: Overzicht, Instellingen en Statistieken.
Stap A. ApexCharts installeren (alleen voor Statistieken)
De grafieken op het tabblad Statistieken gebruiken de kaart ApexCharts Card uit HACS. Overzicht en Instellingen gebruiken alleen standaardkaarten en werken ook zonder.
1.	Open HACS in de zijbalk en zoek ApexCharts Card.
2.	Klik op Downloaden en bevestig. Heb je hem al (staat er Gedownload bij), sla deze stap dan over.
3.	Ververs de browser met Ctrl+F5.
Stap B. Dashboard aanmaken
1.	Ga naar Instellingen → Dashboards en klik rechtsonder op + Dashboard toevoegen.
2.	Kies Nieuw dashboard vanaf nul en klik op Volgende.
3.	Vul in: Titel Zendure EMS, pictogram mdi:home-battery, en laat Weergeven in zijbalk aan staan. Klik op Aanmaken.
Heb je al een Zendure-dashboard (bijvoorbeeld EMS), sla deze stap dan over en gebruik dat.
Stap C. Dashboardtekst plakken
1.	Open op je computer het bestand dashboard.yaml met een teksteditor, zoals Kladblok of TextEdit. Selecteer alles (Ctrl+A) en kopieer het (Ctrl+C). Het bestand is groot (ongeveer 120 kB) omdat de afbeeldingen erin zitten; dat is normaal.
2.	Klik in de zijbalk van Home Assistant op het dashboard.
3.	Klik rechtsboven op het potlood (Dashboard bewerken). Vraagt Home Assistant of je de controle wilt overnemen, klik dan op Neem de controle over.
4.	Klik rechtsboven op de drie puntjes → Raw-configuratie-editor.
5.	Selecteer in de editor alle tekst (Ctrl+A), verwijder die en plak de gekopieerde tekst (Ctrl+V).
6.	Klik rechtsboven op Opslaan en sluit de editor met het kruisje. Klik op Klaar.
Stap D. Controleren
1.	Ververs de pagina met Ctrl+F5 (Mac: Cmd+Shift+R).
2.	Op het tabblad Overzicht staat bovenaan de Energiestroom met het huis. Zolang de velden nog niet zijn ingevuld, staan er waarden als 0 W of Niet beschikbaar; dat is normaal.
3.	Op het tabblad Statistieken staan de grafieken. Zie je daar Custom element doesn't exist: apexcharts-card, doe dan stap A.
4.	Op het tabblad Instellingen staan alle invoervelden (hoofdstuk 6). Ga verder met 4.3.
1, 2 of 3 sets.  Alles van set 2 en set 3 (meters, kaarten, grenzen, kalibratie en de accutorens in de Energiestroom) verschijnt pas als je het IP-adres van die set invult op het tabblad Instellingen. De IP-velden zelf zijn altijd zichtbaar. Een set zonder IP-adres vraagt Home Assistant zelf om een klein bestand, zodat er geen foutmeldingen in het logboek komen.

Oude afbeeldingenmap opruimen
Kom je van versie 1.6.2 tot en met 1.7.0, dan staan de afbeeldingen nog in /config/www/zendure_ems. Die map is niet meer nodig. Verwijder hem pas als het nieuwe dashboard werkt (stap D):
•	Samba share: open \\homeassistant.local\config\www, klik met rechts op de map zendure_ems → Verwijderen.
•	Studio Code Server of File editor: open de map www, klik met rechts op zendure_ems → Verwijderen (File editor: map selecteren en het prullenbakje).
Let op.  Verwijder alleen de map zendure_ems, niet de map www zelf. HACS bewaart daar zijn kaarten (www/community), ook ApexCharts Card voor het tabblad Statistieken.

Dashboard bijwerken bij een nieuwe versie
1.	Herhaal stap C: alles in de Raw-configuratie-editor vervangen door het nieuwe dashboard.
2.	Ververs met Ctrl+F5. Op de telefoon: app helemaal sluiten en opnieuw openen.
Eigen wijzigingen in dit dashboard worden bij het plakken overschreven. Zet eigen kaarten daarom op een ander dashboard.
4.3 Velden invullen
Vul op het tabblad Instellingen van het dashboard minimaal in: de IP-adressen van de sets, de netmeter-sensor en de capaciteit per accupack. Heb je een HomeWizard P1, vul dan ook het IP-adres van de P1 in. Voor prijssturing ook de prijssensor en de zonneverwachting. Hoofdstuk 6 beschrijft elk veld.
Tip.  Tot de IP-adressen zijn ingevuld, meldt het logboek elke 5 seconden dat de rapporten niet opgehaald kunnen worden. Dat verdwijnt vanzelf zodra de adressen kloppen.
4.4 Bijwerken vanaf een eerdere versie
1.	Vervang het package-bestand in packages/ door de nieuwe versie (dezelfde bestandsnaam houden) en werk het dashboard bij zoals beschreven aan het eind van 4.2 (dashboard plakken, Ctrl+F5).
2.	Controleer de configuratie en herstart Home Assistant.
3.	Nieuwe velden krijgen automatisch eenmalig hun standaardwaarde; je bestaande instellingen blijven ongewijzigd. Je krijgt hierover een melding in Home Assistant.
4.	Kom je van versie 1.1: wil je de nieuwe standaarden van versie 1.2.0, zet dan Kp op 0,7 en Minimale winst per kWh op 0,05.
5.	Kom je van versie 1.2 of eerder: het oude verbruiksprofiel wordt voor werkdag en weekend overgenomen en Zonnecorrectie leren wordt aangezet.
6.	Kom je van versie 1.4 of eerder: vul de kaart Teruglevering in (kale-prijssensor, btw, vaste vergoeding en bonus van je leverancier). Tot en met 2026 verandert er niets.
7.	Kom je van versie 1.5 of eerder en laad je de auto: vul de kaart EV laden in (vermogenssensor van de lader en je laadschakelaar). Gebruik als netmeter weer je echte P1-sensor, niet een eigen P1-gecorrigeerd-sensor.
8.	Kom je van versie 1.7.0 of eerder: installeer ApexCharts Card als je het tabblad Statistieken wilt gebruiken, en verwijder daarna de map /config/www/zendure_ems (4.2). Had je een eigen aangepaste versie (1.7.0-ram), dan zit alles daaruit nu in het package; je instellingen blijven behouden.
9.	Kom je van versie 1.6 of eerder: de exportlimiet gaat voortaan in stappen (500 W per 10 s). Controleer bij Exportlimiet normaal of die gelijk is aan wat je omvormer normaal heeft.
10.	Kom je van versie 1.3 of eerder: Afschalen staat op Uit. Vul de kaart Zonnepanelen afschalen in, kies Bij volle accu of Direct, en zet je eigen automatisering voor negatieve prijzen uit.
