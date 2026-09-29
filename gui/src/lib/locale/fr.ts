// Francais - Katalog der Oberflaeche.
//
// Schluessel ist der englische Quelltext (siehe lib/i18n.svelte.ts).
// Ein fehlender Eintrag faellt auf Englisch zurueck.

import type { Dict } from "../i18n.svelte";

const dict: Dict = {
  "(exit {code})":
    "(sortie {code})",
  "<b>JIT</b> is needed by Java and emulator apps (Minecraft launchers, for example): ModStaller starts the app with a debugger attached and releases memory as soon as it asks for it.":
    "<b>JIT</b> est nécessaire pour les applications Java et les émulateurs (les lanceurs Minecraft, par exemple) : ModStaller démarre l’application avec un débogueur attaché et libère de la mémoire dès qu’elle en demande.",
  "Account":
    "Compte",
  "Action":
    "Action",
  "Active":
    "Actif",
  "Active account ({account})":
    "Compte actif ({account})",
  "Add account":
    "Ajouter un compte",
  "Add an Apple account":
    "Ajouter un compte Apple",
  "After the running task.":
    "Après la tâche en cours.",
  "Again":
    "Réessayer",
  "All":
    "Tout",
  "All areas":
    "Tous les domaines",
  "All {max} app slots of the free profile are taken – iOS will refuse a further app. Remove one first:":
    "Les {max} emplacements du profil gratuit sont occupés – iOS refusera une app de plus. Supprimez-en d’abord une :",
  "Also delete sign-ins, settings and logs":
    "Supprimer aussi les connexions, les réglages et les journaux",
  "Also discard the device identity (Apple will then ask for a two-factor code again)":
    "Effacer aussi l’identité de l’appareil (Apple redemandera alors un code à deux facteurs)",
  "An installed app belongs to it – from ModStaller or from another tool. After deleting, it can no longer be renewed.":
    "Une application installée en dépend – de ModStaller ou d’un autre outil. Après la suppression, elle ne pourra plus être renouvelée.",
  "An instance has to be started inside the app while it waits – only then does it ask for memory.":
    "Une instance doit être lancée dans l’application pendant l’attente – ce n’est qu’alors qu’elle demande de la mémoire.",
  "An ordinary, free Apple ID is enough. Apple then asks for a code on your iPhone.":
    "Un identifiant Apple ordinaire et gratuit suffit. Apple demande ensuite un code sur votre iPhone.",
  "Another operation is already running.":
    "Une opération est déjà en cours.",
  "Any image; it is cropped to a square.":
    "N’importe quelle image ; elle est recadrée en carré.",
  "App ID deleted.":
    "Identifiant d’app supprimé.",
  "App IDs in the account":
    "Identifiants d’app du compte",
  "App IDs this week":
    "App ID cette semaine",
  "App extensions were removed to save App IDs.":
    "Les extensions ont été retirées pour économiser des identifiants d’app.",
  "App icon":
    "Icône de l’app",
  "Apple account":
    "Compte Apple",
  "Apple allows only a few at a time. A foreign one (from AltStore or SideStore, say) cannot be used by ModStaller – its private key lives with the tool that requested it.":
    "Apple n’en autorise que quelques-uns à la fois. Un certificat étranger (d’AltStore ou de SideStore, par exemple) est inutilisable par ModStaller – sa clé privée reste chez l’outil qui l’a demandé.",
  "Apple counts App IDs created in the last 7 days – deleting one does not give it back.":
    "Apple compte les App ID créés ces 7 derniers jours – en supprimer un ne le rend pas.",
  "Apple device service is not running":
    "Le service d’appareils Apple est arrêté",
  "Apple device service missing":
    "Service d’appareils Apple manquant",
  "Apple sent a six-digit code to your iPhone.":
    "Apple a envoyé un code à six chiffres sur votre iPhone.",
  "Applies to the whole program, including the messages that come from the background service.":
    "S’applique à tout le programme, y compris aux messages du service en arrière-plan.",
  "Applies to this launch only – unlock again after quitting the app.":
    "Ne vaut que pour ce lancement – à réactiver après avoir quitté l’application.",
  "Apps":
    "Applications",
  "Apps on the iPhone (free profile)":
    "Apps sur l’iPhone (profil gratuit)",
  "Asking Apple – this takes a few seconds …":
    "Interrogation d’Apple – cela prend quelques secondes …",
  "Automatic updates exist only in the AppImage and in the Windows version installed with the setup.":
    "Les mises à jour automatiques n’existent que dans l’AppImage et dans la version Windows installée avec le programme d’installation.",
  "Back":
    "Retour",
  "Backend not reachable":
    "Service de fond injoignable",
  "Background":
    "Arrière-plan",
  "Battery {level} %":
    "Batterie {level} %",
  "Beta channel":
    "Canal bêta",
  "Beta versions bring new features earlier, but they can be unstable and contain bugs.":
    "Les versions bêta apportent les nouveautés plus tôt, mais peuvent être instables et contenir des bugs.",
  "Beta – may be unstable":
    "Bêta – peut être instable",
  "Bundle ID":
    "Bundle ID",
  "Bundle ID {id} · transport: {transport}":
    "Bundle ID {id} · transport : {transport}",
  "Cancel":
    "Annuler",
  "Cancelled":
    "Annulé",
  "Cancelled.":
    "Annulé.",
  "Cannot be kept – its ID does not belong to the app.":
    "Impossible de la conserver – son ID n’appartient pas à l’app.",
  "Certificate revoked.":
    "Certificat révoqué.",
  "Change icon":
    "Changer l’icône",
  "Charging … {level} %":
    "En charge – {level} %",
  "Check again":
    "Vérifier à nouveau",
  "Check for updates":
    "Rechercher des mises à jour",
  "Checking the App ID quota …":
    "Vérification du quota d’App ID…",
  "Checking …":
    "Vérification …",
  "Choose a file":
    "Choisir un fichier",
  "Choose image …":
    "Choisir une image…",
  "Close":
    "Fermer",
  "Closing the window keeps ModStaller in the tray. Quit it from the tray icon.":
    "Fermer la fenêtre laisse ModStaller dans la barre système. Quittez-le depuis l’icône.",
  "Confirm":
    "Confirmer",
  "Confirmation code":
    "Code de confirmation",
  "Connected but not ready":
    "Connecté mais pas prêt",
  "Connected but not ready – unlock the iPhone and confirm “Trust”.":
    "Connecté mais pas prêt – déverrouillez l’iPhone et confirmez « Se fier ».",
  "Connected via USB. Wi-Fi is on – without the cable ModStaller finds the iPhone in the same network.":
    "Connecté en USB. Le Wi-Fi est activé – sans câble, ModStaller trouve l’iPhone sur le même réseau.",
  "Connected via USB. With Wi-Fi switched on, ModStaller also reaches the iPhone without the cable – for installing, renewing and the automatic renewal in the tray.":
    "Connecté en USB. Avec le Wi-Fi activé, ModStaller joint aussi l’iPhone sans câble – pour installer, renouveler et pour le renouvellement automatique depuis la barre système.",
  "Connected via Wi-Fi. For JIT below iOS 17.4 the cable is still needed.":
    "Connecté en Wi-Fi. Pour le JIT sous iOS 17.4, le câble reste nécessaire.",
  "Connection":
    "Connexion",
  "Copy":
    "Copier",
  "Copying is not possible.":
    "Impossible de copier.",
  "Create a desktop shortcut":
    "Créer un raccourci sur le bureau",
  "Customize":
    "Personnaliser",
  "Data in":
    "Données dans",
  "Delete":
    "Supprimer",
  "Delete App ID":
    "Supprimer l’identifiant d’app",
  "Delete App ID?":
    "Supprimer l’identifiant d’app ?",
  "Developer Mode":
    "Mode développeur",
  "Developer Mode is off.":
    "Le mode développeur est désactivé.",
  "Developer Mode off":
    "Mode développeur désactivé",
  "Developer Mode on":
    "Mode développeur activé",
  "Developer-signed":
    "Signé par un développeur",
  "Development certificates":
    "Certificats de développement",
  "Device":
    "Appareil",
  "Device forgotten.":
    "Appareil oublié.",
  "Device, sign-in and what expires soon – at a glance.":
    "Appareil, connexion et ce qui expire bientôt – en un coup d’œil.",
  "Different IPA":
    "Autre IPA",
  "Done":
    "Terminé",
  "Download":
    "Télécharger",
  "Downloads new versions and installs them while ModStaller is not in use. Afterwards it keeps running in the tray.":
    "Télécharge les nouvelles versions et les installe quand ModStaller n’est pas utilisé. Ensuite, il reste dans la barre système.",
  "Drag an IPA here":
    "Glissez un IPA ici",
  "Drag an IPA into the window or pick one from your Downloads.":
    "Glissez un IPA dans la fenêtre ou choisissez-en un dans vos téléchargements.",
  "Each kept extension needs an App ID of its own.":
    "Chaque extension conservée a besoin de son propre App ID.",
  "Enable JIT":
    "Activer le JIT",
  "Errors":
    "Erreurs",
  "Every app signed with it will no longer start – including those of other sideloading tools.":
    "Toutes les applications signées avec lui ne démarreront plus – y compris celles d’autres outils de sideloading.",
  "Everything ready for sideloading.":
    "Tout est prêt pour le sideloading.",
  "Everything ready.":
    "Tout est prêt.",
  "Explorer shows the iPhone but ModStaller doesn’t? Unplug it, unlock it and plug it back in – if that doesn’t help, restart the PC.":
    "L’Explorateur affiche l’iPhone mais pas ModStaller ? Débranchez-le, déverrouillez-le et rebranchez-le – sinon, redémarrez le PC.",
  "Extension":
    "Extension",
  "Extensions":
    "Extensions",
  "Failed":
    "Échec",
  "Files":
    "Fichiers",
  "Filter":
    "Filtrer",
  "Fix":
    "Corriger",
  "Follow live again":
    "Suivre à nouveau en direct",
  "Forget":
    "Oublier",
  "Forget device":
    "Oublier l’appareil",
  "Forget {name}?":
    "Oublier {name} ?",
  "Found in your folders":
    "Trouvés dans vos dossiers",
  "Free":
    "Gratuit",
  "Free again: {dates}":
    "De nouveau libres : {dates}",
  "From other tools":
    "D’autres outils",
  "Full log:":
    "Journal complet :",
  "Go to device":
    "Aller à l’appareil",
  "Hello, {name}!":
    "Bonjour, {name} !",
  "How ModStaller behaves on this computer.":
    "Comment ModStaller se comporte sur cet ordinateur.",
  "In the background":
    "En arrière-plan",
  "Install":
    "Installer",
  "Install app":
    "Installer une application",
  "Install updates automatically":
    "Installer les mises à jour automatiquement",
  "Install {name}":
    "Installer {name}",
  "Installed through your package manager ({name}) – updates come from there.":
    "Installé via votre gestionnaire de paquets ({name}) – les mises à jour viennent de là.",
  "Installed user apps":
    "Apps utilisateur installées",
  "Installing ModStaller…":
    "Installation de ModStaller…",
  "Is everything here that ModStaller needs?":
    "Tout ce dont ModStaller a besoin est-il présent ?",
  "It becomes the active account for new installs. Apps keep renewing with the account that installed them.":
    "Il devient le compte actif pour les nouvelles installations. Les apps continuent d’être renouvelées avec le compte qui les a installées.",
  "It is installed but stopped. Windows asks for confirmation once when it is started.":
    "Il est installé, mais arrêté. Windows demande une confirmation au démarrage.",
  "JIT and the Developer Disk Image still need the cable on this iOS version (Wi-Fi needs iOS 17.4 or newer for that).":
    "Le JIT et la Developer Disk Image nécessitent encore le câble sur cette version d’iOS (en Wi-Fi, il faut iOS 17.4 ou plus récent).",
  "JIT for {name}":
    "JIT pour {name}",
  "Keep running in the tray when closed":
    "Rester dans la barre système à la fermeture",
  "Keep that screen open and pick the Apple TV below.":
    "Gardez cet écran ouvert et choisissez l’Apple TV ci-dessous.",
  "Keyboard":
    "Clavier",
  "Language":
    "Langue",
  "Leave out all extensions":
    "Omettre toutes les extensions",
  "Leaving the beta channel keeps the installed beta until a newer stable version is out.":
    "En quittant le canal bêta, la bêta installée est conservée jusqu’à la sortie d’une version stable plus récente.",
  "List apps":
    "Lister les apps",
  "Live":
    "En direct",
  "Log":
    "Journal",
  "Log file":
    "Fichier journal",
  "Log file not found.":
    "Fichier journal introuvable.",
  "Log in":
    "Journal dans",
  "Looking for updates …":
    "Recherche de mises à jour …",
  "Looking in the network …":
    "Recherche sur le réseau …",
  "Make active":
    "Rendre actif",
  "Manage App IDs ({count})":
    "Gérer les identifiants d’app ({count})",
  "Manage all":
    "Tout gérer",
  "Microsoft Store":
    "Microsoft Store",
  "ModStaller Setup":
    "Installation de ModStaller",
  "ModStaller can stay in the tray, remind you before apps expire and renew them on its own. Renewing needs your iPhone connected via USB.":
    "ModStaller peut rester dans la barre système, vous rappeler l’expiration des apps et les renouveler tout seul. Le renouvellement nécessite que votre iPhone soit branché en USB.",
  "ModStaller forgets the device and its pairing. Over the cable it shows up again; an Apple TV has to be paired again with a PIN.":
    "ModStaller oublie l’appareil et son jumelage. Par câble, il réapparaît ; une Apple TV doit être jumelée à nouveau avec un code PIN.",
  "ModStaller is starting …":
    "ModStaller démarre …",
  "ModStaller was removed.":
    "ModStaller a été supprimé.",
  "ModStaller {version} is already installed.":
    "ModStaller {version} est déjà installé.",
  "ModStaller {version} is installed.":
    "ModStaller {version} est installé.",
  "Must be unique at Apple. Empty: ModStaller picks one that fits your team.":
    "Doit être unique chez Apple. Vide : ModStaller en choisit un adapté à votre équipe.",
  "Name on the home screen":
    "Nom sur l’écran d’accueil",
  "New icon – cropped to a square.":
    "Nouvelle icône – recadrée en carré.",
  "New installs sign with the active account. Renewals always use the account that installed the app.":
    "Les nouvelles installations sont signées avec le compte actif. Les renouvellements utilisent toujours le compte qui a installé l’app.",
  "Next: turn on Developer Mode on the Apple TV (Settings › Privacy & Security), then install the tvOS version of an app.":
    "Ensuite : activez le mode développeur sur l’Apple TV (Réglages › Confidentialité et sécurité), puis installez la version tvOS d’une app.",
  "No Apple TV found. Is the pairing screen open and the Apple TV in the same network?":
    "Aucune Apple TV trouvée. L’écran de jumelage est-il ouvert et l’Apple TV sur le même réseau ?",
  "No IPAs in Downloads, Documents or Desktop.":
    "Aucun IPA dans Téléchargements, Documents ou Bureau.",
  "No app installed yet":
    "Aucune application installée pour l’instant",
  "No certificates in the account.":
    "Aucun certificat dans le compte.",
  "No device":
    "Aucun appareil",
  "No device connected – plug the iPhone in via USB and unlock it, or bring it into the same Wi-Fi.":
    "Aucun appareil connecté – branchez l’iPhone en USB et déverrouillez-le, ou mettez-le sur le même Wi-Fi.",
  "No device connected. Plug the iPhone in via USB and unlock it – or bring it into the same Wi-Fi.":
    "Aucun appareil connecté. Branchez l’iPhone en USB et déverrouillez-le – ou mettez-le sur le même Wi-Fi.",
  "No entries for this filter.":
    "Aucune entrée pour ce filtre.",
  "No installed app belongs to this App ID right now.":
    "Aucune application installée ne dépend actuellement de cet identifiant d’app.",
  "No messages yet.":
    "Pas encore de messages.",
  "No new App ID needed – the ones this install uses already exist.":
    "Aucun nouvel App ID nécessaire – ceux utilisés existent déjà.",
  "No tray icon available. Reminders and renewals still work; start ModStaller again to open the window.":
    "Aucune icône de barre système disponible. Les rappels et renouvellements fonctionnent quand même ; relancez ModStaller pour ouvrir la fenêtre.",
  "Not checked yet.":
    "Pas encore vérifié.",
  "Not connected":
    "Non connecté",
  "Not signed in":
    "Non connecté",
  "Not signed in with Apple.":
    "Non connecté à Apple.",
  "Nothing found – everything on the iPhone comes from the store or from ModStaller.":
    "Rien trouvé – tout ce qui est sur l’iPhone vient de l’App Store ou de ModStaller.",
  "Nothing has happened yet.":
    "Rien ne s'est encore passé.",
  "Nothing has happened yet. As soon as you plug in an iPhone or install something, it shows up here.":
    "Rien ne s'est encore passé. Dès que vous branchez un iPhone ou installez quelque chose, cela apparaît ici.",
  "Nothing installed through ModStaller yet.":
    "Rien d’installé via ModStaller pour l’instant.",
  "Nothing is due right now":
    "Rien n’arrive à échéance",
  "Nothing was due.":
    "Rien n’était à renouveler.",
  "Notifications":
    "Notifications",
  "On the Apple TV open Settings › Remotes and Devices › Remote App and Devices.":
    "Sur l’Apple TV, ouvrez Réglages › Télécommandes et appareils › App Télécommande et appareils.",
  "One click fixes it – see above.":
    "Un clic suffit – voir ci-dessus.",
  "Only for installed copies and the AppImage - not in development builds.":
    "Uniquement pour les copies installées et l’AppImage – pas dans les builds de développement.",
  "Only for your user – no administrator rights needed. Your sign-ins and settings stay where they are.":
    "Uniquement pour votre utilisateur – sans droits d’administrateur. Vos connexions et réglages restent où ils sont.",
  "Optional – empty fields keep what the IPA says.":
    "Facultatif – les champs vides gardent ce que contient l’IPA.",
  "Original icon":
    "Icône d’origine",
  "Overview":
    "Vue d’ensemble",
  "PIN from the Apple TV":
    "Code PIN de l’Apple TV",
  "Paid":
    "Payant",
  "Paid account – no weekly limit on App IDs and no limit on apps.":
    "Compte payant – pas de limite hebdomadaire d’App ID ni de limite d’apps.",
  "Pair":
    "Jumeler",
  "Pair Apple TV":
    "Jumeler une Apple TV",
  "Pair {name}":
    "Jumeler {name}",
  "Paired by PIN – reachable while the Apple TV is on and in the same network.":
    "Jumelée par code PIN – joignable tant que l’Apple TV est allumée et sur le même réseau.",
  "Password":
    "Mot de passe",
  "Pause":
    "Pause",
  "Paused":
    "En pause",
  "Photo editing":
    "Retouche photo",
  "Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.":
    "Choisissez un IPA – ModStaller le signe avec votre compte Apple et l’installe sur l’iPhone.",
  "Plug it in via USB and unlock it – or bring it into the same Wi-Fi.":
    "Branchez-le en USB et déverrouillez-le – ou mettez-le sur le même Wi-Fi.",
  "Preparing Anisette …":
    "Préparation d’Anisette …",
  "Program":
    "Programme",
  "Read again":
    "Relire",
  "Reading the IPA …":
    "Lecture de l’IPA …",
  "Receive beta versions":
    "Recevoir les versions bêta",
  "Recent activity":
    "Activité récente",
  "Refresh":
    "Actualiser",
  "Registered devices":
    "Appareils enregistrés",
  "Reload":
    "Recharger",
  "Remind me before apps expire":
    "Me rappeler avant l’expiration des apps",
  "Remove":
    "Retirer",
  "Remove from the device":
    "Supprimer de l’appareil",
  "Remove {name}":
    "Retirer {name}",
  "Remove {name}?":
    "Retirer {name} ?",
  "Removes the program, the start menu entry and the `modstaller` command.":
    "Supprime le programme, l’entrée du menu et la commande `modstaller`.",
  "Removing ModStaller…":
    "Suppression de ModStaller…",
  "Renew":
    "Renouveler",
  "Renew apps automatically":
    "Renouveler les apps automatiquement",
  "Renew before it expires, from the overview or under “Apps”.":
    "Renouvelez avant l’expiration, depuis la vue d’ensemble ou sous « Applications ».",
  "Renew due":
    "Renouveler les échéances",
  "Renew due apps":
    "Renouveler les applications dues",
  "Renew now":
    "Renouveler maintenant",
  "Renew {name}":
    "Renouveler {name}",
  "Renewed {count} apps.":
    "{count} applications renouvelées.",
  "Renewing {name} in the background …":
    "Renouvellement de {name} en arrière-plan …",
  "Repair":
    "Réparer",
  "Restart":
    "Redémarrer",
  "Reuse an unused App ID …":
    "Réutiliser un App ID inutilisé…",
  "Revoke":
    "Révoquer",
  "Revoke certificate?":
    "Révoquer le certificat ?",
  "SRP-6a: Apple gets proof that you know the password – not the password itself.":
    "SRP-6a : Apple obtient la preuve que vous connaissez le mot de passe – pas le mot de passe lui-même.",
  "Safari":
    "Safari",
  "Screen broadcast":
    "Diffusion d’écran",
  "Search":
    "Rechercher",
  "Search again":
    "Rechercher à nouveau",
  "Set up automatically":
    "Configurer automatiquement",
  "Set up the Apple device service":
    "Configurer le service d’appareils Apple",
  "Settings":
    "Réglages",
  "Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.":
    "Réglages › Confidentialité et sécurité › Mode développeur – sinon aucune application sideloadée ne démarrera.",
  "Share":
    "Partage",
  "Show teams and certificates":
    "Afficher les équipes et certificats",
  "Sideloading for {platform}":
    "Sideloading pour {platform}",
  "Sideloads on the iPhone that do not come from ModStaller – from AltStore or SideStore, for instance. Renewing is not possible: the original IPA and the private key live with the other tool.":
    "Sideloads présents sur l’iPhone qui ne viennent pas de ModStaller – d’AltStore ou de SideStore, par exemple. Le renouvellement est impossible : l’IPA d’origine et la clé privée restent chez l’autre outil.",
  "Sign & install":
    "Signer et installer",
  "Sign in":
    "Se connecter",
  "Sign in once, then ModStaller signs by itself.":
    "Connectez-vous une fois, ensuite ModStaller signe tout seul.",
  "Sign in with Apple":
    "Se connecter avec Apple",
  "Sign out":
    "Se déconnecter",
  "Sign out?":
    "Se déconnecter ?",
  "Sign with":
    "Signer avec",
  "Signed by someone else":
    "Signé par un tiers",
  "Signed by {account}":
    "Signée par {account}",
  "Signed in":
    "Connecté",
  "Signed in.":
    "Connecté.",
  "Signed out.":
    "Déconnecté.",
  "Signed-in accounts":
    "Comptes connectés",
  "Siri & Shortcuts":
    "Siri et Raccourcis",
  "Source missing ({path}) – renewing is not possible.":
    "Source manquante ({path}) – renouvellement impossible.",
  "Stable channel":
    "Canal stable",
  "Stable versions are always offered. With the beta channel, pre-release versions (-beta.x) are offered as well.":
    "Les versions stables sont toujours proposées. Avec le canal bêta, les préversions (-beta.x) le sont aussi.",
  "Start ModStaller":
    "Lancer ModStaller",
  "Start an instance inside the app now (a game, for example) – only then does it ask for memory. The unlock applies to this launch of the app only.":
    "Lancez maintenant une instance dans l’application (un jeu, par exemple) – ce n’est qu’alors qu’elle demande de la mémoire. L’activation ne vaut que pour ce lancement.",
  "Start menu":
    "Menu",
  "Start service":
    "Démarrer le service",
  "Start with the system":
    "Démarrer avec le système",
  "Starting …":
    "Démarrage …",
  "Starts in the tray after you log in, without a window.":
    "Démarre dans la barre système après la connexion, sans fenêtre.",
  "Still to do: {what}":
    "Reste à faire : {what}",
  "Switch off Wi-Fi":
    "Désactiver le Wi-Fi",
  "Switch on Wi-Fi":
    "Activer le Wi-Fi",
  "Switch to this device":
    "Passer à cet appareil",
  "System":
    "Système",
  "System check":
    "Diagnostic",
  "System is ready – {count} step(s) still open.":
    "Le système est prêt – {count} étape(s) encore ouverte(s).",
  "Teams and certificates of {account}":
    "Équipes et certificats de {account}",
  "Terminal":
    "Terminal",
  "That image cannot be read.":
    "Impossible de lire cette image.",
  "That is not an IPA file.":
    "Ce n’est pas un fichier IPA.",
  "The Apple TV now shows a code on the screen. Type it in here.":
    "L’Apple TV affiche maintenant un code à l’écran. Saisissez-le ici.",
  "The Apple Watch app is removed – it cannot be installed this way.":
    "L’app Apple Watch est supprimée – elle ne peut pas être installée ainsi.",
  "The ModStaller service in the background has stopped":
    "Le service ModStaller en arrière-plan s’est arrêté",
  "The app and its data are deleted from the device. It comes from another tool – ModStaller cannot restore it.":
    "L’app et ses données sont supprimées de l’appareil. Elle provient d’un autre outil – ModStaller ne peut pas la restaurer.",
  "The app and its data are deleted from the device. That frees one of the three slots.":
    "L’app et ses données sont supprimées de l’appareil. Cela libère l’un des trois emplacements.",
  "The app runs under the unused App ID {id}.":
    "L’app utilise l’App ID inutilisé {id}.",
  "The backend did not report in.":
    "Le service de fond ne s’est pas manifesté.",
  "The backend has stopped.":
    "Le service de fond s’est arrêté.",
  "The bundle ID is not valid – letters, digits and hyphens, separated by dots.":
    "Le bundle ID n’est pas valide – lettres, chiffres et tirets, séparés par des points.",
  "The connected device.":
    "L’appareil connecté.",
  "The iPhone is plugged in but locked or not paired.":
    "L’iPhone est branché mais verrouillé ou non appairé.",
  "The next one frees up around {date}.":
    "Le prochain se libère vers le {date}.",
  "The session is discarded. Installed apps keep running but can only be renewed after signing in again.":
    "La session est abandonnée. Les applications installées continuent de fonctionner mais ne pourront être renouvelées qu’après une nouvelle connexion.",
  "There already is a different `modstaller` command in ~/.local/bin – it was left untouched.":
    "Il existe déjà une autre commande `modstaller` dans ~/.local/bin – elle n’a pas été modifiée.",
  "This IPA is App Store encrypted (FairPlay) and cannot be re-signed.":
    "Cet IPA est chiffré par l’App Store (FairPlay) et ne peut pas être re-signé.",
  "This IPA is an Apple TV app – pick the Apple TV as the device.":
    "Cette IPA est une app Apple TV – choisissez l’Apple TV comme appareil.",
  "This IPA is for iPhone and iPad – an Apple TV needs the app's tvOS version.":
    "Cette IPA est pour iPhone et iPad – une Apple TV a besoin de la version tvOS de l’app.",
  "This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself.":
    "Cela ne rend aucun quota hebdomadaire : Apple compte les identifiants d’app nouvellement créés, pas ceux qui existent. Quand la fenêtre est pleine, ModStaller bascule de lui-même sur un identifiant libre.",
  "This install needs {cost} – {missing} more than are left.":
    "Cette installation en nécessite {cost} – {missing} de plus que ce qui reste.",
  "This install uses {cost} of them.":
    "Cette installation en utilise {cost}.",
  "To renew, unlock or remove, the iPhone has to be connected and unlocked.":
    "Pour renouveler, activer ou retirer, l’iPhone doit être branché et déverrouillé.",
  "Translations that are missing fall back to English.":
    "Les traductions manquantes reviennent à l’anglais.",
  "Try again":
    "Réessayer",
  "Turn on":
    "Activer",
  "Type in the PIN the Apple TV then shows.":
    "Saisissez le code PIN que l’Apple TV affiche alors.",
  "Undo":
    "Annuler",
  "Undo changes":
    "Annuler les modifications",
  "Uninstall":
    "Désinstaller",
  "Uninstall now":
    "Désinstaller maintenant",
  "Unlock the iPhone and confirm “Trust”.":
    "Déverrouillez l’iPhone et confirmez « Se fier ».",
  "Unplug the iPhone and plug it in again.":
    "Débranchez l’iPhone et rebranchez-le.",
  "Unused ones are reused automatically when the weekly quota is used up – or pick one yourself when installing.":
    "Les inutilisés sont réutilisés automatiquement quand le quota hebdomadaire est épuisé – ou choisissez-en un lors de l’installation.",
  "Up to date – no newer version on GitHub.":
    "À jour – aucune version plus récente sur GitHub.",
  "Update check failed: {message}":
    "Échec de la vérification des mises à jour : {message}",
  "Update to {version}":
    "Mettre à jour vers {version}",
  "Updates":
    "Mises à jour",
  "VPN / network":
    "VPN / réseau",
  "Version {version} for Linux":
    "Version {version} pour Linux",
  "Version {version} is available":
    "La version {version} est disponible",
  "Version {version} is available – see bottom left.":
    "La version {version} est disponible – voir en bas à gauche.",
  "Version {version} is ready":
    "La version {version} est prête",
  "Version {version} · Apple TV · from tvOS {os}":
    "Version {version} · Apple TV · à partir de tvOS {os}",
  "Version {version} · from iOS {ios}":
    "Version {version} · à partir d’iOS {ios}",
  "View quotas and certificates":
    "Voir les quotas et les certificats",
  "Wait for the running task first":
    "Attendez d’abord la fin de la tâche en cours",
  "Warnings":
    "Avertissements",
  "What ModStaller does – live. The complete history is in the log file.":
    "Ce que fait ModStaller – en direct. L'historique complet se trouve dans le fichier journal.",
  "What ModStaller has installed. Free accounts: at most 3 apps, valid for 7 days each.":
    "Ce que ModStaller a installé. Comptes gratuits : 3 applications au maximum, valables 7 jours chacune.",
  "What's new?":
    "Quoi de neuf ?",
  "Where ModStaller is installed":
    "Où ModStaller est installé",
  "Whether an app depends on it cannot be determined without a connected iPhone.":
    "Impossible de déterminer si une application en dépend sans iPhone connecté.",
  "Wi-Fi":
    "Wi-Fi",
  "Wi-Fi is off. The iPhone is only reachable over the cable again.":
    "Le Wi-Fi est désactivé. L’iPhone n’est de nouveau joignable que par câble.",
  "Wi-Fi is on. The iPhone can now be unplugged – ModStaller finds it in the same network.":
    "Le Wi-Fi est activé. L’iPhone peut maintenant être débranché – ModStaller le trouve sur le même réseau.",
  "Widget":
    "Widget",
  "Windows shows the iPhone in Explorer through its own photo driver – ModStaller needs Apple’s device service for USB. ModStaller can set it up for you: “Apple Devices” from the Microsoft Store, otherwise just Apple’s USB driver.":
    "Windows affiche l’iPhone dans l’Explorateur via son propre pilote photo – ModStaller a besoin du service d’appareils d’Apple pour l’USB. ModStaller peut le configurer pour vous : « Appareils Apple » depuis le Microsoft Store, sinon seulement le pilote USB d’Apple.",
  "Without a connected iPhone it cannot be said which App IDs are in use right now – apps of other tools depend on them too.":
    "Sans iPhone connecté, impossible de dire quels identifiants d’app sont utilisés – des applications d’autres outils en dépendent aussi.",
  "You find it in the start menu. You can remove it again by running this setup once more.":
    "Vous le trouverez dans le menu. Pour le supprimer, relancez simplement ce programme d’installation.",
  "Your Apple account signs the apps. The password is never stored or transmitted.":
    "Votre compte Apple signe les applications. Le mot de passe n’est jamais enregistré ni transmis.",
  "Your apps":
    "Vos applications",
  "Your sign-ins and settings were kept.":
    "Vos connexions et réglages ont été conservés.",
  "and {count} more":
    "et {count} de plus",
  "days before expiry":
    "jours avant l’expiration",
  "expired":
    "expiré",
  "expires {date}":
    "expire le {date}",
  "expires – {when}":
    "expire – {when}",
  "extensions":
    "extensions",
  "frameworks":
    "frameworks",
  "free":
    "libre",
  "has expired":
    "a expiré",
  "hours before expiry. If your iPhone is not connected then, ModStaller asks for it and renews as soon as it is.":
    "heures avant l’expiration. Si votre iPhone n’est pas branché à ce moment-là, ModStaller le demande et renouvelle dès qu’il l’est.",
  "in use":
    "utilisé",
  "injected dylibs":
    "dylibs injectées",
  "just now":
    "à l’instant",
  "off":
    "désactivé",
  "on":
    "activé",
  "or":
    "ou",
  "yesterday":
    "hier",
  "{account} now signs new installs.":
    "{account} signe désormais les nouvelles installations.",
  "{available} of {max} left":
    "{available} sur {max} disponibles",
  "{count} accounts signed in":
    "{count} comptes connectés",
  "{count} day left":
    "encore {count} jour",
  "{count} days ago":
    "il y a {count} jours",
  "{count} days left":
    "encore {count} jours",
  "{count} entries copied.":
    "{count} entrées copiées.",
  "{count} free":
    "{count} libre(s)",
  "{count} h ago":
    "il y a {count} h",
  "{count} hour left":
    "encore {count} heure",
  "{count} hours left":
    "encore {count} heures",
  "{count} new":
    "{count} nouvelles",
  "{count} new App ID(s) created.":
    "{count} nouvel(s) App ID créé(s).",
  "{count} point(s) prevent sideloading.":
    "{count} point(s) empêchent le sideloading.",
  "{count} point(s) to clear up.":
    "{count} point(s) à régler.",
  "{kind} via {via}":
    "{kind} via {via}",
  "{minutes} min ago":
    "il y a {minutes} min",
  "{name} is being renewed in the background. Try again in a moment.":
    "{name} est en cours de renouvellement en arrière-plan. Réessayez dans un instant.",
  "{name} is installed and runs for {days} days.":
    "{name} est installée et fonctionne {days} jours.",
  "{name} is paired.":
    "{name} est jumelée.",
  "{name} was removed from the device.":
    "{name} a été supprimée de l’appareil.",
  "{name} was renewed – valid for {days} days again.":
    "{name} a été renouvelée – de nouveau valable {days} jours.",
  "{percent}% transferred":
    "{percent}% transférés",
  "{used} of {max} used":
    "{used} sur {max} utilisés",
  "~/.local/bin is not on your PATH yet – the `modstaller` command works in the terminal after logging in again.":
    "~/.local/bin n’est pas encore dans votre PATH – la commande `modstaller` fonctionnera dans le terminal après une nouvelle connexion.",
};

export default dict;
