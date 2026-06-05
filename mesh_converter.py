#!/usr/bin/env python3
"""Modern drag-and-drop GUI to batch-convert 3D mesh files via assimp (PySide6)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QListWidget, QComboBox, QCheckBox, QFileDialog, QProgressBar,
    QPlainTextEdit, QMessageBox, QSizePolicy,
)

OUTPUT_FORMATS = [
    ("obj", "OBJ — universal, opens in macOS QuickLook"),
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
    found = shutil.which("assimp")
    if found:
        return found
    for p in ("/opt/homebrew/bin/assimp", "/usr/local/bin/assimp", "/usr/bin/assimp"):
        if os.path.exists(p):
            return p
    return None


class DropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumHeight(140)
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #888;
                border-radius: 14px;
                background: rgba(127,127,127,0.06);
            }
            DropZone[hover="true"] {
                border-color: #2d7cf0;
                background: rgba(45,124,240,0.10);
            }
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        big = QLabel("Drop 3D files here")
        big.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        big.setFont(f)
        sub = QLabel("FBX / OBJ / STL / glTF / PLY / DAE / 3DS / X3D  —  or click to browse")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #777;")
        layout.addWidget(big)
        layout.addWidget(sub)
        self.setProperty("hover", False)

    def mousePressEvent(self, _):
        # Click-to-browse fallback
        self.files_dropped.emit([])  # special signal: empty list = open dialog

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.setProperty("hover", True)
            self.style().unpolish(self); self.style().polish(self)

    def dragLeaveEvent(self, _):
        self.setProperty("hover", False)
        self.style().unpolish(self); self.style().polish(self)

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        self.setProperty("hover", False)
        self.style().unpolish(self); self.style().polish(self)
        if paths:
            self.files_dropped.emit(paths)


class ConvertWorker(QThread):
    progress = Signal(int, int, str)   # (current_index, total, message)
    finished_ok = Signal(int, int, int)  # (ok, fail, skipped)

    def __init__(self, assimp_path, files, ext, out_dir_sel, overwrite):
        super().__init__()
        self.assimp_path = assimp_path
        self.files = files
        self.ext = ext
        self.out_dir_sel = out_dir_sel
        self.overwrite = overwrite

    def run(self):
        out_ext = "gltf" if self.ext == "gltf2" else ("dae" if self.ext == "collada" else self.ext)
        total = len(self.files)
        ok = fail = skipped = 0
        for i, src in enumerate(self.files, 1):
            src_path = Path(src)
            if self.out_dir_sel:
                dst = Path(self.out_dir_sel) / (src_path.stem + f".{out_ext}")
            else:
                dst = src_path.with_suffix(f".{out_ext}")
            if dst.exists() and not self.overwrite:
                self.progress.emit(i, total, f"skip (exists): {dst.name}")
                skipped += 1
                continue
            try:
                proc = subprocess.run(
                    [self.assimp_path, "export", str(src_path), str(dst), "-f", self.ext],
                    capture_output=True, text=True, timeout=600,
                )
                if proc.returncode == 0 and dst.exists():
                    self.progress.emit(i, total, f"✓ {src_path.name} → {dst.name}")
                    ok += 1
                else:
                    tail = (proc.stderr or proc.stdout or "unknown").strip().splitlines()
                    err = tail[-1] if tail else "unknown error"
                    self.progress.emit(i, total, f"✗ {src_path.name}: {err}")
                    fail += 1
            except Exception as e:
                self.progress.emit(i, total, f"✗ {src_path.name}: {e}")
                fail += 1
        self.finished_ok.emit(ok, fail, skipped)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mesh Converter")
        self.resize(820, 660)
        self.assimp_path = find_assimp()
        self.files = []
        self.out_dir_sel = ""
        self.worker = None
        self._build_ui()
        if self.assimp_path:
            self._log(f"assimp: {self.assimp_path}")
        else:
            self._log("⚠ assimp not found on PATH. Install it:  brew install assimp")
            self.convert_btn.setEnabled(False)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Mesh Converter")
        tf = QFont(); tf.setPointSize(20); tf.setBold(True)
        title.setFont(tf)
        sub = QLabel("Batch-convert 3D mesh files (FBX → OBJ and more) via assimp.")
        sub.setStyleSheet("color: #777;")
        root.addWidget(title)
        root.addWidget(sub)

        self.drop = DropZone()
        self.drop.files_dropped.connect(self._on_dropped)
        root.addWidget(self.drop)

        # File list with header
        list_header = QHBoxLayout()
        self.file_count_label = QLabel("Files: 0")
        list_header.addWidget(self.file_count_label)
        list_header.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self._remove_selected)
        list_header.addWidget(remove_btn)
        list_header.addWidget(clear_btn)
        root.addLayout(list_header)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setMinimumHeight(130)
        root.addWidget(self.list_widget)

        # Output controls
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output format:"))
        self.fmt_combo = QComboBox()
        for ext, desc in OUTPUT_FORMATS:
            self.fmt_combo.addItem(f"{ext}  —  {desc}", userData=ext)
        out_row.addWidget(self.fmt_combo, 1)
        root.addLayout(out_row)

        out_row2 = QHBoxLayout()
        out_row2.addWidget(QLabel("Output dir:"))
        self.out_dir_label = QLabel("(same folder as each input)")
        self.out_dir_label.setStyleSheet("color: #777;")
        out_row2.addWidget(self.out_dir_label, 1)
        choose_btn = QPushButton("Choose…")
        choose_btn.clicked.connect(self._choose_out_dir)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_out_dir)
        out_row2.addWidget(choose_btn)
        out_row2.addWidget(reset_btn)
        root.addLayout(out_row2)

        self.overwrite_check = QCheckBox("Overwrite existing output files")
        root.addWidget(self.overwrite_check)

        # Convert
        action_row = QHBoxLayout()
        self.convert_btn = QPushButton("Convert")
        cf = QFont(); cf.setPointSize(14); cf.setBold(True)
        self.convert_btn.setFont(cf)
        self.convert_btn.setMinimumHeight(40)
        self.convert_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.convert_btn.clicked.connect(self._start_convert)
        action_row.addWidget(self.convert_btn)
        root.addLayout(action_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)

        log_label = QLabel("Log")
        log_label.setStyleSheet("color: #777;")
        root.addWidget(log_label)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(140)
        root.addWidget(self.log_view)

    # ----- handlers -----

    def _on_dropped(self, paths):
        if not paths:
            # Empty list signals "click to browse" from DropZone
            self._add_files_dialog()
            return
        for p in paths:
            if os.path.isdir(p):
                for r, _d, fs in os.walk(p):
                    for n in fs:
                        if n.lower().rsplit(".", 1)[-1] in INPUT_EXTS:
                            self._add_file(os.path.join(r, n))
            elif os.path.isfile(p):
                ext = p.lower().rsplit(".", 1)[-1]
                if ext in INPUT_EXTS:
                    self._add_file(p)
                else:
                    self._log(f"skip (unsupported): {os.path.basename(p)}")

    def _add_files_dialog(self):
        types = "3D meshes (" + " ".join(f"*.{e}" for e in INPUT_EXTS) + ");;All (*)"
        paths, _ = QFileDialog.getOpenFileNames(self, "Pick mesh files", "", types)
        for p in paths:
            self._add_file(p)

    def _add_file(self, p):
        if p not in self.files:
            self.files.append(p)
            self.list_widget.addItem(p)
            self.file_count_label.setText(f"Files: {len(self.files)}")

    def _remove_selected(self):
        for item in self.list_widget.selectedItems():
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
            del self.files[row]
        self.file_count_label.setText(f"Files: {len(self.files)}")

    def _clear(self):
        self.files.clear()
        self.list_widget.clear()
        self.file_count_label.setText("Files: 0")

    def _choose_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Output directory")
        if d:
            self.out_dir_sel = d
            self.out_dir_label.setText(d)

    def _reset_out_dir(self):
        self.out_dir_sel = ""
        self.out_dir_label.setText("(same folder as each input)")

    def _log(self, msg):
        self.log_view.appendPlainText(msg)

    def _start_convert(self):
        if not self.files:
            QMessageBox.information(self, "Nothing to do", "Add files first (drag in or click the drop zone).")
            return
        if not self.assimp_path:
            return
        ext = self.fmt_combo.currentData()
        self.convert_btn.setEnabled(False)
        self.progress.setMaximum(len(self.files))
        self.progress.setValue(0)
        self.worker = ConvertWorker(
            self.assimp_path, list(self.files), ext, self.out_dir_sel, self.overwrite_check.isChecked()
        )
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished_ok.connect(self._on_worker_done)
        self.worker.start()

    def _on_worker_progress(self, i, total, msg):
        self._log(f"[{i}/{total}] {msg}")
        self.progress.setValue(i)

    def _on_worker_done(self, ok, fail, skipped):
        self._log(f"Done. ok={ok}  failed={fail}  skipped={skipped}")
        self.convert_btn.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
