import os
import sys
import subprocess
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

# Run the checkin script
result = subprocess.run([sys.executable, str(Path(__file__).parent / "embys_checkin.py")], env=os.environ)
sys.exit(result.returncode)