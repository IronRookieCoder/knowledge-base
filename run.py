#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows环境下的make替代脚本
"""

import sys
import subprocess
import os
import time
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == "win32":
    import locale
    import codecs

    # 尝试设置UTF-8编码
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass


def run_command(command, description="", background=False):
    """运行命令"""
    print(f"[任务] {description}")
    print(f"[执行] {command}")

    if background:
        # 后台运行
        process = subprocess.Popen(command, shell=True)
        return process
    else:
        result = subprocess.run(command, shell=True)
        return result.returncode == 0


def help_command():
    """显示帮助信息"""
    print("可用命令:")
    commands = {
        "help": "显示帮助信息",
        "install": "安装依赖",
        "dev": "启动开发环境",
        "docs-dev": "启动文档开发服务器",
        "docs-build": "构建文档",
        "docs-deploy": "部署文档",
        "sync-start": "启动同步服务",
        "api-start": "启动API服务",
        "mcp-start": "启动MCP服务",
        "update-nav": "更新导航",
        "test": "运行测试",
        "lint": "代码检查",
        "clean": "清理缓存"
    }

    for cmd, desc in commands.items():
        print(f"  {cmd:<15} {desc}")


def install():
    """安装依赖"""
    return run_command("pip install -e .[all]", "安装依赖")


def dev():
    """启动开发环境"""
    print("[启动] 开发环境启动中...")

    # 启动API服务(后台)
    api_process = run_command(
        "python -m uvicorn packages.knowledge_api.main:app --reload --host 127.0.0.1 --port 8080",
        "启动API服务(后台)",
        background=True
    )

    # 等待一下让API服务启动
    time.sleep(2)

    # 启动文档服务
    os.chdir("packages/docs")
    try:
        run_command("mkdocs serve", "启动文档服务")
    finally:
        # 清理后台进程
        try:
            api_process.terminate()
        except:
            pass


def docs_dev():
    """启动文档开发服务器"""
    os.chdir("packages/docs")
    return run_command("mkdocs serve", "启动文档开发服务器")


def docs_build():
    """构建文档"""
    os.chdir("packages/docs")
    return run_command("mkdocs build", "构建文档")


def docs_deploy():
    """部署文档"""
    os.chdir("packages/docs")
    return run_command("mkdocs gh-deploy", "部署文档")


def sync_start():
    """启动同步服务"""
    return run_command("python -m packages.knowledge_sync.main", "启动同步服务")


def api_start():
    """启动API服务"""
    return run_command("python -m uvicorn packages.knowledge_api.main:app --reload --host 127.0.0.1 --port 8080", "启动API服务")


def mcp_start():
    """启动MCP服务"""
    return run_command("python -m packages.knowledge_mcp.server", "启动MCP服务")


def update_nav():
    """更新导航"""
    return run_command("python packages/docs/scripts/update_nav.py", "更新导航")


def test():
    """运行测试"""
    return run_command("pytest tests/", "运行测试")


def lint():
    """代码检查"""
    commands = [
        ("black packages/", "格式化代码"),
        ("isort packages/", "排序import"),
        ("mypy packages/", "类型检查")
    ]

    for command, description in commands:
        if not run_command(command, description):
            return False
    return True


def clean():
    """清理缓存"""
    import shutil

    print("[清理] 缓存清理中...")

    # 查找并删除__pycache__目录
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                cache_dir = os.path.join(root, dir_name)
                print(f"删除: {cache_dir}")
                shutil.rmtree(cache_dir)

        # 删除.pyc文件
        for file_name in files:
            if file_name.endswith('.pyc'):
                pyc_file = os.path.join(root, file_name)
                print(f"删除: {pyc_file}")
                os.remove(pyc_file)

    print("[完成] 缓存清理完成")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        help_command()
        return

    command = sys.argv[1]

    # 命令映射
    commands = {
        "help": help_command,
        "install": install,
        "dev": dev,
        "docs-dev": docs_dev,
        "docs-build": docs_build,
        "docs-deploy": docs_deploy,
        "sync-start": sync_start,
        "api-start": api_start,
        "mcp-start": mcp_start,
        "update-nav": update_nav,
        "test": test,
        "lint": lint,
        "clean": clean
    }

    if command in commands:
        try:
            commands[command]()
        except KeyboardInterrupt:
            print("\n[中断] 操作被用户中断")
        except Exception as e:
            print(f"[错误] 执行失败: {e}")
    else:
        print(f"[错误] 未知命令: {command}")
        help_command()


if __name__ == "__main__":
    main()