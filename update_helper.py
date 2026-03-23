import os
import sys
import time
import subprocess

def main():
    installer_path = sys.argv[1]

    # Wait for main app to fully close
    time.sleep(3)

    # Run installer
    subprocess.Popen(installer_path, shell=True)

if __name__ == "__main__":
    main()