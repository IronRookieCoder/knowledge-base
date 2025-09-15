@echo off
REM Windows 安装 Git hooks 脚本

echo 安装 Git hooks...

REM 检查是否在 Git 仓库中
git rev-parse --git-dir >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 当前目录不是 Git 仓库
    pause
    exit /b 1
)

REM 设置 Git hooks 目录
git config core.hooksPath .githooks

if %ERRORLEVEL% EQU 0 (
    echo Git hooks 安装成功！
    echo.
    echo 现在当您提交包含 docs 目录变更的内容时，
    echo mkdocs.yml 的导航配置将自动更新。
    echo.
    echo 您也可以随时运行 update-nav.bat 手动更新导航。
) else (
    echo Git hooks 安装失败！
)

pause