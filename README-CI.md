# GitHub Actions CI/CD 工作流配置

## 📋 工作流程概览

本项目已配置了完整的GitHub Actions CI/CD工作流，包含以下4个主要工作流：

### 1. 🔄 CI Pipeline (`ci.yml`)
**触发条件**: 每次推送到 main/develop 分支或创建PR时
**主要功能**:
- ✅ Flutter代码质量检查（格式、分析）
- ✅ Python代码质量检查（Black、isort、Flake8、Pylint、mypy）
- 🔨 Flutter构建测试（Windows应用构建）
- 🐍 Python模块测试
- 🔒 安全检查（Bandit）
- 📦 依赖安全检查（pip-audit）
- 🐳 Docker构建测试（可选）

### 2. 🔐 Security Scan (`security.yml`)
**触发条件**: 推送代码、PR或每周定时扫描
**主要功能**:
- 🔍 Trivy漏洞扫描
- 🛡️ Bandit Python安全扫描
- ⚠️ Safety依赖漏洞检查
- 🔬 Semgrep静态分析
- 📊 生成综合安全报告

### 3. 📊 Code Coverage Report (`coverage.yml`)
**触发条件**: 推送代码、PR时
**主要功能**:
- 📈 Flutter测试覆盖率分析
- 📈 Python测试覆盖率分析
- 🔗 自动上传到Codecov
- 📄 生成覆盖率报告

### 4. 🚀 Auto Release (`release.yml`)
**触发条件**: 创建版本标签或手动触发
**主要功能**:
- 🏗️ 构建Flutter Windows应用
- 📦 构建Python包
- 🏷️ 创建GitHub Release
- 🐳 发布Docker镜像（可选）

## 🛠️ 工具配置

### Flutter配置
- **版本**: 3.24.3 (stable)
- **平台**: Windows
- **检查项目**: 格式、分析、测试、构建

### Python配置
- **版本**: 3.11
- **代码质量工具**:
  - Black (代码格式化)
  - isort (导入排序)
  - Flake8 (代码规范)
  - Pylint (静态分析)
  - mypy (类型检查)
  - Bandit (安全扫描)
  - pytest (测试框架)

## 🔧 使用说明

### 1. 推送代码
```bash
git add .
git commit -m "feat: 添加新功能"
git push origin main
```
系统将自动触发CI Pipeline进行全面的代码质量检查。

### 2. 代码覆盖率
工作流会自动：
- 运行Flutter和Python测试
- 生成覆盖率报告
- 上传数据到Codecov
- 在PR中显示覆盖率变化

### 3. 安全检查
系统会定期自动运行安全扫描，也可以手动触发：
- GitHub → Actions → Security Scan → Run workflow

### 4. 创建发布
#### 自动发布（推荐）
```bash
git tag v1.0.0
git push origin v1.0.0
```

#### 手动发布
1. GitHub → Actions → Auto Release
2. 点击 "Run workflow"
3. 输入版本号并执行

## 📋 配置要求

### GitHub Secrets配置
确保在GitHub仓库设置中配置以下密钥：
- `DOCKER_USERNAME`: Docker Hub用户名
- `DOCKER_PASSWORD`: Docker Hub访问令牌
- `CODECOV_TOKEN`: Codecov令牌（可选）

### 文件结构要求
项目应包含以下文件（根据实际需要）：
- `pubspec.yaml`: Flutter项目配置
- `requirements.txt`: Python依赖（可选）
- `setup.py`: Python包配置（可选）
- `Dockerfile`: Docker配置（可选）
- `tests/`: 测试目录（可选）

## ⚙️ 自定义配置

### 修改触发分支
在各工作流文件中修改：
```yaml
on:
  push:
    branches: [ main, develop, your-branch ]
```

### 调整代码质量标准
在 `ci.yml` 中修改：
```yaml
- name: 运行Flake8代码检查
  run: python -m flake8 . --max-line-length=88 --ignore=E203,W503
```

### 调整安全检查级别
在 `security.yml` 中修改Bandit配置：
```yaml
- name: 运行Bandit Python安全扫描
  run: bandit -r . -f json -o bandit-results.json -ll
```

## 🚨 故障排除

### 常见问题
1. **Flutter构建失败**: 检查pubspec.yaml配置
2. **Python依赖错误**: 确保requirements.txt格式正确
3. **Docker构建失败**: 检查Dockerfile配置
4. **安全扫描警告**: 审查并修复安全问题

### 查看构建日志
- GitHub → Actions → 选择工作流 → 点击失败的任务 → 查看日志

## 📈 性能优化

### 缓存策略
- Flutter依赖缓存
- Python依赖缓存
- Docker层缓存

### 并行执行
- 代码质量检查、构建、测试并行运行
- 独立的工作流减少总体执行时间

---

**最后更新**: 2025年11月14日
**版本**: v1.0.0