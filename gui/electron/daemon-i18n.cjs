// Texte des Hintergrundbetriebs: Benachrichtigungen und Tray-Menue.
//
// Die Oberflaeche uebersetzt mit src/lib/locale/*.ts - die gibt es im
// Hauptprozess nicht, und mit --background laedt gar keine Seite. Also ein
// eigenes, kleines Woerterbuch. Schluessel ist der englische Text, wie in der
// Oberflaeche; was fehlt, bleibt Englisch.

const DICT = {
  de: {
    "{name} expires soon": "{name} läuft bald ab",
    "Valid for {left}. ModStaller renews it on the last day - keep the device on USB or in the same Wi-Fi then.":
      "Noch {left} gültig. ModStaller erneuert die App am letzten Tag – das Gerät sollte dann per USB oder im selben WLAN erreichbar sein.",
    "Valid for {left}. Open ModStaller to renew it.": "Noch {left} gültig. Öffne ModStaller, um die App zu erneuern.",
    "Device not reachable":
      "Gerät nicht erreichbar",
    "{names} must be renewed. Connect the device via USB or bring it into the same Wi-Fi - ModStaller does the rest.":
      "{names} muss erneuert werden. Schließ das Gerät per USB an oder bring es ins selbe WLAN – den Rest macht ModStaller.",
    "{name} cannot be renewed": "{name} kann nicht erneuert werden",
    "The original IPA is gone. Install the app again.": "Die ursprüngliche IPA fehlt. Installiere die App neu.",
    "The Apple account is not signed in. Open ModStaller and sign in.":
      "Der Apple-Account ist nicht angemeldet. Öffne ModStaller und melde dich an.",
    "Sign in again": "Erneut anmelden",
    "Apple wants you to sign in again before {name} can be renewed.":
      "Apple verlangt eine neue Anmeldung, bevor {name} erneuert werden kann.",
    "Renewing {name} failed": "Erneuern von {name} fehlgeschlagen",
    "{name} renewed": "{name} erneuert",
    "Valid until {date}.": "Gültig bis {date}.",
    "ModStaller updated": "ModStaller aktualisiert",
    "Now running version {version}.": "Jetzt läuft Version {version}.",
    "ModStaller keeps running": "ModStaller läuft weiter",
    "It renews your apps in the background. Quit it from the tray icon.":
      "Deine Apps werden im Hintergrund erneuert. Beenden kannst du über das Tray-Symbol.",
    "Nothing to renew": "Nichts zu erneuern",
    "No app can be renewed right now. Is the device connected via USB or in the same Wi-Fi?":
      "Gerade lässt sich keine App erneuern. Ist das Gerät per USB angeschlossen oder im selben WLAN?",
    "Open ModStaller": "ModStaller öffnen",
    "Renew now": "Jetzt erneuern",
    "Quit": "Beenden",
    "Next: {name} - {left}": "Als Nächstes: {name} – {left}",
    "No apps installed": "Keine Apps installiert",
    "Renewing {name} …": "Erneuere {name} …",
    "expired": "abgelaufen",
    "1 day": "1 Tag",
    "{n} days": "{n} Tage",
    "1 hour": "1 Stunde",
    "{n} hours": "{n} Stunden",
  },
  fr: {
    "{name} expires soon": "{name} expire bientôt",
    "Valid for {left}. ModStaller renews it on the last day - keep the device on USB or in the same Wi-Fi then.":
      "Encore valide {left}. ModStaller la renouvelle le dernier jour – l’appareil doit alors être branché en USB ou sur le même Wi-Fi.",
    "Valid for {left}. Open ModStaller to renew it.": "Encore valide {left}. Ouvrez ModStaller pour la renouveler.",
    "Device not reachable":
      "Appareil injoignable",
    "{names} must be renewed. Connect the device via USB or bring it into the same Wi-Fi - ModStaller does the rest.":
      "{names} doit être renouvelé. Branchez l’appareil en USB ou mettez-le sur le même Wi-Fi – ModStaller s’occupe du reste.",
    "{name} cannot be renewed": "Impossible de renouveler {name}",
    "The original IPA is gone. Install the app again.": "L’IPA d’origine a disparu. Réinstallez l’app.",
    "The Apple account is not signed in. Open ModStaller and sign in.":
      "Le compte Apple n’est pas connecté. Ouvrez ModStaller et connectez-vous.",
    "Sign in again": "Reconnectez-vous",
    "Apple wants you to sign in again before {name} can be renewed.":
      "Apple demande une nouvelle connexion avant de pouvoir renouveler {name}.",
    "Renewing {name} failed": "Échec du renouvellement de {name}",
    "{name} renewed": "{name} renouvelée",
    "Valid until {date}.": "Valide jusqu’au {date}.",
    "ModStaller updated": "ModStaller mis à jour",
    "Now running version {version}.": "Version {version} en cours d’exécution.",
    "ModStaller keeps running": "ModStaller reste actif",
    "It renews your apps in the background. Quit it from the tray icon.":
      "Il renouvelle vos apps en arrière-plan. Quittez-le depuis l’icône de la barre système.",
    "Nothing to renew": "Rien à renouveler",
    "No app can be renewed right now. Is the device connected via USB or in the same Wi-Fi?":
      "Aucune app ne peut être renouvelée pour l’instant. L’appareil est-il branché en USB ou sur le même Wi-Fi ?",
    "Open ModStaller": "Ouvrir ModStaller",
    "Renew now": "Renouveler maintenant",
    "Quit": "Quitter",
    "Next: {name} - {left}": "Prochaine : {name} – {left}",
    "No apps installed": "Aucune app installée",
    "Renewing {name} …": "Renouvellement de {name} …",
    "expired": "expirée",
    "1 day": "1 jour",
    "{n} days": "{n} jours",
    "1 hour": "1 heure",
    "{n} hours": "{n} heures",
  },
  es: {
    "{name} expires soon": "{name} caduca pronto",
    "Valid for {left}. ModStaller renews it on the last day - keep the device on USB or in the same Wi-Fi then.":
      "Válida {left} más. ModStaller la renueva el último día; el dispositivo debe estar entonces por USB o en la misma Wi-Fi.",
    "Valid for {left}. Open ModStaller to renew it.": "Válida {left} más. Abre ModStaller para renovarla.",
    "Device not reachable":
      "Dispositivo no disponible",
    "{names} must be renewed. Connect the device via USB or bring it into the same Wi-Fi - ModStaller does the rest.":
      "Hay que renovar {names}. Conecta el dispositivo por USB o ponlo en la misma Wi-Fi y ModStaller hace el resto.",
    "{name} cannot be renewed": "No se puede renovar {name}",
    "The original IPA is gone. Install the app again.": "Falta la IPA original. Vuelve a instalar la app.",
    "The Apple account is not signed in. Open ModStaller and sign in.":
      "La cuenta de Apple no tiene la sesión iniciada. Abre ModStaller e inicia sesión.",
    "Sign in again": "Vuelve a iniciar sesión",
    "Apple wants you to sign in again before {name} can be renewed.":
      "Apple pide iniciar sesión de nuevo antes de poder renovar {name}.",
    "Renewing {name} failed": "Error al renovar {name}",
    "{name} renewed": "{name} renovada",
    "Valid until {date}.": "Válida hasta el {date}.",
    "ModStaller updated": "ModStaller actualizado",
    "Now running version {version}.": "Ahora se ejecuta la versión {version}.",
    "ModStaller keeps running": "ModStaller sigue en marcha",
    "It renews your apps in the background. Quit it from the tray icon.":
      "Renueva tus apps en segundo plano. Ciérralo desde el icono de la bandeja.",
    "Nothing to renew": "Nada que renovar",
    "No app can be renewed right now. Is the device connected via USB or in the same Wi-Fi?":
      "Ahora mismo no se puede renovar ninguna app. ¿Está el dispositivo conectado por USB o en la misma Wi-Fi?",
    "Open ModStaller": "Abrir ModStaller",
    "Renew now": "Renovar ahora",
    "Quit": "Salir",
    "Next: {name} - {left}": "Siguiente: {name} – {left}",
    "No apps installed": "No hay apps instaladas",
    "Renewing {name} …": "Renovando {name} …",
    "expired": "caducada",
    "1 day": "1 día",
    "{n} days": "{n} días",
    "1 hour": "1 hora",
    "{n} hours": "{n} horas",
  },
  it: {
    "{name} expires soon": "{name} scade a breve",
    "Valid for {left}. ModStaller renews it on the last day - keep the device on USB or in the same Wi-Fi then.":
      "Valida ancora per {left}. ModStaller la rinnova l’ultimo giorno: il dispositivo dovrà essere collegato via USB o sulla stessa Wi-Fi.",
    "Valid for {left}. Open ModStaller to renew it.": "Valida ancora per {left}. Apri ModStaller per rinnovarla.",
    "Device not reachable":
      "Dispositivo non raggiungibile",
    "{names} must be renewed. Connect the device via USB or bring it into the same Wi-Fi - ModStaller does the rest.":
      "{names} va rinnovata. Collega il dispositivo via USB o portalo sulla stessa Wi-Fi, al resto pensa ModStaller.",
    "{name} cannot be renewed": "Impossibile rinnovare {name}",
    "The original IPA is gone. Install the app again.": "L’IPA originale non c’è più. Reinstalla l’app.",
    "The Apple account is not signed in. Open ModStaller and sign in.":
      "L’account Apple non ha effettuato l’accesso. Apri ModStaller e accedi.",
    "Sign in again": "Accedi di nuovo",
    "Apple wants you to sign in again before {name} can be renewed.":
      "Apple chiede un nuovo accesso prima di poter rinnovare {name}.",
    "Renewing {name} failed": "Rinnovo di {name} non riuscito",
    "{name} renewed": "{name} rinnovata",
    "Valid until {date}.": "Valida fino al {date}.",
    "ModStaller updated": "ModStaller aggiornato",
    "Now running version {version}.": "Ora è in esecuzione la versione {version}.",
    "ModStaller keeps running": "ModStaller resta attivo",
    "It renews your apps in the background. Quit it from the tray icon.":
      "Rinnova le tue app in background. Chiudilo dall’icona nell’area di notifica.",
    "Nothing to renew": "Niente da rinnovare",
    "No app can be renewed right now. Is the device connected via USB or in the same Wi-Fi?":
      "Al momento nessuna app può essere rinnovata. Il dispositivo è collegato via USB o sulla stessa Wi-Fi?",
    "Open ModStaller": "Apri ModStaller",
    "Renew now": "Rinnova ora",
    "Quit": "Esci",
    "Next: {name} - {left}": "Prossima: {name} – {left}",
    "No apps installed": "Nessuna app installata",
    "Renewing {name} …": "Rinnovo di {name} …",
    "expired": "scaduta",
    "1 day": "1 giorno",
    "{n} days": "{n} giorni",
    "1 hour": "1 ora",
    "{n} hours": "{n} ore",
  },
  "pt-BR": {
    "{name} expires soon": "{name} expira em breve",
    "Valid for {left}. ModStaller renews it on the last day - keep the device on USB or in the same Wi-Fi then.":
      "Válido por mais {left}. O ModStaller renova no último dia – o dispositivo precisa estar via USB ou na mesma Wi-Fi nesse dia.",
    "Valid for {left}. Open ModStaller to renew it.": "Válido por mais {left}. Abra o ModStaller para renovar.",
    "Device not reachable":
      "Dispositivo inacessível",
    "{names} must be renewed. Connect the device via USB or bring it into the same Wi-Fi - ModStaller does the rest.":
      "{names} precisa ser renovado. Conecte o dispositivo via USB ou coloque-o na mesma Wi-Fi e o ModStaller faz o resto.",
    "{name} cannot be renewed": "Não é possível renovar {name}",
    "The original IPA is gone. Install the app again.": "O IPA original sumiu. Instale o app novamente.",
    "The Apple account is not signed in. Open ModStaller and sign in.":
      "A conta Apple não está conectada. Abra o ModStaller e entre.",
    "Sign in again": "Entre novamente",
    "Apple wants you to sign in again before {name} can be renewed.":
      "A Apple pede um novo login antes de renovar {name}.",
    "Renewing {name} failed": "Falha ao renovar {name}",
    "{name} renewed": "{name} renovado",
    "Valid until {date}.": "Válido até {date}.",
    "ModStaller updated": "ModStaller atualizado",
    "Now running version {version}.": "Agora rodando a versão {version}.",
    "ModStaller keeps running": "O ModStaller continua rodando",
    "It renews your apps in the background. Quit it from the tray icon.":
      "Ele renova seus apps em segundo plano. Feche pelo ícone da bandeja.",
    "Nothing to renew": "Nada para renovar",
    "No app can be renewed right now. Is the device connected via USB or in the same Wi-Fi?":
      "Nenhum app pode ser renovado agora. O dispositivo está conectado via USB ou na mesma Wi-Fi?",
    "Open ModStaller": "Abrir ModStaller",
    "Renew now": "Renovar agora",
    "Quit": "Sair",
    "Next: {name} - {left}": "Próximo: {name} – {left}",
    "No apps installed": "Nenhum app instalado",
    "Renewing {name} …": "Renovando {name} …",
    "expired": "expirado",
    "1 day": "1 dia",
    "{n} days": "{n} dias",
    "1 hour": "1 hora",
    "{n} hours": "{n} horas",
  },
  nl: {
    "{name} expires soon": "{name} verloopt binnenkort",
    "Valid for {left}. ModStaller renews it on the last day - keep the device on USB or in the same Wi-Fi then.":
      "Nog {left} geldig. ModStaller vernieuwt de app op de laatste dag – het apparaat moet dan via USB of in hetzelfde wifi bereikbaar zijn.",
    "Valid for {left}. Open ModStaller to renew it.": "Nog {left} geldig. Open ModStaller om de app te vernieuwen.",
    "Device not reachable":
      "Apparaat niet bereikbaar",
    "{names} must be renewed. Connect the device via USB or bring it into the same Wi-Fi - ModStaller does the rest.":
      "{names} moet worden vernieuwd. Sluit het apparaat via USB aan of breng het in hetzelfde wifi – ModStaller doet de rest.",
    "{name} cannot be renewed": "{name} kan niet worden vernieuwd",
    "The original IPA is gone. Install the app again.": "De oorspronkelijke IPA is weg. Installeer de app opnieuw.",
    "The Apple account is not signed in. Open ModStaller and sign in.":
      "Het Apple-account is niet ingelogd. Open ModStaller en log in.",
    "Sign in again": "Opnieuw inloggen",
    "Apple wants you to sign in again before {name} can be renewed.":
      "Apple wil dat je opnieuw inlogt voordat {name} kan worden vernieuwd.",
    "Renewing {name} failed": "Vernieuwen van {name} mislukt",
    "{name} renewed": "{name} vernieuwd",
    "Valid until {date}.": "Geldig tot {date}.",
    "ModStaller updated": "ModStaller bijgewerkt",
    "Now running version {version}.": "Nu draait versie {version}.",
    "ModStaller keeps running": "ModStaller blijft actief",
    "It renews your apps in the background. Quit it from the tray icon.":
      "Je apps worden op de achtergrond vernieuwd. Afsluiten kan via het pictogram in het systeemvak.",
    "Nothing to renew": "Niets te vernieuwen",
    "No app can be renewed right now. Is the device connected via USB or in the same Wi-Fi?":
      "Er kan nu geen app worden vernieuwd. Is het apparaat via USB aangesloten of in hetzelfde wifi?",
    "Open ModStaller": "ModStaller openen",
    "Renew now": "Nu vernieuwen",
    "Quit": "Afsluiten",
    "Next: {name} - {left}": "Volgende: {name} – {left}",
    "No apps installed": "Geen apps geïnstalleerd",
    "Renewing {name} …": "{name} vernieuwen …",
    "expired": "verlopen",
    "1 day": "1 dag",
    "{n} days": "{n} dagen",
    "1 hour": "1 uur",
    "{n} hours": "{n} uur",
  },
};

/** Die passende Sprache: genau, sonst ohne Region (de-AT -> de), sonst null. */
function resolve(language) {
  if (!language) return null;
  if (DICT[language]) return language;
  const base = String(language).split("-")[0];
  return Object.keys(DICT).find((k) => k.split("-")[0] === base) ?? null;
}

function t(language, key, vars = {}) {
  const lang = resolve(language);
  const text = (lang && DICT[lang][key]) || key;
  return text.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? String(vars[name]) : m));
}

/** Wie lange noch: gerundete Tage, unter einem Tag Stunden. Gerundet, nicht
 *  abgeschnitten - "2 Tage" liest sich richtiger als "1 Tag" fuer 1,99. */
function left(language, ms) {
  if (ms <= 0) return t(language, "expired");
  const hours = Math.max(1, Math.round(ms / (3600 * 1000)));
  if (hours < 24) return hours === 1 ? t(language, "1 hour") : t(language, "{n} hours", { n: hours });
  const days = Math.round(ms / (24 * 3600 * 1000));
  return days === 1 ? t(language, "1 day") : t(language, "{n} days", { n: days });
}

/** Datum mit Uhrzeit in der Sprache der Oberflaeche. */
function date(language, ms) {
  try {
    return new Date(ms).toLocaleString(language || "en", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return new Date(ms).toLocaleString();
  }
}

module.exports = { DICT, resolve, t, left, date };
