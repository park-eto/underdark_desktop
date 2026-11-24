@echo off
chcp 65001 > nul
echo ========================================================
echo   Underdark Macro Solver - Windows 실행 파일(.exe) 빌드
echo ========================================================
echo.

taskkill /f /im UnderdarkMacroSolver.exe 2>nul
python -m PyInstaller --clean --noconfirm UnderdarkMacroSolver.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [빌드 성공!]
    echo   실행 파일 위치: dist\UnderdarkMacroSolver.exe
    echo ========================================================
) else (
    echo.
    echo [오류] 빌드 중 문제가 발생했습니다.
)
pause
