import unittest

from parser import parse_events


SAMPLE_HTML = """
<table>
    <tr>
        <th></th>
        <th>Hoạt động(T/gia)<br>Click vào tên HĐ để xem thông tin</th>
        <th>Học kỳ</th>
        <th>Điểm tích luỹ</th>
        <th>Kết thúc đăng ký</th>
        <th>Đăng ký</th>
    </tr>
    <tr>
        <td>1</td>
        <td><a href="doanvien.html?action=view&id=1">Hoạt động A (400/400)</a></td>
        <td>1/2026 - 2027</td>
        <td>2</td>
        <td>01-10-2026</td>
        <td>Đã đủ số lượng</td>
    </tr>
    <tr>
        <td>2</td>
        <td><a href="doanvien.html?action=view&id=2">Hoạt động B (385/400)</a></td>
        <td>1/2026 - 2027</td>
        <td>2</td>
        <td>29-09-2026</td>
        <td><a href="doanvien.html?action=reg&id=2">Đăng ký</a></td>
    </tr>
</table>
"""


class ParserTests(unittest.TestCase):
    def test_parses_full_and_available_events(self):
        ok, events, message = parse_events(SAMPLE_HTML)

        self.assertTrue(ok, message)
        self.assertEqual(len(events), 2)
        self.assertFalse(events[0]["is_available"])
        self.assertTrue(events[1]["is_available"])
        self.assertEqual(events[1]["available_slots"], 15)
        self.assertIn("action=reg&id=2", events[1]["register_url"])


if __name__ == "__main__":
    unittest.main()

