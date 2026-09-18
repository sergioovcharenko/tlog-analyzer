package ua.tloganalyzer.offline

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.ByteArrayInputStream
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
                val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "*/*"
                    putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("application/octet-stream", "application/x-tlog", "*/*"))
                    putExtra(Intent.EXTRA_ALLOW_MULTIPLE, false)
                }
                filePicker.launch(intent)
                return true
            }
        }

        startLocalAnalyzer()
    }

    private fun startLocalAnalyzer() {
        io.execute {
            try {
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(this))
                }
                Python.getInstance().getModule("android_server").callAttr("start_server", 8765)
                waitForServer()
                runOnUiThread {
                    webView.loadUrl("http://127.0.0.1:8765/")
                }
            } catch (t: Throwable) {
                runOnUiThread {
                    webView.loadData(
                        "<html><body style='background:#111;color:white;font-family:sans-serif;padding:20px'><h2>Помилка запуску офлайн-аналізатора</h2><pre>${t.message}</pre></body></html>",
                        "text/html",
                        "utf-8"
                    )
                }
            }
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

    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) webView.goBack()
        else super.onBackPressed()
    }
}
