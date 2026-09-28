// Deutsch - Katalog der Oberflaeche.
//
// Schluessel ist der englische Quelltext (siehe lib/i18n.svelte.ts).
// Ein fehlender Eintrag faellt auf Englisch zurueck.

import type { Dict } from "../i18n.svelte";

const dict: Dict = {
  "(exit {code})":
    "(Exit {code})",
  "<b>JIT</b> is needed by Java and emulator apps (Minecraft launchers, for example): ModStaller starts the app with a debugger attached and releases memory as soon as it asks for it.":
    "<b>JIT</b> brauchen Java- und Emulator-Apps (z. B. Minecraft-Launcher): ModStaller startet die App mit angehängtem Debugger und gibt Speicher frei, sobald sie danach fragt.",
  "Account":
    "Konto",
  "Action":
    "Aktion",
  "Active":
    "Aktiv",
  "Active account ({account})":
    "Aktiver Account ({account})",
  "Add account":
    "Account hinzufügen",
  "Add an Apple account":
    "Apple-Account hinzufügen",
  "After the running task.":
    "Nach dem laufenden Vorgang.",
  "Again":
    "Erneut",
  "All":
    "Alles",
  "All areas":
    "Alle Bereiche",
  "All {max} app slots of the free profile are taken – iOS will refuse a further app. Remove one first:":
    "Alle {max} App-Slots des Free-Profils sind belegt – iOS lehnt eine weitere App ab. Erst eine entfernen:",
  "Also delete sign-ins, settings and logs":
    "Auch Anmeldungen, Einstellungen und Protokolle löschen",
  "Also discard the device identity (Apple will then ask for a two-factor code again)":
    "Auch die Geräte-Identität verwerfen (Apple fragt dann wieder nach einem 2FA-Code)",
  "An installed app belongs to it – from ModStaller or from another tool. After deleting, it can no longer be renewed.":
    "Dazu gehört eine installierte App – von ModStaller oder von einem anderen Werkzeug. Nach dem Löschen lässt sie sich nicht mehr erneuern.",
  "An instance has to be started inside the app while it waits – only then does it ask for memory.":
    "Im Programm muss während des Wartens eine Instanz gestartet werden – erst dann fragt es nach Speicher.",
  "An ordinary, free Apple ID is enough. Apple then asks for a code on your iPhone.":
    "Eine normale, kostenlose Apple ID reicht. Danach fragt Apple einen Code auf deinem iPhone ab.",
  "Another operation is already running.":
    "Es läuft bereits ein Vorgang.",
  "Any image; it is cropped to a square.":
    "Beliebiges Bild, es wird quadratisch zugeschnitten.",
  "App ID deleted.":
    "App-ID gelöscht.",
  "App IDs in the account":
    "App-IDs im Konto",
  "App IDs this week":
    "App-IDs diese Woche",
  "App extensions were removed to save App IDs.":
    "App-Extensions wurden entfernt, um App-IDs zu sparen.",
  "App icon":
    "App-Icon",
  "Apple account":
    "Apple-Konto",
  "Apple allows only a few at a time. A foreign one (from AltStore or SideStore, say) cannot be used by ModStaller – its private key lives with the tool that requested it.":
    "Apple erlaubt nur wenige gleichzeitig. Ein fremdes (z. B. von AltStore oder SideStore) kann ModStaller nicht mitbenutzen – der private Schlüssel liegt beim anfordernden Werkzeug.",
  "Apple counts App IDs created in the last 7 days – deleting one does not give it back.":
    "Apple zählt die in den letzten 7 Tagen angelegten App-IDs – Löschen gibt keine zurück.",
  "Apple device service is not running":
    "Apple-Gerätedienst läuft nicht",
  "Apple device service missing":
    "Apple-Gerätedienst fehlt",
  "Apple sent a six-digit code to your iPhone.":
    "Apple hat einen sechsstelligen Code an dein iPhone geschickt.",
  "Applies to the whole program, including the messages that come from the background service.":
    "Gilt für das ganze Programm, auch für die Meldungen aus dem Hintergrunddienst.",
  "Applies to this launch only – unlock again after quitting the app.":
    "Gilt nur für diesen Start – nach dem Beenden der App erneut freischalten.",
  "Apps":
    "Apps",
  "Apps on the iPhone (free profile)":
    "Apps auf dem iPhone (Free-Profil)",
  "Asking Apple – this takes a few seconds …":
    "Bei Apple nachfragen – das dauert ein paar Sekunden …",
  "Automatic updates exist only in the AppImage and in the Windows version installed with the setup.":
    "Automatische Updates gibt es nur in der AppImage bzw. der mit dem Setup installierten Windows-Version.",
  "Back":
    "Zurück",
  "Backend not reachable":
    "Backend nicht erreichbar",
  "Battery {level} %":
    "Akku {level} %",
  "Beta channel":
    "Beta-Kanal",
  "Beta versions bring new features earlier, but they can be unstable and contain bugs.":
    "Beta-Versionen bringen neue Funktionen früher, können aber instabil sein und Fehler enthalten.",
  "Beta – may be unstable":
    "Beta – kann instabil sein",
  "Bundle ID":
    "Bundle-ID",
  "Bundle ID {id} · transport: {transport}":
    "Bundle-ID {id} · Transport: {transport}",
  "Cancel":
    "Abbrechen",
  "Cancelled":
    "Abgebrochen",
  "Cancelled.":
    "Abgebrochen.",
  "Cannot be kept – its ID does not belong to the app.":
    "Kann nicht behalten werden – ihre ID gehört nicht zur App.",
  "Certificate revoked.":
    "Zertifikat widerrufen.",
  "Change icon":
    "Icon ändern",
  "Charging … {level} %":
    "Lädt … {level} %",
  "Check again":
    "Erneut prüfen",
  "Check for updates":
    "Nach Updates suchen",
  "Checking the App ID quota …":
    "Prüfe das App-ID-Kontingent …",
  "Checking …":
    "Wird geprüft …",
  "Choose a file":
    "Datei auswählen",
  "Choose image …":
    "Bild wählen …",
  "Close":
    "Schließen",
  "Confirm":
    "Bestätigen",
  "Confirmation code":
    "Bestätigungscode",
  "Connected but not ready":
    "Angesteckt, aber nicht bereit",
  "Connected but not ready – unlock the iPhone and confirm “Trust”.":
    "Angesteckt, aber nicht bereit – iPhone entsperren und „Vertrauen“ bestätigen.",
  "Copy":
    "Kopieren",
  "Copying is not possible.":
    "Kopieren nicht möglich.",
  "Create a desktop shortcut":
    "Verknüpfung auf dem Schreibtisch anlegen",
  "Customize":
    "Anpassen",
  "Data in":
    "Daten unter",
  "Delete":
    "Löschen",
  "Delete App ID":
    "App-ID löschen",
  "Delete App ID?":
    "App-ID löschen?",
  "Developer Mode is off.":
    "Entwicklermodus ist aus.",
  "Developer Mode off":
    "Entwicklermodus aus",
  "Developer Mode on":
    "Entwicklermodus an",
  "Developer-signed":
    "Entwickler-signiert",
  "Development certificates":
    "Development-Zertifikate",
  "Device":
    "Gerät",
  "Different IPA":
    "Andere IPA",
  "Done":
    "Fertig",
  "Download":
    "Herunterladen",
  "Drag an IPA here":
    "IPA hierher ziehen",
  "Drag an IPA into the window or pick one from your Downloads.":
    "Zieh eine IPA ins Fenster oder wähle eine aus deinen Downloads.",
  "Each kept extension needs an App ID of its own.":
    "Jede behaltene Erweiterung braucht eine eigene App-ID.",
  "Enable JIT":
    "JIT freischalten",
  "Errors":
    "Fehler",
  "Every app signed with it will no longer start – including those of other sideloading tools.":
    "Alle Apps, die damit signiert wurden, starten danach nicht mehr – auch die anderer Sideload-Werkzeuge.",
  "Everything ready for sideloading.":
    "Alles bereit fürs Sideloading.",
  "Everything ready.":
    "Alles bereit.",
  "Explorer shows the iPhone but ModStaller doesn’t? Unplug it, unlock it and plug it back in – if that doesn’t help, restart the PC.":
    "Der Explorer zeigt das iPhone, ModStaller aber nicht? Abstecken, entsperren und wieder einstecken – hilft das nicht, den PC neu starten.",
  "Extension":
    "Erweiterung",
  "Extensions":
    "Erweiterungen",
  "Failed":
    "Fehlgeschlagen",
  "Files":
    "Dateien",
  "Filter":
    "Filtern",
  "Fix":
    "Beheben",
  "Follow live again":
    "Wieder live folgen",
  "Found in your folders":
    "In deinen Ordnern gefunden",
  "Free":
    "Kostenlos",
  "Free again: {dates}":
    "Wieder frei: {dates}",
  "From other tools":
    "Von anderen Werkzeugen",
  "Full log:":
    "Vollständiges Protokoll:",
  "Go to device":
    "Zum Gerät",
  "Hello, {name}!":
    "Hallo, {name}!",
  "How ModStaller behaves on this computer.":
    "Wie sich ModStaller auf diesem Rechner verhält.",
  "In the background":
    "Im Hintergrund",
  "Install":
    "Installieren",
  "Install app":
    "App installieren",
  "Install {name}":
    "{name} installieren",
  "Installing ModStaller…":
    "ModStaller wird installiert…",
  "Is everything here that ModStaller needs?":
    "Ist alles da, was ModStaller braucht?",
  "It becomes the active account for new installs. Apps keep renewing with the account that installed them.":
    "Er wird zum aktiven Account für neue Installationen. Apps werden weiter mit dem Account erneuert, der sie installiert hat.",
  "It is installed but stopped. Windows asks for confirmation once when it is started.":
    "Er ist installiert, aber gestoppt. Beim Starten fragt Windows einmal nach.",
  "JIT for {name}":
    "JIT für {name}",
  "Keyboard":
    "Tastatur",
  "Language":
    "Sprache",
  "Leave out all extensions":
    "Alle Erweiterungen weglassen",
  "Leaving the beta channel keeps the installed beta until a newer stable version is out.":
    "Wer den Beta-Kanal verlässt, behält die installierte Beta, bis eine neuere stabile Version erscheint.",
  "Live":
    "Live",
  "Log":
    "Protokoll",
  "Log file":
    "Log-Datei",
  "Log file not found.":
    "Log-Datei nicht gefunden.",
  "Log in":
    "Protokoll unter",
  "Looking for updates …":
    "Suche nach Updates …",
  "Make active":
    "Als aktiv setzen",
  "Manage App IDs ({count})":
    "App-IDs verwalten ({count})",
  "Manage all":
    "Alle verwalten",
  "Microsoft Store":
    "Microsoft Store",
  "ModStaller Setup":
    "ModStaller-Setup",
  "ModStaller is starting …":
    "ModStaller startet …",
  "ModStaller was removed.":
    "ModStaller wurde entfernt.",
  "ModStaller {version} is already installed.":
    "ModStaller {version} ist bereits installiert.",
  "ModStaller {version} is installed.":
    "ModStaller {version} ist installiert.",
  "Must be unique at Apple. Empty: ModStaller picks one that fits your team.":
    "Muss bei Apple eindeutig sein. Leer: ModStaller wählt eine passende für dein Team.",
  "Name on the home screen":
    "Name auf dem Home-Bildschirm",
  "New icon – cropped to a square.":
    "Neues Icon – quadratisch zugeschnitten.",
  "New installs sign with the active account. Renewals always use the account that installed the app.":
    "Neue Installationen signiert der aktive Account. Erneuert wird immer mit dem Account, der die App installiert hat.",
  "No IPAs in Downloads, Documents or Desktop.":
    "Keine IPAs in Downloads, Dokumente oder Desktop.",
  "No app installed yet":
    "Noch keine App installiert",
  "No certificates in the account.":
    "Keine Zertifikate im Account.",
  "No entries for this filter.":
    "Keine Einträge für diesen Filter.",
  "No iPhone":
    "Kein iPhone",
  "No iPhone connected – plug it in via USB and unlock it.":
    "Kein iPhone verbunden – per USB anstecken und entsperren.",
  "No iPhone connected. Plug it in via USB and unlock it.":
    "Kein iPhone verbunden. Per USB anstecken und entsperren.",
  "No installed app belongs to this App ID right now.":
    "Zu dieser App-ID gehört gerade keine installierte App.",
  "No messages yet.":
    "Noch keine Meldungen.",
  "No new App ID needed – the ones this install uses already exist.":
    "Keine neue App-ID nötig – die benötigten gibt es schon.",
  "Not checked yet.":
    "Noch nicht geprüft.",
  "Not connected":
    "Nicht verbunden",
  "Not signed in":
    "Nicht angemeldet",
  "Not signed in with Apple.":
    "Nicht bei Apple angemeldet.",
  "Nothing found – everything on the iPhone comes from the store or from ModStaller.":
    "Nichts gefunden – alles auf dem iPhone kommt aus dem Store oder von ModStaller.",
  "Nothing has happened yet.":
    "Noch nichts passiert.",
  "Nothing has happened yet. As soon as you plug in an iPhone or install something, it shows up here.":
    "Noch nichts passiert. Sobald du ein iPhone ansteckst oder etwas installierst, erscheint es hier.",
  "Nothing installed through ModStaller yet.":
    "Noch nichts über ModStaller installiert.",
  "Nothing is due right now":
    "Gerade ist nichts fällig",
  "Nothing was due.":
    "Nichts war fällig.",
  "Notifications":
    "Mitteilungen",
  "One click fixes it – see above.":
    "Ein Klick behebt das – siehe oben.",
  "Only for your user – no administrator rights needed. Your sign-ins and settings stay where they are.":
    "Nur für deinen Benutzer – ohne Administratorrechte. Deine Anmeldungen und Einstellungen bleiben, wo sie sind.",
  "Optional – empty fields keep what the IPA says.":
    "Optional – leere Felder behalten, was im IPA steht.",
  "Original icon":
    "Original-Icon",
  "Overview":
    "Übersicht",
  "Paid":
    "Bezahlt",
  "Paid account – no weekly limit on App IDs and no limit on apps.":
    "Bezahlter Account – kein Wochenlimit für App-IDs und keine Begrenzung bei Apps.",
  "Password":
    "Passwort",
  "Pause":
    "Anhalten",
  "Paused":
    "Angehalten",
  "Photo editing":
    "Fotobearbeitung",
  "Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.":
    "IPA wählen – ModStaller signiert sie mit deinem Apple-Konto und spielt sie aufs iPhone.",
  "Plug it in via USB and unlock it.":
    "Per USB anstecken und entsperren.",
  "Preparing Anisette …":
    "Anisette vorbereiten …",
  "Program":
    "Programm",
  "Read again":
    "Neu lesen",
  "Reading the IPA …":
    "IPA wird gelesen …",
  "Receive beta versions":
    "Beta-Versionen erhalten",
  "Recent activity":
    "Letzte Aktivität",
  "Refresh":
    "Aktualisieren",
  "Registered devices":
    "Registrierte Geräte",
  "Remove":
    "Entfernen",
  "Remove from the iPhone":
    "Vom iPhone entfernen",
  "Remove {name}":
    "{name} entfernen",
  "Remove {name}?":
    "{name} entfernen?",
  "Removes the program, the start menu entry and the `modstaller` command.":
    "Entfernt das Programm, den Startmenü-Eintrag und den Befehl `modstaller`.",
  "Removing ModStaller…":
    "ModStaller wird entfernt…",
  "Renew":
    "Erneuern",
  "Renew before it expires, from the overview or under “Apps”.":
    "Vor Ablauf in der Übersicht oder unter „Apps“ erneuern.",
  "Renew due":
    "Fällige erneuern",
  "Renew due apps":
    "Fällige Apps erneuern",
  "Renew now":
    "Jetzt erneuern",
  "Renew {name}":
    "{name} erneuern",
  "Renewed {count} apps.":
    "{count} Apps erneuert.",
  "Repair":
    "Reparieren",
  "Restart":
    "Neu starten",
  "Reuse an unused App ID …":
    "Ungenutzte App-ID wiederverwenden …",
  "Revoke":
    "Widerrufen",
  "Revoke certificate?":
    "Zertifikat widerrufen?",
  "SRP-6a: Apple gets proof that you know the password – not the password itself.":
    "SRP-6a: Apple bekommt einen Beweis, dass du das Passwort kennst – nicht das Passwort selbst.",
  "Safari":
    "Safari",
  "Screen broadcast":
    "Bildschirmübertragung",
  "Search":
    "Suchen",
  "Set up automatically":
    "Automatisch einrichten",
  "Set up the Apple device service":
    "Apple-Gerätedienst einrichten",
  "Settings":
    "Einstellungen",
  "Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.":
    "Einstellungen › Datenschutz & Sicherheit › Entwicklermodus – sonst startet keine sideloadete App.",
  "Share":
    "Teilen",
  "Show teams and certificates":
    "Teams und Zertifikate anzeigen",
  "Sideloading for {platform}":
    "Sideloading für {platform}",
  "Sideloads on the iPhone that do not come from ModStaller – from AltStore or SideStore, for instance. Renewing is not possible: the original IPA and the private key live with the other tool.":
    "Sideloads auf dem iPhone, die nicht von ModStaller stammen – etwa von AltStore oder SideStore. Erneuern geht nicht: die Original-IPA und der private Schlüssel liegen beim anderen Werkzeug.",
  "Sign & install":
    "Signieren & installieren",
  "Sign in":
    "Anmelden",
  "Sign in once, then ModStaller signs by itself.":
    "Einmal anmelden, dann signiert ModStaller selbst.",
  "Sign in with Apple":
    "Bei Apple anmelden",
  "Sign out":
    "Abmelden",
  "Sign out?":
    "Abmelden?",
  "Sign with":
    "Signieren mit",
  "Signed by someone else":
    "Fremd signiert",
  "Signed by {account}":
    "Signiert von {account}",
  "Signed in":
    "Angemeldet",
  "Signed in.":
    "Angemeldet.",
  "Signed out.":
    "Abgemeldet.",
  "Signed-in accounts":
    "Angemeldete Accounts",
  "Siri & Shortcuts":
    "Siri & Kurzbefehle",
  "Source missing ({path}) – renewing is not possible.":
    "Quelle fehlt ({path}) – Erneuern nicht möglich.",
  "Stable channel":
    "Stabiler Kanal",
  "Stable versions are always offered. With the beta channel, pre-release versions (-beta.x) are offered as well.":
    "Stabile Versionen werden immer angeboten. Mit dem Beta-Kanal zusätzlich auch Vorabversionen (-beta.x).",
  "Start ModStaller":
    "ModStaller starten",
  "Start an instance inside the app now (a game, for example) – only then does it ask for memory. The unlock applies to this launch of the app only.":
    "Starte jetzt in der App eine Instanz (z. B. ein Spiel) – erst dann fragt sie nach Speicher. Die Freischaltung gilt nur für diesen Start der App.",
  "Start menu":
    "Startmenü",
  "Start service":
    "Dienst starten",
  "Starting …":
    "Wird gestartet …",
  "Still to do: {what}":
    "Noch zu tun: {what}",
  "System":
    "System",
  "System check":
    "Systemcheck",
  "System is ready – {count} step(s) still open.":
    "System ist bereit – noch {count} Schritt(e) offen.",
  "Teams and certificates of {account}":
    "Teams und Zertifikate von {account}",
  "Terminal":
    "Terminal",
  "That image cannot be read.":
    "Dieses Bild lässt sich nicht lesen.",
  "That is not an IPA file.":
    "Das ist keine IPA-Datei.",
  "The Apple Watch app is removed – it cannot be installed this way.":
    "Die Apple-Watch-App wird entfernt – sie lässt sich so nicht installieren.",
  "The ModStaller service in the background has stopped":
    "Der ModStaller-Dienst im Hintergrund wurde beendet",
  "The app and its data are deleted from the iPhone. It comes from another tool – ModStaller cannot restore it.":
    "Die App und ihre Daten werden vom iPhone gelöscht. Sie stammt von einem anderen Werkzeug – ModStaller kann sie nicht wiederherstellen.",
  "The app and its data are deleted from the iPhone. That frees one of the three slots.":
    "Die App und ihre Daten werden vom iPhone gelöscht. Das macht einen der drei Plätze frei.",
  "The app runs under the unused App ID {id}.":
    "Die App läuft unter der ungenutzten App-ID {id}.",
  "The backend did not report in.":
    "Das Backend hat sich nicht gemeldet.",
  "The backend has stopped.":
    "Das Backend wurde beendet.",
  "The bundle ID is not valid – letters, digits and hyphens, separated by dots.":
    "Die Bundle-ID ist ungültig – Buchstaben, Ziffern und Bindestriche, durch Punkte getrennt.",
  "The connected iPhone.":
    "Das angeschlossene iPhone.",
  "The iPhone is plugged in but locked or not paired.":
    "iPhone ist angesteckt, aber gesperrt oder nicht gekoppelt.",
  "The next one frees up around {date}.":
    "Die nächste wird etwa am {date} frei.",
  "The session is discarded. Installed apps keep running but can only be renewed after signing in again.":
    "Die Sitzung wird verworfen. Installierte Apps laufen weiter, lassen sich aber erst nach erneuter Anmeldung erneuern.",
  "There already is a different `modstaller` command in ~/.local/bin – it was left untouched.":
    "In ~/.local/bin gibt es schon einen anderen Befehl `modstaller` – er wurde nicht angetastet.",
  "This IPA is App Store encrypted (FairPlay) and cannot be re-signed.":
    "Diese IPA ist App-Store-verschlüsselt (FairPlay) und lässt sich nicht neu signieren.",
  "This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself.":
    "Das gibt kein Wochenkontingent zurück: Apple zählt neu angelegte App-IDs, nicht vorhandene. Ist das Fenster voll, weicht ModStaller von selbst auf eine freie App-ID aus.",
  "This install needs {cost} – {missing} more than are left.":
    "Diese Installation braucht {cost} – {missing} mehr, als noch frei sind.",
  "This install uses {cost} of them.":
    "Diese Installation verbraucht {cost} davon.",
  "To renew, unlock or remove, the iPhone has to be connected and unlocked.":
    "Zum Erneuern, Freischalten oder Entfernen muss das iPhone angesteckt und entsperrt sein.",
  "Translations that are missing fall back to English.":
    "Fehlende Übersetzungen fallen auf Englisch zurück.",
  "Try again":
    "Erneut versuchen",
  "Turn on":
    "Einschalten",
  "Undo":
    "Rückgängig",
  "Undo changes":
    "Änderungen verwerfen",
  "Uninstall":
    "Deinstallieren",
  "Uninstall now":
    "Jetzt deinstallieren",
  "Unlock the iPhone and confirm “Trust”.":
    "iPhone entsperren und „Vertrauen“ bestätigen.",
  "Unplug the iPhone and plug it in again.":
    "iPhone abstecken und wieder einstecken.",
  "Unused ones are reused automatically when the weekly quota is used up – or pick one yourself when installing.":
    "Ungenutzte werden automatisch wiederverwendet, wenn das Wochenkontingent aufgebraucht ist – oder du wählst beim Installieren selbst eine.",
  "Up to date – no newer version on GitHub.":
    "Aktuell – keine neuere Version auf GitHub.",
  "Update check failed: {message}":
    "Update-Prüfung fehlgeschlagen: {message}",
  "Update to {version}":
    "Auf {version} aktualisieren",
  "Updates":
    "Updates",
  "VPN / network":
    "VPN / Netzwerk",
  "Version {version} for Linux":
    "Version {version} für Linux",
  "Version {version} is available":
    "Version {version} ist da",
  "Version {version} is available – see bottom left.":
    "Version {version} ist verfügbar – siehe unten links.",
  "Version {version} is ready":
    "Version {version} ist bereit",
  "Version {version} · from iOS {ios}":
    "Version {version} · ab iOS {ios}",
  "View quotas and certificates":
    "Kontingente und Zertifikate ansehen",
  "Wait for the running task first":
    "Erst den laufenden Vorgang abwarten",
  "Warnings":
    "Warnungen",
  "What ModStaller does – live. The complete history is in the log file.":
    "Was ModStaller tut – live. Die komplette Historie steht in der Log-Datei.",
  "What ModStaller has installed. Free accounts: at most 3 apps, valid for 7 days each.":
    "Was ModStaller installiert hat. Kostenlose Konten: höchstens 3 Apps, je 7 Tage gültig.",
  "What's new?":
    "Was ist neu?",
  "Where ModStaller is installed":
    "Wohin ModStaller installiert wird",
  "Whether an app depends on it cannot be determined without a connected iPhone.":
    "Ob gerade eine App daran hängt, ist ohne angestecktes iPhone nicht feststellbar.",
  "Widget":
    "Widget",
  "Windows shows the iPhone in Explorer through its own photo driver – ModStaller needs Apple’s device service for USB. ModStaller can set it up for you: “Apple Devices” from the Microsoft Store, otherwise just Apple’s USB driver.":
    "Windows zeigt das iPhone im Explorer über seinen eigenen Fototreiber an – ModStaller braucht für USB aber Apples Gerätedienst. ModStaller kann ihn für dich einrichten: „Apple-Geräte“ aus dem Microsoft Store, sonst nur Apples USB-Treiber.",
  "Without a connected iPhone it cannot be said which App IDs are in use right now – apps of other tools depend on them too.":
    "Ohne angestecktes iPhone lässt sich nicht sagen, welche App-IDs gerade gebraucht werden – auch Apps anderer Werkzeuge hängen daran.",
  "You find it in the start menu. You can remove it again by running this setup once more.":
    "Du findest es im Startmenü. Entfernen kannst du es, indem du dieses Setup noch einmal startest.",
  "Your Apple account signs the apps. The password is never stored or transmitted.":
    "Dein Apple-Account signiert die Apps. Das Passwort wird nie gespeichert oder übertragen.",
  "Your apps":
    "Deine Apps",
  "Your sign-ins and settings were kept.":
    "Deine Anmeldungen und Einstellungen wurden behalten.",
  "and {count} more":
    "und {count} weitere",
  "expired":
    "abgelaufen",
  "expires {date}":
    "läuft ab {date}",
  "expires – {when}":
    "läuft ab – {when}",
  "extensions":
    "Extensions",
  "frameworks":
    "Frameworks",
  "free":
    "frei",
  "has expired":
    "ist abgelaufen",
  "iPhone, sign-in and what expires soon – at a glance.":
    "iPhone, Anmeldung und was demnächst abläuft – auf einen Blick.",
  "in use":
    "in Benutzung",
  "injected dylibs":
    "injizierte dylibs",
  "just now":
    "gerade eben",
  "off":
    "aus",
  "on":
    "an",
  "or":
    "oder",
  "yesterday":
    "gestern",
  "{account} now signs new installs.":
    "{account} signiert jetzt neue Installationen.",
  "{available} of {max} left":
    "noch {available} von {max} frei",
  "{count} accounts signed in":
    "{count} Accounts angemeldet",
  "{count} day left":
    "noch {count} Tag",
  "{count} days ago":
    "vor {count} Tagen",
  "{count} days left":
    "noch {count} Tage",
  "{count} entries copied.":
    "{count} Einträge kopiert.",
  "{count} free":
    "{count} frei",
  "{count} h ago":
    "vor {count} Std.",
  "{count} hour left":
    "noch {count} Stunde",
  "{count} hours left":
    "noch {count} Stunden",
  "{count} new":
    "{count} neue",
  "{count} new App ID(s) created.":
    "{count} neue App-ID(s) angelegt.",
  "{count} point(s) prevent sideloading.":
    "{count} Punkt(e) verhindern das Sideloading.",
  "{count} point(s) to clear up.":
    "{count} Punkt(e) zu klären.",
  "{minutes} min ago":
    "vor {minutes} Min.",
  "{name} is installed and runs for {days} days.":
    "{name} ist installiert und läuft {days} Tage.",
  "{name} was removed from the iPhone.":
    "{name} wurde vom iPhone entfernt.",
  "{name} was renewed – valid for {days} days again.":
    "{name} ist erneuert – wieder {days} Tage gültig.",
  "{percent}% transferred":
    "{percent}% übertragen",
  "{used} of {max} used":
    "{used} von {max} belegt",
  "~/.local/bin is not on your PATH yet – the `modstaller` command works in the terminal after logging in again.":
    "~/.local/bin ist noch nicht in deinem PATH – der Befehl `modstaller` funktioniert im Terminal nach einer erneuten Anmeldung.",
};

export default dict;
