package com.satlink.remotepro;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/** SatLink Neon theme - shared colors and styled widgets (all sizes in dp). */
public final class Neon {
    private Neon() {}

    public static final int BG        = Color.rgb(5, 6, 15);       // #05060F
    public static final int SURFACE   = Color.rgb(14, 16, 34);     // #0E1022
    public static final int SURFACE_2 = Color.rgb(22, 25, 51);     // #161933
    public static final int CYAN      = Color.rgb(0, 240, 255);    // #00F0FF
    public static final int MAGENTA   = Color.rgb(255, 43, 214);   // #FF2BD6
    public static final int PURPLE    = Color.rgb(138, 92, 255);   // #8A5CFF
    public static final int GREEN     = Color.rgb(57, 255, 136);   // #39FF88
    public static final int RED       = Color.rgb(255, 59, 107);   // #FF3B6B
    public static final int AMBER     = Color.rgb(255, 196, 0);    // #FFC400
    public static final int TEXT      = Color.rgb(230, 241, 255);  // #E6F1FF
    public static final int MUTED     = Color.rgb(138, 160, 200);  // #8AA0C8

    public static int dp(Context c, float v) {
        return Math.round(v * c.getResources().getDisplayMetrics().density);
    }

    public static int alpha(int color, int a) {
        return Color.argb(a, Color.red(color), Color.green(color), Color.blue(color));
    }

    /** Maps the old project colors to neon accents so existing calls keep working. */
    public static int accentFromLegacy(int color) {
        if (color == Color.rgb(31, 111, 235) || color == Color.rgb(74, 163, 255)) return CYAN;
        if (color == Color.rgb(35, 134, 54)) return GREEN;
        if (color == Color.rgb(112, 34, 46) || color == Color.rgb(121, 46, 46) || color == Color.rgb(177, 68, 47)) return RED;
        if (color == Color.rgb(111, 66, 193)) return MAGENTA;
        if (color == Color.rgb(23, 38, 61) || color == Color.rgb(13, 27, 47)) return PURPLE;
        return color;
    }

    public static GradientDrawable rounded(int fill, int stroke, float strokeDp, float radiusDp, Context c) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(fill);
        g.setCornerRadius(dp(c, radiusDp));
        if (strokeDp > 0) g.setStroke(dp(c, strokeDp), stroke);
        return g;
    }

    static Drawable ripple(Drawable content, int accent) {
        return new RippleDrawable(ColorStateList.valueOf(alpha(accent, 90)), content, null);
    }

    /** Outlined neon button: dark glass fill + glowing border + accent text. */
    public static void style(Button b, int accent) {
        Context c = b.getContext();
        b.setAllCaps(false);
        b.setTextColor(accent);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setStateListAnimator(null);
        b.setMinHeight(0); b.setMinimumHeight(0);
        b.setMinWidth(0); b.setMinimumWidth(0);
        b.setPadding(dp(c, 10), dp(c, 4), dp(c, 10), dp(c, 4));
        b.setShadowLayer(dp(c, 6), 0, 0, alpha(accent, 170));
        b.setBackground(ripple(rounded(alpha(accent, 28), alpha(accent, 210), 1.4f, 12, c), accent));
    }

    /** Filled gradient button for the main action. */
    public static void stylePrimary(Button b) {
        Context c = b.getContext();
        b.setAllCaps(false);
        b.setTextColor(BG);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setStateListAnimator(null);
        b.setMinHeight(0); b.setMinimumHeight(0);
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT, new int[]{CYAN, PURPLE});
        g.setCornerRadius(dp(c, 14));
        b.setBackground(ripple(g, Color.WHITE));
    }

    public static Button button(Context c, String text, int accent) {
        Button b = new Button(c);
        b.setText(text);
        b.setTextSize(14);
        style(b, accent);
        return b;
    }

    public static Button smallButton(Context c, String text, int accent) {
        Button b = button(c, text, accent);
        b.setTextSize(12);
        b.setSingleLine(true);
        b.setPadding(dp(c, 6), 0, dp(c, 6), 0);
        b.setShadowLayer(dp(c, 4), 0, 0, alpha(accent, 150));
        return b;
    }

    /** Full-width button params: 52dp tall with spacing. */
    public static LinearLayout.LayoutParams btnLp(Context c) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, dp(c, 52));
        lp.setMargins(0, dp(c, 5), 0, dp(c, 5));
        return lp;
    }

    public static Drawable card(Context c) {
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.TL_BR, new int[]{SURFACE_2, SURFACE});
        g.setCornerRadius(dp(c, 18));
        g.setStroke(dp(c, 1), alpha(CYAN, 90));
        return g;
    }

    public static Drawable glassPanel(Context c) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(alpha(BG, 215));
        g.setCornerRadius(dp(c, 18));
        g.setStroke(dp(c, 1), alpha(CYAN, 140));
        return g;
    }

    public static Drawable circle(Context c, int accent) {
        GradientDrawable g = new GradientDrawable();
        g.setShape(GradientDrawable.OVAL);
        g.setColor(alpha(BG, 200));
        g.setStroke(dp(c, 2), accent);
        return ripple(g, accent);
    }

    public static void glowText(TextView t, int color) {
        t.setTextColor(color);
        t.setShadowLayer(dp(t.getContext(), 10), 0, 0, alpha(color, 200));
    }

    public static View divider(Context c) {
        View v = new View(c);
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT,
                new int[]{alpha(CYAN, 0), alpha(CYAN, 200), alpha(MAGENTA, 200), alpha(MAGENTA, 0)});
        v.setBackground(g);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, dp(c, 2));
        lp.setMargins(0, dp(c, 8), 0, dp(c, 10));
        v.setLayoutParams(lp);
        return v;
    }

    public static TextView chip(Context c, String text) {
        TextView t = new TextView(c);
        t.setText(text);
        t.setTextSize(13);
        t.setGravity(Gravity.CENTER);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        t.setPadding(dp(c, 14), 0, dp(c, 14), 0);
        setChipActive(t, false);
        return t;
    }

    public static void setChipActive(TextView t, boolean active) {
        Context c = t.getContext();
        if (active) {
            GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT, new int[]{CYAN, PURPLE});
            g.setCornerRadius(dp(c, 20));
            t.setBackground(g);
            t.setTextColor(BG);
            t.setShadowLayer(0, 0, 0, 0);
        } else {
            t.setBackground(ripple(rounded(alpha(SURFACE_2, 230), alpha(PURPLE, 160), 1, 20, c), CYAN));
            t.setTextColor(MUTED);
        }
    }
}
