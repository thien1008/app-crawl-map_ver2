import streamlit as st

def crawl_form():
    st.subheader("🔎 Thông tin tìm kiếm trên Google Maps")
    with st.form("crawl_form"):
        c1, c2 = st.columns([1, 1])
        query = c1.text_input("Từ khóa (search_query)", value="thi công bảng hiệu")
        location = c2.text_input("Khu vực (location)", value="Thành phố Hồ Chí Minh, Việt Nam")

        related = st.text_area(
            "Thêm từ khóa liên quan (mỗi từ khóa nằm trên một dòng hoặc ngăn cách bằng dấu phẩy)",
            value="",
            help="Hệ thống sẽ thêm chúng vào danh sách tìm kiếm để mở rộng phạm vi thu thập."
        )
        st.caption("Ví dụ: thi công bảng hiệu, in PP, làm hộp đèn (mỗi dòng một mục hoặc ngăn cách bằng dấu phẩy)")

        num = st.slider("Số kết quả mong muốn (tối đa 100)", 10, 100, 100, step=10)
        save_unique = st.checkbox("Không ghi đè file trùng tên, luôn tạo file mới", value=True)

        submitted = st.form_submit_button("Chạy")

    return submitted, query, location, related, num, save_unique
