@echo off
echo Pokrecem AI SysAdmin Agenta...

:: 1. Aktiviraj virtualno okruzenje (za svaki slucaj)
call .venv\Scripts\activate

:: 2. Postavi Python putanju da vidi 'app' mapu
set PYTHONPATH=.

:: 3. Pokreni Chainlit
chainlit run app/ui/chat.py

:: 4. Zadrzi prozor otvorenim ako se dogodi greska
pause