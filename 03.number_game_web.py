import random
import secrets

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(16))


def render_page(message: str, tries: int, finished: bool) -> str:
    if finished:
        body = f"""
        <p class="result win">🎉 정답입니다! {tries}번 만에 맞추셨습니다.</p>
        <form action="/new" method="post">
            <button type="submit">다시 시작하기</button>
        </form>
        """
    else:
        body = f"""
        <p class="result">{message}</p>
        <p>시도 횟수: {tries}</p>
        <form action="/guess" method="post">
            <input type="number" name="guess" min="1" max="100" required autofocus>
            <button type="submit">확인</button>
        </form>
        <form action="/new" method="post">
            <button type="submit" class="secondary">새 게임</button>
        </form>
        """

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <title>숫자 맞추기 게임</title>
        <style>
            body {{ font-family: sans-serif; max-width: 400px; margin: 60px auto; text-align: center; }}
            input {{ font-size: 1.2rem; padding: 6px; width: 100px; text-align: center; }}
            button {{ font-size: 1rem; padding: 6px 16px; margin: 8px 4px; cursor: pointer; }}
            button.secondary {{ background: none; border: 1px solid #ccc; }}
            .result {{ font-size: 1.2rem; min-height: 1.5em; }}
            .win {{ color: #2a9d2a; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>1~100 숫자 맞추기</h1>
        {body}
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    if "answer" not in request.session:
        request.session["answer"] = random.randint(1, 100)
        request.session["tries"] = 0
        request.session["finished"] = False
        request.session["message"] = "숫자를 입력해서 맞춰보세요."

    return render_page(
        message=request.session["message"],
        tries=request.session["tries"],
        finished=request.session["finished"],
    )


@app.post("/guess")
def guess(request: Request, guess: int = Form(...)):
    if "answer" not in request.session or request.session.get("finished"):
        return RedirectResponse("/", status_code=303)

    request.session["tries"] += 1
    answer = request.session["answer"]

    if guess < answer:
        request.session["message"] = "더 높은 숫자입니다."
    elif guess > answer:
        request.session["message"] = "더 낮은 숫자입니다."
    else:
        request.session["finished"] = True

    return RedirectResponse("/", status_code=303)


@app.post("/new")
def new_game(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
