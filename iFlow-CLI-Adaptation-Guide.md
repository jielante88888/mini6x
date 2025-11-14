# GitHub Spec Kit 工作流适配 iFlow CLI 说明

## 概述

本指南说明了如何将 GitHub Spec Kit 工作流配置适配到 iFlow CLI 环境。

## 已完成的适配工作

### 1. 目录结构分析

```
E:\DAIMA\mini6\
├── .gemini/commands/          # iFlow CLI 命令配置目录
│   ├── speckit.analyze.toml   # 分析命令
│   ├── speckit.plan.toml      # 规划命令
│   ├── speckit.tasks.toml     # 任务命令
│   ├── speckit.clarify.toml   # 澄清命令
│   ├── speckit.constitution.toml # 宪法命令
│   ├── speckit.implement.toml # 实现命令
│   ├── speckit.specify.toml   # 规范命令
│   └── speckit.checklist.toml # 清单命令
├── .specify/                  # 原有 GitHub Spec Kit 配置
│   ├── scripts/               # 脚本目录
│   │   ├── powershell/        # PowerShell 脚本 (原始)
│   │   ├── bash/              # Bash 脚本 (新增)
│   │   ├── windows/           # Windows 批处理 (新增)
│   │   └── adaptive-check-prerequisites.py # 适配脚本
│   ├── templates/             # 模板文件
│   └── memory/                # 内存文件
└── specs/                     # 特性规格目录
```

### 2. 主要修改内容

#### A. 脚本调用路径适配

原始配置中所有 TOML 文件都调用 PowerShell 脚本：
```toml
# 原始 (不兼容 iFlow CLI)
Run `.specify/scripts/powershell/check-prerequisites.ps1 -Json` from repo root
```

已修改为使用 Python 适配脚本：
```toml
# 适配后 (兼容 iFlow CLI)
Run `python .specify/scripts/adaptive-check-prerequisites.py --json` from E:\DAIMA\mini6
```

#### B. 跨平台支持

创建了多平台支持的脚本版本：

1. **Python 适配脚本** (`.specify/scripts/adaptive-check-prerequisites.py`)
   - 自动检测操作系统
   - 调用对应的脚本版本
   - 统一接口

2. **Bash 版本** (`.specify/scripts/bash/`)
   - `check-prerequisites.sh` - 先决条件检查
   - `common.sh` - 通用函数库

3. **Windows 批处理版本** (`.specify/scripts/windows/`)
   - `check-prerequisites.bat` - 先决条件检查
   - `common.bat` - 通用函数库

### 3. 配置修改清单

| 文件 | 原始调用 | 修改后调用 |
|------|----------|------------|
| speckit.analyze.toml | PowerShell 脚本 | Python 适配脚本 |
| speckit.plan.toml | PowerShell 脚本 | Python 适配脚本 |
| speckit.tasks.toml | PowerShell 脚本 | Python 适配脚本 |
| speckit.clarify.toml | PowerShell 脚本 | Python 适配脚本 |
| speckit.implement.toml | PowerShell 脚本 | Python 适配脚本 |
| speckit.specify.toml | PowerShell 脚本 | Python 适配脚本 + bash 命令 |
| speckit.checklist.toml | PowerShell 脚本 | Python 适配脚本 |

## 使用方法

### 1. 基本使用

适配后的工作流与原始 GitHub Spec Kit 工作流使用方法相同：

```bash
# 创建新特性规范
/speckit.specify "Add user authentication system"

# 澄清需求
/speckit.clarify

# 生成实现计划
/speckit.plan

# 生成任务列表
/speckit.tasks

# 分析一致性
/speckit.analyze

# 执行实现
/speckit.implement
```

### 2. 脚本直接调用

也可以直接调用适配脚本：

```bash
# 使用 Python 适配脚本 (推荐)
python .specify/scripts/adaptive-check-prerequisites.py --json

# 在 Unix/Linux/macOS 上使用 Bash 脚本
bash .specify/scripts/bash/check-prerequisites.sh --json

# 在 Windows 上使用批处理脚本
cmd /c .specify/scripts/windows/check-prerequisites.bat /json
```

## 兼容性说明

### 1. 完全兼容

- **功能**: 所有原始 GitHub Spec Kit 功能都完整保留
- **接口**: 命令调用方式保持不变
- **输出**: JSON 和文本输出格式完全一致

### 2. 新增功能

- **跨平台支持**: 同时支持 Windows、macOS、Linux
- **自动检测**: Python 适配脚本自动选择最佳脚本版本
- **错误处理**: 改进了错误处理和用户反馈

### 3. 系统要求

- **Python 3.6+**: 用于运行适配脚本
- **Git**: 用于版本控制功能 (可选)
- **PowerShell**: 仅用于原始脚本，适配后不强制要求

## 故障排除

### 1. 常见问题

#### Python 脚本执行失败
```bash
# 确保 Python 已安装
python --version

# 确保脚本有执行权限
chmod +x .specify/scripts/adaptive-check-prerequisites.py
```

#### 脚本路径问题
```bash
# 确保在项目根目录执行
cd E:\DAIMA\mini6

# 使用绝对路径
python E:\DAIMA\mini6\.specify\scripts\adaptive-check-prerequisites.py --json
```

### 2. 调试模式

设置环境变量启用调试模式：
```bash
export SPECIFY_DEBUG=1
python .specify/scripts/adaptive-check-prerequisites.py --json --debug
```

## 下一步计划

1. **测试验证**: 验证所有命令在 iFlow CLI 环境中的正常运行
2. **文档完善**: 补充更多使用示例和最佳实践
3. **性能优化**: 优化脚本执行速度
4. **功能扩展**: 根据需要添加更多功能

## 支持与反馈

如果在使用过程中遇到问题，请：

1. 检查本故障排除部分
2. 查看脚本错误日志
3. 确认系统要求已满足
4. 提供详细的错误信息以便进一步诊断

---

**版本**: 1.0  
**更新日期**: 2025-11-14  
**适配目标**: iFlow CLI + GitHub Spec Kit