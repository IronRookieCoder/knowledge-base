## 📋 项目简介

此项目为一个 **AI-Native 开发实践经验文档库**，旨在分享和沉淀 AI 驱动的软件开发模式实践经验，为开发团队提供可操作的指导和参考。

## 🏗️ 项目架构

```
ai-native-docs/
├── README.md                   # 项目说明文档
├── CLAUDE.md                   # AI 助手项目记忆
├── mkdocs.yml                  # MkDocs 配置文件
├── requirements.txt            # Python 依赖
├── .gitlab-ci.yml             # GitLab Pages CI/CD
├── DEPLOYMENT.md              # 部署指南
├── docs/                      # 文档源码
│   ├── index.md              # 首页
│   ├── about.md              # 关于页面
│   ├── concepts/             # 基础概念
│   ├── paradigms/            # 开发范式
│   ├── practices/            # 实践指南
│   ├── tools/                # 开发工具
│   ├── cases/                # 实践案例
│   ├── stylesheets/          # 自定义样式
│   │   └── extra.css
│   └── javascripts/          # JavaScript 文件
│       └── mathjax.js
├── overrides/                 # 模板覆盖
│   └── 404.html              # 自定义 404 页面
└── site/                     # 生成的静态网站（构建后）
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Git

### 本地开发

1. **克隆仓库**
   ```bash
   git clone https://gitlab.com/your-repo/ai-native-docs.git
   cd ai-native-docs
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **启动开发服务器**
   ```bash
   mkdocs serve
   ```
   访问：http://127.0.0.1:8000

4. **构建静态网站**
   ```bash
   mkdocs build
   ```