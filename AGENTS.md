# DesktopWidget 项目说明

## 文件访问
本项目文件位于 D:\PythonProjects\DesktopWidget，代码基于 Python 3 + PyQt6。

## 已知问题：Codex 沙箱无法启动 pwsh.exe

### 现象
- `shell_command` 报错：`CreateProcessAsUserW failed: 5 (拒绝访问。)`
- 错误命令路径始终指向 `C:\Users\Cherish\AppData\Local\Microsoft\WindowsApps\pwsh.exe`

### 根因
Codex 沙箱内部硬编码了 `WindowsApps` 目录下的 `pwsh.exe` 路径来启动 PowerShell，但：
1. **`C:\Program Files\` 下面没有 `WindowsApps` 文件夹**，`WindowsApps` 位于 `C:\Program Files\WindowsApps`，且是受系统保护的特殊目录，普通进程无法读取或执行其中的文件。
2. 新安装的 PowerShell 7.6.5 在 `C:\Program Files\PowerShell\7\pwsh.exe`，但沙箱不会去 PATH 中查找，而是硬编码了 `WindowsApps` 路径。

### 当前状态
- ❌ `shell_command`（沙箱内置工具）不可用
- ✅ Node.js MCP `child_process` 调 `C:\Program Files\PowerShell\7\pwsh.exe` 正常
- ✅ Node.js 直接读写文件正常
- ✅ 通过 Node.js 调用 git、Python 正常

### 备注
这个问题是 Codex 沙箱的 bug，需要 Codex 开发团队修复路径查找逻辑（应从 PATH 环境变量中查找 `pwsh.exe` 而非硬编码）。
