; Eigene Schritte im NSIS-Setup (electron-builder bindet build/installer.nsh
; selbst ein, siehe buildResources in electron-builder.yml).
;
; 1. Sprache: Die im Sprachdialog des Setups gewaehlte Sprache wird zur
;    Startsprache der App. Das Setup legt dafuer language.json in den
;    userData-Ordner; die App liest sie beim ersten Start genau einmal
;    (gui/electron/langseed.cjs) und loescht sie dann. Updates schreiben
;    nichts - die eigene Wahl in den Einstellungen bleibt.
;
; 2. Apple-Geraetedienst: Ohne ihn sieht ModStaller kein iPhone, obwohl der
;    Explorer es ueber den Windows-Fototreiber zeigt. Fehlt er (oder steht er),
;    richtet das Setup ihn auf Wunsch gleich ein - mit demselben Code wie der
;    Button in der App: `modstaller-backend.exe usb-setup` (modstaller/
;    winsetup.py: "Apple Devices" per winget, sonst nur Apples Treiber).
;    Klappt das nicht, bleibt der Microsoft Store als Ausweg.
;
; Die Datei ist UTF-8 mit BOM - sonst liest NSIS die Umlaute falsch.

; LangString mit Sprachnummern (LCID), wie electron-builder es fuer seine
; eigenen Texte macht: die Sprachen sind hier noch nicht geladen.
LangString msAppleServiceSetup 1033 "ModStaller needs Apple's device service to reach the iPhone over USB - it is not set up on this PC.$\r$\nWindows Explorer shows the iPhone without it, ModStaller does not.$\r$\n$\r$\nSet it up automatically now? (Apple Devices from the Microsoft Store, otherwise just Apple's USB driver - Windows may ask for confirmation.)"
LangString msAppleServiceSetup 1031 "ModStaller braucht Apples Gerätedienst, um das iPhone per USB zu erreichen - er ist auf diesem PC nicht eingerichtet.$\r$\nDer Windows-Explorer zeigt das iPhone auch ohne ihn an, ModStaller nicht.$\r$\n$\r$\nJetzt automatisch einrichten? („Apple-Geräte“ aus dem Microsoft Store, sonst nur Apples USB-Treiber - Windows fragt eventuell nach.)"
LangString msAppleServiceSetup 1036 "ModStaller a besoin du service d'appareils d'Apple pour accéder à l'iPhone en USB - il n'est pas configuré sur ce PC.$\r$\nL'Explorateur Windows affiche l'iPhone sans lui, ModStaller non.$\r$\n$\r$\nLe configurer automatiquement maintenant ? (« Appareils Apple » depuis le Microsoft Store, sinon seulement le pilote USB d'Apple - Windows peut demander une confirmation.)"
LangString msAppleServiceSetup 3082 "ModStaller necesita el servicio de dispositivos de Apple para acceder al iPhone por USB, y no está configurado en este PC.$\r$\nEl Explorador de Windows muestra el iPhone sin él; ModStaller no.$\r$\n$\r$\n¿Configurarlo automáticamente ahora? («Dispositivos Apple» desde Microsoft Store o, si no, solo el controlador USB de Apple; Windows puede pedir confirmación.)"
LangString msAppleServiceSetup 1040 "ModStaller ha bisogno del servizio dispositivi di Apple per raggiungere l'iPhone via USB, ma su questo PC non è configurato.$\r$\nEsplora file di Windows mostra l'iPhone anche senza, ModStaller no.$\r$\n$\r$\nConfigurarlo automaticamente ora? («Dispositivi Apple» dal Microsoft Store, altrimenti solo il driver USB di Apple; Windows potrebbe chiedere una conferma.)"
LangString msAppleServiceSetup 1046 "O ModStaller precisa do serviço de dispositivos da Apple para acessar o iPhone via USB - ele não está configurado neste PC.$\r$\nO Explorador do Windows mostra o iPhone sem ele, o ModStaller não.$\r$\n$\r$\nConfigurar automaticamente agora? (“Dispositivos Apple” da Microsoft Store ou, se não der, só o driver USB da Apple - o Windows pode pedir confirmação.)"
LangString msAppleServiceSetup 1043 "ModStaller heeft de apparaatdienst van Apple nodig om de iPhone via USB te bereiken - die is op deze pc niet ingesteld.$\r$\nWindows Verkenner toont de iPhone ook zonder, ModStaller niet.$\r$\n$\r$\nNu automatisch instellen? (‘Apple-apparaten’ uit de Microsoft Store, anders alleen het USB-stuurprogramma van Apple - Windows vraagt mogelijk om bevestiging.)"

LangString msAppleServiceWorking 1033 "Setting up the Apple device service ..."
LangString msAppleServiceWorking 1031 "Apple-Gerätedienst wird eingerichtet ..."
LangString msAppleServiceWorking 1036 "Configuration du service d'appareils Apple ..."
LangString msAppleServiceWorking 3082 "Configurando el servicio de dispositivos Apple ..."
LangString msAppleServiceWorking 1040 "Configurazione del servizio dispositivi Apple ..."
LangString msAppleServiceWorking 1046 "Configurando o serviço de dispositivos Apple ..."
LangString msAppleServiceWorking 1043 "Apple-apparaatdienst wordt ingesteld ..."

LangString msAppleServiceFailed 1033 "The Apple device service could not be set up automatically (details in the installer log).$\r$\n$\r$\nOpen $\"Apple Devices$\" in the Microsoft Store instead? ModStaller also offers the automatic setup again on its overview."
LangString msAppleServiceFailed 1031 "Der Apple-Gerätedienst ließ sich nicht automatisch einrichten (Details im Setup-Protokoll).$\r$\n$\r$\nStattdessen „Apple-Geräte“ im Microsoft Store öffnen? ModStaller bietet das automatische Einrichten auch in der Übersicht erneut an."
LangString msAppleServiceFailed 1036 "Le service d'appareils Apple n'a pas pu être configuré automatiquement (détails dans le journal d'installation).$\r$\n$\r$\nOuvrir plutôt « Appareils Apple » dans le Microsoft Store ? ModStaller propose aussi à nouveau la configuration automatique dans sa vue d'ensemble."
LangString msAppleServiceFailed 3082 "No se pudo configurar automáticamente el servicio de dispositivos Apple (detalles en el registro de instalación).$\r$\n$\r$\n¿Abrir «Dispositivos Apple» en Microsoft Store? ModStaller también vuelve a ofrecer la configuración automática en su resumen."
LangString msAppleServiceFailed 1040 "Non è stato possibile configurare automaticamente il servizio dispositivi Apple (dettagli nel registro di installazione).$\r$\n$\r$\nAprire invece «Dispositivi Apple» nel Microsoft Store? ModStaller ripropone la configurazione automatica anche nella panoramica."
LangString msAppleServiceFailed 1046 "Não foi possível configurar automaticamente o serviço de dispositivos da Apple (detalhes no registro da instalação).$\r$\n$\r$\nAbrir “Dispositivos Apple” na Microsoft Store? O ModStaller também oferece a configuração automática de novo na visão geral."
LangString msAppleServiceFailed 1043 "De Apple-apparaatdienst kon niet automatisch worden ingesteld (details in het installatielogboek).$\r$\n$\r$\n‘Apple-apparaten’ in de Microsoft Store openen? ModStaller biedt het automatisch instellen ook opnieuw aan in het overzicht."

!macro msWriteLanguageSeed
  ; LCID des Setup-Sprachdialogs -> Sprachcode der App (gui/src/lib/i18n.svelte.ts).
  StrCpy $R0 "en"
  ${Switch} $LANGUAGE
    ${Case} 1031
      StrCpy $R0 "de"
      ${Break}
    ${Case} 1036
      StrCpy $R0 "fr"
      ${Break}
    ${Case} 1034
    ${Case} 3082
      StrCpy $R0 "es"
      ${Break}
    ${Case} 1040
      StrCpy $R0 "it"
      ${Break}
    ${Case} 1046
      StrCpy $R0 "pt-BR"
      ${Break}
    ${Case} 1043
      StrCpy $R0 "nl"
      ${Break}
  ${EndSwitch}
  ; Derselbe Ordner wie app.getPath("userData") - pro Benutzer installiert,
  ; also das Roaming-Profil dessen, der das Setup ausfuehrt.
  CreateDirectory "$APPDATA\${PRODUCT_NAME}"
  ClearErrors
  FileOpen $R1 "$APPDATA\${PRODUCT_NAME}\language.json" w
  ${IfNot} ${Errors}
    FileWrite $R1 '{"language":"$R0"}'
    FileClose $R1
  ${EndIf}
!macroend

!macro msCheckAppleService
  ; Dieselbe Pruefung wie in der App (modstaller/winsetup.py). Exit-Code von
  ; "usb-setup --check": 0 laeuft, 2 installiert aber gestoppt, 3 fehlt.
  ; Alles andere (Backend startet nicht) heisst: nicht nachfragen.
  StrCpy $R2 "$INSTDIR\resources\backend\modstaller-backend.exe"
  nsExec::ExecToStack `"$R2" usb-setup --check`
  Pop $R0
  Pop $R1
  ${If} $R0 == "2"
  ${OrIf} $R0 == "3"
    MessageBox MB_YESNO|MB_ICONQUESTION "$(msAppleServiceSetup)" IDNO msAppleServiceDone
    DetailPrint "$(msAppleServiceWorking)"
    ; Die Schritte landen im Protokoll des Setups ("Details anzeigen").
    nsExec::ExecToLog `"$R2" usb-setup`
    Pop $R0
    ${If} $R0 != "0"
      MessageBox MB_YESNO|MB_ICONEXCLAMATION "$(msAppleServiceFailed)" IDNO msAppleServiceDone
      ExecShell "open" "ms-windows-store://pdp/?productid=9NP83LWLPZ9K"
    ${EndIf}
    msAppleServiceDone:
  ${EndIf}
!macroend

!macro customInstall
  ; Updates (auch die stillen von electron-updater) lassen beides aus.
  ${ifNot} ${isUpdated}
    !insertmacro msWriteLanguageSeed
    ${IfNot} ${Silent}
      !insertmacro msCheckAppleService
    ${EndIf}
  ${endIf}
!macroend

; 3. Autostart: Den Eintrag unter Run legt die App selbst an (Einstellungen >
;    Hintergrund, app.setLoginItemSettings mit dem Namen "ModStaller"). Beim
;    Deinstallieren muss er mit weg - sonst startet Windows eine Datei, die es
;    nicht mehr gibt. Nicht bei Updates: da laeuft das alte Deinstallations-
;    programm auch, und der Autostart soll bleiben.
!macro customUnInstall
  ${ifNot} ${isUpdated}
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "ModStaller"
  ${endIf}
!macroend
