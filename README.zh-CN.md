<h1 align="center">Claude Shield</h1>

<p align="center"><strong>面向 Codex、Claude Code 和 Agent Skills 宿主的本地隐私与代理一致性审计。</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/default-read--only-2DD4BF?style=flat-square" alt="默认只读">
  <img src="https://img.shields.io/badge/platform-Windows-4F7CFF?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/license-MIT-64748B?style=flat-square" alt="MIT License">
</p>

<p align="center"><a href="README.md">English</a> · <a href="SKILL.md">Skill 指令</a> · <a href="LICENSE">MIT License</a></p>

> **先审计，只修改你明确批准的内容。**

Claude Shield 检查真实的网络与系统矛盾，不伪造指纹、不隐藏自动化、不编造身份，也不承诺绕过平台审核。

## 快速开始

```powershell
git clone https://github.com/AschoofAlpha/claude-shield.git "$HOME/.codex/skills/anti-claude-check"
```

在 Codex 中调用 `$anti-claude-check`。Claude Code 用户将同一目录安装到 `~/.claude/skills/anti-claude-check`，调用 `/anti-claude-check`。

## 你会得到什么

- Windows 完整只读采集器：检查代理、DNS、IPv6、系统及 Claude Code 官方隐私设置；POSIX 仅提供有限的环境摘要。
- Clash Verge/Mihomo 检查：规则模式、系统代理、服务/TUN、`strict-route`、fake-IP、DNS 劫持、局域网访问，以及本地控制器可用时的实际策略选择。
- 建议明确分成 **必须处理**、**可选一致性** 和 **保持不动**。
- 可选且可回滚的隐私环境变量修复；不会自动修改 DNS、路由、防火墙、VPN、IPv6 网卡、设备 ID、缓存或浏览器指纹。

审计结果只是本地证据，不是账号通过审核或避免封禁的预测。

## 只读采集

Windows PowerShell 7：

```powershell
pwsh -NoProfile -File .\scripts\collect_windows_network.ps1
```

Windows PowerShell 5.1：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\collect_windows_network.ps1
```

macOS 或 Linux：

```bash
bash ./scripts/collect_posix_network.sh
```

采集器原始输出可能含本地标识，请留在本机，由 Skill 脱敏后再分享。

## 报告

Skill 会返回一张紧凑的证据表（`signal`、`status`、`confidence`、`evidence`、`action`），后接三个短章节：**必须处理**、**可选一致性**、**保持不动**。完整报告格式与判定规则见 `SKILL.md`。

## 隐私开关

先预览：

```powershell
pwsh -NoProfile -File .\scripts\remediate_windows_network.ps1
```

经明确批准后，应用文档化的 Claude Code 隐私环境变量：

```powershell
pwsh -NoProfile -File .\scripts\remediate_windows_network.ps1 -Apply
```

脚本会写备份并打印精确的回滚命令。宽泛的非必要流量开关可能禁用 Claude Code 的某些可选功能，仅在明确接受该权衡时启用。POSIX 下 `--apply` 只创建私有环境文件并打印 `source` 命令，不修改 shell 配置或网络设置。

## 安全边界

- 不伪造指纹、不隐藏自动化、不绕过验证码，也不做多账号工具。
- 不编造身份、居住地、账单、税务或支付信息。
- 不自动删除设备 ID、遥测缓存，也不做全局网络修改。
- 不声称任何配置能防止账号审核或封禁。

Claude Code 隐私开关与限流规则以官方最新文档为准。第三方检测器标签只是观点，需有实时路由证据佐证。

如果这个项目帮你发现了一个真实泄漏、或避免了一次不必要的破坏性改动，一个 GitHub star 能让更多人找到它。
