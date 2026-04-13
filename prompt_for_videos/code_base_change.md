@echo off

REM clear your logs before new run
adb logcat -c 

echo Creating timestamp...
set datetime=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set datetime=%datetime: =0%

set logfile=D:\MIKO\Downloads\Automation script\Logs\Story_maker_%datetime%.txt
set errorfile=D:\MIKO\Downloads\Automation script\Logs\Story_maker_error_%datetime%.txt

REM ========================================
REM Flow: Home -> Apps -> Launch Talent -> Existing user Test
REM ========================================

REM bot is on root screen
adb shell input keyevent 3
timeout /t 2

REM action click on APPS button
adb shell input tap 1207 644
timeout /t 3

REM action click on storymaker talent
adb shell input tap 933 212
timeout /t 12

REM action click on cross icon of AI disclaimer
adb shell input tap 154 120
timeout /t 1

REM action click on existing story
adb shell input tap 590 370

REM action click on open story book
set COUNT=8

for /l %%i in (1,1,%COUNT%) do (
    adb shell input swipe 1100 360 200 360 250
    timeout /t 2 > nul
)

REM action click on like feature
adb shell input tap 947 507

REM action rever page of story book
set COUNT=8

for /l %%i in (1,1,%COUNT%) do (
   adb shell input swipe 200 360 1100 360 250
   timeout /t 2 > nul
)

REM action click on cross icon 
adb shell input tap 40 53

REM action to delete story
adb shell input tap 730 612
timeout /t 1

REM action click on delete deny 
adb shell input tap 908 642
timeout /t 1

REM action click on delete ok
adb shell input tap 1123 612

REM action to click on favourite
adb shell input tap 812 62
timeout /t 3

REM action to click on story book
adb shell input tap 476 77
timeout /t 3

REM action to click on Story left for the month
adb shell input tap 1216 66
timeout /t 3

REM action click on cross icon
adb shell input tap 71 73
timeout /t 2

REM action click on NO icon
adb shell input tap 892 620
timeout /t 2

REM action click on cross icon
adb shell input tap 71 73
timeout /t 2

REM action click on yes icon
adb shell input tap 1114 630
timeout /t 2

REM action click on exit icon to comeback to root screen
adb shell input tap 55 77
timeout /t 2

echo Dump logs to file...
adb logcat -d > "%logfile%"

echo Checking for crashes...
findstr /i "FATAL EXCEPTION ANR CRASH Error" "%logfile%" > "%errorfile%"

if %errorlevel%==0 (
    echo Story Talent = FAIL >> report.txt
) else (
    echo Story Talent = PASS >> report.txt
)

REM testing completed within 1m 42sec
echo Logs captured.

echo Story Test Completed