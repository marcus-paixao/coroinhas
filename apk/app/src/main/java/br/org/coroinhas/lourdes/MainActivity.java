package br.org.coroinhas.lourdes;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentValues;
import android.content.Intent;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Abre o sistema dos Coroinhas: sobe o servidor Flask (Python, via Chaquopy) dentro do app
 * e mostra as telas num WebView. Os dados ficam só neste celular.
 */
public class MainActivity extends Activity {
    private static final int AZUL = 0xFF12215F;
    private static final int PEDIDO_ARQUIVO = 1;

    private WebView web;
    private ValueCallback<Uri[]> escolhaArquivo;

    @Override
    protected void onCreate(Bundle estado) {
        super.onCreate(estado);
        FrameLayout raiz = new FrameLayout(this);
        raiz.setBackgroundColor(AZUL);
        // Android 15 desenha atrás das barras do sistema: afasta o conteúdo delas (e do teclado)
        raiz.setOnApplyWindowInsetsListener((v, insets) -> {
            Insets i = insets.getInsets(android.view.WindowInsets.Type.systemBars() | android.view.WindowInsets.Type.ime());
            v.setPadding(i.left, i.top, i.right, i.bottom);
            return android.view.WindowInsets.CONSUMED;
        });

        web = new WebView(this);
        web.setBackgroundColor(AZUL);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);       // sem o "esticar" do Android ao chegar no fim da rolagem
        web.setVerticalScrollBarEnabled(false);
        web.setHorizontalScrollBarEnabled(false);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setSupportZoom(false);                              // nada de pinça/duplo toque dando zoom na tela
        web.addJavascriptInterface(new Ponte(), "Android");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                Uri u = req.getUrl();
                if ("127.0.0.1".equals(u.getHost())) return false;
                startActivity(new Intent(Intent.ACTION_VIEW, u));     // link externo: abre no navegador
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (escolhaArquivo != null) escolhaArquivo.onReceiveValue(null);
                escolhaArquivo = callback;
                // "*/*": o Android não entende ".xlsx" como tipo; quem confere a extensão é o servidor
                Intent i = new Intent(Intent.ACTION_GET_CONTENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*");
                startActivityForResult(Intent.createChooser(i, "Escolher arquivo"), PEDIDO_ARQUIVO);
                return true;
            }
        });
        raiz.addView(web);
        setContentView(raiz);

        web.loadDataWithBaseURL(null, TELA_ABRINDO, "text/html", "utf-8", null);
        new Thread(this::iniciarSistema, "iniciar").start();
    }

    private void iniciarSistema() {
        try {
            File sistema = new File(getFilesDir(), "sistema");
            File dados = new File(getFilesDir(), "dados");
            prepararSistema(sistema);
            if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
            int porta = Python.getInstance().getModule("servidor")
                    .callAttr("iniciar", sistema.getAbsolutePath(), dados.getAbsolutePath()).toInt();
            runOnUiThread(() -> web.loadUrl("http://127.0.0.1:" + porta + "/"));
        } catch (Throwable e) {
            String msg = String.valueOf(e.getMessage()).replace("&", "&amp;").replace("<", "&lt;");
            runOnUiThread(() -> web.loadDataWithBaseURL(null, TELA_ERRO.replace("{erro}", msg), "text/html", "utf-8", null));
        }
    }

    /** Descompacta o sistema (assets/sistema.zip) na 1ª abertura de cada versão instalada. */
    private void prepararSistema(File destino) throws Exception {
        String versao = String.valueOf(getPackageManager().getPackageInfo(getPackageName(), 0).lastUpdateTime);
        File marca = new File(destino, ".versao");
        if (marca.exists() && versao.equals(new String(Files.readAllBytes(marca.toPath())))) return;
        apagar(destino);
        String base = destino.getCanonicalPath() + File.separator;
        try (ZipInputStream zip = new ZipInputStream(getAssets().open("sistema.zip"))) {
            byte[] buf = new byte[64 * 1024];
            for (ZipEntry e; (e = zip.getNextEntry()) != null; ) {
                File f = new File(destino, e.getName());
                if (!f.getCanonicalPath().startsWith(base)) throw new IOException("Arquivo inválido no pacote: " + e.getName());
                if (e.isDirectory()) { f.mkdirs(); continue; }
                f.getParentFile().mkdirs();
                try (OutputStream out = new FileOutputStream(f)) {
                    for (int n; (n = zip.read(buf)) > 0; ) out.write(buf, 0, n);
                }
            }
        }
        Files.write(marca.toPath(), versao.getBytes());
    }

    private static void apagar(File f) {
        File[] filhos = f.listFiles();
        if (filhos != null) for (File c : filhos) apagar(c);
        f.delete();
    }

    @Override
    protected void onActivityResult(int pedido, int resultado, Intent dados) {
        if (pedido == PEDIDO_ARQUIVO && escolhaArquivo != null) {
            escolhaArquivo.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultado, dados));
            escolhaArquivo = null;
            return;
        }
        super.onActivityResult(pedido, resultado, dados);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onPause() {
        super.onPause();
        CookieManager.getInstance().flush();      // mantém o login salvo
    }

    /** Salva na pasta Downloads/Coroinhas e devolve o endereço do arquivo. */
    private Uri salvarEmDownloads(String nome, String tipo, byte[] conteudo) throws IOException {
        ContentValues v = new ContentValues();
        v.put(MediaStore.Downloads.DISPLAY_NAME, nome);
        v.put(MediaStore.Downloads.MIME_TYPE, tipo);
        v.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Coroinhas");
        Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
        if (uri == null) throw new IOException("Não consegui criar o arquivo em Downloads.");
        try (OutputStream out = getContentResolver().openOutputStream(uri)) {
            out.write(conteudo);
        }
        return uri;
    }

    private void avisar(String msg) {
        runOnUiThread(() -> Toast.makeText(this, msg, Toast.LENGTH_LONG).show());
    }

    /** Funções chamadas pelo JavaScript das telas (window.Android, ver static/js/comum.js). */
    private class Ponte {
        @JavascriptInterface
        public void salvar(String nome, String tipo, String base64) {
            try {
                salvarEmDownloads(nome, tipo, Base64.decode(base64, Base64.DEFAULT));
                avisar("Salvo em Downloads/Coroinhas: " + nome);
            } catch (Exception e) {
                avisar("Não consegui salvar: " + e.getMessage());
            }
        }

        @JavascriptInterface
        public void compartilhar(String nome, String tipo, String base64, String titulo) {
            try {
                Uri uri = salvarEmDownloads(nome, tipo, Base64.decode(base64, Base64.DEFAULT));
                Intent i = new Intent(Intent.ACTION_SEND).setType(tipo)
                        .putExtra(Intent.EXTRA_STREAM, uri)
                        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                i.setClipData(ClipData.newRawUri(nome, uri));
                runOnUiThread(() -> startActivity(Intent.createChooser(i, titulo)));
            } catch (Exception e) {
                avisar("Não consegui compartilhar: " + e.getMessage());
            }
        }

        @JavascriptInterface
        public void copiar(String texto) {
            runOnUiThread(() -> ((ClipboardManager) getSystemService(CLIPBOARD_SERVICE))
                    .setPrimaryClip(ClipData.newPlainText("Escala dos Coroinhas", texto)));
        }
    }

    private static final String ESTILO = "<meta name='viewport' content='width=device-width,initial-scale=1'><style>"
            + "body{margin:0;height:100vh;display:grid;place-items:center;background:#12215f;color:#fff;font-family:sans-serif;text-align:center}"
            + "p{opacity:.8}code{display:block;margin:16px;padding:12px;border-radius:12px;background:rgba(255,255,255,.1);font-size:12px;white-space:pre-wrap;text-align:left}"
            + "</style>";
    private static final String TELA_ABRINDO = ESTILO
            + "<div><div style='font-size:48px'>🕯️</div><h2>Coroinhas</h2><p>Abrindo…</p></div>";
    private static final String TELA_ERRO = ESTILO
            + "<div><div style='font-size:48px'>😕</div><h2>Não consegui abrir o sistema</h2><p>Feche e abra o app de novo.</p><code>{erro}</code></div>";
}
