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
  "App ID deleted.":
    "Identifiant d’app supprimé.",
  "App IDs in the account":
    "Identifiants d’app du compte",
  "App extensions were removed to save App IDs.":
    "Les extensions ont été retirées pour économiser des identifiants d’app.",
  "Apple account":
    "Compte Apple",
  "Apple allows only a few at a time. A foreign one (from AltStore or SideStore, say) cannot be used by ModStaller – its private key lives with the tool that requested it.":
    "Apple n’en autorise que quelques-uns à la fois. Un certificat étranger (d’AltStore ou de SideStore, par exemple) est inutilisable par ModStaller – sa clé privée reste chez l’outil qui l’a demandé.",
  "Apple allows {max} <b>newly created</b> ones per week. Existing ones do not count – deleting therefore gives back no quota. When the window is full, ModStaller reuses a free one.":
    "Apple en autorise {max} <b>nouvellement créés</b> par semaine. Les existants ne comptent pas – supprimer ne rend donc aucun quota. Quand la fenêtre est pleine, ModStaller réutilise un identifiant libre.",
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
  "Asking Apple – this takes a few seconds …":
    "Interrogation d’Apple – cela prend quelques secondes …",
  "Automatic updates exist only in the AppImage and in the Windows version installed with the setup.":
    "Les mises à jour automatiques n’existent que dans l’AppImage et dans la version Windows installée avec le programme d’installation.",
  "Back":
    "Retour",
  "Backend not reachable":
    "Service de fond injoignable",
  "Battery {level} %":
    "Batterie {level} %",
  "Beta channel":
    "Canal bêta",
  "Beta versions bring new features earlier, but they can be unstable and contain bugs.":
    "Les versions bêta apportent les nouveautés plus tôt, mais peuvent être instables et contenir des bugs.",
  "Beta – may be unstable":
    "Bêta – peut être instable",
  "Bundle ID {id} · transport: {transport}":
    "Bundle ID {id} · transport : {transport}",
  "Cancel":
    "Annuler",
  "Cancelled":
    "Annulé",
  "Cancelled.":
    "Annulé.",
  "Certificate revoked.":
    "Certificat révoqué.",
  "Charging … {level} %":
    "En charge – {level} %",
  "Check again":
    "Vérifier à nouveau",
  "Check for updates":
    "Rechercher des mises à jour",
  "Checking …":
    "Vérification …",
  "Choose a file":
    "Choisir un fichier",
  "Close":
    "Fermer",
  "Confirm":
    "Confirmer",
  "Confirmation code":
    "Code de confirmation",
  "Connected but not ready":
    "Connecté mais pas prêt",
  "Connected but not ready – unlock the iPhone and confirm “Trust”.":
    "Connecté mais pas prêt – déverrouillez l’iPhone et confirmez « Se fier ».",
  "Copy":
    "Copier",
  "Copying is not possible.":
    "Impossible de copier.",
  "Costs {count} App ID(s) from the weekly quota (10 per week on free accounts). The app itself runs without them.":
    "Coûte {count} identifiant(s) d’app du quota hebdomadaire (10 par semaine sur les comptes gratuits). L’application fonctionne aussi sans.",
  "Create a desktop shortcut":
    "Créer un raccourci sur le bureau",
  "Data in":
    "Données dans",
  "Delete":
    "Supprimer",
  "Delete App ID":
    "Supprimer l’identifiant d’app",
  "Delete App ID?":
    "Supprimer l’identifiant d’app ?",
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
  "Different IPA":
    "Autre IPA",
  "Done":
    "Terminé",
  "Download":
    "Télécharger",
  "Drag an IPA here":
    "Glissez un IPA ici",
  "Drag an IPA into the window or pick one from your Downloads.":
    "Glissez un IPA dans la fenêtre ou choisissez-en un dans vos téléchargements.",
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
  "Failed":
    "Échec",
  "Filter":
    "Filtrer",
  "Fix":
    "Corriger",
  "Follow live again":
    "Suivre à nouveau en direct",
  "Found in your folders":
    "Trouvés dans vos dossiers",
  "Free":
    "Gratuit",
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
  "Install {name}":
    "Installer {name}",
  "Installing ModStaller…":
    "Installation de ModStaller…",
  "Is everything here that ModStaller needs?":
    "Tout ce dont ModStaller a besoin est-il présent ?",
  "It becomes the active account for new installs. Apps keep renewing with the account that installed them.":
    "Il devient le compte actif pour les nouvelles installations. Les apps continuent d’être renouvelées avec le compte qui les a installées.",
  "It is installed but stopped. Windows asks for confirmation once when it is started.":
    "Il est installé, mais arrêté. Windows demande une confirmation au démarrage.",
  "JIT for {name}":
    "JIT pour {name}",
  "Keep extensions":
    "Conserver les extensions",
  "Language":
    "Langue",
  "Leaving the beta channel keeps the installed beta until a newer stable version is out.":
    "En quittant le canal bêta, la bêta installée est conservée jusqu’à la sortie d’une version stable plus récente.",
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
  "ModStaller is starting …":
    "ModStaller démarre …",
  "ModStaller was removed.":
    "ModStaller a été supprimé.",
  "ModStaller {version} is already installed.":
    "ModStaller {version} est déjà installé.",
  "ModStaller {version} is installed.":
    "ModStaller {version} est installé.",
  "New installs sign with the active account. Renewals always use the account that installed the app.":
    "Les nouvelles installations sont signées avec le compte actif. Les renouvellements utilisent toujours le compte qui a installé l’app.",
  "No IPAs in Downloads, Documents or Desktop.":
    "Aucun IPA dans Téléchargements, Documents ou Bureau.",
  "No app installed yet":
    "Aucune application installée pour l’instant",
  "No certificates in the account.":
    "Aucun certificat dans le compte.",
  "No entries for this filter.":
    "Aucune entrée pour ce filtre.",
  "No iPhone":
    "Aucun iPhone",
  "No iPhone connected – plug it in via USB and unlock it.":
    "Aucun iPhone connecté – branchez-le en USB et déverrouillez-le.",
  "No iPhone connected. Plug it in via USB and unlock it.":
    "Aucun iPhone connecté. Branchez-le en USB et déverrouillez-le.",
  "No installed app belongs to this App ID right now.":
    "Aucune application installée ne dépend actuellement de cet identifiant d’app.",
  "No messages yet.":
    "Pas encore de messages.",
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
  "One click fixes it – see above.":
    "Un clic suffit – voir ci-dessus.",
  "Only for your user – no administrator rights needed. Your sign-ins and settings stay where they are.":
    "Uniquement pour votre utilisateur – sans droits d’administrateur. Vos connexions et réglages restent où ils sont.",
  "Overview":
    "Vue d’ensemble",
  "Paid":
    "Payant",
  "Password":
    "Mot de passe",
  "Pause":
    "Pause",
  "Paused":
    "En pause",
  "Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.":
    "Choisissez un IPA – ModStaller le signe avec votre compte Apple et l’installe sur l’iPhone.",
  "Plug it in via USB and unlock it.":
    "Branchez-le en USB et déverrouillez-le.",
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
  "Remove":
    "Retirer",
  "Remove from the iPhone":
    "Retirer de l’iPhone",
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
  "Repair":
    "Réparer",
  "Restart":
    "Redémarrer",
  "Revoke":
    "Révoquer",
  "Revoke certificate?":
    "Révoquer le certificat ?",
  "SRP-6a: Apple gets proof that you know the password – not the password itself.":
    "SRP-6a : Apple obtient la preuve que vous connaissez le mot de passe – pas le mot de passe lui-même.",
  "Search":
    "Rechercher",
  "Set up automatically":
    "Configurer automatiquement",
  "Set up the Apple device service":
    "Configurer le service d’appareils Apple",
  "Settings":
    "Réglages",
  "Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.":
    "Réglages › Confidentialité et sécurité › Mode développeur – sinon aucune application sideloadée ne démarrera.",
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
  "Starting …":
    "Démarrage …",
  "Still to do: {what}":
    "Reste à faire : {what}",
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
  "That is not an IPA file.":
    "Ce n’est pas un fichier IPA.",
  "The ModStaller service in the background has stopped":
    "Le service ModStaller en arrière-plan s’est arrêté",
  "The app and its data are deleted from the iPhone. It comes from another tool – ModStaller cannot restore it.":
    "L’application et ses données sont supprimées de l’iPhone. Elle vient d’un autre outil – ModStaller ne peut pas la restaurer.",
  "The app and its data are deleted from the iPhone. That frees one of the three slots.":
    "L’application et ses données sont supprimées de l’iPhone. Cela libère l’un des trois emplacements.",
  "The backend did not report in.":
    "Le service de fond ne s’est pas manifesté.",
  "The backend has stopped.":
    "Le service de fond s’est arrêté.",
  "The connected iPhone.":
    "L’iPhone connecté.",
  "The iPhone is plugged in but locked or not paired.":
    "L’iPhone est branché mais verrouillé ou non appairé.",
  "The session is discarded. Installed apps keep running but can only be renewed after signing in again.":
    "La session est abandonnée. Les applications installées continuent de fonctionner mais ne pourront être renouvelées qu’après une nouvelle connexion.",
  "There already is a different `modstaller` command in ~/.local/bin – it was left untouched.":
    "Il existe déjà une autre commande `modstaller` dans ~/.local/bin – elle n’a pas été modifiée.",
  "This IPA is App Store encrypted (FairPlay) and cannot be re-signed.":
    "Cet IPA est chiffré par l’App Store (FairPlay) et ne peut pas être re-signé.",
  "This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself.":
    "Cela ne rend aucun quota hebdomadaire : Apple compte les identifiants d’app nouvellement créés, pas ceux qui existent. Quand la fenêtre est pleine, ModStaller bascule de lui-même sur un identifiant libre.",
  "To renew, unlock or remove, the iPhone has to be connected and unlocked.":
    "Pour renouveler, activer ou retirer, l’iPhone doit être branché et déverrouillé.",
  "Translations that are missing fall back to English.":
    "Les traductions manquantes reviennent à l’anglais.",
  "Try again":
    "Réessayer",
  "Turn on":
    "Activer",
  "Uninstall":
    "Désinstaller",
  "Uninstall now":
    "Désinstaller maintenant",
  "Unlock the iPhone and confirm “Trust”.":
    "Déverrouillez l’iPhone et confirmez « Se fier ».",
  "Unplug the iPhone and plug it in again.":
    "Débranchez l’iPhone et rebranchez-le.",
  "Up to date – no newer version on GitHub.":
    "À jour – aucune version plus récente sur GitHub.",
  "Update check failed: {message}":
    "Échec de la vérification des mises à jour : {message}",
  "Update to {version}":
    "Mettre à jour vers {version}",
  "Updates":
    "Mises à jour",
  "Version {version} for Linux":
    "Version {version} pour Linux",
  "Version {version} is available":
    "La version {version} est disponible",
  "Version {version} is available – see bottom left.":
    "La version {version} est disponible – voir en bas à gauche.",
  "Version {version} is ready":
    "La version {version} est prête",
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
  "iPhone, sign-in and what expires soon – at a glance.":
    "iPhone, connexion et ce qui expire bientôt – en un coup d’œil.",
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
  "{count} point(s) prevent sideloading.":
    "{count} point(s) empêchent le sideloading.",
  "{count} point(s) to clear up.":
    "{count} point(s) à régler.",
  "{minutes} min ago":
    "il y a {minutes} min",
  "{name} is installed and runs for {days} days.":
    "{name} est installée et fonctionne {days} jours.",
  "{name} was removed from the iPhone.":
    "{name} a été retirée de l’iPhone.",
  "{name} was renewed – valid for {days} days again.":
    "{name} a été renouvelée – de nouveau valable {days} jours.",
  "{percent}% transferred":
    "{percent}% transférés",
  "~/.local/bin is not on your PATH yet – the `modstaller` command works in the terminal after logging in again.":
    "~/.local/bin n’est pas encore dans votre PATH – la commande `modstaller` fonctionnera dans le terminal après une nouvelle connexion.",
};

export default dict;
