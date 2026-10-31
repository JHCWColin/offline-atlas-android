# 离线网页馆 / Offline Atlas

适用于 **Android 8.1（API 27）及以上**的横屏全屏离线网页应用。入口可选择 SOCPK 与 ModelDial，支持返回、前进、刷新、页面首页、文字缩放、页内查找、单页收藏、隐藏工具栏。

**[下载正式 APK 与校验文件](https://github.com/JHCWColin/offline-atlas-android/releases/tag/v1.0.0)**（通用版约 246 MB，首次启动无需联网）。

## 收录范围

2026-10-31 快照：

| 网站 | 离线内容 | 资源 |
| --- | --- | --- |
| [SOCPK](https://www.socpk.com/) | 全部 14 组公开图表、157 个芯片数据及列表、所需图片与脚本、页面配置与 API 数据 | 190 项，22.81 MB |
| [ModelDial](https://modeldial.com/radar) | 中文/英文排行榜、雷达/表格交互、维度筛选及必需数据、品牌图片、字体和脚本 | 106 项，13.28 MB |

ModelDial 的其他详情页、登录、外站社交及视频不属于快照。SOCPK 的 Bilibili 外链录像未打包（80 个链接，已知时长约 688 小时）；外链与不可用内容的审计见 `sites/socpk/external-audit.json`。未收录链接明确显示离线提示，**不会在线回退**。这是固定时点快照，不自动更新榜单。

## 原网页代码保持不变

`sites/<id>/files/` 保存源站响应的原始 HTML、JS、CSS、JSON、字体和图片字节。每项资源在 `manifest.json` 中保存原 URL、相对路径、MIME、SHA-256 与 HTTP 状态。应用只在容器层提供 URL 映射，不改写站点文件。

应用在设备 `127.0.0.1` 上启动只读服务器（18081/18082），保持站点路径与查询参数。内置 WebExtension 将绝对在线资源 URL 重定向到本地快照；未命中时返回 404，不访问互联网。`INTERNET` 权限用于访问设备自身的回环服务器，不代表需要网络。

两个站点当前脚本包含旧系统 WebView 不支持的语法。Android 8.1 原厂 WebView 61 不能完整运行，默认采用 APK 内置 **GeckoView 140**。馆藏页可以切换系统 WebView 进行兼容尝试，原厂旧内核会提示升级/切换。APK 包含 ARMv7、ARM64 和 x86_64，体积主要来自内置内核。

## 构建

需要 JDK 17/21、Android SDK Platform 35、可联网下载依赖。已包含 Gradle 8.9 Wrapper。

```powershell
# local.properties 写入 sdk.dir，或设置 ANDROID_HOME
.\gradlew.bat assembleDebug
```

```bash
./gradlew assembleRelease
```

正式签名：设置 `ATLAS_KEYSTORE`、`ATLAS_STORE_PASSWORD`、`ATLAS_KEY_PASSWORD`，别名为 `offline-atlas`。本地默认路径 `signing/release.jks`，默认密码仅作开发示例：`offline-atlas-2026`；私钥不进入仓库。没有正式私钥时构建使用开发签名，不能覆盖已发布正式版本。Windows 若 JBR 报 `Unable to establish loopback connection`，将 `JAVA_TOOL_OPTIONS` 设置为 `-Djava.io.tmpdir=C:/Windows/Temp -Djdk.net.unixdomain.tmpdir=C:/Windows/Temp` 后再构建。

## 更新快照与验证

```powershell
python tools/mirror_socpk.py
python tools/mirror_modeldial.py
python tools/verify_offline.py --strict --output docs/offline-verification.json
```

抓取脚本只抓公开资源，不包含登录或付费内容。命令参数以各脚本 `--help` 为准。具体设备验收流程见 [docs/testing.md](docs/testing.md)。`qa/` 保存运行截图和交互报告。

新增网站：添加 `sites/<id>/manifest.json` 与原始资源，再在 `app/src/main/assets/catalog.json` 添加入口和独立回环端口。服务器和入口 UI 从清单加载，不需改写原站。新站仍应执行资源审计和离线交互验收，尤其是绝对 URL 的域名映射。

## 来源与许可

Android 容器与工具为 MIT 许可。网站内容与品牌版权归原作者，**不受容器 MIT 许可覆盖**。SOCPK 未找到可确认的网站开源许可；此项目为公开内容的离线快照与兼容演示，保留来源与版权，不宣称网站开源。ModelDial 官方组织目前只公开开源计划，未找到站点完整源代码；其公开数据标注 CC BY 4.0，详见 `sites/modeldial/NOTICE.md`。原始快照未改动。

GeckoView 为 Mozilla MPL 2.0，版本 `140.0.20250707120347`，未修改库；对应源代码：[Mozilla revision 65c832029a47e8865556ad3f4dbfe690863f637c](https://hg.mozilla.org/releases/mozilla-release/rev/65c832029a47e8865556ad3f4dbfe690863f637c)。依赖许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
