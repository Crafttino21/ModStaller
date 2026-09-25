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
  "Again":
    "Réessayer",
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
  "Bundle ID {id} · transport: {transport}":
    "Bundle ID {id} · transport : {transport}",
  "Cancel":
    "Annuler",
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
  "Costs {count} App ID(s) from the weekly quota (10 per week on free accounts). The app itself runs without them.":
    "Coûte {count} identifiant(s) d’app du quota hebdomadaire (10 par semaine sur les comptes gratuits). L’application fonctionne aussi sans.",
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
  "Drag an IPA here":
    "Glissez un IPA ici",
  "Drag an IPA into the window or pick one from your Downloads.":
    "Glissez un IPA dans la fenêtre ou choisissez-en un dans vos téléchargements.",
  "Enable JIT":
    "Activer le JIT",
  "Every app signed with it will no longer start – including those of other sideloading tools.":
    "Toutes les applications signées avec lui ne démarreront plus – y compris celles d’autres outils de sideloading.",
  "Everything ready for sideloading.":
    "Tout est prêt pour le sideloading.",
  "Everything ready.":
    "Tout est prêt.",
  "Filter":
    "Filtrer",
  "Fix":
    "Corriger",
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
  "How ModStaller behaves on this computer.":
    "Comment ModStaller se comporte sur cet ordinateur.",
  "Install":
    "Installer",
  "Install app":
    "Installer une application",
  "Install {name}":
    "Installer {name}",
  "Is everything here that ModStaller needs?":
    "Tout ce dont ModStaller a besoin est-il présent ?",
  "JIT for {name}":
    "JIT pour {name}",
  "Keep extensions":
    "Conserver les extensions",
  "Language":
    "Langue",
  "Log in":
    "Journal dans",
  "Looking for updates …":
    "Recherche de mises à jour …",
  "Manage App IDs ({count})":
    "Gérer les identifiants d’app ({count})",
  "Manage all":
    "Tout gérer",
  "ModStaller is starting …":
    "ModStaller démarre …",
  "No IPAs in Downloads, Documents or Desktop.":
    "Aucun IPA dans Téléchargements, Documents ou Bureau.",
  "No app installed yet":
    "Aucune application installée pour l’instant",
  "No certificates in the account.":
    "Aucun certificat dans le compte.",
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
  "Nothing installed through ModStaller yet.":
    "Rien d’installé via ModStaller pour l’instant.",
  "Nothing is due right now":
    "Rien n’arrive à échéance",
  "Nothing was due.":
    "Rien n’était à renouveler.",
  "Overview":
    "Vue d’ensemble",
  "Paid":
    "Payant",
  "Password":
    "Mot de passe",
  "Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.":
    "Choisissez un IPA – ModStaller le signe avec votre compte Apple et l’installe sur l’iPhone.",
  "Plug it in via USB and unlock it.":
    "Branchez-le en USB et déverrouillez-le.",
  "Preparing Anisette …":
    "Préparation d’Anisette …",
  "Read again":
    "Relire",
  "Reading the IPA …":
    "Lecture de l’IPA …",
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
  "Restart":
    "Redémarrer",
  "Revoke":
    "Révoquer",
  "Revoke certificate?":
    "Révoquer le certificat ?",
  "SRP-6a: Apple gets proof that you know the password – not the password itself.":
    "SRP-6a : Apple obtient la preuve que vous connaissez le mot de passe – pas le mot de passe lui-même.",
  "Settings":
    "Réglages",
  "Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.":
    "Réglages › Confidentialité et sécurité › Mode développeur – sinon aucune application sideloadée ne démarrera.",
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
  "Signed by someone else":
    "Signé par un tiers",
  "Signed in":
    "Connecté",
  "Signed in.":
    "Connecté.",
  "Signed out.":
    "Déconnecté.",
  "Source missing ({path}) – renewing is not possible.":
    "Source manquante ({path}) – renouvellement impossible.",
  "Start an instance inside the app now (a game, for example) – only then does it ask for memory. The unlock applies to this launch of the app only.":
    "Lancez maintenant une instance dans l’application (un jeu, par exemple) – ce n’est qu’alors qu’elle demande de la mémoire. L’activation ne vaut que pour ce lancement.",
  "Starting …":
    "Démarrage …",
  "Still to do: {what}":
    "Reste à faire : {what}",
  "System check":
    "Diagnostic",
  "System is ready – {count} step(s) still open.":
    "Le système est prêt – {count} étape(s) encore ouverte(s).",
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
  "This IPA is App Store encrypted (FairPlay) and cannot be re-signed.":
    "Cet IPA est chiffré par l’App Store (FairPlay) et ne peut pas être re-signé.",
  "This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself.":
    "Cela ne rend aucun quota hebdomadaire : Apple compte les identifiants d’app nouvellement créés, pas ceux qui existent. Quand la fenêtre est pleine, ModStaller bascule de lui-même sur un identifiant libre.",
  "To renew, unlock or remove, the iPhone has to be connected and unlocked.":
    "Pour renouveler, activer ou retirer, l’iPhone doit être branché et déverrouillé.",
  "Translations that are missing fall back to English.":
    "Les traductions manquantes reviennent à l’anglais.",
  "Turn on":
    "Activer",
  "Unlock the iPhone and confirm “Trust”.":
    "Déverrouillez l’iPhone et confirmez « Se fier ».",
  "Up to date – no newer version on GitHub.":
    "À jour – aucune version plus récente sur GitHub.",
  "Update check failed: {message}":
    "Échec de la vérification des mises à jour : {message}",
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
  "What ModStaller has installed. Free accounts: at most 3 apps, valid for 7 days each.":
    "Ce que ModStaller a installé. Comptes gratuits : 3 applications au maximum, valables 7 jours chacune.",
  "What's new?":
    "Quoi de neuf ?",
  "Whether an app depends on it cannot be determined without a connected iPhone.":
    "Impossible de déterminer si une application en dépend sans iPhone connecté.",
  "Without a connected iPhone it cannot be said which App IDs are in use right now – apps of other tools depend on them too.":
    "Sans iPhone connecté, impossible de dire quels identifiants d’app sont utilisés – des applications d’autres outils en dépendent aussi.",
  "Your Apple account signs the apps. The password is never stored or transmitted.":
    "Votre compte Apple signe les applications. Le mot de passe n’est jamais enregistré ni transmis.",
  "Your apps":
    "Vos applications",
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
  "{count} day left":
    "encore {count} jour",
  "{count} days ago":
    "il y a {count} jours",
  "{count} days left":
    "encore {count} jours",
  "{count} free":
    "{count} libre(s)",
  "{count} h ago":
    "il y a {count} h",
  "{count} hour left":
    "encore {count} heure",
  "{count} hours left":
    "encore {count} heures",
  "{count} point(s) prevent sideloading.":
    "{count} point(s) empêchent le sideloading.",
  "{count} point(s) to clear up.":
    "{count} point(s) à régler.",
  "{name} is installed and runs for {days} days.":
    "{name} est installée et fonctionne {days} jours.",
  "{name} was removed from the iPhone.":
    "{name} a été retirée de l’iPhone.",
  "{name} was renewed – valid for {days} days again.":
    "{name} a été renouvelée – de nouveau valable {days} jours.",
  "{percent}% transferred":
    "{percent}% transférés",
};

export default dict;
