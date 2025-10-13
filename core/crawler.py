import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urlparse
from typing import Optional, Callable  # <-- thêm

# Try to import streamlit to read secrets; fall back to env if not available
try:
    import streamlit as st
except Exception:
    st = None

# ===== CẤU HÌNH =====
SCRAPING_DELAY = 1.5
API_DELAY = 1.0
REQUEST_TIMEOUT = 15

def _ensure_key():
    key = None
    if st is not None:
        try:
            key = st.secrets.get("SERPER_API_KEY")
        except Exception:
            key = None
    if not key:
        key = os.getenv("SERPER_API_KEY")
    if not key:
        raise RuntimeError("Thiếu SERPER_API_KEY (đặt trong .streamlit/secrets.toml hoặc .env).")
    headers = {"X-API-KEY": key, "Content-Type": "application/json"}
    return headers

def serper_places(payload: dict):
    headers = _ensure_key()
    r = requests.post("https://google.serper.dev/places", headers=headers, json=payload, timeout=40)
    r.raise_for_status()
    return r.json()

def serper_search(payload: dict):
    headers = _ensure_key()
    r = requests.post("https://google.serper.dev/search", headers=headers, json=payload, timeout=40)
    r.raise_for_status()
    return r.json()

# ===== XỬ LÝ URL =====
def is_valid_website_url(url):
    """Kiểm tra xem URL có phải là website hợp lệ không"""
    if not url or not isinstance(url, str) or url.strip() == "" or url == "N/A":
        return False
    
    excluded_domains = [
        'drive.google.com', 'docs.google.com', 'sheets.google.com',
        'facebook.com', 'fb.com', 'm.facebook.com',
        'instagram.com', 'youtube.com', 'youtu.be',
        'twitter.com', 'x.com', 'linkedin.com',
        'zalo.me', 'telegram.me', 't.me',
        'tiktok.com', 'shopee.vn', 'lazada.vn',
        'foursquare.com', 'goo.gl', 'bit.ly'
    ]
    
    try:
        url_str = str(url).strip()
        if not url_str.startswith(('http://', 'https://')):
            url_str = 'https://' + url_str
        
        parsed_url = urlparse(url_str.lower())
        domain = parsed_url.netloc.replace('www.', '')
        
        if not domain:
            return False
        
        for excluded in excluded_domains:
            if excluded in domain:
                return False
        
        return True
    except Exception:
        return False

def clean_and_validate_url(url):
    """Làm sạch và kiểm tra URL"""
    if not url or not isinstance(url, (str, int, float)):
        return None
    
    url_str = str(url).strip()
    if url_str == "" or url_str == "N/A" or url_str == "nan":
        return None
    
    if not url_str.startswith(('http://', 'https://')):
        url_str = 'https://' + url_str
    
    if is_valid_website_url(url_str):
        return url_str
    return None

# ===== XỬ LÝ SỐ ĐIỆN THOẠI =====
def normalize_phone_number(phone_raw):
    """Chuẩn hóa số điện thoại Việt Nam về dạng tiêu chuẩn"""
    if not phone_raw:
        return None
    
    phone_str = str(phone_raw).strip()
    cleaned = re.sub(r'[^\d+]', '', phone_str)
    
    if not cleaned:
        return None
    
    if cleaned.startswith('+84'):
        if len(cleaned) >= 12:
            cleaned = '0' + cleaned[3:]
    elif cleaned.startswith('84') and not cleaned.startswith('840'):
        if len(cleaned) >= 11:
            cleaned = '0' + cleaned[2:]
    elif cleaned.startswith('840'):
        cleaned = '0' + cleaned[3:]
    
    if len(cleaned) < 10 or len(cleaned) > 11:
        return None
    
    return cleaned

def is_valid_vietnamese_phone(phone):
    """Kiểm tra số điện thoại Việt Nam hợp lệ"""
    if not phone:
        return False
    
    normalized = normalize_phone_number(phone)
    if not normalized:
        return False
    
    valid_prefixes = {
        '032', '033', '034', '035', '036', '037', '038', '039',
        '081', '082', '083', '084', '085', '088',
        '070', '076', '077', '078', '079', '089',
        '052', '056', '058', '092',
        '059', '099',
        '087',
        '055',
        '024', '028',
        '023', '025', '026', '027', '029',
        '054', '063', '064', '065', '066', '067', '068', '069'
    }
    
    for prefix in valid_prefixes:
        if normalized.startswith(prefix):
            expected_length = 11 if len(prefix) == 3 else 10
            if len(normalized) == expected_length:
                return True
    
    old_prefixes_2_digit = ['03', '05', '07', '08', '09']
    for prefix in old_prefixes_2_digit:
        if normalized.startswith(prefix) and len(normalized) == 10:
            return True
    
    return False

def extract_phone_from_text(text):
    """Trích xuất số điện thoại từ text với độ chính xác cao"""
    if not text:
        return None
    
    phone_patterns = [
        r'(?:\+84|84)?[0]?[3-9]\d{8,9}',
        r'(?:\+84|84)?[0]?[3-9][\d\s\-\.]{8,15}',
        r'(?:hotline|phone|tel|điện\s*thoại|liên\s*hệ|gọi)[\s:]*(?:\+84|84)?[0]?[3-9][\d\s\-\.]{8,15}',
    ]
    
    potential_phones = []
    for pattern in phone_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        potential_phones.extend(matches)
    
    for phone_candidate in potential_phones:
        cleaned_phone = re.sub(r'[^\d+]', '', phone_candidate)
        if is_valid_vietnamese_phone(cleaned_phone):
            return normalize_phone_number(cleaned_phone)
    
    return None

def is_valid_email(email):
    """Kiểm tra email hợp lệ"""
    if not email:
        return False
    
    generic_emails = [
        'info@example.com', 'contact@example.com', 'admin@example.com',
        'test@test.com', 'user@domain.com', 'email@domain.com',
        'support@domain.com', 'hello@domain.com', 'admin@admin.com',
        'info@info.com', 'contact@contact.com', 'example@example.com'
    ]
    
    if email.lower() in generic_emails:
        return False
    
    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    if not re.match(email_pattern, email):
        return False
    
    excluded_domains = ['example.com', 'test.com', 'domain.com', 'email.com']
    domain = email.split('@')[1].lower()
    if domain in excluded_domains:
        return False
    
    return True

# ===== CÀO THÔNG TIN WEBSITE =====
def scrape_contact_info(url, stop_cb: Optional[Callable[[], bool]] = None):
    """Cào thông tin liên hệ với thuật toán cực mạnh"""
    phone = None
    email = None

    # cho phép thoát sớm
    if stop_cb and stop_cb():
        return phone, email
    
    clean_url = clean_and_validate_url(url)
    if not clean_url:
        return phone, email
    
    try:
        if stop_cb and stop_cb():
            return phone, email

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        response = requests.get(clean_url, timeout=REQUEST_TIMEOUT, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        if stop_cb and stop_cb():
            return phone, email

        soup = BeautifulSoup(response.text, 'html.parser')
        raw_html = response.text
        
        # ========== TÌM SỐ ĐIỆN THOẠI ==========
        phone_links = soup.find_all('a', href=re.compile(r'tel:', re.IGNORECASE))
        if phone_links and not phone:
            phone_raw = phone_links[0]['href'].replace('tel:', '').strip()
            if is_valid_vietnamese_phone(phone_raw):
                phone = normalize_phone_number(phone_raw)
        
        if not phone and stop_cb and stop_cb():
            return phone, email

        phone_data = soup.find_all(attrs={"data-phone": True}) + soup.find_all(attrs={"data-tel": True})
        for elem in phone_data:
            phone_raw = elem.get('data-phone') or elem.get('data-tel')
            if is_valid_vietnamese_phone(phone_raw):
                phone = normalize_phone_number(phone_raw)
                break
        
        if not phone and stop_cb and stop_cb():
            return phone, email

        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                if script.string:
                    data = json.loads(script.string)
                    json_str = json.dumps(data)
                    phone_from_json = extract_phone_from_text(json_str)
                    if phone_from_json:
                        phone = phone_from_json
                        break
            except json.JSONDecodeError:
                continue
        
        if not phone and stop_cb and stop_cb():
            return phone, email

        meta_tags = soup.find_all('meta', content=re.compile(r'[\d\s\-\+\(\)]{10,}'))
        for meta in meta_tags:
            phone_raw = meta.get('content', '')
            extracted_phone = extract_phone_from_text(phone_raw)
            if extracted_phone:
                phone = extracted_phone
                break
        
        if not phone and stop_cb and stop_cb():
            return phone, email

        # 5. Tìm bằng REGEX trong toàn bộ text content
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        text_content = soup.get_text()
        extracted_phone = extract_phone_from_text(text_content)
        if extracted_phone:
            phone = extracted_phone
        
        if stop_cb and stop_cb():
            return phone, email
        
        # ========== TÌM EMAIL ==========
        email_links = soup.find_all('a', href=re.compile(r'mailto:', re.IGNORECASE))
        if email_links and not email:
            email_raw = email_links[0]['href'].replace('mailto:', '').strip()
            email_raw = email_raw.split('?')[0]
            if is_valid_email(email_raw):
                email = email_raw
        
        if not email and stop_cb and stop_cb():
            return phone, email

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, text_content, re.IGNORECASE)
        for email_match in email_matches:
            if is_valid_email(email_match):
                email = email_match
                break
    
    except requests.exceptions.Timeout:
        pass
    except requests.exceptions.RequestException:
        pass
    except Exception:
        pass
    
    return phone, email

# ===== TÌM KIẾM BỔ SUNG =====
def search_business_contact(business_name, address, stop_cb: Optional[Callable[[], bool]] = None):
    """Tìm kiếm thông tin liên hệ của doanh nghiệp bằng Google Search API"""
    try:
        search_terms = [
            f'"{business_name}" "{address}" điện thoại',
            f'"{business_name}" phone contact',
            f'"{business_name}" hotline'
        ]
        
        for search_query_term in search_terms:
            if stop_cb and stop_cb():
                break

            payload = {
                "q": search_query_term,
                "gl": "vn",
                "hl": "vi",
                "num": 5
            }
            
            response = serper_search(payload)
            if stop_cb and stop_cb():
                break
            
            for result in response.get("organic", []):
                if stop_cb and stop_cb():
                    break
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                combined_text = f"{title} {snippet}"
                phone = extract_phone_from_text(combined_text)
                if phone:
                    return phone, None
            
            if stop_cb and stop_cb():
                break

            for paa in response.get("peopleAlsoAsk", []):
                if stop_cb and stop_cb():
                    break
                snippet = paa.get("snippet", "")
                phone = extract_phone_from_text(snippet)
                if phone:
                    return phone, None
            
            # delay giữa các lượt search
            if stop_cb and stop_cb():
                break
            time.sleep(API_DELAY)
    
    except Exception:
        pass
    
    return None, None

# ===== GENERATE VARIATIONS =====
def _generate_location_variations(location: str):
    """Tạo các biến thể location SIÊU MẠNH như file gốc"""
    base_locations = [location]
    # ... (giữ nguyên toàn bộ như cũ)
    if "Đà Nẵng" in location:
        base_locations.extend([
            "Đà Nẵng",
            "Da Nang",
            "Quận Hải Châu, Đà Nẵng",
            "Quận Cẩm Lệ, Đà Nẵng",
            "Quận Thanh Khê, Đà Nẵng",
            "Quận Liên Chiểu, Đà Nẵng",
            "Quận Ngũ Hành Sơn, Đà Nẵng",
            "Quận Sơn Trà, Đà Nẵng",
            "Huyện Hòa Vang, Đà Nẵng"
        ])
    elif "Hà Nội" in location:
        base_locations.extend([
            "Hà Nội",
            "Ha Noi",
            "Hanoi",
            "Quận Ba Đình, Hà Nội",
            "Quận Hoàn Kiếm, Hà Nội",
            "Quận Hai Bà Trưng, Hà Nội",
            "Quận Đống Đa, Hà Nội",
            "Quận Tây Hồ, Hà Nội",
            "Quận Cầu Giấy, Hà Nội",
            "Quận Thanh Xuân, Hà Nội"
        ])
    elif "TP.HCM" in location or "Ho Chi Minh" in location or "Sài Gòn" in location:
        base_locations.extend([
            "TP.HCM",
            "Ho Chi Minh City",
            "Sài Gòn",
            "Quận 1, TP.HCM",
            "Quận 3, TP.HCM",
            "Quận 5, TP.HCM",
            "Quận 7, TP.HCM",
            "Quận Tân Bình, TP.HCM",
            "Quận Bình Thạnh, TP.HCM"
        ])
    elif "Cần Thơ" in location:
        base_locations.extend([
            "Cần Thơ",
            "Can Tho",
            "Quận Ninh Kiều, Cần Thơ",
            "Quận Bình Thủy, Cần Thơ",
            "Quận Cái Răng, Cần Thơ",
            "Quận Ô Môn, Cần Thơ"
        ])
    elif "Hải Phòng" in location:
        base_locations.extend([
            "Hải Phòng",
            "Hai Phong",
            "Quận Hồng Bàng, Hải Phòng",
            "Quận Lê Chân, Hải Phòng",
            "Quận Ngô Quyền, Hải Phòng"
        ])
    elif "Đồng Nai" in location:
        base_locations.extend([
            "Đồng Nai",
            "Dong Nai",
            "Biên Hòa, Đồng Nai",
            "Long Khánh, Đồng Nai"
        ])
    elif "Bà Rịa" in location or "Vũng Tàu" in location:
        base_locations.extend([
            "Bà Rịa - Vũng Tàu",
            "Ba Ria Vung Tau",
            "Vũng Tàu",
            "Bà Rịa"
        ])
    else:
        location_english_map = {
            "An Giang": "An Giang",
            "Bắc Giang": "Bac Giang",
            "Bắc Kạn": "Bac Kan",
            "Bạc Liêu": "Bac Lieu",
            "Bắc Ninh": "Bac Ninh",
            "Bến Tre": "Ben Tre",
            "Bình Định": "Binh Dinh",
            "Bình Dương": "Binh Duong",
            "Bình Phước": "Binh Phuoc",
            "Bình Thuận": "Binh Thuan",
            "Cà Mau": "Ca Mau",
            "Cao Bằng": "Cao Bang",
            "Đắk Lắk": "Dak Lak",
            "Đắk Nông": "Dak Nong",
            "Điện Biên": "Dien Bien",
            "Đồng Tháp": "Dong Thap",
            "Gia Lai": "Gia Lai",
            "Hà Giang": "Ha Giang",
            "Hà Nam": "Ha Nam",
            "Hà Tĩnh": "Ha Tinh",
            "Hải Dương": "Hai Duong",
            "Hậu Giang": "Hau Giang",
            "Hòa Bình": "Hoa Binh",
            "Hưng Yên": "Hung Yen",
            "Khánh Hòa": "Khanh Hoa",
            "Kiên Giang": "Kien Giang",
            "Kon Tum": "Kon Tum",
            "Lai Châu": "Lai Chau",
            "Lâm Đồng": "Lam Dong",
            "Lạng Sơn": "Lang Son",
            "Lào Cai": "Lao Cai",
            "Long An": "Long An",
            "Nam Định": "Nam Dinh",
            "Nghệ An": "Nghe An",
            "Ninh Bình": "Ninh Binh",
            "Ninh Thuận": "Ninh Thuan",
            "Phú Thọ": "Phu Tho",
            "Phú Yên": "Phu Yen",
            "Quảng Bình": "Quang Binh",
            "Quảng Nam": "Quang Nam",
            "Quảng Ngãi": "Quang Ngai",
            "Quảng Ninh": "Quang Ninh",
            "Quảng Trị": "Quang Tri",
            "Sóc Trăng": "Soc Trang",
            "Sơn La": "Son La",
            "Tây Ninh": "Tay Ninh",
            "Thái Bình": "Thai Binh",
            "Thái Nguyên": "Thai Nguyen",
            "Thanh Hóa": "Thanh Hoa",
            "Thừa Thiên Huế": "Thua Thien Hue",
            "Tiền Giang": "Tien Giang",
            "Trà Vinh": "Tra Vinh",
            "Tuyên Quang": "Tuyen Quang",
            "Vĩnh Long": "Vinh Long",
            "Vĩnh Phúc": "Vinh Phuc",
            "Yên Bái": "Yen Bai"
        }
        
        for vn_name, en_name in location_english_map.items():
            if vn_name in location:
                base_locations.append(en_name)
                break
    
    return base_locations


def _parse_extra_keywords(text: str):
    """Tách chuỗi textarea (xuống dòng / dấu phẩy) -> list; loại trùng & trim."""
    if not text:
        return []
    parts = []
    for line in str(text).replace("\r", "").split("\n"):
        for seg in line.split(","):
            kw = seg.strip()
            if kw:
                parts.append(kw)
    seen, out = set(), []
    for kw in parts:
        if kw not in seen:
            seen.add(kw); out.append(kw)
    return out


def _generate_query_variations(query: str, _extra_keywords_text: str = None):
    """Tạo các biến thể query SIÊU MẠNH như file gốc"""
    search_variations = [
        query,
        f"{query} chuyên nghiệp",
        f"{query} uy tín",
        f"{query} giá rẻ",
        f"{query} nhanh",
        f"{query} đẹp",
    ]
    
    # Thêm từ khóa người dùng (textarea) nếu có
    try:
        for kw in _parse_extra_keywords(_extra_keywords_text):
            if kw not in search_variations:
                search_variations.append(kw)
    except Exception:
        pass
    return search_variations

def _safe_coords(place: dict):
    """Trả về (lat, lng) an toàn"""
    pos = place.get("position") or place.get("coordinates")
    if isinstance(pos, dict):
        return pos.get("lat"), pos.get("lng")
    if isinstance(pos, (list, tuple)) and len(pos) >= 2:
        return pos[0], pos[1]
    return None, None

def _unique_key(place: dict):
    """Khóa dedupe ổn định"""
    lat, lng = _safe_coords(place)
    if lat is not None and lng is not None:
        try:
            return f"{float(lat):.6f},{float(lng):.6f}"
        except Exception:
            pass
    name = str(place.get("title") or "").strip()
    address = str(place.get("address") or "").strip()
    return f"{name}||{address}"

# ===== HÀM CRAWL CHÍNH - LOGIC TỪ FILE GỐC =====
def crawl(query: str,
          location: str,
          num: int = 100,
          gl: str = "vn",
          hl: str = "vi",
          extra_keywords_text: str = None,
          stop_cb: Optional[Callable[[], bool]] = None  # <-- thêm
          ):
    """
    Thu thập dữ liệu từ Google Maps với logic SIÊU MẠNH từ crawl_map_ver5.py
    """
    target = max(1, min(int(num), 200))
    
    print(f"🎯 Đang tìm kiếm tại: {location}")
    print(f"🔍 Từ khóa: {query}")
    print(f"📊 Mục tiêu: {target} kết quả")
    
    # Tạo variations như file gốc
    base_locations = _generate_location_variations(location)
    search_variations = _generate_query_variations(query, _extra_keywords_text=extra_keywords_text)
    
    print(f"📍 Sử dụng {len(base_locations)} locations và {len(search_variations)} search variations")
    
    all_places_raw = []
    existing_places = set()
    current_results_count = 0
    stop_now = False  # <-- cờ dừng xuyên tầng

    # Chiến lược 1: Loop qua locations và search terms
    page_sizes = [20, 15, 10]
    
    for location_idx, specific_location in enumerate(base_locations, 1):
        if stop_cb and stop_cb():
            stop_now = True
        if stop_now or current_results_count >= target:
            break
        
        print(f"\n📍 Đang tìm kiếm tại {specific_location} ({location_idx}/{len(base_locations)})")
        
        for search_idx, search_term in enumerate(search_variations, 1):
            if stop_cb and stop_cb():
                stop_now = True
            if stop_now or current_results_count >= target:
                break
            
            for page_size in page_sizes:
                if stop_cb and stop_cb():
                    stop_now = True
                if stop_now or current_results_count >= target:
                    break
                
                try:
                    payload = {
                        "q": f"{search_term} in {specific_location}",
                        "gl": gl,
                        "hl": hl,
                        "num": page_size,
                        "type": "places"
                    }
                    
                    data = serper_places(payload)
                    if stop_cb and stop_cb():
                        stop_now = True
                        # không xử lý tiếp kết quả trang này
                        break

                    places_data = data.get("places", [])
                    if not isinstance(places_data, list) or not places_data:
                        # chuyển page_size khác/variation khác
                        continue
                    
                    new_places = []
                    for place in places_data:
                        if stop_cb and stop_cb():
                            stop_now = True
                            break
                        try:
                            if not isinstance(place, dict):
                                continue
                            
                            name = place.get("title", "")
                            address = place.get("address", "")
                            
                            if not isinstance(name, str):
                                name = str(name) if name is not None else ""
                            if not isinstance(address, str):
                                address = str(address) if address is not None else ""
                            
                            name = name.strip()
                            address = address.strip()
                            
                            position = place.get("position", {})
                            
                            if isinstance(position, dict) and "lat" in position and "lng" in position:
                                try:
                                    lat = float(position['lat'])
                                    lng = float(position['lng'])
                                    unique_key = f"{lat},{lng}"
                                except (ValueError, TypeError):
                                    unique_key = f"{name}||{address}"
                            else:
                                unique_key = f"{name}||{address}"
                            
                            if unique_key and unique_key not in existing_places and name and address:
                                new_places.append(place)
                                existing_places.add(unique_key)
                        
                        except Exception:
                            continue
                    
                    if stop_now:
                        break

                    if new_places:
                        all_places_raw.extend(new_places)
                        current_results_count = len(all_places_raw)
                        print(f"    ✅ Lấy được {len(new_places)} kết quả mới (page_size={page_size})")
                        print(f"    📊 Tổng cộng hiện tại: {current_results_count}")
                        # chuyển sang variation kế để tránh trùng lặp trong cùng page_size
                        break
                    else:
                        print(f"    ⚠️ Tất cả kết quả đã trùng lặp với page_size={page_size}")
                
                except Exception as e:
                    print(f"    ❌ Lỗi API với page_size={page_size}: {str(e)[:100]}...")
                    # tiếp tục thử page_size khác
                    continue
                
                # delay giữa các lần gọi — kiểm tra dừng trước khi sleep
                if stop_cb and stop_cb():
                    stop_now = True
                    break
                time.sleep(API_DELAY)
            
            # delay ngắn giữa các variation
            if stop_now:
                break
            if stop_cb and stop_cb():
                stop_now = True
                break
            time.sleep(API_DELAY * 0.5)
        
        # delay ngắn giữa các location
        if stop_now:
            break
        if stop_cb and stop_cb():
            stop_now = True
            break
        time.sleep(API_DELAY)
        print(f"  📊 Tổng kết location '{specific_location}': {current_results_count} kết quả")
    
    print(f"\n🎯 Kết thúc thu thập dữ liệu:")
    print(f"   📊 Tổng cộng: {len(all_places_raw)} kết quả unique")
    print(f"   🎯 Mục tiêu: {target}")
    print(f"   📈 Tỷ lệ hoàn thành: {len(all_places_raw)/target*100:.1f}%")
    print(f"   📍 Địa điểm tìm kiếm: {location}")
    
    if len(all_places_raw) < target and not stop_now:
        print(f"\n💡 SUGGESTIONS để lấy thêm dữ liệu:")
        print(f"   - Thử mở rộng từ khóa tìm kiếm")
        print(f"   - Thêm các quận/huyện khác của {location}")
        print(f"   - Kiểm tra API key còn quota không")
        print(f"   - Thử tăng delay giữa các requests")
    
    # ===== XỬ LÝ VÀ LÀM PHONG PHÚ DỮ LIỆU =====
    print(f"\n🔄 Bắt đầu xử lý và làm phong phú dữ liệu ({len(all_places_raw)} items)...")
    
    rows = []
    for idx, place in enumerate(all_places_raw, 1):
        if stop_cb and stop_cb():
            # dừng xử lý phần enrich, trả về phần đã có
            break

        # Lấy thông tin cơ bản từ API
        name = str(place.get("title", "")).strip()
        address = str(place.get("address", "")).strip()
        website_raw = place.get("website")
        gg_maps_link = str(place.get("link", "")).strip()
        
        # Xử lý website_url an toàn
        if website_raw and website_raw != "N/A":
            website_url = str(website_raw).strip()
        else:
            website_url = None
        
        # Chuẩn hóa số điện thoại từ API
        phone_from_api = place.get("phone") or place.get("phoneNumber")
        final_phone = None
        if phone_from_api and is_valid_vietnamese_phone(phone_from_api):
            final_phone = normalize_phone_number(phone_from_api)
        
        final_email = None
        
        # Progress indicator
        if idx % 10 == 0 or idx == 1:
            print(f"📋 Đang xử lý {idx}/{len(all_places_raw)}: {name[:50]}...")
        
        # BƯỚC 1: Cào thông tin từ website nếu có
        if is_valid_website_url(website_url):
            try:
                scraped_phone, scraped_email = scrape_contact_info(website_url, stop_cb=stop_cb)
                
                if scraped_phone and (not final_phone or len(scraped_phone) > len(final_phone)):
                    final_phone = scraped_phone
                
                if scraped_email:
                    final_email = scraped_email
                
                # kiểm tra dừng trước khi sleep
                if stop_cb and stop_cb():
                    break
                time.sleep(SCRAPING_DELAY)
            
            except Exception:
                pass
        else:
            if website_url and website_url != "N/A":
                website_url = None
        
        # BƯỚC 2: Tìm kiếm bổ sung bằng Google Search nếu chưa có SĐT
        if not final_phone and name and len(name) > 3:
            try:
                search_phone, _ = search_business_contact(name, address, stop_cb=stop_cb)
                if search_phone:
                    final_phone = search_phone
                if stop_cb and stop_cb():
                    break
                time.sleep(API_DELAY)
            except Exception:
                pass
        
        # Trích xuất thông tin khác
        rating = place.get("rating")
        reviews = place.get("reviews")
        place_type = str(place.get("type", "")).strip()
        lat, lng = _safe_coords(place)
        
        # Xử lý giờ mở cửa
        open_hours = None
        extensions = place.get("extensions", [])
        if extensions and isinstance(extensions, list):
            for ext in extensions:
                if isinstance(ext, str) and any(keyword in ext.lower() for keyword in ["giờ", "mở", "đóng", "hour", "open", "close", "24"]):
                    open_hours = ext
                    break
            if not open_hours and extensions:
                open_hours = str(extensions[0])
        
        # Chuẩn hóa dữ liệu đầu ra
        rows.append({
            "name": name if name else None,
            "address": address if address else None,
            "lat": lat,
            "lng": lng,
            "website": website_url,
            "rating": rating,
            "reviews": reviews,
            "type": place_type if place_type else None,
            "open_hours": open_hours,
            "phone": final_phone,
            "emails": final_email,
            "google_maps_link": gg_maps_link if gg_maps_link else None
        })
    
    print(f"\n🎉 Hoàn thành xử lý dữ liệu!")
    print(f"📊 Tổng cộng: {len(rows)} kết quả")
    
    # Tạo DataFrame
    df = pd.DataFrame(rows)
    
    # Thống kê chất lượng dữ liệu
    if not df.empty:
        total_records = len(df)
        total_with_phone = len(df[df['phone'].notna()])
        total_with_email = len(df[df['emails'].notna()])
        total_with_website = len(df[df['website'].notna()])
        total_with_rating = len(df[df['rating'].notna()])
        
        print(f"\n{'='*60}")
        print("📊 THỐNG KÊ CHẤT LƯỢNG DỮ LIỆU")
        print(f"{'='*60}")
        print(f"📋 Tổng số kết quả: {total_records}")
        print(f"📞 Có số điện thoại: {total_with_phone}/{total_records} ({total_with_phone/total_records*100:.1f}%)")
        print(f"📧 Có email: {total_with_email}/{total_records} ({total_with_email/total_records*100:.1f}%)")
        print(f"🌐 Có website: {total_with_website}/{total_records} ({total_with_website/total_records*100:.1f}%)")
        print(f"⭐ Có đánh giá: {total_with_rating}/{total_records} ({total_with_rating/total_records*100:.1f}%)")
        print(f"{'='*60}")
    
    return df
