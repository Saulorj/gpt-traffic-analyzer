import subprocess
import sys

def test_cli_help_runs():
    result = subprocess.run([sys.executable, "main.py", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage" in result.stdout or "--lang" in result.stdout
