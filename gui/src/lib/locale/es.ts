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
  "Action":
    "Acción",
  "Active":
    "Activa",
  "Active account ({account})":
    "Cuenta activa ({account})",
  "Add":
    "Añadir",
  "Add account":
    "Añadir cuenta",
  "Add an Apple account":
    "Añadir una cuenta de Apple",
  "After the running task.":
    "Tras la tarea en curso.",
  "Again":
    "Reintentar",
  "All":
    "Todo",
  "All areas":
    "Todas las áreas",
  "All sources":
    "Todas las fuentes",
  "All {max} app slots of the free profile are taken – iOS will refuse a further app. Remove one first:":
    "Los {max} huecos del perfil gratuito están ocupados: iOS rechazará otra app. Quita una primero:",
  "Also delete sign-ins, settings and logs":
    "Borrar también los inicios de sesión, los ajustes y los registros",
  "Also discard the device identity (Apple will then ask for a two-factor code again)":
    "Descartar también la identidad del dispositivo (Apple volverá a pedir un código de doble factor)",
  "Also lists jailbreak tools and exploits - they are marked and ask before installing.":
    "También incluye herramientas de jailbreak y exploits: están marcados y piden confirmación antes de instalar.",
  "An installed app belongs to it – from ModStaller or from another tool. After deleting, it can no longer be renewed.":
    "Hay una app instalada que depende de él: de ModStaller o de otra herramienta. Tras borrarlo ya no se podrá renovar.",
  "An instance has to be started inside the app while it waits – only then does it ask for memory.":
    "Hay que iniciar una instancia dentro de la app mientras espera: solo entonces pide memoria.",
  "An ordinary, free Apple ID is enough. Apple then asks for a code on your iPhone.":
    "Basta un ID de Apple normal y gratuito. Apple pedirá después un código en tu iPhone.",
  "Another operation is already running.":
    "Ya hay una operación en curso.",
  "Any image; it is cropped to a square.":
    "Cualquier imagen; se recorta en cuadrado.",
  "App ID deleted.":
    "ID de app borrado.",
  "App IDs in the account":
    "ID de app en la cuenta",
  "App IDs this week":
    "App ID esta semana",
  "App extensions were removed to save App IDs.":
    "Se quitaron las extensiones para ahorrar ID de app.",
  "App icon":
    "Icono de la app",
  "Apple account":
    "Cuenta de Apple",
  "Apple allows only a few at a time. A foreign one (from AltStore or SideStore, say) cannot be used by ModStaller – its private key lives with the tool that requested it.":
    "Apple solo permite unos pocos a la vez. Uno ajeno (de AltStore o SideStore, por ejemplo) no le sirve a ModStaller: su clave privada está en la herramienta que lo pidió.",
  "Apple counts App IDs created in the last 7 days – deleting one does not give it back.":
    "Apple cuenta los App ID creados en los últimos 7 días; borrar uno no lo devuelve.",
  "Apple device service is not running":
    "El servicio de dispositivos Apple no se está ejecutando",
  "Apple device service missing":
    "Falta el servicio de dispositivos Apple",
  "Apple sent a six-digit code to your iPhone.":
    "Apple ha enviado un código de seis dígitos a tu iPhone.",
  "Applies to the whole program, including the messages that come from the background service.":
    "Vale para todo el programa, también para los mensajes del servicio en segundo plano.",
  "Applies to this launch only – unlock again after quitting the app.":
    "Vale solo para este arranque: vuelve a activarlo tras cerrar la app.",
  "Apps":
    "Apps",
  "Apps from AltStore-compatible sources – signed with your Apple account and installed like any IPA.":
    "Apps de fuentes compatibles con AltStore: firmadas con tu cuenta de Apple e instaladas como cualquier IPA.",
  "Apps from the store are brought to the newest version of their source when they are renewed – same bundle ID, the app's data stays.":
    "Las apps de la tienda se actualizan a la versión más nueva de su fuente al renovarse: mismo bundle ID, los datos de la app se conservan.",
  "Apps on the iPhone (free profile)":
    "Apps en el iPhone (perfil gratuito)",
  "Asking Apple – this takes a few seconds …":
    "Consultando a Apple: esto tarda unos segundos …",
  "Automatic updates exist only in the AppImage and in the Windows version installed with the setup.":
    "Las actualizaciones automáticas solo existen en la AppImage y en la versión de Windows instalada con el instalador.",
  "Back":
    "Atrás",
  "Backend not reachable":
    "Servicio de fondo inaccesible",
  "Background":
    "Segundo plano",
  "Battery {level} %":
    "Batería {level} %",
  "Beta channel":
    "Canal beta",
  "Beta versions bring new features earlier, but they can be unstable and contain bugs.":
    "Las versiones beta traen funciones nuevas antes, pero pueden ser inestables y contener errores.",
  "Beta – may be unstable":
    "Beta – puede ser inestable",
  "Bundle ID":
    "Bundle ID",
  "Bundle ID {id} · transport: {transport}":
    "Bundle ID {id} · transporte: {transport}",
  "Cancel":
    "Cancelar",
  "Cancelled":
    "Cancelado",
  "Cancelled.":
    "Cancelado.",
  "Cannot be kept – its ID does not belong to the app.":
    "No se puede conservar: su ID no pertenece a la app.",
  "Certificate revoked.":
    "Certificado revocado.",
  "Change icon":
    "Cambiar el icono",
  "Charging … {level} %":
    "Cargando – {level} %",
  "Check again":
    "Comprobar de nuevo",
  "Check for updates":
    "Buscar actualizaciones",
  "Checking the App ID quota …":
    "Comprobando la cuota de App ID…",
  "Checking {count} apps …":
    "Comprobando {count} apps …",
  "Checking …":
    "Comprobando …",
  "Choose a file":
    "Elegir un archivo",
  "Choose image …":
    "Elegir imagen…",
  "Clear store cache":
    "Vaciar caché de la tienda",
  "Close":
    "Cerrar",
  "Closing the window keeps ModStaller in the tray. Quit it from the tray icon.":
    "Al cerrar la ventana, ModStaller sigue en la bandeja. Ciérralo desde el icono de la bandeja.",
  "Confirm":
    "Confirmar",
  "Confirmation code":
    "Código de confirmación",
  "Connect a device to install.":
    "Conecta un dispositivo para instalar.",
  "Connected but not ready":
    "Conectado pero no listo",
  "Connected but not ready – unlock the iPhone and confirm “Trust”.":
    "Conectado pero no listo: desbloquea el iPhone y confirma «Confiar».",
  "Connected via USB. Wi-Fi is on – without the cable ModStaller finds the iPhone in the same network.":
    "Conectado por USB. La Wi-Fi está activada: sin cable, ModStaller encuentra el iPhone en la misma red.",
  "Connected via USB. With Wi-Fi switched on, ModStaller also reaches the iPhone without the cable – for installing, renewing and the automatic renewal in the tray.":
    "Conectado por USB. Con la Wi-Fi activada, ModStaller también llega al iPhone sin cable: para instalar, renovar y para la renovación automática desde la bandeja.",
  "Connected via Wi-Fi. For JIT below iOS 17.4 the cable is still needed.":
    "Conectado por Wi-Fi. Para JIT por debajo de iOS 17.4 sigue haciendo falta el cable.",
  "Connection":
    "Conexión",
  "Copy":
    "Copiar",
  "Copying is not possible.":
    "No se puede copiar.",
  "Create a desktop shortcut":
    "Crear un acceso directo en el escritorio",
  "Customize":
    "Personalizar",
  "Customize …":
    "Personalizar …",
  "Data in":
    "Datos en",
  "Delete":
    "Borrar",
  "Delete App ID":
    "Borrar ID de app",
  "Delete App ID?":
    "¿Borrar el ID de app?",
  "Developer Mode":
    "Modo de desarrollador",
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
  "Device forgotten.":
    "Dispositivo olvidado.",
  "Device, sign-in and what expires soon – at a glance.":
    "Dispositivo, sesión y lo que caduca pronto, de un vistazo.",
  "Different IPA":
    "Otro IPA",
  "Does not fit":
    "No compatible",
  "Done":
    "Listo",
  "Download":
    "Descargar",
  "Download {name}":
    "Descargar {name}",
  "Downloaded IPAs stay so apps can be renewed later. Clearing removes pictures and every IPA no installed app needs.":
    "Las IPA descargadas se conservan para poder renovar las apps más tarde. Vaciar elimina las imágenes y cada IPA que ninguna app instalada necesite.",
  "Downloads new versions and installs them while ModStaller is not in use. Afterwards it keeps running in the tray.":
    "Descarga las versiones nuevas y las instala mientras no usas ModStaller. Después sigue en la bandeja.",
  "Drag an IPA here":
    "Arrastra un IPA aquí",
  "Drag an IPA into the window or pick one from your Downloads.":
    "Arrastra un IPA a la ventana o elige uno de tus descargas.",
  "Each kept extension needs an App ID of its own.":
    "Cada extensión que conserves necesita su propio App ID.",
  "Enable JIT":
    "Activar JIT",
  "Errors":
    "Errores",
  "Every app signed with it will no longer start – including those of other sideloading tools.":
    "Todas las apps firmadas con él dejarán de arrancar, también las de otras herramientas de sideloading.",
  "Everything ready for sideloading.":
    "Todo listo para el sideloading.",
  "Everything ready.":
    "Todo listo.",
  "Exploit":
    "Exploit",
  "Explorer shows the iPhone but ModStaller doesn’t? Unplug it, unlock it and plug it back in – if that doesn’t help, restart the PC.":
    "¿El Explorador muestra el iPhone pero ModStaller no? Desconéctalo, desbloquéalo y vuelve a conectarlo; si no ayuda, reinicia el PC.",
  "Extension":
    "Extensión",
  "Extensions":
    "Extensiones",
  "Failed":
    "Falló",
  "Files":
    "Archivos",
  "Filter":
    "Filtrar",
  "Fix":
    "Arreglar",
  "Follow live again":
    "Volver a seguir en directo",
  "Forget":
    "Olvidar",
  "Forget device":
    "Olvidar dispositivo",
  "Forget {name}?":
    "¿Olvidar {name}?",
  "Found in your folders":
    "Encontrados en tus carpetas",
  "Free":
    "Gratuita",
  "Free again: {dates}":
    "Vuelven a quedar libres: {dates}",
  "From other tools":
    "De otras herramientas",
  "From {source}":
    "De {source}",
  "Full log:":
    "Registro completo:",
  "Go to device":
    "Ir al dispositivo",
  "Hello, {name}!":
    "¡Hola, {name}!",
  "How ModStaller behaves on this computer.":
    "Cómo se comporta ModStaller en este ordenador.",
  "In the background":
    "En segundo plano",
  "Install":
    "Instalar",
  "Install anyway":
    "Instalar de todos modos",
  "Install app":
    "Instalar app",
  "Install updates automatically":
    "Instalar actualizaciones automáticamente",
  "Install {name}":
    "Instalar {name}",
  "Install {name}?":
    "¿Instalar {name}?",
  "Installed":
    "Instalada",
  "Installed through your package manager ({name}) – updates come from there.":
    "Instalado con tu gestor de paquetes ({name}): las actualizaciones llegan desde ahí.",
  "Installed user apps":
    "Apps de usuario instaladas",
  "Installing ModStaller…":
    "Instalando ModStaller…",
  "Is everything here that ModStaller needs?":
    "¿Está todo lo que ModStaller necesita?",
  "It becomes the active account for new installs. Apps keep renewing with the account that installed them.":
    "Pasa a ser la cuenta activa para nuevas instalaciones. Las apps se siguen renovando con la cuenta que las instaló.",
  "It is installed but stopped. Windows asks for confirmation once when it is started.":
    "Está instalado, pero detenido. Windows pide confirmación una vez al iniciarlo.",
  "JIT and the Developer Disk Image still need the cable on this iOS version (Wi-Fi needs iOS 17.4 or newer for that).":
    "JIT y la Developer Disk Image siguen necesitando el cable en esta versión de iOS (por Wi-Fi hace falta iOS 17.4 o posterior).",
  "JIT for {name}":
    "JIT para {name}",
  "Jailbreak tool":
    "Herramienta de jailbreak",
  "Keep running in the tray when closed":
    "Seguir en la bandeja al cerrar",
  "Keep that screen open and pick the Apple TV below.":
    "Deja esa pantalla abierta y elige el Apple TV abajo.",
  "Keyboard":
    "Teclado",
  "Language":
    "Idioma",
  "Leave out all extensions":
    "Quitar todas las extensiones",
  "Leaving the beta channel keeps the installed beta until a newer stable version is out.":
    "Al salir del canal beta se mantiene la beta instalada hasta que haya una versión estable más reciente.",
  "List apps":
    "Listar apps",
  "Live":
    "En directo",
  "Loading sources …":
    "Cargando fuentes …",
  "Log":
    "Registro",
  "Log file":
    "Archivo de registro",
  "Log file not found.":
    "No se encontró el archivo de registro.",
  "Log in":
    "Registro en",
  "Looking for updates …":
    "Buscando actualizaciones …",
  "Looking in the network …":
    "Buscando en la red …",
  "Make active":
    "Activar",
  "Manage App IDs ({count})":
    "Gestionar los ID de app ({count})",
  "Manage all":
    "Gestionar todo",
  "Microsoft Store":
    "Microsoft Store",
  "ModStaller Setup":
    "Instalación de ModStaller",
  "ModStaller can stay in the tray, remind you before apps expire and renew them on its own. Renewing needs your iPhone connected via USB.":
    "ModStaller puede seguir en la bandeja, avisarte antes de que caduquen las apps y renovarlas por sí solo. Para renovar, tu iPhone debe estar conectado por USB.",
  "ModStaller forgets the device and its pairing. Over the cable it shows up again; an Apple TV has to be paired again with a PIN.":
    "ModStaller olvida el dispositivo y su emparejamiento. Por cable vuelve a aparecer; un Apple TV hay que emparejarlo de nuevo con un PIN.",
  "ModStaller is starting …":
    "ModStaller está arrancando …",
  "ModStaller was removed.":
    "ModStaller se ha eliminado.",
  "ModStaller {version} is already installed.":
    "ModStaller {version} ya está instalado.",
  "ModStaller {version} is installed.":
    "ModStaller {version} está instalado.",
  "Must be unique at Apple. Empty: ModStaller picks one that fits your team.":
    "Debe ser único en Apple. Vacío: ModStaller elige uno adecuado para tu equipo.",
  "Name on the home screen":
    "Nombre en la pantalla de inicio",
  "New icon – cropped to a square.":
    "Icono nuevo: recortado en cuadrado.",
  "New installs sign with the active account. Renewals always use the account that installed the app.":
    "Las nuevas instalaciones se firman con la cuenta activa. Las renovaciones usan siempre la cuenta que instaló la app.",
  "Next: turn on Developer Mode on the Apple TV (Settings › Privacy & Security), then install the tvOS version of an app.":
    "Después: activa el modo de desarrollador en el Apple TV (Ajustes › Privacidad y seguridad) e instala la versión tvOS de una app.",
  "Next: turn on Developer Mode on the Vision Pro (Settings › Privacy & Security), then install an app.":
    "Después: activa el modo de desarrollador en el Vision Pro (Ajustes › Privacidad y seguridad) e instala una app.",
  "No IPAs in Downloads, Documents or Desktop.":
    "No hay IPA en Descargas, Documentos ni Escritorio.",
  "No app in your sources fits the {kind}.":
    "Ninguna app de tus fuentes es compatible con el {kind}.",
  "No app installed yet":
    "Todavía no hay ninguna app instalada",
  "No app matches “{query}”.":
    "Ninguna app coincide con «{query}».",
  "No apps - add a source under “Sources”.":
    "No hay apps: añade una fuente en «Fuentes».",
  "No certificates in the account.":
    "No hay certificados en la cuenta.",
  "No device":
    "Ningún dispositivo",
  "No device connected – plug the iPhone in via USB and unlock it, or bring it into the same Wi-Fi.":
    "Ningún dispositivo conectado: conecta el iPhone por USB y desbloquéalo, o ponlo en la misma Wi-Fi.",
  "No device connected. Plug the iPhone in via USB and unlock it – or bring it into the same Wi-Fi.":
    "Ningún dispositivo conectado. Conecta el iPhone por USB y desbloquéalo, o ponlo en la misma Wi-Fi.",
  "No entries for this filter.":
    "No hay entradas para este filtro.",
  "No installed app belongs to this App ID right now.":
    "Ahora mismo no hay ninguna app instalada que use este ID de app.",
  "No messages yet.":
    "Todavía no hay mensajes.",
  "No new App ID needed – the ones this install uses already exist.":
    "No hace falta ningún App ID nuevo: los que usa esta instalación ya existen.",
  "No tray icon available. Reminders and renewals still work; start ModStaller again to open the window.":
    "No hay icono de bandeja disponible. Los avisos y las renovaciones siguen funcionando; vuelve a abrir ModStaller para ver la ventana.",
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
  "Nothing found. Is the pairing screen open on the device and is it in the same network?":
    "No se encontró nada. ¿Está abierta la pantalla de emparejamiento en el dispositivo y está en la misma red?",
  "Nothing has happened yet.":
    "Todavía no ha pasado nada.",
  "Nothing has happened yet. As soon as you plug in an iPhone or install something, it shows up here.":
    "Todavía no ha pasado nada. En cuanto conectes un iPhone o instales algo, aparecerá aquí.",
  "Nothing installed through ModStaller yet.":
    "Todavía no hay nada instalado con ModStaller.",
  "Nothing is due right now":
    "Ahora mismo no vence nada",
  "Nothing was due.":
    "No vencía nada.",
  "Notifications":
    "Notificaciones",
  "On the Apple TV open Settings › Remotes and Devices › Remote App and Devices.":
    "En el Apple TV abre Ajustes › Mandos y dispositivos › App Remote y dispositivos.",
  "On the Vision Pro open Settings › General › Remote Devices.":
    "En el Vision Pro abre Ajustes › General › Dispositivos remotos.",
  "One click fixes it – see above.":
    "Se arregla con un clic: mira arriba.",
  "Only for installed copies and the AppImage - not in development builds.":
    "Solo para copias instaladas y la AppImage, no en compilaciones de desarrollo.",
  "Only for your user – no administrator rights needed. Your sign-ins and settings stay where they are.":
    "Solo para tu usuario, sin permisos de administrador. Tus inicios de sesión y ajustes se quedan donde están.",
  "Optional – empty fields keep what the IPA says.":
    "Opcional: los campos vacíos conservan lo que dice el IPA.",
  "Original icon":
    "Icono original",
  "Overview":
    "Resumen",
  "PIN from the Apple TV":
    "PIN del Apple TV",
  "Paid":
    "De pago",
  "Paid account – no weekly limit on App IDs and no limit on apps.":
    "Cuenta de pago: sin límite semanal de App ID ni límite de apps.",
  "Pair":
    "Emparejar",
  "Pair Apple TV or Vision Pro":
    "Emparejar Apple TV o Vision Pro",
  "Pair device":
    "Emparejar dispositivo",
  "Pair {name}":
    "Emparejar {name}",
  "Paired over the network – reachable while the device is on and in the same network.":
    "Emparejado por la red: accesible mientras el dispositivo esté encendido y en la misma red.",
  "Password":
    "Contraseña",
  "Pause":
    "Pausar",
  "Paused":
    "En pausa",
  "Photo editing":
    "Edición de fotos",
  "Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.":
    "Elige un IPA: ModStaller lo firma con tu cuenta de Apple y lo instala en el iPhone.",
  "Pick it below and confirm the pairing on the Vision Pro.":
    "Elígelo abajo y confirma el emparejamiento en el Vision Pro.",
  "Plug it in via USB and unlock it – or bring it into the same Wi-Fi.":
    "Conéctalo por USB y desbloquéalo, o ponlo en la misma Wi-Fi.",
  "Preparing Anisette …":
    "Preparando Anisette …",
  "Program":
    "Programa",
  "Read again":
    "Volver a leer",
  "Reading the IPA …":
    "Leyendo el IPA …",
  "Receive beta versions":
    "Recibir versiones beta",
  "Recent activity":
    "Actividad reciente",
  "Refresh":
    "Actualizar",
  "Registered devices":
    "Dispositivos registrados",
  "Reinstall":
    "Reinstalar",
  "Released":
    "Publicada",
  "Reload":
    "Recargar",
  "Reload sources":
    "Recargar fuentes",
  "Remind me before apps expire":
    "Avisarme antes de que caduquen las apps",
  "Remove":
    "Quitar",
  "Remove from the device":
    "Quitar del dispositivo",
  "Remove {name}":
    "Quitar {name}",
  "Remove {name}?":
    "¿Quitar {name}?",
  "Removes the program, the start menu entry and the `modstaller` command.":
    "Elimina el programa, la entrada del menú de inicio y el comando `modstaller`.",
  "Removing ModStaller…":
    "Eliminando ModStaller…",
  "Renew":
    "Renovar",
  "Renew apps automatically":
    "Renovar apps automáticamente",
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
  "Renewing {name} in the background …":
    "Renovando {name} en segundo plano …",
  "Repair":
    "Reparar",
  "Requires":
    "Requiere",
  "Restart":
    "Reiniciar",
  "Reuse an unused App ID …":
    "Reutilizar un App ID sin usar…",
  "Revoke":
    "Revocar",
  "Revoke certificate?":
    "¿Revocar el certificado?",
  "Runs on":
    "Funciona en",
  "SRP-6a: Apple gets proof that you know the password – not the password itself.":
    "SRP-6a: Apple obtiene la prueba de que conoces la contraseña, no la contraseña en sí.",
  "Safari":
    "Safari",
  "Screen broadcast":
    "Emisión de pantalla",
  "Search":
    "Buscar",
  "Search again":
    "Buscar de nuevo",
  "Search apps":
    "Buscar apps",
  "Set up automatically":
    "Configurar automáticamente",
  "Set up the Apple device service":
    "Configurar el servicio de dispositivos Apple",
  "Settings":
    "Ajustes",
  "Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.":
    "Ajustes › Privacidad y seguridad › Modo de desarrollador – si no, no arrancará ninguna app con sideload.",
  "Share":
    "Compartir",
  "Show all":
    "Mostrar todas",
  "Show in the store":
    "Mostrar en la tienda",
  "Show teams and certificates":
    "Mostrar equipos y certificados",
  "Sideloading for {platform}":
    "Sideloading para {platform}",
  "Sideloading has risks: apps from sources are not reviewed by Apple. Only install apps from sources you trust, and keep an eye on what an app asks for.":
    "El sideloading tiene riesgos: Apple no revisa las apps de las fuentes. Instala solo apps de fuentes en las que confíes y fíjate en lo que pide cada app.",
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
  "Sign with":
    "Firmar con",
  "Signed by someone else":
    "Firmada por un tercero",
  "Signed by {account}":
    "Firmada por {account}",
  "Signed in":
    "Sesión iniciada",
  "Signed in.":
    "Sesión iniciada.",
  "Signed out.":
    "Sesión cerrada.",
  "Signed-in accounts":
    "Cuentas conectadas",
  "Siri & Shortcuts":
    "Siri y Atajos",
  "Size":
    "Tamaño",
  "Source":
    "Fuente",
  "Source added: {name} ({count} apps)":
    "Fuente añadida: {name} ({count} apps)",
  "Source missing ({path}) – renewing is not possible.":
    "Falta el origen ({path}): no se puede renovar.",
  "Sources":
    "Fuentes",
  "Sources in the AltStore format – the same ones AltStore and SideStore read. ModStaller comes with the official sources of AltStore, SideStore, UTM, PojavLauncher/Amethyst, iSH, StikDebug and several emulators.":
    "Fuentes en formato AltStore: las mismas que leen AltStore y SideStore. ModStaller incluye las fuentes oficiales de AltStore, SideStore, UTM, PojavLauncher/Amethyst, iSH, StikDebug y varios emuladores.",
  "Sources you add are your responsibility: ModStaller shows what they list, it does not check it. Only install apps you are allowed to use.":
    "Las fuentes que añadas son tu responsabilidad: ModStaller muestra lo que ofrecen, no lo comprueba. Instala solo apps que tengas derecho a usar.",
  "Stable channel":
    "Canal estable",
  "Stable versions are always offered. With the beta channel, pre-release versions (-beta.x) are offered as well.":
    "Las versiones estables se ofrecen siempre. Con el canal beta se ofrecen también versiones preliminares (-beta.x).",
  "Start ModStaller":
    "Iniciar ModStaller",
  "Start an instance inside the app now (a game, for example) – only then does it ask for memory. The unlock applies to this launch of the app only.":
    "Inicia ahora una instancia dentro de la app (un juego, por ejemplo): solo entonces pide memoria. La activación vale solo para este arranque.",
  "Start menu":
    "Menú de inicio",
  "Start service":
    "Iniciar el servicio",
  "Start with the system":
    "Iniciar con el sistema",
  "Starting …":
    "Iniciando …",
  "Starts in the tray after you log in, without a window.":
    "Se inicia en la bandeja al iniciar sesión, sin ventana.",
  "Still to do: {what}":
    "Queda por hacer: {what}",
  "Store":
    "Tienda",
  "Suitable for {name} ({os} {version})":
    "Compatible con {name} ({os} {version})",
  "Switch off Wi-Fi":
    "Desactivar Wi-Fi",
  "Switch on Wi-Fi":
    "Activar Wi-Fi",
  "Switch to this device":
    "Cambiar a este dispositivo",
  "System":
    "Sistema",
  "System check":
    "Diagnóstico",
  "System is ready – {count} step(s) still open.":
    "El sistema está listo: quedan {count} paso(s).",
  "Teams and certificates of {account}":
    "Equipos y certificados de {account}",
  "Terminal":
    "Terminal",
  "That image cannot be read.":
    "No se puede leer esta imagen.",
  "That is not an IPA file.":
    "Eso no es un archivo IPA.",
  "The Apple TV now shows a code on the screen. Type it in here.":
    "El Apple TV muestra ahora un código en pantalla. Escríbelo aquí.",
  "The Apple Watch app is removed – it cannot be installed this way.":
    "Se elimina la app de Apple Watch: no se puede instalar de esta forma.",
  "The ModStaller service in the background has stopped":
    "El servicio de ModStaller en segundo plano se ha detenido",
  "The app and its data are deleted from the device. It comes from another tool – ModStaller cannot restore it.":
    "La app y sus datos se borran del dispositivo. Viene de otra herramienta: ModStaller no puede restaurarla.",
  "The app and its data are deleted from the device. That frees one of the three slots.":
    "La app y sus datos se borran del dispositivo. Eso libera uno de los tres huecos.",
  "The app runs under the unused App ID {id}.":
    "La app usa el App ID sin usar {id}.",
  "The backend did not report in.":
    "El servicio de fondo no dio señales.",
  "The backend has stopped.":
    "El servicio de fondo se ha detenido.",
  "The bundle ID is not valid – letters, digits and hyphens, separated by dots.":
    "El bundle ID no es válido: letras, dígitos y guiones, separados por puntos.",
  "The connected device.":
    "El dispositivo conectado.",
  "The iPhone is plugged in but locked or not paired.":
    "El iPhone está conectado pero bloqueado o no emparejado.",
  "The next one frees up around {date}.":
    "El siguiente se libera hacia el {date}.",
  "The session is discarded. Installed apps keep running but can only be renewed after signing in again.":
    "La sesión se descarta. Las apps instaladas siguen funcionando, pero solo podrán renovarse tras iniciar sesión de nuevo.",
  "There already is a different `modstaller` command in ~/.local/bin – it was left untouched.":
    "Ya existe otro comando `modstaller` en ~/.local/bin; no se ha tocado.",
  "Third-party store":
    "Tienda de terceros",
  "This IPA is App Store encrypted (FairPlay) and cannot be re-signed.":
    "Este IPA está cifrado por la App Store (FairPlay) y no se puede volver a firmar.",
  "This IPA is an Apple TV app – pick the Apple TV as the device.":
    "Esta IPA es una app de Apple TV: elige el Apple TV como dispositivo.",
  "This IPA is an Apple Vision Pro app – pick the Vision Pro as the device.":
    "Esta IPA es una app de Apple Vision Pro: elige el Vision Pro como dispositivo.",
  "This IPA is for iPhone and iPad – an Apple TV needs the app's tvOS version.":
    "Esta IPA es para iPhone y iPad: un Apple TV necesita la versión tvOS de la app.",
  "This app changes the system through an exploit. That can go wrong and leave the device unstable - only install it if you know what it does.":
    "Esta app modifica el sistema mediante un exploit. Puede salir mal y dejar el dispositivo inestable: instálala solo si sabes lo que hace.",
  "This app installs apps from another store, many of them cracked. ModStaller cannot check what comes from there.":
    "Esta app instala apps de otra tienda, muchas de ellas crackeadas. ModStaller no puede comprobar lo que viene de ahí.",
  "This app is made for iPad only and does not start on an {kind}.":
    "Esta app está hecha solo para iPad y no arranca en un {kind}.",
  "This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself.":
    "Esto no devuelve cuota semanal: Apple cuenta los ID de app recién creados, no los existentes. Cuando la ventana está llena, ModStaller pasa por sí mismo a un ID libre.",
  "This install needs {cost} – {missing} more than are left.":
    "Esta instalación necesita {cost}: {missing} más de los que quedan.",
  "This install uses {cost} of them.":
    "Esta instalación usa {cost} de ellos.",
  "This is a jailbreak tool. It attacks the system with an exploit - a failed run can mean a boot loop, a restore and lost data, and it weakens the device's security. Only install it if you know exactly what you are doing.":
    "Es una herramienta de jailbreak. Ataca el sistema con un exploit: un intento fallido puede provocar un bucle de arranque, una restauración y pérdida de datos, y debilita la seguridad del dispositivo. Instálala solo si sabes exactamente lo que haces.",
  "This version does not fit the {kind} ({name}) - check the required system version and device type, or pick another source.":
    "Esta versión no es compatible con el {kind} ({name}): comprueba la versión del sistema necesaria y el tipo de dispositivo, o elige otra fuente.",
  "To renew, unlock or remove, the iPhone has to be connected and unlocked.":
    "Para renovar, activar o quitar, el iPhone tiene que estar conectado y desbloqueado.",
  "Translations that are missing fall back to English.":
    "Las traducciones que falten vuelven al inglés.",
  "Try again":
    "Reintentar",
  "Turn on":
    "Activar",
  "Type in the PIN the Apple TV then shows.":
    "Escribe el PIN que muestra entonces el Apple TV.",
  "Undo":
    "Deshacer",
  "Undo changes":
    "Descartar cambios",
  "Uninstall":
    "Desinstalar",
  "Uninstall now":
    "Desinstalar ahora",
  "Unlock the iPhone and confirm “Trust”.":
    "Desbloquea el iPhone y confirma «Confiar».",
  "Unplug the iPhone and plug it in again.":
    "Desconecta el iPhone y vuelve a conectarlo.",
  "Unused ones are reused automatically when the weekly quota is used up – or pick one yourself when installing.":
    "Los que no se usan se reutilizan automáticamente cuando se agota la cuota semanal, o elige uno tú al instalar.",
  "Up to date – no newer version on GitHub.":
    "Al día: no hay ninguna versión más nueva en GitHub.",
  "Update":
    "Actualizar",
  "Update check failed: {message}":
    "Falló la comprobación de actualizaciones: {message}",
  "Update store apps while renewing":
    "Actualizar apps de la tienda al renovar",
  "Update to {version}":
    "Actualizar a {version}",
  "Updates":
    "Actualizaciones",
  "Updates available":
    "Actualizaciones disponibles",
  "VPN / network":
    "VPN / red",
  "Version":
    "Versión",
  "Version {version} for Linux":
    "Versión {version} para Linux",
  "Version {version} is available":
    "La versión {version} está disponible",
  "Version {version} is available – see bottom left.":
    "La versión {version} está disponible: mira abajo a la izquierda.",
  "Version {version} is ready":
    "La versión {version} está lista",
  "Version {version} · Apple TV · from tvOS {os}":
    "Versión {version} · Apple TV · desde tvOS {os}",
  "Version {version} · Apple Vision Pro · from visionOS {os}":
    "Versión {version} · Apple Vision Pro · desde visionOS {os}",
  "Version {version} · from iOS {ios}":
    "Versión {version} · desde iOS {ios}",
  "View quotas and certificates":
    "Ver cuotas y certificados",
  "Wait for the running task first":
    "Espera primero a que termine la tarea en curso",
  "Warnings":
    "Advertencias",
  "What ModStaller does – live. The complete history is in the log file.":
    "Lo que hace ModStaller, en directo. El historial completo está en el archivo de registro.",
  "What ModStaller has installed. Free accounts: at most 3 apps, valid for 7 days each.":
    "Lo que ModStaller ha instalado. Cuentas gratuitas: 3 apps como máximo, válidas 7 días cada una.",
  "What's new in {version}":
    "Novedades de {version}",
  "What's new?":
    "¿Qué hay de nuevo?",
  "Where ModStaller is installed":
    "Dónde se instala ModStaller",
  "Whether an app depends on it cannot be determined without a connected iPhone.":
    "Sin un iPhone conectado no se puede saber si alguna app depende de él.",
  "Wi-Fi":
    "Wi-Fi",
  "Wi-Fi is off. The iPhone is only reachable over the cable again.":
    "La Wi-Fi está desactivada. El iPhone vuelve a estar accesible solo por cable.",
  "Wi-Fi is on. The iPhone can now be unplugged – ModStaller finds it in the same network.":
    "La Wi-Fi está activada. Ya puedes desconectar el iPhone: ModStaller lo encuentra en la misma red.",
  "Widget":
    "Widget",
  "Windows shows the iPhone in Explorer through its own photo driver – ModStaller needs Apple’s device service for USB. ModStaller can set it up for you: “Apple Devices” from the Microsoft Store, otherwise just Apple’s USB driver.":
    "Windows muestra el iPhone en el Explorador mediante su propio controlador de fotos, pero ModStaller necesita el servicio de dispositivos de Apple para el USB. ModStaller puede configurarlo por ti: «Dispositivos Apple» desde Microsoft Store o, si no, solo el controlador USB de Apple.",
  "Without a connected iPhone it cannot be said which App IDs are in use right now – apps of other tools depend on them too.":
    "Sin un iPhone conectado no se puede decir qué ID de app están en uso: también dependen de ellos apps de otras herramientas.",
  "You find it in the start menu. You can remove it again by running this setup once more.":
    "Lo encontrarás en el menú de inicio. Para quitarlo, vuelve a ejecutar este instalador.",
  "Your Apple account signs the apps. The password is never stored or transmitted.":
    "Tu cuenta de Apple firma las apps. La contraseña nunca se guarda ni se transmite.",
  "Your apps":
    "Tus apps",
  "Your sign-ins and settings were kept.":
    "Tus inicios de sesión y ajustes se han conservado.",
  "and {count} more":
    "y {count} más",
  "days before expiry":
    "días antes de caducar",
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
  "hours before expiry. If your iPhone is not connected then, ModStaller asks for it and renews as soon as it is.":
    "horas antes de caducar. Si tu iPhone no está conectado en ese momento, ModStaller lo pide y renueva en cuanto lo esté.",
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
  "{account} now signs new installs.":
    "{account} firma ahora las nuevas instalaciones.",
  "{available} of {max} left":
    "quedan {available} de {max}",
  "{count} accounts signed in":
    "{count} cuentas conectadas",
  "{count} apps":
    "{count} apps",
  "{count} day left":
    "queda {count} día",
  "{count} days ago":
    "hace {count} días",
  "{count} days left":
    "quedan {count} días",
  "{count} entries copied.":
    "{count} entradas copiadas.",
  "{count} free":
    "{count} libre(s)",
  "{count} h ago":
    "hace {count} h",
  "{count} hidden":
    "{count} ocultas",
  "{count} hour left":
    "queda {count} hora",
  "{count} hours left":
    "quedan {count} horas",
  "{count} new":
    "{count} nuevas",
  "{count} new App ID(s) created.":
    "{count} App ID nuevo(s) creado(s).",
  "{count} point(s) prevent sideloading.":
    "{count} punto(s) impiden el sideloading.",
  "{count} point(s) to clear up.":
    "{count} punto(s) por aclarar.",
  "{count} sources":
    "{count} fuentes",
  "{from} → {to}":
    "{from} → {to}",
  "{kind} via {via}":
    "{kind} por {via}",
  "{minutes} min ago":
    "hace {minutes} min",
  "{name} is being renewed in the background. Try again in a moment.":
    "{name} se está renovando en segundo plano. Vuelve a intentarlo en un momento.",
  "{name} is downloaded - adjust it and install.":
    "{name} está descargada: ajústala e instálala.",
  "{name} is installed and runs for {days} days.":
    "{name} está instalada y funciona {days} días.",
  "{name} is paired.":
    "{name} está emparejado.",
  "{name} was removed from the device.":
    "{name} se quitó del dispositivo.",
  "{name} was renewed – valid for {days} days again.":
    "{name} se ha renovado: vuelve a ser válida {days} días.",
  "{percent}% transferred":
    "{percent}% transferido",
  "{size} freed ({count} IPAs removed).":
    "{size} liberados ({count} IPA eliminadas).",
  "{used} of {max} used":
    "{used} de {max} ocupados",
  "~/.local/bin is not on your PATH yet – the `modstaller` command works in the terminal after logging in again.":
    "~/.local/bin aún no está en tu PATH: el comando `modstaller` funcionará en la terminal tras volver a iniciar sesión.",
};

export default dict;
