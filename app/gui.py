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


def default_output_dir() -> Path:
    documents = Path.home() / "Documents"
    base = documents if documents.exists() else Path.home()
    return base / "家长会助手输出"


class MappingDialog(tk.Toplevel):
    def __init__(self, parent, info: dict, on_confirm):
        super().__init__(parent)
        self.title("确认成绩字段")
        self.geometry("560x520")
        self.transient(parent)
        self.grab_set()
        self.info = info
        self.on_confirm = on_confirm
        headers = info["headers"]
        suggested: MappingConfig = info["suggested"]

        root = ttk.Frame(self, padding=18)
        root.pack(fill=tk.BOTH, expand=True)
        ttk.Label(root, text=f"识别到表头第 {info['header_row']} 行，请确认字段。", font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W)

        ttk.Label(root, text="姓名列").pack(anchor=tk.W, pady=(16, 4))
        self.name_var = tk.StringVar(value=headers[suggested.name_col - 1] if suggested.name_col else headers[0])
        self.name_combo = ttk.Combobox(root, textvariable=self.name_var, values=headers, state="readonly")
        self.name_combo.pack(fill=tk.X)

        ttk.Label(root, text="成绩科目（可多选）").pack(anchor=tk.W, pady=(16, 4))
        self.listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, height=14, exportselection=False)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        for idx, h in enumerate(headers):
            self.listbox.insert(tk.END, h)
            if (idx + 1) in suggested.subject_cols:
                self.listbox.selection_set(idx)

        ttk.Label(root, text="提示：不要选择总分、排名、学号等列。", foreground="#666666").pack(anchor=tk.W, pady=(8, 12))

        actions = ttk.Frame(root)
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="取消", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(actions, text="确认", command=self._confirm).pack(side=tk.RIGHT, padx=(0, 8))

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
        self.title("家长会助手 V0.1")
        self.geometry("820x620")
        self.minsize(760, 560)

        self.current_path = tk.StringVar()
        self.previous_path = tk.StringVar()
        self.exam_name = tk.StringVar(value="期中考试")
        self.class_title = tk.StringVar(value="班级家长会")
        self.use_ai = tk.BooleanVar(value=False)
        self.current_info = None
        self.current_mapping: MappingConfig | None = None
        self.output_dir = default_output_dir()
        self._build()

    def _build(self):
        root = ttk.Frame(self, padding=20)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text="家长会材料助手", font=("Microsoft YaHei UI", 20, "bold")).pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(root, text="Excel 在本机读取与统计；可生成分析 Excel、家长会 PPT 和学生个人报告。默认不上传学生原始数据。", font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W, pady=(0, 18))

        form = ttk.Frame(root)
        form.pack(fill=tk.X)
        self._file_row(form, 0, "本次成绩表", self.current_path, self._choose_current)
        self._file_row(form, 1, "上次成绩表（可选）", self.previous_path, self._choose_previous)

        ttk.Label(form, text="考试名称").grid(row=2, column=0, sticky=tk.W, pady=8)
        ttk.Entry(form, textvariable=self.exam_name).grid(row=2, column=1, sticky=tk.EW, padx=(10, 10), pady=8)
        ttk.Label(form, text="PPT标题").grid(row=3, column=0, sticky=tk.W, pady=8)
        ttk.Entry(form, textvariable=self.class_title).grid(row=3, column=1, sticky=tk.EW, padx=(10, 10), pady=8)
        form.columnconfigure(1, weight=1)

        opts = ttk.Frame(root)
        opts.pack(fill=tk.X, pady=(8, 2))
        ttk.Checkbutton(opts, text="启用 AI 班级总结（需配置 config/ai.json；失败会自动回退离线模板）", variable=self.use_ai).pack(anchor=tk.W)

        actions = ttk.Frame(root)
        actions.pack(fill=tk.X, pady=16)
        ttk.Button(actions, text="字段确认", command=self._confirm_fields).pack(side=tk.LEFT)
        self.generate_btn = ttk.Button(actions, text="生成家长会材料", command=self._generate)
        self.generate_btn.pack(side=tk.LEFT, padx=8)
        ttk.Button(actions, text="生成示例成绩表", command=self._make_sample).pack(side=tk.LEFT)
        ttk.Button(actions, text="打开输出目录", command=self._open_output).pack(side=tk.LEFT, padx=8)

        ttk.Separator(root).pack(fill=tk.X, pady=(2, 14))
        ttk.Label(root, text="运行日志", font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W)
        self.status_box = tk.Text(root, height=14, wrap=tk.WORD, font=("Consolas", 10))
        self.status_box.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self._log(f"输出目录：{self.output_dir}")

    def _file_row(self, parent, row, label, var, command):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=8)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky=tk.EW, padx=(10, 10), pady=8)
        ttk.Button(parent, text="选择…", command=command).grid(row=row, column=2, pady=8)

    def _choose_current(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xlsm")])
        if not p:
            return
        self.current_path.set(p)
        try:
            self.current_info = inspect_excel(p)
            self.current_mapping = self.current_info["suggested"]
            self._log(f"本次成绩：{p}")
            self._log(f"自动识别表头第 {self.current_info['header_row']} 行，建议先点击‘字段确认’。")
        except Exception as e:
            self._log(f"识别失败：{e}")

    def _choose_previous(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xlsm")])
        if p:
            self.previous_path.set(p)
            self._log(f"上次成绩：{p}")

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
        self._log(f"字段已确认：姓名列={headers[mapping.name_col - 1] if headers else mapping.name_col}；科目={', '.join(subject_names)}")

    def _generate(self):
        if not self.current_path.get().strip():
            messagebox.showwarning("提示", "请先选择本次考试成绩表。")
            return
        self.generate_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._do_generate, daemon=True).start()

    def _do_generate(self):
        try:
            self.after(0, lambda: self._log("开始读取成绩表…"))
            current = read_exam(self.current_path.get().strip(), self.exam_name.get().strip() or "本次考试", self.current_mapping)
            previous = None
            if self.previous_path.get().strip():
                previous = read_exam(self.previous_path.get().strip(), "上次考试")

            self.output_dir.mkdir(parents=True, exist_ok=True)
            excel_out = self.output_dir / "班级成绩分析.xlsx"
            ppt_out = self.output_dir / "家长会PPT.pptx"
            student_out = self.output_dir / "学生个人报告.docx"

            self.after(0, lambda: self._log("正在生成分析 Excel…"))
            export_analysis(current, previous, str(excel_out))

            ai_summary = None
            if self.use_ai.get():
                self.after(0, lambda: self._log("正在生成 AI 班级总结…"))
                provider = build_provider(current, previous)
                try:
                    ai_summary = provider.generate_class_summary(build_summary_facts(current, previous))
                except Exception as e:
                    self.after(0, lambda e=e: self._log(f"AI 调用失败，已回退离线模板：{e}"))

            self.after(0, lambda: self._log("正在生成家长会 PPT…"))
            generate_ppt(current, previous, str(ppt_out), self.class_title.get().strip() or "班级家长会", ai_summary=ai_summary)

            self.after(0, lambda: self._log("正在生成学生个人报告…"))
            generate_student_report(current, previous, str(student_out))

            msg = f"生成完成。\n- {excel_out}\n- {ppt_out}\n- {student_out}\n识别学生 {len(current.students)} 人，科目 {len(current.subjects)} 个。"
            self.after(0, lambda: self._log(msg))
            self.after(0, lambda: messagebox.showinfo("完成", "家长会材料已生成。"))
        except Exception as e:
            self.after(0, lambda e=e: self._log(f"生成失败：{e}"))
            self.after(0, lambda e=e: messagebox.showerror("生成失败", str(e)))
        finally:
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
        self._log(f"已生成示例成绩表：{current}")

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
        self.status_box.insert(tk.END, msg + "\n")
        self.status_box.see(tk.END)
