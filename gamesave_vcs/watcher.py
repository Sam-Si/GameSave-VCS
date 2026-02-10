import time
import threading
from pathlib import Path
from .config import get_game_path
from .backup import get_save_hash, backup_save

class GameWatcher:
    def __init__(self, game_name, interval=5):
        self.game_name = game_name
        self.interval = interval
        self.running = False
        self.thread = None
        self.last_hash = None
        self.save_path = get_game_path(game_name)

    def start(self):
        if self.save_path is None:
            print("Game not found")
            return
        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        print(f"Started watcher for {self.game_name}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        print(f"Stopped watcher for {self.game_name}")

    def _watch_loop(self):
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
                current_hash = get_save_hash(save_path)
                if current_hash != self.last_hash:
                    print(f"Change detected in {self.game_name} save")
                    backup_save(self.game_name)
                    self.last_hash = current_hash
