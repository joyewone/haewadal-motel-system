import tempfile
import unittest

from windows_app.motel_manager import MotelStore


class MotelStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db")
        self.store = MotelStore(self.tmp.name)

    def tearDown(self):
        self.store.conn.close()
        self.tmp.close()

    def test_seed_rooms(self):
        rooms = self.store.list_rooms()
        self.assertEqual(len(rooms), 30)

    def test_checkin_checkout_flow(self):
        target = "101"
        self.store.check_in(target, "홍길동", "01012341234", "", 70000)
        room = [r for r in self.store.list_rooms() if r.room_number == target][0]
        self.assertEqual(room.status, "occupied")
        self.assertEqual(room.guest_name, "홍길동")

        self.store.check_out(target)
        room = [r for r in self.store.list_rooms() if r.room_number == target][0]
        self.assertEqual(room.status, "available")

        stats = self.store.stats()
        self.assertGreaterEqual(stats["today_revenue"], 70000)

    def test_checkin_validation(self):
        with self.assertRaises(ValueError):
            self.store.check_in("101", "", "010", "", 1000)
        with self.assertRaises(ValueError):
            self.store.check_in("101", "홍길동", "010", "", -1)
        with self.assertRaises(ValueError):
            self.store.check_in("999", "홍길동", "010", "", 1000)

    def test_prevent_double_occupancy(self):
        self.store.check_in("101", "첫손님", "010", "", 30000)
        with self.assertRaises(ValueError):
            self.store.check_in("101", "두번째손님", "010", "", 30000)

    def test_invalid_room_status_update(self):
        with self.assertRaises(ValueError):
            self.store.set_cleaning("999")


if __name__ == "__main__":
    unittest.main()
