<p align="center">
  <img src="assets/social-preview.jpg" alt="Claude Shield — 本地隐私与代理一致性审计" width="100%">
</p>

<h1 align="center">Claude Shield</h1>

<p align="center"><strong>面向 Codex、Claude Code 和 Agent Skills 宿主的本地隐私与代理一致性审计。</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/default-read--only-2DD4BF?style=flat-square" alt="默认只读">
  <img src="https://img.shields.io/badge/platform-Windows-4F7CFF?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/browser-Chrome%20%2F%20Edge-4F7CFF?style=flat-square" alt="Chrome 和 Edge">
  <img src="https://img.shields.io/badge/license-MIT-64748B?style=flat-square" alt="MIT License">
</p>

<p align="center"><a href="README.md">English</a> · <a href="SKILL.md">Skill 指令</a> · <a href="LICENSE">MIT License</a></p>

> **先审计，只修改你明确批准的内容。**

Claude Shield 检查真实的网络、DNS、WebRTC、IPv6 和浏览器矛盾，不伪造指纹、不隐藏自动化、不编造身份，也不承诺绕过平台审核。

## 快速开始

```powershell
git clone https://github.com/AschoofAlpha/claude-shield.git "$HOME/.codex/skills/anti-claude-check"
```

在 Codex 中调用 `$anti-claude-check`。Claude Code 用户将同一目录安装到 `~/.claude/skills/anti-claude-check`，调用 `/anti-claude-check`。

## 你会得到什么

- Windows 完整只读采集器：检查代理、DNS、IPv6、浏览器及 Claude Code 官方隐私设置；POSIX 仅提供有限的环境摘要。
- 中英双语 Chrome/Edge 页面：透明的 0–100 启发式评分、分类图表、问题列表、LLM 文本、脱敏 JSON 和 PNG 图片报告。
- Clash Verge/Mihomo 检查：规则模式、系统代理、服务/TUN、`strict-route`、fake-IP、DNS 劫持、局域网访问，以及本地控制器可用时的实际策略选择。
- 建议明确分成 **必须处理**、**可选一致性** 和 **保持不动**。
- 可选且可回滚的隐私环境变量修复；不会自动修改 DNS、路由、防火墙、VPN、IPv6 网卡、设备 ID、缓存或浏览器指纹。

评分只是本地证据，不是账号通过审核或避免封禁的预测。

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

## 浏览器评分和图片报告

在日常使用的 Chrome 配置中打开 [`assets/browser-audit.html`](assets/browser-audit.html)，完成检测后再在 Edge 中重复。页面会：

- 只读取浏览器正常提供的值，不修改任何指纹；
- 显示中英文评分、分类图表和建议；
- 导出 CLI 可直接导入的脱敏 JSON；
- 复制 `ANTI_CLAUDE_BROWSER_REPORT_V1` 报告给 LLM；
- 生成对应语言的 PNG 图片报告。

可选 WebRTC 检查会向 Google 公共 STUN 服务发送一次发现请求。原始 ICE 地址只在本地页面显示，导出时会替换为分类标签。

## 可选 CLI

```powershell
python -m pip install .
anti-claude-check audit --offline --format json
anti-claude-check browser import .\browser-audit.json
```

旧命令 `claude-shield` 作为兼容别名保留。wheel 会包含采集脚本、浏览器评分页、Schema、Skill 指令和中英文 README。

## 隐私设置修复

先预览：

```powershell
pwsh -NoProfile -File .\scripts\remediate_windows_network.ps1
```

得到明确同意后，再设置 Claude Code 官方隐私环境变量：

```powershell
pwsh -NoProfile -File .\scripts\remediate_windows_network.ps1 -Apply
```

脚本会创建备份并打印准确的回滚命令。广义“非必要流量”开关可能同时停用部分 Claude Code 可选功能，只有接受该取舍时才应开启。POSIX 的 `--apply` 只创建权限受限的环境文件并打印 `source` 命令，不会编辑 shell 配置或网络设置。

## 安全边界

- 不伪造浏览器指纹，不隐藏自动化，不绕过验证码，不提供多账号工具。
- 不编造身份、居住地、账单、税务或支付信息。
- 不自动删除设备 ID、遥测缓存，也不进行全局网络修改。
- 不承诺任何配置能够阻止账号审核或封禁。

Claude Code 隐私设置和限流结论以当前官方文档为准；第三方检测器标签只有得到实时路由证据支持后才应视为问题。

如果它帮你发现了真实泄漏，或避免了一次不必要的破坏性修改，欢迎点一个 GitHub Star。
