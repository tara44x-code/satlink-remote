package com.satlink.remotepro;

import android.content.ContentResolver;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.util.*;

public class Net {
    public interface DiscoveryCallback { void onDevice(DeviceInfo d); void onDone(); }
    public static final int DISCOVERY_PORT = 47656;
    public static final String MAGIC = "SATLINK_REMOTE_PRO_DISCOVER";

    static String normalizePin(String raw) {
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


    static String withPin(String url, String pin) throws Exception {
        String p = URLEncoder.encode(normalizePin(pin), "UTF-8");
        if (url.contains("?")) return url + "&pin=" + p;
        return url + "?pin=" + p;
    }

    public static void discover(DiscoveryCallback cb) {
        new Thread(() -> {
            DatagramSocket socket = null;
            try {
                socket = new DatagramSocket();
                socket.setBroadcast(true);
                socket.setSoTimeout(900);
                byte[] data = MAGIC.getBytes("UTF-8");
                DatagramPacket packet = new DatagramPacket(data, data.length, InetAddress.getByName("255.255.255.255"), DISCOVERY_PORT);
                socket.send(packet);
                long end = System.currentTimeMillis() + 2500;
                Set<String> seen = new HashSet<>();
                while (System.currentTimeMillis() < end) {
                    try {
                        byte[] buf = new byte[4096];
                        DatagramPacket resp = new DatagramPacket(buf, buf.length);
                        socket.receive(resp);
                        String json = new String(resp.getData(), 0, resp.getLength(), "UTF-8");
                        JSONObject o = new JSONObject(json);
                        String id = o.optString("device_id");
                        if (seen.contains(id)) continue;
                        seen.add(id);
                        cb.onDevice(new DeviceInfo(id, o.optString("device_name"), resp.getAddress().getHostAddress(), o.optInt("port", 47655), o.optString("version", "PRO")));
                    } catch (Exception ignored) {}
                }
            } catch (Exception ignored) {} finally { if (socket != null) socket.close(); cb.onDone(); }
        }).start();
    }

    public static String postJson(String url, String pin, JSONObject body) throws Exception {
        HttpURLConnection c = (HttpURLConnection)new URL(withPin(url, pin)).openConnection();
        c.setRequestMethod("POST"); c.setConnectTimeout(4000); c.setReadTimeout(7000);
        c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        c.setRequestProperty("X-SatLink-PIN", normalizePin(pin));
        c.setDoOutput(true);
        OutputStream os = c.getOutputStream(); os.write(body.toString().getBytes("UTF-8")); os.close();
        return readResponse(c);
    }

    public static String getText(String url, String pin) throws Exception {
        HttpURLConnection c = (HttpURLConnection)new URL(withPin(url, pin)).openConnection();
        c.setRequestMethod("GET"); c.setConnectTimeout(4000); c.setReadTimeout(7000);
        c.setRequestProperty("X-SatLink-PIN", normalizePin(pin));
        return readResponse(c);
    }

    static String readResponse(HttpURLConnection c) throws Exception {
        InputStream is = c.getResponseCode() >= 400 ? c.getErrorStream() : c.getInputStream();
        if (is == null) throw new IOException("HTTP " + c.getResponseCode());
        BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
        StringBuilder sb = new StringBuilder(); String line; while ((line = br.readLine()) != null) sb.append(line);
        br.close();
        if (c.getResponseCode() >= 400) throw new IOException(sb.toString());
        return sb.toString();
    }

    public static Bitmap getBitmap(String url, String pin) throws Exception {
        HttpURLConnection c = (HttpURLConnection)new URL(withPin(url, pin)).openConnection();
        c.setConnectTimeout(2500); c.setReadTimeout(3500);
        c.setUseCaches(false);
        c.setRequestProperty("Cache-Control", "no-cache");
        c.setRequestProperty("Connection", "close");
        c.setRequestProperty("X-SatLink-PIN", normalizePin(pin));
        InputStream is = new BufferedInputStream(c.getInputStream(), 1024 * 32);
        Bitmap b = BitmapFactory.decodeStream(is); is.close(); return b;
    }

    public static String uploadFile(String url, String pin, ContentResolver resolver, Uri uri, String filename) throws Exception {
        String boundary = "----SatLinkRemotePRO" + System.currentTimeMillis();
        HttpURLConnection c = (HttpURLConnection)new URL(withPin(url, pin)).openConnection();
        c.setRequestMethod("POST"); c.setConnectTimeout(12000); c.setReadTimeout(240000);
        c.setRequestProperty("X-SatLink-PIN", normalizePin(pin));
        c.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        c.setRequestProperty("Connection", "close");
        c.setDoOutput(true);
        // مهم للملفات الكبيرة: بدون هذا Android قد يحاول تخزين الملف بالذاكرة قبل الإرسال.
        c.setChunkedStreamingMode(1024 * 128);
        OutputStream out = new BufferedOutputStream(c.getOutputStream(), 1024 * 128);
        write(out, "--" + boundary + "\r\n");
        String safeName = safeMultipartFilename(filename);
        String encodedName = URLEncoder.encode(filename == null ? "file.bin" : filename, "UTF-8").replace("+", "%20");
        write(out, "Content-Disposition: form-data; name=\"file\"; filename=\"" + safeName + "\"; filename*=UTF-8''" + encodedName + "\r\n");
        write(out, "Content-Type: application/octet-stream\r\n\r\n");
        InputStream in = resolver.openInputStream(uri);
        if (in == null) throw new IOException("تعذر فتح الملف");
        byte[] buf = new byte[1024 * 128]; int n;
        while ((n = in.read(buf)) != -1) {
            out.write(buf, 0, n);
        }
        in.close();
        write(out, "\r\n--" + boundary + "--\r\n");
        out.flush(); out.close();
        return readResponse(c);
    }


    public static String uploadFileRaw(String url, String pin, ContentResolver resolver, Uri uri, String filename) throws Exception {
        String encodedName = URLEncoder.encode(filename == null ? "file.bin" : filename, "UTF-8").replace("+", "%20");
        String full = url;
        if (full.contains("?")) full += "&filename=" + encodedName;
        else full += "?filename=" + encodedName;
        HttpURLConnection c = (HttpURLConnection)new URL(withPin(full, pin)).openConnection();
        c.setRequestMethod("POST");
        c.setConnectTimeout(12000);
        c.setReadTimeout(240000);
        c.setRequestProperty("X-SatLink-PIN", normalizePin(pin));
        c.setRequestProperty("Content-Type", "application/octet-stream");
        c.setRequestProperty("Connection", "close");
        c.setDoOutput(true);
        c.setChunkedStreamingMode(1024 * 128);
        OutputStream out = new BufferedOutputStream(c.getOutputStream(), 1024 * 128);
        InputStream in = resolver.openInputStream(uri);
        if (in == null) throw new IOException("تعذر فتح الملف");
        byte[] buf = new byte[1024 * 128];
        int n;
        while ((n = in.read(buf)) != -1) out.write(buf, 0, n);
        in.close();
        out.flush();
        out.close();
        return readResponse(c);
    }


    static String safeMultipartFilename(String name) {
        if (name == null || name.trim().length() == 0) return "file.bin";
        String n = name.replace("\\", "_").replace("/", "_").replace("\"", "_").replace("\r", "_").replace("\n", "_");
        if (n.length() > 180) n = n.substring(0, 180);
        return n;
    }

    static void write(OutputStream out, String s) throws IOException { out.write(s.getBytes("UTF-8")); }

    public static void downloadToUri(String url, String pin, ContentResolver resolver, Uri outUri) throws Exception {
        HttpURLConnection c = (HttpURLConnection)new URL(withPin(url, pin)).openConnection();
        c.setRequestMethod("GET"); c.setConnectTimeout(7000); c.setReadTimeout(120000);
        c.setRequestProperty("X-SatLink-PIN", normalizePin(pin));
        if (c.getResponseCode() >= 400) throw new IOException(readResponse(c));
        InputStream in = new BufferedInputStream(c.getInputStream());
        OutputStream out = resolver.openOutputStream(outUri);
        if (out == null) throw new IOException("تعذر إنشاء ملف الحفظ");
        byte[] buf = new byte[1024 * 128]; int n;
        while ((n = in.read(buf)) != -1) {
            out.write(buf, 0, n);
        }
        out.flush(); out.close(); in.close();
    }

    public static String getTextWithToken(String url, String token) throws Exception {
        HttpURLConnection c = (HttpURLConnection)new URL(url).openConnection();
        c.setRequestMethod("GET"); c.setConnectTimeout(5000); c.setReadTimeout(10000);
        c.setRequestProperty("X-SatLink-Token", token == null ? "" : token.trim());
        return readResponse(c);
    }

}
