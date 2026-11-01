"""文献カード検索 bibcard

読んだ論文・本を「文献カード」（タイトル・著者・年・出典・キーワード・
メモ）として登録し、キーワードで探せるようにするツール。検索は
タイトル・著者・キーワードへの部分一致のみで、外部AIは使わない。
データは SQLite に保存する。単一ファイル Flask + SQLite。
"""
import os
import sqlite3

from flask import Flask, g, jsonify, redirect, render_template_string, request, url_for

app = Flask(__name__)
DB_PATH = os.environ.get("BIBCARD_DB", os.path.join(os.path.dirname(__file__), "bibcard.db"))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            authors TEXT NOT NULL DEFAULT '',
            year TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            keywords TEXT NOT NULL DEFAULT '',
            memo TEXT NOT NULL DEFAULT ''
        );
        """
    )
    db.commit()
    db.close()


def search_cards(db, q):
    q = (q or "").strip()
    if not q:
        return db.execute("SELECT * FROM cards ORDER BY id DESC").fetchall()
    like = f"%{q}%"
    return db.execute(
        "SELECT * FROM cards WHERE title LIKE ? OR authors LIKE ? OR keywords LIKE ? "
        "ORDER BY id DESC",
        (like, like, like),
    ).fetchall()


PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>文献カード検索</title>
<style>body{font-family:sans-serif;max-width:680px;margin:2em auto;padding:0 1em}
.card{border:1px solid #ccc;border-radius:8px;padding:.8em;margin:.8em 0}
.meta{color:#555;font-size:.9em}
input[type=text],textarea{width:100%;box-sizing:border-box;margin:.2em 0}
textarea{width:100%}</style>
</head><body>
<h1>文献カード検索</h1>
<p>読んだ文献をカードで登録して、キーワードで探せるようにするツールです。外部AIは使わず、登録したカードの中だけを検索します。</p>

<h2>文献カードを登録</h2>
<form method="post" action="{{ url_for('add') }}">
  <label>タイトル<input type="text" name="title" required></label>
  <label>著者<input type="text" name="authors" placeholder="例：山田太郎・佐藤花子"></label>
  <label>年<input type="text" name="year" placeholder="例：2024"></label>
  <label>出典<input type="text" name="source" placeholder="例：〇〇学会誌 12(3)"></label>
  <label>キーワード<input type="text" name="keywords" placeholder="例：自己調整学習, フィードバック"></label>
  <label>メモ</label><textarea name="memo" rows="2"></textarea>
  <button type="submit">登録する</button>
</form>

<h2>カード一覧</h2>
<form method="get" action="{{ url_for('index') }}">
  <input type="text" name="q" value="{{ q }}" placeholder="タイトル・著者・キーワードで検索">
  <button type="submit">検索</button>
  {% if q %}<a href="{{ url_for('index') }}">検索をクリア</a>{% endif %}
</form>
{% for c in cards %}
<div class="card">
  <strong>{{ c.title }}</strong>
  <div class="meta">{{ c.authors }}{% if c.year %}（{{ c.year }}）{% endif %}{% if c.source %}／{{ c.source }}{% endif %}</div>
  {% if c.keywords %}<div class="meta">キーワード：{{ c.keywords }}</div>{% endif %}
  {% if c.memo %}<div>{{ c.memo }}</div>{% endif %}
  <form method="post" action="{{ url_for('delete', cid=c.id) }}" onsubmit="return confirm('この文献カードを削除しますか？')"><button type="submit">削除</button></form>
</div>
{% else %}
<p>文献カードがありません{% if q %}（検索条件：{{ q }}）{% endif %}。</p>
{% endfor %}
</body></html>"""


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    db = get_db()
    q = request.args.get("q", "")
    return render_template_string(PAGE, cards=search_cards(db, q), q=q)


@app.route("/add", methods=["POST"])
def add():
    title = (request.form.get("title") or "").strip()
    if title:
        db = get_db()
        db.execute(
            "INSERT INTO cards(title, authors, year, source, keywords, memo) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (
                title,
                (request.form.get("authors") or "").strip(),
                (request.form.get("year") or "").strip(),
                (request.form.get("source") or "").strip(),
                (request.form.get("keywords") or "").strip(),
                (request.form.get("memo") or "").strip(),
            ),
        )
        db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:cid>", methods=["POST"])
def delete(cid):
    db = get_db()
    db.execute("DELETE FROM cards WHERE id = ?", (cid,))
    db.commit()
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
