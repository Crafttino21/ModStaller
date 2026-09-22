# ModStaller

Ein iOS-Sideloader fuer Linux. Nimmt eine IPA, signiert sie mit einem ueber
den eigenen Apple-Account bezogenen Development-Zertifikat und installiert sie
aufs iPhone - ohne Mac, ohne Jailbreak.

Getestet gegen: iPhone 16 Pro Max (iPhone17,2), iOS 27.0, CachyOS/Arch.

## Stand

| Meilenstein | Inhalt | Status |
|---|---|---|
| M0 | Geruest, `doctor`, Device-Verbindung | laeuft |
| M1 | Anisette + GSA-Login inkl. 2FA | laeuft |
| M2 | Zertifikat, App-ID, Provisioning-Profil | laeuft |
| M3 | Signieren und installieren | laeuft |
| M4 | `refresh`, `uninstall`, `certs` | gebaut, Refresh noch ungetestet |
| M5 | systemd-Timer fuer automatischen Refresh | offen |

Erster vollstaendiger Durchlauf am 23.09.2026: PojavLauncher 2.2 (17
injizierte dylibs, 4 Frameworks) signiert und auf iPhone 16 Pro Max unter
iOS 27.0 installiert. Transportweg: lockdown - der RSD-Tunnel wird auf
iOS 27 fuer die Installation also nicht gebraucht.

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -e .
paru -S zsign-bin
.venv/bin/modstaller doctor
```

## Benutzung

Ohne Argument startet die interaktive Oberflaeche - sie zeigt oben, ob das
iPhone haengt, ob du angemeldet bist und was demnaechst ablaeuft, und bietet
vorrangig an, was gerade dran ist:

```bash
modstaller
```

Fuer Skripte und den Refresh-Dienst bleiben die Unterkommandos:

```bash
modstaller login                  # einmalig, fragt Apple ID + 2FA-Code
modstaller account                # Team, Kontingente, angelegte App-IDs
modstaller device info            # iPhone, iOS-Version, Developer Mode

modstaller install app.ipa        # signieren und installieren
modstaller list                   # was laeuft, und wie lange noch
modstaller refresh                # vor dem 7-Tage-Ablauf erneuern
modstaller uninstall <bundle-id>  # App entfernen, macht einen Platz frei
modstaller certs                  # Zertifikate anzeigen/widerrufen
```

Bei einem Gratis-Account werden App-Extensions per Default entfernt: jede
kostet eine App-ID aus einem Kontingent von zehn pro Woche, und die App
selbst laeuft ohne sie. Mit `--keep-extensions` behaeltst du sie.

`refresh` nutzt die beim Installieren gemerkte Original-IPA und haelt die
Bundle-ID stabil - sonst waere die App fuer iOS eine andere und die
gespeicherten Daten weg.

## Zwei Fallstricke, die hier geloest sind

**Apples 503-Nebelkerze.** Seit Ende August 2026 weist Apple jeden
GSA-Request an der Edge mit HTTP 503 ab, dessen `X-MMe-Client-Info` den
Identifier `com.apple.dt.Xcode` traegt - was die `anisette`-Bibliothek per
Default tut. Das sieht aus wie ein Apple-Ausfall und ist keiner. ModStaller
ersetzt den Identifier durch `com.apple.akd` und verweigert in
`apple/clientinfo.py` jeden Request, der das nicht tut. Empirisch geprueft:

    com.apple.dt.Xcode  ->  HTTP 503, 190 B  (an der Edge abgewiesen)
    com.apple.akd/1.0   ->  HTTP 404          (durchgekommen)

**Apples private CA.** `gsa.apple.com` wird nicht von einer oeffentlichen CA
signiert, sondern von "Apple Server Authentication CA". Mit dem System-Trust-
Store scheitert jede Verbindung. Die Kette liegt in
`modstaller/apple/certs/apple-gsa-ca.pem` - wir verifizieren dagegen, statt
die Pruefung abzuschalten.

**Ein Request pro Verbindung.** Apples Edge laesst an `GsService2` nur den
ersten Request einer TCP-Verbindung durch; jeder weitere bekommt HTTP 429.
Gemessen:

    Verbindung wiederverwendet:  404, 429, 429, 429, 429, 429
    Connection: close:           404, 404, 404, 404, 404, 429

Ein Login besteht aus zwei Requests (`init`, `complete`) - mit Keep-Alive
scheitert also *jeder* Login am zweiten, und es sieht aus wie eine Sperre des
Accounts. ModStaller erzwingt pro Request eine frische Verbindung. Der
verbleibende sporadische 429 ist ein Budget pro IP-Adresse und wird begrenzt
wiederholt; das ist unbedenklich, weil die Edge vor dem Auth-Dienst abweist
und das SRP-Cookie dabei nicht verbraucht wird.

Diagnose und Messmethode stammen aus den Untersuchungen von SideStore
(Issue #1557) und OpenTagViewer (Issue #226); die Umsetzung hier ist eigener
Code.

## Grenzen kostenloser Apple-Accounts

Keine davon ist ein Fehler von ModStaller; sie kommen von Apple:

* **Profile laufen nach 7 Tagen ab.** Danach startet die App nicht mehr, bis
  `modstaller refresh` sie neu signiert.
* **Hoechstens 3 sideloadete Apps gleichzeitig** pro Geraet. Die vierte lehnt
  das iPhone ab; `modstaller uninstall <bundle-id>` macht Platz.
* **10 App-IDs pro Woche.** Gezaehlt werden *neu angelegte*, nicht die
  vorhandenen - eine zu loeschen gibt also kein Kontingent zurueck. Ist das
  Fenster voll, weicht ModStaller auf eine vorhandene, ungenutzte App-ID aus;
  die App laeuft dann unter deren Bundle-ID. App-IDs installierter Apps und
  ihrer Extensions bleiben dabei unangetastet. Jede Extension braucht eine
  eigene App-ID, deshalb werden sie bei kostenlosen Accounts per Default
  entfernt.
* **Nur ein Development-Zertifikat.** Zwei Sideload-Werkzeuge parallel
  verdraengen sich zwangslaeufig gegenseitig, weil der private Schluessel
  jeweils beim anfordernden Werkzeug liegt.

Ob ein Account kostenlos ist, laesst sich Apple nicht direkt entlocken: es
meldet auch bezahlte Einzelaccounts als `Individual`. ModStaller nimmt im
Zweifel "kostenlos" an und korrigiert sich an der tatsaechlichen Laufzeit des
ersten Profils - 7 Tage heisst kostenlos, ein Jahr heisst bezahlt.

## Sicherheit

Das Apple-Passwort wird nie gespeichert und nie uebertragen: SRP-6a beweist
seine Kenntnis, ohne es zu senden. Alle Secrets liegen unter
`~/.local/share/modstaller/` mit 0600 in 0700-Verzeichnissen.
