# Een privégids combineren voor Nuvio

`private_guide.py` maakt per land één XMLTV-bestand voor de bestaande Live TV-gids van Nuvio of TiviMate. Publiceer het bestand via een privé bereikbaar adres op bijvoorbeeld TrueNAS en voeg de link in Nuvio onder **TV Guides (EPG)** toe. Voer het commando per land uit en voeg alleen de gewenste landen in Nuvio toe. Voor een volgende update mag hetzelfde uitvoerpad worden gebruikt.

## Polen en Nederland

```sh
python3 private_guide.py --region PL --output /private/epg/pl.xml.gz
python3 private_guide.py --region NL --output /private/epg/nl.xml.gz
```

| Selectie | Bron en dekking |
| --- | --- |
| `epgshare` | [EPGShare01](https://epgshare01.online/epgshare01/), beschikbaar voor alle landen in de addon |
| `epg-ovh` | [EPG.OVH](https://epg.ovh/), Poolse feed met categorieën |
| `iptv-epg` | [IPTV-EPG.org](https://iptv-epg.org/guides), NL, BE, DE, PL, UK en US |
| `epg-guru` | [EPG.Guru](https://epg.guru/), Poolse zevendaagse gids voor privégebruik |
| `open-epg` | [Open-EPG](https://www.open-epg.com/app/epgguide.php), extra Poolse gids die eenmaal per dag ververst |

Een commando zonder `--source` gebruikt alle bovenstaande presets voor het opgegeven land. Herhaal `--source` om de volgorde te bepalen. Meteen na je eigen provider voeg je met `--source regional` de beschikbare landpresets toe.

## Eigen provider en aanvullingen

Zet de volledige HTTPS-URL van de XMLTV-feed in een private omgevingsvariabele, bijvoorbeeld `PROVIDER_PL_EPG`. Een lokale `.xml` of `.xml.gz` is ook bruikbaar.

```sh
python3 private_guide.py --region PL --output /private/epg/pl.xml.gz \
  --source env=PROVIDER_PL_EPG --source regional --source file=/private/onet-guide.xml
```

Het [Onet-zenderbestand](https://github.com/iptv-org/epg/blob/master/sites/programtv.onet.pl/programtv.onet.pl.channels.xml) bevat zenderkoppelingen. [Het bijbehorende iptv-org-script](https://github.com/iptv-org/epg/tree/master/sites/programtv.onet.pl) genereert de gids met `npm run grab --- --sites=programtv.onet.pl` vanuit die repository, waar de bron bereikbaar is. Gebruik het gegenereerde `guide.xml` als invoer. [Ziggo](https://www.ziggo.nl/entertainment/tv-gids) en [KPN](https://tv.kpn.com/tv-gids) bieden online tv-gidsen. Voor beide is er in deze implementatie geen gevalideerde XMLTV-preset. Een XMLTV-export waar je toegang toe hebt kan via dezelfde `file=` of `env=` optie worden toegevoegd.

De eerste bron heeft voorrang voor zender-ID's, titels en tijden. Bronnen verderop voegen zenders toe, vullen gaten en vullen beschrijvingen en andere gegevens aan. Verschillende ID's worden alleen samengevoegd bij een unieke genormaliseerde zendernaam in beide feeds en minimaal twee verschillende programma's met gelijke begin- en eindtijd. Zenders die niet veilig aan elkaar gekoppeld kunnen worden, behouden elk hun eigen ID.

Na generatie toont de JSON-uitvoer per bron de status en het aantal toegevoegde programma's, verrijkte programma's en conflicten. `latest_programme_end` toont hoe ver de gids werkelijk vooruitloopt. Een onbeschikbare landpreset wordt overgeslagen. Als een opgegeven provider-URL of lokaal bestand faalt, blijft het vorige uitvoerbestand beschikbaar. De URL en de naam van de omgevingsvariabele verschijnen niet in het verslag.
