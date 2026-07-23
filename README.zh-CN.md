<div align="center">

# 反 Claude 检查

### 面向正常 Claude 使用场景的网络隐私与环境一致性审计

![License](https://img.shields.io/badge/license-MIT-2ea44f)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6)
![PowerShell](https://img.shields.io/badge/PowerShell-5.1%20%7C%207-5391FE)
![Codex](https://img.shields.io/badge/Codex-skill-111111)
![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-D97757)

[English](README.md) · [Skill 指令](SKILL.md) · [MIT License](LICENSE)

**一个 Skill 联合检查 Windows、Clash Verge/Mihomo、Chrome 与 Edge，不伪造指纹，不依赖反检测浏览器。**

</div>

> [!IMPORTANT]
> 本项目用于发现真实隐私泄漏和环境矛盾，不用于绕过 Claude 审核、机器人检测、验证码、地区限制或平台安全措施。

## 为什么需要它

代理正常不等于只有“出口 IP 正确”。DNS、WebRTC、IPv6、自动策略组或另一个浏览器仍可能走不同路径；检测网站也可能把字体、RTT、TCP/IP 系统推断或代理出口 IPv6 误判为泄漏。

`anti-claude-check` 把本地系统证据、Mihomo 运行时状态和浏览器实测整合到同一套流程中，区分真实问题与检测噪声，并只建议最小、可验证的修复。

## 能检查什么

| 层级 | 检查范围 |
| --- | --- |
| Clash Verge/Mihomo | 服务模式、系统代理、TUN、`strict-route`、stack、局域网访问、运行时策略选择 |
| DNS 与路由 | Mihomo DNS、fake-IP、`any:53`、`respect-rules`、物理网卡绕行、跨网站出口 |
| IPv6 与 WebRTC | 物理 IPv6、Teredo、隧道 IPv6、ICE candidates、Chrome/Edge 策略与扩展状态 |
| 浏览器一致性 | 活动配置、语言顺序、Accept-Language、时区、WebGL/GPU 上下文、浏览器降精度硬件值 |
| 检测报告 | ChaIP/BrowserLeaks 类报告中的 IP 信誉、ASN、RTT、TCP/IP 推断及指纹矛盾 |
| 本机适配 | 非默认路径、配置文件、网卡、策略组名称，以及真实长期美国或日本使用环境 |

## 30 秒安装

### Codex

```powershell
New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
git clone https://github.com/AschoofAlpha/anti-claude-check.git "$HOME/.codex/skills/anti-claude-check"
```

使用 `$anti-claude-check` 调用，或直接提出匹配的隐私审计问题。

### Claude Code

```powershell
New-Item -ItemType Directory -Force "$HOME/.claude/skills" | Out-Null
git clone https://github.com/AschoofAlpha/anti-claude-check.git "$HOME/.claude/skills/anti-claude-check"
```

使用 `/anti-claude-check` 调用。

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

## 工作流程

1. 采集只读本地快照。
2. 分别在 Chrome 和 Edge 中实测 DNS、WebRTC、IPv4/IPv6 与检测报告。
3. 将证据标记为 `已验证`、`推断` 或 `需要人工检查`。
4. 区分 `必须修复`、`可选一致性` 和 `保持不动`。
5. 每次只执行一项已获同意的修改，然后重新测试。

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
