"""Exercise every menu option with disposable records."""
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bank import Bank
from decimal import Decimal

with tempfile.TemporaryDirectory() as directory:
    output = Path(directory) / "statement.txt"
    commands = ["1", "C1", "Ravi", "9876543210", "ravi@example.com",
                "2", "S1", "C1", "1000", "100", "6",
                "3", "A1", "C1", "200", "500",
                "4", "S1", "100", "5", "S1", "50", "6", "S1", "A1", "100",
                "7", "S1", "8", "S1", "12", "9", "S1", "12", "2026", "YES",
                "10", "S1", "11", "S1", str(output), "12", "C1", "13", "14"]
    result = subprocess.run([sys.executable, "main.py", "--data-dir", directory],
                            input="\n".join(commands) + "\n", capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "Error:" not in result.stdout, result.stdout
    assert "Goodbye." in result.stdout
    bank = Bank(directory)
    assert bank.get_account("S1").balance == Decimal("1007.00")
    assert bank.get_account("A1").balance == Decimal("300.00")
    assert "INTEREST" in output.read_text(encoding="utf-8")
    print("CLI smoke test passed: all 14 menu choices, export and restart verified.")
