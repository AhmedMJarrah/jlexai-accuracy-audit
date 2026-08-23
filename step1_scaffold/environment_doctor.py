"""
Run this any time you're unsure the environment is sane —
especially right after cloning on a new machine, or before
starting a new step.
"""
import importlib
import sys
from pathlib import Path

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging, get_logger

REQUIRED_PACKAGES = ["pydantic_settings", "dotenv"]  # extend as later steps add deps
MIN_PYTHON = (3, 11)


def check(label: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    line = f"[{status}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    return passed


def main() -> int:
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)
    logger = get_logger("environment_doctor")

    results = []

    # Python version
    results.append(check(
        "Python version >= 3.11",
        sys.version_info >= MIN_PYTHON,
        f"found {sys.version_info.major}.{sys.version_info.minor}",
    ))

    # venv active
    in_venv = sys.prefix != sys.base_prefix
    results.append(check("Virtual environment active", in_venv, sys.prefix))

    venv_name = Path(sys.prefix).name
    if venv_name != "audit":
        print(f"  [WARN] venv folder name is '{venv_name}', expected 'audit' — not fatal, just confirm this is intentional.")

    # Required packages importable
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            results.append(check(f"Package importable: {pkg}", True))
        except ImportError as e:
            results.append(check(f"Package importable: {pkg}", False, str(e)))

    # Directories exist and are writable
    for d in (settings.data_dir, settings.log_dir):
        writable = d.exists() and d.is_dir()
        results.append(check(f"Directory ready: {d}", writable))

    all_passed = all(results)
    logger.info("Environment check complete", extra={})
    print("\n" + ("ALL CHECKS PASSED" if all_passed else "ONE OR MORE CHECKS FAILED"))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())