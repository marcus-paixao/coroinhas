# App Android (APK) · Coroinhas

O mesmo sistema do site, rodando **dentro do celular e sem internet**. O app sobe o Flask (Python, via
[Chaquopy](https://chaquo.com/chaquopy/)) em `127.0.0.1` e mostra as telas num WebView. O código é o da raiz do
projeto (`app.py`, `acesso.py`, `projetos/`, `templates/`, `static/`), empacotado a cada build: mudou o site,
rode o build de novo e o APK sai atualizado.

**Os dados do celular são separados dos do PC.** Para levar de um para o outro: *Ajustes & Backup → Baixar backup*
de um lado e *Restaurar backup* do outro. Restaurar substitui tudo o que estiver no aparelho de destino.

## Gerar o APK (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File apk\construir.ps1
```

Na primeira vez, o script:
- baixa o Android SDK (linha de comando) e o Gradle, uns 2 GB em `%LOCALAPPDATA%`, e aceita as licenças do Android SDK;
- cria a chave de assinatura em `apk\assinatura\`.

Depois ele gera `apk\Coroinhas.apk`, com uns 25 a 35 MB. O que é necessário no PC: JDK 17+ e Python 3.11 (o `py -3.11`, que o Chaquopy usa no build).

## Instalar no celular

1. Passe o `Coroinhas.apk` para o celular (cabo USB, Google Drive, WhatsApp para você mesmo…).
2. Toque no arquivo. O Android pede para permitir "instalar apps desconhecidos" para o app que abriu o arquivo (Arquivos, Drive…).
   O Play Protect pode avisar que o app não é conhecido: é normal para um app que não veio da Play Store.
3. Na primeira abertura, crie a conta de coordenador. As outras contas são criadas em *Minha conta*.

## Atualizar

Rode o `construir.ps1` de novo e instale o APK novo **por cima** do antigo: os dados são mantidos.
A versão é numerada sozinha pela data do build (`versionCode`/`versionName` em `app/build.gradle`).

> ⚠️ **Guarde a pasta `apk\assinatura\`**. Sem ela, o Android não aceita a atualização, e a única saída é
> desinstalar, o que **apaga os dados do celular**. Desinstalar sempre apaga os dados: baixe um backup antes.

## Como funciona

| Arquivo | O que faz |
|---|---|
| `app/build.gradle` | Empacota o sistema em `sistema.zip` (assets), instala Flask e openpyxl para Android (Python 3.11), assina |
| `app/src/main/python/servidor.py` | Sobe o Flask em 127.0.0.1:8765 numa thread (`COROINHAS_APK=1`, dados na pasta interna do app) |
| `app/src/main/java/.../MainActivity.java` | WebView, escolher arquivo, salvar em Downloads/Coroinhas, compartilhar (WhatsApp), copiar texto, botão voltar |
| `construir.ps1` | Prepara as ferramentas na 1ª vez e gera `Coroinhas.apk` |

No JavaScript, `window.Android` (usado em `static/js/comum.js`: `App.baixar`, `App.compartilhar`, `App.copiar`) só existe dentro do app.
No navegador, as mesmas funções usam download, compartilhamento e área de transferência da Web.
Com `COROINHAS_APK=1`, a tela de entrar permite criar o primeiro coordenador quando não há nenhuma conta.
No PC isso continua sendo feito pelo terminal.
