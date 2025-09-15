#!/usr/bin/env python3
"""
自动更新 mkdocs.yml 导航配置
根据 docs 目录结构自动生成导航树
"""

import os
from pathlib import Path
import re
from ruamel.yaml import YAML

# 配置项
DOCS_DIR = Path(__file__).parent.parent / "docs"
MKDOCS_FILE = Path(__file__).parent.parent / "mkdocs.yml"

# 目录名称映射（英文到中文）
DIR_NAME_MAP = {
    "concepts": "基础概念",
    "paradigms": "开发范式", 
    "practices": "实践指南",
    "tools": "开发工具",
    "cases": "实践案例"
}

# 文件名称映射（可选，用于特定文件的中文名称）
FILE_NAME_MAP = {
    "index.md": "首页",
    "about.md": "关于",
    "ai-native-development.md": "AI-Native 开发模式",
    "development-paradigms.md": "三种开发范式",
    "ai-tools-classification.md": "AI工具分类",
    "spec-driven-development.md": "规格驱动开发",
    "prototype-verification.md": "原型验证开发",
    "ai-enhanced-traditional.md": "AI赋能传统流程",
    "making-ai-understand.md": "让AI懂",
    "making-ai-work.md": "让AI做",
    "making-ai-controllable.md": "让AI可控",
    "tool-usage.md": "工具使用",
    "agent-tools.md": "Agent类工具",
    "autonomous-tools.md": "自主开发工具",
    "specialized-tools.md": "专用工具",
    "knowledge-management.md": "知识管理",
    "git-worktree-claude.md": "Git Worktree + Claude Code"
}

# 导航顺序配置
NAV_ORDER = [
    "index.md",
    "concepts",
    "paradigms", 
    "practices",
    "tools",
    "cases",
    "about.md"
]

def get_file_title(file_path):
    """从 Markdown 文件中获取标题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('# '):
                    return line[2:].strip()
    except:
        pass
    
    # 如果无法从文件中获取标题，使用文件名映射或文件名
    file_name = os.path.basename(file_path)
    if file_name in FILE_NAME_MAP:
        return FILE_NAME_MAP[file_name]
    
    # 将文件名转换为标题格式
    name = os.path.splitext(file_name)[0]
    name = name.replace('-', ' ').replace('_', ' ')
    return name.title()

def scan_directory(path, base_path=None):
    """递归扫描目录，生成导航结构"""
    if base_path is None:
        base_path = path
    
    items = []
    
    # 获取目录中的所有文件和子目录
    entries = sorted(os.listdir(path))
    
    # 分离文件和目录
    files = []
    dirs = []
    
    for entry in entries:
        entry_path = os.path.join(path, entry)
        if os.path.isfile(entry_path) and entry.endswith('.md'):
            files.append(entry)
        elif os.path.isdir(entry_path) and not entry.startswith('.'):
            dirs.append(entry)
    
    # 处理文件
    for file in files:
        file_path = os.path.join(path, file)
        rel_path = os.path.relpath(file_path, base_path).replace('\\', '/')
        
        # 跳过根目录的 index.md 和 about.md（它们会单独处理）
        if path == base_path and file in ['index.md', 'about.md']:
            continue
            
        title = get_file_title(file_path)
        items.append({title: rel_path})
    
    # 处理子目录
    for dir_name in dirs:
        dir_path = os.path.join(path, dir_name)
        sub_items = scan_directory(dir_path, base_path)
        
        if sub_items:
            # 使用目录映射名称
            dir_title = DIR_NAME_MAP.get(dir_name, dir_name.replace('-', ' ').title())
            items.append({dir_title: sub_items})
    
    return items

def generate_nav():
    """生成导航结构"""
    nav = []
    processed = set()
    
    # 按照预定义顺序处理导航项
    for item in NAV_ORDER:
        item_path = DOCS_DIR / item
        
        if item.endswith('.md'):
            # 处理单个文件
            if item_path.exists():
                title = get_file_title(item_path)
                nav.append({title: item})
                processed.add(item)
        else:
            # 处理目录
            if item_path.exists() and item_path.is_dir():
                sub_items = scan_directory(item_path, DOCS_DIR)
                if sub_items:
                    dir_title = DIR_NAME_MAP.get(item, item.replace('-', ' ').title())
                    nav.append({dir_title: sub_items})
                    processed.add(item)
    
    # 添加任何未处理的项目
    for entry in sorted(os.listdir(DOCS_DIR)):
        if entry not in processed:
            entry_path = DOCS_DIR / entry
            
            if entry.endswith('.md') and entry_path.is_file():
                title = get_file_title(entry_path)
                nav.append({title: entry})
            elif entry_path.is_dir() and not entry.startswith('.'):
                sub_items = scan_directory(entry_path, DOCS_DIR)
                if sub_items:
                    dir_title = DIR_NAME_MAP.get(entry, entry.replace('-', ' ').title())
                    nav.append({dir_title: sub_items})
    
    return nav

def update_mkdocs_config():
    """更新 mkdocs.yml 文件中的导航配置"""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    
    # 读取现有配置
    with open(MKDOCS_FILE, 'r', encoding='utf-8') as f:
        config = yaml.load(f)
    
    # 生成新的导航
    new_nav = generate_nav()
    
    # 检查导航是否有变化
    if config.get('nav') == new_nav:
        print("导航已是最新，无需更新")
        return False
    
    # 更新导航
    config['nav'] = new_nav
    
    # 写回配置文件
    with open(MKDOCS_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(config, f)
    
    print("导航已更新")
    return True

def main():
    """主函数"""
    print(f"扫描文档目录: {DOCS_DIR}")
    print(f"更新配置文件: {MKDOCS_FILE}")
    
    if not DOCS_DIR.exists():
        print(f"错误: 文档目录不存在: {DOCS_DIR}")
        return 1
    
    if not MKDOCS_FILE.exists():
        print(f"错误: 配置文件不存在: {MKDOCS_FILE}")
        return 1
    
    try:
        changed = update_mkdocs_config()
        if changed:
            print("\n更新后的导航结构:")
            yaml = YAML()
            with open(MKDOCS_FILE, 'r', encoding='utf-8') as f:
                config = yaml.load(f)
                import json
                print(json.dumps(config['nav'], indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())