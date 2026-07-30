# Script Ghidra (Jython) per l'analisi HEADLESS di Antigravity.
# Senza argomenti: elenca le funzioni. Con un nome funzione: la decompila.
# @category Antigravity
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

args = getScriptArgs()
target = args[0] if len(args) > 0 else None
fm = currentProgram.getFunctionManager()

if target and target != "__list__":
    di = DecompInterface()
    di.openProgram(currentProgram)
    found = False
    for f in fm.getFunctions(True):
        if f.getName() == target:
            res = di.decompileFunction(f, 60, ConsoleTaskMonitor())
            dc = res.getDecompiledFunction() if res else None
            if dc:
                print("=== DECOMPILE %s @ %s ===" % (f.getName(), f.getEntryPoint()))
                print(dc.getC())
            else:
                print("Decompilazione fallita per %s" % target)
            found = True
            break
    if not found:
        print("Funzione non trovata: %s" % target)
else:
    print("=== FUNZIONI (%d) ===" % fm.getFunctionCount())
    n = 0
    for f in fm.getFunctions(True):
        print("%s  %s" % (f.getEntryPoint(), f.getName()))
        n += 1
        if n >= 500:
            print("... (troncato a 500)")
            break
