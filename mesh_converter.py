#!/usr/bin/env python3
"""Simple drag-and-drop GUI to batch-convert 3D mesh files via assimp."""

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import Tk, ttk, filedialog, messagebox, StringVar, BooleanVar, END
from tkinter.scrolledtext import ScrolledText

OUTPUT_FORMATS = [
    ("obj", "OBJ — universal, opens in mac QuickLook"),
    ("gltf2", "glTF 2.0 — modern web/AR standard"),
    ("stl", "STL — 3D printing"),
    ("ply", "PLY — point clouds / scans"),
    ("fbx", "FBX — Autodesk interchange"),
    ("collada", "DAE (Collada)"),
    ("x3d", "X3D"),
    ("3ds", "3DS"),
]

INPUT_EXTS = ("fbx", "obj", "stl", "ply", "gltf", "glb", "dae", "3ds", "x3d", "blend")


def find_assimp():
    return shutil.which("assimp")


class App:
    def __init__(self, root):
        self.root = root
        root.title("Mesh Converter")
        root.geometry("720x560")

        self.assimp_path = find_assimp()
        self.files = []
        self.out_dir = StringVar(value="(same as input)")
        self.fmt = StringVar(value=OUTPUT_FORMATS[0][0])
        self.overwrite = BooleanVar(value=False)

        self._build_ui()

        if not self.assimp_path:
            self.log("⚠ assimp not found. Install it first:  brew install assimp")
            self.convert_btn.config(state="disabled")
        else:
            self.log(f"assimp: {self.assimp_path}")

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)
        ttk.Button(top, text="Add files…", command=self.add_files).pack(side="left")
        ttk.Button(top, text="Add folder…", command=self.add_folder).pack(side="left", padx=4)
        ttk.Button(top, text="Clear", command=self.clear_files).pack(side="left")

        list_frame = ttk.LabelFrame(self.root, text="Input files")
        list_frame.pack(fill="both", expand=True, **pad)
        self.listbox_frame = ttk.Frame(list_frame)
        self.listbox_frame.pack(fill="both", expand=True, padx=4, pady=4)
        from tkinter import Listbox, Scrollbar
        sb = Scrollbar(self.listbox_frame, orient="vertical")
        self.listbox = Listbox(self.listbox_frame, selectmode="extended", yscrollcommand=sb.set)
        sb.config(command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        ttk.Button(list_frame, text="Remove selected", command=self.remove_selected).pack(pady=4)

        opts = ttk.LabelFrame(self.root, text="Output")
        opts.pack(fill="x", **pad)

        row1 = ttk.Frame(opts)
        row1.pack(fill="x", padx=4, pady=4)
        ttk.Label(row1, text="Format:").pack(side="left")
        fmt_menu = ttk.Combobox(
            row1, textvariable=self.fmt, state="readonly",
            values=[f"{ext}  —  {desc}" for ext, desc in OUTPUT_FORMATS], width=46,
        )
        fmt_menu.current(0)
        fmt_menu.pack(side="left", padx=4)
        fmt_menu.bind("<<ComboboxSelected>>", self._on_fmt_change)

        row2 = ttk.Frame(opts)
        row2.pack(fill="x", padx=4, pady=4)
        ttk.Label(row2, text="Output dir:").pack(side="left")
        ttk.Label(row2, textvariable=self.out_dir, foreground="#555").pack(side="left", padx=4)
        ttk.Button(row2, text="Choose…", command=self.choose_out_dir).pack(side="left")
        ttk.Button(row2, text="Reset to same as input", command=self.reset_out_dir).pack(side="left", padx=4)

        row3 = ttk.Frame(opts)
        row3.pack(fill="x", padx=4, pady=4)
        ttk.Checkbutton(row3, text="Overwrite existing files", variable=self.overwrite).pack(side="left")

        actions = ttk.Frame(self.root)
        actions.pack(fill="x", **pad)
        self.convert_btn = ttk.Button(actions, text="Convert", command=self.start_convert)
        self.convert_btn.pack(side="left")
        self.progress = ttk.Progressbar(actions, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=8)

        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_view = ScrolledText(log_frame, height=8, state="disabled")
        self.log_view.pack(fill="both", expand=True, padx=4, pady=4)

    def _on_fmt_change(self, _):
        sel = self.fmt.get().split("  —  ")[0]
        self.fmt.set(sel)

    def add_files(self):
        types = [("3D mesh files", " ".join(f"*.{e}" for e in INPUT_EXTS)), ("All", "*.*")]
        paths = filedialog.askopenfilenames(title="Pick mesh files", filetypes=types)
        for p in paths:
            self._add_file(p)

    def add_folder(self):
        d = filedialog.askdirectory(title="Pick a folder (scans recursively)")
        if not d:
            return
        for root, _dirs, fnames in os.walk(d):
            for n in fnames:
                if n.lower().rsplit(".", 1)[-1] in INPUT_EXTS:
                    self._add_file(os.path.join(root, n))

    def _add_file(self, path):
        if path not in self.files:
            self.files.append(path)
            self.listbox.insert(END, path)

    def remove_selected(self):
        for idx in reversed(self.listbox.curselection()):
            del self.files[idx]
            self.listbox.delete(idx)

    def clear_files(self):
        self.files.clear()
        self.listbox.delete(0, END)

    def choose_out_dir(self):
        d = filedialog.askdirectory(title="Pick output directory")
        if d:
            self.out_dir.set(d)

    def reset_out_dir(self):
        self.out_dir.set("(same as input)")

    def log(self, msg):
        self.log_view.config(state="normal")
        self.log_view.insert(END, msg + "\n")
        self.log_view.see(END)
        self.log_view.config(state="disabled")

    def start_convert(self):
        if not self.files:
            messagebox.showinfo("Nothing to do", "Add some files first.")
            return
        if not self.assimp_path:
            return
        self.convert_btn.config(state="disabled")
        t = threading.Thread(target=self._convert_all, daemon=True)
        t.start()

    def _convert_all(self):
        ext = self.fmt.get().split("  —  ")[0].strip()
        # assimp's output extension differs from its format id for gltf2
        out_ext = "gltf" if ext == "gltf2" else ("dae" if ext == "collada" else ext)
        out_dir_sel = self.out_dir.get()
        total = len(self.files)
        self.progress.config(maximum=total, value=0)
        ok = fail = skipped = 0
        for i, src in enumerate(self.files, 1):
            src_path = Path(src)
            if out_dir_sel == "(same as input)":
                dst = src_path.with_suffix(f".{out_ext}")
            else:
                dst = Path(out_dir_sel) / (src_path.stem + f".{out_ext}")
            if dst.exists() and not self.overwrite.get():
                self.log(f"[{i}/{total}] skip (exists): {dst.name}")
                skipped += 1
                self.progress.config(value=i)
                continue
            try:
                proc = subprocess.run(
                    [self.assimp_path, "export", str(src_path), str(dst), "-f", ext],
                    capture_output=True, text=True, timeout=600,
                )
                if proc.returncode == 0 and dst.exists():
                    self.log(f"[{i}/{total}] ✓ {src_path.name} → {dst.name}")
                    ok += 1
                else:
                    err = (proc.stderr or proc.stdout or "unknown").strip().splitlines()[-1]
                    self.log(f"[{i}/{total}] ✗ {src_path.name}: {err}")
                    fail += 1
            except Exception as e:
                self.log(f"[{i}/{total}] ✗ {src_path.name}: {e}")
                fail += 1
            self.progress.config(value=i)
        self.log(f"Done. ok={ok}  failed={fail}  skipped={skipped}")
        self.convert_btn.config(state="normal")


def main():
    root = Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
