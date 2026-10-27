from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .ai_service import build_provider
from .analysis_service import build_summary_facts
from .excel_report_service import export_analysis
from .excel_service import inspect_excel, read_exam
from .models import MappingConfig
from .ppt_service import generate_ppt
from .sample_data import create_sample
from .student_report_service import generate_student_report


APP_BG = "#F4F7FB"
CARD_BG = "#FFFFFF"
TEXT = "#172033"
MUTED = "#6B7280"
ACCENT = "#3563E9"
ACCENT_DARK = "#274FC7"
ACCENT_SOFT = "#EAF0FF"
SUCCESS = "#16845B"
SUCCESS_SOFT = "#E8F7F1"
BORDER = "#E5EAF2"
WARNING = "#B7791F"


def default_output_dir() -> Path:
    documents = Path.home() / "Documents"
    base = documents if documents.exists() else Path.home()
    return base / "家长会助手输出"


class MappingDialog(tk.Toplevel):
    def __init__(self, parent, info: dict, on_confirm):
        super().__init__(parent)
        self.title("确认成绩字段")
        self.geometry("620x590")
        self.minsize(580, 520)
        self.configure(bg=APP_BG)
        self.transient(parent)
        self.grab_set()
        self.info = info
        self.on_confirm = on_confirm

        headers = info["headers"]
        suggested: MappingConfig = info["suggested"]

        shell = tk.Frame(self, bg=APP_BG, padx=24, pady=24)
        shell.pack(fill=tk.BOTH, expand=True)

        card = tk.Frame(shell, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill=tk.BOTH, expand=True)

        body = tk.Frame(card, bg=CARD_BG, padx=24, pady=22)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(body, text="确认成绩字段", bg=CARD_BG, fg=TEXT,
                 font=("Microsoft YaHei UI", 17, "bold")).pack(anchor=tk.W)
        tk.Label(body,
                 text=f"已识别到第 {info['header_row']} 行为表头。请确认姓名列，并选择需要统计的科目。",
                 bg=CARD_BG, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W, pady=(6, 20))

        tk.Label(body, text="姓名列", bg=CARD_BG, fg=TEXT,
                 font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W)
        self.name_var = tk.StringVar(value=headers[suggested.name_col - 1] if suggested.name_col else headers[0])
        self.name_combo = ttk.Combobox(body, textvariable=self.name_var, values=headers, state="readonly", height=10)
        self.name_combo.pack(fill=tk.X, pady=(7, 18))

        tk.Label(body, text="成绩科目（可多选）", bg=CARD_BG, fg=TEXT,
                 font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W)

        list_wrap = tk.Frame(body, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER)
        list_wrap.pack(fill=tk.BOTH, expand=True, pady=(7, 10))
        self.listbox = tk.Listbox(list_wrap, selectmode=tk.MULTIPLE, exportselection=False,
                                  borderwidth=0, highlightthickness=0, activestyle="none",
                                  bg="#FBFCFE", fg=TEXT, selectbackground=ACCENT,
                                  selectforeground="#FFFFFF", font=("Microsoft YaHei UI", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        for idx, h in enumerate(headers):
            self.listbox.insert(tk.END, f"  {h}")
            if (idx + 1) in suggested.subject_cols:
                self.listbox.selection_set(idx)

        hint = tk.Frame(body, bg="#FFF8E7", padx=12, pady=9)
        hint.pack(fill=tk.X, pady=(0, 18))
        tk.Label(hint, text="提示：不要选择总分、排名、学号等非科目字段。",
                 bg="#FFF8E7", fg=WARNING, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)

        actions = tk.Frame(body, bg=CARD_BG)
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="取消", style="Secondary.TButton", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(actions, text="确认字段", style="Primary.TButton", command=self._confirm).pack(side=tk.RIGHT, padx=(0, 10))

    def _confirm(self):
        headers = self.info["headers"]
        try:
            name_col = headers.index(self.name_var.get()) + 1
        except ValueError:
            messagebox.showerror("错误", "请选择姓名列。", parent=self)
            return
        subject_cols = [i + 1 for i in self.listbox.curselection()]
        if not subject_cols:
            messagebox.showerror("错误", "请至少选择一个成绩科目列。", parent=self)
            return
        mapping = MappingConfig(
            header_row=self.info["header_row"],
            name_col=name_col,
            subject_cols=subject_cols,
            id_col=self.info["suggested"].id_col,
            class_col=self.info["suggested"].class_col,
        )
        self.on_confirm(mapping)
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("班主任工具箱 · 家长会助手 V0.2")
        self.geometry("980x760")
        self.minsize(900, 700)
        self.configure(bg=APP_BG)

        self.current_path = tk.StringVar()
        self.previous_path = tk.StringVar()
        self.exam_name = tk.StringVar(value="期中考试")
        self.class_title = tk.StringVar(value="班级家长会")
        self.use_ai = tk.BooleanVar(value=False)
        self.current_info = None
        self.current_mapping: MappingConfig | None = None
        self.output_dir = default_output_dir()

        self._setup_styles()
        self._build()

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 10, "bold"),
                        foreground="#FFFFFF", background=ACCENT, borderwidth=0,
                        focusthickness=0, padding=(18, 11))
        style.map("Primary.TButton",
                  background=[("active", ACCENT_DARK), ("disabled", "#AAB7D8")],
                  foreground=[("disabled", "#F1F5F9")])

        style.configure("Secondary.TButton", font=("Microsoft YaHei UI", 10), foreground=TEXT,
                        background="#FFFFFF", bordercolor=BORDER, lightcolor=BORDER,
                        darkcolor=BORDER, padding=(14, 10))
        style.map("Secondary.TButton", background=[("active", "#F8FAFC")])

        style.configure("Ghost.TButton", font=("Microsoft YaHei UI", 9), foreground=ACCENT,
                        background=CARD_BG, borderwidth=0, padding=(8, 6))
        style.map("Ghost.TButton", background=[("active", ACCENT_SOFT)])

        style.configure("App.TCheckbutton", background=CARD_BG, foreground=TEXT,
                        font=("Microsoft YaHei UI", 9))
        style.configure("TCombobox", fieldbackground="#FBFCFE", background="#FBFCFE",
                        bordercolor=BORDER, padding=8)
        style.configure("Blue.Horizontal.TProgressbar", troughcolor="#E8EDF6",
                        background=ACCENT, bordercolor="#E8EDF6",
                        lightcolor=ACCENT, darkcolor=ACCENT)

    def _build(self):
        outer = tk.Frame(self, bg=APP_BG, padx=28, pady=24)
        outer.pack(fill=tk.BOTH, expand=True)

        self._build_header(outer)

        content = tk.Frame(outer, bg=APP_BG)
        content.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        left = tk.Frame(content, bg=APP_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = tk.Frame(content, bg=APP_BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_import_card(left)
        self._build_options_card(left)
        self._build_action_card(left)
        self._build_output_card(right)
        self._build_status_card(right)
        self._build_footer(outer)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=APP_BG)
        header.pack(fill=tk.X)
        title_row = tk.Frame(header, bg=APP_BG)
        title_row.pack(fill=tk.X)

        title_block = tk.Frame(title_row, bg=APP_BG)
        title_block.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(title_block, text="班主任工具箱", bg=APP_BG, fg=TEXT,
                 font=("Microsoft YaHei UI", 23, "bold")).pack(anchor=tk.W)
        tk.Label(title_block, text="家长会材料助手 · 从成绩表到完整家长会材料",
                 bg=APP_BG, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W, pady=(4, 0))

        badge = tk.Frame(title_row, bg=SUCCESS_SOFT, padx=12, pady=7)
        badge.pack(side=tk.RIGHT)
        tk.Label(badge, text="●  本地处理 · 默认不上传成绩", bg=SUCCESS_SOFT,
                 fg=SUCCESS, font=("Microsoft YaHei UI", 9, "bold")).pack()

        steps = tk.Frame(header, bg=APP_BG)
        steps.pack(fill=tk.X, pady=(18, 0))
        self._step_chip(steps, "1", "导入成绩", True).pack(side=tk.LEFT)
        tk.Label(steps, text="—", bg=APP_BG, fg="#B8C0CC", font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT, padx=6)
        self._step_chip(steps, "2", "确认字段", False).pack(side=tk.LEFT)
        tk.Label(steps, text="—", bg=APP_BG, fg="#B8C0CC", font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT, padx=6)
        self._step_chip(steps, "3", "生成材料", False).pack(side=tk.LEFT)

    def _step_chip(self, parent, num: str, label: str, active: bool):
        bg = ACCENT_SOFT if active else "#EEF1F5"
        fg = ACCENT if active else MUTED
        chip = tk.Frame(parent, bg=bg, padx=10, pady=6)
        tk.Label(chip, text=f"{num}  {label}", bg=bg, fg=fg,
                 font=("Microsoft YaHei UI", 9, "bold" if active else "normal")).pack()
        return chip

    def _card(self, parent):
        card = tk.Frame(parent, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill=tk.X, pady=(0, 14))
        return card

    def _card_title(self, parent, title: str, subtitle: str):
        tk.Label(parent, text=title, bg=CARD_BG, fg=TEXT,
                 font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W)
        tk.Label(parent, text=subtitle, bg=CARD_BG, fg=MUTED,
                 font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, pady=(4, 14))

    def _build_import_card(self, parent):
        card = self._card(parent)
        body = tk.Frame(card, bg=CARD_BG, padx=20, pady=18)
        body.pack(fill=tk.X)
        self._card_title(body, "1. 导入成绩", "先选择本次考试成绩，上次考试可选，用于生成进退步分析。")
        self._file_field(body, "本次考试成绩", self.current_path, self._choose_current, required=True)
        self._file_field(body, "上次考试成绩", self.previous_path, self._choose_previous, required=False)
        helper = tk.Frame(body, bg=CARD_BG)
        helper.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(helper, text="生成一份示例成绩表", style="Ghost.TButton", command=self._make_sample).pack(side=tk.LEFT)
        ttk.Button(helper, text="确认识别字段", style="Ghost.TButton", command=self._confirm_fields).pack(side=tk.LEFT, padx=(8, 0))

    def _file_field(self, parent, label, var, command, required=False):
        wrap = tk.Frame(parent, bg=CARD_BG)
        wrap.pack(fill=tk.X, pady=(0, 13))
        label_row = tk.Frame(wrap, bg=CARD_BG)
        label_row.pack(fill=tk.X)
        tk.Label(label_row, text=label, bg=CARD_BG, fg=TEXT,
                 font=("Microsoft YaHei UI", 9, "bold")).pack(side=tk.LEFT)
        tk.Label(label_row, text="必填" if required else "可选", bg=CARD_BG,
                 fg=ACCENT if required else MUTED, font=("Microsoft YaHei UI", 8)).pack(side=tk.RIGHT)

        row = tk.Frame(wrap, bg=CARD_BG)
        row.pack(fill=tk.X, pady=(6, 0))
        entry = tk.Entry(row, textvariable=var, relief=tk.FLAT, bd=0, bg="#F8FAFC",
                         fg=TEXT, insertbackground=TEXT, font=("Microsoft YaHei UI", 9),
                         highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=9)
        ttk.Button(row, text="选择文件", style="Secondary.TButton", command=command).pack(side=tk.LEFT, padx=(10, 0))

    def _build_options_card(self, parent):
        card = self._card(parent)
        body = tk.Frame(card, bg=CARD_BG, padx=20, pady=18)
        body.pack(fill=tk.X)
        self._card_title(body, "2. 材料设置", "这些内容会用于生成 PPT 标题和分析文件。")

        grid = tk.Frame(body, bg=CARD_BG)
        grid.pack(fill=tk.X)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        self._labeled_entry(grid, 0, 0, "考试名称", self.exam_name)
        self._labeled_entry(grid, 0, 1, "PPT 标题", self.class_title)

        ai_box = tk.Frame(body, bg="#F8FAFC", padx=12, pady=10, highlightthickness=1, highlightbackground=BORDER)
        ai_box.pack(fill=tk.X, pady=(14, 0))
        ttk.Checkbutton(ai_box, text="启用 AI 班级总结", variable=self.use_ai,
                        style="App.TCheckbutton").pack(anchor=tk.W)
        tk.Label(ai_box, text="未配置 AI 时仍可正常生成，系统会自动使用离线模板。",
                 bg="#F8FAFC", fg=MUTED, font=("Microsoft YaHei UI", 8)).pack(anchor=tk.W, pady=(3, 0))

    def _labeled_entry(self, parent, row, col, label, variable):
        box = tk.Frame(parent, bg=CARD_BG)
        box.grid(row=row, column=col, sticky="ew", padx=(0, 8) if col == 0 else (8, 0))
        tk.Label(box, text=label, bg=CARD_BG, fg=TEXT,
                 font=("Microsoft YaHei UI", 9, "bold")).pack(anchor=tk.W)
        entry = tk.Entry(box, textvariable=variable, relief=tk.FLAT, bd=0, bg="#F8FAFC",
                         fg=TEXT, insertbackground=TEXT, font=("Microsoft YaHei UI", 9),
                         highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        entry.pack(fill=tk.X, pady=(6, 0), ipady=9)

    def _build_action_card(self, parent):
        card = self._card(parent)
        body = tk.Frame(card, bg=CARD_BG, padx=20, pady=18)
        body.pack(fill=tk.X)
        self._card_title(body, "3. 生成材料", "确认无误后，一次生成完整家长会资料。")
        self.generate_btn = ttk.Button(body, text="开始生成家长会材料",
                                       style="Primary.TButton", command=self._generate)
        self.generate_btn.pack(fill=tk.X)
        self.progress = ttk.Progressbar(body, mode="indeterminate", style="Blue.Horizontal.TProgressbar")
        self.progress.pack(fill=tk.X, pady=(12, 0))
        self.progress_text = tk.StringVar(value="等待开始")
        tk.Label(body, textvariable=self.progress_text, bg=CARD_BG, fg=MUTED,
                 font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, pady=(7, 0))

    def _build_output_card(self, parent):
        card = self._card(parent)
        body = tk.Frame(card, bg=CARD_BG, padx=20, pady=18)
        body.pack(fill=tk.X)
        self._card_title(body, "将生成这些文件", "所有输出默认保存到“文档 / 家长会助手输出”。")

        outputs = [
            ("01", "班级成绩分析.xlsx", "各科统计、分数段、进退步"),
            ("02", "家长会PPT.pptx", "可直接继续修改的演示文稿"),
            ("03", "学生个人报告.docx", "逐个学生的成绩变化与建议"),
        ]
        for idx, title, desc in outputs:
            row = tk.Frame(body, bg=CARD_BG)
            row.pack(fill=tk.X, pady=7)
            icon = tk.Frame(row, bg=ACCENT_SOFT, width=34, height=34)
            icon.pack(side=tk.LEFT)
            icon.pack_propagate(False)
            tk.Label(icon, text=idx, bg=ACCENT_SOFT, fg=ACCENT,
                     font=("Microsoft YaHei UI", 9, "bold")).pack(expand=True)
            text = tk.Frame(row, bg=CARD_BG)
            text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
            tk.Label(text, text=title, bg=CARD_BG, fg=TEXT,
                     font=("Microsoft YaHei UI", 9, "bold")).pack(anchor=tk.W)
            tk.Label(text, text=desc, bg=CARD_BG, fg=MUTED,
                     font=("Microsoft YaHei UI", 8)).pack(anchor=tk.W, pady=(2, 0))

        ttk.Button(body, text="打开输出目录", style="Secondary.TButton",
                   command=self._open_output).pack(fill=tk.X, pady=(14, 0))

    def _build_status_card(self, parent):
        card = self._card(parent)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 14))
        body = tk.Frame(card, bg=CARD_BG, padx=20, pady=18)
        body.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(body, bg=CARD_BG)
        top.pack(fill=tk.X)
        tk.Label(top, text="运行状态", bg=CARD_BG, fg=TEXT,
                 font=("Microsoft YaHei UI", 13, "bold")).pack(side=tk.LEFT)
        self.status_badge = tk.Label(top, text="就绪", bg=SUCCESS_SOFT, fg=SUCCESS,
                                     font=("Microsoft YaHei UI", 8, "bold"), padx=9, pady=4)
        self.status_badge.pack(side=tk.RIGHT)

        self.status_box = tk.Text(body, height=18, wrap=tk.WORD, relief=tk.FLAT, bd=0,
                                  bg="#F8FAFC", fg="#485366", insertbackground=TEXT,
                                  font=("Microsoft YaHei UI", 9), padx=10, pady=10,
                                  highlightthickness=1, highlightbackground=BORDER)
        self.status_box.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.status_box.configure(state=tk.DISABLED)
        self._log(f"输出目录：{self.output_dir}")

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=APP_BG)
        footer.pack(fill=tk.X, pady=(10, 0))
        tk.Label(footer, text="V0.2 Preview", bg=APP_BG, fg="#9AA3AF",
                 font=("Microsoft YaHei UI", 8)).pack(side=tk.LEFT)
        tk.Label(footer, text="成绩数据默认仅在本机处理", bg=APP_BG, fg="#9AA3AF",
                 font=("Microsoft YaHei UI", 8)).pack(side=tk.RIGHT)

    def _choose_current(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xlsm")])
        if not p:
            return
        self.current_path.set(p)
        try:
            self.current_info = inspect_excel(p)
            self.current_mapping = self.current_info["suggested"]
            self._log(f"已导入本次成绩：{Path(p).name}")
            self._log(f"自动识别表头第 {self.current_info['header_row']} 行，建议点击“确认识别字段”。")
            self.progress_text.set("已读取本次成绩表")
        except Exception as e:
            self._log(f"识别失败：{e}")

    def _choose_previous(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xlsm")])
        if p:
            self.previous_path.set(p)
            self._log(f"已导入上次成绩：{Path(p).name}")

    def _confirm_fields(self):
        p = self.current_path.get().strip()
        if not p:
            messagebox.showwarning("提示", "请先选择本次考试成绩表。")
            return
        try:
            self.current_info = self.current_info or inspect_excel(p)
            MappingDialog(self, self.current_info, self._save_mapping)
        except Exception as e:
            messagebox.showerror("字段识别失败", str(e))

    def _save_mapping(self, mapping: MappingConfig):
        self.current_mapping = mapping
        headers = self.current_info["headers"] if self.current_info else []
        subject_names = [headers[i - 1] for i in mapping.subject_cols]
        name_label = headers[mapping.name_col - 1] if headers else str(mapping.name_col)
        self._log(f"字段已确认：姓名列={name_label}；科目={', '.join(subject_names)}")
        self.progress_text.set(f"字段已确认，共 {len(subject_names)} 个科目")

    def _generate(self):
        if not self.current_path.get().strip():
            messagebox.showwarning("提示", "请先选择本次考试成绩表。")
            return
        self.generate_btn.config(state=tk.DISABLED)
        self.progress.start(10)
        self.progress_text.set("正在准备生成材料…")
        self.status_badge.config(text="生成中", bg=ACCENT_SOFT, fg=ACCENT)
        threading.Thread(target=self._do_generate, daemon=True).start()

    def _do_generate(self):
        try:
            self.after(0, lambda: self._log("开始读取成绩表…"))
            self.after(0, lambda: self.progress_text.set("正在读取并校验成绩数据"))
            current = read_exam(self.current_path.get().strip(),
                                self.exam_name.get().strip() or "本次考试",
                                self.current_mapping)
            previous = None
            if self.previous_path.get().strip():
                previous = read_exam(self.previous_path.get().strip(), "上次考试")

            self.output_dir.mkdir(parents=True, exist_ok=True)
            excel_out = self.output_dir / "班级成绩分析.xlsx"
            ppt_out = self.output_dir / "家长会PPT.pptx"
            student_out = self.output_dir / "学生个人报告.docx"

            self.after(0, lambda: self._log("正在生成分析 Excel…"))
            self.after(0, lambda: self.progress_text.set("正在生成班级成绩分析"))
            export_analysis(current, previous, str(excel_out))

            ai_summary = None
            if self.use_ai.get():
                self.after(0, lambda: self._log("正在生成 AI 班级总结…"))
                self.after(0, lambda: self.progress_text.set("正在生成班级总结"))
                provider = build_provider(current, previous)
                try:
                    ai_summary = provider.generate_class_summary(build_summary_facts(current, previous))
                except Exception as e:
                    self.after(0, lambda e=e: self._log(f"AI 调用失败，已回退离线模板：{e}"))

            self.after(0, lambda: self._log("正在生成家长会 PPT…"))
            self.after(0, lambda: self.progress_text.set("正在生成家长会 PPT"))
            generate_ppt(current, previous, str(ppt_out),
                         self.class_title.get().strip() or "班级家长会",
                         ai_summary=ai_summary)

            self.after(0, lambda: self._log("正在生成学生个人报告…"))
            self.after(0, lambda: self.progress_text.set("正在生成学生个人报告"))
            generate_student_report(current, previous, str(student_out))

            msg = (f"生成完成：识别学生 {len(current.students)} 人，科目 {len(current.subjects)} 个。\n"
                   "已输出：班级成绩分析.xlsx / 家长会PPT.pptx / 学生个人报告.docx")
            self.after(0, lambda: self._log(msg))
            self.after(0, lambda: self.progress_text.set("生成完成，可以打开输出目录查看"))
            self.after(0, lambda: self.status_badge.config(text="已完成", bg=SUCCESS_SOFT, fg=SUCCESS))
            self.after(0, lambda: messagebox.showinfo("生成完成", "家长会材料已生成，可以打开输出目录查看。"))
        except Exception as e:
            self.after(0, lambda e=e: self._log(f"生成失败：{e}"))
            self.after(0, lambda: self.progress_text.set("生成失败，请查看运行状态"))
            self.after(0, lambda: self.status_badge.config(text="失败", bg="#FDECEC", fg="#B42318"))
            self.after(0, lambda e=e: messagebox.showerror("生成失败", str(e)))
        finally:
            self.after(0, self.progress.stop)
            self.after(0, lambda: self.generate_btn.config(state=tk.NORMAL))

    def _make_sample(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        current = self.output_dir / "本次考试_示例.xlsx"
        previous = self.output_dir / "上次考试_示例.xlsx"
        create_sample(str(current), seed=42, shift=1.5)
        create_sample(str(previous), seed=42, shift=0.0)
        self.current_path.set(str(current))
        self.previous_path.set(str(previous))
        self.current_info = inspect_excel(str(current))
        self.current_mapping = self.current_info["suggested"]
        self._log("已生成示例成绩表，并自动填入本次/上次考试。")
        self.progress_text.set("示例数据已准备好，可以直接生成")

    def _open_output(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(self.output_dir)
            else:
                os.system(f'xdg-open "{self.output_dir}" >/dev/null 2>&1 &')
        except Exception as e:
            messagebox.showerror("打开失败", str(e))

    def _log(self, msg: str):
        self.status_box.configure(state=tk.NORMAL)
        self.status_box.insert(tk.END, "• " + msg + "\n")
        self.status_box.see(tk.END)
        self.status_box.configure(state=tk.DISABLED)
