"""Live Memory Patching & Hot-Reloading Engine.

Provides process hooking mechanisms for in-memory RPA overrides and a Hot-Reloading Studio
watching asset folders for changes to reload modified sprites and sound effects live in-game.
"""

from pathlib import Path
import shutil
import time
from typing import Callable, List, Optional
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from core.logger import logger


class RenPyProcessHooker:
    """Manages process detection and in-memory RPA override hook generation."""

    @staticmethod
    def detect_running_renpy_games() -> List[Path]:
        """Detects active running Ren'Py game executable directory paths."""
        detected: List[Path] = []
        # Fallback process scanner checking common executable names
        try:
            import subprocess
            cmd = "tasklist /FO CSV /NH" if shutil.which("tasklist") else "ps -ef"
            out = subprocess.check_output(cmd, shell=True).decode("utf-8", errors="ignore")
            for line in out.splitlines():
                if ".exe" in line.lower() or "renpy" in line.lower():
                    # Filter system executables
                    clean_name = line.split(",")[0].strip('"')
                    if clean_name.lower() not in ("cmd.exe", "powershell.exe", "tasklist.exe", "pytest.exe", "python.exe"):
                        detected.append(Path(clean_name))
        except Exception as e:
            logger.warning(f"Process scanner check error: {e}")
        return detected

    @staticmethod
    def inject_rpa_override_hook(game_dir: Path, mod_assets_dir: Path) -> Path:
        """Injects live memory RPA searchpath override hook script into game directory."""
        game_path = game_dir / "game" if (game_dir / "game").exists() else game_dir
        game_path.mkdir(parents=True, exist_ok=True)

        hook_script_path = game_path / "00_v3_rpa_override.rpy"
        mod_dir_str = str(mod_assets_dir.resolve()).replace("\\", "/")

        rpy_code = f"""# Ren'Py Asset Extraction Tool v3.0 - In-Memory RPA Override Hook
init -999 python:
    import renpy.config
    import os
    override_dir = "{mod_dir_str}"
    if os.path.exists(override_dir) and override_dir not in renpy.config.searchpath:
        renpy.config.searchpath.insert(0, override_dir)
        print("[RenPyExtractor v3.0] Live RPA Override injected: " + override_dir)
"""

        with open(hook_script_path, "w", encoding="utf-8") as f:
            f.write(rpy_code)

        logger.info(f"Live RPA Override hook successfully injected into: {hook_script_path}")
        return hook_script_path

    @staticmethod
    def remove_override_hook(game_dir: Path) -> bool:
        """Removes injected RPA override hook script from target game directory."""
        game_path = game_dir / "game" if (game_dir / "game").exists() else game_dir
        hook_path = game_path / "00_v3_rpa_override.rpy"
        if hook_path.exists():
            hook_path.unlink()
            logger.info(f"Removed override hook: {hook_path}")
            return True
        return False


class HotReloadHandler(FileSystemEventHandler):
    """Watchdog event handler for monitoring asset modifications."""

    def __init__(self, callback: Optional[Callable[[Path], None]] = None) -> None:
        super().__init__()
        self.callback = callback

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            p = Path(event.src_path)
            logger.info(f"Asset modified: {p.name}")
            if self.callback:
                self.callback(p)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            p = Path(event.src_path)
            logger.info(f"New asset detected: {p.name}")
            if self.callback:
                self.callback(p)


class HotReloadStudio:
    """Monitors asset folders and triggers live hot-reloading updates."""

    def __init__(self, watch_dir: Path, on_change_cb: Optional[Callable[[Path], None]] = None) -> None:
        self.watch_dir = Path(watch_dir)
        self.on_change_cb = on_change_cb
        self.observer: Optional[Observer] = None

    def start(self) -> None:
        """Starts monitoring target asset folder for hot-reloading."""
        if not self.watch_dir.exists():
            self.watch_dir.mkdir(parents=True, exist_ok=True)

        handler = HotReloadHandler(callback=self.on_change_cb)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.watch_dir), recursive=True)
        self.observer.start()
        logger.info(f"Hot-Reloading Studio listening on: {self.watch_dir}")

    def stop(self) -> None:
        """Stops file watcher thread."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Hot-Reloading Studio stopped.")
