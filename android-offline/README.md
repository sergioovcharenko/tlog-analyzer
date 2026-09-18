# TLOG Analyzer Offline — Android

Це окремий Android-проєкт, який пакує production TLOG Analyzer у APK і запускає Python/FastAPI локально на 127.0.0.1.

## Офлайн
Після встановлення APK аналіз TLOG не потребує Render, GitHub Pages або зовнішнього API. WebView дозволяє навігацію лише до localhost/content/blob/data. INTERNET permission потрібен Android тільки для локального loopback HTTP server.

## Production parity
У `app/src/main/python/backend/` під час розробки зберігаються ті самі production Python-модулі, що у `/backend`, а `index.html` і `map3d.js` — ті самі файли, що у веб-версії.

## Не додається
Жодного автоматичного визначення v3.0/v3.1 не додано.

## Збірка
В Android Studio: Open `android-offline`, Sync, Build > Build APK(s).

GitHub Actions workflow також збирає debug APK.
