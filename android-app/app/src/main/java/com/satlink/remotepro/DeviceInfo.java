package com.satlink.remotepro;

public class DeviceInfo {
    public String id;
    public String name;
    public String ip;
    public int port;
    public String version;
    public boolean viaRelay = false;
    public String relayUrl = "";

    public DeviceInfo(String id, String name, String ip, int port, String version) {
        this.id = id; this.name = name; this.ip = ip; this.port = port; this.version = version;
    }

    public DeviceInfo(String id, String name, String ip, int port, String version, boolean viaRelay, String relayUrl) {
        this.id = id; this.name = name; this.ip = ip; this.port = port; this.version = version;
        this.viaRelay = viaRelay;
        this.relayUrl = relayUrl == null ? "" : relayUrl;
    }

    public String baseUrl() {
        if (viaRelay) {
            String r = relayUrl == null ? "" : relayUrl.trim();
            while (r.endsWith("/")) r = r.substring(0, r.length()-1);
            return r + "/" + id;
        }
        return "http://" + ip + ":" + port;
    }

    public String displayAddress() {
        if (viaRelay) return "Relay: " + relayUrl;
        return ip + ":" + port;
    }
}
