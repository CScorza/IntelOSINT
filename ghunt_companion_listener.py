import os
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    py = root / ".venv" / "Scripts" / "python.exe"
    ghunt_main = root / "GHunt" / "main.py"

    if not py.exists():
        print(f"[GHunt] Python .venv non trovato: {py}")
        input("Premi INVIO per chiudere...")
        return 1

    if not ghunt_main.exists():
        print(f"[GHunt] GHunt main.py non trovato: {ghunt_main}")
        input("Premi INVIO per chiudere...")
        return 1

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["LC_ALL"] = "C.UTF-8"
    env["LANG"] = "C.UTF-8"

    print("[GHunt] Pulizia sessione precedente...")
    subprocess.run(
        [str(py), str(ghunt_main), "login", "--clean"],
        cwd=str(root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    print("[GHunt] Avvio listener Companion su 127.0.0.1:60067...")
    print("[GHunt] Ora usa l'estensione GHunt Companion nel browser.")
    proc = subprocess.Popen(
        [str(py), str(ghunt_main), "login"],
        cwd=str(root),
        env=env,
        stdin=subprocess.PIPE,
        text=True,
    )
    try:
        proc.stdin.write("1\n")
        proc.stdin.flush()
        proc.stdin.close()
    except Exception:
        pass

    return proc.wait()


if __name__ == "__main__":
    raise SystemExit(main())
