package com.tloganalyzer.offline

import android.annotation.SuppressLint
import android.app.Activity
import android.content.ContentValues
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

class MainActivity : Activity() {
    private lateinit var webView: WebView
    private var pendingUri: Uri? = null
    private var pageReady = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        pendingUri = extractIncomingUri(intent)
        setupWebView()
        startPythonAndOpenUi()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        pendingUri = extractIncomingUri(intent)
        if (pageReady) consumePendingShare()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        webView = WebView(this)
        setContentView(webView)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = true
        webView.settings.allowContentAccess = true
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                pageReady = true
                consumePendingShare()
            }
        }
    }

    private fun startPythonAndOpenUi() {
        Thread {
            try {
                if (!Python.isStarted()) Python.start(AndroidPlatform(this))
                Python.getInstance().getModule("bridge").callAttr("start_server")
                waitForServer()
                runOnUiThread { webView.loadUrl("http://127.0.0.1:8765/") }
            } catch (e: Exception) {
                showFatal("Не вдалося запустити офлайн-аналізатор: ${e.message}")
            }
        }.start()
    }

    private fun waitForServer() {
        var lastError: Exception? = null
        repeat(80) {
            try {
                val c = URL("http://127.0.0.1:8765/health").openConnection() as HttpURLConnection
                c.connectTimeout = 500
                c.readTimeout = 500
                c.requestMethod = "GET"
                if (c.responseCode == 200) {
                    c.disconnect()
                    return
                }
                c.disconnect()
            } catch (e: Exception) {
                lastError = e
            }
            Thread.sleep(250)
        }
        throw IllegalStateException("Локальний сервер не відповідає", lastError)
    }

    private fun extractIncomingUri(src: Intent?): Uri? {
        if (src == null) return null
        return when (src.action) {
            Intent.ACTION_SEND -> src.getParcelableExtra(Intent.EXTRA_STREAM)
            Intent.ACTION_VIEW -> src.data
            else -> null
        }
    }

    private fun consumePendingShare() {
        val uri = pendingUri ?: return
        pendingUri = null
        pageReady = false
        showAnalyzingState()

        Thread {
            try {
                val name = displayName(uri).ifBlank { "shared-${System.currentTimeMillis()}.tlog" }
                if (!name.lowercase().endsWith(".tlog") && !name.lowercase().endsWith(".bin")) {
                    throw IllegalArgumentException("Підтримуються лише .tlog та .bin")
                }
                val localFile = copyToCache(uri, name)
                saveToDownloads(uri, name)
                val resultJson = postForAnalysis(localFile, name)
                runOnUiThread {
                    val js = """
                        (function(){
                          try {
                            const data = $resultJson;
                            const upload = document.querySelector('.upload'); if (upload) upload.style.display='none';
                            const fileBox = document.querySelector('.file-box'); if (fileBox) fileBox.style.display='none';
                            const btn = document.querySelector('.analyze'); if (btn) btn.style.display='none';
                            if (typeof renderResults === 'function') {
                              renderResults(data);
                              window.scrollTo(0,0);
                            } else {
                              document.body.innerHTML='<pre style="color:white;padding:20px">renderResults() не знайдено</pre>';
                            }
                          } catch(e) {
                            document.body.innerHTML='<pre style="color:white;padding:20px">'+String(e)+'</pre>';
                          }
                        })();
                    """.trimIndent()
                    webView.evaluateJavascript(js, null)
                    pageReady = true
                }
            } catch (e: Exception) {
                runOnUiThread {
                    val msg = JSONObject.quote("Помилка аналізу: ${e.message}")
                    webView.evaluateJavascript("alert($msg);", null)
                    pageReady = true
                }
            }
        }.start()
    }

    private fun showAnalyzingState() {
        val js = """
            (function(){
              const p=document.querySelector('.progress-container'); if(p) p.style.display='block';
              const f=document.querySelector('.progress-fill'); if(f) f.style.width='60%';
              const h=document.querySelector('.progress-header'); if(h) h.innerHTML='<span>Офлайн-аналіз TLOG...</span><span>60%</span>';
              const u=document.querySelector('.upload'); if(u) u.style.display='none';
            })();
        """.trimIndent()
        webView.evaluateJavascript(js, null)
    }

    private fun displayName(uri: Uri): String {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) {
                val i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (i >= 0) return c.getString(i) ?: ""
            }
        }
        return uri.lastPathSegment?.substringAfterLast('/') ?: ""
    }

    private fun copyToCache(uri: Uri, name: String): File {
        val dir = File(cacheDir, "shared").apply { mkdirs() }
        val out = File(dir, name.replace(Regex("[^A-Za-z0-9._ -]"), "_"))
        contentResolver.openInputStream(uri).use { input ->
            requireNotNull(input) { "Не вдалося прочитати файл" }
            FileOutputStream(out).use { output -> input.copyTo(output, 1024 * 128) }
        }
        return out
    }

    private fun saveToDownloads(uri: Uri, name: String) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return
        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, name)
            put(MediaStore.Downloads.MIME_TYPE, "application/octet-stream")
            put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/TLOG Receiver")
            put(MediaStore.Downloads.IS_PENDING, 1)
        }
        val target = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: return
        try {
            contentResolver.openInputStream(uri).use { input ->
                contentResolver.openOutputStream(target).use { output ->
                    if (input != null && output != null) input.copyTo(output, 1024 * 128)
                }
            }
            values.clear()
            values.put(MediaStore.Downloads.IS_PENDING, 0)
            contentResolver.update(target, values, null, null)
        } catch (e: Exception) {
            contentResolver.delete(target, null, null)
        }
    }

    private fun postForAnalysis(file: File, originalName: String): String {
        val boundary = "----TLOG-${UUID.randomUUID()}"
        val c = URL("http://127.0.0.1:8765/analyze").openConnection() as HttpURLConnection
        c.requestMethod = "POST"
        c.doOutput = true
        c.connectTimeout = 10_000
        c.readTimeout = 240_000
        c.setChunkedStreamingMode(1024 * 128)
        c.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")

        BufferedOutputStream(c.outputStream).use { out ->
            out.write("--$boundary\r\n".toByteArray())
            out.write("Content-Disposition: form-data; name=\"file\"; filename=\"$originalName\"\r\n".toByteArray())
            out.write("Content-Type: application/octet-stream\r\n\r\n".toByteArray())
            BufferedInputStream(file.inputStream()).use { input -> input.copyTo(out, 1024 * 128) }
            out.write("\r\n--$boundary--\r\n".toByteArray())
            out.flush()
        }

        val code = c.responseCode
        val stream = if (code in 200..299) c.inputStream else c.errorStream
        val text = stream.bufferedReader().use { it.readText() }
        c.disconnect()
        if (code !in 200..299) throw IllegalStateException("HTTP $code: $text")
        return text
    }

    private fun showFatal(message: String) {
        runOnUiThread {
            webView.loadDataWithBaseURL(
                null,
                "<html><body style='background:#0a0d11;color:white;font-family:sans-serif;padding:24px'><h2>TLOG Analyzer Offline</h2><p>${message}</p></body></html>",
                "text/html",
                "UTF-8",
                null
            )
        }
    }
}
