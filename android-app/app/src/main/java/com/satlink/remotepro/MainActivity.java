package com.satlink.remotepro;

import android.app.*;
import android.os.*;
import android.content.*;
import android.graphics.Color;
import android.view.*;
import android.widget.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

public class MainActivity extends Activity {
    LinearLayout list;
    TextView status;
    ArrayList<DeviceInfo> devices = new ArrayList<>();
    int blue = Neon.CYAN;
    SharedPreferences prefs;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences("satlink_remote_pro", MODE_PRIVATE);
        build();
        loadSavedDevices();
        renderList();
    }

    TextView tv(String t, int sp, int color, int style) {
        TextView v = new TextView(this);
        v.setText(t); v.setTextSize(sp); v.setTextColor(color); v.setTypeface(null, style);
        v.setPadding(Neon.dp(this,12),Neon.dp(this,8),Neon.dp(this,12),Neon.dp(this,6));
        return v;
    }

    Button btn(String t) {
        Button b = new Button(this);
        b.setText(t); b.setTextSize(15);
        Neon.style(b, Neon.CYAN);
        return b;
    }

    void build() {
        ScrollView sv = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(Neon.dp(this,16),Neon.dp(this,20),Neon.dp(this,16),Neon.dp(this,20));
        sv.setBackgroundColor(Neon.BG);
        root.setBackgroundColor(Neon.BG);
        sv.addView(root);

        TextView title = tv("SatLink Remote PRO", 28, blue, 1);
        Neon.glowText(title, Neon.CYAN);
        root.addView(title);
        root.addView(tv("المطور: مهند سات لنك  |  PRO 2.3.1 Neon", 13, Neon.MUTED, 0));
        status = tv("الأجهزة المحفوظة تبقى موجودة. استخدم Wi‑Fi أو Relay للاتصال من أي مكان.", 14, Neon.GREEN, 0);
        root.addView(status);
        root.addView(Neon.divider(this));

        Button search = btn("بحث وتحديث الأجهزة داخل Wi‑Fi");
        Neon.stylePrimary(search);
        root.addView(search, Neon.btnLp(this));
        Button manual = btn("إضافة يدوي IP / Port");
        Neon.style(manual, Neon.accentFromLegacy(Color.rgb(23,38,61)));
        root.addView(manual, Neon.btnLp(this));
        Button relay = btn("Relay: الاتصال من أي مكان / تحديث الأجهزة");
        Neon.style(relay, Neon.accentFromLegacy(Color.rgb(111,66,193)));
        root.addView(relay, Neon.btnLp(this));
        Button about = btn("حول SatLink Remote PRO");
        Neon.style(about, Neon.accentFromLegacy(Color.rgb(13,27,47)));
        root.addView(about, Neon.btnLp(this));

        root.addView(Neon.divider(this));
        TextView myDevices = tv("أجهزتي المحفوظة", 22, Color.WHITE, 1);
        Neon.glowText(myDevices, Neon.MAGENTA);
        root.addView(myDevices);
        list = new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        root.addView(list);
        setContentView(sv);

        search.setOnClickListener(v -> discover());
        manual.setOnClickListener(v -> manualAdd());
        relay.setOnClickListener(v -> relaySettings());
        about.setOnClickListener(v -> showAbout());
    }

    void showAbout() {
        new AlertDialog.Builder(this)
                .setTitle("SatLink Remote PRO")
                .setMessage("الإصدار: PRO 2.3.1 Neon\nالمطور: مهند سات لنك\n\nنسخة 2.3.0 Neon: ثيم نيون جديد، شاشة تحكم كاملة بدون حواف سوداء، لوحة تحكم عائمة، وضع Touchpad، اختصارات كيبورد، كتابة عربي، وأزرار الطاقة (قفل/سكون/إعادة تشغيل/إطفاء).\n\nالأمان: الاتصال يحتاج Owner Token + PIN، والجهاز يبقى باسمك المختار دون الاعتماد على IP ثابت.")
                .setPositiveButton("تمام", null)
                .show();
    }

    void discover() {
        status.setText("جاري البحث وتحديث IP الأجهزة...");
        Net.discover(new Net.DiscoveryCallback() {
            int found = 0;
            public void onDevice(DeviceInfo d) {
                runOnUiThread(() -> {
                    found++;
                    addOrUpdateDevice(d, true);
                    status.setText("تم العثور على جهاز: " + d.name);
                });
            }
            public void onDone() {
                runOnUiThread(() -> {
                    renderList();
                    status.setText(found == 0 ? "لم يتم العثور على جهاز. تأكد أن برنامج Windows شغال ونفس شبكة Wi‑Fi." : "تم تحديث الأجهزة المحفوظة بنجاح.");
                });
            }
        });
    }

    void addOrUpdateDevice(DeviceInfo d, boolean save) {
        for (DeviceInfo x: devices) {
            if (x.id.equals(d.id)) {
                // الاسم يبقى الاسم الذي اختاره المستخدم، لكن IP يتحدث تلقائياً.
                x.ip = d.ip; x.port = d.port; x.version = d.version; x.viaRelay = d.viaRelay; x.relayUrl = d.relayUrl;
                if (save) saveDevices();
                return;
            }
        }
        devices.add(d);
        if (save) saveDevices();
    }

    void renderList() {
        list.removeAllViews();
        if (devices.size() == 0) {
            list.addView(tv("لا توجد أجهزة محفوظة بعد. اضغط بحث أو إضافة يدوي.", 15, Neon.MUTED, 0));
            return;
        }
        for (DeviceInfo d: devices) addDeviceCard(d);
    }

    void addDeviceCard(DeviceInfo d) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(Neon.dp(this,14),Neon.dp(this,12),Neon.dp(this,14),Neon.dp(this,12));
        card.setBackground(Neon.card(this));
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(-1, -2);
        cp.setMargins(0,Neon.dp(this,6),0,Neon.dp(this,10));
        list.addView(card, cp);

        card.addView(tv("🟢 " + d.name, 19, Color.WHITE, 1));
        card.addView(tv("ID ثابت: " + d.id + "\nالعنوان: " + d.displayAddress(), 13, Neon.MUTED, 0));

        Button connect = btn("دخول وتحكم");
        Neon.stylePrimary(connect);
        card.addView(connect, Neon.btnLp(this));
        Button files = btn("مدير الملفات");
        Neon.style(files, Neon.accentFromLegacy(Color.rgb(35,134,54)));
        card.addView(files, Neon.btnLp(this));
        Button rename = btn("إعادة تسمية");
        Neon.style(rename, Neon.accentFromLegacy(Color.rgb(23,38,61)));
        card.addView(rename, Neon.btnLp(this));
        Button remove = btn("حذف من التطبيق");
        Neon.style(remove, Neon.accentFromLegacy(Color.rgb(112,34,46)));
        card.addView(remove, Neon.btnLp(this));

        connect.setOnClickListener(v -> askPinAndOpen(d));
        files.setOnClickListener(v -> askPinAndOpenFiles(d));
        rename.setOnClickListener(v -> renameLocal(d));
        remove.setOnClickListener(v -> confirmRemove(d));
    }

    void renameLocal(DeviceInfo d) {
        final EditText input = new EditText(this);
        input.setText(d.name);
        input.setSelectAllOnFocus(true);
        new AlertDialog.Builder(this)
                .setTitle("تغيير اسم الجهاز داخل التطبيق")
                .setMessage("تغيير الاسم لا يغير هوية الجهاز الثابتة.")
                .setView(input)
                .setPositiveButton("حفظ", (di,w)->{
                    String n = input.getText().toString().trim();
                    if (n.length() > 0) d.name = n;
                    saveDevices(); renderList();
                })
                .setNegativeButton("إلغاء", null).show();
    }

    void confirmRemove(DeviceInfo d) {
        new AlertDialog.Builder(this)
                .setTitle("حذف الجهاز؟")
                .setMessage("سيتم حذفه من قائمة التطبيق فقط، ولا يتأثر برنامج الحاسبة.")
                .setPositiveButton("حذف", (di,w)->{
                    devices.remove(d);
                    prefs.edit().remove("pin_" + d.id).apply();
                    saveDevices(); renderList();
                })
                .setNegativeButton("إلغاء", null).show();
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

    String friendlyError(Exception e) {
        String m = e.getMessage();
        if (m == null) return e.toString();
        if (m.contains("PIN") || m.contains("064a") || m.contains("0635")) {
            return "PIN غير صحيح. امسح الرقم المحفوظ واكتب الرقم الأخضر الظاهر في برنامج الحاسبة.";
        }
        return m.length() > 220 ? m.substring(0, 220) : m;
    }


    void askPinAndOpen(DeviceInfo d) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        final EditText input = new EditText(this);
        input.setHint("PIN الظاهر على برنامج الحاسبة");
        input.setInputType(2);
        input.setText(prefs.getString("pin_" + d.id, ""));
        input.setSelectAllOnFocus(true);
        final CheckBox remember = new CheckBox(this);
        remember.setText("تذكر PIN لهذا الجهاز داخل التطبيق");
        remember.setChecked(input.getText().toString().length() > 0);
        box.addView(input); box.addView(remember);

        new AlertDialog.Builder(this)
                .setTitle("رمز الدخول")
                .setView(box)
                .setPositiveButton("دخول", (di,w)->{
                    String pin = normalizePin(input.getText().toString());
                    new Thread(() -> {
                        try {
                            Net.postJson(d.baseUrl()+"/api/auth", pin, new JSONObject());
                            if (remember.isChecked()) prefs.edit().putString("pin_" + d.id, pin).apply();
                            else prefs.edit().remove("pin_" + d.id).apply();
                            runOnUiThread(() -> {
                                Intent in = new Intent(this, RemoteActivity.class);
                                in.putExtra("url", d.baseUrl());
                                in.putExtra("pin", pin);
                                in.putExtra("name", d.name);
                                startActivity(in);
                            });
                        } catch(Exception e) {
                            prefs.edit().remove("pin_" + d.id).apply();
                            runOnUiThread(() -> Toast.makeText(this, "فشل الدخول: " + friendlyError(e), Toast.LENGTH_LONG).show());
                        }
                    }).start();
                })
                .setNegativeButton("إلغاء", null).show();
    }


    void askPinAndOpenFiles(DeviceInfo d) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        final EditText input = new EditText(this);
        input.setHint("PIN الظاهر على برنامج الحاسبة");
        input.setInputType(2);
        input.setText(prefs.getString("pin_" + d.id, ""));
        input.setSelectAllOnFocus(true);
        final CheckBox remember = new CheckBox(this);
        remember.setText("تذكر PIN لهذا الجهاز داخل التطبيق");
        remember.setChecked(input.getText().toString().length() > 0);
        box.addView(input); box.addView(remember);

        new AlertDialog.Builder(this)
                .setTitle("رمز الدخول للملفات")
                .setView(box)
                .setPositiveButton("فتح الملفات", (di,w)->{
                    String pin = normalizePin(input.getText().toString());
                    new Thread(() -> {
                        try {
                            Net.postJson(d.baseUrl()+"/api/auth", pin, new JSONObject());
                            if (remember.isChecked()) prefs.edit().putString("pin_" + d.id, pin).apply();
                            else prefs.edit().remove("pin_" + d.id).apply();
                            runOnUiThread(() -> {
                                Intent in = new Intent(this, FileTransferActivity.class);
                                in.putExtra("url", d.baseUrl());
                                in.putExtra("pin", pin);
                                in.putExtra("name", d.name);
                                startActivity(in);
                            });
                        } catch(Exception e) {
                            prefs.edit().remove("pin_" + d.id).apply();
                            runOnUiThread(() -> Toast.makeText(this, "فشل الدخول: " + friendlyError(e), Toast.LENGTH_LONG).show());
                        }
                    }).start();
                })
                .setNegativeButton("إلغاء", null).show();
    }

    void manualAdd() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        EditText name = new EditText(this); name.setHint("اسم الجهاز"); name.setText("حاسبتي");
        EditText ip = new EditText(this); ip.setHint("IP مثل 192.168.1.5");
        EditText port = new EditText(this); port.setHint("Port"); port.setText("47655");
        box.addView(name); box.addView(ip); box.addView(port);
        new AlertDialog.Builder(this)
                .setTitle("إضافة يدوي")
                .setView(box)
                .setPositiveButton("إضافة", (d,w)->{
                    try {
                        String deviceName = name.getText().toString().trim();
                        String deviceIp = ip.getText().toString().trim();
                        int p = Integer.parseInt(port.getText().toString().trim());
                        addOrUpdateDevice(new DeviceInfo("MANUAL-"+System.currentTimeMillis(), deviceName.length()==0?"حاسبتي":deviceName, deviceIp, p, "PRO"), true);
                        renderList();
                    } catch(Exception e) { Toast.makeText(this, "تأكد من IP و Port", Toast.LENGTH_LONG).show(); }
                })
                .setNegativeButton("إلغاء", null).show();
    }


    String cleanUrl(String raw) {
        String u = raw == null ? "" : raw.trim();
        while (u.endsWith("/")) u = u.substring(0, u.length()-1);
        return u;
    }

    void relaySettings() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        EditText server = new EditText(this);
        server.setHint("رابط السيرفر مثل http://192.168.1.10:7777 أو https://your-server.com");
        server.setText(prefs.getString("relay_server", ""));
        EditText token = new EditText(this);
        token.setHint("Owner Token");
        token.setText(prefs.getString("owner_token", "SLR-CHANGE-ME-PRO-2026"));
        box.addView(tv("اكتب نفس السيرفر ونفس Owner Token الموجودين في server_config.json و relay_config.json", 13, Neon.MUTED, 0));
        box.addView(server); box.addView(token);
        new AlertDialog.Builder(this)
                .setTitle("Relay الاتصال من أي مكان")
                .setView(box)
                .setPositiveButton("حفظ وتحديث الأجهزة", (d,w)->{
                    String srv = cleanUrl(server.getText().toString());
                    String tok = token.getText().toString().trim();
                    prefs.edit().putString("relay_server", srv).putString("owner_token", tok).apply();
                    relayListDevices(srv, tok);
                })
                .setNegativeButton("إلغاء", null).show();
    }

    void relayListDevices(String relayServer, String ownerToken) {
        status.setText("جاري الاتصال بسيرفر Relay...");
        new Thread(() -> {
            try {
                String raw = Net.getTextWithToken(cleanUrl(relayServer) + "/api/mobile/devices?token=" + java.net.URLEncoder.encode(ownerToken, "UTF-8"), ownerToken);
                JSONObject root = new JSONObject(raw);
                if (!root.optBoolean("ok", false)) throw new Exception(root.optString("error", "فشل الاتصال"));
                JSONArray arr = root.optJSONArray("devices");
                int count = 0;
                if (arr != null) {
                    for (int i=0; i<arr.length(); i++) {
                        JSONObject o = arr.getJSONObject(i);
                        if (!o.optBoolean("online", false)) continue;
                        DeviceInfo di = new DeviceInfo(
                                o.optString("device_id"),
                                o.optString("device_name", "حاسبتي"),
                                "RELAY",
                                0,
                                o.optString("version", "PRO"),
                                true,
                                cleanUrl(relayServer) + "/api/relay/" + java.net.URLEncoder.encode(ownerToken, "UTF-8")
                        );
                        addOrUpdateDevice(di, false);
                        count++;
                    }
                }
                saveDevices();
                final int c = count;
                runOnUiThread(() -> { renderList(); status.setText(c == 0 ? "لا يوجد جهاز متصل بالـ Relay. تأكد أن relay_client شغال على الحاسبة." : "تم تحديث أجهزة Relay: " + c); });
            } catch(Exception e) {
                runOnUiThread(() -> Toast.makeText(this, "فشل Relay: " + friendlyError(e), Toast.LENGTH_LONG).show());
                runOnUiThread(() -> status.setText("فشل الاتصال بالـ Relay"));
            }
        }).start();
    }

    void loadSavedDevices() {
        devices.clear();
        String raw = prefs.getString("devices", "[]");
        try {
            JSONArray arr = new JSONArray(raw);
            for (int i=0; i<arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                devices.add(new DeviceInfo(
                        o.optString("id"),
                        o.optString("name", "حاسبتي"),
                        o.optString("ip", ""),
                        o.optInt("port", 47655),
                        o.optString("version", "PRO"),
                        o.optBoolean("viaRelay", false),
                        o.optString("relayUrl", "")
                ));
            }
        } catch(Exception ignored) {}
    }

    void saveDevices() {
        try {
            JSONArray arr = new JSONArray();
            for (DeviceInfo d: devices) {
                JSONObject o = new JSONObject();
                o.put("id", d.id); o.put("name", d.name); o.put("ip", d.ip); o.put("port", d.port); o.put("version", d.version); o.put("viaRelay", d.viaRelay); o.put("relayUrl", d.relayUrl);
                arr.put(o);
            }
            prefs.edit().putString("devices", arr.toString()).apply();
        } catch(Exception ignored) {}
    }
}
