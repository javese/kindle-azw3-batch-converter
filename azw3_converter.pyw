import os
from pathlib import Path
import queue
import sys
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


ENGINE = Path(__file__).resolve().parent / "azw3-engine"
KINDLING = ENGINE / "kindling-cli-windows.exe"
EPUB_TO_AZW3 = ENGINE / "epub3-kindle" / "epub3-kindle.exe"
UNPACK = ENGINE / "KindleUnpack-master" / "lib" / "kindleunpack.py"
sys.path.insert(0, str(ENGINE))
from tkinterdnd2 import COPY, DND_FILES, REFUSE_DROP, TkinterDnD


def run_engine(*arguments):
    result = subprocess.run(
        [str(argument) for argument in arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    log = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode:
        raise RuntimeError(log or f"Engine exit code {result.returncode}")
    return log


def convert_book(source, destination):
    with tempfile.TemporaryDirectory(prefix=".azw3-", dir=destination) as temporary:
        workspace = Path(temporary)
        staged = workspace / "converted.azw3"
        book = source
        if source.suffix.lower() == ".mobi":
            unpacked = workspace / "unpacked"
            python = Path(sys.executable).with_name("python.exe")
            log = run_engine(python, UNPACK, "--epub_version=A", source, unpacked)
            book = next((unpacked / "mobi8").glob("*.epub"), None)
            if book is None:
                book = next((unpacked / "mobi7").glob("*.opf"), None)
                if book is None:
                    raise RuntimeError(log or "无法从 MOBI 提取电子书。")
                intermediate = workspace / "legacy.epub"
                run_engine(KINDLING, "epub2", book, "-o", intermediate)
                book = intermediate
        log = run_engine(EPUB_TO_AZW3, book, "-o", staged)
        if not staged.is_file():
            raise RuntimeError(log or "The conversion engine did not create a file.")
        with staged.open("rb") as file:
            header = file.read(86)
            start = int.from_bytes(header[78:82], "big")
            if len(header) < 86 or header[60:68] != b"BOOKMOBI" or start < 86:
                raise RuntimeError("Invalid Kindle book header.")
            file.seek(start + 16)
            mobi = file.read(24)
            if len(mobi) < 24 or mobi[:4] != b"MOBI" or int.from_bytes(mobi[20:24], "big") != 8:
                raise RuntimeError("The output is not a KF8 / AZW3 book.")
        number = 1
        target = destination / f"{source.stem}.azw3"
        while True:
            try:
                staged.rename(target)
                return target
            except FileExistsError:
                number += 1
                target = destination / f"{source.stem} ({number}).azw3"


class ConverterApp:
    def __init__(self, window):
        self.window = window
        self.jobs = {}
        self.details = {}
        self.events = queue.Queue()
        self.running = False
        self.destination = tk.StringVar()
        self.status = tk.StringVar(value="将 EPUB 或 MOBI 文件拖到列表，或点击「添加文件」。")

        window.title("Kindle 批量转换 · AZW3")
        window.minsize(720, 460)
        window.geometry("850x530")
        window.state("zoomed")
        window.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(window)
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 19, "bold"))
        style.configure("Treeview", rowheight=27)

        body = ttk.Frame(window, padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Kindle 批量转换", style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text="EPUB / MOBI → AZW3").pack(anchor="w", pady=(3, 14))

        toolbar = ttk.Frame(body)
        toolbar.pack(fill="x", pady=(0, 8))
        self.controls = []
        for label, callback in (
            ("添加文件", self.add_files),
            ("移除所选", self.remove_selected),
            ("清空列表", self.clear),
        ):
            button = ttk.Button(toolbar, text=label, command=callback)
            button.pack(side="left", padx=(0, 6))
            self.controls.append(button)

        listing = ttk.Frame(body)
        listing.pack(fill="both", expand=True)
        self.table = ttk.Treeview(listing, columns=("book", "state"), show="headings")
        self.table.heading("book", text="源文件")
        self.table.heading("state", text="转换状态")
        self.table.column("book", width=520)
        self.table.column("state", width=120, stretch=False)
        scrollbar = ttk.Scrollbar(listing, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.table.pack(side="left", fill="both", expand=True)
        self.table.bind("<Double-1>", self.show_details)
        self.table.drop_target_register(DND_FILES)
        self.table.dnd_bind("<<DropEnter>>", self.drop_action)
        self.table.dnd_bind("<<DropPosition>>", self.drop_action)
        self.table.dnd_bind("<<Drop>>", self.drop_files)

        self.path_row(body, "输出目录", self.destination, self.choose_destination)
        self.progress = ttk.Progressbar(body, mode="determinate")
        self.progress.pack(fill="x", pady=(14, 7))

        footer = ttk.Frame(body)
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status).pack(side="left")
        self.start_button = ttk.Button(footer, text="开始转换", command=self.start)
        self.start_button.pack(side="right")
        ttk.Button(footer, text="打开输出目录", command=self.open_destination).pack(
            side="right", padx=(0, 8)
        )

    def path_row(self, parent, title, variable, callback):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text=title, width=13).pack(side="left")
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True)
        button = ttk.Button(row, text="浏览…", command=callback)
        button.pack(side="right", padx=(8, 0))
        self.controls.extend((entry, button))

    def add_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("电子书", "*.epub *.mobi"), ("所有文件", "*.*")]
        )
        if files:
            self.add_paths(files)

    def drop_action(self, event):
        return REFUSE_DROP if self.running else COPY

    def drop_files(self, event):
        if self.running:
            return REFUSE_DROP
        self.add_paths(self.window.tk.splitlist(event.data))
        return COPY

    def add_paths(self, files):
        existing = set(self.jobs.values())
        added = 0
        for filename in files:
            source = Path(filename).resolve()
            if source.suffix.lower() not in {".epub", ".mobi"} or source in existing or not source.is_file():
                continue
            row = self.table.insert("", "end", values=(str(source), "等待转换"))
            self.jobs[row] = source
            existing.add(source)
            added += 1
            if not self.destination.get():
                self.destination.set(str(source.parent))
        if added:
            self.status.set(f"已添加 {added} 本，列表中共有 {len(self.jobs)} 本。")
        else:
            self.status.set("没有可添加的新 EPUB 或 MOBI 文件。")

    def remove_selected(self):
        for row in self.table.selection():
            self.table.delete(row)
            self.jobs.pop(row)
            self.details.pop(row, None)
        self.status.set(f"列表中有 {len(self.jobs)} 本书。")

    def clear(self):
        for row in self.jobs:
            self.table.delete(row)
        self.jobs.clear()
        self.details.clear()
        self.progress["value"] = 0
        self.status.set("将 EPUB 或 MOBI 文件拖到列表，或点击「添加文件」。")

    def choose_destination(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination.set(folder)

    def open_destination(self):
        folder = self.destination.get().strip()
        if folder and Path(folder).is_dir():
            os.startfile(folder)
        else:
            messagebox.showinfo("输出目录", "请选择一个存在的输出目录。")

    def start(self):
        if not self.jobs:
            messagebox.showinfo("批量转换", "请先添加电子书。")
            return
        if not all(path.is_file() for path in (KINDLING, EPUB_TO_AZW3, UNPACK)):
            messagebox.showerror("缺少转换组件", "请将 azw3-engine 文件夹放在应用旁边。")
            return
        folder = self.destination.get().strip()
        if not folder:
            messagebox.showinfo("输出目录", "请选择输出目录。")
            return
        destination = Path(folder).resolve()
        if not destination.is_dir():
            messagebox.showerror("输出目录", "请输入一个存在的输出目录。")
            return
        self.running = True
        for control in (*self.controls, self.start_button):
            control.configure(state="disabled")
        self.progress.configure(value=0, maximum=len(self.jobs))
        self.details.clear()
        for row in self.jobs:
            self.table.set(row, "state", "等待转换")
        threading.Thread(
            target=self.process, args=(destination, tuple(self.jobs.items())),
            daemon=True,
        ).start()
        self.window.after(80, self.update_progress)

    def process(self, destination, jobs):
        failures = 0
        for row, source in jobs:
            self.events.put(("active", row, source.name))
            try:
                output = convert_book(source, destination)
            except (OSError, RuntimeError) as error:
                failures += 1
                self.events.put(("result", row, ("失败", str(error))))
            else:
                self.events.put(("result", row, ("完成", str(output))))
        self.events.put(("done", len(jobs), failures))

    def update_progress(self):
        while not self.events.empty():
            event, row, data = self.events.get_nowait()
            if event == "active":
                self.table.set(row, "state", "转换中")
                self.status.set(f"正在转换第 {int(self.progress['value']) + 1} / {len(self.jobs)} 本")
            elif event == "result":
                state, detail = data
                self.table.set(row, "state", state)
                self.details[row] = detail
                self.progress["value"] += 1
            else:
                self.running = False
                for control in (*self.controls, self.start_button):
                    control.configure(state="normal")
                self.status.set(f"成功 {row - data} 本，失败 {data} 本。双击结果查看详情。")
        if self.running:
            self.window.after(80, self.update_progress)

    def show_details(self, event):
        row = self.table.identify_row(event.y)
        if row not in self.details:
            return
        dialog = tk.Toplevel(self.window)
        dialog.title(self.jobs[row].name)
        dialog.geometry("680x310")
        text = tk.Text(dialog, wrap="word", padx=12, pady=12)
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.details[row])
        text.configure(state="disabled")

    def close(self):
        if self.running:
            messagebox.showinfo("转换中", "请等待当前批次完成后关闭窗口。")
        else:
            self.window.destroy()


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    ConverterApp(root)
    root.mainloop()
