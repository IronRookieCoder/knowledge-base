# Makefile - Python项目统一管理
.PHONY: help install install-dev install-all install-web install-api install-sync install-mcp dev test lint clean docs-dev docs-build docs-deploy

help:  ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:  ## 安装基础依赖
	pip install -e .

install-web:  ## 安装web服务依赖
	pip install -e .[web]

install-api:  ## 安装API服务依赖
	pip install -e .[api]

install-sync:  ## 安装同步服务依赖
	pip install -e .[sync]

install-mcp:  ## 安装MCP服务依赖
	pip install -e .[mcp]

install-dev:  ## 安装开发依赖
	pip install -e .[dev]

install-all:  ## 安装所有依赖
	pip install -e .[all]

dev:  ## 启动开发环境
	python -m uvicorn packages.knowledge_api.main:app --reload &
	cd packages/docs && mkdocs serve

docs-dev:  ## 启动文档开发服务器
	cd packages/docs && mkdocs serve

docs-build:  ## 构建文档
	cd packages/docs && mkdocs build

docs-deploy:  ## 部署文档
	cd packages/docs && mkdocs gh-deploy

sync-start:  ## 启动同步服务
	kb-sync sync

sync-init:  ## 初始化数据库
	kb-sync init-db

api-start:  ## 启动API服务
	kb-api

mcp-start:  ## 启动MCP服务
	kb-mcp

update-nav:  ## 更新导航
	python packages/docs/scripts/update_nav.py

test:  ## 运行测试
	pytest tests/

lint:  ## 代码检查
	black packages/ && isort packages/ && mypy packages/

clean:  ## 清理缓存
	find . -name '__pycache__' -exec rm -rf {} + && find . -name '*.pyc' -delete