# Antigravity Ghidra post-script: estrae funzioni + decompilato (prime N).
# Lanciato da analyzeHeadless con -postScript. Scrive in stdout un report leggibile.
# Usa l'API Ghidra (Jython). Niente modifiche al binary.
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

program = currentProgram
fm = program.getFunctionManager()
funcs = list(fm.getFunctions(True))
print("=== ANTIGRAVITY DECOMPILE REPORT ===")
print("File: " + program.getExecutablePath())
print("Totale funzioni: " + str(len(funcs)))

decomp = DecompInterface()
decomp.openProgram(program)
mon = ConsoleTaskMonitor()
N = 20
for i, f in enumerate(funcs):
    if i >= N:
        print("... (mostrate prime " + str(N) + " di " + str(len(funcs)) + ")")
        break
    print("\n--- FUNZIONE: " + f.getName() + " @ " + str(f.getEntryPoint()) + " ---")
    res = decomp.decompileFunction(f, 30, mon)
    if res and res.getDecompiledFunction():
        print(res.getDecompiledFunction().getC())
    else:
        print("(decompilazione non disponibile)")
decomp.dispose()
print("=== FINE REPORT ===")
