' Lanciatore silenzioso per la sorveglianza crash di Kodi.
' L'Utilita' di pianificazione deve puntare a wscript.exe con questo file:
' e' l'unico modo per non far lampeggiare la finestra nera (vedi nota in memoria).
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\Users\infoa\Antigravity"
sh.Run "cmd /c node traduttore\cattura-crash.js >> C:\Users\infoa\Antigravity\traduttore\crash\guardia.log 2>&1", 0, False
