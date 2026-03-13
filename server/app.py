import os
import re
import tempfile
import requests
import pandas as pd
import camelot

from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Allow GitHub Pages to call this API
# You can restrict this later to your exact Pages domain.
CORS(app, resources={r"/api/*": {"origins": "*"}})

MAX_PDF_MB = 15

def drive_preview_to_download(url: str) -> str:
    """
    Converts:
      https://drive.google.com/file/d/<ID>/preview
    to:
      https://drive.google.com/uc?export=download&id=<ID>
    """
    m = re.search(r"drive\.google\.com\/file\/d\/([^\/]+)\/", url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

def download_pdf(url: str) -> bytes:
    # Basic validation
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("Only http/https URLs are allowed.")

    s = requests.Session()
    r = s.get(url, timeout=40, allow_redirects=True)
    r.raise_for_status()

    content_type = (r.headers.get("content-type") or "").lower()

    # If Drive returns an HTML page instead of a PDF, it's usually permissions.
    if "text/html" in content_type:
        raise ValueError(
            "Drive returned HTML instead of a PDF. "
            "Make sure the file is shared as 'Anyone with the link can view'."
        )

    size = len(r.content)
    if size > MAX_PDF_MB * 1024 * 1024:
        raise ValueError(f"PDF too large ({size/1024/1024:.1f}MB). Limit is {MAX_PDF_MB}MB.")

    return r.content

def tables_to_responsive_html(tables) -> str:
    parts = []
    parts.append("""
    <style>
      .pdf-section{margin:10px 0 18px}
      .pdf-title{margin:0 0 10px;font:700 14px ui-sans-serif,system-ui;color:#cfe0ff}
      .pdf-table{width:100%;border-collapse:collapse}
      .pdf-table td,.pdf-table th{border:1px solid rgba(255,255,255,.10);padding:8px 10px;font-size:13px}
      .pdf-table thead th{background:rgba(17,26,46,.92);text-align:left}
    </style>
    """)

    for i, t in enumerate(tables):
        df = t.df.copy()

        # Optional cleanup: remove fully empty rows
        df = df.replace(r"^\s*$", "", regex=True)
        df = df.loc[~(df == "").all(axis=1)]

        html_table = df.to_html(index=False, header=True, classes="pdf-table", border=0, escape=True)
        parts.append(f'<div class="pdf-section"><div class="pdf-title">Table {i+1}</div>{html_table}</div>')

    return "\n".join(parts)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/convert")
def convert():
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "").strip()
    flavor = (data.get("flavor") or "stream").strip()

    if flavor not in ("stream", "lattice"):
        return Response("Invalid flavor. Use 'stream' or 'lattice'.", status=400)

    try:
        pdf_url = drive_preview_to_download(url)
        pdf_bytes = download_pdf(pdf_url)

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(pdf_bytes)
            f.flush()

            # Camelot extracts tables from text-based PDFs [Source]
            # https://camelot-py.readthedocs.io/en/master/user/how-it-works.html
            tables = camelot.read_pdf(f.name, pages="all", flavor=flavor)

        if tables.n == 0:
            return Response(
                "No tables detected. Try switching mode stream/lattice. "
                "If the PDF is scanned (image-only), you need OCR first.",
                status=422
            )

        html = tables_to_responsive_html(tables)
        return Response(html, mimetype="text/html")

    except Exception as e:
        return Response(str(e), status=400)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
