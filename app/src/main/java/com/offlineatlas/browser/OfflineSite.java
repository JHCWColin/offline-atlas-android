package com.offlineatlas.browser;

import android.content.Context;
import android.net.Uri;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

final class OfflineSite {
    final String id, title, subtitle, description, color, entryUrl, capturedAt;
    final int port;
    final Map<String, Resource> exact = new HashMap<>(), paths = new HashMap<>();
    final Set<String> hosts = new HashSet<>();
    final Context context;
    String fallback;
    static final class Resource {
        String path, mime; int status;
        Resource(JSONObject o) throws JSONException {
            path=o.getString("path"); mime=o.optString("contentType","application/octet-stream");
            status=o.optInt("status",200);
        }
    }
    OfflineSite(Context c, JSONObject card) throws Exception {
        context=c; id=card.getString("id"); title=card.getString("title");
        subtitle=card.getString("subtitle"); description=card.getString("description");
        color=card.getString("color"); port=card.getInt("port");
        JSONObject manifest=new JSONObject(read(c.getAssets().open("sites/"+id+"/manifest.json")));
        entryUrl=manifest.getString("entryUrl"); capturedAt=manifest.optString("capturedAt", "2026-10-31");
        hosts.add(Uri.parse(entryUrl).getHost());
        JSONArray aliases=manifest.optJSONArray("hostAliases");
        if(aliases!=null) for(int i=0;i<aliases.length();i++) hosts.add(aliases.getString(i));
        JSONArray entries=manifest.getJSONArray("entries");
        for(int i=0;i<entries.length();i++) {
            JSONObject o=entries.getJSONObject(i); Resource r=new Resource(o);
            Uri u=Uri.parse(o.getString("url"));
            exact.put(normalize(u),r);
            // Queries in the snapshot may encode data. Keep exact lookup first.
            paths.putIfAbsent(withoutQuery(u),r);
        }
        fallback=manifest.optString("spaFallback",null);
    }
    static String read(InputStream in) throws IOException {
        try(InputStream source=in; ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] b=new byte[16384]; int n; while((n=source.read(b))!=-1) out.write(b,0,n);
            return out.toString("UTF-8");
        }
    }
    static String normalize(Uri u) { return u.buildUpon().fragment(null).build().toString(); }
    static String withoutQuery(Uri u) { return u.buildUpon().clearQuery().fragment(null).build().toString(); }
    Resource resolve(String url, boolean document) {
        Uri u=Uri.parse(url); Resource r=exact.get(normalize(u));
        if(r==null) r=paths.get(withoutQuery(u));
        if(r==null && hosts.contains(u.getHost())) {
            for(String host:hosts) {
                Uri alias=u.buildUpon().authority(host).build();
                r=exact.get(normalize(alias)); if(r==null) r=paths.get(withoutQuery(alias));
                if(r!=null) break;
            }
        }
        if(r==null && fallback!=null && document && hosts.contains(u.getHost()) && !u.getPath().startsWith("/api/")) {
            try {r=new Resource(new JSONObject().put("path",fallback).put("contentType","text/html; charset=utf-8"));}
            catch(JSONException ignored) { }
        }
        return r;
    }
    String localEntry() { return localUrl(entryUrl); }
    String localUrl(String remote) {
        Uri u=Uri.parse(remote);
        return "http://127.0.0.1:"+port+(u.getEncodedPath().isEmpty()?"/":u.getEncodedPath())+
            (u.getEncodedQuery()==null?"":"?"+u.getEncodedQuery())+(u.getEncodedFragment()==null?"":"#"+u.getEncodedFragment());
    }
    String originalUrl(String target) {
        Uri u=Uri.parse(target);
        String p=u.getEncodedPath();
        if(p.startsWith("/_remote/")) return p.substring(9).replaceFirst("/","://")+(u.getEncodedQuery()==null?"":"?"+u.getEncodedQuery());
        return Uri.parse(entryUrl).buildUpon().encodedPath(p).encodedQuery(u.getEncodedQuery()).fragment(null).build().toString();
    }
    InputStream open(Resource r) throws IOException { return context.getAssets().open("sites/"+id+"/"+r.path); }
}
