import subprocess
import sys
from pathlib import Path
import difflib

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden"

DOS = "2026-01-16"

def run_command(cmd: str) -> str:
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)
    return result.stdout


def diff(name: str, expected: str, actual: str) -> None:
    if expected == actual:
        print(f"✅ {name}: OK")
        return

    print(f"❌ {name}: CHANGED")
    for line in difflib.unified_diff(
        expected.splitlines(),
        actual.splitlines(),
        fromfile=f"golden/{name}",
        tofile="current",
        lineterm="",
    ):
        print(line)
    sys.exit(1)


def main():
    # --- Console ---
    console_cmd = (
        f"python -m radiology_reports.capacity_reporting.cli "
        f"--dos {DOS}"
    )
    console_out = run_command(console_cmd)
    console_expected = (GOLDEN / "console_capacity.txt").read_text()

    diff("console_capacity.txt", console_expected, console_out)

    # --- Scheduling Email ---
    email_cmd = (
        f"python -m radiology_reports.capacity_reporting.cli "
        f"--dos {DOS} --email"
    )
    email_out = run_command(email_cmd)

    # IMPORTANT:
    # This assumes your CLI prints or returns HTML for scheduling.
    # If not, this step stays manual (email capture).
    email_expected = (GOLDEN / "scheduling_email.html").read_text()

    diff("scheduling_email.html", email_expected, email_out)


if __name__ == "__main__":
    main()
