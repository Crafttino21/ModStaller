# ModStaller

Ein iOS-Sideloader fuer Linux. Nimmt eine IPA, signiert sie mit einem ueber
den eigenen Apple-Account bezogenen Development-Zertifikat und installiert sie
aufs iPhone - ohne Mac, ohne Jailbreak.

Getestet gegen: iPhone 16 Pro Max (iPhone17,2), iOS 27.0, CachyOS/Arch.

## Stand

| Meilenstein | Inhalt | Status |
|---|---|---|
| M0 | Geruest, `doctor`, Device-Verbindung | steht |
| M1 | Anisette + GSA-Login | Transport bewiesen, Login ungetestet |
| M2 | Zertifikat, App-ID, Provisioning-Profil | offen |
| M3 | Signieren und installieren | offen |
| M4/M5 | Politur, Auto-Refresh-Daemon | offen |

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -e .
paru -S zsign-bin
.venv/bin/modstaller doctor
```

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

## Sicherheit

Das Apple-Passwort wird nie gespeichert und nie uebertragen: SRP-6a beweist
seine Kenntnis, ohne es zu senden. Alle Secrets liegen unter
`~/.local/share/modstaller/` mit 0600 in 0700-Verzeichnissen.
