@echo off
rem 뉴스 크롤러 실행파일(dist\NewsCrawler.exe) 빌드 + 배포용 zip 생성
chcp 65001 > nul
cd /d %~dp0

pyinstaller --noconfirm --clean --onefile --windowed --name NewsCrawler ^
  --exclude-module PySide6 --exclude-module matplotlib --exclude-module pandas ^
  --exclude-module numpy --exclude-module scipy --exclude-module IPython ^
  --exclude-module tkinter ^
  naver_news_crawler.py
if errorlevel 1 exit /b 1

powershell -NoProfile -Command "Compress-Archive -Path dist\NewsCrawler.exe -DestinationPath dist\NewsCrawler.zip -Force"
echo.
echo 완료: dist\NewsCrawler.exe, dist\NewsCrawler.zip
