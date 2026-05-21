@REM git config --global user.name "akusing"
@REM git config --global user.email "Qwerty@147258."
@REM git config --global credential.helper manager-core
@echo off
git add .
for /f "tokens=1-6 delims=/: " %%a in ('echo %date%%time%') do (
    set year=%%a
    set month=%%b
    set day=%%c
    set hour=%%d
    set minute=%%e
    set second=%%f
)
git commit -m "%year%-%month%-%day% %hour%:%minute%:%second%"

@REM git commit -m "XXXXXX"
git push -u origin master
