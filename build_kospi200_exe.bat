@echo off
rem 코스피200 크롤러 실행파일(dist\Kospi200.exe) 빌드 + 배포용 zip 생성
chcp 65001 > nul
cd /d %~dp0

pyinstaller --noconfirm --clean --onefile --windowed --name Kospi200 ^
  --exclude-module PySide6 --exclude-module matplotlib --exclude-module pandas ^
  --exclude-module numpy --exclude-module scipy --exclude-module IPython ^
  --exclude-module tkinter --exclude-module bs4 ^
  kospi200_crawler.py
if errorlevel 1 exit /b 1

powershell -NoProfile -Command "Compress-Archive -Path dist\Kospi200.exe -DestinationPath dist\Kospi200.zip -Force"
echo.
echo 완료: dist\Kospi200.exe, dist\Kospi200.zip
