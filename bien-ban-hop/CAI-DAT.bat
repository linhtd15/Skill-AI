@echo off
chcp 65001 >nul
title Cai dat Agent bien ban hop
echo ============================================================
echo   CAI DAT AGENT BIEN BAN HOP (mien phi, chay tren may)
echo   Lan dau can Internet va khoang 3 GB dung luong trong.
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
echo.
pause
