// Espanol - Katalog der Oberflaeche.
//
// Schluessel ist der englische Quelltext (siehe lib/i18n.svelte.ts).
// Ein fehlender Eintrag faellt auf Englisch zurueck.

import type { Dict } from "../i18n.svelte";

const dict: Dict = {
  "(exit {code})":
    "(salida {code})",
  "<b>JIT</b> is needed by Java and emulator apps (Minecraft launchers, for example): ModStaller starts the app with a debugger attached and releases memory as soon as it asks for it.":
    "<b>JIT</b> lo necesitan las apps de Java y los emuladores (los lanzadores de Minecraft, por ejemplo): ModStaller inicia la app con un depurador adjunto y libera memoria en cuanto la pide.",
  "Account":
    "Cuenta",
  "Again":
    "Reintentar",
  "Also discard the device identity (Apple will then ask for a two-factor code again)":
    "Descartar también la identidad del dispositivo (Apple volverá a pedir un código de doble factor)",
  "An installed app belongs to it – from ModStaller or from another tool. After deleting, it can no longer be renewed.":
    "Hay una app instalada que depende de él: de ModStaller o de otra herramienta. Tras borrarlo ya no se podrá renovar.",
  "An instance has to be started inside the app while it waits – only then does it ask for memory.":
    "Hay que iniciar una instancia dentro de la app mientras espera: solo entonces pide memoria.",
  "An ordinary, free Apple ID is enough. Apple then asks for a code on your iPhone.":
    "Basta un ID de Apple normal y gratuito. Apple pedirá después un código en tu iPhone.",
  "Another operation is already running.":
    "Ya hay una operación en curso.",
  "App ID deleted.":
    "ID de app borrado.",
  "App IDs in the account":
    "ID de app en la cuenta",
  "App extensions were removed to save App IDs.":
    "Se quitaron las extensiones para ahorrar ID de app.",
  "Apple account":
    "Cuenta de Apple",
  "Apple allows only a few at a time. A foreign one (from AltStore or SideStore, say) cannot be used by ModStaller – its private key lives with the tool that requested it.":
    "Apple solo permite unos pocos a la vez. Uno ajeno (de AltStore o SideStore, por ejemplo) no le sirve a ModStaller: su clave privada está en la herramienta que lo pidió.",
  "Apple allows {max} <b>newly created</b> ones per week. Existing ones do not count – deleting therefore gives back no quota. When the window is full, ModStaller reuses a free one.":
    "Apple permite {max} <b>recién creados</b> por semana. Los existentes no cuentan, así que borrarlos no devuelve cuota. Cuando la ventana está llena, ModStaller reutiliza uno libre.",
  "Apple sent a six-digit code to your iPhone.":
    "Apple ha enviado un código de seis dígitos a tu iPhone.",
  "Applies to the whole program, including the messages that come from the background service.":
    "Vale para todo el programa, también para los mensajes del servicio en segundo plano.",
  "Applies to this launch only – unlock again after quitting the app.":
    "Vale solo para este arranque: vuelve a activarlo tras cerrar la app.",
  "Apps":
    "Apps",
  "Asking Apple – this takes a few seconds …":
    "Consultando a Apple: esto tarda unos segundos …",
  "Automatic updates exist only in the AppImage and in the Windows version installed with the setup.":
    "Las actualizaciones automáticas solo existen en la AppImage y en la versión de Windows instalada con el instalador.",
  "Back":
    "Atrás",
  "Backend not reachable":
    "Servicio de fondo inaccesible",
  "Battery {level} %":
    "Batería {level} %",
  "Bundle ID {id} · transport: {transport}":
    "Bundle ID {id} · transporte: {transport}",
  "Cancel":
    "Cancelar",
  "Certificate revoked.":
    "Certificado revocado.",
  "Charging … {level} %":
    "Cargando – {level} %",
  "Check again":
    "Comprobar de nuevo",
  "Check for updates":
    "Buscar actualizaciones",
  "Checking …":
    "Comprobando …",
  "Choose a file":
    "Elegir un archivo",
  "Close":
    "Cerrar",
  "Confirm":
    "Confirmar",
  "Confirmation code":
    "Código de confirmación",
  "Connected but not ready":
    "Conectado pero no listo",
  "Connected but not ready – unlock the iPhone and confirm “Trust”.":
    "Conectado pero no listo: desbloquea el iPhone y confirma «Confiar».",
  "Costs {count} App ID(s) from the weekly quota (10 per week on free accounts). The app itself runs without them.":
    "Cuesta {count} ID de app de la cuota semanal (10 por semana en cuentas gratuitas). La app funciona igual sin ellas.",
  "Data in":
    "Datos en",
  "Delete":
    "Borrar",
  "Delete App ID":
    "Borrar ID de app",
  "Delete App ID?":
    "¿Borrar el ID de app?",
  "Developer Mode is off.":
    "El modo de desarrollador está desactivado.",
  "Developer Mode off":
    "Modo de desarrollador desactivado",
  "Developer Mode on":
    "Modo de desarrollador activado",
  "Developer-signed":
    "Firmada por un desarrollador",
  "Development certificates":
    "Certificados de desarrollo",
  "Device":
    "Dispositivo",
  "Different IPA":
    "Otro IPA",
  "Drag an IPA here":
    "Arrastra un IPA aquí",
  "Drag an IPA into the window or pick one from your Downloads.":
    "Arrastra un IPA a la ventana o elige uno de tus descargas.",
  "Enable JIT":
    "Activar JIT",
  "Every app signed with it will no longer start – including those of other sideloading tools.":
    "Todas las apps firmadas con él dejarán de arrancar, también las de otras herramientas de sideloading.",
  "Everything ready for sideloading.":
    "Todo listo para el sideloading.",
  "Everything ready.":
    "Todo listo.",
  "Filter":
    "Filtrar",
  "Fix":
    "Arreglar",
  "Found in your folders":
    "Encontrados en tus carpetas",
  "Free":
    "Gratuita",
  "From other tools":
    "De otras herramientas",
  "Full log:":
    "Registro completo:",
  "Go to device":
    "Ir al dispositivo",
  "How ModStaller behaves on this computer.":
    "Cómo se comporta ModStaller en este ordenador.",
  "Install":
    "Instalar",
  "Install app":
    "Instalar app",
  "Install {name}":
    "Instalar {name}",
  "Is everything here that ModStaller needs?":
    "¿Está todo lo que ModStaller necesita?",
  "JIT for {name}":
    "JIT para {name}",
  "Keep extensions":
    "Conservar las extensiones",
  "Language":
    "Idioma",
  "Log in":
    "Registro en",
  "Looking for updates …":
    "Buscando actualizaciones …",
  "Manage App IDs ({count})":
    "Gestionar los ID de app ({count})",
  "Manage all":
    "Gestionar todo",
  "ModStaller is starting …":
    "ModStaller está arrancando …",
  "No IPAs in Downloads, Documents or Desktop.":
    "No hay IPA en Descargas, Documentos ni Escritorio.",
  "No app installed yet":
    "Todavía no hay ninguna app instalada",
  "No certificates in the account.":
    "No hay certificados en la cuenta.",
  "No iPhone":
    "Sin iPhone",
  "No iPhone connected – plug it in via USB and unlock it.":
    "No hay ningún iPhone conectado: conéctalo por USB y desbloquéalo.",
  "No iPhone connected. Plug it in via USB and unlock it.":
    "No hay ningún iPhone conectado. Conéctalo por USB y desbloquéalo.",
  "No installed app belongs to this App ID right now.":
    "Ahora mismo no hay ninguna app instalada que use este ID de app.",
  "No messages yet.":
    "Todavía no hay mensajes.",
  "Not checked yet.":
    "Aún sin comprobar.",
  "Not connected":
    "No conectado",
  "Not signed in":
    "No has iniciado sesión",
  "Not signed in with Apple.":
    "Sin sesión iniciada en Apple.",
  "Nothing found – everything on the iPhone comes from the store or from ModStaller.":
    "No se encontró nada: todo lo que hay en el iPhone viene de la tienda o de ModStaller.",
  "Nothing installed through ModStaller yet.":
    "Todavía no hay nada instalado con ModStaller.",
  "Nothing is due right now":
    "Ahora mismo no vence nada",
  "Nothing was due.":
    "No vencía nada.",
  "Overview":
    "Resumen",
  "Paid":
    "De pago",
  "Password":
    "Contraseña",
  "Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.":
    "Elige un IPA: ModStaller lo firma con tu cuenta de Apple y lo instala en el iPhone.",
  "Plug it in via USB and unlock it.":
    "Conéctalo por USB y desbloquéalo.",
  "Preparing Anisette …":
    "Preparando Anisette …",
  "Read again":
    "Volver a leer",
  "Reading the IPA …":
    "Leyendo el IPA …",
  "Refresh":
    "Actualizar",
  "Registered devices":
    "Dispositivos registrados",
  "Remove":
    "Quitar",
  "Remove from the iPhone":
    "Quitar del iPhone",
  "Remove {name}":
    "Quitar {name}",
  "Remove {name}?":
    "¿Quitar {name}?",
  "Renew":
    "Renovar",
  "Renew before it expires, from the overview or under “Apps”.":
    "Renuévala antes de que caduque, desde el resumen o en «Apps».",
  "Renew due":
    "Renovar las vencidas",
  "Renew due apps":
    "Renovar las apps vencidas",
  "Renew now":
    "Renovar ahora",
  "Renew {name}":
    "Renovar {name}",
  "Renewed {count} apps.":
    "{count} apps renovadas.",
  "Restart":
    "Reiniciar",
  "Revoke":
    "Revocar",
  "Revoke certificate?":
    "¿Revocar el certificado?",
  "SRP-6a: Apple gets proof that you know the password – not the password itself.":
    "SRP-6a: Apple obtiene la prueba de que conoces la contraseña, no la contraseña en sí.",
  "Settings":
    "Ajustes",
  "Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.":
    "Ajustes › Privacidad y seguridad › Modo de desarrollador – si no, no arrancará ninguna app con sideload.",
  "Sideloading for {platform}":
    "Sideloading para {platform}",
  "Sideloads on the iPhone that do not come from ModStaller – from AltStore or SideStore, for instance. Renewing is not possible: the original IPA and the private key live with the other tool.":
    "Sideloads en el iPhone que no vienen de ModStaller, por ejemplo de AltStore o SideStore. Renovarlas no es posible: el IPA original y la clave privada están en la otra herramienta.",
  "Sign & install":
    "Firmar e instalar",
  "Sign in":
    "Iniciar sesión",
  "Sign in once, then ModStaller signs by itself.":
    "Inicia sesión una vez y luego ModStaller firma solo.",
  "Sign in with Apple":
    "Iniciar sesión con Apple",
  "Sign out":
    "Cerrar sesión",
  "Sign out?":
    "¿Cerrar sesión?",
  "Signed by someone else":
    "Firmada por un tercero",
  "Signed in":
    "Sesión iniciada",
  "Signed in.":
    "Sesión iniciada.",
  "Signed out.":
    "Sesión cerrada.",
  "Source missing ({path}) – renewing is not possible.":
    "Falta el origen ({path}): no se puede renovar.",
  "Start an instance inside the app now (a game, for example) – only then does it ask for memory. The unlock applies to this launch of the app only.":
    "Inicia ahora una instancia dentro de la app (un juego, por ejemplo): solo entonces pide memoria. La activación vale solo para este arranque.",
  "Starting …":
    "Iniciando …",
  "Still to do: {what}":
    "Queda por hacer: {what}",
  "System check":
    "Diagnóstico",
  "System is ready – {count} step(s) still open.":
    "El sistema está listo: quedan {count} paso(s).",
  "That is not an IPA file.":
    "Eso no es un archivo IPA.",
  "The ModStaller service in the background has stopped":
    "El servicio de ModStaller en segundo plano se ha detenido",
  "The app and its data are deleted from the iPhone. It comes from another tool – ModStaller cannot restore it.":
    "La app y sus datos se borran del iPhone. Viene de otra herramienta: ModStaller no puede restaurarla.",
  "The app and its data are deleted from the iPhone. That frees one of the three slots.":
    "La app y sus datos se borran del iPhone. Eso libera uno de los tres huecos.",
  "The backend did not report in.":
    "El servicio de fondo no dio señales.",
  "The backend has stopped.":
    "El servicio de fondo se ha detenido.",
  "The connected iPhone.":
    "El iPhone conectado.",
  "The iPhone is plugged in but locked or not paired.":
    "El iPhone está conectado pero bloqueado o no emparejado.",
  "The session is discarded. Installed apps keep running but can only be renewed after signing in again.":
    "La sesión se descarta. Las apps instaladas siguen funcionando, pero solo podrán renovarse tras iniciar sesión de nuevo.",
  "This IPA is App Store encrypted (FairPlay) and cannot be re-signed.":
    "Este IPA está cifrado por la App Store (FairPlay) y no se puede volver a firmar.",
  "This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself.":
    "Esto no devuelve cuota semanal: Apple cuenta los ID de app recién creados, no los existentes. Cuando la ventana está llena, ModStaller pasa por sí mismo a un ID libre.",
  "To renew, unlock or remove, the iPhone has to be connected and unlocked.":
    "Para renovar, activar o quitar, el iPhone tiene que estar conectado y desbloqueado.",
  "Translations that are missing fall back to English.":
    "Las traducciones que falten vuelven al inglés.",
  "Turn on":
    "Activar",
  "Unlock the iPhone and confirm “Trust”.":
    "Desbloquea el iPhone y confirma «Confiar».",
  "Up to date – no newer version on GitHub.":
    "Al día: no hay ninguna versión más nueva en GitHub.",
  "Update check failed: {message}":
    "Falló la comprobación de actualizaciones: {message}",
  "Version {version} is available":
    "La versión {version} está disponible",
  "Version {version} is available – see bottom left.":
    "La versión {version} está disponible: mira abajo a la izquierda.",
  "Version {version} is ready":
    "La versión {version} está lista",
  "Version {version} · from iOS {ios}":
    "Versión {version} · desde iOS {ios}",
  "View quotas and certificates":
    "Ver cuotas y certificados",
  "What ModStaller has installed. Free accounts: at most 3 apps, valid for 7 days each.":
    "Lo que ModStaller ha instalado. Cuentas gratuitas: 3 apps como máximo, válidas 7 días cada una.",
  "What's new?":
    "¿Qué hay de nuevo?",
  "Whether an app depends on it cannot be determined without a connected iPhone.":
    "Sin un iPhone conectado no se puede saber si alguna app depende de él.",
  "Without a connected iPhone it cannot be said which App IDs are in use right now – apps of other tools depend on them too.":
    "Sin un iPhone conectado no se puede decir qué ID de app están en uso: también dependen de ellos apps de otras herramientas.",
  "Your Apple account signs the apps. The password is never stored or transmitted.":
    "Tu cuenta de Apple firma las apps. La contraseña nunca se guarda ni se transmite.",
  "Your apps":
    "Tus apps",
  "and {count} more":
    "y {count} más",
  "expired":
    "caducada",
  "expires {date}":
    "caduca el {date}",
  "expires – {when}":
    "caduca – {when}",
  "extensions":
    "extensiones",
  "frameworks":
    "frameworks",
  "free":
    "libre",
  "has expired":
    "ha caducado",
  "iPhone, sign-in and what expires soon – at a glance.":
    "iPhone, sesión y lo que caduca pronto: de un vistazo.",
  "in use":
    "en uso",
  "injected dylibs":
    "dylibs inyectadas",
  "just now":
    "ahora mismo",
  "off":
    "desactivado",
  "on":
    "activado",
  "or":
    "o",
  "yesterday":
    "ayer",
  "{count} day left":
    "queda {count} día",
  "{count} days ago":
    "hace {count} días",
  "{count} days left":
    "quedan {count} días",
  "{count} free":
    "{count} libre(s)",
  "{count} h ago":
    "hace {count} h",
  "{count} hour left":
    "queda {count} hora",
  "{count} hours left":
    "quedan {count} horas",
  "{count} point(s) prevent sideloading.":
    "{count} punto(s) impiden el sideloading.",
  "{count} point(s) to clear up.":
    "{count} punto(s) por aclarar.",
  "{name} is installed and runs for {days} days.":
    "{name} está instalada y funciona {days} días.",
  "{name} was removed from the iPhone.":
    "{name} se ha quitado del iPhone.",
  "{name} was renewed – valid for {days} days again.":
    "{name} se ha renovado: vuelve a ser válida {days} días.",
  "{percent}% transferred":
    "{percent}% transferido",
};

export default dict;
