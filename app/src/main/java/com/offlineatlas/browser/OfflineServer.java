package com.offlineatlas.browser;

import android.net.Uri;
import android.util.Log;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Loopback-only, read-only asset server. There is deliberately no network fallback. */
final class OfflineServer implements Closeable {
    final OfflineSite site;
    private ServerSocket server;
    private final ExecutorService pool=Executors.newCachedThreadPool();
    OfflineServer(OfflineSite site) throws IOException {
        this.site=site;
        server=new ServerSocket(); server.setReuseAddress(true);
        server.bind(new InetSocketAddress(InetAddress.getByName("127.0.0.1"),site.port));
        pool.execute(()->{while(!server.isClosed()) try { Socket s=server.accept(); pool.execute(()->serve(s)); } catch(IOException e) { if(!server.isClosed()) Log.e("OfflineServer","accept",e); }});
    }
    private void serve(Socket s) {
        try(Socket socket=s) {
            socket.setSoTimeout(15000);
            BufferedReader in=new BufferedReader(new InputStreamReader(socket.getInputStream(),StandardCharsets.US_ASCII));
            String line=in.readLine(); if(line==null) return;
            String[] start=line.split(" ",3); if(start.length<2) return;
            String method=start[0], target=start[1]; Map<String,String> headers=new HashMap<>();
            while((line=in.readLine())!=null && !line.isEmpty()) {int colon=line.indexOf(':'); if(colon>0) headers.put(line.substring(0,colon).toLowerCase(Locale.ROOT),line.substring(colon+1).trim());}
            String remote=site.originalUrl(target);
            if("OPTIONS".equals(method)) {respond(socket,204,"text/plain",new byte[0],false); return;}
            // Visits are local. Analytics endpoints receive no personal data and never leave the device.
            if(!"GET".equals(method) && !"HEAD".equals(method)) {
                if(Uri.parse(remote).getPath().equals("/api/metrics/page-view")) respond(socket,200,"application/json","{}".getBytes(StandardCharsets.UTF_8),false);
                else respond(socket,405,"text/plain","Read-only offline snapshot".getBytes(StandardCharsets.UTF_8),false);
                return;
            }
            boolean document=headers.getOrDefault("accept","").contains("text/html");
            OfflineSite.Resource r=site.resolve(remote,document);
            if(r==null) {
                Log.w("OfflineMissing",site.id+" "+remote);
                String accept=headers.getOrDefault("accept","");
                String msg=document?missingPage(remote):"Offline resource not captured: "+remote;
                respond(socket,404,document?"text/html; charset=utf-8":"text/plain; charset=utf-8",msg.getBytes(StandardCharsets.UTF_8),"HEAD".equals(method));
                return;
            }
            byte[] bytes;
            try(InputStream asset=site.open(r);ByteArrayOutputStream out=new ByteArrayOutputStream()) {
                byte[] b=new byte[65536]; int n; while((n=asset.read(b))!=-1) out.write(b,0,n); bytes=out.toByteArray();
            }
            respond(socket,r.status,r.mime,bytes,"HEAD".equals(method));
        } catch(Exception e) {Log.w("OfflineServer","Request failed",e);}
    }
    private static String escape(String s) { return s.replace("&","&amp;").replace("<","&lt;").replace("\"","&quot;"); }
    static String missingPage(String url) {
        return "<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><body style='background:#101827;color:#edf5ff;font:20px sans-serif;padding:8vh 8vw'><h1>此链接未收录到离线快照</h1><p>ModelDial 仅包含排行榜；外站视频、社交和登录页面需要访问原网站。</p><p style='overflow-wrap:anywhere;color:#9cbbdc'>"+escape(url)+"</p><button style='font-size:20px;padding:12px' onclick='history.back()'>返回上一页</button></body>";
    }
    private void respond(Socket s,int status,String mime,byte[] bytes,boolean head) throws IOException {
        String reason=status==200?"OK":status==204?"No Content":status==404?"Not Found":"Response";
        String h="HTTP/1.1 "+status+" "+reason+"\r\nContent-Type: "+mime+"\r\nContent-Length: "+bytes.length+"\r\nConnection: close\r\nCache-Control: no-store\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Headers: *\r\nAccess-Control-Allow-Methods: GET, HEAD, OPTIONS, POST\r\nCross-Origin-Resource-Policy: cross-origin\r\n\r\n";
        OutputStream out=s.getOutputStream(); out.write(h.getBytes(StandardCharsets.US_ASCII)); if(!head) out.write(bytes); out.flush();
    }
    @Override public void close() throws IOException {server.close(); pool.shutdownNow();}
}
