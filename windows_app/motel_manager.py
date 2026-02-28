"""Windows desktop motel room manager (Tkinter + SQLite)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk


@dataclass
class RoomView:
    room_number: str
    room_type: str
    status: str
    guest_name: str
    guest_phone: str
    checkin_at: str
    checkout_at: str
    price: int


class MotelStore:
    def __init__(self, db_path: str = "motel_manager.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self._seed_rooms_if_empty()

    def _init_db(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                room_number TEXT PRIMARY KEY,
                room_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                guest_name TEXT,
                guest_phone TEXT,
                checkin_at TEXT,
                checkout_at TEXT,
                price INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stay_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_number TEXT NOT NULL,
                guest_name TEXT NOT NULL,
                guest_phone TEXT,
                checkin_at TEXT NOT NULL,
                checkout_at TEXT NOT NULL,
                final_price INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def _seed_rooms_if_empty(self) -> None:
        row = self.conn.execute("SELECT COUNT(*) AS cnt FROM rooms").fetchone()
        if row["cnt"] > 0:
            return
        now = datetime.now().isoformat(timespec="seconds")
        room_types = ["standard", "ondol", "twin", "couple", "longterm"]
        batch = []
        for floor in [1, 2, 3]:
            for idx in range(1, 11):
                room_number = f"{floor}{idx:02d}"
                room_type = room_types[(idx - 1) % len(room_types)]
                batch.append((room_number, room_type, "available", now))
        self.conn.executemany(
            """
            INSERT INTO rooms (room_number, room_type, status, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            batch,
        )
        self.conn.commit()

    def list_rooms(self) -> list[RoomView]:
        rows = self.conn.execute(
            """
            SELECT room_number, room_type, status,
                   COALESCE(guest_name, '') AS guest_name,
                   COALESCE(guest_phone, '') AS guest_phone,
                   COALESCE(checkin_at, '') AS checkin_at,
                   COALESCE(checkout_at, '') AS checkout_at,
                   COALESCE(price, 0) AS price
            FROM rooms
            ORDER BY room_number
            """
        ).fetchall()
        return [RoomView(**dict(r)) for r in rows]

    def set_cleaning(self, room_number: str) -> None:
        self._update_status(room_number, "cleaning")

    def set_available(self, room_number: str) -> None:
        self._update_status(room_number, "available")

    def _update_status(self, room_number: str, status: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            """
            UPDATE rooms
            SET status = ?, updated_at = ?
            WHERE room_number = ?
            """,
            (status, now, room_number),
        )
        self.conn.commit()

    def check_in(
        self,
        room_number: str,
        guest_name: str,
        guest_phone: str,
        checkout_at: str,
        price: int,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            """
            UPDATE rooms
            SET status = 'occupied',
                guest_name = ?,
                guest_phone = ?,
                checkin_at = ?,
                checkout_at = ?,
                price = ?,
                updated_at = ?
            WHERE room_number = ?
            """,
            (guest_name, guest_phone, now, checkout_at, price, now, room_number),
        )
        self.conn.commit()

    def check_out(self, room_number: str) -> None:
        room = self.conn.execute(
            "SELECT * FROM rooms WHERE room_number = ?", (room_number,)
        ).fetchone()
        if not room or room["status"] != "occupied":
            return

        now = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            """
            INSERT INTO stay_history (
                room_number, guest_name, guest_phone, checkin_at, checkout_at, final_price, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                room["room_number"],
                room["guest_name"] or "-",
                room["guest_phone"] or "",
                room["checkin_at"] or now,
                now,
                room["price"] or 0,
                now,
            ),
        )
        self.conn.execute(
            """
            UPDATE rooms
            SET status='available',
                guest_name=NULL,
                guest_phone=NULL,
                checkin_at=NULL,
                checkout_at=NULL,
                price=0,
                updated_at=?
            WHERE room_number=?
            """,
            (now, room_number),
        )
        self.conn.commit()

    def stats(self) -> dict[str, int]:
        counts = self.conn.execute(
            """
            SELECT
                SUM(CASE WHEN status='available' THEN 1 ELSE 0 END) AS available,
                SUM(CASE WHEN status='occupied' THEN 1 ELSE 0 END) AS occupied,
                SUM(CASE WHEN status='cleaning' THEN 1 ELSE 0 END) AS cleaning
            FROM rooms
            """
        ).fetchone()
        today = date.today().isoformat()
        revenue_row = self.conn.execute(
            """
            SELECT COALESCE(SUM(final_price), 0) AS revenue
            FROM stay_history
            WHERE substr(checkout_at, 1, 10) = ?
            """,
            (today,),
        ).fetchone()
        return {
            "available": counts["available"] or 0,
            "occupied": counts["occupied"] or 0,
            "cleaning": counts["cleaning"] or 0,
            "today_revenue": revenue_row["revenue"] or 0,
        }


class MotelManagerApp:
    def __init__(self, root: tk.Tk, store: MotelStore) -> None:
        self.root = root
        self.store = store
        self.root.title("해와달 모텔 관리 시스템 (Windows)")
        self.root.geometry("980x640")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")

        self.stats_label = ttk.Label(top, text="로딩 중...")
        self.stats_label.pack(side="left")

        ttk.Button(top, text="새로고침", command=self.refresh).pack(side="right", padx=4)
        ttk.Button(top, text="이용가능", command=self.mark_available).pack(side="right", padx=4)
        ttk.Button(top, text="청소중", command=self.mark_cleaning).pack(side="right", padx=4)
        ttk.Button(top, text="체크아웃", command=self.checkout).pack(side="right", padx=4)
        ttk.Button(top, text="체크인", command=self.checkin).pack(side="right", padx=4)

        columns = (
            "room_number",
            "room_type",
            "status",
            "guest_name",
            "guest_phone",
            "checkin_at",
            "checkout_at",
            "price",
        )
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        for col, width in [
            ("room_number", 80),
            ("room_type", 90),
            ("status", 80),
            ("guest_name", 120),
            ("guest_phone", 110),
            ("checkin_at", 150),
            ("checkout_at", 150),
            ("price", 90),
        ]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _selected_room(self) -> str | None:
        item = self.tree.focus()
        if not item:
            messagebox.showwarning("선택 필요", "객실을 먼저 선택해주세요.")
            return None
        return self.tree.item(item, "values")[0]

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for room in self.store.list_rooms():
            self.tree.insert(
                "",
                "end",
                values=(
                    room.room_number,
                    room.room_type,
                    room.status,
                    room.guest_name,
                    room.guest_phone,
                    room.checkin_at,
                    room.checkout_at,
                    f"{room.price:,}",
                ),
            )

        s = self.store.stats()
        self.stats_label.config(
            text=(
                f"이용가능 {s['available']} | 사용중 {s['occupied']} | 청소중 {s['cleaning']}"
                f" | 오늘 매출 {s['today_revenue']:,}원"
            )
        )

    def checkin(self) -> None:
        room_number = self._selected_room()
        if not room_number:
            return
        name = simpledialog.askstring("체크인", "고객명")
        if not name:
            return
        phone = simpledialog.askstring("체크인", "전화번호") or ""
        checkout_at = simpledialog.askstring(
            "체크인", "예상 체크아웃 (예: 2026-01-01T12:00)", initialvalue=""
        ) or ""
        price_raw = simpledialog.askstring("체크인", "요금(숫자)", initialvalue="50000")
        if not price_raw:
            return
        try:
            price = int(price_raw)
        except ValueError:
            messagebox.showerror("오류", "요금은 숫자로 입력해주세요.")
            return

        self.store.check_in(room_number, name, phone, checkout_at, price)
        self.refresh()

    def checkout(self) -> None:
        room_number = self._selected_room()
        if not room_number:
            return
        self.store.check_out(room_number)
        self.refresh()

    def mark_cleaning(self) -> None:
        room_number = self._selected_room()
        if not room_number:
            return
        self.store.set_cleaning(room_number)
        self.refresh()

    def mark_available(self) -> None:
        room_number = self._selected_room()
        if not room_number:
            return
        self.store.set_available(room_number)
        self.refresh()


def main() -> None:
    db_path = Path(__file__).with_name("motel_manager.db")
    store = MotelStore(str(db_path))
    root = tk.Tk()
    app = MotelManagerApp(root, store)
    app  # keep reference
    root.mainloop()


if __name__ == "__main__":
    main()
