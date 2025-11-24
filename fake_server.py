# fake_server.py
# Simple FastAPI server that hosts 4 fake quiz pages and a /fake-submit endpoint
# Run: python fake_server.py
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn
import json
import base64
import gzip
import io
import os

app = FastAPI()

# === Config / expected answers (simple, deterministic) ===
# PDF Sum Task: numbers: 10, 20, 30 -> sum = 60
PDF_SUM_ANSWER = 10 + 20 + 30

# Image OCR Task: the page will ask for the single number 777
IMAGE_OCR_ANSWER = 777

# Audio Task: the audio "transcript" will contain numbers 3,4,5 -> sum = 12
AUDIO_ANSWER = 3 + 4 + 5

# Deeply hidden puzzle: decode gzipped json -> return field "secret_sum" which is 42
PUZZLE_ANSWER = 42

# Local path from conversation history (developer note). We insert it into HTML where requested.
LOCAL_IMAGE_PATH = "/mnt/data/5c3302c6-d159-4ece-bc3a-1b837d5d9516.png"

# ----------------------------
# Helper: page templates
# ----------------------------
def wrap_atob(payload_str: str):
    b = payload_str.encode("utf-8")
    return base64.b64encode(b).decode("ascii")

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse("<h3>Fake TDS Quiz Server (for local testing)</h3>"
                        "<ul>"
                        "<li><a href='/pdf-demo'>PDF Sum Demo</a></li>"
                        "<li><a href='/image-demo'>Image OCR Demo</a></li>"
                        "<li><a href='/audio-demo'>Audio Demo</a></li>"
                        "<li><a href='/puzzle-demo'>Deeply Hidden Puzzle Demo</a></li>"
                        "</ul>")

# ----------------------------
# PDF Sum Task page
# - instructs student to download a CSV (we'll embed the CSV as a data: URL inside the base64 payload)
# ----------------------------
@app.get("/pdf-demo", response_class=HTMLResponse)
async def pdf_demo():
    # Build a small CSV and base64-encode it for demonstration (the real exercise expects a downloadable file link)
    csv_text = "name,value\nA,10\nB,20\nC,30\n"
    csv_b64 = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    # The instruction asks to POST the sum to /fake-submit
    instr = json.dumps({
        "question": "Download file. What is the sum of the 'value' column in the CSV?",
        "file_data_uri": f"data:text/csv;base64,{csv_b64}",
        "submit_url": "/fake-submit",
        "submit_payload_template": {"email": "<email>", "secret": "<secret>", "url": "http://localhost:8001/pdf-demo", "answer": "<sum>"}
    }, indent=2)
    # embed via atob (base64) so your solver must decode from JS like TDS pages do
    s = wrap_atob(instr)
    html = f"""
    <div id="result"></div>
    <script>
      // demo: page shows base64 payload inside atob(...) to mimic TDS
      document.querySelector("#result").innerHTML = atob(`{s}`);
    </script>
    """
    return HTMLResponse(html)

# ----------------------------
# Image OCR Task page
# - contains an atob that instructs to download the image from a local path (developer-supplied)
# ----------------------------
@app.get("/image-demo", response_class=HTMLResponse)
async def image_demo():
    # The page instructs to read the image at the LOCAL_IMAGE_PATH and OCR it.
    instr = json.dumps({
        "question": "Open the image at the provided local path and OCR to find the number. Post it to /fake-submit",
        "image_path": LOCAL_IMAGE_PATH,
        "submit_url": "/fake-submit",
        "submit_payload_template": {"email": "<email>", "secret": "<secret>", "url": "http://localhost:8001/image-demo", "answer": "<number>"}
    }, indent=2)
    s = wrap_atob(instr)
    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{s}`);
    </script>
    <p>Note: For this demo the expected OCR result is <strong>{IMAGE_OCR_ANSWER}</strong>. 
    The image path embedded (local) is: <code>{LOCAL_IMAGE_PATH}</code></p>
    """
    return HTMLResponse(html)

# ----------------------------
# Audio Task page
# - contains an atob with an audio file path embedded (we simulate by sending a small text "audio")
# ----------------------------
@app.get("/audio-demo", response_class=HTMLResponse)
async def audio_demo():
    # For demo simplicity, we give a tiny "data" audio URI (text) — the solver should try to fetch the audio link
    # and then transcribe. We'll instruct the expected sum in the page comments.
    instr = json.dumps({
        "question": "Fetch the audio file at the given link and transcribe its numbers, sum them and POST.",
        "audio_data_uri": "data:audio/wav;base64," + base64.b64encode(b"SIMULATED AUDIO: numbers 3 4 5").decode("ascii"),
        "submit_url": "/fake-submit",
        "submit_payload_template": {"email": "<email>", "secret": "<secret>", "url": "http://localhost:8001/audio-demo", "answer": "<sum>"}
    }, indent=2)
    s = wrap_atob(instr)
    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{s}`);
    </script>
    <p>Note: expected answer for demo = <strong>{AUDIO_ANSWER}</strong></p>
    """
    return HTMLResponse(html)

# ----------------------------
# Deeply Hidden JS / atob puzzle
# - returns a base64 of gzipped JSON in a nested atob to mimic more complex obfuscation
# ----------------------------
@app.get("/puzzle-demo", response_class=HTMLResponse)
async def puzzle_demo():
    payload = {"instructions": "Decode gzip+base64 then read 'secret_sum' and POST it", "secret_sum": PUZZLE_ANSWER}
    js = json.dumps(payload).encode("utf-8")
    gz = gzip.compress(js)
    gz_b64 = base64.b64encode(gz).decode("ascii")
    # We'll create nested JS: atob -> inflate(gzip) simulated by solver having to fetch base64, decode & gunzip.
    instr = f"""
    {{
      "payload_gz_b64": "{gz_b64}",
      "hint": "base64 of gzipped JSON; decode and gunzip to reveal secret_sum",
      "submit_url": "/fake-submit",
      "submit_payload_template": {{ "email":"<email>", "secret":"<secret>", "url":"http://localhost:8001/puzzle-demo", "answer":"<secret_sum>" }}
    }}
    """
    s = wrap_atob(instr)
    html = f"""
    <div id="result"></div>
    <script>
      // nested atob to mimic obfuscation
      document.querySelector("#result").innerHTML = atob(`{s}`);
    </script>
    <p>Note: expected answer for demo = <strong>{PUZZLE_ANSWER}</strong></p>
    """
    return HTMLResponse(html)

# ----------------------------
# Fake submit endpoint: validates and returns "correct" based on our expected answers above.
# This endpoint mimics the grader: returns {"correct": bool, "url": next_url or None, "reason": ...}
# ----------------------------
@app.post("/fake-submit")
async def fake_submit(req: Request):
    try:
        data = await req.json()
    except:
        raise HTTPException(status_code=400, detail="invalid json")
    email = data.get("email")
    secret = data.get("secret")
    url = data.get("url")
    answer = data.get("answer")

    # Basic validation
    if not email or not secret or not url:
        return JSONResponse({"correct": False, "reason": "missing fields"}, status_code=200)

    # simple secret check (accept any secret for demo)
    # Determine expected answer by url
    expected = None
    next_url = None

    if url.endswith("/pdf-demo"):
        expected = PDF_SUM_ANSWER
        next_url = "/image-demo"
    elif url.endswith("/image-demo"):
        expected = IMAGE_OCR_ANSWER
        next_url = "/audio-demo"
    elif url.endswith("/audio-demo"):
        expected = AUDIO_ANSWER
        next_url = "/puzzle-demo"
    elif url.endswith("/puzzle-demo"):
        expected = PUZZLE_ANSWER
        next_url = None
    else:
        # unknown page -> treat as incorrect
        return JSONResponse({"correct": False, "reason": "unknown url", "url": None})

    # allow numeric answers or numeric-like strings
    try:
        ans_num = float(answer) if answer is not None else None
    except:
        ans_num = None

    if ans_num is not None and abs(ans_num - expected) < 1e-6:
        return JSONResponse({"correct": True, "reason": "", "url": f"http://localhost:8001{next_url}" if next_url else None})
    else:
        return JSONResponse({"correct": False, "reason": "Wrong answer", "url": f"http://localhost:8001{next_url}" if next_url else None})

# ----------------------------
# If you want to serve the actual file referenced in the HTML (LOCAL_IMAGE_PATH),
# you can optionally add an endpoint to stream it. (This server does not modify local files.)
# We'll expose a friendly endpoint that simply returns the path value to show where
# the student's solver should look for the file.
@app.get("/local-path-info", response_class=JSONResponse)
async def local_path_info():
    return JSONResponse({"local_image_path": LOCAL_IMAGE_PATH})

if __name__ == "__main__":
    print("Fake TDS server running on http://0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
