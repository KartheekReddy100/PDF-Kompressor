from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List
import sys

from .ghostscript_finder import get_ghostscript_path
from .pdf_compressor import (
    Engine,
    Quality,
    auto_compress,
    choose_engine,
    default_output_path_for,
)


class PDFCompressorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Kompressor")
        self.geometry("720x520")
        self.minsize(680, 480)

        # State
        self.files: List[str] = []
        self.output_dir: str | None = None
        self.ghostscript_path: str | None = get_ghostscript_path()

        # UI
        self._build_ui()
        self._update_gs_status()

    def _build_ui(self) -> None:
        # Try to apply the EXE icon to the window (works well on Windows)
        try:
            if sys.platform.startswith("win"):
                # Use the executable's icon if available
                self.iconbitmap(sys.executable)
        except Exception:
            pass

        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        # Top controls
        top = ttk.Frame(root)
        top.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(top, text="Add Files", command=self.on_add_files).pack(side=tk.LEFT)
        ttk.Button(top, text="Add Folder", command=self.on_add_folder).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top, text="Remove Selected", command=self.on_remove_selected).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top, text="Clear", command=self.on_clear).pack(side=tk.LEFT, padx=(8, 0))

        # File list
        mid = ttk.Frame(root)
        mid.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(mid, selectmode=tk.EXTENDED)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=sb.set)

        # Options
        opts = ttk.LabelFrame(root, text="Options")
        opts.pack(fill=tk.X, pady=(8, 8))

        # Output directory
        out_row = ttk.Frame(opts)
        out_row.pack(fill=tk.X, pady=4)
        ttk.Label(out_row, text="Output folder (optional):").pack(side=tk.LEFT)
        self.output_dir_var = tk.StringVar()
        self.output_entry = ttk.Entry(out_row, textvariable=self.output_dir_var)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(out_row, text="Browse", command=self.on_choose_output_dir).pack(side=tk.LEFT)

        # Engine and quality
        eq_row = ttk.Frame(opts)
        eq_row.pack(fill=tk.X, pady=4)

        ttk.Label(eq_row, text="Engine:").pack(side=tk.LEFT)
        self.engine_var = tk.StringVar(value="auto")
        self.engine_combo = ttk.Combobox(eq_row, textvariable=self.engine_var, state="readonly")
        self.engine_combo["values"] = ("auto", "ghostscript", "basic")
        self.engine_combo.pack(side=tk.LEFT, padx=(8, 24))

        ttk.Label(eq_row, text="Quality:").pack(side=tk.LEFT)
        self.quality_var = tk.StringVar(value="balanced")
        self.quality_combo = ttk.Combobox(eq_row, textvariable=self.quality_var, state="readonly")
        self.quality_combo["values"] = ("extreme", "strong", "balanced", "high")
        self.quality_combo.pack(side=tk.LEFT, padx=(8, 0))

        # Ghostscript status
        self.gs_status = ttk.Label(opts, foreground="#666")
        self.gs_status.pack(fill=tk.X, pady=(4, 0))

        # Actions
        bottom = ttk.Frame(root)
        bottom.pack(fill=tk.X)
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 8))
        self.start_btn = ttk.Button(bottom, text="Start Compression", command=self.on_start)
        self.start_btn.pack(side=tk.LEFT)

        # Log
        log_frame = ttk.LabelFrame(root, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.log = tk.Text(log_frame, height=8, wrap="word")
        self.log.pack(fill=tk.BOTH, expand=True)

    # UI actions
    def on_add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF Files", "*.pdf")],
        )
        if not paths:
            return
        added = 0
        for p in paths:
            if p.lower().endswith(".pdf") and p not in self.files:
                self.files.append(p)
                self.listbox.insert(tk.END, p)
                added += 1
        if added:
            self._log(f"Added {added} file(s)")

    def on_add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select folder with PDFs")
        if not folder:
            return
        count = 0
        for name in os.listdir(folder):
            if not name.lower().endswith(".pdf"):
                continue
            p = os.path.join(folder, name)
            if os.path.isfile(p) and p not in self.files:
                self.files.append(p)
                self.listbox.insert(tk.END, p)
                count += 1
        self._log(f"Added {count} file(s) from folder")

    def on_remove_selected(self) -> None:
        sel = list(self.listbox.curselection())
        sel.reverse()  # remove bottom-up
        removed = 0
        for idx in sel:
            path = self.listbox.get(idx)
            self.listbox.delete(idx)
            if path in self.files:
                self.files.remove(path)
                removed += 1
        if removed:
            self._log(f"Removed {removed} file(s)")

    def on_clear(self) -> None:
        self.listbox.delete(0, tk.END)
        self.files.clear()
        self._log("Cleared file list")

    def on_choose_output_dir(self) -> None:
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.output_dir = d
            self.output_dir_var.set(d)

    def on_start(self) -> None:
        if not self.files:
            messagebox.showwarning("No files", "Please add at least one PDF file to compress.")
            return
        # Hint: extreme quality benefits greatly from Ghostscript
        try:
            if self.quality_var.get() == "extreme":
                eng = self.engine_var.get()
                gs = get_ghostscript_path()
                if eng in ("auto", "ghostscript") and not gs:
                    messagebox.showinfo(
                        "Ghostscript not found",
                        "Extreme quality achieves best results with Ghostscript.\n"
                        "Install Ghostscript or select Engine = Basic to proceed (quality impact).",
                    )
        except Exception:
            pass
        self._set_running(True)
        t = threading.Thread(target=self._run_compression, daemon=True)
        t.start()

    def _run_compression(self) -> None:
        try:
            engine: Engine = self.engine_var.get()  # type: ignore
            quality: Quality = self.quality_var.get()  # type: ignore

            compressor = choose_engine(engine)

            total = len(self.files)
            self._set_progress(0, total)

            for i, src in enumerate(self.files, start=1):
                out = default_output_path_for(src, self.output_dir or None)
                self._log(f"[{i}/{total}] Compressing: {src}")
                res = compressor(src, out, quality)  # type: ignore[arg-type]

                if res.ok:
                    try:
                        in_size = os.path.getsize(src)
                        out_size = os.path.getsize(out)
                        saved = in_size - out_size
                        pct = (saved / in_size * 100.0) if in_size > 0 else 0
                        self._log(
                            f"  ✔ {os.path.basename(out)} | saved {saved/1024:.1f} KB ({pct:.1f}%) via {res.engine}"
                        )
                    except Exception:
                        self._log(f"  ✔ Done via {res.engine}")
                else:
                    self._log(f"  ✖ Failed via {res.engine}: {res.message}")
                self._set_progress(i, total)

            self._log("All done.")
            self._on_done()
        finally:
            self._set_running(False)

    # Helpers
    def _set_running(self, running: bool) -> None:
        state = tk.DISABLED if running else tk.NORMAL
        for w in [
            self.engine_combo,
            self.quality_combo,
            self.output_entry,
            self.start_btn,
        ]:
            w.configure(state=state)

    def _set_progress(self, i: int, total: int) -> None:
        self.progress["maximum"] = max(total, 1)
        self.progress["value"] = i

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _on_done(self) -> None:
        try:
            self.bell()
        except Exception:
            pass
        messagebox.showinfo("Completed", "Compression finished.")

    def _update_gs_status(self) -> None:
        if self.ghostscript_path:
            self.gs_status.configure(text=f"Ghostscript detected: {self.ghostscript_path}")
        else:
            self.gs_status.configure(text="Ghostscript not found. Engine 'basic' will be used unless you install it.")


def main() -> None:
    app = PDFCompressorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
