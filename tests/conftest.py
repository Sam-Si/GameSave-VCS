import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from pytest import MonkeyPatch


@pytest.fixture(autouse=True)
def clean_config(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> Generator[None, None, None]:
    """Isolate each test with unique config dir to prevent duplicate game errors.
    Uses pytest tmp_path and monkeypatch for isolation.
    """
    test_home = tmp_path / "test_home"
    test_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("gamesave_vcs.config.Path.home", lambda: test_home)
    monkeypatch.setenv("HOME", str(test_home))
    # Cleanup after
    yield
    if test_home.exists():
        shutil.rmtree(test_home, ignore_errors=True)
