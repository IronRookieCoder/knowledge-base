#!/usr/bin/env python3
"""
项目初始化脚本
"""

import os
import sys
import subprocess
import shutil
import venv
from pathlib import Path


def run_command(command, description=""):
    """运行命令并处理错误"""
    print(f"📋 {description}")
    print(f"💻 执行: {command}")

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ 成功")
        if result.stdout:
            print(result.stdout)
    else:
        print("❌ 失败")
        print(result.stderr)
        return False

    print("-" * 50)
    return True


def setup_virtual_environment():
    """设置虚拟环境"""
    venv_dir = Path("venv")

    # 检查是否已在虚拟环境中
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 已在虚拟环境中运行")
        return True

    # 检查虚拟环境是否存在
    if venv_dir.exists():
        print("📁 发现现有虚拟环境目录")
        response = input("❓ 是否重新创建虚拟环境? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            print("🗑️  删除现有虚拟环境...")
            shutil.rmtree(venv_dir)
        else:
            print("💡 使用现有虚拟环境，请手动激活:")
            if os.name == 'nt':  # Windows
                print(f"   # CMD:")
                print(f"   {venv_dir}\\Scripts\\activate")
                print(f"   # Git Bash:")
                print(f"   source ./{venv_dir}/Scripts/activate")
            else:  # Unix/Linux/Mac
                print(f"   source {venv_dir}/bin/activate")
            print("   然后重新运行此脚本")
            return False

    # 创建虚拟环境
    print("🐍 创建虚拟环境...")
    try:
        venv.create(venv_dir, with_pip=True)
        print("✅ 虚拟环境创建成功")

        print("\n💡 请激活虚拟环境后重新运行此脚本:")
        if os.name == 'nt':  # Windows
            print(f"   # CMD:")
            print(f"   {venv_dir}\\Scripts\\activate")
            print(f"   # Git Bash:")
            print(f"   source ./{venv_dir}/Scripts/activate")
        else:  # Unix/Linux/Mac
            print(f"   source {venv_dir}/bin/activate")
        print("   python tools/scripts/setup.py")

        return False
    except Exception as e:
        print(f"❌ 创建虚拟环境失败: {e}")
        return False


def check_prerequisites():
    """检查前置条件"""
    print("🔍 检查前置条件...")

    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ Python版本需要3.8或更高")
        return False

    print(f"✅ Python版本: {sys.version}")

    # 检查虚拟环境
    if not setup_virtual_environment():
        return False

    # 检查Docker
    if not shutil.which("docker"):
        print("⚠️  Docker未安装，Docker功能将不可用")
    else:
        print("✅ Docker已安装")

    # 检查Git
    if not shutil.which("git"):
        print("⚠️  Git未安装，部分功能可能不可用")
    else:
        print("✅ Git已安装")

    return True


def setup_environment():
    """设置开发环境"""
    print("🛠️  设置开发环境...")

    # 创建.env文件
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ 创建.env文件")

    # 创建数据目录
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    search_index_dir = data_dir / "search_index"
    search_index_dir.mkdir(exist_ok=True)

    print("✅ 创建数据目录")


def install_dependencies():
    """安装依赖"""
    print("📦 安装Python依赖...")

    # 首先确保pip可用
    print("🔧 确保pip可用...")
    try:
        # 使用ensurepip确保pip已安装
        result = subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("⚠️  ensurepip失败，尝试其他方法...")
            # 如果ensurepip失败，尝试直接运行pip
            test_result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                       capture_output=True, text=True)
            if test_result.returncode != 0:
                print("❌ pip不可用，请检查Python安装")
                return False
        print("✅ pip可用")
    except Exception as e:
        print(f"⚠️  pip检查异常: {e}")

    # 安装完整依赖
    commands = [
        (f"{sys.executable} -m pip install --upgrade pip", "升级pip"),
        (f"{sys.executable} -m pip install -e .[all]", "安装所有项目依赖（包括核心、同步、API、MCP、Web和开发依赖）"),
    ]

    for command, description in commands:
        if not run_command(command, description):
            # 如果完整安装失败，尝试分别安装各个模块
            print("⚠️  完整安装失败，尝试分别安装各个模块...")
            fallback_commands = [
                (f"{sys.executable} -m pip install -e .", "安装核心依赖"),
                (f"{sys.executable} -m pip install -e .[sync]", "安装同步服务依赖"),
                (f"{sys.executable} -m pip install -e .[api]", "安装API服务依赖"),
                (f"{sys.executable} -m pip install -e .[web]", "安装Web服务依赖"),
                (f"{sys.executable} -m pip install -e .[dev]", "安装开发依赖"),
                # MCP依赖可能不可用，单独处理
            ]

            success_count = 0
            for fallback_cmd, fallback_desc in fallback_commands:
                if run_command(fallback_cmd, fallback_desc):
                    success_count += 1
                else:
                    print(f"⚠️  {fallback_desc}失败，跳过...")

            # 单独尝试安装MCP依赖（可能失败）
            print("🔧 尝试安装MCP依赖（可能需要额外配置）...")
            mcp_result = run_command(f"{sys.executable} -m pip install -e .[mcp]", "安装MCP服务依赖")
            if not mcp_result:
                print("⚠️  MCP依赖安装失败，MCP功能将不可用")
                print("💡 您可以稍后手动安装: pip install mcp websockets")

            if success_count >= 4:  # 至少安装成功4个模块
                print(f"✅ 成功安装 {success_count} 个模块的依赖")
                return True
            else:
                print(f"❌ 只成功安装了 {success_count} 个模块，可能影响系统功能")
                return False

    return True


def setup_database():
    """设置数据库"""
    print("🗄️  设置数据库...")

    # 检查是否有Docker
    if shutil.which("docker"):
        command = "docker-compose -f docker/docker-compose.dev.yml up -d database"
        if run_command(command, "启动开发数据库"):
            # 等待数据库启动
            import time
            print("⏳ 等待数据库启动...")
            time.sleep(10)

            # 初始化数据库
            command = "python -m packages.knowledge_sync.main init-db"
            run_command(command, "初始化数据库表")
    else:
        print("⚠️  Docker未安装，SQLite数据库将在首次运行时自动创建")


def setup_pre_commit():
    """设置pre-commit钩子"""
    print("🔧 设置pre-commit钩子...")

    commands = [
        ("pre-commit install", "安装pre-commit钩子"),
        ("pre-commit autoupdate", "更新pre-commit配置"),
    ]

    for command, description in commands:
        run_command(command, description)


def run_tests():
    """运行测试"""
    print("🧪 运行测试...")

    command = "pytest tests/ -v"
    run_command(command, "运行单元测试")


def print_next_steps():
    """打印后续步骤"""
    print("\n" + "="*60)
    print("🎉 业务知识管理平台初始化完成！")
    print("="*60)

    print("\n📋 功能模块说明:")
    print("🔄 同步服务 - 从GitLab/Confluence等平台同步文档")
    print("🌐 Web服务  - MkDocs文档网站，提供用户友好界面")
    print("🔌 API服务  - REST API，支持搜索和文档管理")
    print("🤖 MCP服务  - Model Context Protocol，与AI工具集成")

    print("\n📋 快速启动步骤:")
    print("1. 编辑 .env 文件，配置GitLab和Confluence访问凭据")
    print("2. 编辑 config/sources.yml 文件，配置要同步的文档源")
    print("3. 启动开发环境: python run.py dev")
    print("   （或分别启动各个服务）")

    print("\n🚀 启动命令:")
    print("- python run.py dev   # 启动完整开发环境（推荐）")
    print("- make dev            # 使用Makefile启动（如果已安装make）")
    print("- make docs-dev       # 仅启动文档服务")
    print("- make api-start      # 仅启动API服务")
    print("- make sync-start     # 仅运行同步服务")
    print("- make mcp-start      # 仅启动MCP服务")

    print("\n🔧 开发工具:")
    print("- make test           # 运行测试")
    print("- make lint           # 代码检查和格式化")
    print("- make clean          # 清理缓存文件")
    print("- make help           # 查看所有可用命令")

    print("\n🐳 Docker部署:")
    print("- docker-compose -f docker/docker-compose.dev.yml up  # 开发环境")
    print("- docker-compose -f docker/docker-compose.yml up     # 生产环境")

    print("\n📚 访问地址:")
    print("- 📖 文档网站: http://localhost:8000/")
    print("- 🔌 API文档: http://localhost:8080/docs")
    print("- 💊 健康检查: http://localhost:8080/health")
    print("- 🔍 搜索示例: curl -X POST http://localhost:8080/api/documents/search \\")
    print("               -H 'Content-Type: application/json' \\")
    print("               -d '{\"query\": \"知识管理\", \"limit\": 5}'")

    print("\n💡 使用提示:")
    print("- 首次运行会自动创建SQLite数据库和搜索索引")
    print("- 本地文档会自动加载到系统中，支持中文搜索")
    print("- 如需MCP功能，确保已安装: pip install mcp websockets")
    print("- 生产环境建议使用Docker部署")

    print("\n📋 配置说明:")
    print("- .env: 环境变量配置（数据库、API密钥等）")
    print("- config/sources.yml: 文档源配置文件")
    print("- packages/docs/mkdocs.yml: 文档站点配置")
    print("- pyproject.toml: Python项目和依赖配置")


def main():
    """主函数"""
    print("🚀 Knowledge Base 项目初始化")
    print("="*60)

    try:
        if not check_prerequisites():
            return False

        setup_environment()

        if not install_dependencies():
            return False

        setup_database()
        setup_pre_commit()

        # 询问是否运行测试
        response = input("\n❓ 是否运行测试? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            run_tests()

        print_next_steps()
        return True

    except KeyboardInterrupt:
        print("\n\n❌ 初始化被用户中断")
        return False
    except Exception as e:
        print(f"\n\n❌ 初始化失败: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)