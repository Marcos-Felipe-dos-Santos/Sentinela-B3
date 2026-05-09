import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config):
    """Redirect tmp_path base on Windows when the default dir is inaccessible.

    pytest stores temporary files under ``%TEMP%/pytest-of-<user>``.  On
    Windows this directory sometimes ends up with broken NTFS permissions
    (e.g. owned by SYSTEM after an elevated process), causing every test
    that uses the ``tmp_path`` fixture to fail with ``PermissionError``.

    This hook detects the problem and sets ``basetemp`` to a fallback
    directory that the current user can write to.
    """
    if config.option.basetemp is not None:
        return  # user already specified --basetemp, respect it

    if os.name != "nt":
        return  # only needed on Windows

    default_base = Path(tempfile.gettempdir()) / f"pytest-of-{os.getlogin()}"
    if default_base.exists():
        try:
            # Quick writability probe
            probe = default_base / ".sentinela_probe"
            probe.touch()
            probe.unlink()
            return  # directory is fine, nothing to do
        except PermissionError:
            pass  # fall through to workaround

    # Fallback: use a sibling directory we can create ourselves
    fallback = Path(tempfile.gettempdir()) / "sentinela_pytest"
    fallback.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(fallback)
