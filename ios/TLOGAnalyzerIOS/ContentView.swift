import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @State private var showImporter = false
    @State private var importedFile: URL?
    @State private var importError: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if let importedFile {
                    LocalAnalyzerWebView(fileURL: importedFile)
                } else {
                    VStack(spacing: 18) {
                        Image(systemName: "waveform.path.ecg.rectangle")
                            .font(.system(size: 54))
                        Text("TLOG Analyzer")
                            .font(.title.bold())
                        Text("Офлайн-аналіз TLOG на iPhone / iPad")
                            .foregroundStyle(.secondary)
                        Button("Вибрати .tlog") {
                            showImporter = true
                        }
                        .buttonStyle(.borderedProminent)

                        if let importError {
                            Text(importError)
                                .foregroundStyle(.red)
                                .font(.footnote)
                                .multilineTextAlignment(.center)
                        }
                    }
                    .padding(24)
                }
            }
            .navigationTitle("TLOG Analyzer")
            .toolbar {
                if importedFile != nil {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Інший файл") {
                            importedFile = nil
                            showImporter = true
                        }
                    }
                }
            }
        }
        .fileImporter(
            isPresented: $showImporter,
            allowedContentTypes: [UTType.data],
            allowsMultipleSelection: false
        ) { result in
            do {
                guard let url = try result.get().first else { return }
                guard url.pathExtension.lowercased() == "tlog" else {
                    importError = "Потрібен файл .tlog"
                    return
                }
                importError = nil
                importedFile = url
            } catch {
                importError = error.localizedDescription
            }
        }
    }
}
