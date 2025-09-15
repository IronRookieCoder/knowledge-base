@echo off
REM Windows 批处理脚本 - 手动更新导航

echo 更新 mkdocs.yml 导航配置...

REM 检查 Python 是否可用
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python scripts\update_nav.py
) else (
    where python3 >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        python3 scripts\update_nav.py
    ) else (
        echo 错误: 未找到 Python，请先安装 Python
        pause
        exit /b 1
    )
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 导航更新完成！
) else (
    echo.
    echo 导航更新失败！
)

pause