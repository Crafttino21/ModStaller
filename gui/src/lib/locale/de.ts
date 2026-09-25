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
  "Again":
    "Erneut",
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
  "App ID deleted.":
    "App-ID gelöscht.",
  "App IDs in the account":
    "App-IDs im Konto",
  "App extensions were removed to save App IDs.":
    "App-Extensions wurden entfernt, um App-IDs zu sparen.",
  "Apple account":
    "Apple-Konto",
  "Apple allows only a few at a time. A foreign one (from AltStore or SideStore, say) cannot be used by ModStaller – its private key lives with the tool that requested it.":
    "Apple erlaubt nur wenige gleichzeitig. Ein fremdes (z. B. von AltStore oder SideStore) kann ModStaller nicht mitbenutzen – der private Schlüssel liegt beim anfordernden Werkzeug.",
  "Apple allows {max} <b>newly created</b> ones per week. Existing ones do not count – deleting therefore gives back no quota. When the window is full, ModStaller reuses a free one.":
    "Apple lässt {max} <b>neu angelegte</b> pro Woche zu. Vorhandene zählen nicht mit – Löschen gibt also kein Kontingent zurück. Ist das Fenster voll, nutzt ModStaller eine freie weiter.",
  "Apple sent a six-digit code to your iPhone.":
    "Apple hat einen sechsstelligen Code an dein iPhone geschickt.",
  "Applies to the whole program, including the messages that come from the background service.":
    "Gilt für das ganze Programm, auch für die Meldungen aus dem Hintergrunddienst.",
  "Applies to this launch only – unlock again after quitting the app.":
    "Gilt nur für diesen Start – nach dem Beenden der App erneut freischalten.",
  "Apps":
    "Apps",
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
  "Bundle ID {id} · transport: {transport}":
    "Bundle-ID {id} · Transport: {transport}",
  "Cancel":
    "Abbrechen",
  "Certificate revoked.":
    "Zertifikat widerrufen.",
  "Charging … {level} %":
    "Lädt … {level} %",
  "Check again":
    "Erneut prüfen",
  "Check for updates":
    "Nach Updates suchen",
  "Checking …":
    "Wird geprüft …",
  "Choose a file":
    "Datei auswählen",
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
  "Costs {count} App ID(s) from the weekly quota (10 per week on free accounts). The app itself runs without them.":
    "Kostet {count} App-ID(s) vom Wochenkontingent (10 pro Woche bei Gratis-Accounts). Die App selbst läuft auch ohne.",
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
  "Drag an IPA here":
    "IPA hierher ziehen",
  "Drag an IPA into the window or pick one from your Downloads.":
    "Zieh eine IPA ins Fenster oder wähle eine aus deinen Downloads.",
  "Enable JIT":
    "JIT freischalten",
  "Every app signed with it will no longer start – including those of other sideloading tools.":
    "Alle Apps, die damit signiert wurden, starten danach nicht mehr – auch die anderer Sideload-Werkzeuge.",
  "Everything ready for sideloading.":
    "Alles bereit fürs Sideloading.",
  "Everything ready.":
    "Alles bereit.",
  "Filter":
    "Filtern",
  "Fix":
    "Beheben",
  "Found in your folders":
    "In deinen Ordnern gefunden",
  "Free":
    "Kostenlos",
  "From other tools":
    "Von anderen Werkzeugen",
  "Full log:":
    "Vollständiges Protokoll:",
  "Go to device":
    "Zum Gerät",
  "How ModStaller behaves on this computer.":
    "Wie sich ModStaller auf diesem Rechner verhält.",
  "Install":
    "Installieren",
  "Install app":
    "App installieren",
  "Install {name}":
    "{name} installieren",
  "Is everything here that ModStaller needs?":
    "Ist alles da, was ModStaller braucht?",
  "JIT for {name}":
    "JIT für {name}",
  "Keep extensions":
    "Extensions behalten",
  "Language":
    "Sprache",
  "Log in":
    "Protokoll unter",
  "Looking for updates …":
    "Suche nach Updates …",
  "Manage App IDs ({count})":
    "App-IDs verwalten ({count})",
  "Manage all":
    "Alle verwalten",
  "ModStaller is starting …":
    "ModStaller startet …",
  "No IPAs in Downloads, Documents or Desktop.":
    "Keine IPAs in Downloads, Dokumente oder Desktop.",
  "No app installed yet":
    "Noch keine App installiert",
  "No certificates in the account.":
    "Keine Zertifikate im Account.",
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
  "Nothing installed through ModStaller yet.":
    "Noch nichts über ModStaller installiert.",
  "Nothing is due right now":
    "Gerade ist nichts fällig",
  "Nothing was due.":
    "Nichts war fällig.",
  "Overview":
    "Übersicht",
  "Paid":
    "Bezahlt",
  "Password":
    "Passwort",
  "Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.":
    "IPA wählen – ModStaller signiert sie mit deinem Apple-Konto und spielt sie aufs iPhone.",
  "Plug it in via USB and unlock it.":
    "Per USB anstecken und entsperren.",
  "Preparing Anisette …":
    "Anisette vorbereiten …",
  "Read again":
    "Neu lesen",
  "Reading the IPA …":
    "IPA wird gelesen …",
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
  "Restart":
    "Neu starten",
  "Revoke":
    "Widerrufen",
  "Revoke certificate?":
    "Zertifikat widerrufen?",
  "SRP-6a: Apple gets proof that you know the password – not the password itself.":
    "SRP-6a: Apple bekommt einen Beweis, dass du das Passwort kennst – nicht das Passwort selbst.",
  "Settings":
    "Einstellungen",
  "Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.":
    "Einstellungen › Datenschutz & Sicherheit › Entwicklermodus – sonst startet keine sideloadete App.",
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
  "Signed by someone else":
    "Fremd signiert",
  "Signed in":
    "Angemeldet",
  "Signed in.":
    "Angemeldet.",
  "Signed out.":
    "Abgemeldet.",
  "Source missing ({path}) – renewing is not possible.":
    "Quelle fehlt ({path}) – Erneuern nicht möglich.",
  "Start an instance inside the app now (a game, for example) – only then does it ask for memory. The unlock applies to this launch of the app only.":
    "Starte jetzt in der App eine Instanz (z. B. ein Spiel) – erst dann fragt sie nach Speicher. Die Freischaltung gilt nur für diesen Start der App.",
  "Starting …":
    "Wird gestartet …",
  "Still to do: {what}":
    "Noch zu tun: {what}",
  "System check":
    "Systemcheck",
  "System is ready – {count} step(s) still open.":
    "System ist bereit – noch {count} Schritt(e) offen.",
  "That is not an IPA file.":
    "Das ist keine IPA-Datei.",
  "The ModStaller service in the background has stopped":
    "Der ModStaller-Dienst im Hintergrund wurde beendet",
  "The app and its data are deleted from the iPhone. It comes from another tool – ModStaller cannot restore it.":
    "Die App und ihre Daten werden vom iPhone gelöscht. Sie stammt von einem anderen Werkzeug – ModStaller kann sie nicht wiederherstellen.",
  "The app and its data are deleted from the iPhone. That frees one of the three slots.":
    "Die App und ihre Daten werden vom iPhone gelöscht. Das macht einen der drei Plätze frei.",
  "The backend did not report in.":
    "Das Backend hat sich nicht gemeldet.",
  "The backend has stopped.":
    "Das Backend wurde beendet.",
  "The connected iPhone.":
    "Das angeschlossene iPhone.",
  "The iPhone is plugged in but locked or not paired.":
    "iPhone ist angesteckt, aber gesperrt oder nicht gekoppelt.",
  "The session is discarded. Installed apps keep running but can only be renewed after signing in again.":
    "Die Sitzung wird verworfen. Installierte Apps laufen weiter, lassen sich aber erst nach erneuter Anmeldung erneuern.",
  "This IPA is App Store encrypted (FairPlay) and cannot be re-signed.":
    "Diese IPA ist App-Store-verschlüsselt (FairPlay) und lässt sich nicht neu signieren.",
  "This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself.":
    "Das gibt kein Wochenkontingent zurück: Apple zählt neu angelegte App-IDs, nicht vorhandene. Ist das Fenster voll, weicht ModStaller von selbst auf eine freie App-ID aus.",
  "To renew, unlock or remove, the iPhone has to be connected and unlocked.":
    "Zum Erneuern, Freischalten oder Entfernen muss das iPhone angesteckt und entsperrt sein.",
  "Translations that are missing fall back to English.":
    "Fehlende Übersetzungen fallen auf Englisch zurück.",
  "Turn on":
    "Einschalten",
  "Unlock the iPhone and confirm “Trust”.":
    "iPhone entsperren und „Vertrauen“ bestätigen.",
  "Up to date – no newer version on GitHub.":
    "Aktuell – keine neuere Version auf GitHub.",
  "Update check failed: {message}":
    "Update-Prüfung fehlgeschlagen: {message}",
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
  "What ModStaller has installed. Free accounts: at most 3 apps, valid for 7 days each.":
    "Was ModStaller installiert hat. Kostenlose Konten: höchstens 3 Apps, je 7 Tage gültig.",
  "What's new?":
    "Was ist neu?",
  "Whether an app depends on it cannot be determined without a connected iPhone.":
    "Ob gerade eine App daran hängt, ist ohne angestecktes iPhone nicht feststellbar.",
  "Without a connected iPhone it cannot be said which App IDs are in use right now – apps of other tools depend on them too.":
    "Ohne angestecktes iPhone lässt sich nicht sagen, welche App-IDs gerade gebraucht werden – auch Apps anderer Werkzeuge hängen daran.",
  "Your Apple account signs the apps. The password is never stored or transmitted.":
    "Dein Apple-Account signiert die Apps. Das Passwort wird nie gespeichert oder übertragen.",
  "Your apps":
    "Deine Apps",
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
  "{count} day left":
    "noch {count} Tag",
  "{count} days ago":
    "vor {count} Tagen",
  "{count} days left":
    "noch {count} Tage",
  "{count} free":
    "{count} frei",
  "{count} h ago":
    "vor {count} Std.",
  "{count} hour left":
    "noch {count} Stunde",
  "{count} hours left":
    "noch {count} Stunden",
  "{count} point(s) prevent sideloading.":
    "{count} Punkt(e) verhindern das Sideloading.",
  "{count} point(s) to clear up.":
    "{count} Punkt(e) zu klären.",
  "{name} is installed and runs for {days} days.":
    "{name} ist installiert und läuft {days} Tage.",
  "{name} was removed from the iPhone.":
    "{name} wurde vom iPhone entfernt.",
  "{name} was renewed – valid for {days} days again.":
    "{name} ist erneuert – wieder {days} Tage gültig.",
  "{percent}% transferred":
    "{percent}% übertragen",
};

export default dict;
