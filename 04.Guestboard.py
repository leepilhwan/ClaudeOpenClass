import hashlib
import html
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "Guestboard.json"

MAX_NAME_LEN = 20
MAX_MESSAGE_LEN = 500

app = FastAPI()
_lock = threading.Lock()


def load_entries() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_entries(entries: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def render_entry(entry: dict) -> str:
    name = html.escape(entry["name"])
    message = html.escape(entry["message"]).replace("\n", "<br>")
    created_at = entry["created_at"]
    initial = html.escape(entry["name"][0].upper())
    has_password = bool(entry.get("password_hash"))

    delete_form = ""
    if has_password:
        delete_form = f"""
        <details class="delete-box">
            <summary>삭제</summary>
            <form action="/delete/{entry['id']}" method="post" class="delete-form">
                <input type="password" name="password" placeholder="비밀번호" required>
                <button type="submit">삭제</button>
            </form>
        </details>
        """

    return f"""
    <li class="entry">
        <div class="avatar">{initial}</div>
        <div class="entry-body">
            <div class="entry-header">
                <span class="entry-name">{name}</span>
                <span class="entry-date">{created_at}</span>
            </div>
            <p class="entry-message">{message}</p>
            {delete_form}
        </div>
    </li>
    """


def render_page(entries: list[dict], error: Optional[str] = None) -> str:
    if entries:
        items = "\n".join(render_entry(e) for e in reversed(entries))
        list_html = f'<ul class="entry-list">{items}</ul>'
    else:
        list_html = '<p class="empty">아직 방명록이 없습니다. 첫 번째 글을 남겨보세요! 🌱</p>'

    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>방명록</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --green-900: #1b4332;
                --green-700: #2d6a4f;
                --green-600: #40916c;
                --green-500: #52b788;
                --green-300: #95d5b2;
                --green-100: #d8f3dc;
                --green-50: #f1faf4;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                font-family: 'Noto Sans KR', sans-serif;
                background: var(--green-50);
                color: #1b1b1b;
                min-height: 100vh;
                padding-bottom: 60px;
            }}
            header {{
                background: linear-gradient(135deg, var(--green-700), var(--green-500));
                color: white;
                padding: 48px 20px 64px;
                text-align: center;
                box-shadow: 0 4px 20px rgba(27, 67, 50, 0.25);
            }}
            header h1 {{
                margin: 0 0 8px;
                font-size: 2.2rem;
                letter-spacing: 1px;
            }}
            header p {{
                margin: 0;
                opacity: 0.9;
            }}
            .container {{
                max-width: 640px;
                margin: -40px auto 0;
                padding: 0 20px;
            }}
            .write-card {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 10px 30px rgba(27, 67, 50, 0.12);
                padding: 24px;
                margin-bottom: 32px;
            }}
            .write-card h2 {{
                margin: 0 0 16px;
                font-size: 1.1rem;
                color: var(--green-900);
            }}
            .form-row {{
                display: flex;
                gap: 10px;
                margin-bottom: 10px;
            }}
            input, textarea, button {{
                font-family: inherit;
                font-size: 0.95rem;
            }}
            input[type="text"], input[type="password"] {{
                flex: 1;
                padding: 10px 12px;
                border: 1.5px solid var(--green-100);
                border-radius: 8px;
                outline: none;
                transition: border-color 0.15s;
                min-width: 0;
            }}
            input[type="text"]:focus, input[type="password"]:focus, textarea:focus {{
                border-color: var(--green-500);
            }}
            textarea {{
                width: 100%;
                min-height: 90px;
                padding: 10px 12px;
                border: 1.5px solid var(--green-100);
                border-radius: 8px;
                outline: none;
                resize: vertical;
                margin-bottom: 12px;
                transition: border-color 0.15s;
            }}
            textarea:focus {{ border-color: var(--green-500); }}
            .submit-btn {{
                display: block;
                width: 100%;
                padding: 12px;
                background: var(--green-600);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                cursor: pointer;
                transition: background 0.15s;
            }}
            .submit-btn:hover {{ background: var(--green-700); }}
            .hint {{
                font-size: 0.78rem;
                color: #888;
                margin: 6px 0 0;
            }}
            .error {{
                color: #c0392b;
                background: #fdecea;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 0.9rem;
                margin: 0 0 16px;
            }}
            .entry-list {{
                list-style: none;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                gap: 14px;
            }}
            .entry {{
                background: white;
                border-radius: 14px;
                box-shadow: 0 4px 16px rgba(27, 67, 50, 0.08);
                padding: 18px;
                display: flex;
                gap: 14px;
                align-items: flex-start;
            }}
            .avatar {{
                flex-shrink: 0;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: linear-gradient(135deg, var(--green-500), var(--green-300));
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
            }}
            .entry-body {{ flex: 1; min-width: 0; }}
            .entry-header {{
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                gap: 8px;
                flex-wrap: wrap;
            }}
            .entry-name {{
                font-weight: 700;
                color: var(--green-900);
            }}
            .entry-date {{
                font-size: 0.78rem;
                color: #999;
            }}
            .entry-message {{
                margin: 8px 0 0;
                line-height: 1.5;
                word-break: break-word;
                white-space: pre-wrap;
            }}
            .delete-box {{
                margin-top: 10px;
            }}
            .delete-box summary {{
                cursor: pointer;
                font-size: 0.78rem;
                color: #aaa;
                width: fit-content;
            }}
            .delete-box summary:hover {{ color: var(--green-600); }}
            .delete-form {{
                display: flex;
                gap: 6px;
                margin-top: 8px;
            }}
            .delete-form input {{
                flex: 1;
                padding: 6px 10px;
                border: 1.5px solid var(--green-100);
                border-radius: 6px;
                font-size: 0.85rem;
            }}
            .delete-form button {{
                padding: 6px 12px;
                border: none;
                border-radius: 6px;
                background: #e57373;
                color: white;
                cursor: pointer;
            }}
            .delete-form button:hover {{ background: #d75c5c; }}
            .empty {{
                text-align: center;
                color: #888;
                padding: 40px 0;
            }}
            .count-badge {{
                display: inline-block;
                background: var(--green-100);
                color: var(--green-700);
                font-size: 0.8rem;
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 999px;
                margin-bottom: 12px;
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>🌿 방명록</h1>
            <p>다녀가신 흔적을 남겨주세요</p>
        </header>
        <div class="container">
            <div class="write-card">
                <h2>글 남기기</h2>
                {error_html}
                <form action="/write" method="post">
                    <div class="form-row">
                        <input type="text" name="name" placeholder="이름" maxlength="{MAX_NAME_LEN}" required>
                        <input type="password" name="password" placeholder="비밀번호 (삭제 시 필요, 선택)" maxlength="50">
                    </div>
                    <textarea name="message" placeholder="방명록에 남길 메시지를 적어주세요." maxlength="{MAX_MESSAGE_LEN}" required></textarea>
                    <button type="submit" class="submit-btn">남기기</button>
                    <p class="hint">비밀번호를 입력하면 나중에 본인 글을 삭제할 수 있어요.</p>
                </form>
            </div>
            <span class="count-badge">전체 {len(entries)}개의 글</span>
            {list_html}
        </div>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def index():
    return render_page(load_entries())


@app.post("/write")
def write(
    name: str = Form(...),
    message: str = Form(...),
    password: str = Form(""),
    request: Request = None,
):
    name = name.strip()[:MAX_NAME_LEN]
    message = message.strip()[:MAX_MESSAGE_LEN]

    if not name or not message:
        return HTMLResponse(render_page(load_entries(), error="이름과 메시지를 모두 입력해주세요."))

    with _lock:
        entries = load_entries()
        entries.append(
            {
                "id": uuid.uuid4().hex,
                "name": name,
                "message": message,
                "password_hash": hash_password(password) if password else None,
                "ip": get_client_ip(request),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        )
        save_entries(entries)

    return RedirectResponse("/", status_code=303)


@app.post("/delete/{entry_id}")
def delete(entry_id: str, password: str = Form("")):
    with _lock:
        entries = load_entries()
        target = next((e for e in entries if e["id"] == entry_id), None)

        if target is None:
            return RedirectResponse("/", status_code=303)

        if not target.get("password_hash") or target["password_hash"] != hash_password(password):
            return HTMLResponse(render_page(entries, error="비밀번호가 일치하지 않습니다."))

        entries = [e for e in entries if e["id"] != entry_id]
        save_entries(entries)

    return RedirectResponse("/", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
