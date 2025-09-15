# Knowledge Base 企业知识库管理系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个现代化的企业知识库管理系统，支持多源文档同步、智能搜索和MCP协议接口。

## ✨ 特性

- 🔄 **多源同步**: 支持GitLab和Confluence文档自动同步
- 🔍 **智能搜索**: 基于Whoosh的全文搜索，支持中文分词
- 🚀 **RESTful API**: 完整的REST API接口
- 🤖 **MCP协议**: 支持Claude等AI助手直接访问
- 🐳 **容器化**: 完整的Docker部署方案
- 📚 **文档展示**: 基于MkDocs的美观文档界面
- 🔧 **MonoRepo**: 统一的代码仓库管理

## 🏗️ 架构设计

```
knowledge-base/
├── packages/                    # 核心服务包
│   ├── knowledge_common/        # 共享模块
│   ├── knowledge_sync/          # 文档同步服务
│   ├── knowledge_api/           # REST API服务
│   └── knowledge_mcp/           # MCP协议服务
├── config/                      # 配置文件
├── docker/                      # Docker配置
├── tests/                       # 测试文件
└── docs/                        # 项目文档
```

## 🚀 快速开始

> **注意**: 建议在虚拟环境中运行本项目，以避免依赖冲突。

### 前置要求

- Python 3.8+
- Docker & Docker Compose (可选)
- SQLite (轻量级数据库)
- Git (用于文档同步)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd knowledge-base
   ```

2. **创建并激活虚拟环境**

   **Windows (CMD):**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

   **Windows (Git Bash):**
   ```bash
   python -m venv venv
   source ./venv/Scripts/activate
   ```

   **Linux/Mac:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **运行初始化脚本**
   ```bash
   python tools/scripts/setup.py
   ```

   初始化脚本会自动：
   - 检查虚拟环境状态
   - 创建虚拟环境（如果需要）
   - 安装所有依赖
   - 设置开发环境
   - 初始化数据库

4. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置数据库和API凭据
   ```

5. **配置文档源**
   ```bash
   # 编辑 config/sources.yml，配置GitLab项目和Confluence空间
   ```

### 开发环境启动

**Linux/Mac (使用make):**
```bash
# 启动完整开发环境
make dev

# 或分别启动各服务
make docs-dev     # 文档服务 (http://localhost:8000)
make api-start    # API服务 (http://localhost:8080)
make mcp-start    # MCP服务
make sync-start   # 同步服务
```

**Windows (使用Python脚本):**
```bash
# 启动完整开发环境
python run.py dev

# 或分别启动各服务
python run.py docs-dev     # 文档服务 (http://localhost:8000)
python run.py api-start    # API服务 (http://localhost:8080)
python run.py mcp-start    # MCP服务
python run.py sync-start   # 同步服务

# 查看所有可用命令
python run.py help
```

### Docker部署

```bash
# 开发环境
docker-compose -f docker/docker-compose.dev.yml up -d

# 生产环境
docker-compose -f docker/docker-compose.yml up -d
```

## 📖 使用指南

### 1. 文档同步

配置 `config/sources.yml` 文件：

```yaml
sources:
  gitlab:
    - name: "API文档"
      project_id: 123
      docs_path: "docs/"
      branch: "main"
      target_path: "api/"
      category: "api"

  confluence:
    - key: "DEV"
      name: "开发指南"
      target_path: "dev-guide/"
      category: "development"
```

执行同步：

**Linux/Mac:**
```bash
# 同步所有配置的源
make sync-start

# 或使用CLI命令
python -m packages.knowledge_sync.main sync
```

**Windows:**
```bash
# 同步所有配置的源
python run.py sync-start

# 或使用CLI命令
python -m packages.knowledge_sync.main sync
```

**通用CLI命令:**
```bash
# 同步特定GitLab项目
python -m packages.knowledge_sync.main sync-gitlab --project-id 123

# 同步特定Confluence空间
python -m packages.knowledge_sync.main sync-confluence --space-key DEV
```

### 2. API接口

启动API服务后，访问以下端点：

- **API文档**: http://localhost:8080/docs
- **健康检查**: http://localhost:8080/health
- **搜索文档**: `POST /api/documents/search`
- **获取文档**: `GET /api/documents/{id}`
- **文档列表**: `GET /api/documents/`
- **分类统计**: `GET /api/documents/categories/`

### 3. MCP集成

MCP服务提供以下工具：

- `search_knowledge`: 搜索知识库内容
- `get_document`: 获取特定文档
- `get_categories`: 获取文档分类
- `get_stats`: 获取统计信息

在Claude中配置MCP服务器：

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "python",
      "args": ["-m", "packages.knowledge_mcp.server"],
      "cwd": "/path/to/knowledge-base"
    }
  }
}
```

## 🔧 配置说明

### 环境变量

主要配置项（`.env`文件）：

```bash
# 数据库
DATABASE_URL=sqlite+aiosqlite:///data/knowledge_base.db

# GitLab
GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=your_token

# Confluence
CONFLUENCE_URL=https://company.atlassian.net/wiki
CONFLUENCE_USER=username
CONFLUENCE_TOKEN=token

# 服务配置
API_HOST=0.0.0.0
API_PORT=8080
MCP_PORT=9000
```

### 搜索配置

在 `config/custom_dict.txt` 中添加自定义词典，提高中文搜索准确性：

```text
# 技术术语
API接口
微服务
容器化
Kubernetes
```

## 📊 监控和维护

### 健康检查

```bash
# 检查所有服务状态
curl http://localhost:8080/health

# 检查数据库连接
python -c "from packages.knowledge_common.database import db_manager; import asyncio; asyncio.run(db_manager.get_session().__anext__())"
```

### 日志查看

```bash
# Docker环境
docker-compose logs -f api-service
docker-compose logs -f sync-service

# 直接运行
tail -f logs/app.log
```

### 数据备份

```bash
# 备份SQLite数据库
cp data/knowledge_base.db backup/knowledge_base_$(date +%Y%m%d).db

# 备份搜索索引
tar -czf search_index_backup.tar.gz data/search_index/
```

## 🧪 测试

**Linux/Mac:**
```bash
# 运行所有测试
make test

# 运行特定模块测试
pytest tests/test_api/ -v

# 运行覆盖率测试
pytest --cov=packages/ --cov-report=html
```

**Windows:**
```bash
# 运行所有测试
python run.py test

# 运行特定模块测试
pytest tests/test_api/ -v

# 运行覆盖率测试
pytest --cov=packages/ --cov-report=html
```

## 🛠️ 开发指南

### 代码规范

项目使用以下工具确保代码质量：

- **Black**: 代码格式化
- **isort**: 导入排序
- **MyPy**: 类型检查
- **pre-commit**: Git钩子

**Linux/Mac:**
```bash
# 运行代码检查
make lint

# 手动格式化
black packages/
isort packages/
```

**Windows:**
```bash
# 运行代码检查
python run.py lint

# 手动格式化
black packages/
isort packages/
```

### 添加新功能

1. 在相应的包中添加功能代码
2. 添加对应的测试用例
3. 更新API文档和配置
4. 提交前运行完整测试

### 调试技巧

```bash
# 启用调试模式
export DEBUG=true

# 查看详细日志
export LOG_LEVEL=debug

# 使用调试器
python -m pdb packages/knowledge_api/main.py
```

## 📚 API文档

完整的API文档在服务启动后可通过以下地址访问：

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI规范**: http://localhost:8080/openapi.json

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如有问题或建议，请：

1. 查看 [文档](docs/)
2. 搜索 [Issues](../../issues)
3. 创建新的 [Issue](../../issues/new)

---

⭐ 如果这个项目对您有帮助，请给个星标！