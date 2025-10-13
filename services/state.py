import streamlit as st

def init_state():
    defaults = {
        "sb_render_i": 0,   # đếm số lần render sidebar để sinh key cho button
        "sel_ver": 0,       # version để đổi key checkbox/download
        "stop_crawl": False,
        "just_saved": False,
        "just_deleted": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def new_sidebar_render_id() -> int:
    st.session_state["sb_render_i"] += 1
    return st.session_state["sb_render_i"]

def bump_sel_ver():
    st.session_state["sel_ver"] += 1

def set_stop():
    st.session_state["stop_crawl"] = True

def should_stop() -> bool:
    return st.session_state.get("stop_crawl", False)
