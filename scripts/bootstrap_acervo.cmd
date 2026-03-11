@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0bootstrap_acervo.ps1" %*
endlocal
