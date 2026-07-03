import json
import os
import re
import time
import uuid

import streamlit as st

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json")
CATEGORIES = ["업무", "개인", "쇼핑", "기타"]
FILTER_OPTIONS = ["전체보기", "★ 중요"] + CATEGORIES

CATEGORY_KEYWORDS = {
    "업무": ["회의", "미팅", "보고서", "발표", "프로젝트", "이메일", "메일", "출장",
            "계약", "회사", "클라이언트", "마감", "기획", "결재", "협업", "야근",
            "출근", "퇴근", "업무", "면접", "세미나"],
    "개인": ["운동", "헬스", "병원", "약속", "가족", "친구", "생일", "취미", "독서",
            "여행", "휴가", "산책", "다이어트", "공부", "학원", "청소", "빨래",
            "약", "미용실", "영화"],
    "쇼핑": ["구매", "쇼핑", "주문", "택배", "장보기", "마트", "온라인", "결제",
            "배송", "세일", "환불", "교환", "영수증", "쿠팡", "장바구니", "옷"],
}

st.set_page_config(page_title="할 일 관리", page_icon="✅", layout="centered")

st.markdown(
    """
    <style>
    div[data-testid="stProgress"] > div > div > div > div {
        background-image: linear-gradient(90deg, #3b82f6, #22c55e);
        transition: width 0.4s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 2px 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def create_sample_todos():
    now = time.time()
    return [
        {"id": "s1", "text": "이 앱 사용법 둘러보기", "category": "개인",
         "isImportant": True, "isDone": False, "createdAt": now},
        {"id": "s2", "text": "카테고리 탭을 눌러 필터링 해보기", "category": "업무",
         "isImportant": False, "isDone": False, "createdAt": now + 1},
        {"id": "s3", "text": "완료한 할 일은 체크박스로 표시", "category": "기타",
         "isImportant": False, "isDone": True, "createdAt": now + 2},
    ]


def save_todos(todos):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def load_todos():
    if not os.path.exists(DATA_FILE):
        todos = create_sample_todos()
        save_todos(todos)
        return todos

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, list):
            raise ValueError("todos.json must contain a list")

        cleaned = []
        for item in raw:
            if not isinstance(item, dict) or "id" not in item:
                continue
            cleaned.append({
                "id": str(item.get("id")),
                "text": item.get("text") if isinstance(item.get("text"), str) else "",
                "category": item.get("category") if item.get("category") in CATEGORIES else CATEGORIES[-1],
                "isImportant": bool(item.get("isImportant", False)),
                "isDone": bool(item.get("isDone", False)),
                "createdAt": item.get("createdAt") if isinstance(item.get("createdAt"), (int, float)) else 0,
            })
        return cleaned
    except (json.JSONDecodeError, ValueError, OSError):
        todos = create_sample_todos()
        save_todos(todos)
        return todos


def escape_markdown(text):
    return re.sub(r"([\\`*_{}\[\]()#+\-.!~>])", r"\\\1", text)


def classify_category(text):
    """키워드 매칭 기반으로 텍스트에 어울리는 카테고리를 추정한다. 매칭이 없으면 '기타'."""
    lowered = text.lower()
    scores = {cat: 0 for cat in CATEGORIES}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lowered:
                scores[cat] += 1
    best_cat = max(scores, key=lambda c: scores[c])
    return best_cat if scores[best_cat] > 0 else "기타"


def get_filtered(todos, filt):
    if filt == "전체보기":
        return todos
    if filt == "★ 중요":
        return [t for t in todos if t["isImportant"]]
    return [t for t in todos if t["category"] == filt]


def is_visible_under(item, filt):
    if filt == "전체보기":
        return True
    if filt == "★ 중요":
        return item["isImportant"]
    return item["category"] == filt


def sort_key(todo):
    if todo["isDone"]:
        weight = 2
    elif todo["isImportant"]:
        weight = 0
    else:
        weight = 1
    return (weight, -todo["createdAt"])


if "todos" not in st.session_state:
    st.session_state.todos = load_todos()
if "filter" not in st.session_state:
    st.session_state.filter = "전체보기"
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None
if "_pending_filter" in st.session_state:
    st.session_state.filter = st.session_state.pop("_pending_filter")

todos = st.session_state.todos

st.markdown("<h1 style='text-align:center;'>✅ 할 일 관리</h1>", unsafe_allow_html=True)

# ---- 진행률 바 (현재 필터 기준 실시간 계산) ----
filtered_for_progress = get_filtered(todos, st.session_state.filter)
total = len(filtered_for_progress)
done_count = sum(1 for t in filtered_for_progress if t["isDone"])
pct = int(round((done_count / total) * 100)) if total else 0

progress_top = st.columns([3, 1])
progress_top[0].caption(f"{done_count} / {total} 완료")
progress_top[1].markdown(f"<div style='text-align:right; font-size:20px; font-weight:700; color:#3b82f6;'>{pct}%</div>", unsafe_allow_html=True)
st.progress(pct / 100)

# ---- 카테고리 / 중요 필터 탭 ----
st.radio(
    "필터",
    FILTER_OPTIONS,
    horizontal=True,
    label_visibility="collapsed",
    key="filter",
)

# ---- 할 일 추가 폼 ----
default_category_index = CATEGORIES.index(st.session_state.filter) if st.session_state.filter in CATEGORIES else 0
default_important = st.session_state.filter == "★ 중요"

auto_classify = st.checkbox("🤖 입력 내용을 분석해 카테고리 자동 분류", value=True, key="auto_classify")

with st.form("add_form", clear_on_submit=True):
    if auto_classify:
        cols = st.columns([5, 2, 1.3])
        new_text = cols[0].text_input(
            "할 일", placeholder="할 일을 입력하세요 (카테고리는 자동으로 분류됩니다)", label_visibility="collapsed",
        )
        new_important = cols[1].checkbox(
            "★ 중요", value=default_important, key=f"important_check_{st.session_state.filter}",
        )
        submitted = cols[2].form_submit_button("추가")
        new_category = None
    else:
        cols = st.columns([4, 2, 2, 1.3])
        new_text = cols[0].text_input("할 일", placeholder="할 일을 입력하세요", label_visibility="collapsed")
        new_category = cols[1].selectbox(
            "카테고리", CATEGORIES, index=default_category_index,
            key=f"category_select_{st.session_state.filter}", label_visibility="collapsed",
        )
        new_important = cols[2].checkbox(
            "★ 중요", value=default_important, key=f"important_check_{st.session_state.filter}",
        )
        submitted = cols[3].form_submit_button("추가")

    if submitted:
        text_clean = new_text.strip()
        if text_clean:
            final_category = classify_category(text_clean) if auto_classify else new_category
            new_item = {
                "id": uuid.uuid4().hex,
                "text": text_clean,
                "category": final_category,
                "isImportant": new_important,
                "isDone": False,
                "createdAt": time.time(),
            }
            todos.append(new_item)
            save_todos(todos)

            if auto_classify:
                st.toast(f"'{final_category}' 카테고리로 자동 분류되었습니다.", icon="🤖")

            # 방금 추가한 항목이 현재 필터에서 보이지 않으면 전체보기로 전환해 즉시 확인 가능하게 함
            if not is_visible_under(new_item, st.session_state.filter):
                st.session_state["_pending_filter"] = "전체보기"

            st.rerun()

# ---- 할 일 목록 (정렬: 미완료&중요 -> 미완료&일반 -> 완료) ----
filtered = get_filtered(todos, st.session_state.filter)
sorted_todos = sorted(filtered, key=sort_key)

if not sorted_todos:
    st.caption("표시할 할 일이 없습니다.")
else:
    for todo in sorted_todos:
        tid = todo["id"]
        with st.container(border=True):
            row = st.columns([0.6, 0.6, 5, 0.7, 0.7])

            done_val = row[0].checkbox(
                "완료", value=todo["isDone"], key=f"done_{tid}", label_visibility="collapsed",
            )
            if done_val != todo["isDone"]:
                todo["isDone"] = done_val
                save_todos(todos)
                st.rerun()

            star_label = "★" if todo["isImportant"] else "☆"
            if row[1].button(star_label, key=f"star_{tid}", help="중요 토글"):
                todo["isImportant"] = not todo["isImportant"]
                save_todos(todos)
                st.rerun()

            if st.session_state.editing_id == tid:
                edit_val = row[2].text_input(
                    "수정", value=todo["text"], key=f"edit_input_{tid}", label_visibility="collapsed",
                )
                if row[3].button("저장", key=f"save_{tid}"):
                    trimmed = edit_val.strip()
                    if trimmed:
                        todo["text"] = trimmed
                    st.session_state.editing_id = None
                    save_todos(todos)
                    st.rerun()
                if row[4].button("취소", key=f"cancel_{tid}"):
                    st.session_state.editing_id = None
                    st.rerun()
            else:
                safe_text = escape_markdown(todo["text"])
                text_display = f"~~{safe_text}~~" if todo["isDone"] else safe_text
                badge = " :orange[★]" if todo["isImportant"] else ""
                row[2].markdown(f"{text_display}{badge}  \n:gray[{todo['category']}]")

                if row[3].button("✏️", key=f"edit_{tid}", help="수정"):
                    st.session_state.editing_id = tid
                    st.rerun()
                if row[4].button("✕", key=f"del_{tid}", help="삭제"):
                    st.session_state.todos = [t for t in todos if t["id"] != tid]
                    save_todos(st.session_state.todos)
                    st.rerun()
