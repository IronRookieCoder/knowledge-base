#!/bin/bash
# Linux/Mac 安装 Git hooks 脚本

echo "安装 Git hooks..."

# 检查是否在 Git 仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "错误: 当前目录不是 Git 仓库"
    exit 1
fi

# 设置 Git hooks 目录
git config core.hooksPath .githooks

# 确保 hook 脚本有执行权限
chmod +x .githooks/pre-commit
chmod +x update-nav.sh

if [ $? -eq 0 ]; then
    echo "Git hooks 安装成功！"
    echo ""
    echo "现在当您提交包含 docs 目录变更的内容时，"
    echo "mkdocs.yml 的导航配置将自动更新。"
    echo ""
    echo "您也可以随时运行 ./update-nav.sh 手动更新导航。"
else
    echo "Git hooks 安装失败！"
    exit 1
fi