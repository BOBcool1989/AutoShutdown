#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动关机助手
作者：上杉 <windai@qq.com>
版本：1.0.0
功能：设置自动关机时间，到达前弹出确认对话框，可取消关机
兼容：Windows 7/8/10/11+
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import os
import sys
from datetime import datetime, timedelta


class AutoShutdownApp:
    VERSION = "1.0.0"
    AUTHOR = "上杉"
    EMAIL = "windai@qq.com"

    def __init__(self, root):
        self.root = root
        self.root.title(f"自动关机助手 v{self.VERSION}")
        self.root.geometry("420x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#2c3e50")

        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap(self.resource_path("icon.ico"))
        except:
            pass

        # 居中窗口
        self.center_window()

        # 变量
        self.shutdown_time = None
        self.timer_thread = None
        self.running = False
        self.warning_shown = False

        # 颜色主题
        self.colors = {
            "bg": "#2c3e50",
            "card": "#34495e",
            "accent": "#e74c3c",
            "accent_hover": "#c0392b",
            "success": "#27ae60",
            "success_hover": "#1e8449",
            "primary": "#3498db",
            "primary_hover": "#2980b9",
            "text": "#ecf0f1",
            "text_dim": "#bdc3c7",
            "warning": "#f39c12",
        }

        self.build_ui()

    def resource_path(self, relative_path):
        """获取资源路径，兼容PyInstaller打包"""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        width = 420
        height = 520
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def build_ui(self):
        """构建界面"""
        # 标题
        title_frame = tk.Frame(self.root, bg=self.colors["bg"])
        title_frame.pack(pady=(20, 10))

        title_label = tk.Label(
            title_frame,
            text="自动关机助手",
            font=("Microsoft YaHei", 24, "bold"),
            fg=self.colors["accent"],
            bg=self.colors["bg"]
        )
        title_label.pack()

        subtitle = tk.Label(
            title_frame,
            text=f"v{self.VERSION}  by {self.AUTHOR}",
            font=("Microsoft YaHei", 10),
            fg=self.colors["text_dim"],
            bg=self.colors["bg"]
        )
        subtitle.pack()

        # 主内容卡片
        card = tk.Frame(self.root, bg=self.colors["card"], padx=20, pady=20)
        card.pack(padx=20, pady=10, fill=tk.X)

        # 时间设置区域
        time_label = tk.Label(
            card,
            text="设置关机时间",
            font=("Microsoft YaHei", 12, "bold"),
            fg=self.colors["text"],
            bg=self.colors["card"]
        )
        time_label.pack(anchor=tk.W, pady=(0, 10))

        time_frame = tk.Frame(card, bg=self.colors["card"])
        time_frame.pack(fill=tk.X, pady=5)

        # 小时
        self.hour_var = tk.StringVar(value="23")
        hour_spin = tk.Spinbox(
            time_frame,
            from_=0,
            to=23,
            width=5,
            textvariable=self.hour_var,
            font=("Microsoft YaHei", 14),
            justify=tk.CENTER,
            wrap=True,
            format="%02.0f"
        )
        hour_spin.pack(side=tk.LEFT, padx=(0, 5))

        colon = tk.Label(
            time_frame,
            text=":",
            font=("Microsoft YaHei", 14, "bold"),
            fg=self.colors["text"],
            bg=self.colors["card"]
        )
        colon.pack(side=tk.LEFT, padx=5)

        # 分钟
        self.minute_var = tk.StringVar(value="00")
        minute_spin = tk.Spinbox(
            time_frame,
            from_=0,
            to=59,
            width=5,
            textvariable=self.minute_var,
            font=("Microsoft YaHei", 14),
            justify=tk.CENTER,
            wrap=True,
            format="%02.0f"
        )
        minute_spin.pack(side=tk.LEFT, padx=(5, 0))

        # 快捷设置按钮
        quick_frame = tk.Frame(card, bg=self.colors["card"])
        quick_frame.pack(fill=tk.X, pady=(15, 5))

        quick_times = [
            ("30分钟后", 30),
            ("1小时后", 60),
            ("2小时后", 120),
        ]

        for text, minutes in quick_times:
            btn = tk.Button(
                quick_frame,
                text=text,
                font=("Microsoft YaHei", 9),
                bg=self.colors["primary"],
                fg="white",
                activebackground=self.colors["primary_hover"],
                activeforeground="white",
                bd=0,
                padx=10,
                pady=5,
                cursor="hand2",
                command=lambda m=minutes: self.set_quick_time(m)
            )
            btn.pack(side=tk.LEFT, padx=5)

        # 分割线
        sep = tk.Frame(card, height=2, bg=self.colors["bg"])
        sep.pack(fill=tk.X, pady=15)

        # 状态显示
        status_label = tk.Label(
            card,
            text="当前状态",
            font=("Microsoft YaHei", 12, "bold"),
            fg=self.colors["text"],
            bg=self.colors["card"]
        )
        status_label.pack(anchor=tk.W, pady=(0, 10))

        self.status_var = tk.StringVar(value="未设置自动关机")
        self.status_display = tk.Label(
            card,
            textvariable=self.status_var,
            font=("Microsoft YaHei", 11),
            fg=self.colors["text_dim"],
            bg=self.colors["card"]
        )
        self.status_display.pack(anchor=tk.W, pady=5)

        # 倒计时
        self.countdown_var = tk.StringVar(value="--:--:--")
        self.countdown_label = tk.Label(
            card,
            textvariable=self.countdown_var,
            font=("Consolas", 28, "bold"),
            fg=self.colors["accent"],
            bg=self.colors["card"]
        )
        self.countdown_label.pack(pady=10)

        # 按钮区域
        btn_frame = tk.Frame(self.root, bg=self.colors["bg"])
        btn_frame.pack(pady=15)

        self.start_btn = tk.Button(
            btn_frame,
            text="开始定时关机",
            font=("Microsoft YaHei", 11, "bold"),
            bg=self.colors["success"],
            fg="white",
            activebackground=self.colors["success_hover"],
            activeforeground="white",
            bd=0,
            padx=25,
            pady=10,
            cursor="hand2",
            command=self.start_shutdown
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = tk.Button(
            btn_frame,
            text="取消关机",
            font=("Microsoft YaHei", 11, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground=self.colors["accent_hover"],
            activeforeground="white",
            bd=0,
            padx=25,
            pady=10,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.cancel_shutdown
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        # 底部版权
        copyright = tk.Label(
            self.root,
            text=f"{self.AUTHOR} <{self.EMAIL}>",
            font=("Microsoft YaHei", 8),
            fg=self.colors["text_dim"],
            bg=self.colors["bg"]
        )
        copyright.pack(side=tk.BOTTOM, pady=(0, 10))

    def set_quick_time(self, minutes):
        """设置快捷时间"""
        future = datetime.now() + timedelta(minutes=minutes)
        self.hour_var.set(f"{future.hour:02d}")
        self.minute_var.set(f"{future.minute:02d}")

    def start_shutdown(self):
        """开始定时关机"""
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的时间")
            return

        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # 如果目标时间已过，设置为明天
        if target <= now:
            target += timedelta(days=1)

        self.shutdown_time = target
        self.running = True
        self.warning_shown = False

        # 更新UI状态
        self.start_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.status_var.set(f"将在 {target.strftime('%H:%M')} 自动关机")
        self.status_display.config(fg=self.colors["success"])

        # 启动定时器线程
        self.timer_thread = threading.Thread(target=self.countdown_loop, daemon=True)
        self.timer_thread.start()

    def countdown_loop(self):
        """倒计时循环"""
        while self.running and self.shutdown_time:
            now = datetime.now()
            remaining = self.shutdown_time - now

            if remaining.total_seconds() <= 0:
                # 时间到，执行关机
                self.root.after(0, self.perform_shutdown)
                break

            # 更新倒计时显示
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.root.after(0, lambda s=time_str: self.countdown_var.set(s))

            # 关机前30秒弹出确认对话框
            if remaining.total_seconds() <= 30 and not self.warning_shown:
                self.warning_shown = True
                self.root.after(0, self.show_warning_dialog)

            time.sleep(1)

    def show_warning_dialog(self):
        """显示关机确认对话框"""
        if not self.running:
            return

        # 将窗口置顶
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))

        result = messagebox.askyesno(
            "即将关机",
            "电脑将在 30 秒后自动关机！\n\n是否取消关机？",
            icon='warning'
        )

        if result:
            self.cancel_shutdown()
        # 如果点击"否"，继续关机流程

    def perform_shutdown(self):
        """执行关机"""
        if not self.running:
            return

        self.running = False
        self.countdown_var.set("00:00:00")
        self.status_var.set("正在关机...")

        # 使用Windows shutdown命令
        try:
            subprocess.run(["shutdown", "/s", "/t", "0", "/f"], check=True)
        except subprocess.CalledProcessError:
            messagebox.showerror("错误", "执行关机命令失败，请手动关机")
            self.reset_ui()
        except FileNotFoundError:
            messagebox.showerror("错误", "找不到 shutdown 命令")
            self.reset_ui()

    def cancel_shutdown(self):
        """取消关机"""
        self.running = False

        # 取消Windows关机计划（如果有的话）
        try:
            subprocess.run(["shutdown", "/a"], check=False)
        except:
            pass

        self.reset_ui()
        messagebox.showinfo("已取消", "自动关机已取消")

    def reset_ui(self):
        """重置UI状态"""
        self.shutdown_time = None
        self.running = False
        self.warning_shown = False
        self.countdown_var.set("--:--:--")
        self.status_var.set("未设置自动关机")
        self.status_display.config(fg=self.colors["text_dim"])
        self.start_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)

    def on_closing(self):
        """窗口关闭处理"""
        if self.running:
            result = messagebox.askyesno(
                "确认退出",
                "自动关机任务正在运行，退出后将无法取消关机。\n\n确定要退出吗？",
                icon='warning'
            )
            if not result:
                return

            # 尝试取消Windows关机
            try:
                subprocess.run(["shutdown", "/a"], check=False)
            except:
                pass

        self.running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AutoShutdownApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
