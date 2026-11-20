# Nuvio EPG · TV-gids

Internationale gidsinformatie als gewone addon, plus compacte XMLTV-bestanden voor de bestaande Live TV-gids van NuvioPlusIPTV en TiviMate. **Geen videostreams, geen IPTV-login en geen eigen server nodig.**

## Addon installeren

Open in Nuvio **Addons → toevoegen via URL** en plak:

```text
https://raw.githubusercontent.com/Kevin2296/nuvio-epg-addon/epg-data/public/manifest.json
```

Je krijgt de zes compacte hoofdlandencatalogi (NL, BE, DE, PL, US, UK) met zendernamen en programmering. Extra landen blijven beschikbaar als XMLTV, zonder de TV-addon met tienduizenden individuele bestanden te belasten. Open een zender om de tijden te bekijken. De addon levert geen afspeellinks. De link is beschikbaar na de eerste geslaagde [workflow-uitvoering](https://github.com/Kevin2296/nuvio-epg-addon/actions/workflows/update-guide.yml).

## Je geïntegreerde Live TV-gids vullen

De addon schrijft niet in je privé-IPTV-instellingen. Voeg daarom in **Instellingen → Live TV → Setup → TV Guides (EPG) → Add EPG Source** ook deze link toe en ververs je gids:

```text
https://raw.githubusercontent.com/Kevin2296/nuvio-epg-addon/epg-data/public/epg/all.xml.gz
```

Nuvio gebruikt zijn bestaande kanaalmatching en handmatige **Change EPG**-toewijzing. Je playlist en provider-login blijven op je apparaat. Dezelfde link werkt als aanvullende XMLTV-bron in TiviMate. Wil je kleinere bestanden of een andere bronkeuze? Vervang `all.xml.gz` door `nl.xml.gz`, `be.xml.gz`, `de.xml.gz`, `pl.xml.gz`, `us.xml.gz` of `uk.xml.gz`. Het bestaande `all.xml.gz` blijft bewust de compacte combinatie van deze zes kernregio's.

Dit zijn bronregio's, geen garantie dat iedere zender uit dat land komt. `all.xml.gz` bevat niet automatisch alle aanvullende landen. Bij gelijke XMLTV-ID's kiest de gecombineerde publieke gids de eerste bruikbare bron in de volgorde NL, BE, DE, PL, US, UK. XXX voeg je zo nodig privé in Nuvio toe; er is geen aparte automatische XXX-bron en geen gegarandeerde classificatie van volwassen zenders in externe landengidsen.

## Wereldwijde XMLTV-uitbreiding (14-daags maximum)

Naast NL, BE, DE, PL, US en UK publiceert de generator afzonderlijke XMLTV-bestanden voor ruim veertig extra bronregio's, waaronder Frankrijk, Italië, Spanje, Portugal, Oostenrijk, Zwitserland, Scandinavië, Tsjechië, Slowakije, Hongarije, Roemenië, Turkije, Canada, Australië, Zuid-Amerika, India, Japan, Zuid-Korea, Singapore, Indonesië en Zuid-Afrika. Het aantal beschikbare landen wisselt wanneer een bron uitvalt.

Een extra land toevoegen in Nuvio of TiviMate:

```text
https://raw.githubusercontent.com/Kevin2296/nuvio-epg-addon/epg-data/public/epg/fr.xml.gz
```

Verander `fr` in `es`, `it`, `pt`, `at`, `ch`, `cz`, `sk`, `hu`, `ro`, `tr`, `se`, `no`, `dk`, `fi`, `ca`, `au`, `br`, `jp`, `kr`, `in` enzovoort. De betreffende URL werkt zodra er voor dat land een actuele gids is gepubliceerd. Bekijk [quality.json](https://raw.githubusercontent.com/Kevin2296/nuvio-epg-addon/epg-data/public/quality.json) voor de werkelijke actieve regio's en de laatste programmatijd per regio. Een regio zonder bruikbare programmering verschijnt niet in het rapport.

De gegenereerde gids bewaart `<desc>`, `<category>`, `<sub-title>` en bruikbare `<episode-num>`-informatie als de bron die heeft; wat ontbreekt wordt niet verzonnen. Nuvio's huidige XMLTV-parser ondersteunt deze velden al. Om meer dan de standaard periode te zien moet de instelling voor toekomstige gidsdagen in Nuvio voldoende hoog staan. De actuele werking op de Nokia Streaming Box moet nog worden getest.

Voor automatisch naamkoppelen publiceert de Nederlandse gids `SBS` als alternatieve `display-name` bij `SBS 6` **uitsluitend wanneer dat binnen de Nederlandse bron ondubbelzinnig is**. `SBS6 HD`, `NL | SBS 6 FHD` en `SBS 6` worden al grotendeels door Nuvio's naamnormalisatie opgevangen. Andere onduidelijke afkortingen worden niet stilzwijgend gekoppeld: kies bij twijfel handmatig **Change EPG**. Een algemeen fouttolerant scoringsmodel zou daarnaast een eigen wijziging in Nuvio vereisen.

Om de Nokia niet te overbelasten blijft de standaardgids op de oorspronkelijke zes regio's. Voeg alleen de extra regiobestanden toe die je gebruikt. Ook eventuele volwassenenzenders hebben alleen een gids waar de upstreambron voldoende gegevens voor heeft; er is geen afzonderlijke garantie voor XXX.

## Optioneel: gidsbronnen lokaal combineren (v1.2)

De publieke addon blijft volledig werken **zonder eigen server**. Wil je extra gidsen voor ontbrekende uitzendingen, dan kun je de generator **privé** op TrueNAS of een computer uitvoeren met een extra lokaal XMLTV-bestand. Dat bestand wordt nooit naar de GitHub Actions-workflow verstuurd.

```sh
python3 -m unittest -v test_addon test_fusion
python3 addon.py --output private-public --supplement NL=/private/extra-nl.xml.gz
```

De aanvullende bron moet een XMLTV- of XMLTV.gz-bestand zijn waar je rechtmatig toegang toe hebt. Je kunt meerdere `--supplement LAND=BESTAND`-argumenten opgeven, maar slechts één per land; gebruik de provider-EPG in Nuvio rechtstreeks als je al een Xtream-account hebt.

**Fusie is bewust voorzichtig:** dezelfde XMLTV-`id` én een overeenkomende zendernaam zijn vereist. Het bestaande programma wint bij tegenstrijdige titels of overlappende tijden. Bij een gelijke uitzending kan een ontbrekende beschrijving, genre, ondertitel of aflevering worden aangevuld. Een aanvullend programma mag alleen een werkelijk leeg tijdslot vullen. Het rapport `quality.json` bevat tellingen onder `supplemental_merges`.

Dit is geen automatische publieke TVgids.nl-, Ziggo- of KPN-scraper; openbare zichtbaarheid is niet automatisch toestemming voor herpublicatie. Ook worden onjuiste `tvg-id`-koppelingen niet door fuzzy gokken rechtgetrokken: die logica hoort bij de privéplaylist in Nuvio, met controle van land en bron.

De generator verwerkt bronregio's stapsgewijs en schrijft XMLTV in gedeelten naar gzip. Hierdoor hoeft hij niet alle bronbestanden of een volledige XMLTV-uitvoer tegelijk in het geheugen te houden. De Android-app ontvangt precies hetzelfde XMLTV-formaat als voorheen.

## Compatibiliteit

De geïnspecteerde NuvioPlusIPTV-versie kan TV-addon-catalogi lezen maar geeft `startTime`/`endTime` uit addon-video's nog niet door aan zijn IPTV-tijdlijn. Daarom is de XMLTV-instelling nodig voor die tijdlijn. De beschrijvingen bevatten ook de tijden, zodat je de programmering als addon-informatie kunt lezen. De daadwerkelijke bediening op jouw TV-box moet nog worden getest.

De generator levert daarnaast de [standaard Stremio EPG-velden](https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/epg.md) voor clients die deze ondersteunen. De aparte native Android-proef in [PRIVATE_EPG_HUB.patch](PRIVATE_EPG_HUB.patch) is **niet nodig** voor deze addon of de XMLTV-links. [PRIVATE_EPG_HUB.md](PRIVATE_EPG_HUB.md) beschrijft uitsluitend die eerdere proef. Er is geen nieuwe APK vereist voor XMLTV-import in de bestaande app.

## Updates en kwaliteit

GitHub Actions haalt de regionale openbare EPGShare01-bronnen op, test de generator en neemt maximaal 14 dagen programmering over. **Dit is een maximum, geen belofte van 14 dagen:** zodra de bron ophoudt, houdt de gids ook op; er worden geen programma's geschat. Updates worden iedere zes uur gepland, bij relevante broncodewijzigingen en handmatig via **Run workflow**. GitHub kan geplande taken vertragen of na langdurige inactiviteit uitschakelen; dit is geen beschikbaarheidsgarantie.

De branch `main` bevat broncode. Alleen de automatische datasnapshot op `epg-data` wordt vervangen. Er is geen GitHub Pages-instelling of backend nodig. De workflow gebruikt het tijdelijke, repositorygebonden `GITHUB_TOKEN` met alleen `contents: write`; er zijn geen persoonlijke tokens of repository-secrets nodig.

[quality.json](https://raw.githubusercontent.com/Kevin2296/nuvio-epg-addon/epg-data/public/quality.json) toont generatietijd, bronstatus, aantallen en ongeldige/overlappende programma's. Deze cijfers gaan over de openbare bronnen **bij genereren**, niet over hoeveel van jouw privékanalen gekoppeld zijn.

Bij een bronstoring probeert de generator de vorige openbare snapshot van die regio, uitsluitend als die nog toekomstige programma's bevat. Dat staat als fallback in het rapport. Bij een volledige storing blijft de eerder gepubliceerde branch behouden. Controleer de generatietijd als de gids verouderd lijkt. Een verlopen programma wordt niet gebruikt om een gat op te vullen.

De beschrijvingen tonen de vermelde bronregio-tijdzone; US gebruikt New York, niet alle Amerikaanse lokale tijdzones. De XMLTV- en EPG-velden hebben expliciete UTC-tijden voor omzetting door de client. Programmering is een gedateerde snapshot, geen live status.

## Privacy

- Geen eigen M3U, Xtream-login, Nextcloud-wachtwoord of persoonlijke zenderkeuze wordt verwerkt.
- De bronserver ziet het IP-adres van de GitHub-runner. Je app haalt gidsen en lokaal gegenereerde SVG-kaartjes bij GitHub op. GitHub kan daardoor je IP-adres en opgevraagde openbare zender-ID's zien.
- Alleen zendernamen, programmatitels, tijden en beschikbare tekstuele beschrijvingen, genres, ondertitels en veilige afleveringaanduidingen worden overgenomen. Verdachte URL's of inlog-/tokengegevens in beschrijvingen worden geweerd. Provider-extensies en externe logo-URL's worden niet doorgegeven.
- Foutmeldingen bevatten geen URL's of antwoordinhoud. XML-entiteiten en onbekende DTD's worden geweigerd; de gebruikelijke `xmltv.dtd`-verwijzing wordt genegeerd zonder extern ophalen.
- Zet geen privéfeeds, playlists of credentials in deze openbare repository. De generator accepteert bewust geen willekeurige download-URL's.

## Ontwikkelen

Python 3.11+, zonder extra pakketten. Linux gebruikt de aanwezige tijdzonedatabase. Ontbreekt die bijvoorbeeld op Windows, dan worden beschrijvingstijden duidelijk als UTC gelabeld.

```sh
python -m unittest -v test_addon
python addon.py --output public
```

De uitvoermap moet nieuw of leeg zijn. Tests dekken protocolvelden, paginering, daggrenzen, tijdzones, landen-ID's, dubbele XMLTV-ID's, onveilige XML, metadatafiltering en een volledige bronstoring.

Bronnen: [EPGShare01](https://epgshare01.online/epgshare01/). Beschikbaarheid, juistheid en rechten op externe gidsgegevens hangen af van de bron; de softwarelicentie verleent geen rechten op die data.

Geen officiële Nuvio- of Stremio-uitgave. Broncode: GPL-3.0, zie [LICENSE](LICENSE). De native patch bouwt voort op [NuvioPlusIPTV](https://github.com/homelessbrian/NuvioPlusIPTV).
