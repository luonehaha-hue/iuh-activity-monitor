import re
import urllib.parse
from bs4 import BeautifulSoup

def is_session_expired(html_content: str, current_url: str = "") -> bool:
    """
    Kiem tra xem phien dang nhap co bi het han va redirect ve login hay khong.
    """
    if not html_content:
        return True

    # Kiem tra URL neu requests tu dong redirect ve login.html
    if current_url and "login.html" in current_url:
        return True

    # Kiem tra the meta refresh ve login.html
    if "URL=login.html" in html_content or "url=login.html" in html_content:
        return True

    # Kiem tra form dang nhap co ma captcha hoac name=frmLogin
    if 'id="frmLogin"' in html_content or 'name="frmLogin"' in html_content:
        return True

    if 'name="security_code"' in html_content and 'name="mssv"' in html_content:
        return True

    return False


def parse_events(html_content: str, base_url: str = "https://doantn.iuh.edu.vn/", current_url: str = ""):
    """
    Parse bang su kien tu HTML cua trang doanvien.html@211@Tra-cuu.
    Trich xuat them dia diem va thoi gian to chuc tu cac Bootstrap Modal tren trang.
    Tra ve tuple: (success: bool, events: list, message: str)
    """
    if not html_content:
        return False, [], "Nội dung phản hồi từ website rỗng."

    if is_session_expired(html_content, current_url=current_url):
        return False, [], "Phiên đăng nhập (Cookie PHPSESSID) đã hết hạn hoặc không đúng. Vui lòng đăng nhập lại và cập nhật Cookie."

    soup = BeautifulSoup(html_content, "html.parser")

    # Thu thap tat ca cac Bootstrap Modals tren trang
    modals_dict = {}
    for m in soup.find_all("div", class_="modal"):
        m_id = m.get("id")
        if m_id:
            m_body = m.find(class_="modal-body")
            body_txt = m_body.get_text("\n", strip=True) if m_body else m.get_text("\n", strip=True)
            
            # Trich xuat Thoi gian to chuc
            time_m = re.search(r"Thời gian(?: tổ chức)?:?\s*([^;\n]+)", body_txt, re.IGNORECASE)
            event_time = time_m.group(1).strip().rstrip(";") if time_m else ""

            # Trich xuat Dia diem
            loc_m = re.search(r"Địa điểm:?\s*([^;\n]+)", body_txt, re.IGNORECASE)
            event_loc = loc_m.group(1).strip().rstrip(";") if loc_m else ""

            # Trich xuat Don vi to chuc
            org_m = re.search(r"Đơn vị(?: tổ chức)?:?\s*([^;\n]+)", body_txt, re.IGNORECASE)
            event_org = org_m.group(1).strip().rstrip(";") if org_m else ""

            modals_dict[m_id] = {
                "event_time": event_time,
                "location": event_loc,
                "organizer": event_org,
                "raw_text": body_txt
            }

    # Tim tat ca cac bang trong HTML
    tables = soup.find_all("table")
    if not tables:
        return True, [], "Không tìm thấy bảng dữ liệu nào trên trang web."

    target_table = None

    for tbl in tables:
        tbl_text = tbl.get_text()
        if ("Hoạt động" in tbl_text or "HĐ" in tbl_text) and ("Điểm tích luỹ" in tbl_text or "Điểm" in tbl_text or "Học kỳ" in tbl_text):
            target_table = tbl
            break

    if not target_table:
        for tbl in tables:
            tbl_text = tbl.get_text()
            if "Đăng ký" in tbl_text and ("Điểm" in tbl_text or "Học kỳ" in tbl_text):
                target_table = tbl
                break

    if not target_table:
        return True, [], "Không tìm thấy bảng danh sách sự kiện (có thể thời điểm này chưa có sự kiện nào được tạo)."

    rows = target_table.find_all("tr")
    if not rows:
        return True, [], "Bảng sự kiện không có dòng dữ liệu nào."

    # Tim hang tieu de (Header) de xac dinh dung vi tri cot
    header_indices = {
        "stt": -1,
        "title": -1,
        "semester": -1,
        "points": -1,
        "deadline": -1,
        "register": -1
    }

    header_row_idx = -1
    for r_idx, row in enumerate(rows[:4]):
        ths = row.find_all(["th", "td"])
        th_texts = [th.get_text(strip=True).lower() for th in ths]
        for col_idx, txt in enumerate(th_texts):
            if ("hoạt động" in txt or "hđ" in txt or "tên" in txt) and header_indices["title"] == -1:
                header_indices["title"] = col_idx
                header_row_idx = r_idx
            elif ("học kỳ" in txt or "học kì" in txt) and header_indices["semester"] == -1:
                header_indices["semester"] = col_idx
            elif ("điểm" in txt) and header_indices["points"] == -1:
                header_indices["points"] = col_idx
            elif ("kết thúc" in txt or "hạn" in txt) and header_indices["deadline"] == -1:
                header_indices["deadline"] = col_idx
            elif ("đăng ký" in txt or "đk" in txt or "trạng thái" in txt) and header_indices["register"] == -1:
                header_indices["register"] = col_idx
        if header_indices["title"] != -1:
            break

    start_row = header_row_idx + 1 if header_row_idx != -1 else 1

    events = []
    for row in rows[start_row:]:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        row_full_text = row.get_text(strip=True)
        if "tổng chưa đóng" in row_full_text.lower() or "tìm kiếm" in row_full_text.lower():
            continue

        # 1. STT
        stt_txt = cols[0].get_text(strip=True) if len(cols) > 0 else ""

        # 2. Hoat dong
        title_idx = header_indices["title"] if (header_indices["title"] != -1 and header_indices["title"] < len(cols)) else 1
        title_col = cols[title_idx]
        title_txt = " ".join(title_col.get_text(" ", strip=True).split())
        
        # Link chi tiet hoac data-target modal
        title_a = title_col.find("a")
        detail_url = ""
        modal_id = ""
        event_time = ""
        event_location = ""
        event_org = ""

        if title_a:
            href_val = title_a.get("href", "")
            target_val = title_a.get("data-target", "")
            if target_val:
                modal_id = target_val.replace("#", "")
            elif href_val and href_val.startswith("#"):
                modal_id = href_val.replace("#", "")

            if href_val and not href_val.startswith("#"):
                detail_url = urllib.parse.urljoin(base_url, href_val)

        # Lay thong tin tu modal neu co
        if modal_id and modal_id in modals_dict:
            event_time = modals_dict[modal_id].get("event_time", "")
            event_location = modals_dict[modal_id].get("location", "")
            event_org = modals_dict[modal_id].get("organizer", "")

        # 3. Hoc ky
        sem_idx = header_indices["semester"] if (header_indices["semester"] != -1 and header_indices["semester"] < len(cols)) else 2
        semester_txt = cols[sem_idx].get_text(strip=True) if sem_idx < len(cols) else ""

        # 4. Diem tich luy
        pts_idx = header_indices["points"] if (header_indices["points"] != -1 and header_indices["points"] < len(cols)) else 3
        points_txt = cols[pts_idx].get_text(strip=True) if pts_idx < len(cols) else ""

        # 5. Han dang ky
        dl_idx = header_indices["deadline"] if (header_indices["deadline"] != -1 and header_indices["deadline"] < len(cols)) else 4
        deadline_txt = cols[dl_idx].get_text(strip=True) if dl_idx < len(cols) else ""

        # 6. Trang thai dang ky
        reg_idx = header_indices["register"] if (header_indices["register"] != -1 and header_indices["register"] < len(cols)) else (len(cols) - 1)
        reg_col = cols[reg_idx] if reg_idx < len(cols) else cols[-1]
        reg_txt = " ".join(reg_col.get_text(" ", strip=True).split())

        # Link dang ky neu co
        reg_a = reg_col.find("a")
        register_url = ""
        if reg_a and reg_a.get("href"):
            register_url = urllib.parse.urljoin(base_url, reg_a.get("href"))

        # Trich xuat ty le so luong: (400/400)
        current_slots = None
        max_slots = None

        ratio_match = re.search(r"\(?(\d+)\s*/\s*(\d+)\)?", title_txt)
        if not ratio_match:
            ratio_match = re.search(r"\(?(\d+)\s*/\s*(\d+)\)?", row_full_text)

        if ratio_match:
            current_slots = int(ratio_match.group(1))
            max_slots = int(ratio_match.group(2))

        # Danh gia su kien co con cho dang ky khong
        is_full = False
        reg_lower = reg_txt.lower()
        if "đã đủ số lượng" in reg_lower or "đủ số lượng" in reg_lower or "hết chỗ" in reg_lower or "hết hạn" in reg_lower:
            is_full = True
        elif current_slots is not None and max_slots is not None:
            if current_slots >= max_slots:
                is_full = True

        is_available = not is_full
        available_slots = (max_slots - current_slots) if (current_slots is not None and max_slots is not None) else None

        # Clean title: loai bo phan so luong o cuoi
        cleaned_title = re.sub(r"\s*\(\s*\d+\s*/\s*\d+\s*\)\s*$", "", title_txt).strip()

        events.append({
            "stt": stt_txt,
            "raw_title": title_txt,
            "title": cleaned_title,
            "detail_url": detail_url,
            "modal_id": modal_id,
            "event_time": event_time,
            "location": event_location,
            "organizer": event_org,
            "current_slots": current_slots,
            "max_slots": max_slots,
            "available_slots": available_slots,
            "semester": semester_txt,
            "points": points_txt,
            "deadline": deadline_txt,
            "status_text": reg_txt,
            "register_url": register_url,
            "is_available": is_available
        })

    return True, events, "OK"
