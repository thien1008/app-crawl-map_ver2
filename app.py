import streamlit as st
from services.state import init_state

st.set_page_config(page_title="Cào Google Maps", layout="wide")
init_state()

st.title("Cào địa điểm từ Google Maps")
st.markdown("""
Chọn trang ở thanh **Pages** bên trái:

- **🗺️ Crawl**: nhập từ khóa, khu vực → chạy cào → xem bảng kết quả → lưu Excel.
- **📂 Files**: xem các file đã tạo, tải xuống, chọn/xóa nhiều file.

""")

st.markdown("""
<style>
a[data-testid="stDeployButton"] { display: none !important; }
button[title="Deploy this app"] { display: none !important; }
button[aria-label="Deploy this app"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }   /* đã bật */
</style>
""", unsafe_allow_html=True)