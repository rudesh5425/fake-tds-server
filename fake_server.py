# fake_server.py
# FINAL — Railway-deployable Fake TDS Server

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import json
import base64
import gzip
import os

app = FastAPI()

# -----------------------------
# Expected Answers
# -----------------------------
PDF_SUM_ANSWER = 60      # values 10 + 20 + 30
IMAGE_OCR_ANSWER = 777   # demo OCR
AUDIO_ANSWER = 12        # 3 + 4 + 5
PUZZLE_ANSWER = 42       # decoded from gzip JSON

# For image demo (not used by Railway)
LOCAL_IMAGE_PATH = "/mnt/data/fake_image.png"

# -----------------------------
# Get BASE URL (Railway) 
# -----------------------------
# Railway gives PUBLIC_URL automatically:
BASE_URL = os.environ.get("RAILWAY_PUBLIC_DOMAIN")

if BASE_URL:
    BASE_URL = f"https://{BASE_URL}"
else:
    BASE_URL = "http://localhost:8001"   # local dev fallback

print("Using BASE_URL:", BASE_URL)


def wrap_atob(x: str) -> str:
    return base64.b64encode(x.encode()).decode()


# -----------------------------
# ROOT
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    return f"""
    <h2>Fake TDS Quiz Server</h2>
    <p>BASE_URL = {BASE_URL}</p>
    <ul>
        <li><a href="{BASE_URL}/pdf-demo">PDF Demo</a></li>
        <li><a href="{BASE_URL}/image-demo">Image Demo</a></li>
        <li><a href="{BASE_URL}/audio-demo">Audio Demo</a></li>
        <li><a href="{BASE_URL}/puzzle-demo">Puzzle Demo</a></li>
    </ul>
    """


# -----------------------------
# PDF DEMO
# -----------------------------
@app.get("/pdf-demo", response_class=HTMLResponse)
async def pdf_demo():
    csv = "name,value\nA,10\nB,20\nC,30\n"
    csv_b64 = base64.b64encode(csv.encode()).decode()

    instructions = json.dumps({
        "task": "Download CSV and compute sum of column 'value'.",
        "file_data_uri": f"data:text/csv;base64,{csv_b64}",
        "submit_url": f"{BASE_URL}/submit",
        "url": f"{BASE_URL}/pdf-demo"
    })

    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    """
    return HTMLResponse(html)


# -----------------------------
# IMAGE DEMO
# -----------------------------
@app.get("/image-demo", response_class=HTMLResponse)
async def image_demo():

    instructions = json.dumps({
        "task": "OCR the number from the image.",
        "image_path": LOCAL_IMAGE_PATH,
        "submit_url": f"{BASE_URL}/submit",
        "url": f"{BASE_URL}/image-demo"
    })

    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    <p>Expected OCR output: <b>{IMAGE_OCR_ANSWER}</b></p>
    """
    return HTMLResponse(html)


# -----------------------------
# AUDIO DEMO
# -----------------------------
@app.get("/audio-demo", response_class=HTMLResponse)
async def audio_demo():

    audio_b64 = base64.b64encode(b"SIMULATED AUDIO numbers 3 4 5").decode()

    instructions = json.dumps({
        "task": "Decode & read numbers from simulated audio and sum them.",
        "audio_data_uri": f"data:audio/wav;base64,{audio_b64}",
        "submit_url": f"{BASE_URL}/submit",
        "url": f"{BASE_URL}/audio-demo"
    })

    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    <p>Expected sum = <b>{AUDIO_ANSWER}</b></p>
    """
    return HTMLResponse(html)


# -----------------------------
# PUZZLE DEMO (gzip/base64)
# -----------------------------
@app.get("/puzzle-demo", response_class=HTMLResponse)
async def puzzle_demo():

    payload = {"secret_sum": PUZZLE_ANSWER}
    gz = gzip.compress(json.dumps(payload).encode())
    b64 = base64.b64encode(gz).decode()

    instructions = json.dumps({
        "task": "Decode base64 → gunzip → extract secret_sum",
        "payload_gz_b64": b64,
        "submit_url": f"{BASE_URL}/submit",
        "url": f"{BASE_URL}/puzzle-demo"
    })

    html = f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    <p>Expected answer: <b>{PUZZLE_ANSWER}</b></p>
    """
    return HTMLResponse(html)


# -----------------------------
# SUBMIT ENDPOINT
# -----------------------------
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

    # identify question by URL
    if url.endswith("/pdf-demo"):
        expected = PDF_SUM_ANSWER
        next_url = f"{BASE_URL}/image-demo"

    elif url.endswith("/image-demo"):
        expected = IMAGE_OCR_ANSWER
        next_url = f"{BASE_URL}/audio-demo"

    elif url.endswith("/audio-demo"):
        expected = AUDIO_ANSWER
        next_url = f"{BASE_URL}/puzzle-demo"

    elif url.endswith("/puzzle-demo"):
        expected = PUZZLE_ANSWER
        next_url = None

    else:
        return {"correct": False, "reason": "unknown url", "url": None}

    # check numeric answer
    try:
        numeric = float(answer)
    except:
        numeric = None

    if numeric == expected:
        return {"correct": True, "reason": "", "url": next_url}

    return {"correct": False, "reason": "Wrong answer", "url": next_url}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))   # Railway injects PORT
    uvicorn.run("fake_server:app", host="0.0.0.0", port=port, reload=False)
