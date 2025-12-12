import subprocess
import os
import re
from pathlib import Path

PS1_SCRIPT = Path(os.path.join(os.path.dirname(__file__), "copy_locked.ps1")).absolute()


def get_auth_key():
    key = None
    try:
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(PS1_SCRIPT)],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("❌ Erreur lors de l'exécution du script PowerShell :", e)
        exit(1)

    temp_file = Path(os.getenv("TEMP")) / "data2_copy"
    if not temp_file.exists():
        print(f"❌ Fichier copié non trouvé : {temp_file}")
        exit(1)

    try:
        with open(temp_file, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore")

        match = re.search(r"authkey=([a-zA-Z0-9%]+)", content)

        if match:
            key = match.group(1)
        else:
            print("❌ Authkey non trouvée.")
    finally:
        # Suppression du fichier temporaire dans tous les cas
        try:
            temp_file.unlink()
        except Exception as e:
            print(f"⚠️ Impossible de supprimer le fichier temporaire : {e}")
    return key


if __name__ == "__main__":
    auth_key = get_auth_key()
    if auth_key:
        print(f"✅ Authkey récupérée : {auth_key}")
    else:
        print("❌ Authkey non récupérée.")
