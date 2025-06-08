#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simplified HaeWaDal Motel PMS to demonstrate bug fixes."""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime


# --- DataManager stub -------------------------------------------------------
class DataManager:
    def save_current_room_status(self, room):
        print(f"saving room status: {room['id']} -> {room['status']}")

    def update_checkout(self, room_id):
        print(f"checkout room {room_id}")
        return True

# --- Notification system stub ----------------------------------------------
class NotificationSystem:
    def __init__(self, parent):
        self.parent = parent

    def add_notification(self, msg):
        print(f"NOTIFY: {msg}")

# --- Check-in dialog with explicit save button -----------------------------
class CheckinDialog(simpledialog.Dialog):
    def __init__(self, parent, room):
        self.room = room
        self.result = None
        super().__init__(parent, f"{room['id']}호 체크인")

    def body(self, master):
        tk.Label(master, text="고객명").grid(row=0, column=0, padx=5, pady=5)
        self.name = tk.Entry(master)
        self.name.grid(row=0, column=1, padx=5, pady=5)
        return self.name

    def buttonbox(self):
        box = tk.Frame(self)
        tk.Button(box, text="저장", command=self.ok, width=10).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(box, text="취소", command=self.cancel, width=10).pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def validate(self):
        if not self.name.get().strip():
            messagebox.showwarning("입력 오류", "고객명을 입력해주세요.", parent=self)
            return False
        return True

    def apply(self):
        self.result = {'guest_name': self.name.get().strip()}

# --- Room status change dialog (combobox width fix) ------------------------
class ChangeRoomStatusDialog(simpledialog.Dialog):
    def __init__(self, parent, room):
        self.room = room
        self.result = None
        super().__init__(parent, f"{room['id']}호 상태 변경")

    def body(self, master):
        tk.Label(master, text="상태 선택").pack(padx=10, pady=5)
        options = {'available': '✅ 사용가능', 'cleaning': '🧹 청소중', 'maintenance': '🔧 정비중'}
        self.map = {v: k for k, v in options.items()}
        self.var = tk.StringVar()
        self.combo = ttk.Combobox(master, textvariable=self.var, values=list(options.values()), state="readonly", width=18)
        self.combo.set(options.get(self.room['status'], '✅ 사용가능'))
        self.combo.pack(padx=10, pady=5)
        return self.combo

    def apply(self):
        self.result = self.map.get(self.var.get())

# --- Main application -------------------------------------------------------
class HaeWaDalPMS:
    def __init__(self):
        self.root = tk.Tk()
        self.data = DataManager()
        self.notify = NotificationSystem(self.root)
        self.rooms = [{'id': '101', 'status': 'available', 'platform': ''}]
        self.current_room = None
        self.create_ui()
        self.root.mainloop()

    def create_ui(self):
        btn = tk.Button(self.root, text="101호", command=lambda r=self.rooms[0]: self.on_room_selected(r))
        btn.pack(padx=20, pady=20)
        self.info = tk.Label(self.root, text="선택된 객실 없음")
        self.info.pack(pady=10)
        checkout = tk.Button(self.root, text="체크아웃", command=self.checkout_guest)
        checkout.pack(pady=5)
        change = tk.Button(self.root, text="상태변경", command=self.change_room_status)
        change.pack(pady=5)
        checkin = tk.Button(self.root, text="체크인", command=self.checkin_guest)
        checkin.pack(pady=5)

    def on_room_selected(self, room):
        self.current_room = room
        self.info.config(text=f"선택됨: {room['id']}호 ({room['status']})")

    def checkin_guest(self):
        if not self.current_room or self.current_room['status'] != 'available':
            messagebox.showwarning("오류", "체크인 가능한 객실을 선택하세요.")
            return
        dlg = CheckinDialog(self.root, self.current_room)
        if dlg.result:
            self.current_room['status'] = 'occupied'
            self.current_room['guest_name'] = dlg.result['guest_name']
            self.current_room['platform'] = '야놀자'
            self.data.save_current_room_status(self.current_room)
            self.notify.add_notification(f"{self.current_room['id']}호 체크인")
            self.info.config(text=f"선택됨: {self.current_room['id']}호 (occupied)")

    def checkout_guest(self):
        if not self.current_room or self.current_room['status'] != 'occupied':
            messagebox.showwarning("오류", "체크아웃할 객실을 선택하세요.")
            return
        if self.data.update_checkout(self.current_room['id']):
            self.current_room['status'] = 'cleaning'
            self.current_room['guest_name'] = ''
            self.current_room['platform'] = ''  # 플랫폼 정보 초기화
            self.data.save_current_room_status(self.current_room)
            self.notify.add_notification(f"{self.current_room['id']}호 체크아웃")
            self.info.config(text=f"선택됨: {self.current_room['id']}호 (cleaning)")

    def change_room_status(self):
        if not self.current_room:
            messagebox.showwarning("오류", "객실을 먼저 선택하세요.")
            return
        dlg = ChangeRoomStatusDialog(self.root, self.current_room)
        if dlg.result and dlg.result != self.current_room['status']:
            self.current_room['status'] = dlg.result
            self.data.save_current_room_status(self.current_room)
            self.info.config(text=f"선택됨: {self.current_room['id']}호 ({dlg.result})")

if __name__ == "__main__":
    HaeWaDalPMS()
