import pytest
from pathlib import Path
import shutil

@pytest.fixture(autouse=True)
def clean_config(tmp_path, monkeypatch):
    """Isolate each test with unique config dir to prevent duplicate game errors."""
    test_home = tmp_path / "test_home"
    monkeypatch.setattr("gamesave_vcs.config.Path.home", lambda: test_home)
    # Cleanup after
    yield
    if test_home.exists():
        shutil.rmtree(test_home, ignore_errors=True)
