@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "src\URUCHOM_CAPRI_BEZ_INSTALATORA.bat" (
 echo [BLAD] Brak pelnych zrodel Capri 0.1.3 w folderze src.
 echo Zsynchronizuj zrodla przed uruchomieniem.
 pause
 exit /b 2
)
call "src\URUCHOM_CAPRI_BEZ_INSTALATORA.bat" %*
exit /b %ERRORLEVEL%
