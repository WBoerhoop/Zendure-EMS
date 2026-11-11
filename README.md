# Zendure EMS

Energiebeheer voor thuisbatterijen in Home Assistant. Zendure EMS stuurt 1, 2 of 3
Zendure SolarFlow-sets (2400 AC+ / 2400 AC Pro) rechtstreeks aan via de lokale API.
Volledig in YAML: geen Python, geen HACS en geen extra kaarten nodig.

## Functionaliteit
- **Nul op de meter**: laadt van zonne-overschot en ontlaadt voor eigen verbruik, zodat het net rond 0 W blijft.
- **Prijsgestuurd laden en verkopen**: een planner per kwartier op basis van dynamische prijzen
  (Nordpool, Zonneplan, ENTSO-e), zonneverwachting en een geleerd verbruiksprofiel. Houdt rekening
  met rendement en slijtage.
- **Profielen**: met één keuze naar Nul op de meter, Dynamisch NOM, Dynamisch Handelen,
  Alleen slim opladen/ontladen of Stand-by, of je eigen profiel.
- **Meerdere sets**: slimme verdeling over de sets op SOC en gemeten rendement, met een eigen modus per set.
  Minimale looptijden zorgen voor zo min mogelijk relaisschakelingen.
- **Snelle regeling**: leest een HomeWizard P1 elke seconde uit, met automatische wachttijd op basis van het meterinterval.
- **Kalibratie**: plant het volladen naar 100 % zelf in de goedkoopste kwartieren.
- **Extra's**: afschalen van zonnepanelen bij een negatieve prijs, EV-laden van het net en een reserve per set.
  Spaart het flashgeheugen door limieten naar het RAM te schrijven.
- **Dashboard**: een geanimeerde energiestroom (dag/nacht), planner, statistieken en de besparing door de accu.

## Vereisten
Home Assistant 2025.1+, SolarFlow-sets lokaal bereikbaar met een vast IP-adres, HEMS uit in de Zendure-app
en een netmeter-sensor (bijv. HomeWizard P1).
