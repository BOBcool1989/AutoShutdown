#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动关机助手 v2.1.0
作者：上杉 WeChat: kiceby
功能：定时关机、系统托盘、开机自启、配置保存、到达时间弹窗确认
兼容：Windows 7/8/10/11+
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import time
import os
import sys
import json
import winreg
from datetime import datetime, timedelta

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pystray
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

# ==================== 常量 ====================

APP_NAME = "AutoShutdown"
APP_TITLE = "自动关机助手"
APP_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), APP_NAME)
CONFIG_FILE = os.path.join(APP_DIR, 'config.json')

DEFAULT_CONFIG = {
    'hour': 23,
    'minute': 0,
    'auto_start': False,
}

# 配色方案
C = {
    'bg_dark':    '#0f0f1a',
    'bg':         '#1a1a2e',
    'bg_light':   '#16213e',
    'card':       '#1e2a4a',
    'card_hover': '#243354',
    'accent':     '#e94560',
    'accent_dim': '#b8354d',
    'success':    '#00b894',
    'success_dim':'#009975',
    'primary':    '#0abde3',
    'primary_dim':'#089bbf',
    'warning':    '#feca57',
    'text':       '#f5f6fa',
    'text_dim':   '#8395a7',
    'text_muted': '#576574',
    'border':     '#2d3f65',
    'red':        '#ee5a24',
    'green':      '#78e08f',
    'progress':   '#e94560',
    'progress_bg':'#2d3f65',
}

# ==================== 配置管理 ====================

def load_config():
    """加载配置"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in config:
                        config[k] = v
                return config
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)


def save_config(config):
    """保存配置"""
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def set_auto_start(enable):
    """设置/取消开机自启"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if enable:
            exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, '"{}" --tray'.format(exe_path))
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def get_auto_start():
    """获取开机自启状态"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


# ==================== 系统托盘 ====================

class SystemTray:
    """系统托盘管理"""

    def __init__(self, app):
        self.app = app
        self.tray = None
        self.thread = None

    def create_icon_image(self):
        """生成托盘图标（红色圆形+白色电源符号）"""
        if not HAS_PIL:
            return None
        size = 64
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 红色圆形背景
        margin = 4
        draw.ellipse([margin, margin, size - margin, size - margin],
                     fill=(233, 69, 96, 255))
        # 电源符号 - 竖线
        cx, cy = size // 2, size // 2
        draw.line([(cx, margin + 12), (cx, cy - 2)], fill=(255, 255, 255, 255), width=4)
        # 电源符号 - 弧线
        r = size // 2 - margin - 10
        bbox = [cx - r, cy - r, cx + r, cy + r]
        draw.arc(bbox, start=230, end=310, fill=(255, 255, 255, 255), width=4)
        return img

    def start(self):
        """启动系统托盘"""
        if not HAS_PYSTRAY or not HAS_PIL:
            return

        icon_image = self.create_icon_image()
        if icon_image is None:
            return

        def on_show(icon, item):
            self.app.root.after(0, self.app.show_window)

        def on_cancel(icon, item):
            self.app.root.after(0, self.app.cancel_shutdown)

        def on_exit(icon, item):
            self.app.root.after(0, self.app.exit_app)

        menu = pystray.Menu(
            pystray.MenuItem("显示主窗口", on_show, default=True),
            pystray.MenuItem("取消关机", on_cancel),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", on_exit),
        )

        self.tray = pystray.Icon(APP_NAME, icon_image, APP_TITLE, menu)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        try:
            self.tray.run()
        except Exception:
            pass

    def update_tooltip(self, text):
        """更新托盘提示文字"""
        if self.tray:
            try:
                self.tray.title = text
                self.tray.notify("", text) if hasattr(self.tray, 'notify') else None
            except Exception:
                pass

    def show_notification(self, title, message):
        """显示系统通知"""
        if self.tray:
            try:
                self.tray.notify(message, title)
            except Exception:
                pass

    def stop(self):
        """停止托盘"""
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass


# ==================== 关机确认对话框 ====================

class ShutdownWarningDialog:
    """到达关机时间后弹出的确认对话框，带倒计时"""

    def __init__(self, parent, countdown_seconds=60, on_cancel=None, on_confirm=None):
        self.parent = parent
        self.countdown_seconds = countdown_seconds
        self.remaining = countdown_seconds
        self.on_cancel_cb = on_cancel
        self.on_confirm_cb = on_confirm
        self.cancelled = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("即将关机")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=C['bg'])
        self.dialog.attributes('-topmost', True)
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel_click)
        self.dialog.grab_set()

        # 居中
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 200
        y = (self.dialog.winfo_screenheight() // 2) - 150
        self.dialog.geometry('400x300+{}+{}'.format(x, y))

        # 闪烁任务栏
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            ctypes.windll.user32.FlashWindow(hwnd, True)
        except Exception:
            pass

        self._build_ui()
        self._tick()

    def _build_ui(self):
        # 警告图标
        tk.Label(self.dialog, text="⚠", font=("Segoe UI Emoji", 40),
                 bg=C['bg'], fg=C['warning']).pack(pady=(20, 5))

        # 标题
        tk.Label(self.dialog, text="电脑即将自动关机",
                 font=("Microsoft YaHei", 16, "bold"),
                 bg=C['bg'], fg=C['text']).pack(pady=(5, 5))

        # 倒计时
        self.countdown_label = tk.Label(
            self.dialog,
            text="{} 秒后关机".format(self.remaining),
            font=("Microsoft YaHei", 13),
            bg=C['bg'], fg=C['accent']
        )
        self.countdown_label.pack(pady=5)

        # 进度条
        self.progress_canvas = tk.Canvas(
            self.dialog, width=300, height=8,
            bg=C['progress_bg'], highlightthickness=0
        )
        self.progress_canvas.pack(pady=5)

        # 按钮
        btn_frame = tk.Frame(self.dialog, bg=C['bg'])
        btn_frame.pack(pady=15)

        tk.Button(
            btn_frame, text="跳过本次",
            font=("Microsoft YaHei", 12, "bold"),
            bg=C['success'], fg="white",
            activebackground=C['success_dim'], activeforeground="white",
            bd=0, padx=30, pady=8, cursor="hand2",
            command=self.on_cancel_click
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            btn_frame, text="立即关机",
            font=("Microsoft YaHei", 12, "bold"),
            bg=C['accent'], fg="white",
            activebackground=C['accent_dim'], activeforeground="white",
            bd=0, padx=30, pady=8, cursor="hand2",
            command=self.on_confirm_click
        ).pack(side=tk.LEFT, padx=10)

    def _update_progress(self):
        """更新进度条"""
        self.progress_canvas.delete("all")
        ratio = self.remaining / self.countdown_seconds
        bar_width = int(300 * ratio)
        self.progress_canvas.create_rectangle(
            0, 0, bar_width, 8, fill=C['accent'], outline=""
        )

    def _tick(self):
        """倒计时"""
        if self.cancelled:
            return
        if self.remaining <= 0:
            self.on_confirm_click()
            return

        self.countdown_label.config(text="{} 秒后关机".format(self.remaining))
        self._update_progress()
        self.remaining -= 1
        self.dialog.after(1000, self._tick)

    def on_cancel_click(self):
        self.cancelled = True
        self.dialog.destroy()
        if self.on_cancel_cb:
            self.on_cancel_cb()

    def on_confirm_click(self):
        self.cancelled = True
        self.dialog.destroy()
        if self.on_confirm_cb:
            self.on_confirm_cb()


# ==================== 主应用 ====================

class AutoShutdownApp:
    VERSION = "2.1.0"
    AUTHOR = "上杉"
    WECHAT = "kiceby"

    def __init__(self, root):
        self.root = root
        self.root.title("{} v{}".format(APP_TITLE, self.VERSION))
        self.root.geometry("460x600")
        self.root.resizable(False, False)
        self.root.configure(bg=C['bg_dark'])

        # 尝试设置窗口图标
        try:
            if getattr(sys, 'frozen', False):
                self.root.iconbitmap(sys.executable)
        except Exception:
            pass

        # 状态
        self.shutdown_time = None
        self.running = False
        self.timer_thread = None
        self.warning_shown = False

        # 加载配置
        self.config = load_config()

        # 居中
        self._center_window()

        # 构建界面
        self._build_ui()

        # 恢复配置
        self._restore_config()

        # 系统托盘
        self.tray = None
        if HAS_PYSTRAY and HAS_PIL:
            self.tray = SystemTray(self)
            self.tray.start()

        # 关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 如果带 --tray 参数启动，最小化到托盘
        if '--tray' in sys.argv:
            self.root.after(200, self.hide_window)

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 460, 600
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry('{}x{}+{}+{}'.format(w, h, x, y))

    def _build_ui(self):
        # ===== 标题区域 =====
        header = tk.Frame(self.root, bg=C['bg_dark'])
        header.pack(fill=tk.X, pady=(18, 8))

        tk.Label(header, text="⏻ 自动关机助手",
                 font=("Microsoft YaHei", 22, "bold"),
                 fg=C['accent'], bg=C['bg_dark']).pack()

        tk.Label(header, text="v{}  by {}".format(self.VERSION, self.AUTHOR),
                 font=("Microsoft YaHei", 9),
                 fg=C['text_muted'], bg=C['bg_dark']).pack(pady=(2, 0))

        # ===== 时间设置卡片 =====
        time_card = tk.Frame(self.root, bg=C['card'], padx=18, pady=14)
        time_card.pack(padx=18, pady=(8, 4), fill=tk.X)

        tk.Label(time_card, text="⏰ 设置关机时间",
                 font=("Microsoft YaHei", 12, "bold"),
                 fg=C['text'], bg=C['card']).pack(anchor=tk.W, pady=(0, 8))

        # 时:分输入
        time_input = tk.Frame(time_card, bg=C['card'])
        time_input.pack(fill=tk.X, pady=5)

        self.hour_var = tk.StringVar(value="23")
        hour_spin = tk.Spinbox(
            time_input, from_=0, to=23, width=4,
            textvariable=self.hour_var,
            font=("Consolas", 18, "bold"),
            justify=tk.CENTER, wrap=True, format="%02.0f",
            bg=C['bg_light'], fg=C['text'],
            buttonbackground=C['border'],
            insertbackground=C['text'],
            relief=tk.FLAT, highlightthickness=1,
            highlightcolor=C['primary'], highlightbackground=C['border']
        )
        hour_spin.pack(side=tk.LEFT, padx=(0, 4))

        tk.Label(time_input, text=":",
                 font=("Consolas", 20, "bold"),
                 fg=C['text'], bg=C['card']).pack(side=tk.LEFT, padx=4)

        self.minute_var = tk.StringVar(value="00")
        minute_spin = tk.Spinbox(
            time_input, from_=0, to=59, width=4,
            textvariable=self.minute_var,
            font=("Consolas", 18, "bold"),
            justify=tk.CENTER, wrap=True, format="%02.0f",
            bg=C['bg_light'], fg=C['text'],
            buttonbackground=C['border'],
            insertbackground=C['text'],
            relief=tk.FLAT, highlightthickness=1,
            highlightcolor=C['primary'], highlightbackground=C['border']
        )
        minute_spin.pack(side=tk.LEFT, padx=(4, 0))

        # 快捷按钮
        quick_frame = tk.Frame(time_card, bg=C['card'])
        quick_frame.pack(fill=tk.X, pady=(12, 0))

        for text, minutes in [("30分钟后", 30), ("1小时后", 60), ("2小时后", 120)]:
            tk.Button(
                quick_frame, text=text,
                font=("Microsoft YaHei", 9),
                bg=C['primary'], fg="white",
                activebackground=C['primary_dim'], activeforeground="white",
                bd=0, padx=12, pady=4, cursor="hand2",
                command=lambda m=minutes: self._set_quick_time(m)
            ).pack(side=tk.LEFT, padx=4)

        # ===== 状态卡片 =====
        status_card = tk.Frame(self.root, bg=C['card'], padx=18, pady=14)
        status_card.pack(padx=18, pady=4, fill=tk.X)

        tk.Label(status_card, text="📊 当前状态",
                 font=("Microsoft YaHei", 12, "bold"),
                 fg=C['text'], bg=C['card']).pack(anchor=tk.W, pady=(0, 6))

        self.status_var = tk.StringVar(value="未设置自动关机")
        self.status_label = tk.Label(
            status_card, textvariable=self.status_var,
            font=("Microsoft YaHei", 11),
            fg=C['text_dim'], bg=C['card']
        )
        self.status_label.pack(anchor=tk.W, pady=2)

        # 倒计时
        self.countdown_var = tk.StringVar(value="--:--:--")
        self.countdown_label = tk.Label(
            status_card, textvariable=self.countdown_var,
            font=("Consolas", 32, "bold"),
            fg=C['accent'], bg=C['card']
        )
        self.countdown_label.pack(pady=6)

        # 倒计时进度条
        self.progress_canvas = tk.Canvas(
            status_card, width=400, height=6,
            bg=C['progress_bg'], highlightthickness=0
        )
        self.progress_canvas.pack(pady=(0, 4))

        # ===== 操作按钮 =====
        btn_frame = tk.Frame(self.root, bg=C['bg_dark'])
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(
            btn_frame, text="▶ 开始定时关机",
            font=("Microsoft YaHei", 12, "bold"),
            bg=C['success'], fg="white",
            activebackground=C['success_dim'], activeforeground="white",
            bd=0, padx=22, pady=9, cursor="hand2",
            command=self.start_shutdown
        )
        self.start_btn.pack(side=tk.LEFT, padx=6)

        self.cancel_btn = tk.Button(
            btn_frame, text="✖ 取消关机",
            font=("Microsoft YaHei", 12, "bold"),
            bg=C['accent'], fg="white",
            activebackground=C['accent_dim'], activeforeground="white",
            bd=0, padx=22, pady=9, cursor="hand2",
            state=tk.DISABLED,
            command=self.cancel_shutdown
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=6)

        # ===== 设置区域 =====
        settings_card = tk.Frame(self.root, bg=C['card'], padx=18, pady=10)
        settings_card.pack(padx=18, pady=4, fill=tk.X)

        tk.Label(settings_card, text="⚙ 设置",
                 font=("Microsoft YaHei", 12, "bold"),
                 fg=C['text'], bg=settings_card['bg']).pack(anchor=tk.W, pady=(0, 4))

        # 开机自启
        self.auto_start_var = tk.BooleanVar(value=get_auto_start())
        auto_start_cb = tk.Checkbutton(
            settings_card, text="开机自动启动（最小化到托盘）",
            variable=self.auto_start_var,
            font=("Microsoft YaHei", 10),
            fg=C['text_dim'], bg=settings_card['bg'],
            selectcolor=C['bg_light'],
            activebackground=settings_card['bg'],
            activeforeground=C['text'],
            command=self._toggle_auto_start
        )
        auto_start_cb.pack(anchor=tk.W, pady=2)

        # 关机后最小化到托盘
        self.minimize_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_card, text="开始后自动最小化到托盘",
            variable=self.minimize_var,
            font=("Microsoft YaHei", 10),
            fg=C['text_dim'], bg=settings_card['bg'],
            selectcolor=C['bg_light'],
            activebackground=settings_card['bg'],
            activeforeground=C['text'],
        ).pack(anchor=tk.W, pady=2)

        # ===== 底部版权 =====
        tk.Label(
            self.root,
            text="{}  WeChat: {}".format(self.AUTHOR, self.WECHAT),
            font=("Microsoft YaHei", 8),
            fg=C['text_muted'], bg=C['bg_dark']
        ).pack(side=tk.BOTTOM, pady=(0, 8))

    def _restore_config(self):
        """恢复上次保存的配置"""
        self.hour_var.set("{:02d}".format(self.config.get('hour', 23)))
        self.minute_var.set("{:02d}".format(self.config.get('minute', 0)))
        self.auto_start_var.set(get_auto_start())

    def _save_current_config(self):
        """保存当前配置"""
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
        except ValueError:
            hour, minute = 23, 0
        self.config['hour'] = hour
        self.config['minute'] = minute
        self.config['auto_start'] = self.auto_start_var.get()
        save_config(self.config)

    def _toggle_auto_start(self):
        """切换开机自启"""
        set_auto_start(self.auto_start_var.get())
        self._save_current_config()

    def _set_quick_time(self, minutes):
        """快捷设置时间"""
        future = datetime.now() + timedelta(minutes=minutes)
        self.hour_var.set("{:02d}".format(future.hour))
        self.minute_var.set("{:02d}".format(future.minute))
        self._save_current_config()

    # ==================== 关机逻辑 ====================

    def start_shutdown(self):
        """开始定时关机"""
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的时间")
            return

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            messagebox.showerror("错误", "时间范围无效（小时0-23，分钟0-59）")
            return

        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        self.shutdown_time = target
        self.running = True
        self.warning_shown = False

        # 保存配置
        self._save_current_config()

        # 更新UI
        self.start_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.status_var.set("将在 {} 自动关机".format(target.strftime('%H:%M')))
        self.status_label.config(fg=C['success'])

        # 更新托盘提示
        if self.tray:
            self.tray.update_tooltip("{} - {}关机".format(APP_TITLE, target.strftime('%H:%M')))

        # 启动倒计时线程
        self.timer_thread = threading.Thread(target=self._countdown_loop, daemon=True)
        self.timer_thread.start()

        # 自动最小化到托盘
        if self.minimize_var.get():
            self.root.after(500, self.hide_window)

    def _countdown_loop(self):
        """倒计时循环"""
        while self.running and self.shutdown_time:
            now = datetime.now()
            remaining = self.shutdown_time - now

            if remaining.total_seconds() <= 0:
                # 时间到，弹出确认对话框
                self.root.after(0, self._on_time_reached)
                break

            # 更新倒计时
            total_sec = int(remaining.total_seconds())
            hours, remainder = divmod(total_sec, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
            self.root.after(0, lambda s=time_str, t=total_sec: self._update_countdown(s, t))

            time.sleep(1)

    def _update_countdown(self, time_str, total_sec):
        """更新倒计时显示"""
        self.countdown_var.set(time_str)
        # 更新进度条
        self.progress_canvas.delete("all")
        if self.shutdown_time:
            now = datetime.now()
            total_duration = (self.shutdown_time - now).total_seconds()
            # 假设最大倒计时为24小时
            max_sec = 24 * 3600
            ratio = max(0, min(1, total_duration / max_sec))
            bar_width = int(400 * ratio)
            self.progress_canvas.create_rectangle(
                0, 0, bar_width, 6, fill=C['progress'], outline=""
            )

    def _on_time_reached(self):
        """到达关机时间"""
        if not self.running:
            return

        # 显示窗口（从托盘恢复）
        self.show_window()

        # 弹出确认对话框
        ShutdownWarningDialog(
            self.root,
            countdown_seconds=60,
            on_cancel=self._skip_this_shutdown,
            on_confirm=self._perform_shutdown
        )

    def _perform_shutdown(self):
        """执行关机"""
        self.running = False
        self.countdown_var.set("00:00:00")
        self.status_var.set("正在关机...")

        try:
            subprocess.run(["shutdown", "/s", "/t", "5", "/f"], check=True)
        except Exception:
            messagebox.showerror("错误", "执行关机命令失败，请手动关机")
            self._reset_ui()

    def _skip_this_shutdown(self):
        """跳过本次关机，自动顺延到明天同一时间"""
        # 取消Windows关机计划（如果有）
        try:
            subprocess.run(["shutdown", "/a"], check=False)
        except Exception:
            pass

        if self.shutdown_time:
            # 顺延到明天同一时间
            self.shutdown_time += timedelta(days=1)
            self.warning_shown = False

            # 更新状态
            self.status_var.set("将在明天 {} 自动关机".format(self.shutdown_time.strftime('%H:%M')))
            self.status_label.config(fg=C['success'])

            # 更新托盘提示
            if self.tray:
                self.tray.update_tooltip("{} - 明天{}关机".format(APP_TITLE, self.shutdown_time.strftime('%H:%M')))
                self.tray.show_notification(APP_TITLE, "已跳过本次，明天 {} 再提醒".format(self.shutdown_time.strftime('%H:%M')))

            # 重新启动倒计时线程
            self.timer_thread = threading.Thread(target=self._countdown_loop, daemon=True)
            self.timer_thread.start()
        else:
            self._reset_ui()

    def cancel_shutdown(self):
        """取消关机"""
        self.running = False

        # 取消Windows关机计划
        try:
            subprocess.run(["shutdown", "/a"], check=False)
        except Exception:
            pass

        self._reset_ui()

        # 托盘通知
        if self.tray:
            self.tray.show_notification(APP_TITLE, "自动关机已取消")

    def _reset_ui(self):
        """重置UI"""
        self.shutdown_time = None
        self.running = False
        self.warning_shown = False
        self.countdown_var.set("--:--:--")
        self.status_var.set("未设置自动关机")
        self.status_label.config(fg=C['text_dim'])
        self.start_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.progress_canvas.delete("all")

        if self.tray:
            self.tray.update_tooltip(APP_TITLE)

    # ==================== 窗口控制 ====================

    def show_window(self):
        """显示主窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))

    def hide_window(self):
        """隐藏到托盘"""
        self.root.withdraw()

    def _on_close(self):
        """关闭窗口事件"""
        if self.running:
            if HAS_PYSTRAY and HAS_PIL and self.tray:
                # 有关机任务且支持托盘，最小化到托盘
                self.hide_window()
                if self.tray:
                    self.tray.show_notification(APP_TITLE, "程序已最小化到托盘，关机任务继续运行")
                return
            else:
                result = messagebox.askyesno(
                    "确认退出",
                    "自动关机任务正在运行！\n退出后将无法取消关机。\n\n确定要退出吗？",
                    icon='warning'
                )
                if not result:
                    return
                # 取消关机
                try:
                    subprocess.run(["shutdown", "/a"], check=False)
                except Exception:
                    pass

        self.exit_app()

    def exit_app(self):
        """退出应用"""
        self.running = False
        self._save_current_config()
        if self.tray:
            self.tray.stop()
        self.root.destroy()


# ==================== 入口 ====================

def main():
    root = tk.Tk()
    app = AutoShutdownApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
