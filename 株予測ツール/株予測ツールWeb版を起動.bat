@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "AI株予測ツール Web版サーバー（このウィンドウを閉じると終了します）" py webapp\server.py
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8765
