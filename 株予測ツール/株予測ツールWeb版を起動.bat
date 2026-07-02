@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo サーバーを起動しています…準備ができ次第ブラウザが自動で開きます。
echo このウィンドウを閉じるとサーバーが終了します。
py webapp\server.py
pause
