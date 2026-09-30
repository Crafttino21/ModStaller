// Italiano - Katalog der Oberflaeche.
//
// Schluessel ist der englische Quelltext (siehe lib/i18n.svelte.ts).
// Ein fehlender Eintrag faellt auf Englisch zurueck.

import type { Dict } from "../i18n.svelte";

const dict: Dict = {
  "(exit {code})":
    "(uscita {code})",
  "<b>JIT</b> is needed by Java and emulator apps (Minecraft launchers, for example): ModStaller starts the app with a debugger attached and releases memory as soon as it asks for it.":
    "<b>JIT</b> serve alle app Java e agli emulatori (i launcher di Minecraft, per esempio): ModStaller avvia l’app con un debugger collegato e libera memoria non appena la richiede.",
  "Account":
    "Account",
  "Action":
    "Azione",
  "Active":
    "Attivo",
  "Active account ({account})":
    "Account attivo ({account})",
  "Add":
    "Aggiungi",
  "Add account":
    "Aggiungi account",
  "Add an Apple account":
    "Aggiungi un account Apple",
  "After the running task.":
    "Dopo l’operazione in corso.",
  "Again":
    "Riprova",
  "All":
    "Tutto",
  "All areas":
    "Tutte le aree",
  "All sources":
    "Tutte le fonti",
  "All {max} app slots of the free profile are taken – iOS will refuse a further app. Remove one first:":
    "Tutti i {max} slot del profilo gratuito sono occupati: iOS rifiuterà un’altra app. Rimuovine prima una:",
  "Also delete sign-ins, settings and logs":
    "Elimina anche accessi, impostazioni e registri",
  "Also discard the device identity (Apple will then ask for a two-factor code again)":
    "Elimina anche l’identità del dispositivo (Apple chiederà di nuovo un codice a due fattori)",
  "Also lists jailbreak tools and exploits - they are marked and ask before installing.":
    "Elenca anche strumenti di jailbreak ed exploit: sono contrassegnati e chiedono conferma prima dell’installazione.",
  "An installed app belongs to it – from ModStaller or from another tool. After deleting, it can no longer be renewed.":
    "Un’app installata dipende da esso, di ModStaller o di un altro strumento. Dopo l’eliminazione non potrà più essere rinnovata.",
  "An instance has to be started inside the app while it waits – only then does it ask for memory.":
    "Durante l’attesa va avviata un’istanza dentro l’app: solo allora chiede memoria.",
  "An ordinary, free Apple ID is enough. Apple then asks for a code on your iPhone.":
    "Basta un ID Apple normale e gratuito. Apple chiederà poi un codice sul tuo iPhone.",
  "Another operation is already running.":
    "C’è già un’operazione in corso.",
  "Any image; it is cropped to a square.":
    "Qualsiasi immagine; viene ritagliata a quadrato.",
  "App ID deleted.":
    "ID app eliminato.",
  "App IDs in the account":
    "ID app nell’account",
  "App IDs this week":
    "App ID questa settimana",
  "App extensions were removed to save App IDs.":
    "Le estensioni sono state rimosse per risparmiare ID app.",
  "App icon":
    "Icona dell’app",
  "Apple account":
    "Account Apple",
  "Apple allows only a few at a time. A foreign one (from AltStore or SideStore, say) cannot be used by ModStaller – its private key lives with the tool that requested it.":
    "Apple ne consente solo pochi alla volta. Uno altrui (di AltStore o SideStore, per dire) non serve a ModStaller: la sua chiave privata resta nello strumento che l’ha richiesto.",
  "Apple counts App IDs created in the last 7 days – deleting one does not give it back.":
    "Apple conta gli App ID creati negli ultimi 7 giorni: eliminarne uno non lo restituisce.",
  "Apple device service is not running":
    "Il servizio dispositivi Apple non è in esecuzione",
  "Apple device service missing":
    "Servizio dispositivi Apple mancante",
  "Apple sent a six-digit code to your iPhone.":
    "Apple ha inviato un codice di sei cifre al tuo iPhone.",
  "Applies to the whole program, including the messages that come from the background service.":
    "Vale per tutto il programma, anche per i messaggi del servizio in background.",
  "Applies to this launch only – unlock again after quitting the app.":
    "Vale solo per questo avvio: da riattivare dopo aver chiuso l’app.",
  "Apps":
    "App",
  "Apps from AltStore-compatible sources – signed with your Apple account and installed like any IPA.":
    "App da fonti compatibili con AltStore, firmate con il tuo account Apple e installate come qualsiasi IPA.",
  "Apps from the store are brought to the newest version of their source when they are renewed – same bundle ID, the app's data stays.":
    "Le app dello store vengono portate all’ultima versione della loro fonte al rinnovo: stesso bundle ID, i dati dell’app restano.",
  "Apps on the iPhone (free profile)":
    "App sull’iPhone (profilo gratuito)",
  "Asking Apple – this takes a few seconds …":
    "Interrogazione di Apple: ci vogliono alcuni secondi …",
  "Automatic updates exist only in the AppImage and in the Windows version installed with the setup.":
    "Gli aggiornamenti automatici esistono solo nell’AppImage e nella versione Windows installata con il programma di installazione.",
  "Back":
    "Indietro",
  "Backend not reachable":
    "Servizio di background irraggiungibile",
  "Background":
    "In background",
  "Battery {level} %":
    "Batteria {level} %",
  "Beta channel":
    "Canale beta",
  "Beta versions bring new features earlier, but they can be unstable and contain bugs.":
    "Le versioni beta portano prima le novità, ma possono essere instabili e contenere errori.",
  "Beta – may be unstable":
    "Beta – può essere instabile",
  "Bundle ID":
    "Bundle ID",
  "Bundle ID {id} · transport: {transport}":
    "Bundle ID {id} · trasporto: {transport}",
  "Cancel":
    "Annulla",
  "Cancelled":
    "Annullato",
  "Cancelled.":
    "Annullato.",
  "Cannot be kept – its ID does not belong to the app.":
    "Non può essere mantenuta: il suo ID non appartiene all’app.",
  "Certificate revoked.":
    "Certificato revocato.",
  "Change icon":
    "Cambia icona",
  "Charging … {level} %":
    "In carica – {level} %",
  "Check again":
    "Controlla di nuovo",
  "Check for updates":
    "Cerca aggiornamenti",
  "Checking the App ID quota …":
    "Controllo della quota di App ID…",
  "Checking {count} apps …":
    "Verifica di {count} app …",
  "Checking …":
    "Controllo …",
  "Choose a file":
    "Scegli un file",
  "Choose image …":
    "Scegli immagine…",
  "Clear store cache":
    "Svuota cache dello store",
  "Close":
    "Chiudi",
  "Closing the window keeps ModStaller in the tray. Quit it from the tray icon.":
    "Chiudendo la finestra ModStaller resta nell’area di notifica. Chiudilo dall’icona.",
  "Confirm":
    "Conferma",
  "Confirmation code":
    "Codice di conferma",
  "Connect a device to install.":
    "Collega un dispositivo per installare.",
  "Connected but not ready":
    "Collegato ma non pronto",
  "Connected but not ready – unlock the iPhone and confirm “Trust”.":
    "Collegato ma non pronto: sblocca l’iPhone e conferma «Autorizza».",
  "Connected via USB. Wi-Fi is on – without the cable ModStaller finds the iPhone in the same network.":
    "Collegato via USB. La Wi-Fi è attiva: senza cavo ModStaller trova l’iPhone nella stessa rete.",
  "Connected via USB. With Wi-Fi switched on, ModStaller also reaches the iPhone without the cable – for installing, renewing and the automatic renewal in the tray.":
    "Collegato via USB. Con la Wi-Fi attiva, ModStaller raggiunge l’iPhone anche senza cavo: per installare, rinnovare e per il rinnovo automatico dall’area di notifica.",
  "Connected via Wi-Fi. For JIT below iOS 17.4 the cable is still needed.":
    "Collegato via Wi-Fi. Per il JIT sotto iOS 17.4 serve ancora il cavo.",
  "Connection":
    "Connessione",
  "Copy":
    "Copia",
  "Copying is not possible.":
    "Impossibile copiare.",
  "Create a desktop shortcut":
    "Crea un collegamento sul desktop",
  "Customize":
    "Personalizza",
  "Customize …":
    "Personalizza …",
  "Data in":
    "Dati in",
  "Delete":
    "Elimina",
  "Delete App ID":
    "Elimina l’ID app",
  "Delete App ID?":
    "Eliminare l’ID app?",
  "Developer Mode":
    "Modalità sviluppatore",
  "Developer Mode is off.":
    "La modalità sviluppatore è disattivata.",
  "Developer Mode off":
    "Modalità sviluppatore disattivata",
  "Developer Mode on":
    "Modalità sviluppatore attiva",
  "Developer-signed":
    "Firmata da uno sviluppatore",
  "Development certificates":
    "Certificati di sviluppo",
  "Device":
    "Dispositivo",
  "Device forgotten.":
    "Dispositivo dimenticato.",
  "Device, sign-in and what expires soon – at a glance.":
    "Dispositivo, accesso e ciò che scade a breve, a colpo d’occhio.",
  "Different IPA":
    "Un altro IPA",
  "Does not fit":
    "Non compatibile",
  "Done":
    "Fatto",
  "Download":
    "Scarica",
  "Download {name}":
    "Scarica {name}",
  "Downloaded IPAs stay so apps can be renewed later. Clearing removes pictures and every IPA no installed app needs.":
    "Le IPA scaricate restano per poter rinnovare le app in seguito. Svuotare rimuove le immagini e ogni IPA che nessuna app installata usa.",
  "Downloads new versions and installs them while ModStaller is not in use. Afterwards it keeps running in the tray.":
    "Scarica le nuove versioni e le installa quando ModStaller non è in uso. Poi resta nell’area di notifica.",
  "Drag an IPA here":
    "Trascina qui un IPA",
  "Drag an IPA into the window or pick one from your Downloads.":
    "Trascina un IPA nella finestra o scegline uno dai download.",
  "Each kept extension needs an App ID of its own.":
    "Ogni estensione mantenuta ha bisogno di un proprio App ID.",
  "Enable JIT":
    "Attiva il JIT",
  "Errors":
    "Errori",
  "Every app signed with it will no longer start – including those of other sideloading tools.":
    "Tutte le app firmate con esso non si avvieranno più, comprese quelle di altri strumenti di sideloading.",
  "Everything ready for sideloading.":
    "Tutto pronto per il sideloading.",
  "Everything ready.":
    "Tutto pronto.",
  "Exploit":
    "Exploit",
  "Explorer shows the iPhone but ModStaller doesn’t? Unplug it, unlock it and plug it back in – if that doesn’t help, restart the PC.":
    "Esplora file mostra l’iPhone ma ModStaller no? Scollegalo, sbloccalo e ricollegalo; se non basta, riavvia il PC.",
  "Extension":
    "Estensione",
  "Extensions":
    "Estensioni",
  "Failed":
    "Non riuscito",
  "Files":
    "File",
  "Filter":
    "Filtra",
  "Fix":
    "Risolvi",
  "Follow live again":
    "Segui di nuovo in diretta",
  "Forget":
    "Dimentica",
  "Forget device":
    "Dimentica dispositivo",
  "Forget {name}?":
    "Dimenticare {name}?",
  "Found in your folders":
    "Trovati nelle tue cartelle",
  "Free":
    "Gratuito",
  "Free again: {dates}":
    "Di nuovo liberi: {dates}",
  "From other tools":
    "Da altri strumenti",
  "From {source}":
    "Da {source}",
  "Full log:":
    "Registro completo:",
  "Go to device":
    "Vai al dispositivo",
  "Hello, {name}!":
    "Ciao, {name}!",
  "How ModStaller behaves on this computer.":
    "Come si comporta ModStaller su questo computer.",
  "In the background":
    "In background",
  "Install":
    "Installa",
  "Install anyway":
    "Installa comunque",
  "Install app":
    "Installa un’app",
  "Install updates automatically":
    "Installa gli aggiornamenti automaticamente",
  "Install {name}":
    "Installa {name}",
  "Install {name}?":
    "Installare {name}?",
  "Installed":
    "Installata",
  "Installed through your package manager ({name}) – updates come from there.":
    "Installato tramite il gestore di pacchetti ({name}): gli aggiornamenti arrivano da lì.",
  "Installed user apps":
    "App utente installate",
  "Installing ModStaller…":
    "Installazione di ModStaller…",
  "Is everything here that ModStaller needs?":
    "C’è tutto quello che serve a ModStaller?",
  "It becomes the active account for new installs. Apps keep renewing with the account that installed them.":
    "Diventa l’account attivo per le nuove installazioni. Le app continuano a essere rinnovate con l’account che le ha installate.",
  "It is installed but stopped. Windows asks for confirmation once when it is started.":
    "È installato, ma arrestato. All’avvio Windows chiede una conferma.",
  "JIT and the Developer Disk Image still need the cable on this iOS version (Wi-Fi needs iOS 17.4 or newer for that).":
    "JIT e la Developer Disk Image richiedono ancora il cavo su questa versione di iOS (via Wi-Fi serve iOS 17.4 o successivo).",
  "JIT for {name}":
    "JIT per {name}",
  "Jailbreak tool":
    "Strumento di jailbreak",
  "Keep running in the tray when closed":
    "Resta nell’area di notifica alla chiusura",
  "Keep that screen open and pick the Apple TV below.":
    "Lascia aperta quella schermata e scegli l’Apple TV qui sotto.",
  "Keyboard":
    "Tastiera",
  "Language":
    "Lingua",
  "Leave out all extensions":
    "Ometti tutte le estensioni",
  "Leaving the beta channel keeps the installed beta until a newer stable version is out.":
    "Uscendo dal canale beta, la beta installata resta finché non esce una versione stabile più recente.",
  "List apps":
    "Elenca app",
  "Live":
    "In diretta",
  "Loading sources …":
    "Caricamento fonti …",
  "Log":
    "Registro",
  "Log file":
    "File di log",
  "Log file not found.":
    "File di log non trovato.",
  "Log in":
    "Registro in",
  "Looking for updates …":
    "Ricerca di aggiornamenti …",
  "Looking in the network …":
    "Ricerca nella rete …",
  "Make active":
    "Rendi attivo",
  "Manage App IDs ({count})":
    "Gestisci gli ID app ({count})",
  "Manage all":
    "Gestisci tutto",
  "Microsoft Store":
    "Microsoft Store",
  "ModStaller Setup":
    "Installazione di ModStaller",
  "ModStaller can stay in the tray, remind you before apps expire and renew them on its own. Renewing needs your iPhone connected via USB.":
    "ModStaller può restare nell’area di notifica, avvisarti prima che le app scadano e rinnovarle da solo. Per il rinnovo l’iPhone deve essere collegato via USB.",
  "ModStaller forgets the device and its pairing. Over the cable it shows up again; an Apple TV has to be paired again with a PIN.":
    "ModStaller dimentica il dispositivo e il suo abbinamento. Via cavo ricompare; un’Apple TV va abbinata di nuovo con un PIN.",
  "ModStaller is starting …":
    "ModStaller si sta avviando …",
  "ModStaller was removed.":
    "ModStaller è stato rimosso.",
  "ModStaller {version} is already installed.":
    "ModStaller {version} è già installato.",
  "ModStaller {version} is installed.":
    "ModStaller {version} è installato.",
  "Must be unique at Apple. Empty: ModStaller picks one that fits your team.":
    "Deve essere univoco presso Apple. Vuoto: ModStaller ne sceglie uno adatto al tuo team.",
  "Name on the home screen":
    "Nome nella schermata Home",
  "New icon – cropped to a square.":
    "Nuova icona, ritagliata a quadrato.",
  "New installs sign with the active account. Renewals always use the account that installed the app.":
    "Le nuove installazioni vengono firmate con l’account attivo. I rinnovi usano sempre l’account che ha installato l’app.",
  "Next: turn on Developer Mode on the Apple TV (Settings › Privacy & Security), then install the tvOS version of an app.":
    "Poi: attiva la modalità sviluppatore sull’Apple TV (Impostazioni › Privacy e sicurezza), quindi installa la versione tvOS di un’app.",
  "Next: turn on Developer Mode on the Vision Pro (Settings › Privacy & Security), then install an app.":
    "Poi: attiva la modalità sviluppatore sul Vision Pro (Impostazioni › Privacy e sicurezza), quindi installa un’app.",
  "No IPAs in Downloads, Documents or Desktop.":
    "Nessun IPA in Download, Documenti o Scrivania.",
  "No app in your sources fits the {kind}.":
    "Nessuna app delle tue fonti è compatibile con {kind}.",
  "No app installed yet":
    "Nessuna app installata per ora",
  "No app matches “{query}”.":
    "Nessuna app corrisponde a «{query}».",
  "No apps - add a source under “Sources”.":
    "Nessuna app: aggiungi una fonte in «Fonti».",
  "No certificates in the account.":
    "Nessun certificato nell’account.",
  "No device":
    "Nessun dispositivo",
  "No device connected – plug the iPhone in via USB and unlock it, or bring it into the same Wi-Fi.":
    "Nessun dispositivo collegato: collega l’iPhone via USB e sbloccalo, oppure portalo sulla stessa Wi-Fi.",
  "No device connected. Plug the iPhone in via USB and unlock it – or bring it into the same Wi-Fi.":
    "Nessun dispositivo collegato. Collega l’iPhone via USB e sbloccalo, oppure portalo sulla stessa Wi-Fi.",
  "No entries for this filter.":
    "Nessuna voce per questo filtro.",
  "No installed app belongs to this App ID right now.":
    "Al momento nessuna app installata usa questo ID app.",
  "No messages yet.":
    "Ancora nessun messaggio.",
  "No new App ID needed – the ones this install uses already exist.":
    "Nessun nuovo App ID necessario: quelli usati esistono già.",
  "No tray icon available. Reminders and renewals still work; start ModStaller again to open the window.":
    "Nessuna icona nell’area di notifica disponibile. Promemoria e rinnovi funzionano comunque; riavvia ModStaller per aprire la finestra.",
  "Not checked yet.":
    "Non ancora controllato.",
  "Not connected":
    "Non collegato",
  "Not signed in":
    "Non hai effettuato l’accesso",
  "Not signed in with Apple.":
    "Non collegato ad Apple.",
  "Nothing found – everything on the iPhone comes from the store or from ModStaller.":
    "Non trovato nulla: tutto ciò che è sull’iPhone viene dallo store o da ModStaller.",
  "Nothing found. Is the pairing screen open on the device and is it in the same network?":
    "Nessun risultato. La schermata di abbinamento è aperta sul dispositivo ed è nella stessa rete?",
  "Nothing has happened yet.":
    "Non è ancora successo nulla.",
  "Nothing has happened yet. As soon as you plug in an iPhone or install something, it shows up here.":
    "Non è ancora successo nulla. Appena colleghi un iPhone o installi qualcosa, comparirà qui.",
  "Nothing installed through ModStaller yet.":
    "Per ora non è stato installato nulla con ModStaller.",
  "Nothing is due right now":
    "Al momento non scade nulla",
  "Nothing was due.":
    "Non scadeva nulla.",
  "Notifications":
    "Notifiche",
  "On the Apple TV open Settings › Remotes and Devices › Remote App and Devices.":
    "Sull’Apple TV apri Impostazioni › Telecomandi e dispositivi › App Remote e dispositivi.",
  "On the Vision Pro open Settings › General › Remote Devices.":
    "Sul Vision Pro apri Impostazioni › Generali › Dispositivi remoti.",
  "One click fixes it – see above.":
    "Basta un clic: vedi sopra.",
  "Only for installed copies and the AppImage - not in development builds.":
    "Solo per le copie installate e l’AppImage, non nelle build di sviluppo.",
  "Only for your user – no administrator rights needed. Your sign-ins and settings stay where they are.":
    "Solo per il tuo utente, senza diritti di amministratore. I tuoi accessi e le impostazioni restano dove sono.",
  "Optional – empty fields keep what the IPA says.":
    "Facoltativo: i campi vuoti mantengono quanto indicato nell’IPA.",
  "Original icon":
    "Icona originale",
  "Overview":
    "Panoramica",
  "PIN from the Apple TV":
    "PIN dell’Apple TV",
  "Paid":
    "A pagamento",
  "Paid account – no weekly limit on App IDs and no limit on apps.":
    "Account a pagamento: nessun limite settimanale di App ID e nessun limite di app.",
  "Pair":
    "Abbina",
  "Pair Apple TV or Vision Pro":
    "Abbina Apple TV o Vision Pro",
  "Pair device":
    "Abbina dispositivo",
  "Pair {name}":
    "Abbina {name}",
  "Paired over the network – reachable while the device is on and in the same network.":
    "Abbinato via rete: raggiungibile finché il dispositivo è acceso e nella stessa rete.",
  "Password":
    "Password",
  "Pause":
    "Pausa",
  "Paused":
    "In pausa",
  "Photo editing":
    "Modifica foto",
  "Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.":
    "Scegli un IPA: ModStaller lo firma con il tuo account Apple e lo installa sull’iPhone.",
  "Pick it below and confirm the pairing on the Vision Pro.":
    "Sceglilo qui sotto e conferma l’abbinamento sul Vision Pro.",
  "Plug it in via USB and unlock it – or bring it into the same Wi-Fi.":
    "Collegalo via USB e sbloccalo, oppure portalo sulla stessa Wi-Fi.",
  "Preparing Anisette …":
    "Preparazione di Anisette …",
  "Program":
    "Programma",
  "Read again":
    "Rileggi",
  "Reading the IPA …":
    "Lettura dell’IPA …",
  "Receive beta versions":
    "Ricevi versioni beta",
  "Recent activity":
    "Attività recente",
  "Refresh":
    "Aggiorna",
  "Registered devices":
    "Dispositivi registrati",
  "Reinstall":
    "Reinstalla",
  "Released":
    "Pubblicata",
  "Reload":
    "Ricarica",
  "Reload sources":
    "Ricarica fonti",
  "Remind me before apps expire":
    "Avvisami prima che le app scadano",
  "Remove":
    "Rimuovi",
  "Remove from the device":
    "Rimuovi dal dispositivo",
  "Remove {name}":
    "Rimuovi {name}",
  "Remove {name}?":
    "Rimuovere {name}?",
  "Removes the program, the start menu entry and the `modstaller` command.":
    "Rimuove il programma, la voce del menu e il comando `modstaller`.",
  "Removing ModStaller…":
    "Rimozione di ModStaller…",
  "Renew":
    "Rinnova",
  "Renew apps automatically":
    "Rinnova le app automaticamente",
  "Renew before it expires, from the overview or under “Apps”.":
    "Rinnovala prima della scadenza, dalla panoramica o sotto «App».",
  "Renew due":
    "Rinnova le scadute",
  "Renew due apps":
    "Rinnova le app scadute",
  "Renew now":
    "Rinnova ora",
  "Renew {name}":
    "Rinnova {name}",
  "Renewed {count} apps.":
    "{count} app rinnovate.",
  "Renewing {name} in the background …":
    "Rinnovo di {name} in background …",
  "Repair":
    "Ripara",
  "Requires":
    "Richiede",
  "Restart":
    "Riavvia",
  "Reuse an unused App ID …":
    "Riutilizza un App ID inutilizzato…",
  "Revoke":
    "Revoca",
  "Revoke certificate?":
    "Revocare il certificato?",
  "Runs on":
    "Funziona su",
  "SRP-6a: Apple gets proof that you know the password – not the password itself.":
    "SRP-6a: Apple ottiene la prova che conosci la password, non la password stessa.",
  "Safari":
    "Safari",
  "Screen broadcast":
    "Trasmissione schermo",
  "Search":
    "Cerca",
  "Search again":
    "Cerca di nuovo",
  "Search apps":
    "Cerca app",
  "Set up automatically":
    "Configura automaticamente",
  "Set up the Apple device service":
    "Configura il servizio dispositivi Apple",
  "Settings":
    "Impostazioni",
  "Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.":
    "Impostazioni › Privacy e sicurezza › Modalità sviluppatore – altrimenti nessuna app in sideload si avvierà.",
  "Share":
    "Condivisione",
  "Show all":
    "Mostra tutte",
  "Show in the store":
    "Mostra nello store",
  "Show teams and certificates":
    "Mostra team e certificati",
  "Sideloading for {platform}":
    "Sideloading per {platform}",
  "Sideloading has risks: apps from sources are not reviewed by Apple. Only install apps from sources you trust, and keep an eye on what an app asks for.":
    "Il sideloading comporta dei rischi: Apple non verifica le app delle fonti. Installa solo app da fonti di cui ti fidi e fai attenzione a cosa chiede un’app.",
  "Sideloads on the iPhone that do not come from ModStaller – from AltStore or SideStore, for instance. Renewing is not possible: the original IPA and the private key live with the other tool.":
    "Sideload presenti sull’iPhone che non vengono da ModStaller, per esempio da AltStore o SideStore. Il rinnovo non è possibile: l’IPA originale e la chiave privata restano nell’altro strumento.",
  "Sign & install":
    "Firma e installa",
  "Sign in":
    "Accedi",
  "Sign in once, then ModStaller signs by itself.":
    "Accedi una volta, poi ModStaller firma da solo.",
  "Sign in with Apple":
    "Accedi con Apple",
  "Sign out":
    "Esci",
  "Sign out?":
    "Uscire?",
  "Sign with":
    "Firma con",
  "Signed by someone else":
    "Firmata da terzi",
  "Signed by {account}":
    "Firmata da {account}",
  "Signed in":
    "Accesso effettuato",
  "Signed in.":
    "Accesso effettuato.",
  "Signed out.":
    "Uscita effettuata.",
  "Signed-in accounts":
    "Account collegati",
  "Siri & Shortcuts":
    "Siri e Comandi rapidi",
  "Size":
    "Dimensione",
  "Source":
    "Fonte",
  "Source added: {name} ({count} apps)":
    "Fonte aggiunta: {name} ({count} app)",
  "Source missing ({path}) – renewing is not possible.":
    "Sorgente mancante ({path}): rinnovo impossibile.",
  "Sources":
    "Fonti",
  "Sources in the AltStore format – the same ones AltStore and SideStore read. ModStaller comes with the official sources of AltStore, SideStore, UTM, PojavLauncher/Amethyst, iSH, StikDebug and several emulators.":
    "Fonti nel formato AltStore, le stesse che leggono AltStore e SideStore. ModStaller include le fonti ufficiali di AltStore, SideStore, UTM, PojavLauncher/Amethyst, iSH, StikDebug e diversi emulatori.",
  "Sources you add are your responsibility: ModStaller shows what they list, it does not check it. Only install apps you are allowed to use.":
    "Le fonti che aggiungi sono una tua responsabilità: ModStaller mostra ciò che elencano, non lo controlla. Installa solo app che hai il diritto di usare.",
  "Stable channel":
    "Canale stabile",
  "Stable versions are always offered. With the beta channel, pre-release versions (-beta.x) are offered as well.":
    "Le versioni stabili vengono sempre proposte. Con il canale beta anche le versioni preliminari (-beta.x).",
  "Start ModStaller":
    "Avvia ModStaller",
  "Start an instance inside the app now (a game, for example) – only then does it ask for memory. The unlock applies to this launch of the app only.":
    "Avvia ora un’istanza dentro l’app (un gioco, per esempio): solo allora chiede memoria. L’attivazione vale solo per questo avvio.",
  "Start menu":
    "Menu",
  "Start service":
    "Avvia il servizio",
  "Start with the system":
    "Avvia con il sistema",
  "Starting …":
    "Avvio …",
  "Starts in the tray after you log in, without a window.":
    "Si avvia nell’area di notifica dopo l’accesso, senza finestra.",
  "Still to do: {what}":
    "Ancora da fare: {what}",
  "Store":
    "Store",
  "Suitable for {name} ({os} {version})":
    "Adatto a {name} ({os} {version})",
  "Switch off Wi-Fi":
    "Disattiva Wi-Fi",
  "Switch on Wi-Fi":
    "Attiva Wi-Fi",
  "Switch to this device":
    "Passa a questo dispositivo",
  "System":
    "Sistema",
  "System check":
    "Controllo di sistema",
  "System is ready – {count} step(s) still open.":
    "Il sistema è pronto: restano {count} passaggio/i.",
  "Teams and certificates of {account}":
    "Team e certificati di {account}",
  "Terminal":
    "Terminale",
  "That image cannot be read.":
    "Impossibile leggere questa immagine.",
  "That is not an IPA file.":
    "Questo non è un file IPA.",
  "The Apple TV now shows a code on the screen. Type it in here.":
    "L’Apple TV ora mostra un codice sullo schermo. Inseriscilo qui.",
  "The Apple Watch app is removed – it cannot be installed this way.":
    "L’app per Apple Watch viene rimossa: non si può installare in questo modo.",
  "The ModStaller service in the background has stopped":
    "Il servizio ModStaller in background si è fermato",
  "The app and its data are deleted from the device. It comes from another tool – ModStaller cannot restore it.":
    "L’app e i suoi dati vengono eliminati dal dispositivo. Proviene da un altro strumento: ModStaller non può ripristinarla.",
  "The app and its data are deleted from the device. That frees one of the three slots.":
    "L’app e i suoi dati vengono eliminati dal dispositivo. Così si libera uno dei tre posti.",
  "The app runs under the unused App ID {id}.":
    "L’app usa l’App ID inutilizzato {id}.",
  "The backend did not report in.":
    "Il servizio di background non si è fatto vivo.",
  "The backend has stopped.":
    "Il servizio di background si è fermato.",
  "The bundle ID is not valid – letters, digits and hyphens, separated by dots.":
    "Il bundle ID non è valido: lettere, cifre e trattini, separati da punti.",
  "The connected device.":
    "Il dispositivo collegato.",
  "The iPhone is plugged in but locked or not paired.":
    "L’iPhone è collegato ma bloccato o non associato.",
  "The next one frees up around {date}.":
    "Il prossimo si libera intorno al {date}.",
  "The session is discarded. Installed apps keep running but can only be renewed after signing in again.":
    "La sessione viene scartata. Le app installate continuano a funzionare, ma potranno essere rinnovate solo dopo un nuovo accesso.",
  "There already is a different `modstaller` command in ~/.local/bin – it was left untouched.":
    "In ~/.local/bin esiste già un altro comando `modstaller`: non è stato toccato.",
  "Third-party store":
    "Store di terze parti",
  "This IPA is App Store encrypted (FairPlay) and cannot be re-signed.":
    "Questo IPA è cifrato dall’App Store (FairPlay) e non può essere rifirmato.",
  "This IPA is an Apple TV app – pick the Apple TV as the device.":
    "Questa IPA è un’app per Apple TV: scegli l’Apple TV come dispositivo.",
  "This IPA is an Apple Vision Pro app – pick the Vision Pro as the device.":
    "Questa IPA è un’app per Apple Vision Pro: scegli il Vision Pro come dispositivo.",
  "This IPA is for iPhone and iPad – an Apple TV needs the app's tvOS version.":
    "Questa IPA è per iPhone e iPad: un’Apple TV ha bisogno della versione tvOS dell’app.",
  "This app changes the system through an exploit. That can go wrong and leave the device unstable - only install it if you know what it does.":
    "Questa app modifica il sistema tramite un exploit. Può andare storto e rendere il dispositivo instabile: installala solo se sai cosa fa.",
  "This app installs apps from another store, many of them cracked. ModStaller cannot check what comes from there.":
    "Questa app installa app da un altro store, molte delle quali craccate. ModStaller non può controllare ciò che arriva da lì.",
  "This app is made for iPad only and does not start on an {kind}.":
    "Questa app è solo per iPad e non si avvia su un {kind}.",
  "This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself.":
    "Questo non restituisce quota settimanale: Apple conta gli ID app creati ex novo, non quelli esistenti. Quando la finestra è piena, ModStaller passa da solo a un ID libero.",
  "This install needs {cost} – {missing} more than are left.":
    "Questa installazione ne richiede {cost}: {missing} in più di quelli disponibili.",
  "This install uses {cost} of them.":
    "Questa installazione ne usa {cost}.",
  "This is a jailbreak tool. It attacks the system with an exploit - a failed run can mean a boot loop, a restore and lost data, and it weakens the device's security. Only install it if you know exactly what you are doing.":
    "È uno strumento di jailbreak. Attacca il sistema con un exploit: un tentativo fallito può causare un boot loop, un ripristino e la perdita di dati, e indebolisce la sicurezza del dispositivo. Installalo solo se sai esattamente cosa stai facendo.",
  "This version does not fit the {kind} ({name}) - check the required system version and device type, or pick another source.":
    "Questa versione non è compatibile con {kind} ({name}): controlla la versione di sistema richiesta e il tipo di dispositivo, oppure scegli un’altra fonte.",
  "To renew, unlock or remove, the iPhone has to be connected and unlocked.":
    "Per rinnovare, attivare o rimuovere, l’iPhone deve essere collegato e sbloccato.",
  "Translations that are missing fall back to English.":
    "Le traduzioni mancanti tornano all’inglese.",
  "Try again":
    "Riprova",
  "Turn on":
    "Attiva",
  "Type in the PIN the Apple TV then shows.":
    "Inserisci il PIN che l’Apple TV mostra a quel punto.",
  "Undo":
    "Annulla",
  "Undo changes":
    "Annulla modifiche",
  "Uninstall":
    "Disinstalla",
  "Uninstall now":
    "Disinstalla ora",
  "Unlock the iPhone and confirm “Trust”.":
    "Sblocca l’iPhone e conferma «Autorizza».",
  "Unplug the iPhone and plug it in again.":
    "Scollega l’iPhone e ricollegalo.",
  "Unused ones are reused automatically when the weekly quota is used up – or pick one yourself when installing.":
    "Quelli inutilizzati vengono riutilizzati automaticamente quando la quota settimanale è esaurita, oppure scegline uno durante l’installazione.",
  "Up to date – no newer version on GitHub.":
    "Aggiornato: nessuna versione più recente su GitHub.",
  "Update":
    "Aggiorna",
  "Update check failed: {message}":
    "Controllo aggiornamenti non riuscito: {message}",
  "Update store apps while renewing":
    "Aggiorna le app dello store al rinnovo",
  "Update to {version}":
    "Aggiorna a {version}",
  "Updates":
    "Aggiornamenti",
  "Updates available":
    "Aggiornamenti disponibili",
  "VPN / network":
    "VPN / rete",
  "Version":
    "Versione",
  "Version {version} for Linux":
    "Versione {version} per Linux",
  "Version {version} is available":
    "La versione {version} è disponibile",
  "Version {version} is available – see bottom left.":
    "La versione {version} è disponibile: vedi in basso a sinistra.",
  "Version {version} is ready":
    "La versione {version} è pronta",
  "Version {version} · Apple TV · from tvOS {os}":
    "Versione {version} · Apple TV · da tvOS {os}",
  "Version {version} · Apple Vision Pro · from visionOS {os}":
    "Versione {version} · Apple Vision Pro · da visionOS {os}",
  "Version {version} · from iOS {ios}":
    "Versione {version} · da iOS {ios}",
  "View quotas and certificates":
    "Vedi quote e certificati",
  "Wait for the running task first":
    "Attendi prima la fine dell’operazione in corso",
  "Warnings":
    "Avvisi",
  "What ModStaller does – live. The complete history is in the log file.":
    "Cosa fa ModStaller – in diretta. La cronologia completa è nel file di log.",
  "What ModStaller has installed. Free accounts: at most 3 apps, valid for 7 days each.":
    "Che cosa ha installato ModStaller. Account gratuiti: al massimo 3 app, valide 7 giorni ciascuna.",
  "What's new in {version}":
    "Novità di {version}",
  "What's new?":
    "Novità",
  "Where ModStaller is installed":
    "Dove viene installato ModStaller",
  "Whether an app depends on it cannot be determined without a connected iPhone.":
    "Senza un iPhone collegato non si può stabilire se un’app dipende da esso.",
  "Wi-Fi":
    "Wi-Fi",
  "Wi-Fi is off. The iPhone is only reachable over the cable again.":
    "La Wi-Fi è disattivata. L’iPhone è di nuovo raggiungibile solo via cavo.",
  "Wi-Fi is on. The iPhone can now be unplugged – ModStaller finds it in the same network.":
    "La Wi-Fi è attiva. Ora puoi scollegare l’iPhone: ModStaller lo trova nella stessa rete.",
  "Widget":
    "Widget",
  "Windows shows the iPhone in Explorer through its own photo driver – ModStaller needs Apple’s device service for USB. ModStaller can set it up for you: “Apple Devices” from the Microsoft Store, otherwise just Apple’s USB driver.":
    "Windows mostra l’iPhone in Esplora file tramite il proprio driver foto, ma ModStaller ha bisogno del servizio dispositivi di Apple per l’USB. ModStaller può configurarlo per te: «Dispositivi Apple» dal Microsoft Store, altrimenti solo il driver USB di Apple.",
  "Without a connected iPhone it cannot be said which App IDs are in use right now – apps of other tools depend on them too.":
    "Senza un iPhone collegato non si può dire quali ID app siano in uso: anche app di altri strumenti dipendono da essi.",
  "You find it in the start menu. You can remove it again by running this setup once more.":
    "Lo trovi nel menu. Per rimuoverlo, avvia di nuovo questa installazione.",
  "Your Apple account signs the apps. The password is never stored or transmitted.":
    "Il tuo account Apple firma le app. La password non viene mai salvata né trasmessa.",
  "Your apps":
    "Le tue app",
  "Your sign-ins and settings were kept.":
    "I tuoi accessi e le impostazioni sono stati mantenuti.",
  "and {count} more":
    "e altre {count}",
  "days before expiry":
    "giorni prima della scadenza",
  "expired":
    "scaduta",
  "expires {date}":
    "scade il {date}",
  "expires – {when}":
    "scade – {when}",
  "extensions":
    "estensioni",
  "frameworks":
    "framework",
  "free":
    "libero",
  "has expired":
    "è scaduta",
  "hours before expiry. If your iPhone is not connected then, ModStaller asks for it and renews as soon as it is.":
    "ore prima della scadenza. Se l’iPhone non è collegato in quel momento, ModStaller lo chiede e rinnova appena lo è.",
  "in use":
    "in uso",
  "injected dylibs":
    "dylib iniettate",
  "just now":
    "proprio ora",
  "off":
    "disattivata",
  "on":
    "attiva",
  "or":
    "oppure",
  "yesterday":
    "ieri",
  "{account} now signs new installs.":
    "{account} ora firma le nuove installazioni.",
  "{available} of {max} left":
    "{available} di {max} disponibili",
  "{count} accounts signed in":
    "{count} account collegati",
  "{count} apps":
    "{count} app",
  "{count} day left":
    "resta {count} giorno",
  "{count} days ago":
    "{count} giorni fa",
  "{count} days left":
    "restano {count} giorni",
  "{count} entries copied.":
    "{count} voci copiate.",
  "{count} free":
    "{count} liberi",
  "{count} h ago":
    "{count} h fa",
  "{count} hidden":
    "{count} nascoste",
  "{count} hour left":
    "resta {count} ora",
  "{count} hours left":
    "restano {count} ore",
  "{count} new":
    "{count} nuove",
  "{count} new App ID(s) created.":
    "{count} nuovo/i App ID creato/i.",
  "{count} point(s) prevent sideloading.":
    "{count} punto/i impediscono il sideloading.",
  "{count} point(s) to clear up.":
    "{count} punto/i da chiarire.",
  "{count} sources":
    "{count} fonti",
  "{from} → {to}":
    "{from} → {to}",
  "{kind} via {via}":
    "{kind} via {via}",
  "{minutes} min ago":
    "{minutes} min fa",
  "{name} is being renewed in the background. Try again in a moment.":
    "{name} è in fase di rinnovo in background. Riprova tra un momento.",
  "{name} is downloaded - adjust it and install.":
    "{name} è scaricata: modificala e installala.",
  "{name} is installed and runs for {days} days.":
    "{name} è installata e funziona {days} giorni.",
  "{name} is paired.":
    "{name} è abbinata.",
  "{name} was removed from the device.":
    "{name} è stata rimossa dal dispositivo.",
  "{name} was renewed – valid for {days} days again.":
    "{name} è stata rinnovata: di nuovo valida {days} giorni.",
  "{percent}% transferred":
    "{percent}% trasferito",
  "{size} freed ({count} IPAs removed).":
    "{size} liberati ({count} IPA rimosse).",
  "{used} of {max} used":
    "{used} di {max} occupati",
  "~/.local/bin is not on your PATH yet – the `modstaller` command works in the terminal after logging in again.":
    "~/.local/bin non è ancora nel tuo PATH: il comando `modstaller` funzionerà nel terminale dopo un nuovo accesso.",
};

export default dict;
