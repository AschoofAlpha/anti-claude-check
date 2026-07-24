<div align="center">

# 🛡️ Claude Shield (克劳德安全盾)

### 基于 Claude Code 泄露源码风控逻辑的隐私审计与防封硬化 Skill

[![License](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-0078D6)](README.zh-CN.md)
[![Schema](https://img.shields.io/badge/schema-v6.0-5391FE)](scripts/collect_windows_network.ps1)
[![Codex](https://img.shields.io/badge/Codex-skill-111111)](SKILL.md)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-D97757)](SKILL.md)

[English](README.md) · [Skill 指令](SKILL.md) · [快速开始](#30-秒安装) · [一键修复脚本](#运行一键安全修复脚本)

**别让 `userID` 设备指纹、`DISABLE_TELEMETRY` 缺失、IPv6/DNS 静默泄漏与 429 限流触顶，毁掉你的 Claude 账号。**
*拒绝危险的指纹伪造与防关联浏览器，用最干净的 TUN / DNS / 遥测隔离建立 100% 合规安全的系统网络环境。*

</div>

> [!IMPORTANT]
> 💡 **为什么屡屡封号？** 拆解 51 万行 leaked 源码发现，封号是**多维综合判定**：多设备共享账号(极高危) > 429限流触顶(高危) > 假工具/蒸馏检测(高危) > CI自动化滥用(中危) > 客户端改包(中危)。本项目通过只读诊断与最小化硬化，消除真实泄漏与矛盾，不用于绕过人机验证或违反服务条款。

> [!CAUTION]
> 💔 **大陆 Claude 用户三大真实血泪痛点**：
> 1. 💸 **刚充了 Pro / Team 昂贵月费**，正常用不到三天就被“无情封号” (Your account has been suspended)，连申诉邮件都石沉大海。
> 2. 🌐 **以为代理节点绿了就万事大吉**，结果被物理网卡的直连 DNS、WebRTC 候选地址或未禁用的 IPv6 旁路暗度陈仓暴露了国内 ISP 真实身份。
> 3. ⚡ **终端用 Claude Code 灵感正涌现，频繁触发 429 限流**，接着连同 `~/.claude.json` 绑定的 Device ID 与遥测缓存一起被打入小黑屋。

## 为什么需要它

代理正常不等于只有“出口 IP 正确”。DNS、WebRTC、IPv6、自动策略组或另一个浏览器仍可能走不同路径；检测网站也可能把字体、RTT、TCP/IP 系统推断或代理出口 IPv6 误判为泄漏。

`claude-shield` 把本地系统证据、Mihomo/Sing-Box 运行时状态、浏览器实测与 Claude Code 遥测整合到同一套流程中，区分真实问题与检测噪声，并只建议最小、可验证的修复。

## 能检查什么

| 层级 | 检查范围 |
| --- | --- |
| Clash Verge / Mihomo / Sing-Box | 服务模式、系统代理、TUN、`strict-route`、stack、局域网访问、运行时策略选择 |
| DNS 与路由 | Mihomo DNS、fake-IP、`any:53`、`respect-rules`、物理网卡绕行、跨网站出口 |
| IPv6 与 WebRTC | 物理 IPv6、Teredo、隧道 IPv6、ICE candidates、Chrome/Edge 策略与扩展状态 |
| 浏览器一致性 | 内置本地探针检查活动配置的语言、时区、WebGL/GPU (SwiftShader CPU渲染识别)、自动化状态、降精度硬件值 |
| Claude Code 源码级审计 | `DISABLE_TELEMETRY` 环境变量、`~/.claude.json` 设备指纹 `userID` 重置、`telemetry` 缓存监控、429 日志触顶扫描、5 大封号原因判定 |
| 多客户端与跨平台 | 支持 Windows (`pwsh`) / macOS 与 Linux (`collect_posix_network.sh`)，识别 Sing-Box、V2RayN、Xray 等客户端 |

## 30 秒安装

### Codex

```powershell
New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
git clone https://github.com/AschoofAlpha/anti-claude-check.git "$HOME/.codex/skills/claude-shield"
```

使用 `$claude-shield` 调用，或直接提出匹配的隐私审计与防封问题。

### Claude Code

```powershell
New-Item -ItemType Directory -Force "$HOME/.claude/skills" | Out-Null
git clone https://github.com/AschoofAlpha/anti-claude-check.git "$HOME/.claude/skills/claude-shield"
```

使用 `/claude-shield` 调用。

其他 Agent Skills 宿主保留仓库目录结构并加载 `SKILL.md`。普通本地 LLM 可以把 `SKILL.md` 作为指令，再分析采集器输出的 JSON。

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
| Codex | `$anti-claude-check` | 支持 |
| Claude Code | `/anti-claude-check` | 支持，已完成发现测试 |
| Agent Skills 兼容宿主 | 按宿主规则 | 目录结构兼容 |
| 其他本地 LLM | 加载 `SKILL.md` 与采集器 JSON | 手动回退 |
| PowerShell | 7.x / Windows PowerShell 5.1 | 已自检 |

## 参与改进

发现误判或不支持的 Clash Verge 布局时，可提交 Issue，并附上已脱敏的采集结果和实际测试的浏览器/配置。不要发布订阅地址、凭据、完整 IP 或账号数据。

如果它帮你发现了真实泄漏，或者避免了一次破坏性的“指纹修复”，欢迎点一个 ⭐。

## 许可证

[MIT](LICENSE) © 2026 AschoofAlpha
