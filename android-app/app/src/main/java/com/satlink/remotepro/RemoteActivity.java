package com.satlink.remotepro;

import android.app.*;
import android.os.*;
import android.graphics.*;
import android.view.*;
import android.widget.*;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * SatLink Remote PRO 2.3.0 Neon
 * - Full-screen remote view (no empty/black margins in "fill" mode, pan is clamped).
 * - Floating, collapsible neon control panel sized in dp and kept clear of system bars.
 * - Direct touch mode + Touchpad mode, keyboard keys, shortcuts and power actions.
 */
public class RemoteActivity extends Activity {
    // ---- views ----
    FrameLayout root;
    ImageView screen;
    TextView hud;
    LinearLayout panel, chipRow, grid;
    HorizontalScrollView chipScroll;
    TextView fab;
    TextView[] chips;

    // ---- connection ----
    String baseUrl, pin, name;
    volatile boolean running = true;
    volatile int imgW = 1, imgH = 1;

    // ---- view transform ----
    Matrix imageMatrix = new Matrix();
    boolean fillMode = true;      // true = fill whole phone screen, false = show whole PC screen
    float zoom = 1.0f;
    float panX = 0f, panY = 0f;
    float lastPanX = 0f, lastPanY = 0f;

    // ---- input modes ----
    boolean dragMode = false;
    boolean touchpadMode = false;
    boolean remoteDragging = false;
    long lastMoveSent = 0;
    long lastTapAt = 0;
    float lastTapX = 0, lastTapY = 0;
    float downX = 0, downY = 0, prevX = 0, prevY = 0;
    long downTime = 0;
    float tpAccX = 0, tpAccY = 0;
    float scrollAcc = 0;
    boolean multiMoved = false;
    long multiDownAt = 0;
    int maxPointers = 0;
    static final float TOUCHPAD_SPEED = 1.7f;

    // ---- speed engine ----
    int qualityIndex = 1;
    int[] jpegQuality = {35, 50, 58, 42};
    float[] streamScale = {0.40f, 0.58f, 0.72f, 0.48f};
    long[] frameDelay = {750, 420, 230, 120};
    long[] moveDelay = {110, 70, 45, 30};
    int[] maxWidth = {900, 1200, 1500, 1000};
    String[] qualityNames = {"اقتصادي", "متوازن", "سريع", "Turbo"};
    volatile long lastLatencyMs = 0;
    int fpsCounter = 0;
    long fpsWindowStart = System.currentTimeMillis();
    volatile int currentFps = 0;
    volatile String streamError = null;

    // ---- panel ----
    boolean panelOpen = true;
    int currentTab = 0;
    String[] tabNames = {"🖱 الماوس", "⌨ المفاتيح", "⚡ اختصارات", "🖥 العرض", "⏻ الطاقة"};
    int insetL = 0, insetT = 0, insetR = 0, insetB = 0;

    ScaleGestureDetector scaleDetector;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        baseUrl = getIntent().getStringExtra("url");
        pin = getIntent().getStringExtra("pin");
        name = getIntent().getStringExtra("name");
        if (name == null) name = "حاسبتي";
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if (Build.VERSION.SDK_INT >= 28) {
            WindowManager.LayoutParams lp = getWindow().getAttributes();
            lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            getWindow().setAttributes(lp);
        }
        getWindow().setStatusBarColor(Neon.BG);
        getWindow().setNavigationBarColor(Neon.BG);
        build();
        hideBars();
        startStream();
    }

    @Override protected void onDestroy() {
        running = false;
        super.onDestroy();
    }

    @Override public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideBars();
    }

    void hideBars() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN |
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }

    int dp(float v) { return Neon.dp(this, v); }

    // =====================================================================
    // UI
    // =====================================================================
    void build() {
        scaleDetector = new ScaleGestureDetector(this, new ScaleGestureDetector.SimpleOnScaleGestureListener() {
            @Override public boolean onScale(ScaleGestureDetector d) {
                if (touchpadMode) return true;
                float[] before = layoutInfo();
                float newZoom = Math.max(1.0f, Math.min(5.0f, zoom * d.getScaleFactor()));
                float ratio = newZoom / zoom;
                zoom = newZoom;
                // keep the point under the fingers fixed while zooming
                float fx = d.getFocusX(), fy = d.getFocusY();
                float newLeft = fx - (fx - before[1]) * ratio;
                float newTop = fy - (fy - before[2]) * ratio;
                float[] centered = centeredOrigin();
                panX = newLeft - centered[0];
                panY = newTop - centered[1];
                updateImageMatrix();
                return true;
            }
        });

        root = new FrameLayout(this);
        root.setBackgroundColor(Neon.BG);

        screen = new ImageView(this);
        screen.setBackgroundColor(Neon.BG);
        screen.setScaleType(ImageView.ScaleType.MATRIX);
        root.addView(screen, new FrameLayout.LayoutParams(-1, -1));
        screen.setOnTouchListener((v, e) -> handleTouch(e));
        screen.addOnLayoutChangeListener((v, l, t, r, bt, ol, ot, or, ob) -> {
            updateImageMatrix();
            if (r - l != or - ol) renderGrid();
        });

        // ---- HUD (top-left status pill) ----
        hud = new TextView(this);
        hud.setTextSize(11);
        hud.setTextColor(Neon.CYAN);
        hud.setSingleLine(true);
        hud.setPadding(dp(12), dp(5), dp(12), dp(5));
        hud.setBackground(Neon.rounded(Neon.alpha(Neon.BG, 190), Neon.alpha(Neon.CYAN, 140), 1, 14, this));
        hud.setText("● " + name + " | جاري الاتصال...");
        root.addView(hud, new FrameLayout.LayoutParams(-2, -2, Gravity.TOP | Gravity.START));

        // ---- floating toggle button (top-right) ----
        fab = new TextView(this);
        fab.setText("✕");
        fab.setTextSize(20);
        fab.setGravity(Gravity.CENTER);
        fab.setTypeface(Typeface.DEFAULT_BOLD);
        Neon.glowText(fab, Neon.CYAN);
        fab.setBackground(Neon.circle(this, Neon.CYAN));
        root.addView(fab, new FrameLayout.LayoutParams(dp(48), dp(48), Gravity.TOP | Gravity.END));
        fab.setOnClickListener(v -> setPanelOpen(!panelOpen));

        // ---- floating control panel (bottom) ----
        panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setBackground(Neon.glassPanel(this));
        panel.setPadding(dp(8), dp(8), dp(8), dp(8));
        panel.setClickable(true); // swallow touches so they don't reach the PC screen

        chipScroll = new HorizontalScrollView(this);
        chipScroll.setHorizontalScrollBarEnabled(false);
        chipRow = new LinearLayout(this);
        chipRow.setOrientation(LinearLayout.HORIZONTAL);
        chipScroll.addView(chipRow);
        panel.addView(chipScroll, new LinearLayout.LayoutParams(-1, dp(36)));

        chips = new TextView[tabNames.length];
        for (int i = 0; i < tabNames.length; i++) {
            final int idx = i;
            TextView c = Neon.chip(this, tabNames[i]);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-2, -1);
            lp.setMargins(0, 0, dp(6), 0);
            chipRow.addView(c, lp);
            c.setOnClickListener(v -> selectTab(idx));
            chips[i] = c;
        }
        Button exit = Neon.smallButton(this, "✕ خروج", Neon.RED);
        LinearLayout.LayoutParams elp = new LinearLayout.LayoutParams(-2, -1);
        elp.setMargins(dp(6), 0, 0, 0);
        chipRow.addView(exit, elp);
        exit.setOnClickListener(v -> finish());

        grid = new LinearLayout(this);
        grid.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams glp = new LinearLayout.LayoutParams(-1, -2);
        glp.setMargins(0, dp(8), 0, 0);
        panel.addView(grid, glp);

        root.addView(panel, new FrameLayout.LayoutParams(-1, -2, Gravity.BOTTOM));

        // keep floating controls clear of nav bar / gesture area / notch
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            int l = insets.getStableInsetLeft(), t = insets.getStableInsetTop();
            int r = insets.getStableInsetRight(), bt = insets.getStableInsetBottom();
            if (Build.VERSION.SDK_INT >= 28 && insets.getDisplayCutout() != null) {
                DisplayCutout dc = insets.getDisplayCutout();
                l = Math.max(l, dc.getSafeInsetLeft()); t = Math.max(t, dc.getSafeInsetTop());
                r = Math.max(r, dc.getSafeInsetRight()); bt = Math.max(bt, dc.getSafeInsetBottom());
            }
            insetL = l; insetT = t; insetR = r; insetB = bt;
            applyInsets();
            return insets;
        });

        setContentView(root);
        applyInsets();
        selectTab(0);
    }

    void applyInsets() {
        int m = dp(8);
        FrameLayout.LayoutParams hp = (FrameLayout.LayoutParams) hud.getLayoutParams();
        hp.setMargins(insetL + m, insetT + m, 0, 0);
        hud.setLayoutParams(hp);
        FrameLayout.LayoutParams fp = (FrameLayout.LayoutParams) fab.getLayoutParams();
        fp.setMargins(0, insetT + m, insetR + m, 0);
        fab.setLayoutParams(fp);
        FrameLayout.LayoutParams pp = (FrameLayout.LayoutParams) panel.getLayoutParams();
        pp.setMargins(insetL + m, 0, insetR + m, insetB + m);
        panel.setLayoutParams(pp);
    }

    void setPanelOpen(boolean open) {
        panelOpen = open;
        panel.setVisibility(open ? View.VISIBLE : View.GONE);
        fab.setText(open ? "✕" : "☰");
        hideBars();
    }

    void selectTab(int idx) {
        currentTab = idx;
        for (int i = 0; i < chips.length; i++) Neon.setChipActive(chips[i], i == idx);
        renderGrid();
    }

    /** Builds the button grid for the current tab. Columns adapt to the screen width so every button is visible. */
    void renderGrid() {
        if (grid == null) return;
        grid.removeAllViews();
        java.util.List<Button> items = new java.util.ArrayList<>();

        switch (currentTab) {
            case 0: { // mouse
                Button tp = Neon.smallButton(this, touchpadMode ? "Touchpad: ON" : "Touchpad: OFF", touchpadMode ? Neon.GREEN : Neon.PURPLE);
                tp.setOnClickListener(v -> toggleTouchpad());
                Button drag = Neon.smallButton(this, dragMode ? "سحب: ON" : "سحب: OFF", dragMode ? Neon.GREEN : Neon.PURPLE);
                drag.setOnClickListener(v -> toggleDrag());
                items.add(tp); items.add(drag);
                items.add(action("نقرة يمين", Neon.CYAN, () -> sendHere("right_here")));
                items.add(action("دبل كلك", Neon.CYAN, () -> sendHere("double_here")));
                items.add(action("Scroll ↑", Neon.MAGENTA, () -> sendScroll(3)));
                items.add(action("Scroll ↓", Neon.MAGENTA, () -> sendScroll(-3)));
                items.add(action("نقرة وسط", Neon.CYAN, () -> sendHere("middle_here")));
                break;
            }
            case 1: { // keys
                items.add(action("✎ كتابة", Neon.GREEN, this::askText));
                items.add(key("Enter", "enter"));
                items.add(key("Esc", "esc"));
                items.add(key("⌫ Back", "backspace"));
                items.add(key("Tab", "tab"));
                items.add(key("Del", "delete"));
                items.add(key("←", "left"));
                items.add(key("↑", "up"));
                items.add(key("↓", "down"));
                items.add(key("→", "right"));
                items.add(key("Home", "home"));
                items.add(key("End", "end"));
                items.add(key("PgUp", "pageup"));
                items.add(key("PgDn", "pagedown"));
                items.add(key("Space", "space"));
                items.add(key("F5", "f5"));
                break;
            }
            case 2: { // shortcuts
                items.add(combo("نسخ Ctrl+C", "ctrl", "c"));
                items.add(combo("لصق Ctrl+V", "ctrl", "v"));
                items.add(combo("قص Ctrl+X", "ctrl", "x"));
                items.add(combo("تراجع Ctrl+Z", "ctrl", "z"));
                items.add(combo("تحديد Ctrl+A", "ctrl", "a"));
                items.add(combo("حفظ Ctrl+S", "ctrl", "s"));
                items.add(combo("Alt+Tab", "alt", "tab"));
                items.add(combo("⊞ Win", "win"));
                items.add(combo("سطح المكتب", "win", "d"));
                items.add(combo("المستكشف", "win", "e"));
                items.add(combo("إغلاق Alt+F4", "alt", "f4"));
                items.add(combo("مدير المهام", "ctrl", "shift", "esc"));
                items.add(combo("لغة Alt+Shift", "alt", "shift"));
                break;
            }
            case 3: { // view
                items.add(action("الجودة: " + qualityNames[qualityIndex], Neon.CYAN, () -> {
                    qualityIndex = (qualityIndex + 1) % qualityNames.length; renderGrid();
                }));
                items.add(action("⚡ Turbo", Neon.GREEN, () -> { qualityIndex = 3; renderGrid(); toast("Turbo Mode"); }));
                items.add(action(fillMode ? "عرض الشاشة كاملة" : "ملء شاشة الموبايل", Neon.MAGENTA, () -> {
                    fillMode = !fillMode; zoom = 1f; panX = 0; panY = 0; updateImageMatrix(); renderGrid();
                }));
                items.add(action("ضبط الزوم", Neon.PURPLE, () -> { zoom = 1f; panX = 0; panY = 0; updateImageMatrix(); }));
                items.add(action("⟳ إعادة اتصال", Neon.CYAN, this::reconnect));
                break;
            }
            case 4: { // power
                items.add(action("🔒 قفل الحاسبة", Neon.CYAN, () -> confirmPower("lock", "قفل الحاسبة؟")));
                items.add(action("☾ سكون", Neon.PURPLE, () -> confirmPower("sleep", "وضع الحاسبة بالسكون؟ سينقطع الاتصال.")));
                items.add(action("⟳ إعادة تشغيل", Neon.AMBER, () -> confirmPower("restart", "إعادة تشغيل الحاسبة خلال 10 ثواني؟")));
                items.add(action("⏻ إطفاء", Neon.RED, () -> confirmPower("shutdown", "إطفاء الحاسبة خلال 10 ثواني؟")));
                items.add(action("إلغاء الإطفاء", Neon.GREEN, () -> sendPower("cancel")));
                break;
            }
        }

        int widthPx = root.getWidth() > 0 ? root.getWidth() : getResources().getDisplayMetrics().widthPixels;
        float widthDp = (widthPx - insetL - insetR) / getResources().getDisplayMetrics().density - 32;
        int cols = Math.max(3, Math.min(8, (int) (widthDp / 92)));
        LinearLayout row = null;
        for (int i = 0; i < items.size(); i++) {
            if (i % cols == 0) {
                row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                grid.addView(row, new LinearLayout.LayoutParams(-1, dp(40)));
            }
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, -1, 1f);
            lp.setMargins(dp(3), dp(3), dp(3), dp(3));
            row.addView(items.get(i), lp);
        }
        // pad the last row so buttons keep the same width
        int rem = items.size() % cols;
        if (rem != 0 && row != null) {
            for (int i = rem; i < cols; i++) {
                View sp = new View(this);
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, -1, 1f);
                lp.setMargins(dp(3), dp(3), dp(3), dp(3));
                row.addView(sp, lp);
            }
        }
    }

    Button action(String text, int accent, Runnable r) {
        Button b = Neon.smallButton(this, text, accent);
        b.setOnClickListener(v -> { r.run(); hideBars(); });
        return b;
    }

    Button key(String label, String keyName) {
        return action(label, Neon.CYAN, () -> sendKey(keyName));
    }

    Button combo(String label, String... keys) {
        return action(label, Neon.MAGENTA, () -> sendHotkey(keys));
    }

    void toggleTouchpad() {
        touchpadMode = !touchpadMode;
        if (touchpadMode) { zoom = 1f; panX = 0; panY = 0; updateImageMatrix(); }
        toast(touchpadMode
                ? "Touchpad: حرّك إصبع واحد للماوس، نقرة = كلك، إصبعين = Scroll، نقرة بإصبعين = يمين"
                : "اللمس المباشر: المس المكان لتضغط عليه");
        renderGrid();
    }

    void toggleDrag() {
        dragMode = !dragMode;
        toast(dragMode ? "وضع السحب مفعّل" : "وضع السحب متوقف");
        renderGrid();
    }

    void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_SHORT).show(); }

    // =====================================================================
    // Touch
    // =====================================================================
    boolean handleTouch(MotionEvent e) {
        hideBars();
        int action = e.getActionMasked();
        if (action == MotionEvent.ACTION_DOWN) { maxPointers = 1; multiMoved = false; }
        maxPointers = Math.max(maxPointers, e.getPointerCount());

        if (touchpadMode) return handleTouchpad(e, action);

        scaleDetector.onTouchEvent(e);
        if (e.getPointerCount() >= 2 || maxPointers >= 2) {
            if (e.getPointerCount() >= 2) {
                float cx = (e.getX(0) + e.getX(1)) / 2f;
                float cy = (e.getY(0) + e.getY(1)) / 2f;
                if (action == MotionEvent.ACTION_POINTER_DOWN) {
                    lastPanX = cx; lastPanY = cy;
                } else if (action == MotionEvent.ACTION_MOVE) {
                    panX += cx - lastPanX;
                    panY += cy - lastPanY;
                    lastPanX = cx; lastPanY = cy;
                    updateImageMatrix();
                } else if (action == MotionEvent.ACTION_POINTER_UP) {
                    int keep = e.getActionIndex() == 0 ? 1 : 0;
                    lastPanX = e.getX(keep); lastPanY = e.getY(keep);
                }
            }
            if (remoteDragging) { remoteDragging = false; float[] xy = mapTouchToImage(e.getX(), e.getY()); sendInput("mouse_up", xy[0], xy[1]); }
            return true;
        }

        float x = e.getX(), y = e.getY();
        float[] xy = mapTouchToImage(x, y);

        if (dragMode) {
            if (action == MotionEvent.ACTION_DOWN) {
                remoteDragging = true;
                sendInput("mouse_down", xy[0], xy[1]);
            } else if (action == MotionEvent.ACTION_MOVE && remoteDragging) {
                throttleMove(xy[0], xy[1]);
            } else if ((action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_CANCEL) && remoteDragging) {
                remoteDragging = false;
                sendInput("mouse_up", xy[0], xy[1]);
            }
            return true;
        }

        if (action == MotionEvent.ACTION_DOWN) {
            downX = x; downY = y; downTime = System.currentTimeMillis();
        } else if (action == MotionEvent.ACTION_MOVE) {
            throttleMove(xy[0], xy[1]);
        } else if (action == MotionEvent.ACTION_UP) {
            float dx = x - downX, dy = y - downY;
            long now = System.currentTimeMillis();
            if (Math.hypot(dx, dy) < dp(10) && (now - downTime) < 450) {
                if ((now - lastTapAt) < 360 && Math.abs(x - lastTapX) < dp(16) && Math.abs(y - lastTapY) < dp(16)) {
                    sendInput("double_click", xy[0], xy[1]);
                    lastTapAt = 0;
                } else {
                    sendInput("tap", xy[0], xy[1]);
                    lastTapAt = now; lastTapX = x; lastTapY = y;
                }
            }
        }
        return true;
    }

    boolean handleTouchpad(MotionEvent e, int action) {
        float total = layoutInfo()[0];
        if (e.getPointerCount() >= 2) {
            float cy = (e.getY(0) + e.getY(1)) / 2f;
            if (action == MotionEvent.ACTION_POINTER_DOWN) {
                lastPanY = cy; scrollAcc = 0; multiDownAt = System.currentTimeMillis();
            } else if (action == MotionEvent.ACTION_MOVE) {
                float d = cy - lastPanY;
                lastPanY = cy;
                scrollAcc += d;
                if (Math.abs(scrollAcc) > dp(6)) multiMoved = true;
                float step = dp(28);
                while (Math.abs(scrollAcc) >= step) {
                    int dir = scrollAcc > 0 ? 1 : -1; // finger down = content up (natural)
                    sendScroll(dir);
                    scrollAcc -= dir * step;
                }
            } else if (action == MotionEvent.ACTION_POINTER_UP) {
                if (!multiMoved && System.currentTimeMillis() - multiDownAt < 350) sendHere("right_here");
                multiMoved = true; // only one right click per gesture
            }
            return true;
        }
        if (maxPointers >= 2) { // finishing a two-finger gesture
            if (action == MotionEvent.ACTION_UP) maxPointers = 0;
            return true;
        }

        float x = e.getX(), y = e.getY();
        if (action == MotionEvent.ACTION_DOWN) {
            downX = prevX = x; downY = prevY = y; downTime = System.currentTimeMillis();
            tpAccX = 0; tpAccY = 0;
            if (dragMode) { remoteDragging = true; sendHere("down_here"); }
        } else if (action == MotionEvent.ACTION_MOVE) {
            tpAccX += (x - prevX) / Math.max(total, 0.0001f) * TOUCHPAD_SPEED;
            tpAccY += (y - prevY) / Math.max(total, 0.0001f) * TOUCHPAD_SPEED;
            prevX = x; prevY = y;
            long now = System.currentTimeMillis();
            if (now - lastMoveSent > moveDelay[qualityIndex] && (Math.abs(tpAccX) >= 1 || Math.abs(tpAccY) >= 1)) {
                lastMoveSent = now;
                sendRelative(tpAccX, tpAccY);
                tpAccX = 0; tpAccY = 0;
            }
        } else if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_CANCEL) {
            if (Math.abs(tpAccX) >= 1 || Math.abs(tpAccY) >= 1) sendRelative(tpAccX, tpAccY);
            tpAccX = 0; tpAccY = 0;
            if (remoteDragging) { remoteDragging = false; sendHere("up_here"); return true; }
            long now = System.currentTimeMillis();
            if (action == MotionEvent.ACTION_UP && Math.hypot(x - downX, y - downY) < dp(10) && now - downTime < 300) {
                sendHere("click_here");
            }
        }
        return true;
    }

    void throttleMove(float x, float y) {
        long now = System.currentTimeMillis();
        if (now - lastMoveSent > moveDelay[qualityIndex]) {
            lastMoveSent = now;
            sendInput("move", x, y);
        }
    }

    // =====================================================================
    // Stream
    // =====================================================================
    void startStream() {
        new Thread(() -> {
            while (running) {
                try {
                    int mode = qualityIndex;
                    long t0 = System.currentTimeMillis();
                    String url = baseUrl + "/api/screenshot?quality=" + jpegQuality[mode]
                            + "&scale=" + streamScale[mode]
                            + "&max_width=" + maxWidth[mode]
                            + "&fast=1&cursor=1&t=" + System.currentTimeMillis();
                    Bitmap b = Net.getBitmap(url, pin);
                    lastLatencyMs = System.currentTimeMillis() - t0;
                    if (b != null) {
                        streamError = null;
                        long at = System.currentTimeMillis();
                        fpsCounter++;
                        if (at - fpsWindowStart >= 1000) {
                            currentFps = fpsCounter;
                            fpsCounter = 0;
                            fpsWindowStart = at;
                        }
                        runOnUiThread(() -> {
                            imgW = b.getWidth(); imgH = b.getHeight();
                            screen.setImageBitmap(b);
                            updateImageMatrix();
                            updateHud();
                        });
                    }
                    long sleep = Math.max(20, frameDelay[mode] - lastLatencyMs);
                    Thread.sleep(sleep);
                } catch (Exception e) {
                    streamError = friendly(e);
                    runOnUiThread(this::updateHud);
                    try { Thread.sleep(900); } catch (Exception ignored) {}
                }
            }
        }).start();
    }

    void updateHud() {
        if (streamError != null) {
            hud.setTextColor(Neon.RED);
            hud.setText("● توقف البث: " + streamError);
            return;
        }
        hud.setTextColor(Neon.CYAN);
        hud.setText("● " + name + "  |  " + qualityNames[qualityIndex] + "  |  " + currentFps + " FPS  |  " + lastLatencyMs + "ms"
                + (touchpadMode ? "  |  Touchpad" : "") + (dragMode ? "  |  سحب" : ""));
    }

    String friendly(Exception e) {
        String m = e.getMessage();
        if (m == null) return e.toString();
        if (m.contains("PIN")) return "PIN غير صحيح";
        if (m.contains("Connection refused")) return "برنامج الحاسبة متوقف";
        if (m.contains("timed out") || m.contains("timeout")) return "انتهت مهلة الاتصال";
        return m.length() > 90 ? m.substring(0, 90) : m;
    }

    void reconnect() {
        screen.setImageBitmap(null);
        zoom = 1.0f; panX = 0; panY = 0;
        streamError = null;
        hud.setText("● جاري إعادة الاتصال...");
        hideBars();
    }

    // =====================================================================
    // Transform (fit / fill, zoom, clamped pan -> no empty areas)
    // =====================================================================
    float baseScale(int vw, int vh) {
        float sx = (float) vw / imgW, sy = (float) vh / imgH;
        return fillMode ? Math.max(sx, sy) : Math.min(sx, sy);
    }

    /** origin (left, top) of the image when centered at the current zoom */
    float[] centeredOrigin() {
        int vw = screen.getWidth(), vh = screen.getHeight();
        float total = baseScale(vw, vh) * zoom;
        return new float[]{(vw - imgW * total) / 2f, (vh - imgH * total) / 2f};
    }

    /** Clamps pan so the picture never leaves an empty gap. Returns {scale, left, top}. */
    float[] layoutInfo() {
        int vw = screen.getWidth(), vh = screen.getHeight();
        if (vw <= 0 || vh <= 0 || imgW <= 0 || imgH <= 0) return new float[]{1f, 0f, 0f};
        float total = baseScale(vw, vh) * zoom;
        float w = imgW * total, h = imgH * total;
        float cx = (vw - w) / 2f, cy = (vh - h) / 2f;
        float left, top;
        if (w <= vw) { left = cx; panX = 0; }
        else { left = Math.max(vw - w, Math.min(0, cx + panX)); panX = left - cx; }
        if (h <= vh) { top = cy; panY = 0; }
        else { top = Math.max(vh - h, Math.min(0, cy + panY)); panY = top - cy; }
        return new float[]{total, left, top};
    }

    void updateImageMatrix() {
        if (screen == null || screen.getWidth() <= 0) return;
        float[] li = layoutInfo();
        imageMatrix.reset();
        imageMatrix.setScale(li[0], li[0]);
        imageMatrix.postTranslate(li[1], li[2]);
        screen.setImageMatrix(imageMatrix);
    }

    float[] mapTouchToImage(float x, float y) {
        float[] li = layoutInfo();
        float ix = (x - li[1]) / Math.max(li[0], 0.0001f);
        float iy = (y - li[2]) / Math.max(li[0], 0.0001f);
        ix = Math.max(0, Math.min(imgW - 1, ix));
        iy = Math.max(0, Math.min(imgH - 1, iy));
        return new float[]{ix, iy};
    }

    // =====================================================================
    // Network actions
    // =====================================================================
    void post(String path, JSONObject o) {
        new Thread(() -> {
            try { Net.postJson(baseUrl + path, pin, o); } catch (Exception ignored) {}
        }).start();
    }

    void sendInput(String action, float x, float y) {
        try {
            JSONObject o = new JSONObject();
            o.put("action", action);
            o.put("x", x); o.put("y", y);
            o.put("screen_width", imgW); o.put("screen_height", imgH);
            post("/api/input", o);
        } catch (Exception ignored) {}
    }

    /** Action at the current PC cursor position (touchpad mode / panel buttons). */
    void sendHere(String action) {
        try {
            JSONObject o = new JSONObject();
            o.put("action", action);
            post("/api/input", o);
        } catch (Exception ignored) {}
    }

    void sendRelative(float dx, float dy) {
        try {
            JSONObject o = new JSONObject();
            o.put("action", "move_rel");
            o.put("dx", dx); o.put("dy", dy);
            o.put("screen_width", imgW); o.put("screen_height", imgH);
            post("/api/input", o);
        } catch (Exception ignored) {}
    }

    void sendScroll(int notches) {
        try {
            JSONObject o = new JSONObject();
            o.put("action", "scroll_here");
            o.put("amount", notches);
            post("/api/input", o);
        } catch (Exception ignored) {}
    }

    void sendKey(String key) {
        try {
            JSONObject o = new JSONObject();
            o.put("action", "key");
            o.put("key", key);
            post("/api/input", o);
        } catch (Exception ignored) {}
    }

    void sendHotkey(String... keys) {
        try {
            JSONObject o = new JSONObject();
            o.put("action", "hotkey");
            JSONArray arr = new JSONArray();
            for (String k : keys) arr.put(k);
            o.put("keys", arr);
            post("/api/input", o);
        } catch (Exception ignored) {}
    }

    void confirmPower(String action, String message) {
        new AlertDialog.Builder(this)
                .setTitle("تأكيد")
                .setMessage(message)
                .setPositiveButton("نعم", (d, w) -> sendPower(action))
                .setNegativeButton("إلغاء", null)
                .setOnDismissListener(d -> hideBars())
                .show();
    }

    void sendPower(String action) {
        new Thread(() -> {
            try {
                JSONObject o = new JSONObject();
                o.put("action", action);
                Net.postJson(baseUrl + "/api/power", pin, o);
                runOnUiThread(() -> toast("تم إرسال الأمر"));
            } catch (Exception e) {
                runOnUiThread(() -> toast("فشل: " + friendly(e)));
            }
        }).start();
    }

    void askText() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(16), dp(8), dp(16), 0);
        EditText input = new EditText(this);
        input.setHint("اكتب النص (عربي أو إنكليزي)");
        input.setSingleLine(false);
        CheckBox enter = new CheckBox(this);
        enter.setText("اضغط Enter بعد الكتابة");
        box.addView(input); box.addView(enter);
        new AlertDialog.Builder(this)
                .setTitle("كتابة نص")
                .setView(box)
                .setPositiveButton("إرسال", (d, w) -> {
                    String t = input.getText().toString();
                    boolean withEnter = enter.isChecked();
                    new Thread(() -> {
                        try {
                            JSONObject o = new JSONObject();
                            o.put("action", "text");
                            o.put("text", t);
                            Net.postJson(baseUrl + "/api/input", pin, o);
                            if (withEnter) {
                                JSONObject k = new JSONObject();
                                k.put("action", "key"); k.put("key", "enter");
                                Net.postJson(baseUrl + "/api/input", pin, k);
                            }
                        } catch (Exception ignored) {}
                    }).start();
                })
                .setNegativeButton("إلغاء", null)
                .setOnDismissListener(d -> hideBars())
                .show();
    }
}
