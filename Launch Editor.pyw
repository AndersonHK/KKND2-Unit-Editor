"""Windowed entry point: Windows launches .pyw files without a console."""
import tkinter as tk
from tkinter import messagebox
import traceback

if __name__ == "__main__":
    try:
        from kknd2_editor import main
        main()
    except Exception:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("KKND2 Unit Editor could not start", traceback.format_exc(), parent=root)
        root.destroy()
