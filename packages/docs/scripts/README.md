# 导航自动同步工具

此目录包含用于自动同步 docs 目录结构到 mkdocs.yml 导航配置的工具。

## 功能特性

- 🔄 **自动同步**: Git commit 时自动检测 docs 目录变更并更新导航
- 📝 **智能识别**: 从 Markdown 文件中提取标题作为导航项名称
- 🌏 **中文支持**: 预设的目录和文件名映射，生成友好的中文导航
- 🎯 **保持顺序**: 按预定义顺序组织导航结构
- 🛠️ **手动更新**: 提供脚本随时手动更新导航

## 文件说明

```
scripts/
├── update_nav.py        # 核心Python脚本，负责生成和更新导航
├── install-hooks.bat    # Windows 安装脚本
├── install-hooks.sh     # Linux/Mac 安装脚本
└── README.md           # 本文档

.githooks/
└── pre-commit          # Git pre-commit hook

update-nav.bat          # Windows 手动更新脚本
update-nav.sh           # Linux/Mac 手动更新脚本
```

## 安装方法

### Windows

```bash
# 运行安装脚本
scripts\install-hooks.bat
```

### Linux/Mac

```bash
# 添加执行权限并运行安装脚本
chmod +x scripts/install-hooks.sh
./scripts/install-hooks.sh
```

## 使用方法

### 自动更新（推荐）

安装后，每次执行 `git commit` 时，如果有 docs 目录的变更，导航会自动更新：

```bash
# 添加或修改文档
git add docs/new-file.md

# 提交时自动更新导航
git commit -m "添加新文档"
```

### 手动更新

如果需要手动更新导航：

**Windows:**
```bash
update-nav.bat
```

**Linux/Mac:**
```bash
./update-nav.sh
```

**或直接运行 Python 脚本:**
```bash
python scripts/update_nav.py
```

## 配置说明

在 `update_nav.py` 中可以配置：

### 目录名称映射
```python
DIR_NAME_MAP = {
    "concepts": "基础概念",
    "paradigms": "开发范式",
    # ...
}
```

### 文件名称映射
```python
FILE_NAME_MAP = {
    "index.md": "首页",
    "about.md": "关于",
    # ...
}
```

### 导航顺序
```python
NAV_ORDER = [
    "index.md",      # 首页始终在最前
    "concepts",      # 基础概念
    "paradigms",     # 开发范式
    # ...
    "about.md"       # 关于页面在最后
]
```

## 工作原理

1. **扫描 docs 目录**: 递归扫描所有 Markdown 文件
2. **提取标题**: 优先从文件内容提取 `# 标题`，否则使用文件名映射
3. **生成导航树**: 按照预定义顺序组织导航结构
4. **更新配置**: 将新的导航结构写入 mkdocs.yml
5. **Git 集成**: pre-commit hook 自动执行更新并将变更加入提交

## 注意事项

- 需要 Python 3.6+ 环境
- 需要安装 PyYAML: `pip install pyyaml`
- 文档文件必须是 `.md` 扩展名
- 隐藏目录（以 `.` 开头）会被忽略
- 如果文件中没有 `# 标题`，将使用文件名生成标题

## 故障排除

### Python 未找到
确保已安装 Python 并添加到 PATH：
```bash
python --version
# 或
python3 --version
```

### 权限问题（Linux/Mac）
```bash
chmod +x .githooks/pre-commit
chmod +x update-nav.sh
chmod +x scripts/*.sh
```

### Hook 未触发
检查 Git 配置：
```bash
git config core.hooksPath
# 应该输出: .githooks
```

如果没有输出或输出不正确，重新运行安装脚本。

## 临时禁用

如果需要临时跳过自动更新：
```bash
git commit --no-verify -m "跳过导航更新"
```