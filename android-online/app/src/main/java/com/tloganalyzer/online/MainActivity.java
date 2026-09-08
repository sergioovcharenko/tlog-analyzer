package com.tloganalyzer.online;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String WEB_URL = "https://sergioovcharenko.github.io/tlog-analyzer/";
    private static final String API_URL = "https://tlog-api.onrender.com/analyze";
    private static final int FILE_CHOOSER_REQUEST = 1001;

    private WebView webView;
    private ValueCallback<Uri[]> fileChooserCallback;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private volatile boolean webAppLoaded = false;
    private volatile String pendingAnalysisJson = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        setContentView(webView);
        configureWebView();
        webView.loadUrl(WEB_URL);
        handleShareIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleShareIntent(intent);
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (url != null && url.startsWith(WEB_URL)) {
                    webAppLoaded = true;
                    injectPendingResultIfReady();
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView webView,
                                             ValueCallback<Uri[]> filePathCallback,
                                             FileChooserParams fileChooserParams) {
                if (fileChooserCallback != null) {
                    fileChooserCallback.onReceiveValue(null);
                }
                fileChooserCallback = filePathCallback;
                Intent chooserIntent;
                try {
                    chooserIntent = fileChooserParams.createIntent();
                } catch (Exception e) {
                    chooserIntent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                    chooserIntent.setType("*/*");
                    chooserIntent.addCategory(Intent.CATEGORY_OPENABLE);
                }
                startActivityForResult(chooserIntent, FILE_CHOOSER_REQUEST);
                return true;
            }
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER_REQUEST && fileChooserCallback != null) {
            Uri[] result = null;
            if (resultCode == RESULT_OK && data != null) {
                Uri uri = data.getData();
                if (uri != null) {
                    result = new Uri[]{uri};
                }
            }
            fileChooserCallback.onReceiveValue(result);
            fileChooserCallback = null;
        }
    }

    private void handleShareIntent(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) {
            return;
        }

        Uri uri;
        if (Build.VERSION.SDK_INT >= 33) {
            uri = intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri.class);
        } else {
            uri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
        }
        if (uri == null) {
            Toast.makeText(this, "Не вдалося отримати файл", Toast.LENGTH_LONG).show();
            return;
        }

        String fileName = getDisplayName(uri);
        if (fileName == null || fileName.trim().isEmpty()) {
            fileName = "shared.tlog";
        }
        final String finalFileName = fileName;

        Toast.makeText(this, "TLOG отримано. Аналізую онлайн…", Toast.LENGTH_LONG).show();
        executor.execute(() -> uploadAndAnalyze(uri, finalFileName));
    }

    private String getDisplayName(Uri uri) {
        ContentResolver resolver = getContentResolver();
        try (Cursor cursor = resolver.query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) {
                    return cursor.getString(index);
                }
            }
        } catch (Exception ignored) {
        }
        String last = uri.getLastPathSegment();
        return last != null ? last : "shared.tlog";
    }

    private void uploadAndAnalyze(Uri uri, String fileName) {
        HttpURLConnection connection = null;
        try {
            String boundary = "----TLOGBoundary" + UUID.randomUUID();
            connection = (HttpURLConnection) new URL(API_URL).openConnection();
            connection.setConnectTimeout(30000);
            connection.setReadTimeout(180000);
            connection.setDoOutput(true);
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
            connection.setRequestProperty("Accept", "application/json");

            try (DataOutputStream out = new DataOutputStream(connection.getOutputStream());
                 InputStream in = getContentResolver().openInputStream(uri)) {

                if (in == null) {
                    throw new IllegalStateException("Файл недоступний для читання");
                }

                out.writeBytes("--" + boundary + "\r\n");
                out.write(("Content-Disposition: form-data; name=\"file\"; filename=\"" +
                        escapeFileName(fileName) + "\"\r\n").getBytes(StandardCharsets.UTF_8));
                out.writeBytes("Content-Type: application/octet-stream\r\n\r\n");

                byte[] buffer = new byte[64 * 1024];
                int read;
                while ((read = in.read(buffer)) != -1) {
                    out.write(buffer, 0, read);
                }
                out.writeBytes("\r\n--" + boundary + "--\r\n");
                out.flush();
            }

            int code = connection.getResponseCode();
            InputStream responseStream = code >= 200 && code < 300
                    ? connection.getInputStream()
                    : connection.getErrorStream();
            String response = readAll(responseStream);

            if (code < 200 || code >= 300) {
                throw new IllegalStateException("Сервер повернув HTTP " + code + ": " + response);
            }

            pendingAnalysisJson = response;
            runOnUiThread(() -> {
                Toast.makeText(this, "Аналіз завершено", Toast.LENGTH_SHORT).show();
                injectPendingResultIfReady();
            });
        } catch (Exception e) {
            final String message = e.getMessage() == null ? e.toString() : e.getMessage();
            runOnUiThread(() -> Toast.makeText(this,
                    "Помилка аналізу: " + message,
                    Toast.LENGTH_LONG).show());
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private void injectPendingResultIfReady() {
        String json = pendingAnalysisJson;
        if (!webAppLoaded || json == null || json.trim().isEmpty()) {
            return;
        }
        pendingAnalysisJson = null;
        String quoted = JSONObject.quote(json);
        String script = "(function(){try{" +
                "var d=JSON.parse(" + quoted + ");" +
                "if(typeof renderResults==='function'){renderResults(d);window.scrollTo(0,0);}" +
                "else{console.error('renderResults unavailable');}" +
                "}catch(e){console.error(e);}})();";
        webView.evaluateJavascript(script, null);
    }

    private String readAll(InputStream inputStream) throws Exception {
        if (inputStream == null) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line).append('\n');
            }
        }
        return sb.toString();
    }

    private String escapeFileName(String value) {
        return value.replace("\\", "_").replace("\"", "_").replace("\r", "_").replace("\n", "_");
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }
}
