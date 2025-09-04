import tkinter as tk
from tkinter import scrolledtext, font, messagebox, ttk
import sqlite3
from datetime import datetime
from open_ai import get_response
import threading
import wave
import pyaudio
import os


class AudioRecorder:                                    
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.stream = None

    def start_recording(self):
        self.is_recording = True
        self.frames = []
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=1024)

        threading.Thread(target=self.record).start()

    def record(self):
        while self.is_recording:
            data = self.stream.read(1024)
            self.frames.append(data)

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        # Lưu file âm thanh
        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.frames))

        return filename

    def __del__(self):
        self.audio.terminate()


class AIChatApp:
    def __init__(self, master):
        self.master = master
        master.title("🤖 AI Chat Assistant")
        master.geometry("650x750")
        master.configure(bg="#f5f7fa")
        master.minsize(550, 650)

        # Màu sắc
        self.colors = {
            "primary": "#4a6fa5",
            "secondary": "#5e8cba",
            "background": "#f5f7fa",
            "user_bubble": "#e3f2fd",
            "ai_bubble": "#ffffff",
            "user_text": "#0d47a1",
            "ai_text": "#263238",
            "input_bg": "#ffffff",
            "header": "#3a5a80"
        }

        # Font chữ
        self.fonts = {
            "title": font.Font(family="Segoe UI", size=16, weight="bold"),
            "chat": font.Font(family="Segoe UI", size=12),
            "button": font.Font(family="Segoe UI", size=10, weight="bold"),
            "timestamp": font.Font(family="Segoe UI", size=9)
        }

        # Kết nối database
        self.conn = sqlite3.connect('chat_history.db', check_same_thread=False)
        self.create_database()

        # Thiết lập giao diện
        self.setup_ui()

        # Load lịch sử chat
        self.load_history()

        # Khởi tạo AudioRecorder
        self.recorder = AudioRecorder()
        self.is_recording = False

    def create_database(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.master, bg=self.colors["background"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header với gradient effect
        header_frame = tk.Frame(main_frame, bg=self.colors["header"], height=70)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        header_label = tk.Label(
            header_frame,
            text="AI Chat Assistant",
            font=self.fonts["title"],
            bg=self.colors["header"],
            fg="white",
            pady=20
        )
        header_label.pack(fill=tk.X)

        # Khung chat với shadow effect
        chat_container = tk.Frame(main_frame, bg="#e0e0e0", bd=0)
        chat_container.pack(fill=tk.BOTH, expand=True)

        self.chat_display = scrolledtext.ScrolledText(
            chat_container,
            wrap=tk.WORD,
            width=60,
            height=25,
            font=self.fonts["chat"],
            bg=self.colors["ai_bubble"],
            padx=15,
            pady=15,
            state='disabled',
            relief="flat",
            bd=2,
            highlightthickness=2,
            highlightbackground="#e0e0e0",
            highlightcolor="#e0e0e0"
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Cấu hình style cho tin nhắn
        self.chat_display.tag_config('user',
                                     foreground=self.colors["user_text"],
                                     justify='right',
                                     lmargin1=50,
                                     lmargin2=50,
                                     rmargin=10,
                                     background=self.colors["user_bubble"],
                                     relief="flat",
                                     borderwidth=1,
                                     selectbackground="#bbdefb")

        self.chat_display.tag_config('ai',
                                     foreground=self.colors["ai_text"],
                                     justify='left',
                                     lmargin1=10,
                                     lmargin2=10,
                                     rmargin=50,
                                     background=self.colors["ai_bubble"])

        self.chat_display.tag_config('timestamp',
                                     font=self.fonts["timestamp"],
                                     foreground="#757575",
                                     justify='center',
                                     spacing1=5,
                                     spacing3=5)

        # Khung nhập tin nhắn
        input_frame = tk.Frame(main_frame, bg=self.colors["background"])
        input_frame.pack(fill=tk.X, pady=(10, 5))

        self.user_input = tk.Entry(
            input_frame,
            font=self.fonts["chat"],
            bg=self.colors["input_bg"],
            relief="flat",
            bd=2,
            highlightthickness=1,
            highlightbackground="#b0bec5",
            highlightcolor="#4a6fa5"
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.user_input.bind("<Return>", self.send_message)

        # Nút ghi âm
        self.record_btn = tk.Button(
            input_frame,
            text="🎤",
            command=self.toggle_recording,
            font=("Segoe UI", 14),
            bg=self.colors["primary"],
            fg="white",
            relief="flat",
            width=3
        )
        self.record_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Nút gửi với hiệu ứng hover
        send_btn = tk.Button(
            input_frame,
            text="Gửi",
            command=self.send_message,
            font=self.fonts["button"],
            bg=self.colors["primary"],
            fg="white",
            activebackground=self.colors["secondary"],
            relief="flat",
            padx=20,
            bd=0
        )
        send_btn.pack(side=tk.RIGHT)

        # Hiệu ứng hover cho nút
        send_btn.bind("<Enter>", lambda e: send_btn.config(bg=self.colors["secondary"]))
        send_btn.bind("<Leave>", lambda e: send_btn.config(bg=self.colors["primary"]))

        # Khung nút chức năng
        button_frame = tk.Frame(main_frame, bg=self.colors["background"])
        button_frame.pack(fill=tk.X, pady=(5, 0))

        history_btn = tk.Button(
            button_frame,
            text="Lịch sử trò chuyện",
            command=self.show_history_window,
            font=self.fonts["button"],
            bg=self.colors["primary"],
            fg="white",
            relief="flat",
            padx=15
        )
        history_btn.pack(side=tk.LEFT, padx=(0, 10))

        clear_btn = tk.Button(
            button_frame,
            text="Xóa chat",
            command=self.clear_chat,
            font=self.fonts["button"],
            bg="#e74c3c",
            fg="white",
            relief="flat",
            padx=15
        )
        clear_btn.pack(side=tk.LEFT)

        # Hiệu ứng hover cho các nút
        for btn in [history_btn, clear_btn]:
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.colors["secondary"] if b != clear_btn else "#c0392b"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.colors["primary"] if b != clear_btn else "#e74c3c"))

    def save_message(self, sender, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (timestamp, sender, message) VALUES (?, ?, ?)",
            (timestamp, sender, message)
        )
        self.conn.commit()

    def load_history(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT timestamp, sender, message FROM chat_history ORDER BY timestamp ASC LIMIT 50")
        messages = cursor.fetchall()

        if messages:
            self.display_message("AI", "--- Cuộc trò chuyện trước ---", is_history=True)
            for timestamp, sender, message in messages:
                self.display_message(sender, message, is_history=True)
            self.display_message("AI", "--- Cuộc trò chuyện mới ---", is_history=True)
        else:
            self.display_message("AI", "Xin chào! Tôi có thể giúp gì cho bạn? 😊")

    def send_message(self, event=None):
        message = self.user_input.get()
        if message.strip():
            self.display_message("You", message)
            self.save_message("You", message)
            self.user_input.delete(0, tk.END)

            try:
                # Hiển thị indicator "AI đang nhập..."
                self.display_typing_indicator()
                self.master.update()  # Cập nhật giao diện ngay lập tức

                response = get_response(message)
                self.remove_typing_indicator()
                self.display_message("AI", response)
                self.save_message("AI", response)
            except Exception as e:
                self.remove_typing_indicator()
                messagebox.showerror("Lỗi", f"Không thể nhận phản hồi:\n{str(e)}")

    def display_typing_indicator(self):
        self.chat_display.configure(state='normal')
        self.chat_display.insert(tk.END, "AI đang nhập...\n", 'timestamp')
        self.chat_display.see(tk.END)
        self.chat_display.configure(state='disabled')
        self.typing_indicator_id = self.chat_display.index(tk.END)

    def remove_typing_indicator(self):
        if hasattr(self, 'typing_indicator_id'):
            self.chat_display.configure(state='normal')
            self.chat_display.delete(self.typing_indicator_id + "-2l", self.typing_indicator_id)
            self.chat_display.configure(state='disabled')

    def display_message(self, sender, message, is_history=False):
        self.chat_display.configure(state='normal')

        # Thêm thời gian cho tin nhắn mới
        if not is_history:
            timestamp = datetime.now().strftime("%H:%M")
            self.chat_display.insert(tk.END, f"{timestamp}\n", 'timestamp')

        # Thêm tin nhắn với style phù hợp
        if sender == "You":
            self.chat_display.insert(tk.END, f"{message}\n", 'user')
        else:
            self.chat_display.insert(tk.END, f"{message}\n", 'ai')

        self.chat_display.configure(state='disabled')
        self.chat_display.see(tk.END)

    def show_history_window(self):
        history_window = tk.Toplevel(self.master)
        history_window.title("Lịch sử trò chuyện")
        history_window.geometry("700x600")
        history_window.configure(bg=self.colors["background"])

        # Main frame
        main_frame = tk.Frame(history_window, bg=self.colors["background"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Thanh tìm kiếm
        search_frame = tk.Frame(main_frame, bg=self.colors["background"])
        search_frame.pack(fill=tk.X, pady=(0, 10))

        search_label = tk.Label(search_frame, text="Tìm kiếm:", bg=self.colors["background"])
        search_label.pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=self.colors["input_bg"],
            relief="flat",
            bd=2,
            highlightthickness=1,
            highlightbackground="#b0bec5"
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        search_entry.bind("<KeyRelease>", self.filter_history)

        clear_btn = tk.Button(
            search_frame,
            text="Xóa",
            command=self.clear_search,
            bg=self.colors["primary"],
            fg="white",
            relief="flat"
        )
        clear_btn.pack(side=tk.RIGHT)

        # Hiển thị lịch sử
        self.history_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            width=80,
            height=30,
            font=self.fonts["chat"],
            bg="white",
            padx=15,
            pady=15,
            relief="flat"
        )
        self.history_text.pack(fill=tk.BOTH, expand=True)

        # Cấu hình style cho lịch sử
        self.history_text.tag_config('history_user', foreground=self.colors["user_text"])
        self.history_text.tag_config('history_ai', foreground=self.colors["ai_text"])
        self.history_text.tag_config('history_time', foreground="#757575", font=self.fonts["timestamp"])

        # Load dữ liệu
        self.load_history_into_window()

    def load_history_into_window(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT timestamp, sender, message FROM chat_history ORDER BY timestamp DESC")
        messages = cursor.fetchall()

        self.history_text.configure(state='normal')
        self.history_text.delete(1.0, tk.END)

        for timestamp, sender, message in messages:
            self.history_text.insert(tk.END, f"[{timestamp}] ", 'history_time')
            if sender == "You":
                self.history_text.insert(tk.END, f"Bạn: {message}\n\n", 'history_user')
            else:
                self.history_text.insert(tk.END, f"AI: {message}\n\n", 'history_ai')

        self.history_text.configure(state='disabled')

    def filter_history(self, event=None):
        search_term = self.search_var.get().lower()

        cursor = self.conn.cursor()
        cursor.execute("SELECT timestamp, sender, message FROM chat_history ORDER BY timestamp DESC")
        messages = cursor.fetchall()

        self.history_text.configure(state='normal')
        self.history_text.delete(1.0, tk.END)

        for timestamp, sender, message in messages:
            if search_term in message.lower() or search_term in sender.lower():
                self.history_text.insert(tk.END, f"[{timestamp}] ", 'history_time')
                if sender == "You":
                    self.history_text.insert(tk.END, f"Bạn: {message}\n\n", 'history_user')
                else:
                    self.history_text.insert(tk.END, f"AI: {message}\n\n", 'history_ai')

        self.history_text.configure(state='disabled')

    def clear_search(self):
        self.search_var.set("")
        self.filter_history()

    def clear_chat(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa toàn bộ nội dung chat?"):
            self.chat_display.configure(state='normal')
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.configure(state='disabled')
            self.display_message("AI", "Nội dung chat đã được xóa. Tôi có thể giúp gì cho bạn?")

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.is_recording = True
        self.record_btn.config(bg="#e74c3c", text="⏹")
        self.display_message("System", "Đang ghi âm...")
        self.recorder.start_recording()

    def stop_recording(self):
        self.is_recording = False
        self.record_btn.config(bg=self.colors["primary"], text="🎤")
        self.display_message("System", "Đã dừng ghi âm")

        filename = self.recorder.stop_recording()
        self.display_message("You", f"[Voice message recorded: {filename}]")
        self.save_message("You", f"[Voice message: {filename}]")

    def __del__(self):
        if hasattr(self, 'recorder'):
            del self.recorder
        self.conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = AIChatApp(root)
    root.mainloop()