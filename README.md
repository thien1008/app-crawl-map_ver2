nếu chạy ở local
mở cmd(đối với windown) tại thư mục dự án và chạy các lệnh sau:
bước 1: copy .env.example .env
bước 2: pip install -r requirements.txt
bước 3: python -m venv venv
bước 4: venv\Scripts\activate
bước 5: streamlit run app.py
bước 6: mở đường link trang web trên cmd 
bước 7: 
- Vào trang https://serper.dev/ đăng ký tài khoản, 
- Vào mục API key để lấy key, 
- Vào sidebar trang web dán api key vào mục "Nhập SERPER_API_KEY" -> dán api key vào sau đó nhấn lưu
Cách 2: 
Vào thẳng file .env đã tạo dán key vào SERPER_API_KEY=''
-> load lại trang
(hoàn thành)