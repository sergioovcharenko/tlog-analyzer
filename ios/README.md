# TLOG Analyzer iOS

Початковий офлайн-каркас для iPhone/iPad.

## Що вже є
- SwiftUI застосунок
- вибір `.tlog` через системний Files picker
- security-scoped доступ до файлу
- локальний WKWebView
- передача TLOG у WebView без HTTP/upload
- JS bridge для майбутнього локального MAVLink/TLOG engine
- мінімальна ціль iOS 16

## Що ще треба перенести для повного офлайн-паритету
Поточний production analyzer використовує Python + pymavlink/FastAPI. iOS не запускає цей backend як звичайний локальний процес, тому аналіз треба перенести у локальний engine.

Рекомендований порядок:
1. MAVLink v1/v2 frame reader у Swift або JavaScript/WASM.
2. HEARTBEAT / STATUSTEXT / PARAM_VALUE.
3. RC_CHANNELS / SYS_STATUS / LOCAL_POSITION_NED / ATTITUDE.
4. ESC / EFI / RADIO.
5. ARM→DISARM sessions.
6. VISP 1.3.2 / 1.3.4 rules.
7. FL_BRDTYPE / FL_SN / v3.0-v3.1 profile detection.
8. AI/expert rules, antenna geometry, timeline, maps.
9. Graph data and reports.

## Створення Xcode project
У папці `ios/` використовується XcodeGen:

```bash
brew install xcodegen
cd ios
xcodegen generate
open TLOGAnalyzerIOS.xcodeproj
```

Після генерації вибрати свій Signing Team і запустити на iPhone.

## Важливо
Поточний код у цьому каталозі — фундамент iOS-версії. Він уже імпортує TLOG локально, але ще не містить повного перенесеного Python-аналізатора.
