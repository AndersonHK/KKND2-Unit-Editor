"""Windowed entry point: Windows launches .pyw files without a console."""
from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

if __name__ == "__main__":
    try:
        from kknd2_editor.app import main
        main()
    except Exception:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("KKND2 Unit Editor could not start", traceback.format_exc(), parent=root)
        root.destroy()
