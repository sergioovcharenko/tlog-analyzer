package ua.tloganalyzer.offline

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.webkit.*
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.ByteArrayInputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private var fileCallback: ValueCallback<Array<Uri>>? = null
    private val io = Executors.newSingleThreadExecutor()

    private val filePicker = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val callback = fileCallback ?: return@registerForActivityResult
        fileCallback = null
        if (result.resultCode != Activity.RESULT_OK) {
            callback.onReceiveValue(null)
            return@registerForActivityResult
        }
        val data = result.data
        val uris = when {
            data?.clipData != null -> Array(data.clipData!!.itemCount) { i ->
                data.clipData!!.getItemAt(i).uri
            }
            data?.data != null -> arrayOf(data.data!!)
            else -> null
        }
        callback.onReceiveValue(uris)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this)
        setContentView(webView)

        WebView.setWebContentsDebuggingEnabled(false)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = false
        webView.settings.allowContentAccess = true
        webView.settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW

        webView.webViewClient = object : WebViewClient() {
            private fun isAllowed(uri: Uri): Boolean {
                return uri.host == "127.0.0.1" || uri.host == "localhost" ||
                        uri.scheme == "blob" || uri.scheme == "data" || uri.scheme == "content"
            }

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                return !isAllowed(request.url)
            }

            override fun shouldInterceptRequest(
                view: WebView?,
                request: WebResourceRequest?
            ): WebResourceResponse? {
                val uri = request?.url ?: return null
                if ((uri.scheme == "http" || uri.scheme == "https") && !isAllowed(uri)) {
                    return WebResourceResponse(
                        "text/plain",
                        "utf-8",
                        403,
                        "Offline",
                        emptyMap(),
                        ByteArrayInputStream(ByteArray(0))
                    )
                }
                return null
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                fileCallback?.onReceiveValue(null)
                fileCallback = filePathCallback
                val pickerIntent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "*/*"
                    putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("application/octet-stream", "application/x-tlog", "*/*"))
                    putExtra(Intent.EXTRA_ALLOW_MULTIPLE, false)
                }
                filePicker.launch(pickerIntent)
                return true
            }
        }

        startLocalAnalyzer(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent.action == Intent.ACTION_VIEW && intent.data != null) {
            io.execute {
                try {
                    registerIncomingTlog(intent)
                    runOnUiThread {
                        webView.loadUrl("http://127.0.0.1:8765/?shared=1&t=" + System.currentTimeMillis())
                    }
                } catch (t: Throwable) {
                    showIncomingError(t)
                }
            }
        }
    }

    private fun startLocalAnalyzer(startIntent: Intent?) {
        io.execute {
            try {
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(this))
                }
                Python.getInstance().getModule("android_server").callAttr("start_server", 8765)
                waitForServer()

                val hasShared = startIntent?.action == Intent.ACTION_VIEW &&
                        startIntent.data != null &&
                        runCatching { registerIncomingTlog(startIntent) }.isSuccess

                runOnUiThread {
                    if (hasShared) {
                        webView.loadUrl("http://127.0.0.1:8765/?shared=1&t=" + System.currentTimeMillis())
                    } else {
                        webView.loadUrl("http://127.0.0.1:8765/")
                    }
                }
            } catch (t: Throwable) {
                runOnUiThread {
                    webView.loadData(
                        "<html><body style='background:#111;color:white;font-family:sans-serif;padding:20px'><h2>Помилка запуску офлайн-аналізатора</h2><pre>" +
                                (t.message ?: "") +
                                "</pre></body></html>",
                        "text/html",
                        "utf-8"
                    )
                }
            }
        }
    }

    private fun registerIncomingTlog(incomingIntent: Intent) {
        val uri = incomingIntent.data ?: error("Файл не передано")
        val displayName = queryDisplayName(uri)
            .ifBlank { uri.lastPathSegment?.substringAfterLast('/') ?: "shared.tlog" }
            .replace(Regex("[^A-Za-zА-Яа-яІіЇїЄє0-9._() -]"), "_")

        if (!displayName.lowercase().endsWith(".tlog")) {
            error("Потрібен файл формату .tlog")
        }

        val sharedDir = File(cacheDir, "shared_tlog").apply { mkdirs() }
        sharedDir.listFiles()?.forEach { it.delete() }

        val outFile = File(sharedDir, displayName)
        contentResolver.openInputStream(uri).use { input ->
            requireNotNull(input) { "Не вдалося відкрити TLOG" }
            outFile.outputStream().use { output ->
                input.copyTo(output, DEFAULT_BUFFER_SIZE)
            }
        }

        Python.getInstance()
            .getModule("android_server")
            .callAttr("register_shared_tlog", outFile.absolutePath, displayName)
    }

    private fun queryDisplayName(uri: Uri): String {
        if (uri.scheme != "content") {
            return uri.lastPathSegment?.substringAfterLast('/') ?: ""
        }
        return runCatching {
            contentResolver.query(
                uri,
                arrayOf(OpenableColumns.DISPLAY_NAME),
                null,
                null,
                null
            )?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (index >= 0) cursor.getString(index) ?: "" else ""
                } else ""
            } ?: ""
        }.getOrDefault("")
    }

    private fun showIncomingError(t: Throwable) {
        runOnUiThread {
            Toast.makeText(this, t.message ?: "Не вдалося відкрити TLOG", Toast.LENGTH_LONG).show()
            webView.loadUrl("http://127.0.0.1:8765/")
        }
    }

    private fun waitForServer() {
        repeat(100) {
            try {
                val conn = URL("http://127.0.0.1:8765/health").openConnection() as HttpURLConnection
                conn.connectTimeout = 150
                conn.readTimeout = 150
                if (conn.responseCode in 200..299) return
            } catch (_: Throwable) { }
            Thread.sleep(100)
        }
        error("Локальний Python server не запустився")
    }

    override fun onDestroy() {
        fileCallback?.onReceiveValue(null)
        fileCallback = null
        webView.destroy()
        io.shutdownNow()
        super.onDestroy()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) webView.goBack()
        else super.onBackPressed()
    }
}
