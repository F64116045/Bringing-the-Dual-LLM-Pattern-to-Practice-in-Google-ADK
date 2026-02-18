import subprocess
import sys


def main() -> int:
    scripts = [
        "scripts/run_slack.py",
        "scripts/run_travel.py",
        "scripts/run_workspace.py",
    ]

    failures = []
    for script in scripts:
        print(f"\n=== Running {script} ===")
        result = subprocess.run([sys.executable, script], check=False)
        if result.returncode != 0:
            failures.append((script, result.returncode))

    if failures:
        print("\n=== Completed with failures ===")
        for script, code in failures:
            print(f"{script}: exit code {code}")
        return 1

    print("\n=== All benchmark scripts completed successfully ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
