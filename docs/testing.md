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
