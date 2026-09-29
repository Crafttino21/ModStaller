// Portugues (Brasil) - Katalog der Oberflaeche.
//
// Schluessel ist der englische Quelltext (siehe lib/i18n.svelte.ts).
// Ein fehlender Eintrag faellt auf Englisch zurueck.

import type { Dict } from "../i18n.svelte";

const dict: Dict = {
  "(exit {code})":
    "(saída {code})",
  "<b>JIT</b> is needed by Java and emulator apps (Minecraft launchers, for example): ModStaller starts the app with a debugger attached and releases memory as soon as it asks for it.":
    "<b>JIT</b> é necessário para apps em Java e emuladores (lançadores de Minecraft, por exemplo): o ModStaller inicia o app com um depurador anexado e libera memória assim que ele pede.",
  "Account":
    "Conta",
  "Action":
    "Ação",
  "Active":
    "Ativa",
  "Active account ({account})":
    "Conta ativa ({account})",
  "Add account":
    "Adicionar conta",
  "Add an Apple account":
    "Adicionar uma conta Apple",
  "After the running task.":
    "Após a tarefa em andamento.",
  "Again":
    "Tentar de novo",
  "All":
    "Tudo",
  "All areas":
    "Todas as áreas",
  "All {max} app slots of the free profile are taken – iOS will refuse a further app. Remove one first:":
    "Todos os {max} espaços do perfil gratuito estão ocupados – o iOS recusará outro app. Remova um primeiro:",
  "Also delete sign-ins, settings and logs":
    "Excluir também logins, configurações e registros",
  "Also discard the device identity (Apple will then ask for a two-factor code again)":
    "Descartar também a identidade do dispositivo (a Apple vai pedir um código de dois fatores de novo)",
  "An installed app belongs to it – from ModStaller or from another tool. After deleting, it can no longer be renewed.":
    "Há um app instalado que depende dele – do ModStaller ou de outra ferramenta. Depois de excluir, ele não poderá mais ser renovado.",
  "An instance has to be started inside the app while it waits – only then does it ask for memory.":
    "É preciso iniciar uma instância dentro do app enquanto ele espera – só então ele pede memória.",
  "An ordinary, free Apple ID is enough. Apple then asks for a code on your iPhone.":
    "Basta um ID Apple comum e gratuito. Depois a Apple pede um código no seu iPhone.",
  "Another operation is already running.":
    "Já há uma operação em andamento.",
  "Any image; it is cropped to a square.":
    "Qualquer imagem; ela é recortada em quadrado.",
  "App ID deleted.":
    "ID de app excluído.",
  "App IDs in the account":
    "IDs de app na conta",
  "App IDs this week":
    "App IDs nesta semana",
  "App extensions were removed to save App IDs.":
    "As extensões foram removidas para economizar IDs de app.",
  "App icon":
    "Ícone do app",
  "Apple account":
    "Conta Apple",
  "Apple allows only a few at a time. A foreign one (from AltStore or SideStore, say) cannot be used by ModStaller – its private key lives with the tool that requested it.":
    "A Apple só permite alguns por vez. Um de terceiros (do AltStore ou do SideStore, por exemplo) não serve ao ModStaller: a chave privada fica na ferramenta que o pediu.",
  "Apple counts App IDs created in the last 7 days – deleting one does not give it back.":
    "A Apple conta os App IDs criados nos últimos 7 dias – excluir um não o devolve.",
  "Apple device service is not running":
    "O serviço de dispositivos Apple não está em execução",
  "Apple device service missing":
    "Serviço de dispositivos Apple ausente",
  "Apple sent a six-digit code to your iPhone.":
    "A Apple enviou um código de seis dígitos para o seu iPhone.",
  "Applies to the whole program, including the messages that come from the background service.":
    "Vale para o programa inteiro, inclusive para as mensagens do serviço em segundo plano.",
  "Applies to this launch only – unlock again after quitting the app.":
    "Vale só para esta execução – ative de novo depois de fechar o app.",
  "Apps":
    "Apps",
  "Apps on the iPhone (free profile)":
    "Apps no iPhone (perfil gratuito)",
  "Asking Apple – this takes a few seconds …":
    "Consultando a Apple – isso leva alguns segundos …",
  "Automatic updates exist only in the AppImage and in the Windows version installed with the setup.":
    "As atualizações automáticas só existem no AppImage e na versão Windows instalada pelo instalador.",
  "Back":
    "Voltar",
  "Backend not reachable":
    "Serviço em segundo plano inacessível",
  "Background":
    "Segundo plano",
  "Battery {level} %":
    "Bateria {level} %",
  "Beta channel":
    "Canal beta",
  "Beta versions bring new features earlier, but they can be unstable and contain bugs.":
    "Versões beta trazem novidades antes, mas podem ser instáveis e conter erros.",
  "Beta – may be unstable":
    "Beta – pode ser instável",
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
    "Não pode ser mantida – o ID dela não pertence ao app.",
  "Certificate revoked.":
    "Certificado revogado.",
  "Change icon":
    "Alterar ícone",
  "Charging … {level} %":
    "Carregando – {level} %",
  "Check again":
    "Verificar de novo",
  "Check for updates":
    "Procurar atualizações",
  "Checking the App ID quota …":
    "Verificando a cota de App IDs…",
  "Checking …":
    "Verificando …",
  "Choose a file":
    "Escolher um arquivo",
  "Choose image …":
    "Escolher imagem…",
  "Close":
    "Fechar",
  "Closing the window keeps ModStaller in the tray. Quit it from the tray icon.":
    "Fechar a janela mantém o ModStaller na bandeja. Feche pelo ícone da bandeja.",
  "Confirm":
    "Confirmar",
  "Confirmation code":
    "Código de confirmação",
  "Connected but not ready":
    "Conectado, mas não pronto",
  "Connected but not ready – unlock the iPhone and confirm “Trust”.":
    "Conectado, mas não pronto – desbloqueie o iPhone e confirme “Confiar”.",
  "Connected via USB. Wi-Fi is on – without the cable ModStaller finds the iPhone in the same network.":
    "Conectado via USB. A Wi-Fi está ativada – sem cabo, o ModStaller encontra o iPhone na mesma rede.",
  "Connected via USB. With Wi-Fi switched on, ModStaller also reaches the iPhone without the cable – for installing, renewing and the automatic renewal in the tray.":
    "Conectado via USB. Com a Wi-Fi ativada, o ModStaller também alcança o iPhone sem cabo – para instalar, renovar e para a renovação automática na bandeja.",
  "Connected via Wi-Fi. For JIT below iOS 17.4 the cable is still needed.":
    "Conectado via Wi-Fi. Para JIT abaixo do iOS 17.4 o cabo ainda é necessário.",
  "Connection":
    "Conexão",
  "Copy":
    "Copiar",
  "Copying is not possible.":
    "Não é possível copiar.",
  "Create a desktop shortcut":
    "Criar um atalho na área de trabalho",
  "Customize":
    "Personalizar",
  "Data in":
    "Dados em",
  "Delete":
    "Excluir",
  "Delete App ID":
    "Excluir ID de app",
  "Delete App ID?":
    "Excluir o ID de app?",
  "Developer Mode":
    "Modo de desenvolvedor",
  "Developer Mode is off.":
    "O modo de desenvolvedor está desligado.",
  "Developer Mode off":
    "Modo de desenvolvedor desligado",
  "Developer Mode on":
    "Modo de desenvolvedor ligado",
  "Developer-signed":
    "Assinado por um desenvolvedor",
  "Development certificates":
    "Certificados de desenvolvimento",
  "Device":
    "Dispositivo",
  "Device forgotten.":
    "Dispositivo esquecido.",
  "Device, sign-in and what expires soon – at a glance.":
    "Dispositivo, login e o que expira em breve – num relance.",
  "Different IPA":
    "Outro IPA",
  "Done":
    "Concluído",
  "Download":
    "Baixar",
  "Downloads new versions and installs them while ModStaller is not in use. Afterwards it keeps running in the tray.":
    "Baixa novas versões e as instala enquanto o ModStaller não está em uso. Depois continua na bandeja.",
  "Drag an IPA here":
    "Arraste um IPA para cá",
  "Drag an IPA into the window or pick one from your Downloads.":
    "Arraste um IPA para a janela ou escolha um dos seus downloads.",
  "Each kept extension needs an App ID of its own.":
    "Cada extensão mantida precisa de um App ID próprio.",
  "Enable JIT":
    "Ativar JIT",
  "Errors":
    "Erros",
  "Every app signed with it will no longer start – including those of other sideloading tools.":
    "Todos os apps assinados com ele deixarão de abrir – inclusive os de outras ferramentas de sideload.",
  "Everything ready for sideloading.":
    "Tudo pronto para o sideload.",
  "Everything ready.":
    "Tudo pronto.",
  "Explorer shows the iPhone but ModStaller doesn’t? Unplug it, unlock it and plug it back in – if that doesn’t help, restart the PC.":
    "O Explorador mostra o iPhone, mas o ModStaller não? Desconecte, desbloqueie e conecte de novo – se não resolver, reinicie o PC.",
  "Extension":
    "Extensão",
  "Extensions":
    "Extensões",
  "Failed":
    "Falhou",
  "Files":
    "Arquivos",
  "Filter":
    "Filtrar",
  "Fix":
    "Resolver",
  "Follow live again":
    "Voltar a acompanhar ao vivo",
  "Forget":
    "Esquecer",
  "Forget device":
    "Esquecer dispositivo",
  "Forget {name}?":
    "Esquecer {name}?",
  "Found in your folders":
    "Encontrados nas suas pastas",
  "Free":
    "Gratuita",
  "Free again: {dates}":
    "Livres de novo: {dates}",
  "From other tools":
    "De outras ferramentas",
  "Full log:":
    "Log completo:",
  "Go to device":
    "Ir para o dispositivo",
  "Hello, {name}!":
    "Olá, {name}!",
  "How ModStaller behaves on this computer.":
    "Como o ModStaller se comporta neste computador.",
  "In the background":
    "Em segundo plano",
  "Install":
    "Instalar",
  "Install app":
    "Instalar app",
  "Install updates automatically":
    "Instalar atualizações automaticamente",
  "Install {name}":
    "Instalar {name}",
  "Installed through your package manager ({name}) – updates come from there.":
    "Instalado pelo seu gerenciador de pacotes ({name}) – as atualizações vêm de lá.",
  "Installed user apps":
    "Apps de usuário instalados",
  "Installing ModStaller…":
    "Instalando o ModStaller…",
  "Is everything here that ModStaller needs?":
    "Está tudo aqui do que o ModStaller precisa?",
  "It becomes the active account for new installs. Apps keep renewing with the account that installed them.":
    "Ela se torna a conta ativa para novas instalações. Os apps continuam sendo renovados com a conta que os instalou.",
  "It is installed but stopped. Windows asks for confirmation once when it is started.":
    "Ele está instalado, mas parado. Ao iniciá-lo, o Windows pede confirmação uma vez.",
  "JIT and the Developer Disk Image still need the cable on this iOS version (Wi-Fi needs iOS 17.4 or newer for that).":
    "JIT e a Developer Disk Image ainda precisam do cabo nesta versão do iOS (via Wi-Fi é preciso iOS 17.4 ou mais recente).",
  "JIT for {name}":
    "JIT para {name}",
  "Keep running in the tray when closed":
    "Continuar na bandeja ao fechar",
  "Keep that screen open and pick the Apple TV below.":
    "Mantenha essa tela aberta e escolha a Apple TV abaixo.",
  "Keyboard":
    "Teclado",
  "Language":
    "Idioma",
  "Leave out all extensions":
    "Deixar de fora todas as extensões",
  "Leaving the beta channel keeps the installed beta until a newer stable version is out.":
    "Ao sair do canal beta, a beta instalada é mantida até sair uma versão estável mais nova.",
  "List apps":
    "Listar apps",
  "Live":
    "Ao vivo",
  "Log":
    "Registro",
  "Log file":
    "Arquivo de log",
  "Log file not found.":
    "Arquivo de log não encontrado.",
  "Log in":
    "Log em",
  "Looking for updates …":
    "Procurando atualizações …",
  "Looking in the network …":
    "Procurando na rede …",
  "Make active":
    "Tornar ativa",
  "Manage App IDs ({count})":
    "Gerenciar os IDs de app ({count})",
  "Manage all":
    "Gerenciar tudo",
  "Microsoft Store":
    "Microsoft Store",
  "ModStaller Setup":
    "Instalação do ModStaller",
  "ModStaller can stay in the tray, remind you before apps expire and renew them on its own. Renewing needs your iPhone connected via USB.":
    "O ModStaller pode ficar na bandeja, lembrar você antes que os apps expirem e renová-los sozinho. Para renovar, o iPhone precisa estar conectado via USB.",
  "ModStaller forgets the device and its pairing. Over the cable it shows up again; an Apple TV has to be paired again with a PIN.":
    "O ModStaller esquece o dispositivo e o pareamento. Pelo cabo ele aparece de novo; uma Apple TV precisa ser pareada novamente com um PIN.",
  "ModStaller is starting …":
    "O ModStaller está iniciando …",
  "ModStaller was removed.":
    "O ModStaller foi removido.",
  "ModStaller {version} is already installed.":
    "O ModStaller {version} já está instalado.",
  "ModStaller {version} is installed.":
    "O ModStaller {version} está instalado.",
  "Must be unique at Apple. Empty: ModStaller picks one that fits your team.":
    "Precisa ser único na Apple. Vazio: o ModStaller escolhe um adequado à sua equipe.",
  "Name on the home screen":
    "Nome na tela de início",
  "New icon – cropped to a square.":
    "Ícone novo – recortado em quadrado.",
  "New installs sign with the active account. Renewals always use the account that installed the app.":
    "Novas instalações são assinadas com a conta ativa. As renovações sempre usam a conta que instalou o app.",
  "Next: turn on Developer Mode on the Apple TV (Settings › Privacy & Security), then install the tvOS version of an app.":
    "Em seguida: ative o modo de desenvolvedor na Apple TV (Ajustes › Privacidade e Segurança) e instale a versão tvOS de um app.",
  "Next: turn on Developer Mode on the Vision Pro (Settings › Privacy & Security), then install an app.":
    "Em seguida: ative o modo de desenvolvedor no Vision Pro (Ajustes › Privacidade e Segurança) e instale um app.",
  "No IPAs in Downloads, Documents or Desktop.":
    "Nenhum IPA em Downloads, Documentos ou Área de Trabalho.",
  "No app installed yet":
    "Nenhum app instalado ainda",
  "No certificates in the account.":
    "Nenhum certificado na conta.",
  "No device":
    "Nenhum dispositivo",
  "No device connected – plug the iPhone in via USB and unlock it, or bring it into the same Wi-Fi.":
    "Nenhum dispositivo conectado – conecte o iPhone via USB e desbloqueie, ou coloque-o na mesma Wi-Fi.",
  "No device connected. Plug the iPhone in via USB and unlock it – or bring it into the same Wi-Fi.":
    "Nenhum dispositivo conectado. Conecte o iPhone via USB e desbloqueie – ou coloque-o na mesma Wi-Fi.",
  "No entries for this filter.":
    "Nenhuma entrada para este filtro.",
  "No installed app belongs to this App ID right now.":
    "No momento nenhum app instalado usa este ID de app.",
  "No messages yet.":
    "Ainda sem mensagens.",
  "No new App ID needed – the ones this install uses already exist.":
    "Nenhum App ID novo necessário – os usados já existem.",
  "No tray icon available. Reminders and renewals still work; start ModStaller again to open the window.":
    "Nenhum ícone de bandeja disponível. Lembretes e renovações continuam funcionando; abra o ModStaller de novo para ver a janela.",
  "Not checked yet.":
    "Ainda não verificado.",
  "Not connected":
    "Não conectado",
  "Not signed in":
    "Sem sessão iniciada",
  "Not signed in with Apple.":
    "Sem sessão na Apple.",
  "Nothing found – everything on the iPhone comes from the store or from ModStaller.":
    "Nada encontrado – tudo o que está no iPhone vem da loja ou do ModStaller.",
  "Nothing found. Is the pairing screen open on the device and is it in the same network?":
    "Nada encontrado. A tela de pareamento está aberta no dispositivo e ele está na mesma rede?",
  "Nothing has happened yet.":
    "Nada aconteceu ainda.",
  "Nothing has happened yet. As soon as you plug in an iPhone or install something, it shows up here.":
    "Nada aconteceu ainda. Assim que você conectar um iPhone ou instalar algo, aparece aqui.",
  "Nothing installed through ModStaller yet.":
    "Nada instalado pelo ModStaller ainda.",
  "Nothing is due right now":
    "No momento nada está vencendo",
  "Nothing was due.":
    "Nada estava vencendo.",
  "Notifications":
    "Notificações",
  "On the Apple TV open Settings › Remotes and Devices › Remote App and Devices.":
    "Na Apple TV, abra Ajustes › Controles e Dispositivos › App Remote e Dispositivos.",
  "On the Vision Pro open Settings › General › Remote Devices.":
    "No Vision Pro, abra Ajustes › Geral › Dispositivos Remotos.",
  "One click fixes it – see above.":
    "Um clique resolve – veja acima.",
  "Only for installed copies and the AppImage - not in development builds.":
    "Só para cópias instaladas e para o AppImage – não em builds de desenvolvimento.",
  "Only for your user – no administrator rights needed. Your sign-ins and settings stay where they are.":
    "Só para o seu usuário – sem direitos de administrador. Seus logins e configurações continuam onde estão.",
  "Optional – empty fields keep what the IPA says.":
    "Opcional – campos vazios mantêm o que está no IPA.",
  "Original icon":
    "Ícone original",
  "Overview":
    "Visão geral",
  "PIN from the Apple TV":
    "PIN da Apple TV",
  "Paid":
    "Paga",
  "Paid account – no weekly limit on App IDs and no limit on apps.":
    "Conta paga – sem limite semanal de App IDs e sem limite de apps.",
  "Pair":
    "Parear",
  "Pair Apple TV or Vision Pro":
    "Parear Apple TV ou Vision Pro",
  "Pair device":
    "Parear dispositivo",
  "Pair {name}":
    "Parear {name}",
  "Paired over the network – reachable while the device is on and in the same network.":
    "Pareado pela rede – acessível enquanto o dispositivo estiver ligado e na mesma rede.",
  "Password":
    "Senha",
  "Pause":
    "Pausar",
  "Paused":
    "Pausado",
  "Photo editing":
    "Edição de fotos",
  "Pick an IPA – ModStaller signs it with your Apple account and puts it on the iPhone.":
    "Escolha um IPA – o ModStaller assina com a sua conta Apple e instala no iPhone.",
  "Pick it below and confirm the pairing on the Vision Pro.":
    "Escolha-o abaixo e confirme o pareamento no Vision Pro.",
  "Plug it in via USB and unlock it – or bring it into the same Wi-Fi.":
    "Conecte via USB e desbloqueie – ou coloque-o na mesma Wi-Fi.",
  "Preparing Anisette …":
    "Preparando o Anisette …",
  "Program":
    "Programa",
  "Read again":
    "Ler de novo",
  "Reading the IPA …":
    "Lendo o IPA …",
  "Receive beta versions":
    "Receber versões beta",
  "Recent activity":
    "Atividade recente",
  "Refresh":
    "Atualizar",
  "Registered devices":
    "Dispositivos registrados",
  "Reload":
    "Recarregar",
  "Remind me before apps expire":
    "Lembrar antes que os apps expirem",
  "Remove":
    "Remover",
  "Remove from the device":
    "Remover do dispositivo",
  "Remove {name}":
    "Remover {name}",
  "Remove {name}?":
    "Remover {name}?",
  "Removes the program, the start menu entry and the `modstaller` command.":
    "Remove o programa, a entrada do menu iniciar e o comando `modstaller`.",
  "Removing ModStaller…":
    "Removendo o ModStaller…",
  "Renew":
    "Renovar",
  "Renew apps automatically":
    "Renovar apps automaticamente",
  "Renew before it expires, from the overview or under “Apps”.":
    "Renove antes de vencer, pela visão geral ou em “Apps”.",
  "Renew due":
    "Renovar os vencidos",
  "Renew due apps":
    "Renovar os apps vencidos",
  "Renew now":
    "Renovar agora",
  "Renew {name}":
    "Renovar {name}",
  "Renewed {count} apps.":
    "{count} apps renovados.",
  "Renewing {name} in the background …":
    "Renovando {name} em segundo plano …",
  "Repair":
    "Reparar",
  "Restart":
    "Reiniciar",
  "Reuse an unused App ID …":
    "Reutilizar um App ID não usado…",
  "Revoke":
    "Revogar",
  "Revoke certificate?":
    "Revogar o certificado?",
  "SRP-6a: Apple gets proof that you know the password – not the password itself.":
    "SRP-6a: a Apple recebe a prova de que você sabe a senha – não a senha em si.",
  "Safari":
    "Safari",
  "Screen broadcast":
    "Transmissão de tela",
  "Search":
    "Pesquisar",
  "Search again":
    "Procurar de novo",
  "Set up automatically":
    "Configurar automaticamente",
  "Set up the Apple device service":
    "Configurar o serviço de dispositivos Apple",
  "Settings":
    "Configurações",
  "Settings › Privacy & Security › Developer Mode – otherwise no sideloaded app will start.":
    "Ajustes › Privacidade e Segurança › Modo de Desenvolvedor – senão nenhum app por sideload vai abrir.",
  "Share":
    "Compartilhar",
  "Show teams and certificates":
    "Mostrar equipes e certificados",
  "Sideloading for {platform}":
    "Sideload para {platform}",
  "Sideloads on the iPhone that do not come from ModStaller – from AltStore or SideStore, for instance. Renewing is not possible: the original IPA and the private key live with the other tool.":
    "Sideloads no iPhone que não vêm do ModStaller – do AltStore ou do SideStore, por exemplo. Renovar não é possível: o IPA original e a chave privada ficam na outra ferramenta.",
  "Sign & install":
    "Assinar e instalar",
  "Sign in":
    "Entrar",
  "Sign in once, then ModStaller signs by itself.":
    "Entre uma vez e depois o ModStaller assina sozinho.",
  "Sign in with Apple":
    "Entrar com a Apple",
  "Sign out":
    "Sair",
  "Sign out?":
    "Sair?",
  "Sign with":
    "Assinar com",
  "Signed by someone else":
    "Assinado por terceiros",
  "Signed by {account}":
    "Assinado por {account}",
  "Signed in":
    "Sessão iniciada",
  "Signed in.":
    "Sessão iniciada.",
  "Signed out.":
    "Sessão encerrada.",
  "Signed-in accounts":
    "Contas conectadas",
  "Siri & Shortcuts":
    "Siri e Atalhos",
  "Source missing ({path}) – renewing is not possible.":
    "Origem ausente ({path}) – não dá para renovar.",
  "Stable channel":
    "Canal estável",
  "Stable versions are always offered. With the beta channel, pre-release versions (-beta.x) are offered as well.":
    "Versões estáveis são sempre oferecidas. Com o canal beta, versões prévias (-beta.x) também.",
  "Start ModStaller":
    "Iniciar o ModStaller",
  "Start an instance inside the app now (a game, for example) – only then does it ask for memory. The unlock applies to this launch of the app only.":
    "Inicie agora uma instância dentro do app (um jogo, por exemplo) – só então ele pede memória. A liberação vale só para esta execução.",
  "Start menu":
    "Menu iniciar",
  "Start service":
    "Iniciar o serviço",
  "Start with the system":
    "Iniciar com o sistema",
  "Starting …":
    "Iniciando …",
  "Starts in the tray after you log in, without a window.":
    "Inicia na bandeja depois do login, sem janela.",
  "Still to do: {what}":
    "Ainda falta: {what}",
  "Switch off Wi-Fi":
    "Desativar Wi-Fi",
  "Switch on Wi-Fi":
    "Ativar Wi-Fi",
  "Switch to this device":
    "Mudar para este dispositivo",
  "System":
    "Sistema",
  "System check":
    "Verificação do sistema",
  "System is ready – {count} step(s) still open.":
    "O sistema está pronto – ainda {count} passo(s) em aberto.",
  "Teams and certificates of {account}":
    "Equipes e certificados de {account}",
  "Terminal":
    "Terminal",
  "That image cannot be read.":
    "Não foi possível ler esta imagem.",
  "That is not an IPA file.":
    "Isso não é um arquivo IPA.",
  "The Apple TV now shows a code on the screen. Type it in here.":
    "A Apple TV agora mostra um código na tela. Digite-o aqui.",
  "The Apple Watch app is removed – it cannot be installed this way.":
    "O app do Apple Watch é removido – ele não pode ser instalado assim.",
  "The ModStaller service in the background has stopped":
    "O serviço do ModStaller em segundo plano parou",
  "The app and its data are deleted from the device. It comes from another tool – ModStaller cannot restore it.":
    "O app e seus dados são apagados do dispositivo. Ele vem de outra ferramenta – o ModStaller não consegue restaurá-lo.",
  "The app and its data are deleted from the device. That frees one of the three slots.":
    "O app e seus dados são apagados do dispositivo. Isso libera uma das três vagas.",
  "The app runs under the unused App ID {id}.":
    "O app roda sob o App ID não usado {id}.",
  "The backend did not report in.":
    "O serviço em segundo plano não se manifestou.",
  "The backend has stopped.":
    "O serviço em segundo plano parou.",
  "The bundle ID is not valid – letters, digits and hyphens, separated by dots.":
    "O bundle ID é inválido – letras, dígitos e hífens, separados por pontos.",
  "The connected device.":
    "O dispositivo conectado.",
  "The iPhone is plugged in but locked or not paired.":
    "O iPhone está conectado, mas bloqueado ou não pareado.",
  "The next one frees up around {date}.":
    "O próximo fica livre por volta de {date}.",
  "The session is discarded. Installed apps keep running but can only be renewed after signing in again.":
    "A sessão é descartada. Os apps instalados continuam funcionando, mas só poderão ser renovados depois de entrar de novo.",
  "There already is a different `modstaller` command in ~/.local/bin – it was left untouched.":
    "Já existe outro comando `modstaller` em ~/.local/bin – ele não foi alterado.",
  "This IPA is App Store encrypted (FairPlay) and cannot be re-signed.":
    "Este IPA está criptografado pela App Store (FairPlay) e não pode ser reassinado.",
  "This IPA is an Apple TV app – pick the Apple TV as the device.":
    "Este IPA é um app de Apple TV – escolha a Apple TV como dispositivo.",
  "This IPA is an Apple Vision Pro app – pick the Vision Pro as the device.":
    "Este IPA é um app de Apple Vision Pro – escolha o Vision Pro como dispositivo.",
  "This IPA is for iPhone and iPad – an Apple TV needs the app's tvOS version.":
    "Este IPA é para iPhone e iPad – uma Apple TV precisa da versão tvOS do app.",
  "This app is made for iPad only and does not start on an {kind}.":
    "Este app é feito só para iPad e não inicia num {kind}.",
  "This does not give back weekly quota: Apple counts newly created App IDs, not existing ones. When the window is full, ModStaller falls back to a free App ID by itself.":
    "Isso não devolve cota semanal: a Apple conta os IDs de app recém-criados, não os existentes. Quando a janela está cheia, o ModStaller passa sozinho para um ID livre.",
  "This install needs {cost} – {missing} more than are left.":
    "Esta instalação precisa de {cost} – {missing} a mais do que os disponíveis.",
  "This install uses {cost} of them.":
    "Esta instalação usa {cost} deles.",
  "To renew, unlock or remove, the iPhone has to be connected and unlocked.":
    "Para renovar, liberar ou remover, o iPhone precisa estar conectado e desbloqueado.",
  "Translations that are missing fall back to English.":
    "As traduções que faltam voltam para o inglês.",
  "Try again":
    "Tentar de novo",
  "Turn on":
    "Ligar",
  "Type in the PIN the Apple TV then shows.":
    "Digite o PIN que a Apple TV mostrar.",
  "Undo":
    "Desfazer",
  "Undo changes":
    "Desfazer alterações",
  "Uninstall":
    "Desinstalar",
  "Uninstall now":
    "Desinstalar agora",
  "Unlock the iPhone and confirm “Trust”.":
    "Desbloqueie o iPhone e confirme “Confiar”.",
  "Unplug the iPhone and plug it in again.":
    "Desconecte o iPhone e conecte de novo.",
  "Unused ones are reused automatically when the weekly quota is used up – or pick one yourself when installing.":
    "Os não usados são reutilizados automaticamente quando a cota semanal acaba – ou escolha um você mesmo ao instalar.",
  "Up to date – no newer version on GitHub.":
    "Em dia – nenhuma versão mais nova no GitHub.",
  "Update check failed: {message}":
    "Falha ao procurar atualizações: {message}",
  "Update to {version}":
    "Atualizar para {version}",
  "Updates":
    "Atualizações",
  "VPN / network":
    "VPN / rede",
  "Version {version} for Linux":
    "Versão {version} para Linux",
  "Version {version} is available":
    "A versão {version} está disponível",
  "Version {version} is available – see bottom left.":
    "A versão {version} está disponível – veja embaixo à esquerda.",
  "Version {version} is ready":
    "A versão {version} está pronta",
  "Version {version} · Apple TV · from tvOS {os}":
    "Versão {version} · Apple TV · a partir do tvOS {os}",
  "Version {version} · Apple Vision Pro · from visionOS {os}":
    "Versão {version} · Apple Vision Pro · a partir do visionOS {os}",
  "Version {version} · from iOS {ios}":
    "Versão {version} · a partir do iOS {ios}",
  "View quotas and certificates":
    "Ver cotas e certificados",
  "Wait for the running task first":
    "Aguarde primeiro a tarefa em andamento",
  "Warnings":
    "Avisos",
  "What ModStaller does – live. The complete history is in the log file.":
    "O que o ModStaller faz – ao vivo. O histórico completo está no arquivo de log.",
  "What ModStaller has installed. Free accounts: at most 3 apps, valid for 7 days each.":
    "O que o ModStaller instalou. Contas gratuitas: no máximo 3 apps, válidos 7 dias cada.",
  "What's new?":
    "O que há de novo?",
  "Where ModStaller is installed":
    "Onde o ModStaller é instalado",
  "Whether an app depends on it cannot be determined without a connected iPhone.":
    "Sem um iPhone conectado não dá para saber se algum app depende dele.",
  "Wi-Fi":
    "Wi-Fi",
  "Wi-Fi is off. The iPhone is only reachable over the cable again.":
    "A Wi-Fi está desativada. O iPhone volta a ser acessível só pelo cabo.",
  "Wi-Fi is on. The iPhone can now be unplugged – ModStaller finds it in the same network.":
    "A Wi-Fi está ativada. O iPhone já pode ser desconectado – o ModStaller o encontra na mesma rede.",
  "Widget":
    "Widget",
  "Windows shows the iPhone in Explorer through its own photo driver – ModStaller needs Apple’s device service for USB. ModStaller can set it up for you: “Apple Devices” from the Microsoft Store, otherwise just Apple’s USB driver.":
    "O Windows mostra o iPhone no Explorador pelo próprio driver de fotos – o ModStaller precisa do serviço de dispositivos da Apple para USB. O ModStaller pode configurá-lo para você: “Dispositivos Apple” da Microsoft Store ou, se não der, só o driver USB da Apple.",
  "Without a connected iPhone it cannot be said which App IDs are in use right now – apps of other tools depend on them too.":
    "Sem um iPhone conectado não dá para dizer quais IDs de app estão em uso – apps de outras ferramentas também dependem deles.",
  "You find it in the start menu. You can remove it again by running this setup once more.":
    "Você o encontra no menu iniciar. Para removê-lo, execute esta instalação mais uma vez.",
  "Your Apple account signs the apps. The password is never stored or transmitted.":
    "Sua conta Apple assina os apps. A senha nunca é guardada nem transmitida.",
  "Your apps":
    "Seus apps",
  "Your sign-ins and settings were kept.":
    "Seus logins e configurações foram mantidos.",
  "and {count} more":
    "e mais {count}",
  "days before expiry":
    "dias antes de expirar",
  "expired":
    "vencido",
  "expires {date}":
    "vence em {date}",
  "expires – {when}":
    "vence – {when}",
  "extensions":
    "extensões",
  "frameworks":
    "frameworks",
  "free":
    "livre",
  "has expired":
    "venceu",
  "hours before expiry. If your iPhone is not connected then, ModStaller asks for it and renews as soon as it is.":
    "horas antes de expirar. Se o iPhone não estiver conectado nesse momento, o ModStaller pede e renova assim que estiver.",
  "in use":
    "em uso",
  "injected dylibs":
    "dylibs injetadas",
  "just now":
    "agora mesmo",
  "off":
    "desligado",
  "on":
    "ligado",
  "or":
    "ou",
  "yesterday":
    "ontem",
  "{account} now signs new installs.":
    "{account} agora assina novas instalações.",
  "{available} of {max} left":
    "{available} de {max} disponíveis",
  "{count} accounts signed in":
    "{count} contas conectadas",
  "{count} day left":
    "resta {count} dia",
  "{count} days ago":
    "há {count} dias",
  "{count} days left":
    "restam {count} dias",
  "{count} entries copied.":
    "{count} entradas copiadas.",
  "{count} free":
    "{count} livre(s)",
  "{count} h ago":
    "há {count} h",
  "{count} hour left":
    "resta {count} hora",
  "{count} hours left":
    "restam {count} horas",
  "{count} new":
    "{count} novas",
  "{count} new App ID(s) created.":
    "{count} novo(s) App ID(s) criado(s).",
  "{count} point(s) prevent sideloading.":
    "{count} ponto(s) impedem o sideload.",
  "{count} point(s) to clear up.":
    "{count} ponto(s) a resolver.",
  "{kind} via {via}":
    "{kind} via {via}",
  "{minutes} min ago":
    "há {minutes} min",
  "{name} is being renewed in the background. Try again in a moment.":
    "{name} está sendo renovado em segundo plano. Tente de novo em instantes.",
  "{name} is installed and runs for {days} days.":
    "{name} está instalado e funciona {days} dias.",
  "{name} is paired.":
    "{name} está pareada.",
  "{name} was removed from the device.":
    "{name} foi removido do dispositivo.",
  "{name} was renewed – valid for {days} days again.":
    "{name} foi renovado – válido por {days} dias de novo.",
  "{percent}% transferred":
    "{percent}% transferido",
  "{used} of {max} used":
    "{used} de {max} ocupados",
  "~/.local/bin is not on your PATH yet – the `modstaller` command works in the terminal after logging in again.":
    "~/.local/bin ainda não está no seu PATH – o comando `modstaller` funciona no terminal depois de entrar de novo na sessão.",
};

export default dict;
