package com.offlineatlas.browser;

import android.app.*;
import android.os.*;
import android.content.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.view.*;
import android.webkit.*;
import android.widget.*;
import org.json.*;
import org.mozilla.geckoview.*;
import java.io.*;
import java.util.*;

public class MainActivity extends Activity {
    private static GeckoRuntime runtime;
    private static boolean bridgeReady;
    private final ArrayList<OfflineSite> sites=new ArrayList<>();
    private final ArrayList<OfflineServer> servers=new ArrayList<>();
    private LinearLayout root, toolbar;
    private FrameLayout content;
    private TextView address;
    private Button backButton,forwardButton;
    private ProgressBar progress;
    private GeckoView gecko;
    private GeckoSession session;
    private WebView system;
    private OfflineSite selected;
    private String currentUrl="";
    private boolean useSystem, canBack, canForward;
    private float textScale=1;
    private final int ink=Color.rgb(228,237,251), muted=Color.rgb(152,172,202), bg=Color.rgb(13,20,33);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        immersive();
        useSystem=getPreferences(0).getBoolean("system",false);
        try {
            JSONArray catalog=new JSONArray(OfflineSite.read(getAssets().open("catalog.json")));
            for(int i=0;i<catalog.length();i++) {
                OfflineSite s=new OfflineSite(this,catalog.getJSONObject(i)); sites.add(s); servers.add(new OfflineServer(s));
            }
            showLibrary();
        } catch(Exception e) { showFatal("离线资源加载失败",e.toString()); }
    }
    private void immersive() {
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY|View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_LAYOUT_STABLE|View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN|View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
    }
    @Override public void onWindowFocusChanged(boolean focused) { super.onWindowFocusChanged(focused); if(focused) immersive(); }
    private int dp(float n) {return (int)(getResources().getDisplayMetrics().density*n+.5f);}
    private TextView text(String value,float size,int color) {
        TextView t=new TextView(this); t.setText(value); t.setTextSize(size); t.setTextColor(color); return t;
    }
    private GradientDrawable shape(int color,int radius) {
        GradientDrawable g=new GradientDrawable(); g.setColor(color); g.setCornerRadius(dp(radius)); return g;
    }
    private Button button(String label,Runnable click) {
        Button b=new Button(this); b.setText(label); b.setTextSize(14); b.setTextColor(ink);
        b.setAllCaps(false); b.setMinWidth(0); b.setMinimumWidth(0); b.setMinHeight(0); b.setMinimumHeight(0);
        b.setPadding(dp(12),0,dp(12),0); b.setBackground(shape(Color.rgb(31,45,67),8));
        b.setOnClickListener(v->click.run()); return b;
    }
    private void closeBrowser() {
        if(session!=null) {session.close();session=null;}
        if(system!=null) {system.stopLoading();system.destroy();system=null;}
        gecko=null;
    }
    private void showLibrary() {
        closeBrowser(); selected=null;
        LinearLayout page=new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL); page.setBackgroundColor(bg);
        page.setPadding(dp(34),dp(22),dp(34),dp(16)); setContentView(page);
        LinearLayout top=new LinearLayout(this);top.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout title=new LinearLayout(this);title.setOrientation(LinearLayout.VERTICAL);
        TextView over=text("OFFLINE ATLAS   /   本地馆藏",12,muted); over.setLetterSpacing(.15f);title.addView(over);
        TextView heading=text("离线网页馆",30,ink); heading.setTypeface(null,Typeface.BOLD);title.addView(heading);
        top.addView(title,new LinearLayout.LayoutParams(0,-2,1));
        Button engine=button(useSystem?"内核：系统 WebView":"内核：内置 Gecko",this::chooseEngine);
        top.addView(engine,new LinearLayout.LayoutParams(-2,dp(42)));page.addView(top);
        TextView intro=text("选择一个网站，随时离线浏览。",15,muted);intro.setPadding(0,dp(8),0,dp(20));page.addView(intro);
        LinearLayout cards=new LinearLayout(this);cards.setGravity(Gravity.CENTER_VERTICAL);
        for(OfflineSite s:sites) {
            LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(24),dp(20),dp(24),dp(20));card.setBackground(shape(Color.rgb(23,35,55),16));
            TextView tag=text("●  已下载 · 可离线使用",12,Color.parseColor(s.color));card.addView(tag);
            TextView name=text(s.title,31,ink);name.setTypeface(null,Typeface.BOLD);name.setPadding(0,dp(12),0,dp(3));card.addView(name);
            card.addView(text(s.subtitle,16,ink));
            TextView desc=text(s.description,12,muted);desc.setPadding(0,dp(9),0,dp(14));card.addView(desc);
            Button open=button("进入网站  →",()->openSite(s));card.addView(open,new LinearLayout.LayoutParams(-1,dp(42)));
            card.setOnClickListener(v->openSite(s));
            LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(0,-2,1);cp.setMargins(0,0,dp(16),0);cards.addView(card,cp);
        }
        page.addView(cards,new LinearLayout.LayoutParams(-1,0,1));
        LinearLayout foot=new LinearLayout(this);foot.setGravity(Gravity.CENTER_VERTICAL);
        TextView note=text("全部内容来自设备内的快照  ·  横屏全屏  ·  v1.0.0",12,muted);foot.addView(note,new LinearLayout.LayoutParams(0,-2,1));
        Button about=button("关于与来源",this::about);foot.addView(about,new LinearLayout.LayoutParams(-2,dp(34)));page.addView(foot);
        immersive();
    }
    private void chooseEngine() {
        new AlertDialog.Builder(this).setTitle("浏览内核")
            .setSingleChoiceItems(new String[]{"内置 Gecko 140 · 推荐，兼容 Android 8.1","系统 WebView · 原厂旧版本可能无法显示"},useSystem?1:0,(d,which)->{
                useSystem=which==1;getPreferences(0).edit().putBoolean("system",useSystem).apply();d.dismiss();showLibrary();
            }).setNegativeButton("取消",null).show();
    }
    private void about() {
        new AlertDialog.Builder(this).setTitle("离线网页馆 · 1.0.0")
            .setMessage("SOCPK：极客湾手机芯片效能榜，包含公开图表、芯片与电池数据。\nModelDial：仅排行榜及必需资源，数据 CC BY 4.0，版权归原作者。\n\n网页原始 HTML / CSS / JavaScript 按原字节保存。外站视频、社交、登录及未收录页面会提示不可用。当前数据为快照，不自动更新。\n\n内置 GeckoView 140（MPL 2.0），源代码来源：hg.mozilla.org/releases/mozilla-release/rev/65c832029a47e8865556ad3f4dbfe690863f637c\n\n新增网站：添加 sites/<id>/manifest.json 和 catalog.json 条目后重新构建。")
            .setPositiveButton("知道了",null).show();
    }
    private void openSite(OfflineSite s) {
        closeBrowser();selected=s;canBack=false;canForward=false;
        root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(bg);
        toolbar=new LinearLayout(this);toolbar.setGravity(Gravity.CENTER_VERTICAL);toolbar.setPadding(dp(5),dp(3),dp(5),dp(3));
        addTool("馆藏",this::showLibrary);backButton=addTool("‹",this::goBack);forwardButton=addTool("›",this::goForward);
        addTool("刷新",this::reload);addTool("首页",()->navigate(s.localEntry()));
        address=text(s.title+" · 离线",12,ink);address.setSingleLine(true);address.setEllipsize(android.text.TextUtils.TruncateAt.MIDDLE);
        address.setPadding(dp(10),0,dp(6),0);address.setOnClickListener(v->showAddress());toolbar.addView(address,new LinearLayout.LayoutParams(0,-1,1));
        addTool("A−",()->scale(-.1f));addTool("A+",()->scale(.1f));addTool("查找",this::find);addTool("⋯",this::menu);
        root.addView(toolbar,new LinearLayout.LayoutParams(-1,dp(46)));
        progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(100);progress.setProgress(0);
        root.addView(progress,new LinearLayout.LayoutParams(-1,dp(2)));
        content=new FrameLayout(this);root.addView(content,new LinearLayout.LayoutParams(-1,0,1));setContentView(root);
        if(useSystem) openSystem(s); else openGecko(s);
    }
    private Button addTool(String t,Runnable r) {
        Button b=button(t,r);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-2,-1);p.setMargins(dp(2),0,dp(2),0);toolbar.addView(b,p);return b;
    }
    private void openGecko(OfflineSite s) {
        try {
            if(runtime==null) runtime=GeckoRuntime.create(getApplicationContext(),new GeckoRuntimeSettings.Builder()
                .javaScriptEnabled(true).remoteDebuggingEnabled(false).consoleOutput(true)
                .automaticFontSizeAdjustment(false).build());
            TextView loading=text("正在启动内置浏览内核…",20,muted);loading.setGravity(Gravity.CENTER);content.addView(loading,new FrameLayout.LayoutParams(-1,-1));
            if(bridgeReady) attachGecko(s);
            else runtime.getWebExtensionController().ensureBuiltIn("resource://android/assets/bridge/","offline-router@offlineatlas.local")
                .accept(extension->{bridgeReady=true;if(selected==s && !useSystem) attachGecko(s);},error->showFatal("离线资源路由启动失败",error.toString()));
        } catch(Exception e) {showFatal("内置内核启动失败",e.toString());}
    }
    private void attachGecko(OfflineSite s) {
        content.removeAllViews(); gecko=new GeckoView(this);
        session=new GeckoSession(new GeckoSessionSettings.Builder().usePrivateMode(false)
            .userAgentMode(GeckoSessionSettings.USER_AGENT_MODE_DESKTOP).build());
        session.setNavigationDelegate(new GeckoSession.NavigationDelegate() {
            @Override public GeckoResult<AllowOrDeny> onLoadRequest(GeckoSession se,LoadRequest request) {
                Uri uri=Uri.parse(request.uri);
                if("http".equals(uri.getScheme()) && "127.0.0.1".equals(uri.getHost())) return GeckoResult.fromValue(AllowOrDeny.ALLOW);
                if("http".equals(uri.getScheme()) || "https".equals(uri.getScheme())) {
                    String local=s.hosts.contains(uri.getHost())?s.localUrl(request.uri):"http://127.0.0.1:"+s.port+"/_remote/"+uri.getScheme()+"/"+uri.getEncodedAuthority()+uri.getEncodedPath()+(uri.getEncodedQuery()==null?"":"?"+uri.getEncodedQuery());
                    se.loadUri(local);return GeckoResult.fromValue(AllowOrDeny.DENY);
                }
                return GeckoResult.fromValue(AllowOrDeny.DENY);
            }
            @Override public void onLocationChange(GeckoSession se,String url,List<GeckoSession.PermissionDelegate.ContentPermission> permissions,Boolean hasUserGesture) { updateAddress(url); }
            @Override public void onCanGoBack(GeckoSession se,boolean value) {canBack=value;updateNavigation();}
            @Override public void onCanGoForward(GeckoSession se,boolean value) {canForward=value;updateNavigation();}
        });
        session.setProgressDelegate(new GeckoSession.ProgressDelegate() {
            @Override public void onPageStart(GeckoSession se,String url) {progress.setVisibility(View.VISIBLE);progress.setProgress(5);}
            @Override public void onProgressChange(GeckoSession se,int value) {progress.setProgress(value);}
            @Override public void onPageStop(GeckoSession se,boolean success) {progress.setVisibility(View.GONE);}
        });
        session.setContentDelegate(new GeckoSession.ContentDelegate() {
            @Override public void onFullScreen(GeckoSession se,boolean fullScreen) {toolbar.setVisibility(fullScreen?View.GONE:View.VISIBLE);}
            @Override public void onCloseRequest(GeckoSession se) {showLibrary();}
        });
        session.open(runtime);gecko.setSession(session);content.addView(gecko,new FrameLayout.LayoutParams(-1,-1));navigate(s.localEntry());
    }
    @SuppressWarnings("deprecation") private void openSystem(OfflineSite s) {
        system=new WebView(this);WebSettings settings=system.getSettings();settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);settings.setAllowContentAccess(false);settings.setSupportZoom(true);settings.setBuiltInZoomControls(true);settings.setDisplayZoomControls(false);
        settings.setUseWideViewPort(true);settings.setLoadWithOverviewMode(true);
        system.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView v,WebResourceRequest request) {
                Uri uri=request.getUrl();if("127.0.0.1".equals(uri.getHost())) return null;
                try {
                    OfflineSite.Resource r=s.resolve(uri.toString(),request.isForMainFrame());
                    if(r!=null) return new WebResourceResponse(r.mime.split(";")[0],"UTF-8",r.status,"OK",Collections.singletonMap("Access-Control-Allow-Origin","*"),s.open(r));
                    return new WebResourceResponse("text/plain","UTF-8",404,"Not Found",Collections.singletonMap("Access-Control-Allow-Origin","*"),new ByteArrayInputStream(new byte[0]));
                } catch(Exception e) {return new WebResourceResponse("text/plain","UTF-8",new ByteArrayInputStream(new byte[0]));}
            }
            @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest request) {
                Uri u=request.getUrl();if("127.0.0.1".equals(u.getHost())) return false;
                if(s.hosts.contains(u.getHost())) v.loadUrl(s.localUrl(u.toString()));
                else v.loadDataWithBaseURL(null,OfflineServer.missingPage(u.toString()),"text/html","UTF-8",null);
                return true;
            }
            @Override public void onPageFinished(WebView v,String url) {updateAddress(url);canBack=v.canGoBack();canForward=v.canGoForward();updateNavigation();}
        });
        system.setWebChromeClient(new WebChromeClient(){@Override public void onProgressChanged(WebView v,int n){progress.setProgress(n);progress.setVisibility(n==100?View.GONE:View.VISIBLE);}});
        content.addView(system,new FrameLayout.LayoutParams(-1,-1));navigate(s.localEntry());
        PackageInfoCompat.warnIfOld(this);
    }
    private void updateAddress(String url) {if(selected==null || address==null)return;currentUrl=url;address.setText(selected.title+" · "+Uri.parse(url).getPath());}
    private void updateNavigation() {backButton.setEnabled(canBack);forwardButton.setEnabled(canForward);}
    private void navigate(String url) {if(session!=null) session.loadUri(url);if(system!=null) system.loadUrl(url);}
    private void reload() {if(session!=null)session.reload();if(system!=null)system.reload();}
    private void goBack() {if(!canBack)return;if(session!=null)session.goBack();if(system!=null)system.goBack();}
    private void goForward() {if(!canForward)return;if(session!=null)session.goForward();if(system!=null)system.goForward();}
    private void scale(float delta) {textScale=Math.max(.6f,Math.min(1.8f,textScale+delta));if(runtime!=null)runtime.getSettings().setFontSizeFactor(textScale);if(system!=null)system.getSettings().setTextZoom((int)(textScale*100));}
    private void find() {
        EditText query=new EditText(this);query.setSingleLine(true);query.setHint("输入页面文字");
        new AlertDialog.Builder(this).setTitle("页面内查找").setView(query).setPositiveButton("查找",(d,w)->{
            String q=query.getText().toString();if(session!=null)session.getFinder().find(q,0);if(system!=null)system.findAllAsync(q);
        }).setNeutralButton("下一个",(d,w)->{if(session!=null)session.getFinder().find(null,0);if(system!=null)system.findNext(true);}).setNegativeButton("关闭",(d,w)->{if(session!=null)session.getFinder().clear();if(system!=null)system.clearMatches();}).show();
    }
    private void showAddress() {
        String original=selected.originalUrl(currentUrl);
        new AlertDialog.Builder(this).setTitle("当前离线页面").setMessage(original+"\n\n快照："+selected.capturedAt+"\n资源："+selected.exact.size()+" 项")
            .setPositiveButton("复制原始链接",(d,w)->((android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("URL",original))).setNegativeButton("关闭",null).show();
    }
    private void menu() {
        new AlertDialog.Builder(this).setItems(new String[]{"隐藏工具栏 / 全屏阅读","收藏当前页面","打开收藏","返回馆藏"},(d,w)->{
            if(w==0) {toolbar.setVisibility(View.GONE);Button restore=button("☰",()->{toolbar.setVisibility(View.VISIBLE);content.removeView(content.findViewWithTag("restore"));});restore.setTag("restore");FrameLayout.LayoutParams p=new FrameLayout.LayoutParams(dp(48),dp(40),Gravity.TOP|Gravity.END);content.addView(restore,p);}
            if(w==1) {getPreferences(0).edit().putString("bookmark-"+selected.id,currentUrl).apply();Toast.makeText(this,"已收藏当前页面",Toast.LENGTH_SHORT).show();}
            if(w==2) navigate(getPreferences(0).getString("bookmark-"+selected.id,selected.localEntry()));
            if(w==3) showLibrary();
        }).show();
    }
    @Override public void onBackPressed() {if(selected==null)super.onBackPressed();else if(canBack)goBack();else showLibrary();}
    @Override protected void onDestroy() {closeBrowser();for(OfflineServer s:servers)try{s.close();}catch(IOException ignored){}super.onDestroy();}
    private void showFatal(String title,String error) {new AlertDialog.Builder(this).setTitle(title).setMessage(error).setPositiveButton("关闭",(d,w)->finish()).show();}
    private static class PackageInfoCompat {
        static void warnIfOld(Activity a) {
            android.content.pm.PackageInfo info=WebView.getCurrentWebViewPackage();
            String version=info==null?"unknown":info.versionName;
            try {if(Integer.parseInt(version.split("\\.")[0])>=111)return;}catch(Exception ignored){}
            new AlertDialog.Builder(a).setTitle("系统 WebView 版本较旧").setMessage("当前版本："+version+"。这两个网站使用现代 JavaScript，可能白屏。请从馆藏切换到内置 Gecko 内核。").setPositiveButton("知道了",null).show();
        }
    }
}
