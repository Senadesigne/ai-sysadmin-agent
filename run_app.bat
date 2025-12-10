@echo off
echo Installing/Updating dependencies...
py -m pip install -r requirements.txt
echo.
echo Starting AI SysAdmin Agent...
py -m chainlit run app/ui/chat.py -w
pause
