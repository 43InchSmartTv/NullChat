import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path

from nullchat.autocomplete.engine import AutocompleteEngine

REPO_ROOT = Path(__file__).resolve().parents[2]

C_MAIN_BG = "#FFFFFF"
C_BTN_BG = "#333333"
C_BTN_FG = "#FFFFFF"


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, vocab_counts, current_backend, set_engine):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("420x220")
        self.configure(bg=C_MAIN_BG)
        self.transient(parent)

        self.vocab_counts = vocab_counts
        self.set_engine = set_engine
        self._bench_proc = None

        tk.Label(self, text="Autocomplete structure", font=("Segoe UI", 11, "bold"),
                 bg=C_MAIN_BG).pack(anchor="w", padx=20, pady=(15, 5))

        self.backend_var = tk.StringVar(value=current_backend)
        row = tk.Frame(self, bg=C_MAIN_BG)
        row.pack(anchor="w", padx=20)
        for label, value in (("Trie", "trie"), ("Ternary Search Tree", "tst")):
            tk.Radiobutton(row, text=label, value=value, variable=self.backend_var,
                           bg=C_MAIN_BG, font=("Segoe UI", 10),
                           command=self._switch_backend).pack(side=tk.LEFT, padx=(0, 15))

        self.status = tk.Label(self, text="", font=("Segoe UI", 9),
                               bg=C_MAIN_BG, fg="#666666")
        self.status.pack(anchor="w", padx=20, pady=(5, 10))

        tk.Button(self, text="Run Trie vs TST Benchmark", font=("Segoe UI", 10, "bold"),
                  bg=C_BTN_BG, fg=C_BTN_FG, relief=tk.FLAT, padx=15, pady=6,
                  command=self._run_benchmark).pack(padx=20, pady=5, anchor="w")

    def _switch_backend(self):
        backend = self.backend_var.get()

        def rebuild():
            engine = AutocompleteEngine.from_counts(self.vocab_counts, backend=backend)
            self.after(0, lambda: self._apply_engine(engine, backend))

        threading.Thread(target=rebuild, daemon=True).start()

    def _apply_engine(self, engine, backend):
        self.set_engine(engine, backend)
        self.status.config(text=f"autocomplete now using: {backend}")

    def _run_benchmark(self):
        if self._bench_proc is not None:
            return
        self.status.config(text="running benchmark...")
        self._bench_proc = subprocess.Popen(
            [sys.executable, "-m", "benchmarks.benchmark_autocomplete"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=REPO_ROOT,
        )
        self.after(500, self._poll_benchmark)

    def _poll_benchmark(self):
        if self._bench_proc.poll() is None:
            self.after(500, self._poll_benchmark)
            return
        output = self._bench_proc.stdout.read()
        self._bench_proc = None
        self.status.config(text="benchmark finished")
        self._show_results(output)

    def _show_results(self, output):
        popup = tk.Toplevel(self)
        popup.title("Benchmark Results")
        popup.configure(bg=C_MAIN_BG)
        text = tk.Text(popup, font=("Consolas", 10), width=75, height=14,
                       bg=C_MAIN_BG, relief=tk.FLAT)
        text.insert("1.0", output)
        text.config(state="disabled")
        text.pack(padx=15, pady=15)
