"""Installation helper. Prefer: pip install -r requirements.txt"""

import subprocess
import sys

PACKAGES = [
    ("cv2", "opencv-python>=4.8.0"),
    ("mediapipe", "mediapipe>=0.10.0"),
    ("numpy", "numpy>=1.24.0"),
    ("pygame", "pygame>=2.4.0"),
]


def installed(import_name: str) -> bool:
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def main():
    print("Viper / Nokia Snake — setup")
    ok = True
    for import_name, spec in PACKAGES:
        if installed(import_name):
            print(f"  ok  {import_name}")
            continue
        print(f"  installing {spec}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", spec])
        except subprocess.CalledProcessError:
            print(f"  failed {spec}")
            ok = False
    if ok:
        print("\nReady. Run:  python main.py")
    else:
        print("\nInstall remaining packages with:  pip install -r requirements.txt")


if __name__ == "__main__":
    main()
