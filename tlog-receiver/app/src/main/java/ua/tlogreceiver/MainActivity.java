package ua.tlogreceiver;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Locale;

public final class MainActivity extends Activity {
    private static final int PICK_FILE = 1001;
    private TextView status;
    private Button pick;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        buildUi();
        if (state == null) handleIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setPadding(48, 80, 48, 48);
        root.setBackgroundColor(Color.rgb(16, 20, 24));

        TextView title = new TextView(this);
        title.setText("TLOG Receiver");
        title.setTextColor(Color.WHITE);
        title.setTextSize(28);
        title.setGravity(Gravity.CENTER);
        root.addView(title, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView info = new TextView(this);
        info.setText("Приймає .tlog із WhatsApp та зберігає його в Download/TLOG Receiver");
        info.setTextColor(Color.LTGRAY);
        info.setTextSize(16);
        info.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams infoLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        infoLp.setMargins(0, 28, 0, 40);
        root.addView(info, infoLp);

        status = new TextView(this);
        status.setText("Надішли .tlog через «Поділитися» у WhatsApp або вибери файл вручну.");
        status.setTextColor(Color.WHITE);
        status.setTextSize(16);
        status.setGravity(Gravity.CENTER);
        root.addView(status, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        pick = new Button(this);
        pick.setText("Вибрати TLOG-файл");
        pick.setAllCaps(false);
        pick.setOnClickListener(v -> openPicker());
        LinearLayout.LayoutParams buttonLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 150);
        buttonLp.setMargins(0, 40, 0, 0);
        root.addView(pick, buttonLp);

        setContentView(root);
    }

    private void openPicker() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*");
        startActivityForResult(i, PICK_FILE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_FILE && resultCode == RESULT_OK && data != null && data.getData() != null) {
            save(data.getData());
        }
    }

    private void handleIntent(Intent intent) {
        if (intent == null) return;
        Uri uri = null;
        if (Intent.ACTION_SEND.equals(intent.getAction())) {
            uri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
        } else if (Intent.ACTION_VIEW.equals(intent.getAction())) {
            uri = intent.getData();
        }
        if (uri != null) save(uri);
    }

    private void save(Uri source) {
        pick.setEnabled(false);
        status.setText("Зберігаю файл…");
        new Thread(() -> {
            try {
                String original = displayName(source);
                String lower = original.toLowerCase(Locale.ROOT);
                if (!(lower.endsWith(".tlog") || lower.endsWith(".bin"))) {
                    throw new IOException("Файл не має розширення .tlog або .bin: " + original);
                }
                String savedName = normalizeName(original);
                copyToDownloads(source, savedName);
                runOnUiThread(() -> {
                    status.setText("✓ Збережено: " + savedName + "\nDownload/TLOG Receiver");
                    pick.setEnabled(true);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    String m = e.getMessage();
                    status.setText("Помилка: " + (m == null ? "невідома помилка" : m));
                    pick.setEnabled(true);
                });
            }
        }).start();
    }

    private String displayName(Uri uri) {
        ContentResolver resolver = getContentResolver();
        try (Cursor c = resolver.query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                int i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (i >= 0) {
                    String name = c.getString(i);
                    if (name != null && !name.trim().isEmpty()) return name;
                }
            }
        } catch (Exception ignored) {}
        String segment = uri.getLastPathSegment();
        return segment == null ? "flight.tlog" : segment;
    }

    private String normalizeName(String name) {
        if (name == null || name.trim().isEmpty()) return "flight.tlog";
        String clean = name.trim();
        String lower = clean.toLowerCase(Locale.ROOT);
        if (lower.endsWith(".tlog")) return clean;
        if (lower.endsWith(".bin")) return clean.substring(0, clean.length() - 4) + ".tlog";
        return clean + ".tlog";
    }

    private void copyToDownloads(Uri source, String fileName) throws IOException {
        ContentResolver resolver = getContentResolver();
        ContentValues values = new ContentValues();
        values.put(MediaStore.MediaColumns.DISPLAY_NAME, fileName);
        values.put(MediaStore.MediaColumns.MIME_TYPE, "application/octet-stream");
        values.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/TLOG Receiver");
        values.put(MediaStore.MediaColumns.IS_PENDING, 1);

        Uri dest = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (dest == null) throw new IOException("Android не створив файл у Download");
        boolean ok = false;
        try (InputStream in = resolver.openInputStream(source); OutputStream out = resolver.openOutputStream(dest, "w")) {
            if (in == null || out == null) throw new IOException("Не вдалося відкрити файл");
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) != -1) out.write(buf, 0, n);
            out.flush();
            ok = true;
        } finally {
            if (!ok) resolver.delete(dest, null, null);
        }
        ContentValues ready = new ContentValues();
        ready.put(MediaStore.MediaColumns.IS_PENDING, 0);
        resolver.update(dest, ready, null, null);
    }
}
