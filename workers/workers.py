"""Background threading and worker execution module.

Implements non-blocking execution wrappers for folder scanning and asset extraction.
"""

import time
from pathlib import Path
from threading import Event, Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event, Thread, Lock
from typing import Any, Callable, Dict, List, Optional
from core.archive_reader import RpaArchiveReader
from core.logger import logger
from core.metadata import MetadataManager
from core.scanner import AssetScanner


class ExtractionWorker:
    """Manages file extraction in a separate thread with progress tracking and cancellation."""

    def __init__(
        self,
        scanner: AssetScanner,
        output_dir: Path,
        selected_categories: Optional[List[str]] = None,
        overwrite_mode: str = "skip",
        fast_mode: bool = True,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        completion_callback: Optional[Callable[[int], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Initializes the extraction worker.

        Args:
            scanner: An already initialized AssetScanner containing targets.
            output_dir: Folder to extract files to.
            selected_categories: Optional list of file category filters.
            overwrite_mode: Overwrite mode ('skip', 'overwrite', 'rename').
            fast_mode: If True, bypasses hash calculations and media specs checks.
            progress_callback: Callback receiving status dicts.
            completion_callback: Callback when finished.
            error_callback: Callback on exception.
        """
        self.scanner = scanner
        self.output_dir = Path(output_dir).resolve()
        self.selected_categories = selected_categories
        self.overwrite_mode = overwrite_mode
        self.fast_mode = fast_mode
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback

        self.cancel_event = Event()
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        """Launches the background thread."""
        self.cancel_event.clear()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """Requests cancellation of the extraction process."""
        self.cancel_event.set()
        logger.info("Extraction cancellation requested.")

    def _run(self) -> None:
        """Worker thread entrypoint."""
        try:
            start_time = time.time()
            total_extracted = 0

            # Initialize metadata manager
            meta_mgr = MetadataManager(self.output_dir)

            # Build list of archive files and filtered entries
            archives_to_process = self.scanner.archives
            standalone_assets = self.scanner.standalone_assets

            # Calculate total workload
            # 1. Total files inside archives that match categories
            archive_tasks = []
            for rpa in archives_to_process:
                if self.cancel_event.is_set():
                    break
                reader = RpaArchiveReader(rpa)
                index_dict = reader.read_index()
                matching_files = reader.get_filtered_files(self.selected_categories)
                for fname in matching_files:
                    size_bytes = sum(length for _, length, _ in index_dict[fname])
                    archive_tasks.append((reader, fname, rpa.name, size_bytes))

            # 2. Total standalone assets that match categories
            standalone_tasks = []
            for cat, paths in standalone_assets.items():
                if self.selected_categories is None or cat in self.selected_categories:
                    for path in paths:
                        try:
                            # Calculate relative path
                            rel_path = str(path.relative_to(self.scanner.target_path))
                        except ValueError:
                            rel_path = path.name

                        dest_path = (self.output_dir / rel_path).resolve()
                        size_bytes = path.stat().st_size
                        standalone_tasks.append((path, dest_path, rel_path, size_bytes))

            total_items = len(archive_tasks) + len(standalone_tasks)
            completed_count = 0
            lock = Lock()

            if total_items == 0:
                logger.info("No files matching filters were found to extract.")
                if self.completion_callback:
                    self.completion_callback(0)
                return

            # Retrieve thread count configuration
            from core.settings import BaseSettings
            thread_count = BaseSettings.thread_count

            # Helper tasks to run concurrently
            def process_archive_task(reader: RpaArchiveReader, fname: str, rpa_name: str, size: int) -> None:
                nonlocal total_extracted, completed_count
                if self.cancel_event.is_set():
                    return

                try:
                    extracted_path = reader.extract_file(
                        fname, self.output_dir, self.overwrite_mode
                    )

                    # Register file metadata
                    meta_mgr.register_file(
                        rel_path=fname,
                        original_source=rpa_name,
                        file_path=extracted_path,
                        fast_mode=self.fast_mode,
                        size_bytes=size,
                    )

                    with lock:
                        total_extracted += 1
                        completed_count += 1
                        cur_idx = completed_count

                    self._report_progress(
                        current_index=cur_idx,
                        total_items=total_items,
                        current_file=fname,
                        start_time=start_time,
                    )
                except Exception as ex:
                    logger.error(f"Failed to extract {fname} from {rpa_name}: {ex}")

            def process_standalone_task(path: Path, dest_path: Path, rel_path: str, size: int) -> None:
                nonlocal total_extracted, completed_count
                if self.cancel_event.is_set():
                    return

                try:
                    # Handle copy if not already there
                    if not dest_path.exists() or self.overwrite_mode == "overwrite":
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        import shutil
                        shutil.copy2(path, dest_path)

                    # Register file metadata
                    meta_mgr.register_file(
                        rel_path=rel_path,
                        original_source="standalone",
                        file_path=dest_path,
                        fast_mode=self.fast_mode,
                        size_bytes=size,
                    )

                    with lock:
                        total_extracted += 1
                        completed_count += 1
                        cur_idx = completed_count

                    self._report_progress(
                        current_index=cur_idx,
                        total_items=total_items,
                        current_file=path.name,
                        start_time=start_time,
                    )
                except Exception as ex:
                    logger.error(f"Failed to copy standalone file {path.name}: {ex}")

            # Run extraction tasks in parallel using thread pool
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = []
                for reader, fname, rpa_name, size in archive_tasks:
                    futures.append(executor.submit(process_archive_task, reader, fname, rpa_name, size))
                for path, dest_path, rel_path, size in standalone_tasks:
                    futures.append(executor.submit(process_standalone_task, path, dest_path, rel_path, size))

                # Wait for all tasks to complete while monitoring cancellation
                for future in as_completed(futures):
                    if self.cancel_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

            # Save metadata report if not cancelled
            if not self.cancel_event.is_set():
                meta_mgr.save()

            elapsed = time.time() - start_time
            logger.info(
                f"Extraction finished. Extracted {total_extracted}/{total_items} items in {elapsed:.2f}s."
            )

            if self.completion_callback:
                self.completion_callback(total_extracted if not self.cancel_event.is_set() else -1)

        except Exception as e:
            logger.error(f"Error in extraction background thread: {e}")
            if self.error_callback:
                self.error_callback(e)

    def _report_progress(
        self, current_index: int, total_items: int, current_file: str, start_time: float
    ) -> None:
        """Fires progress callback calculating rate and remaining times."""
        if not self.progress_callback:
            return

        elapsed = time.time() - start_time
        speed = current_index / elapsed if elapsed > 0 else 0.0
        eta = (total_items - current_index) / speed if speed > 0 else 0.0

        self.progress_callback(
            {
                "current_index": current_index,
                "total_items": total_items,
                "current_file": current_file,
                "percentage": (current_index / total_items) * 100,
                "speed_files_per_sec": speed,
                "eta_seconds": eta,
            }
        )


class ScanWorker:
    """Executes directory scanning inside a background thread."""

    def __init__(
        self,
        target_path: Path,
        categories: Optional[List[str]] = None,
        completion_callback: Optional[Callable[[AssetScanner], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Initializes the scan worker."""
        self.target_path = target_path
        self.categories = categories
        self.completion_callback = completion_callback
        self.error_callback = error_callback
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        """Launches the thread."""
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            scanner = AssetScanner(self.target_path)
            # Scan files matching categories
            scanner.scan(self.categories)
            if self.completion_callback:
                self.completion_callback(scanner)
        except Exception as e:
            logger.error(f"Error scanning directory {self.target_path}: {e}")
            if self.error_callback:
                self.error_callback(e)
