# Nuvio EPG · TV-gids

Internationale gidsinformatie als gewone addon, plus compacte XMLTV-bestanden voor de bestaande Live TV-gids van NuvioPlusIPTV en TiviMate. **Geen videostreams, geen IPTV-login en geen eigen server nodig.**

## Addon installeren

Open in Nuvio **Addons → toevoegen via URL** en plak:

```text
https://raw.githubusercontent.com/Kevin2296/nuvio-epg-addon/epg-data/public/manifest.json
```

Je krijgt landencatalogi met zendernamen en programmering. Open een zender om de tijden te bekijken. De addon levert geen afspeellinks. De link is beschikbaar na de eerste geslaagde [workflow-uitvoering](https://github.com/Kevin2296/nuvio-epg-addon/actions/workflows/update-guide.yml).

## Je geïntegreerde Live TV-gids vullen

De addon schrijft niet in je privé-IPTV-instellingen. Voeg daarom in **Instellingen → Live TV → Setup → TV Guides (EPG) → Add EPG Source** ook deze link toe en ververs je gids:

```text
https://raw.githubusercontent.com/Kevin2296/nuvio-epg-addon/epg-data/public/epg/all.xml.gz
```

Nuvio gebruikt zijn bestaande kanaalmatching en handmatige **Change EPG**-toewijzing. Je playlist en provider-login blijven op je apparaat. Dezelfde link werkt als aanvullende XMLTV-bron in TiviMate. Wil je kleinere bestanden of een andere bronkeuze? Vervang `all.xml.gz` door `nl.xml.gz`, `be.xml.gz`, `de.xml.gz`, `pl.xml.gz`, `us.xml.gz` of `uk.xml.gz`.

Dit zijn bronregio's, geen garantie dat iedere zender uit dat land komt. Bij gelijke XMLTV-ID's kiest de gecombineerde gids de eerste bruikbare bron in de volgorde NL, BE, DE, PL, US, UK. XXX voeg je zo nodig privé in Nuvio toe; er is geen aparte automatische XXX-bron en geen gegarandeerde classificatie van volwassen zenders in externe landengidsen.

## Compatibiliteit

De geïnspecteerde NuvioPlusIPTV-versie kan TV-addon-catalogi lezen maar geeft `startTime`/`endTime` uit addon-video's nog niet door aan zijn IPTV-tijdlijn. Daarom is de XMLTV-instelling nodig voor die tijdlijn. De beschrijvingen bevatten ook de tijden, zodat je de programmering als addon-informatie kunt lezen. De daadwerkelijke bediening op jouw TV-box moet nog worden getest.

De generator levert daarnaast de [standaard Stremio EPG-velden](https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/epg.md) voor clients die deze ondersteunen. De aparte native Android-proef in [PRIVATE_EPG_HUB.patch](PRIVATE_EPG_HUB.patch) is **niet nodig** voor deze addon of de XMLTV-links. [PRIVATE_EPG_HUB.md](PRIVATE_EPG_HUB.md) beschrijft uitsluitend die eerdere proef. Er is geen nieuwe APK vereist voor XMLTV-import in de bestaande app.

## Updates en kwaliteit

GitHub Actions haalt de zes vaste openbare EPGShare01-bronnen op, test de generator en maakt maximaal 72 uur programmering. Updates worden iedere zes uur gepland, bij relevante broncodewijzigingen en handmatig via **Run workflow**. GitHub kan geplande taken vertragen of na langdurige inactiviteit uitschakelen; dit is geen beschikbaarheidsgarantie.

De branch `main` bevat broncode. Alleen de automatische datasnapshot op `epg-data` wordt vervangen. Er is geen GitHub Pages-instelling of backend nodig. De workflow gebruikt het tijdelijke, repositorygebonden `GITHUB_TOKEN` met alleen `contents: write`; er zijn geen persoonlijke tokens of repository-secrets nodig.

[quality.json](https://raw.githubusercontent.com/Kevin2296/nuvio-epg-addon/epg-data/public/quality.json) toont generatietijd, bronstatus, aantallen en ongeldige/overlappende programma's. Deze cijfers gaan over de openbare bronnen **bij genereren**, niet over hoeveel van jouw privékanalen gekoppeld zijn.

Bij een bronstoring probeert de generator de vorige openbare snapshot van die regio, uitsluitend als die nog toekomstige programma's bevat. Dat staat als fallback in het rapport. Bij een volledige storing blijft de eerder gepubliceerde branch behouden. Controleer de generatietijd als de gids verouderd lijkt. Een verlopen programma wordt niet gebruikt om een gat op te vullen.

De beschrijvingen tonen de vermelde bronregio-tijdzone; US gebruikt New York, niet alle Amerikaanse lokale tijdzones. De XMLTV- en EPG-velden hebben expliciete UTC-tijden voor omzetting door de client. Programmering is een gedateerde snapshot, geen live status.

## Privacy

- Geen eigen M3U, Xtream-login, Nextcloud-wachtwoord of persoonlijke zenderkeuze wordt verwerkt.
- De bronserver ziet het IP-adres van de GitHub-runner. Je app haalt gidsen en lokaal gegenereerde SVG-kaartjes bij GitHub op. GitHub kan daardoor je IP-adres en opgevraagde openbare zender-ID's zien.
- Alleen zendernamen, programmatitels en tijden worden overgenomen. Provider-extensies, externe logo-URL's en programmabeschrijvingen worden niet doorgegeven.
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
