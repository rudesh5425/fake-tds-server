# fake_server.py
# Fully corrected fake TDS-like quiz server.
# /submit endpoint added (instead of /fake-submit).
# Compatible with your deployed solver.

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import json
import base64
import gzip
import io

app = FastAPI()

# === Expected answers ===
PDF_SUM_ANSWER = 60              # 10 + 20 + 30
IMAGE_OCR_ANSWER = 777           # demo OCR
AUDIO_ANSWER = 12                # 3 + 4 + 5
PUZZLE_ANSWER = 42               # from gzipped JSON

LOCAL_IMAGE_PATH = "/mnt/data/5c3302c6-d159-4ece-bc3a-1b837d5d9516.png"


def wrap_atob(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <h2>Fake TDS Quiz Server</h2>
    <ul>
        <li><a href='/pdf-demo'>PDF Demo</a></li>
        <li><a href='/image-demo'>Image Demo</a></li>
        <li><a href='/audio-demo'>Audio Demo</a></li>
        <li><a href='/puzzle-demo'>Puzzle Demo</a></li>
    </ul>
    """


# ----------------------------
# PDF DEMO
# ----------------------------
@app.get("/pdf-demo", response_class=HTMLResponse)
async def pdf_demo():
    csv = "name,value\nA,10\nB,20\nC,30\n"
    csv_b64 = base64.b64encode(csv.encode()).decode()

    instructions = json.dumps({
        "task": "Download CSV & sum column 'value'",
        "file_data_uri": f"data:text/csv;base64,{csv_b64}",
        "submit_url": "/submit",
        "url": "http://localhost:8001/pdf-demo"
    })

    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    """
    return HTMLResponse(html)


# ----------------------------
# IMAGE DEMO
# ----------------------------
@app.get("/image-demo", response_class=HTMLResponse)
async def image_demo():
    instructions = json.dumps({
        "task": "Open the image, OCR it, return the number.",
        "image_path": LOCAL_IMAGE_PATH,
        "submit_url": "/submit",
        "url": "http://localhost:8001/image-demo"
    })

    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    <p>Expected OCR result: <b>{IMAGE_OCR_ANSWER}</b></p>
    """
    return HTMLResponse(html)


# ----------------------------
# AUDIO DEMO
# ----------------------------
@app.get("/audio-demo", response_class=HTMLResponse)
async def audio_demo():
    audio_b64 = base64.b64encode(b"SIMULATED AUDIO numbers 3 4 5").decode()

    instructions = json.dumps({
        "task": "Fetch & transcribe audio → sum numbers",
        "audio_data_uri": f"data:audio/wav;base64,{audio_b64}",
        "submit_url": "/submit",
        "url": "http://localhost:8001/audio-demo"
    })

    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    <p>Expected sum = <b>{AUDIO_ANSWER}</b></p>
    """
    return HTMLResponse(html)


# ----------------------------
# PUZZLE DEMO
# ----------------------------
@app.get("/puzzle-demo", response_class=HTMLResponse)
async def puzzle_demo():
    payload = {"secret_sum": PUZZLE_ANSWER}
    gz_payload = gzip.compress(json.dumps(payload).encode())
    b64_payload = base64.b64encode(gz_payload).decode()

    instructions = json.dumps({
        "task": "Decode base64 → gunzip → read 'secret_sum'",
        "payload_gz_b64": b64_payload,
        "submit_url": "/submit",
        "url": "http://localhost:8001/puzzle-demo"
    })

    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    <p>Expected decoded answer: <b>{PUZZLE_ANSWER}</b></p>
    """
    return HTMLResponse(html)


# ----------------------------
# CORRECTED: REAL TDS-LIKE /submit ENDPOINT
# ----------------------------
@app.post("/submit")
async def submit(req: Request):
    try:
        data = await req.json()
    except:
        raise HTTPException(status_code=400, detail="invalid json")

    email = data.get("email")
    secret = data.get("secret")
    url = data.get("url")
    answer = data.get("answer")

    if not email or not secret or not url:
        return {"correct": False, "reason": "missing fields", "url": None}

    # Route grading based on originating URL
    if url.endswith("/pdf-demo"):
        expected = PDF_SUM_ANSWER
        next_url = "http://localhost:8001/image-demo"

    elif url.endswith("/image-demo"):
        expected = IMAGE_OCR_ANSWER
        next_url = "http://localhost:8001/audio-demo"

    elif url.endswith("/audio-demo"):
        expected = AUDIO_ANSWER
        next_url = "http://localhost:8001/puzzle-demo"

    elif url.endswith("/puzzle-demo"):
        expected = PUZZLE_ANSWER
        next_url = None

    else:
        return {"correct": False, "reason": "unknown url", "url": None}

    # Check answer
    try:
        numeric = float(answer)
    except:
        numeric = None

    if numeric is not None and numeric == expected:
        return {"correct": True, "reason": "", "url": next_url}

    return {"correct": False, "reason": "Wrong answer", "url": next_url}


# ----------------------------
# Run server
# ----------------------------
if __name__ == "__main__":
    print("Fake server running at http://0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
