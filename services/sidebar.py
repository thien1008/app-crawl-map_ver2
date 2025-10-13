import hashlib
from pathlib import Path
import streamlit as st
from services.file_manager import list_output_files
from services.state import new_sidebar_render_id, bump_sel_ver, set_stop

def _hash_key(prefix: str, path: str, ver: int):
    return f"{prefix}_{ver}_" + hashlib.sha1(path.encode("utf-8","ignore")).hexdigest()[:16]

def render_outputs_sidebar(container, file_items, ver: int):
    """Vẽ danh sách file đầy đủ + checkbox theo từng file (không gộp)."""
    if not file_items:
        container.info("Chưa có file nào trong thư mục outputs.")
        return

    for it in file_items:
        c1, c2, c3 = container.columns([0.1, 0.55, 0.35])
        ck_key = _hash_key("sel", it["path"], ver)
        c1.checkbox("", key=ck_key)
        c2.markdown(f"**{it['name']}**\n\n_{it['ts_str']}_")

        # Nút tải
        try:
            with open(it["path"], "rb") as f:
                data = f.read()
        except FileNotFoundError:
            c3.error("File không còn tồn tại")
            continue

        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if it["suffix"] == ".xlsx" else \
               ("text/csv" if it["suffix"] == ".csv" else "application/octet-stream")

        dl_key = _hash_key("dl", it["path"], ver)
        c3.download_button("Tải xuống", data, file_name=it["name"], mime=mime, key=dl_key)

def render_full_sidebar(slot):
    """Vẽ toàn bộ nội dung sidebar vào đúng 'slot' (1 lần mỗi lượt)."""
    rid = new_sidebar_render_id()
    with slot.container():
        st.divider()
        st.subheader("📂 File đã tạo trước đó")

        # Nút Dừng cào (key duy nhất theo lần render)
        st.button("🛑 Dừng cào", on_click=set_stop, use_container_width=True, key=f"btn_stop_{rid}")

        colA, colB, colC = st.columns([0.34, 0.33, 0.33])
        btn_all  = colA.button("Chọn tất cả", key=f"btn_all_{rid}")
        btn_none = colB.button("Bỏ chọn", key=f"btn_none_{rid}")
        btn_del  = colC.button("Xóa đã chọn", type="primary", key=f"btn_del_{rid}")

        file_items = list_output_files()
        ver = st.session_state.get("sel_ver", 0)

        # Áp trạng thái chọn tất cả/bỏ chọn TRƯỚC khi render
        if btn_all or btn_none:
            for it in file_items:
                ck_key = _hash_key("sel", it["path"], ver)
                st.session_state[ck_key] = bool(btn_all)

        box = st.container()
        render_outputs_sidebar(box, file_items, ver)

        # Xoá đã chọn (cập nhật ngay, không rerun toàn trang)
        if btn_del:
            deleted_any = False
            errs = []
            for it in file_items:
                ck_key = _hash_key("sel", it["path"], ver)
                if st.session_state.get(ck_key, False):
                    try:
                        Path(it["path"]).unlink(missing_ok=True)
                        deleted_any = True
                    except Exception as e:
                        errs.append((it["path"], str(e)))

            if deleted_any:
                st.session_state["just_deleted"] = True
                bump_sel_ver()
                box.empty()
                render_outputs_sidebar(box, list_output_files(), st.session_state["sel_ver"])
            else:
                if not errs:
                    st.info("Không có file nào được chọn để xóa.")
            if errs:
                st.warning("Một số file không xóa được:")
                for pth, msg in errs:
                    st.text(f"- {pth}: {msg}")
