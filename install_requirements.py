import os
import subprocess
import sys


def install_requirements():
    """Install the modules listed in requirements.txt"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("All required packages installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while installing packages: {e}")
        sys.exit(1)


if __name__ == "__main__":
    install_requirements()
