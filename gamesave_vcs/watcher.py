import threading
import time
from pathlib import Path
from typing import Optional
# Local
from .backup import backup_save, get_save_hash
from .config import get_game_path

class GameWatcher:
    """Watcher for game save changes using polling + hash diff; triggers backup."""

    def __init__(self, game_name: str, interval: float | int = 5) -> None:
        """Init watcher; save_path from config (may be None if game unknown)."""
        self.game_name: str = game_name
        self.interval: float | int = interval
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.last_hash: Optional[str] = None
        self.save_path: Optional[str] = get_game_path(game_name)

    def start(self) -> None:
        """Start watcher thread if save_path valid."""
        if self.save_path is None:
            print("Game not found")
            return
        self.running = True
        self.thread = threading.Thread(
            target=self._watch_loop, daemon=True
        )
        self.thread.start()
        print(f"Started watcher for {self.game_name}")

    def stop(self) -> None:
        """Stop watcher and join thread."""
        self.running = False
        if self.thread:
            self.thread.join()
        print(f"Stopped watcher for {self.game_name}")

    def _watch_loop(self) -> None:
        """Internal loop: poll, hash compare (using get_save_hash), backup on change.
        Daemon, runs until stop().
        """
        if self.save_path is None:
            return
        save_path = Path(self.save_path)
        if not save_path.exists():
            print("Save path does not exist")
            return
        self.last_hash = get_save_hash(save_path)
        while self.running:
            time.sleep(self.interval)
            if save_path.exists():
                current_hash: str = get_save_hash(save_path)
                if current_hash != self.last_hash:
                    print(f"Change detected in {self.game_name} save")
                    backup_save(self.game_name)
                    self.last_hash = current_hash
