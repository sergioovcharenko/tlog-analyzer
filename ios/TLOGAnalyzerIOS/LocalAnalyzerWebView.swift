import SwiftUI
import WebKit

struct LocalAnalyzerWebView: UIViewRepresentable {
    let fileURL: URL

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        config.userContentController.add(context.coordinator, name: "tlogBridge")

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        context.coordinator.webView = webView
        context.coordinator.pendingFileURL = fileURL

        if let indexURL = Bundle.main.url(
            forResource: "index",
            withExtension: "html",
            subdirectory: "Web"
        ) {
            webView.loadFileURL(
                indexURL,
                allowingReadAccessTo: indexURL.deletingLastPathComponent()
            )
        }

        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        if context.coordinator.pendingFileURL != fileURL {
            context.coordinator.pendingFileURL = fileURL
            context.coordinator.deliverFileIfReady()
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
        weak var webView: WKWebView?
        var pendingFileURL: URL?
        var pageReady = false

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            pageReady = true
            deliverFileIfReady()
        }

        func deliverFileIfReady() {
            guard pageReady, let webView, let fileURL = pendingFileURL else { return }

            let scoped = fileURL.startAccessingSecurityScopedResource()
            defer {
                if scoped { fileURL.stopAccessingSecurityScopedResource() }
            }

            do {
                let data = try Data(contentsOf: fileURL, options: .mappedIfSafe)
                let base64 = data.base64EncodedString()
                let name = fileURL.lastPathComponent
                    .replacingOccurrences(of: "\\", with: "\\\\")
                    .replacingOccurrences(of: "'", with: "\\'")

                let js = """
                window.iOSTLOGBridge?.receiveFile({
                  name: '\(name)',
                  size: \(data.count),
                  base64: '\(base64)'
                });
                """
                webView.evaluateJavaScript(js)
            } catch {
                let message = error.localizedDescription
                    .replacingOccurrences(of: "\\", with: "\\\\")
                    .replacingOccurrences(of: "'", with: "\\'")
                webView.evaluateJavaScript(
                    "window.iOSTLOGBridge?.showNativeError('\(message)');"
                )
            }
        }

        func userContentController(
            _ userContentController: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {
            // Reserved for progress/events from the local JS/WASM analyzer.
        }
    }
}
