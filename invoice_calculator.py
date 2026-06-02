import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import shutil
import subprocess
from decimal import Decimal
from invoice_parser import extract_invoice_info


class InvoiceCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("发票金额统计器")
        self.root.resizable(False, False)

        self.all_invoices = []
        self.valid_invoices = []
        self.duplicates = []
        self.failed_files = []
        self.zero_amount_files = []
        self.folder_path = ""

        self.create_widgets()
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.center_window(560, 480)

    def center_window(self, width, height):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def create_widgets(self):
        style = ttk.Style()
        style.theme_use('vista')
        style.configure('Title.TLabel', font=('微软雅黑', 16, 'bold'), foreground='#1a5276')
        style.configure('Total.TLabel', font=('微软雅黑', 14, 'bold'), foreground='#c0392b')
        style.configure('Sub.TLabel', font=('微软雅黑', 10))
        style.configure('Action.TButton', font=('微软雅黑', 10), padding=(10, 5))
        style.configure('TFrame', background='#f5f5f5')
        style.configure('TLabelframe', font=('微软雅黑', 10, 'bold'))

        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=tk.NSEW)

        title_label = ttk.Label(
            self.main_frame, text="发票金额统计器",
            style='Title.TLabel'
        )
        title_label.grid(row=0, column=0, pady=(0, 20))

        self.select_btn = ttk.Button(
            self.main_frame,
            text="📁 选择发票文件夹",
            command=self.select_folder,
            style='Action.TButton'
        )
        self.select_btn.grid(row=1, column=0, pady=5)

        self.path_var = tk.StringVar()
        self.path_label = ttk.Label(
            self.main_frame,
            textvariable=self.path_var,
            wraplength=500,
            style='Sub.TLabel',
            foreground='#555555'
        )
        self.path_label.grid(row=2, column=0, sticky=tk.EW, pady=(5, 15))

        self.calc_btn = ttk.Button(
            self.main_frame,
            text="▶ 开始计算",
            command=self.calculate_total,
            style='Action.TButton'
        )
        self.calc_btn.grid(row=3, column=0, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            self.main_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress.grid(row=4, column=0, sticky=tk.EW, pady=10)

        self.result_frame = ttk.LabelFrame(self.main_frame, text="统计结果", padding="15")
        self.result_frame.grid(row=5, column=0, sticky=tk.EW, pady=10)

        self.total_var = tk.StringVar(value="总金额：¥ 0.00")
        self.total_label = ttk.Label(
            self.result_frame,
            textvariable=self.total_var,
            style='Total.TLabel'
        )
        self.total_label.grid(row=0, column=0, pady=3)

        self.count_var = tk.StringVar(value="发票数量：0")
        self.count_label = ttk.Label(
            self.result_frame,
            textvariable=self.count_var,
            style='Sub.TLabel'
        )
        self.count_label.grid(row=1, column=0, pady=3)

        self.dedup_var = tk.StringVar(value="")
        self.dedup_label = ttk.Label(
            self.result_frame,
            textvariable=self.dedup_var,
            style='Sub.TLabel'
        )
        self.dedup_label.grid(row=2, column=0, pady=3)

        self.summary_btn = ttk.Button(
            self.main_frame,
            text="📊 查看详细总结",
            command=self.show_summary_window,
            state=tk.DISABLED,
            style='Action.TButton'
        )
        self.summary_btn.grid(row=6, column=0, pady=10)

        self.main_frame.columnconfigure(0, weight=1)
        self.result_frame.columnconfigure(0, weight=1)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path = folder
            self.path_var.set(folder)

    def calculate_total(self):
        folder = self.path_var.get()
        if not folder:
            messagebox.showwarning("警告", "请先选择发票文件夹！")
            return

        self.folder_path = folder
        pdf_files = [f for f in os.listdir(folder) if f.lower().endswith('.pdf')]
        if not pdf_files:
            messagebox.showinfo("提示", "所选文件夹中没有找到PDF文件！")
            return

        self.calc_btn.config(state=tk.DISABLED)
        self.summary_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.all_invoices = []
        self.valid_invoices = []
        self.duplicates = []
        self.failed_files = []
        self.zero_amount_files = []

        total_files = len(pdf_files)
        seen_invoices = {}

        for i, pdf_file in enumerate(pdf_files):
            pdf_path = os.path.join(folder, pdf_file)
            info = extract_invoice_info(pdf_path)
            if info:
                self.all_invoices.append(info)
                if info['amount'] == Decimal('0'):
                    self.zero_amount_files.append(info)
                inv_no = info['invoice_no']
                if inv_no in seen_invoices:
                    self.duplicates.append(info)
                else:
                    seen_invoices[inv_no] = info
                    self.valid_invoices.append(info)
            else:
                self.failed_files.append(pdf_file)

            progress = (i + 1) / total_files * 100
            self.progress_var.set(progress)
            self.root.update()

        self.update_result_display()
        self.calc_btn.config(state=tk.NORMAL)

        if self.valid_invoices:
            self.summary_btn.config(state=tk.NORMAL)
            self.show_summary_window()

        issues = []
        if self.failed_files:
            issues.append(f"无法识别金额：{len(self.failed_files)} 个文件")
        if self.zero_amount_files:
            issues.append(f"金额为 0：{len(self.zero_amount_files)} 个文件")
        if issues:
            messagebox.showwarning("数据校验提示", "\n".join(issues))

    def update_result_display(self):
        total_amount = sum(inv['amount'] for inv in self.valid_invoices)
        self.total_var.set(f"总金额：¥ {total_amount:.2f}")
        total_all = len(self.all_invoices)
        total_valid = len(self.valid_invoices)
        dup_count = len(self.duplicates)
        self.count_var.set(f"发票数量：{total_all}（去重后 {total_valid}）")
        warnings = []
        if dup_count > 0:
            warnings.append(f"重复 {dup_count} 张")
        if self.failed_files:
            warnings.append(f"无法识别 {len(self.failed_files)} 张")
        if self.zero_amount_files:
            warnings.append(f"金额为0 {len(self.zero_amount_files)} 张")
        if warnings:
            self.dedup_var.set("⚠ " + "，".join(warnings))
            self.dedup_label.configure(foreground='#e67e22')
        else:
            self.dedup_var.set("✓ 校验通过，无异常")
            self.dedup_label.configure(foreground='#27ae60')

    def show_summary_window(self):
        summary_win = tk.Toplevel(self.root)
        summary_win.title("详细统计总结")
        summary_win.minsize(860, 600)
        summary_win.transient(self.root)
        summary_win.grab_set()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 900, 720
        summary_win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        total_amount = sum(inv['amount'] for inv in self.valid_invoices)

        summary_frame = ttk.LabelFrame(summary_win, text="汇总信息", padding="15")
        summary_frame.pack(fill=tk.X, padx=15, pady=(15, 5))

        ttk.Label(
            summary_frame,
            text=f"总金额（去重后）：¥ {total_amount:.2f}",
            font=('微软雅黑', 16, 'bold'),
            foreground='#c0392b'
        ).pack(anchor=tk.W)

        ttk.Label(
            summary_frame,
            text=f"发票总数：{len(self.all_invoices)}    去重后：{len(self.valid_invoices)}    重复：{len(self.duplicates)}",
            font=('微软雅黑', 10)
        ).pack(anchor=tk.W, pady=(5, 0))

        if self.failed_files or self.zero_amount_files:
            warn_frame = ttk.LabelFrame(summary_win, text="⚠ 数据校验警告", padding="10")
            warn_frame.pack(fill=tk.X, padx=15, pady=(5, 0))
            if self.failed_files:
                ttk.Label(
                    warn_frame,
                    text=f"无法识别的文件（{len(self.failed_files)} 个）：",
                    font=('微软雅黑', 9, 'bold'),
                    foreground='#c0392b'
                ).pack(anchor=tk.W)
                for f in self.failed_files:
                    ttk.Label(warn_frame, text=f"  · {f}", font=('微软雅黑', 9)).pack(anchor=tk.W)
            if self.zero_amount_files:
                if self.failed_files:
                    ttk.Label(warn_frame, text="", font=('微软雅黑', 5)).pack()
                ttk.Label(
                    warn_frame,
                    text=f"金额为 0 的文件（{len(self.zero_amount_files)} 个）：",
                    font=('微软雅黑', 9, 'bold'),
                    foreground='#e67e22'
                ).pack(anchor=tk.W)
                for inv in self.zero_amount_files:
                    ttk.Label(warn_frame, text=f"  · {inv['file_name']}", font=('微软雅黑', 9)).pack(anchor=tk.W)

        company_group = {}
        for inv in self.valid_invoices:
            name = inv['seller_name']
            if name not in company_group:
                company_group[name] = {'invoices': [], 'total': Decimal('0')}
            company_group[name]['invoices'].append(inv)
            company_group[name]['total'] += inv['amount']

        company_frame = ttk.LabelFrame(
            summary_win,
            text="各公司发票明细  💡 点击公司名称展开/收起  |  双击文件→打开  |  右键文件→定位",
            padding="10"
        )
        company_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        company_tree = ttk.Treeview(company_frame, columns=('数量', '金额'), show='tree headings', height=10)
        company_tree.heading('#0', text='公司名称 / 文件名')
        company_tree.heading('数量', text='数量')
        company_tree.heading('金额', text='金额（¥）')
        company_tree.column('#0', width=420, anchor=tk.W)
        company_tree.column('数量', width=100, anchor=tk.CENTER)
        company_tree.column('金额', width=160, anchor=tk.E)

        company_scroll = ttk.Scrollbar(company_frame, orient=tk.VERTICAL, command=company_tree.yview)
        company_tree.configure(yscrollcommand=company_scroll.set)
        company_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        company_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        file_path_map = {}

        for name, data in sorted(company_group.items(), key=lambda x: x[1]['total'], reverse=True):
            parent = company_tree.insert(
                '', tk.END, text=name,
                values=(len(data['invoices']), f"¥ {data['total']:.2f}")
            )
            for inv in data['invoices']:
                child = company_tree.insert(
                    parent, tk.END, text=inv['file_name'],
                    values=('', f"¥ {inv['amount']:.2f}")
                )
                file_path_map[child] = inv['file_path']

        def on_tree_click(event):
            item_id = company_tree.identify_row(event.y)
            if not item_id:
                return
            region = company_tree.identify_region(event.x, event.y)
            if company_tree.parent(item_id) == '' and region == 'cell':
                is_open = company_tree.item(item_id, 'open')
                company_tree.item(item_id, open=not is_open)

        def on_tree_doubleclick(event):
            item_id = company_tree.identify_row(event.y)
            if not item_id:
                return
            if company_tree.parent(item_id) != '':
                path = file_path_map.get(item_id)
                if path:
                    os.startfile(path)

        def on_tree_rightclick(event):
            item_id = company_tree.identify_row(event.y)
            if not item_id:
                return
            if company_tree.parent(item_id) != '':
                path = file_path_map.get(item_id)
                if path:
                    menu = tk.Menu(company_tree, tearoff=0)
                    menu.add_command(
                        label="📂 打开文件",
                        command=lambda p=path: os.startfile(p)
                    )
                    menu.add_command(
                        label="📁 在资源管理器中定位",
                        command=lambda p=path: subprocess.Popen(f'explorer /select,"{os.path.normpath(p)}"')
                    )
                    menu.tk_popup(event.x_root, event.y_root)

        company_tree.bind('<ButtonRelease-1>', on_tree_click)
        company_tree.bind('<Double-1>', on_tree_doubleclick)
        company_tree.bind('<Button-3>', on_tree_rightclick)

        if self.duplicates:
            dup_frame = ttk.LabelFrame(
                summary_win,
                text="重复发票列表  💡 双击文件→打开  |  右键文件→定位",
                padding="10"
            )
            dup_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

            dup_cols = ('文件名', '发票号', '金额')
            dup_tree = ttk.Treeview(dup_frame, columns=dup_cols, show='headings', height=5)
            dup_tree.heading('文件名', text='文件名')
            dup_tree.heading('发票号', text='发票号')
            dup_tree.heading('金额', text='金额（¥）')
            dup_tree.column('文件名', width=400, anchor=tk.W)
            dup_tree.column('发票号', width=200, anchor=tk.CENTER)
            dup_tree.column('金额', width=120, anchor=tk.E)

            dup_scroll = ttk.Scrollbar(dup_frame, orient=tk.VERTICAL, command=dup_tree.yview)
            dup_tree.configure(yscrollcommand=dup_scroll.set)
            dup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            dup_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            dup_file_path_map = {}
            for inv in self.duplicates:
                item = dup_tree.insert('', tk.END, values=(inv['file_name'], inv['invoice_no'], f"¥ {inv['amount']:.2f}"))
                dup_file_path_map[item] = inv['file_path']

            def on_dup_doubleclick(event):
                item_id = dup_tree.identify_row(event.y)
                if not item_id:
                    return
                path = dup_file_path_map.get(item_id)
                if path:
                    os.startfile(path)

            def on_dup_rightclick(event):
                item_id = dup_tree.identify_row(event.y)
                if not item_id:
                    return
                path = dup_file_path_map.get(item_id)
                if path:
                    menu = tk.Menu(dup_tree, tearoff=0)
                    menu.add_command(
                        label="📂 打开文件",
                        command=lambda p=path: os.startfile(p)
                    )
                    menu.add_command(
                        label="📁 在资源管理器中定位",
                        command=lambda p=path: subprocess.Popen(f'explorer /select,"{os.path.normpath(p)}"')
                    )
                    menu.tk_popup(event.x_root, event.y_root)

            dup_tree.bind('<Double-1>', on_dup_doubleclick)
            dup_tree.bind('<Button-3>', on_dup_rightclick)

            btn_frame = ttk.Frame(summary_win)
            btn_frame.pack(fill=tk.X, padx=15, pady=(5, 15))

            delete_btn = ttk.Button(
                btn_frame,
                text="🗑 删除重复发票文件",
                command=lambda: self.delete_duplicates(summary_win),
                style='Action.TButton'
            )
            delete_btn.pack(side=tk.RIGHT)
        else:
            ttk.Label(
                summary_win, text="✅ 没有发现重复发票",
                font=('微软雅黑', 11),
                foreground='#27ae60'
            ).pack(pady=15)

    def delete_duplicates(self, summary_win):
        if not self.duplicates:
            return

        result = messagebox.askyesno(
            "确认删除",
            f"即将把 {len(self.duplicates)} 个重复发票文件移动到备份文件夹。\n确定要继续吗？",
            icon='warning'
        )
        if not result:
            return

        backup_dir = os.path.join(self.folder_path, '_重复发票_备份')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        moved_count = 0
        failed = []
        for inv in self.duplicates:
            src = inv['file_path']
            dst = os.path.join(backup_dir, inv['file_name'])
            try:
                if os.path.exists(src):
                    shutil.move(src, dst)
                    moved_count += 1
                else:
                    failed.append(inv['file_name'])
            except Exception as e:
                failed.append(inv['file_name'])

        if failed:
            messagebox.showwarning(
                "部分失败",
                f"成功移动 {moved_count}/{len(self.duplicates)} 个文件。\n以下文件移动失败：\n" + "\n".join(failed)
            )
        else:
            messagebox.showinfo("完成", f"已将 {moved_count} 个重复文件移动到：\n{backup_dir}")
        summary_win.destroy()
        self.calculate_total()


if __name__ == "__main__":
    root = tk.Tk()
    app = InvoiceCalculator(root)
    root.mainloop()
