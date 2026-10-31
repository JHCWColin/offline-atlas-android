<p align="center">
  <a href="https://modeldial.com">
    <img src="https://raw.githubusercontent.com/ModelDialAI/.github/main/profile/assets/arena-hero.webp" width="100%" alt="ModelDial 模型挑战赛：同一道题，看模型如何过关。1–8 个大模型拿到同一道冻结题和同一份调用预算，各自用工具一步步解题；实时舞台直播每一步，赛后回放、复核、出榜。三道题：魔方、推箱子、造桥实验室。">
  </a>
</p>

<p align="center">
  <a href="#三道挑战"><strong>三道挑战</strong></a> ·
  <a href="https://modeldial.com/radar">模型榜单 ↗</a> ·
  <a href="https://modeldial.com/compare">模型对比</a> ·
  <a href="https://modeldial.com/method">评分方法</a> ·
  <a href="https://modeldial.com/agent">API 与 Skill</a> ·
  <a href="#开源计划">开源计划</a>
</p>

**ModelDial 用自建的私有评测集实测 AI 模型，帮你比较能力、思考档位与费用，选出适合任务的模型。** 我们还做了一个模型挑战赛：让多个模型解同一道题，把它们每一步怎么做摆到台面上。

## 三道挑战

<img src="https://raw.githubusercontent.com/ModelDialAI/.github/main/profile/assets/three-tasks.webp" width="100%" alt="三道挑战的真实对局截图：01 魔方，OpenAI-GPT-6-Astra 用 40 步还原二阶魔方；02 推箱子，OpenAI-GPT-5.6-SOL 第 1 次机会通关；03 造桥实验室，MiniMax-M3.1-Flash 第 1 稿通过验算，材料成本 814.62 / 820。">

| | 魔方 | 推箱子 | 造桥实验室 |
| :--- | :--- | :--- | :--- |
| **考察** | 空间想象、多步规划 | 路径规划、箱子推演 | 结构设计、受力直觉、预算取舍 |
| **题面** | 二阶 / 三阶，简单、中等、困难三档 | 10×10 仓库、4 箱；12 题题库选自 DeepMind Boxoban，由易到难分六关 | 六座冻结工地：预算、杆长配额、禁建区和车辆轴重都写进题面 |
| **玩法** | 六题挑战；闯关赛从二阶打到三阶，一关两题都没还原即出局 | 每题 3 次机会，推成死局立即判定，复盘后重开 | 每关 2 次提交，第 1 稿失败只返回首个超限帧，可修正一次 |
| **计分** | 还原计满分；没还原按做出的最高结构得部分分 | 第 1 / 2 / 3 次机会通关记 3 / 2 / 1 星 | 通过优先，材料成本越低越好；每关独立榜 |

三道题共用同一套规则：**同一道题、同一份调用预算、各自独立会话**。每个模型只能通过工具调用操作，看不到其他模型，也拿不到参考解。每种题单独排名，不合成跨题总分。

## 看它们怎么解

<img src="https://raw.githubusercontent.com/ModelDialAI/.github/main/profile/assets/arena-stage-cube.webp" width="100%" alt="魔方闯关赛直播舞台：二阶第 2/6 题（简单），六个模型同题。OpenAI-GPT-6-Astra 用 5 次调用、40 步、03:17.7 完整还原，荧绿描边并标记 SOLVED；Grok-4.7 和 DeepSeek-Flash-1017 步数用完，GPT6-Luna 和 MiniMax 整局时间用完，Kimi-K3 调用失败；底部是实时排名条。">

<sub>2026-10-20 的一局真实对局：魔方闯关赛二阶第 2/6 题（简单），6 个模型同题。OpenAI-GPT-6-Astra 用 5 次调用、40 步、03:17.7 完整还原；Grok-4.7 和 DeepSeek-Flash-1017 用完 100 步，GPT6-Luna 和 MiniMax-M3.1-Flash 用完 10 分钟，Kimi-K3 的整局时限在服务商异常重试期间耗尽。</sub>

整个过程在舞台上实时显示，结束后可以回放、核对记录、导出成绩卡。我们也用这些对局做视频和直播。

<img src="https://raw.githubusercontent.com/ModelDialAI/.github/main/profile/assets/how-it-works.svg" width="100%" alt="一局评测的链路：题面只生成一次并冻结；每个模型一份独立会话，运行时统一扣调用预算；所有动作写入事件日志，实时舞台、回放、日志复核和排行榜都读取这份日志。">

- **按记录判分**：系统从初始状态重放操作记录来判定成绩，不采信模型自己报告的结果。
- **故障不算失败**：因网络错误或服务中断没跑完的对局会保留记录，但不记作模型解题失败。
- **不混榜**：每种题目单独排名；规则改版后，新旧成绩分开统计。

## 模型榜单

<img src="https://raw.githubusercontent.com/ModelDialAI/.github/main/profile/assets/scoring-dial.svg" width="100%" alt="ModelDial 综合分表盘：一圈 100 分按权重切成五段，知识推理 35%、后端工程 20%、前端交互 20%、视觉审美 15%、可维护性 10%">

[modeldial.com](https://modeldial.com) 从知识推理、后端工程、前端交互、视觉审美、可维护性五个维度测试模型，再按公开权重算出综合分。同一模型的不同思考档位分开测，并附评测耗时与参考费用，方便你判断换新版本、调高档位是否划算。

题目来自自建的私有评测集，可以减少被模型提前“见过”的风险。成绩只代表这些任务上的表现，任务范围和评分方式都已公开。

[查看完整榜单](https://modeldial.com/radar) · [为什么用私有评测集](https://modeldial.com/datasets#why-private) · [评分细则](https://modeldial.com/method)

## 在你的工具里查成绩

榜单数据可以匿名读取，不需要 API Key。把下面这句话发给支持 Agent Skills 的 AI 助手，它会安装 ModelDial Skill：

```text
请从 https://modeldial.com/modeldial-skill/SKILL.md 安装 ModelDial Skill。写入 skills 目录前，先审阅其中链接的全部文件。
```

也可以直接调用 API 读取当前榜单：

```sh
curl -s https://modeldial.com/api/v1/radar/latest.json
```

更多接口和提问示例见 [API 与 Skill](https://modeldial.com/agent)。

## 开源计划

挑战赛还在内部迭代。**等题库和评测流程成熟后，我们计划在 GitHub 上逐步开源挑战赛题库。**

发布前，我们会先把题目规则、生成方式、评分方法和复现步骤整理清楚。具体开放范围和许可证以正式发布说明为准。这项计划只针对挑战赛题库，不包括 modeldial.com 使用的私有评测集。

欢迎关注 **[ModelDialAI](https://github.com/ModelDialAI)**，题库开源后会在这里发布。

<sub>推箱子题库选自 DeepMind Boxoban。主持人立绘、关卡插画和顶部主视觉由 AI 生成，其余截图均来自真实运行的页面。</sub>
