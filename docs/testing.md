# 离线验证

## 静态资源完整性

```powershell
python tools/verify_offline.py --strict --output docs/offline-verification.json
```

校验器检查每份 `sites/<id>/manifest.json` 的 URL 映射、文件存在性、目录边界和 SHA-256。它还扫描 HTML 的资源属性、CSS `url()` / `@import`、JavaScript 静态 import，并单独列出导航外链、元数据链接和 JavaScript 字符串候选。

构建后可再加 `--apk <APK路径>`，逐项校验 APK 内 `assets/sites/` 中的字节与源清单 SHA-256 一致，避免仅源码齐全但打包漏项。

`--strict` 将明确的运行资源遗漏视为失败。导航外链及 JS 字符串候选不会自动判为缺失运行依赖：其中可能包含文档链接、用户分享地址、正则表达式、拼接 URL 和未使用的上游功能，需结合网站范围和设备实际请求判断。静态分析不能证明所有动态行为完整，应继续执行下面的无网络交互验证。

## Android 8.1 环境

本次工作环境使用：

- Android Emulator，AOSP API 27 / Android 8.1，`default;x86_64` revision 1。
- AVD `offline-api27`，1280 × 800，160 dpi，2 GB 内存，软件 GPU，无窗口运行。
- JDK 21.0.9：`D:\AndroidStudio\jbr`。
- SDK：`D:\AndroidStudioInstall`。
- 原厂 Android System WebView：`com.android.webview 61.0.3163.98`。

本机 JBR 21 启动 Gradle 8.9 daemon 时，Windows 默认短路径临时目录会触发 `UnixDomainSockets.connect0: Invalid argument: connect`。将临时目录属性通过 `JAVA_TOOL_OPTIONS` 传给主进程及其 daemon 后可继续构建：

```powershell
$env:JAVA_HOME='D:\AndroidStudio\jbr'
$env:JAVA_TOOL_OPTIONS='-Djdk.net.unixdomain.tmpdir=C:/Windows/Temp -Djava.io.tmpdir=C:/Windows/Temp'
```

这是一项本机构建环境绕过方式，不会写入 APK 或改变离线网页。若其他电脑无此异常，无需设置。

创建与启动示例（SDK、JDK 路径可按本机修改）：

```powershell
$env:JAVA_HOME='D:\AndroidStudio\jbr'
$env:ANDROID_HOME='D:\AndroidStudioInstall'
& "$env:ANDROID_HOME\emulator\emulator.exe" -avd offline-api27 -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect -skin 1280x800 -memory 2048 -no-snapshot
adb wait-for-device
adb shell getprop ro.build.version.release
adb shell dumpsys webviewupdate
```

启动和安装后，必须禁用网络再清空应用数据做首次启动，以排除在线缓存：

```powershell
adb shell svc wifi disable
adb shell svc data disable
# 如系统允许，再打开飞行模式，并核实 connectivity 状态。
adb shell settings put global airplane_mode_on 1
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true
adb shell dumpsys connectivity
```

AOSP 模拟器首次广播飞行模式若遇权限限制，可先 `adb root` 并 `adb wait-for-device` 再广播；实体设备不要求也不建议为此修改系统。此次 AOSP 模拟器已设置飞行模式为 1、关闭 Wi-Fi 和移动数据，`dumpsys connectivity` 显示 `Active default network: none`。

APK 内 URL 拦截还应保证未镜像的远程资源不会回退到互联网，未收录链接应显示明确提示。飞行模式是设备验收条件，应用内断网设计仍需代码审计与缺失请求日志一起检查。

## 交互检查

1. 清除应用数据后首次启动，确认入口能选择两站，横屏且系统状态栏/导航栏隐藏。
2. SOCPK：逐个打开芯片榜单、图表、分类页；确认图表、说明、字体、图片完整；执行搜索、筛选、排序，展开芯片详情；检查不同芯片及图表的数据变化。
3. ModelDial：确认排行榜载入，执行排序和模型选择，切换雷达/表格与中英文，检查品牌图、模型参数、历史/参考 JSON 的页面实际使用部分。
4. 两站分别验证后退、前进、刷新、页面首页、入口、缩放与查找等容器控制。
5. 测试系统 WebView 模式，记录其真实版本和实际失败行为；现代引擎模式需单独验证，不能用现代引擎成功代替旧 WebView 成功。
6. 检查应用日志中的缺失 URL、JavaScript 异常及致命错误，对照资源清单补齐实际依赖，再重复受影响步骤。
7. 停止进程后再次打开，保持网络关闭。保存入口、两个站点和交互后的截图，并记录 APK SHA-256、包名和版本。

用户未提供实体设备；模拟器验收可说明 Android 8.1 API 兼容与该虚拟硬件上的显示行为，无法代替目标设备 GPU、内存、屏幕尺寸与厂商 WebView 的实机测试。

## 2026-10-31 验收结果

正式 APK：`OfflineAtlas-1.0.0-android8.1-universal.apk`，245,609,787 字节，SHA-256 `a591f10440d678bae5211a2deebc9187313093359401868371d2cb7686192701`。独立 RSA4096 签名，APK v2 签名校验通过；支持 ARMv7、ARM64、x86_64，minSdk 27。设备运行验收使用同一 Java、内核和网站资源的前一构建（SHA-256 `4403d2f9a38e4793f1c8e5aa165ab35cd3328a7943de466a72e4d77f1b242bd7`），最终构建只调整入口的一句说明文案。最终 APK 全部 296 项网站资源的 SHA-256 与原始抓取字节一致，见 `docs/apk-verification.json`。

API27 / Android 8.1 模拟器在飞行模式且 `Active default network: none` 下，清数据首次启动成功。最终全屏布局覆盖 1280×800，已去掉系统栏留白。默认 GeckoView 140 下，SOCPK 主页、CPU 曲线、INT/FP 切换及芯片筛选显示正常；ModelDial 榜单数据、品牌图、维度/排序、中英切换与图表显示正常。已检查容器返回/前进、刷新/首页、查找、收藏和全屏阅读入口。代表性截图位于 `qa/android-*.png`。验收日志未发现 `OfflineMissing` 或应用崩溃；Gecko 自身离线后台 Remote Settings 报 NetworkError，未影响本地网页运行，原始日志保留在 `qa/android-logcat.txt`。

真实触屏事件通过模拟器 `adb emu event mouse` 注入后，网页点击和上下滑动正常。`adb shell input swipe` 在该旧系统与软件 GPU 配置下偶尔把合成滑动识别为长按并进入文字选择；重新启动进程并改用真实触屏事件后正常，不属于已证明的应用触摸故障。

系统 WebView 实际版本 `61.0.3163.98`，运行 SOCPK 原始 `index-BgBY0hhf.js` 报 `Uncaught SyntaxError: Unexpected token ?` 并黑屏，证明原厂内核不满足现代网页脚本要求。系统内核选项保留供更新版 WebView 尝试，正式默认使用内置 Gecko。旧内核提示截图为 `qa/android-system-webview-warning.png`。

桌面依赖覆盖补验：SOCPK 全部14组图表、157个芯片详情，ModelDial六个维度、图表、搜索及双语都通过，仅从manifest取资源，无在线回退。真实Firefox扩展加不可用远端代理的测试也通过跨域JSON与图片重定向。Android Lint 为0错误、3个预期提示（强制横屏、必需JavaScript与中文UI文本）；GitHub Actions也已完成构建与严格快照校验。
