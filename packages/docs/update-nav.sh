#!/bin/bash
# Linux/Mac 脚本 - 手动更新导航

echo "更新 mkdocs.yml 导航配置..."

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 检查 Python 是否可用
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=python
else
    echo "错误: 未找到 Python，请先安装 Python"
    exit 1
fi

# 运行更新脚本
$PYTHON_CMD "$SCRIPT_DIR/scripts/update_nav.py"

if [ $? -eq 0 ]; then
    echo ""
    echo "导航更新完成！"
else
    echo ""
    echo "导航更新失败！"
    exit 1
fi