@echo off
setlocal
pushd "%~dp0"
python working_supplier_data.py %*
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
