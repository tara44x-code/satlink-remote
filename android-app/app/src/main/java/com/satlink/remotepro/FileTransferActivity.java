package com.satlink.remotepro;

import android.app.*;
import android.os.*;
import android.content.*;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.net.URLEncoder;
import java.text.DecimalFormat;
import java.util.*;

public class FileTransferActivity extends Activity {
    static final int REQ_PICK_UPLOAD = 1001;
    static final int REQ_CREATE_DOWNLOAD = 1002;

    String baseUrl, pin, deviceName;
    LinearLayout list, rootsBar;
    TextView status, pathText, hintText;
    String currentRoot = "exchange";
    String currentPath = "";
    String pendingDownloadPath = null;
    String pendingDownloadName = null;
    ArrayList<RootInfo> roots = new ArrayList<>();

    static class RootInfo {
        String key, name, path;
        RootInfo(String k, String n, String p) { key = k; name = n; path = p; }
    }

    String normalizePin(String raw) {
        if (raw == null) return "";
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < raw.length(); i++) {
            char ch = raw.charAt(i);
            if (ch >= '0' && ch <= '9') out.append(ch);
            else if (ch >= '\u0660' && ch <= '\u0669') out.append((char)('0' + (ch - '\u0660')));
            else if (ch >= '\u06F0' && ch <= '\u06F9') out.append((char)('0' + (ch - '\u06F0')));
        }
        return out.toString().trim();
    }

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        baseUrl = getIntent().getStringExtra("url");
        pin = normalizePin(getIntent().getStringExtra("pin"));
        deviceName = getIntent().getStringExtra("name");
        addFallbackRoots();
        build();
        loadRootsThenList();
    }

    TextView tv(String t, int sp, int color, int style) {
        TextView v = new TextView(this);
        v.setText(t);
        v.setTextSize(sp);
        v.setTextColor(color);
        v.setTypeface(null, style);
        v.setPadding(Neon.dp(this,12),Neon.dp(this,6),Neon.dp(this,12),Neon.dp(this,4));
        return v;
    }

    Button btn(String t, int color) {
        Button b = new Button(this);
        b.setText(t);
        b.setTextSize(14);
        Neon.style(b, Neon.accentFromLegacy(color));
        return b;
    }

    void build() {
        ScrollView sv = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(16,16,16,16);
        root.setBackgroundColor(Neon.BG);
        sv.addView(root);

        root.addView(tv("SatLink Remote PRO - مدير الملفات", 23, Neon.CYAN, 1));
        root.addView(tv("الجهاز: " + deviceName + "  |  PRO 2.3.1 Neon", 14, Neon.MUTED, 0));
        status = tv("جاهز", 14, Neon.GREEN, 0);
        root.addView(status);

        hintText = tv("المجلدات المسموحة فقط: التبادل، سطح المكتب، التنزيلات، المستندات.", 12, Neon.MUTED, 0);
        root.addView(hintText);

        rootsBar = new LinearLayout(this);
        rootsBar.setOrientation(LinearLayout.VERTICAL);
        root.addView(rootsBar);
        renderRootButtons();

        pathText = tv("المسار: /", 13, Color.WHITE, 1);
        root.addView(pathText);

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.VERTICAL);
        root.addView(actions);

        Button back = btn("رجوع للمجلد السابق", Color.rgb(23,38,61));
        actions.addView(back, Neon.btnLp(this));
        Button upload = btn("رفع ملف من الموبايل إلى هذا المجلد", Color.rgb(35,134,54));
        actions.addView(upload, Neon.btnLp(this));
        Button mkdir = btn("إنشاء مجلد جديد", Color.rgb(31,111,235));
        actions.addView(mkdir, Neon.btnLp(this));
        Button refresh = btn("تحديث القائمة", Color.rgb(31,111,235));
        actions.addView(refresh, Neon.btnLp(this));

        root.addView(tv("المحتويات", 20, Color.WHITE, 1));
        list = new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        root.addView(list);
        setContentView(sv);

        back.setOnClickListener(v -> goBackFolder());
        upload.setOnClickListener(v -> pickUploadFile());
        mkdir.setOnClickListener(v -> askCreateFolder());
        refresh.setOnClickListener(v -> refreshList());
    }

    void addFallbackRoots() {
        roots.clear();
        roots.add(new RootInfo("exchange", "مجلد التبادل", ""));
        roots.add(new RootInfo("desktop", "سطح المكتب", ""));
        roots.add(new RootInfo("downloads", "التنزيلات", ""));
        roots.add(new RootInfo("documents", "المستندات", ""));
    }

    void renderRootButtons() {
        if (rootsBar == null) return;
        rootsBar.removeAllViews();
        for (RootInfo r: roots) {
            Button b = btn(r.name, r.key.equals(currentRoot) ? Color.rgb(31,111,235) : Color.rgb(13,27,47));
            rootsBar.addView(b, Neon.btnLp(this));
            b.setOnClickListener(v -> {
                currentRoot = r.key;
                currentPath = "";
                renderRootButtons();
                refreshList();
            });
        }
    }

    String enc(String s) throws Exception {
        return URLEncoder.encode(s == null ? "" : s, "UTF-8").replace("+", "%20");
    }

    String fmListUrl() throws Exception {
        return baseUrl + "/api/fm/list?root=" + enc(currentRoot) + "&path=" + enc(currentPath);
    }

    String fmUploadUrl() throws Exception {
        return baseUrl + "/api/fm/upload?root=" + enc(currentRoot) + "&path=" + enc(currentPath);
    }

    String fmUploadRawUrl() throws Exception {
        return baseUrl + "/api/fm/upload_raw?root=" + enc(currentRoot) + "&path=" + enc(currentPath);
    }

    String fmDownloadUrl(String path) throws Exception {
        return baseUrl + "/api/fm/download?root=" + enc(currentRoot) + "&path=" + enc(path);
    }

    void loadRootsThenList() {
        status.setText("جاري قراءة المجلدات المسموحة...");
        new Thread(() -> {
            try {
                String raw = Net.getText(baseUrl + "/api/fm/roots", pin);
                JSONObject o = new JSONObject(raw);
                JSONArray arr = o.optJSONArray("roots");
                ArrayList<RootInfo> got = new ArrayList<>();
                if (arr != null) {
                    for (int i=0; i<arr.length(); i++) {
                        JSONObject r = arr.getJSONObject(i);
                        got.add(new RootInfo(r.optString("key"), r.optString("name"), r.optString("path")));
                    }
                }
                if (got.size() > 0) roots = got;
                runOnUiThread(() -> { renderRootButtons(); refreshList(); });
            } catch(Exception e) {
                runOnUiThread(() -> { renderRootButtons(); refreshList(); });
            }
        }).start();
    }

    void refreshList() {
        status.setText("جاري تحديث الملفات...");
        try { pathText.setText("المسار: " + currentRootName() + " / " + (currentPath.length() == 0 ? "" : currentPath)); } catch(Exception ignored) {}
        new Thread(() -> {
            try {
                String raw = Net.getText(fmListUrl(), pin);
                JSONObject o = new JSONObject(raw);
                JSONArray arr = o.optJSONArray("items");
                String abs = o.optString("absolute_path", "");
                String path = o.optString("path", "");
                ArrayList<JSONObject> items = new ArrayList<>();
                if (arr != null) for (int i=0; i<arr.length(); i++) items.add(arr.getJSONObject(i));
                runOnUiThread(() -> renderItems(abs, path, items));
            } catch(Exception e) {
                runOnUiThread(() -> status.setText("فشل التحديث: " + shortErr(e)));
            }
        }).start();
    }

    String currentRootName() {
        for (RootInfo r: roots) if (r.key.equals(currentRoot)) return r.name;
        return currentRoot;
    }

    void renderItems(String absolutePath, String path, ArrayList<JSONObject> items) {
        currentPath = path == null ? "" : path;
        pathText.setText("المسار: " + currentRootName() + " / " + (currentPath.length() == 0 ? "" : currentPath));
        hintText.setText("مسار الحاسبة: " + absolutePath);
        list.removeAllViews();
        status.setText("عدد العناصر: " + items.size());
        if (items.size() == 0) {
            list.addView(tv("هذا المجلد فارغ. ارفع ملفاً أو أنشئ مجلداً جديداً.", 15, Neon.MUTED, 0));
            return;
        }
        for (JSONObject item: items) addItemCard(item);
    }

    void addItemCard(JSONObject item) {
        String fname = item.optString("name", "");
        String path = item.optString("path", fname);
        boolean isDir = item.optBoolean("is_dir", false);
        long size = item.optLong("size", 0);

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(Neon.dp(this,14),Neon.dp(this,12),Neon.dp(this,14),Neon.dp(this,12));
        card.setBackground(Neon.card(this));
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(-1, -2);
        cp.setMargins(0,Neon.dp(this,6),0,Neon.dp(this,8));
        list.addView(card, cp);

        card.addView(tv((isDir ? "📁 " : "📄 ") + fname, 17, Color.WHITE, 1));
        if (!isDir) card.addView(tv("الحجم: " + human(size), 13, Neon.MUTED, 0));
        card.addView(tv("المسار: " + path, 12, Neon.MUTED, 0));

        if (isDir) {
            Button open = btn("فتح المجلد", Color.rgb(31,111,235));
            card.addView(open, Neon.btnLp(this));
            open.setOnClickListener(v -> { currentPath = path; refreshList(); });
        } else {
            Button dl = btn("تحميل إلى الموبايل", Color.rgb(31,111,235));
            card.addView(dl, Neon.btnLp(this));
            dl.setOnClickListener(v -> askWhereToSave(path, fname));

            Button openPc = btn("فتح على الحاسبة", Color.rgb(23,38,61));
            card.addView(openPc, Neon.btnLp(this));
            openPc.setOnClickListener(v -> openOnPc(path));
        }

        Button rename = btn("إعادة تسمية", Color.rgb(23,38,61));
        card.addView(rename, Neon.btnLp(this));
        rename.setOnClickListener(v -> askRename(path, fname));

        Button del = btn(isDir ? "حذف المجلد ومحتوياته" : "حذف من الحاسبة", Color.rgb(112,34,46));
        card.addView(del, Neon.btnLp(this));
        del.setOnClickListener(v -> confirmDelete(path, fname, isDir));
    }

    void goBackFolder() {
        if (currentPath == null || currentPath.length() == 0) {
            Toast.makeText(this, "أنت في المجلد الرئيسي", Toast.LENGTH_SHORT).show();
            return;
        }
        int idx = currentPath.lastIndexOf('/');
        currentPath = idx <= 0 ? "" : currentPath.substring(0, idx);
        refreshList();
    }

    void pickUploadFile() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*");
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(i, REQ_PICK_UPLOAD);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        if (requestCode == REQ_PICK_UPLOAD) {
            try { getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION); } catch(Exception ignored) {}
            uploadSelected(uri);
        } else if (requestCode == REQ_CREATE_DOWNLOAD) {
            if (pendingDownloadPath != null) downloadTo(uri, pendingDownloadPath, pendingDownloadName == null ? "file.bin" : pendingDownloadName);
        }
    }

    String getDisplayName(Uri uri) {
        String result = "file.bin";
        try {
            Cursor c = getContentResolver().query(uri, null, null, null, null);
            if (c != null) {
                int idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (idx >= 0 && c.moveToFirst()) result = c.getString(idx);
                c.close();
            }
        } catch(Exception ignored) {}
        return result == null || result.trim().length() == 0 ? "file.bin" : result;
    }

    void uploadSelected(Uri uri) {
        String filename = getDisplayName(uri);
        status.setText("جاري رفع: " + filename + " ... لا تغلق التطبيق أثناء الرفع");
        new Thread(() -> {
            try {
                String res;
                try {
                    // المسار الخام أسرع وأثبت لبعض صور المعرض والأسماء العربية لأنه لا يعتمد على multipart.
                    res = Net.uploadFileRaw(fmUploadRawUrl(), pin, getContentResolver(), uri, filename);
                } catch (Exception rawErr) {
                    // احتياطي: إذا فشل الرفع الخام نجرب multipart القديم.
                    res = Net.uploadFile(fmUploadUrl(), pin, getContentResolver(), uri, filename);
                }
                runOnUiThread(() -> { status.setText("تم رفع الملف بنجاح: " + filename); Toast.makeText(this, "تم إرسال الملف للحاسبة", Toast.LENGTH_LONG).show(); refreshList(); });
            } catch(Exception e) {
                runOnUiThread(() -> status.setText("فشل الرفع: " + shortErr(e) + "\nجرّب اختيار الملف من مدير الملفات أو انقله إلى Downloads ثم ارفعه."));
            }
        }).start();
    }

    void askWhereToSave(String path, String fname) {
        pendingDownloadPath = path;
        pendingDownloadName = fname;
        Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("application/octet-stream");
        i.putExtra(Intent.EXTRA_TITLE, fname);
        startActivityForResult(i, REQ_CREATE_DOWNLOAD);
    }

    void downloadTo(Uri outUri, String path, String fname) {
        status.setText("جاري تحميل: " + fname);
        new Thread(() -> {
            try {
                Net.downloadToUri(fmDownloadUrl(path), pin, getContentResolver(), outUri);
                runOnUiThread(() -> { status.setText("تم تحميل الملف: " + fname); Toast.makeText(this, "تم حفظ الملف", Toast.LENGTH_LONG).show(); });
            } catch(Exception e) {
                runOnUiThread(() -> status.setText("فشل التحميل: " + shortErr(e)));
            }
        }).start();
    }

    void confirmDelete(String path, String name, boolean isDir) {
        new AlertDialog.Builder(this)
                .setTitle("حذف؟")
                .setMessage((isDir ? "سيتم حذف المجلد ومحتوياته داخل المجلدات المسموحة فقط:\n" : "سيتم حذف الملف من الحاسبة:\n") + name)
                .setPositiveButton("حذف", (d,w)->deleteRemote(path))
                .setNegativeButton("إلغاء", null).show();
    }

    void deleteRemote(String path) {
        status.setText("جاري الحذف...");
        new Thread(() -> {
            try {
                JSONObject o = new JSONObject();
                o.put("root", currentRoot); o.put("path", path);
                Net.postJson(baseUrl + "/api/fm/delete", pin, o);
                runOnUiThread(() -> { Toast.makeText(this, "تم الحذف", Toast.LENGTH_SHORT).show(); refreshList(); });
            } catch(Exception e) {
                runOnUiThread(() -> status.setText("فشل الحذف: " + shortErr(e)));
            }
        }).start();
    }

    void askCreateFolder() {
        final EditText input = new EditText(this);
        input.setHint("اسم المجلد الجديد");
        new AlertDialog.Builder(this)
                .setTitle("إنشاء مجلد")
                .setView(input)
                .setPositiveButton("إنشاء", (d,w)->{
                    String n = input.getText().toString().trim();
                    if (n.length() > 0) createFolder(n);
                })
                .setNegativeButton("إلغاء", null).show();
    }

    void createFolder(String name) {
        status.setText("جاري إنشاء المجلد...");
        new Thread(() -> {
            try {
                JSONObject o = new JSONObject();
                o.put("root", currentRoot); o.put("path", currentPath); o.put("name", name);
                Net.postJson(baseUrl + "/api/fm/mkdir", pin, o);
                runOnUiThread(() -> { Toast.makeText(this, "تم إنشاء المجلد", Toast.LENGTH_SHORT).show(); refreshList(); });
            } catch(Exception e) {
                runOnUiThread(() -> status.setText("فشل إنشاء المجلد: " + shortErr(e)));
            }
        }).start();
    }

    void askRename(String path, String oldName) {
        final EditText input = new EditText(this);
        input.setText(oldName);
        input.setSelectAllOnFocus(true);
        new AlertDialog.Builder(this)
                .setTitle("إعادة تسمية")
                .setView(input)
                .setPositiveButton("حفظ", (d,w)->{
                    String n = input.getText().toString().trim();
                    if (n.length() > 0) renameRemote(path, n);
                })
                .setNegativeButton("إلغاء", null).show();
    }

    void renameRemote(String path, String newName) {
        status.setText("جاري إعادة التسمية...");
        new Thread(() -> {
            try {
                JSONObject o = new JSONObject();
                o.put("root", currentRoot); o.put("path", path); o.put("new_name", newName);
                Net.postJson(baseUrl + "/api/fm/rename", pin, o);
                runOnUiThread(() -> { Toast.makeText(this, "تمت إعادة التسمية", Toast.LENGTH_SHORT).show(); refreshList(); });
            } catch(Exception e) {
                runOnUiThread(() -> status.setText("فشل إعادة التسمية: " + shortErr(e)));
            }
        }).start();
    }

    void openOnPc(String path) {
        status.setText("جاري فتح الملف على الحاسبة...");
        new Thread(() -> {
            try {
                JSONObject o = new JSONObject();
                o.put("root", currentRoot); o.put("path", path);
                Net.postJson(baseUrl + "/api/fm/open", pin, o);
                runOnUiThread(() -> status.setText("تم إرسال أمر الفتح للحاسبة"));
            } catch(Exception e) {
                runOnUiThread(() -> status.setText("فشل فتح الملف: " + shortErr(e)));
            }
        }).start();
    }

    String human(long bytes) {
        DecimalFormat df = new DecimalFormat("0.##");
        if (bytes < 1024) return bytes + " B";
        double kb = bytes / 1024.0;
        if (kb < 1024) return df.format(kb) + " KB";
        double mb = kb / 1024.0;
        if (mb < 1024) return df.format(mb) + " MB";
        return df.format(mb / 1024.0) + " GB";
    }

    String shortErr(Exception e) {
        String m = e.getMessage();
        if (m == null) return e.toString();
        try {
            JSONObject o = new JSONObject(m);
            String err = o.optString("error", "");
            if (err.length() > 0) m = err;
        } catch(Exception ignored) {}
        if (m.toLowerCase().contains("timeout") || m.contains("timed out") || m.contains("مهلة")) {
            return "انتهت مهلة رفع الملف. جرّب ملف أصغر أو استخدم اتصال مباشر Wi-Fi أو تأكد من تشغيل Relay v2.2.4.";
        }
        if (m.contains("حجم الطلب") || m.contains("أكبر من الحد") || m.contains("413")) {
            return "حجم الملف كبير على إعدادات السيرفر. النسخة 2.2.4 رفعت الحد، أو جرّب ملف أصغر.";
        }
        if (m.contains("لم يصل أي ملف")) {
            return "لم يصل الملف للحاسبة. تم إصلاح طريقة الرفع في نسخة 2.2.4؛ أعد تشغيل التطبيق والبرنامج والسيرفر من نفس النسخة.";
        }
        if (m.contains("PIN") || m.contains("064a") || m.contains("0635")) {
            return "PIN غير صحيح. اكتب الرقم الأخضر الظاهر في برنامج الحاسبة.";
        }
        return m.length() > 220 ? m.substring(0, 220) : m;
    }
}
