# Gera o APK do app Coroinhas (apk\Coroinhas.apk).
#   powershell -ExecutionPolicy Bypass -File apk\construir.ps1
# Na 1ª vez baixa o Android SDK (linha de comando) e o Gradle (~2 GB, para %LOCALAPPDATA%) e cria a chave de assinatura.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"          # Invoke-WebRequest fica muito mais rápido sem a barra
Set-Location $PSScriptRoot

$GRADLE = "8.11.1"
$FERRAMENTAS = Join-Path $env:LOCALAPPDATA "CoroinhasApk\ferramentas"
$SDK = Join-Path $env:LOCALAPPDATA "Android\Sdk"
New-Item -ItemType Directory -Force $FERRAMENTAS | Out-Null

function Passo($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }

# ---- Java 17+
if (-not $env:JAVA_HOME) {
    $jdk = Get-ChildItem "C:\Program Files\Java", "C:\Program Files\Eclipse Adoptium", "C:\Program Files\Microsoft" -Directory -Filter "jdk*" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if (-not $jdk) { throw "Não achei o JDK 17+. Instale em https://adoptium.net e rode de novo." }
    $env:JAVA_HOME = $jdk.FullName
}
Write-Host "Java: $env:JAVA_HOME"

# ---- Android SDK (só as ferramentas de linha de comando, sem Android Studio)
$sdkmanager = Join-Path $SDK "cmdline-tools\latest\bin\sdkmanager.bat"
if (-not (Test-Path $sdkmanager)) {
    Passo "Baixando o Android SDK (ferramentas de linha de comando)"
    $zip = Join-Path $FERRAMENTAS "cmdline-tools.zip"
    Invoke-WebRequest "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip" -OutFile $zip
    $tmp = Join-Path $FERRAMENTAS "cmdline-tools-tmp"
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    Expand-Archive $zip $tmp
    New-Item -ItemType Directory -Force (Join-Path $SDK "cmdline-tools") | Out-Null
    Move-Item (Join-Path $tmp "cmdline-tools") (Join-Path $SDK "cmdline-tools\latest")
    Remove-Item -Recurse -Force $tmp, $zip
}
if (-not (Test-Path (Join-Path $SDK "platforms\android-35"))) {
    Passo "Instalando Android 15 (API 35) e build-tools — aceitando as licenças do Android SDK"
    ("y`n" * 30) | & $sdkmanager --sdk_root="$SDK" --licenses | Out-Null
    & $sdkmanager --sdk_root="$SDK" "platforms;android-35" "build-tools;35.0.0" "platform-tools"
}
$env:ANDROID_HOME = $SDK
Set-Content -Encoding ascii local.properties "sdk.dir=$($SDK -replace '\\', '/')"

# ---- Gradle wrapper (gradlew.bat)
if (-not (Test-Path "gradlew.bat")) {
    Passo "Baixando o Gradle $GRADLE"
    $gdir = Join-Path $FERRAMENTAS "gradle-$GRADLE"
    if (-not (Test-Path $gdir)) {
        $zip = Join-Path $FERRAMENTAS "gradle.zip"
        Invoke-WebRequest "https://services.gradle.org/distributions/gradle-$GRADLE-bin.zip" -OutFile $zip
        Expand-Archive $zip $FERRAMENTAS
        Remove-Item $zip
    }
    & (Join-Path $gdir "bin\gradle.bat") wrapper --gradle-version $GRADLE --no-daemon
    if ($LASTEXITCODE) { throw "Falhou ao criar o gradlew." }
}

# ---- Chave de assinatura (uma vez; guarde a pasta apk\assinatura)
if (-not (Test-Path "assinatura\assinatura.properties")) {
    Passo "Criando a chave de assinatura em apk\assinatura (guarde uma cópia!)"
    New-Item -ItemType Directory -Force assinatura | Out-Null
    $senha = [guid]::NewGuid().ToString("N")
    & (Join-Path $env:JAVA_HOME "bin\keytool.exe") -genkeypair -keystore assinatura\coroinhas.jks -alias coroinhas `
        -keyalg RSA -keysize 2048 -validity 10000 -storepass $senha -keypass $senha `
        -dname "CN=Coroinhas, O=Pastoral dos Coroinhas, L=Rio de Janeiro, C=BR"
    if ($LASTEXITCODE) { throw "Falhou ao criar a chave." }
    Set-Content -Encoding ascii assinatura\assinatura.properties "arquivo=coroinhas.jks`nalias=coroinhas`nsenha=$senha"
}

# ---- Build
Passo "Gerando o APK (a 1ª vez demora: baixa o Python para Android e as bibliotecas)"
& .\gradlew.bat assembleRelease
if ($LASTEXITCODE) { throw "O build falhou (veja as mensagens acima)." }

$apk = Join-Path $env:LOCALAPPDATA "CoroinhasApk\build\app\outputs\apk\release\app-release.apk"
Copy-Item $apk "Coroinhas.apk" -Force
$mb = [math]::Round((Get-Item "Coroinhas.apk").Length / 1MB, 1)
Write-Host "`nPronto: $(Join-Path $PSScriptRoot 'Coroinhas.apk') ($mb MB)" -ForegroundColor Green
Write-Host "Passe para o celular (cabo USB, Google Drive, WhatsApp para você mesmo...) e toque nele para instalar."
