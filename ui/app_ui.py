"""Main interface GUI component module.

Implements the CustomTkinter window layout, sidebar controls, asset tree, and log box.
"""

from pathlib import Path
from tkinter import filedialog, ttk
import tkinter as tk
from typing import Any, Dict, List, Optional, Union
import customtkinter as ctk  # type: ignore[import-untyped]
from core.archive_reader import RpaArchiveReader
from core.config import CATEGORY_FOLDERS, SUPPORTED_EXTENSIONS
from core.logger import logger
from core.scanner import AssetScanner
from core.settings import BaseSettings
from ui.preview import PreviewPanel
from workers.workers import ExtractionWorker, ScanWorker


class LogTextboxSink:
    """Redirects Loguru messages directly into a CTkTextbox."""

    def __init__(self, textbox: ctk.CTkTextbox) -> None:
        self.textbox = textbox

    def write(self, message: str) -> None:
        try:
            self.textbox.configure(state="normal")
            self.textbox.insert("end", message)
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        except Exception:
            pass

    def flush(self) -> None:
        pass


class RenPyExtractorApp(ctk.CTk):
    """Main window interface for the Ren'Py Asset Extraction Tool."""

    def __init__(self) -> None:
        super().__init__()

        # Configure window properties
        self.title("Ren'Py Asset Extraction Tool")
        self.geometry("1100x750")
        self.minsize(1000, 680)

        # Set default theme
        ctk.set_appearance_mode(BaseSettings.theme)
        ctk.set_default_color_theme("blue")

        # State managers
        self.scanner: Optional[Any] = None
        self.active_extraction_worker: Optional[ExtractionWorker] = None
        self.scanned_archives_readers: Dict[str, RpaArchiveReader] = {}

        # Set up UI grid layout
        self.grid_columnconfigure(0, weight=0)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # Main panel
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_panel()
        self._setup_style_treeview()
        self._connect_logger()

        logger.info("GUI loaded successfully.")

    def _setup_style_treeview(self) -> None:
        """Styles the standard Tkinter Treeview to match CustomTkinter theme."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Dark theme tree colors
        style.configure(
            "Treeview",
            background="#2b2b2b",
            fieldbackground="#2b2b2b",
            foreground="#e0e0e0",
            rowheight=25,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#1e1e1e",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", "#1f538d")],
            foreground=[("selected", "#ffffff")],
        )

    def _build_sidebar(self) -> None:
        """Constructs the sidebar controls frame."""
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(12, weight=1)  # Bottom spacer

        # Header Title
        title_lbl = ctk.CTkLabel(
            self.sidebar,
            text="Extraction Panel",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_lbl.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Input Path Browse
        input_lbl = ctk.CTkLabel(
            self.sidebar, text="Game Directory:", font=ctk.CTkFont(size=11, weight="bold")
        )
        input_lbl.grid(row=1, column=0, padx=20, pady=(10, 2), sticky="w")

        self.input_entry = ctk.CTkEntry(self.sidebar, placeholder_text="No folder selected", width=240)
        self.input_entry.grid(row=2, column=0, padx=20, pady=2)

        input_btn = ctk.CTkButton(
            self.sidebar, text="Browse Target", command=self._browse_input_dir, height=26
        )
        input_btn.grid(row=3, column=0, padx=20, pady=(2, 10))

        # Output Path Browse
        output_lbl = ctk.CTkLabel(
            self.sidebar, text="Output Directory:", font=ctk.CTkFont(size=11, weight="bold")
        )
        output_lbl.grid(row=4, column=0, padx=20, pady=(10, 2), sticky="w")

        self.output_entry = ctk.CTkEntry(self.sidebar, placeholder_text="No folder selected", width=240)
        self.output_entry.grid(row=5, column=0, padx=20, pady=2)
        if BaseSettings.output_dir:
            self.output_entry.insert(0, BaseSettings.output_dir)

        output_btn = ctk.CTkButton(
            self.sidebar, text="Browse Output", command=self._browse_output_dir, height=26
        )
        output_btn.grid(row=6, column=0, padx=20, pady=(2, 15))

        # Selective Extraction Filters Title
        filters_lbl = ctk.CTkLabel(
            self.sidebar, text="Filters / Selective Unpacking:", font=ctk.CTkFont(size=12, weight="bold")
        )
        filters_lbl.grid(row=7, column=0, padx=20, pady=(10, 2), sticky="w")

        # Category check buttons
        self.filter_vars: Dict[str, tk.BooleanVar] = {}
        row_idx = 8
        for cat in SUPPORTED_EXTENSIONS.keys():
            var = tk.BooleanVar(value=cat in BaseSettings.selected_categories)
            self.filter_vars[cat] = var
            chk = ctk.CTkCheckBox(
                self.sidebar,
                text=cat.capitalize(),
                variable=var,
                command=self._update_filters_settings,
                font=ctk.CTkFont(size=12),
            )
            chk.grid(row=row_idx, column=0, padx=30, pady=2, sticky="w")
            row_idx += 1

        # Overwrite Dropdown
        ow_lbl = ctk.CTkLabel(
            self.sidebar, text="Overwrite Mode:", font=ctk.CTkFont(size=11, weight="bold")
        )
        ow_lbl.grid(row=row_idx, column=0, padx=20, pady=(15, 2), sticky="w")
        row_idx += 1

        self.overwrite_dropdown = ctk.CTkOptionMenu(
            self.sidebar,
            values=["skip", "overwrite", "rename"],
            command=self._update_overwrite_settings,
            height=26,
            width=240,
        )
        self.overwrite_dropdown.set(BaseSettings.overwrite_mode)
        self.overwrite_dropdown.grid(row=row_idx, column=0, padx=20, pady=2)
        row_idx += 1

        # Fast Mode Checkbox
        self.fast_mode_var = tk.BooleanVar(value=BaseSettings.fast_mode)
        fast_chk = ctk.CTkCheckBox(
            self.sidebar,
            text="Fast Mode (Skip Metadata)",
            variable=self.fast_mode_var,
            command=self._update_fast_mode_setting,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        fast_chk.grid(row=row_idx, column=0, padx=20, pady=(10, 5), sticky="w")
        row_idx += 1

        # Scan & Unpack Actions
        self.scan_btn = ctk.CTkButton(
            self.sidebar, text="Scan Game Folder", command=self._start_scan, fg_color="#2b6cb0", hover_color="#2b5c8f"
        )
        self.scan_btn.grid(row=row_idx, column=0, padx=20, pady=(20, 5))
        row_idx += 1

        self.extract_btn = ctk.CTkButton(
            self.sidebar,
            text="Unpack Selected",
            command=self._start_extraction,
            fg_color="#38a169",
            hover_color="#2f855a",
            state="disabled",
        )
        self.extract_btn.grid(row=row_idx, column=0, padx=20, pady=5)
        row_idx += 1

        # Theme Selector (At Bottom)
        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["dark", "light", "system"],
            command=self._change_theme,
            height=24,
            width=120,
        )
        self.theme_menu.set(BaseSettings.theme)
        self.theme_menu.grid(row=13, column=0, padx=20, pady=15, sticky="w")

    def _build_main_panel(self) -> None:
        """Constructs the tree list, preview window, and logs console."""
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # 3 Rows:
        # Row 0: Tree (left) & Preview (right)
        # Row 1: Extraction progress bar / stats
        # Row 2: Logs console textbox
        self.main_panel.grid_rowconfigure(0, weight=3)
        self.main_panel.grid_rowconfigure(1, weight=0)
        self.main_panel.grid_rowconfigure(2, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        # Row 0 Split: Tree (Left) & Preview (Right)
        split_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        split_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        split_frame.grid_rowconfigure(0, weight=1)
        split_frame.grid_columnconfigure(0, weight=1)  # Tree
        split_frame.grid_columnconfigure(1, weight=1)  # Preview

        # Tree Container
        tree_container = ctk.CTkFrame(split_frame)
        tree_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Scrollbars
        ysb = ttk.Scrollbar(tree_container, orient="vertical")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb = ttk.Scrollbar(tree_container, orient="horizontal")
        xsb.grid(row=1, column=0, sticky="ew")

        # Treeview
        self.tree = ttk.Treeview(
            tree_container,
            columns=("type", "size"),
            show="tree headings",
            yscrollcommand=ysb.set,
            xscrollcommand=xsb.set,
        )
        self.tree.heading("#0", text="Game Assets Tree", anchor="w")
        self.tree.heading("type", text="Type", anchor="w")
        self.tree.heading("size", text="Size", anchor="w")
        self.tree.column("#0", minwidth=250, width=280)
        self.tree.column("type", width=70, minwidth=60, stretch=False)
        self.tree.column("size", width=80, minwidth=70, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")

        ysb.configure(command=self.tree.yview)
        xsb.configure(command=self.tree.xview)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Preview Container (Right)
        self.preview_panel = PreviewPanel(split_frame)
        self.preview_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Row 1: Progress Tracking
        self.progress_frame = ctk.CTkFrame(self.main_panel)
        self.progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 5))

        self.progress_lbl = ctk.CTkLabel(
            self.progress_frame,
            text="Ready. Select target and click Scan.",
            font=ctk.CTkFont(size=11),
        )
        self.progress_lbl.grid(row=1, column=0, sticky="w", padx=15, pady=(2, 10))

        self.speed_lbl = ctk.CTkLabel(
            self.progress_frame, text="", font=ctk.CTkFont(size=11, weight="bold")
        )
        self.speed_lbl.grid(row=1, column=1, sticky="e", padx=15, pady=(2, 10))

        # Row 2: Logs Console Textbox
        logs_container = ctk.CTkFrame(self.main_panel)
        logs_container.grid(row=2, column=0, sticky="nsew")
        logs_container.grid_rowconfigure(1, weight=1)
        logs_container.grid_columnconfigure(0, weight=1)

        logs_title = ctk.CTkLabel(
            logs_container, text="Application Logs Console", font=ctk.CTkFont(size=12, weight="bold")
        )
        logs_title.grid(row=0, column=0, sticky="w", padx=15, pady=2)

        self.log_textbox = ctk.CTkTextbox(
            logs_container,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#1a1a1a",
            text_color="#a0aec0",
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")

    def _connect_logger(self) -> None:
        """Directs Loguru streams to rolling text box."""
        logger.add(LogTextboxSink(self.log_textbox), format="{message}\n", level="INFO")

    def _browse_input_dir(self) -> None:
        folder = filedialog.askdirectory(title="Select Ren'Py Game Folder")
        if folder:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, folder)
            logger.info(f"Selected target game folder: {folder}")

    def _browse_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="Select Output Extraction Folder")
        if folder:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)
            BaseSettings.output_dir = folder
            BaseSettings.save()
            logger.info(f"Selected destination folder: {folder}")

    def _update_filters_settings(self) -> None:
        cats = [cat for cat, var in self.filter_vars.items() if var.get()]
        BaseSettings.selected_categories = cats
        BaseSettings.save()
        logger.debug(f"Filters updated: {cats}")

    def _update_overwrite_settings(self, mode: str) -> None:
        BaseSettings.overwrite_mode = mode
        BaseSettings.save()
        logger.debug(f"Overwrite mode set to: {mode}")

    def _update_fast_mode_setting(self) -> None:
        BaseSettings.fast_mode = self.fast_mode_var.get()
        BaseSettings.save()
        logger.debug(f"Fast mode set to: {BaseSettings.fast_mode}")

    def _change_theme(self, theme: str) -> None:
        BaseSettings.theme = theme
        BaseSettings.save()
        ctk.set_appearance_mode(theme)
        logger.info(f"Theme switched to: {theme}")

    def _start_scan(self) -> None:
        path_str = self.input_entry.get().strip()
        if not path_str:
            logger.warning("Please specify a target game path first.")
            return

        target_path = Path(path_str)
        if not target_path.exists():
            logger.error(f"Target path does not exist: {target_path}")
            return

        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.progress_lbl.configure(text="Scanning directory, please wait...")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        # Run scan inside a background thread
        # We scan all categories to list everything, but we will filter in extraction
        worker = ScanWorker(
            target_path=target_path,
            categories=None,  # Scan everything to build a complete asset tree
            completion_callback=self._on_scan_completed,
            error_callback=self._on_scan_error,
        )
        worker.start()

    def _on_scan_completed(self, scanner: AssetScanner) -> None:
        self.scanner = scanner
        self.scanned_archives_readers.clear()

        # Re-enable button on main thread
        self.after(0, self._populate_tree)

    def _on_scan_error(self, exc: Exception) -> None:
        def handle() -> None:
            self.scan_btn.configure(state="normal", text="Scan Game Folder")
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0)
            self.progress_lbl.configure(text=f"Scan failed: {exc}")
            logger.error(f"Scanner background thread encountered an error: {exc}")

        self.after(0, handle)

    def _populate_tree(self) -> None:
        """Builds tree items mapping archives and standalone assets."""
        self.scan_btn.configure(state="normal", text="Scan Game Folder")
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)

        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        self.preview_panel.clear()

        if not self.scanner:
            return

        # 1. Archives Section
        archives_node = self.tree.insert("", "end", text="Ren'Py Archives (.rpa)", open=True)
        for rpa in self.scanner.archives:
            rpa_node = self.tree.insert(
                archives_node,
                "end",
                text=rpa.name,
                values=("Archive", self._format_size(rpa.stat().st_size)),
                tags=("archive",),
            )

            # Pre-parse archive index to show nested files!
            try:
                reader = RpaArchiveReader(rpa)
                self.scanned_archives_readers[rpa.name] = reader
                index = reader.read_index()
                
                # Sort file list
                sorted_files = sorted(index.keys())
                for fpath in sorted_files:
                    # Calculate total size of entry chunks
                    file_size = sum(length for _, length, _ in index[fpath])
                    suffix = Path(fpath).suffix.lower()
                    
                    self.tree.insert(
                        rpa_node,
                        "end",
                        text=fpath,
                        values=(suffix, self._format_size(file_size)),
                        tags=("archive_inner", rpa.name),
                    )
            except Exception as e:
                logger.error(f"Failed to list archive contents for {rpa.name}: {e}")
                self.tree.insert(
                    rpa_node,
                    "end",
                    text=f"[Error loading index: {e}]",
                    values=("Error", "0 B"),
                )

        # 2. Standalone Assets Section
        standalone_node = self.tree.insert("", "end", text="Loose Standalone Assets", open=True)
        for cat, paths in self.scanner.standalone_assets.items():
            if not paths:
                continue
            cat_node = self.tree.insert(standalone_node, "end", text=cat.capitalize(), open=True)
            for path in sorted(paths, key=lambda p: p.name):
                self.tree.insert(
                    cat_node,
                    "end",
                    text=str(path.relative_to(self.scanner.target_path)),
                    values=(path.suffix.lower(), self._format_size(path.stat().st_size)),
                    tags=("standalone", str(path)),
                )

        total_files = sum(len(paths) for paths in self.scanner.standalone_assets.values())
        self.progress_lbl.configure(
            text=f"Scan completed. Found {len(self.scanner.archives)} archives and {total_files} loose files."
        )
        self.extract_btn.configure(state="normal")

    def _on_tree_select(self, event: Any) -> None:
        """Triggers immediately when an item in the tree is clicked."""
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        tags = self.tree.item(item, "tags")
        if not tags:
            self.preview_panel.clear()
            return

        tag_type = tags[0]
        self.preview_panel.clear()

        # Handle file preview
        if tag_type == "archive_inner":
            # File is inside an archive
            rpa_name = tags[1]
            fpath_in_rpa = self.tree.item(item, "text")
            reader = self.scanned_archives_readers.get(rpa_name)
            if reader:
                try:
                    # Read bytes in memory to show immediate preview
                    file_bytes = reader.read_file_bytes(fpath_in_rpa)
                    self._show_preview_of_bytes_or_path(file_bytes, fpath_in_rpa)
                except Exception as e:
                    logger.debug(f"Failed to preview archive file {fpath_in_rpa}: {e}")
                    self.preview_panel._show_error(f"Cannot read file preview.\n{e}")
        elif tag_type == "standalone":
            # Loose file on disk
            full_path = Path(tags[1])
            if full_path.exists() and full_path.is_file():
                self._show_preview_of_bytes_or_path(full_path, full_path.name)

    def _show_preview_of_bytes_or_path(
        self, data_or_path: Union[bytes, Path], filename: str
    ) -> None:
        """Determines category and routes target to preview panel."""
        suffix = Path(filename).suffix.lower()

        category = "other"
        for cat, exts in SUPPORTED_EXTENSIONS.items():
            if suffix in exts:
                category = cat
                break

        if category == "images":
            self.preview_panel.show_image(data_or_path)
        elif category == "audio":
            self.preview_panel.show_audio(data_or_path, filename)
        elif category == "video":
            self.preview_panel.show_video(data_or_path, filename)
        elif category == "scripts":
            self.preview_panel.show_script(data_or_path, filename)
        elif suffix in (".txt", ".json", ".xml", ".yaml", ".yml", ".csv"):
            self.preview_panel.show_text(data_or_path, filename)
        else:
            # Fallback standard info
            self.preview_panel.clear()
            self.preview_panel.placeholder.configure(text=f"No preview available for: {filename}")

    def _start_extraction(self) -> None:
        """Validates settings and launches background extraction worker."""
        if not self.scanner:
            logger.warning("Please scan a game folder first.")
            return

        # Toggle state if already running
        if self.active_extraction_worker:
            self.active_extraction_worker.cancel()
            self.extract_btn.configure(text="Cancelling...", state="disabled")
            return

        out_path_str = self.output_entry.get().strip()
        if not out_path_str:
            logger.error("Please specify an output directory first.")
            return

        out_dir = Path(out_path_str)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Cannot create output folder: {e}")
            return

        # Save settings state
        BaseSettings.output_dir = str(out_dir)
        BaseSettings.save()

        # Build category filters list
        selected_cats = [cat for cat, var in self.filter_vars.items() if var.get()]

        self.extract_btn.configure(text="Stop Unpacking", fg_color="#e53e3e", hover_color="#c53030")
        self.scan_btn.configure(state="disabled")
        self.progress_bar.set(0)

        # Launch Extraction Thread
        self.active_extraction_worker = ExtractionWorker(
            scanner=self.scanner,
            output_dir=out_dir,
            selected_categories=selected_cats,
            overwrite_mode=BaseSettings.overwrite_mode,
            fast_mode=BaseSettings.fast_mode,
            progress_callback=self._on_extract_progress,
            completion_callback=self._on_extract_completed,
            error_callback=self._on_extract_error,
        )
        self.active_extraction_worker.start()
        logger.info(f"Unpacking started targeting categories: {selected_cats}")

    def _on_extract_progress(self, progress: Dict[str, Any]) -> None:
        """Thread-safe UI callback updating extraction stats."""
        def update() -> None:
            percentage = progress["percentage"]
            self.progress_bar.set(percentage / 100)
            
            cur_file = progress["current_file"]
            if len(cur_file) > 40:
                cur_file = "..." + cur_file[-37:]

            self.progress_lbl.configure(
                text=f"Extracting: {cur_file} ({progress['current_index']}/{progress['total_items']})"
            )
            
            eta = progress["eta_seconds"]
            speed = progress["speed_files_per_sec"]
            self.speed_lbl.configure(text=f"{speed:.1f} file/s | ETA: {int(eta)}s")

        self.after(0, update)

    def _on_extract_completed(self, count: int) -> None:
        """Thread-safe UI callback finishing operations."""
        def handle() -> None:
            self.active_extraction_worker = None
            self.extract_btn.configure(
                text="Unpack Selected",
                fg_color="#38a169",
                hover_color="#2f855a",
                state="normal",
            )
            self.scan_btn.configure(state="normal")
            self.speed_lbl.configure(text="")
            self.progress_bar.set(1)

            if count >= 0:
                self.progress_lbl.configure(text=f"Extraction completed successfully. Extracted {count} files.")
                logger.info(f"Successfully extracted {count} assets. Metadata manifest saved.")
            else:
                self.progress_lbl.configure(text="Extraction cancelled by user.")
                logger.warning("Extraction process cancelled.")

        self.after(0, handle)

    def _on_extract_error(self, exc: Exception) -> None:
        def handle() -> None:
            self.active_extraction_worker = None
            self.extract_btn.configure(
                text="Unpack Selected",
                fg_color="#38a169",
                hover_color="#2f855a",
                state="normal",
            )
            self.scan_btn.configure(state="normal")
            self.speed_lbl.configure(text="")
            self.progress_bar.set(0)
            self.progress_lbl.configure(text=f"Extraction failed: {exc}")
            logger.error(f"Extraction worker failed: {exc}")

        self.after(0, handle)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Helper to format byte count into human-readable size labels."""
        if size_bytes == 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes //= 1024
        return f"{size_bytes} PB"
