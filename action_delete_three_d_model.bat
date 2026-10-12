@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0action_delete_three_d_model.ps1" %*
set "model_exit=%errorlevel%"
if not "%model_exit%"=="0" echo 3D model deletion failed. See the error above.
exit /b %model_exit%
