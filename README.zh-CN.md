<div align="center">

# 🛡️ Claude Shield (克劳德安全盾)

### 基于 Claude Code 泄露源码风控逻辑的隐私审计与防封硬化 Skill

[![License](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-0078D6)](README.zh-CN.md)
[![Schema](https://img.shields.io/badge/schema-v6.0-5391FE)](scripts/collect_windows_network.ps1)
[![Codex](https://img.shields.io/badge/Codex-skill-111111)](SKILL.md)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-D97757)](SKILL.md)

[English](README.md) · [Skill 指令](SKILL.md) · [快速开始](#-30-秒快速开始) · [一键修复脚本](#运行一键安全修复脚本)

> *"最安全的伪装，就是不伪装。用最干净的网络底层隔离，对抗最严厉的 AI 风控审核。"*

**别让 `userID` 设备指纹、`DISABLE_TELEMETRY` 缺失、IPv6/DNS 静默泄漏与 429 限流触顶，毁掉你的 Claude 账号。**
*拒绝危险的指纹伪造与防关联浏览器，用最干净的 TUN / DNS / 遥测隔离建立 100% 合规安全的系统网络环境。*

</div>

> [!IMPORTANT]
> 💡 **为什么你的 Claude 账号屡屡封号？—— 拆解 51 万行 Leaked 源码的 5 大风控判定维度**
> 
> 封号是风控系统的**多维综合判定**，5 大引发封号的核心因素按风险严重程度排序如下：
> 1. 🚨 **多设备共享账号 (极高危 - Risk: Critical)**：源码逻辑显示客户端会在 `~/.claude.json` 中自动生成唯一设备特征码 (`userID` / `deviceId`)。同一账号在短期内出现在多个 Device ID 上，伴随着异地出口 IP 漂移、操作系统 (Windows vs macOS) 或时区剧烈变化，直接触发系统“共享/买卖账号”自动封禁。
> 2. ⚡ **429 速率违规触顶 (高危 - Risk: High)**：后端按 `account_uuid` + `subscription_type` (Pro/Team) + `rate_limit_tier` 进行聚合监控。高频密集发送长 Context 请求将先触发 HTTP 429 配额拦截，若持续触顶，限流关卡会逐步升级，最终导致全站封禁。
> 3. 🕵️ **假工具注入与反蒸馏检测 (高危 - Risk: High)**：源码内置 `tengu_anti_distill_fake_tool_injection` 标记，当怀疑流量被用于训练竞品模型或通过中间人代理抓包时，服务端会在 System Prompt 中静默注入虚假工具定义。若中转或自动化脚本误触发假工具调用，将被直接打上蒸馏标签。
> 4. 🤖 **CI 自动化滥用 (中危 - Risk: Medium)**：检测无头 (Headless) 环境、非交互式 Shell、CI/CD 跑批环境变量以及 Token 消耗速度过快的组合特征。
> 5. 🛠️ **客户端改包与指纹不一致 (中危 - Risk: Medium)**：客户端版本指纹校验失败、User-Agent 格式异常或被第三方防检测浏览器改写。
> 
> *本项目通过只读诊断与最小化硬化，帮助你消除真实的物理网络泄漏与配置矛盾，不用于绕过人机验证或违反平台服务条款。*

> [!CAUTION]
> 💔 **大陆 Claude 用户三大真实血泪痛点**：
> 1. 💸 **刚充了 Pro / Team 昂贵月费**：正常对话不到三天就被无预警“无情封号” (*Your account has been suspended*)，即使发送申诉邮件也只能收到机器人自动回复，资金与历史对话数据双双丢失。
> 2. 🌐 **以为代理节点显示绿色就万事大吉**：殊不知物理网卡的直连 DNS 解析、WebRTC 本地与公网 Candidate 候选地址、或未禁用的 IPv6 旁路暗度陈仓暴露了国内 ISP 物理宽带身份，导致 IP 信誉降级与风控标记。
> 3. ⚡ **终端用 Claude Code 灵感正涌现，频繁触发 429 限流**：由于未配置 `DISABLE_TELEMETRY=1`，遥测文件与 `~/.claude.json` 绑定的固定 Device ID 不断向服务端上报本地轨迹，最终触发连坐打入小黑屋。

### 🛡️ 为什么你需要 Claude Shield？

| 传统“裸奔”或“指纹伪装”环境 ❌ | Claude Shield 纯净隔离环境 ✅ |
| :--- | :--- |
| **设备指纹**：`~/.claude.json` 长期暴露真实的唯一 ID | **设备指纹**：一键抹除重置，甚至可随时隔离备份 |
| **遥测上传**：后台静默上传全量操作与 429 频控报错 | **遥测上传**：注入 `DISABLE_TELEMETRY=1` 彻底斩断上报 |
| **DNS/IPv6**：代理显示正常，但物理网卡悄悄直连暴露位置 | **DNS/IPv6**：一键禁用物理 IPv6，全面阻断 WebRTC 泄漏 |
| **对抗思路**：使用防检测浏览器伪造 UA、硬件，容易被识别 | **对抗思路**：不加掩饰的真实系统，只做最底层的核心网络隔离 |

## ⚡ 核心能力矩阵

- 🔍 **全链路防封体检 (Deep Audit)**
  不仅看代理软件 (Clash/Mihomo/Sing-Box) 的规则栈，更穿透物理网卡，揪出隐藏的 IPv6 旁路、DNS 污染与 WebRTC 本地真实 IP 泄漏。
- 🛡️ **Claude 专属环境硬化 (Zero-Trace Remediation)**
  针对泄露源码的靶向修复。一键静默注入 `DISABLE_TELEMETRY=1` 斩断遥测上报，安全重置 `~/.claude.json` 高危设备指纹，从底层规避 429 连坐限流。
- 🤖 **AI Agent 原生赋能 (AI-Native Integration)**
  专为 Codex、Cursor、Windsurf 与 VS Code 设计的跨平台诊断架构。让大模型直接读取你的本地底层网络报告，化身你的专属高级网络安全专家。
## 🚀 30 秒快速开始

### 1. 原生终端独立运行（推荐：零依赖，账号不可用时也可诊断）

直接在系统的终端中运行，支持只读诊断与一键安全硬化：

```powershell
# 1. 克隆仓库
git clone https://github.com/AschoofAlpha/claude-shield.git

# 2. 运行只读诊断 (Windows)
pwsh -NoProfile -File .\claude-shield\scripts\collect_windows_network.ps1

# 2. 运行只读诊断 (macOS / Linux)
bash ./claude-shield/scripts/collect_posix_network.sh

# 3. 运行一键安全硬化与防封修复 (Windows)
pwsh -NoProfile -File .\claude-shield\scripts\remediate_windows_network.ps1
```

### 2. AI Agent 助手集成 (Codex / Cursor / Windsurf / VS Code)

如果你希望 AI 编程助手读取本地诊断报告并自动给出分析建议：

- **Codex**：
  ```powershell
  New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
  git clone https://github.com/AschoofAlpha/claude-shield.git "$HOME/.codex/skills/claude-shield"
  ```
  在对话中使用 `$claude-shield` 调用。

- **Cursor / Windsurf / VS Code (Agent Skills 兼容宿主)**：
  将仓库克隆或作为 Git Submodule 放入项目的 `.agent/skills/claude-shield` 或个人 Agent 目录，保留 `SKILL.md` 即可。

- **其他 LLM 宿主**：
  直接加载 `SKILL.md` 作为系统 Prompt 指令，并将脚本输出的 JSON 粘贴给 LLM 诊断。

## 运行只读采集器

在 Skill 目录中执行：

```powershell
pwsh -NoProfile -File .\scripts\collect_windows_network.ps1
```

也兼容 Windows PowerShell 5.1：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\collect_windows_network.ps1
```

采集器读取本地 Windows 和浏览器状态；条件允许时，通过 Mihomo HTTP 控制器或命名管道只读获取实际策略选择，并输出 JSON。公开结果前必须遮盖用户名、节点名、地址及其他标识符。

## 运行本地浏览器探针

在日常使用的 Chrome 配置中打开 [`assets/browser-audit.html`](assets/browser-audit.html)，选择简体中文或 English，点击 **开始检测**，然后在 Edge 中重复。页面没有外部依赖，也不会修改任何浏览器值；它会显示启发式评分、分类图表、优先问题和本地建议。选择的语言也会应用到 LLM 摘要和 PNG 图片报告。启用 WebRTC 检查时，它会向 Google 公共 STUN 服务器发送一次发现请求，结果只保留在当前页面。

屏幕会显示原始 ICE 地址，供本地比对；使用 **Copy report for LLM**、**Download redacted JSON** 或 **Download PNG report** 分享时，地址会自动替换为分类标签。把复制的报告粘贴到加载此 Skill 的 Codex、Claude Code 或其他 LLM，即可获得证据表和建议。评分不能预测 Claude 是否放行；该探针也不能判断公网 IP、DNS 解析器归属或真实 Accept-Language 请求头，因此仍须保留实时网络测试。

## 工作流程

1. 采集只读本地快照。
2. 在日常使用的 Chrome 和 Edge 配置中分别运行内置浏览器探针。
3. 分别实测 DNS、公网 IP、IPv4/IPv6、Accept-Language 与检测报告。
4. 将证据标记为 `已验证`、`推断` 或 `需要人工检查`。
5. 区分 `必须修复`、`可选一致性` 和 `保持不动`。
6. 每次只执行一项已获同意的修改，然后重新测试。

## 明确不提供

- 不伪造 Canvas、WebGL、UA、语言、时区或 WebRTC 指纹。
- 不隐藏自动化，不绕过反机器人检测或验证码，不提供多账号工具。
- 不伪造身份、居住地、账单、税务或支付信息。
- 不盲目复制第三方 Mihomo 配置或反检测浏览器代码。
- 不承诺任何配置能够阻止账号审核或封禁。

## 兼容性

| 宿主 | 调用方式 | 状态 |
| --- | --- | --- |
| Codex | `$claude-shield` | 支持 |
| Agent Skills 兼容宿主 | 按宿主规则 | 目录结构兼容 |
| 其他本地 LLM | 加载 `SKILL.md` 与采集器 JSON | 手动回退 |
| PowerShell | 7.x / Windows PowerShell 5.1 | 已自检 |

## 参与改进

发现误判或不支持的 Clash Verge 布局时，可提交 Issue，并附上已脱敏的采集结果和实际测试的浏览器/配置。不要发布订阅地址、凭据、完整 IP 或账号数据。

如果它帮你发现了真实泄漏，或者避免了一次破坏性的“指纹修复”，欢迎点一个 ⭐。

## 许可证

[MIT](LICENSE) © 2026 AschoofAlpha
