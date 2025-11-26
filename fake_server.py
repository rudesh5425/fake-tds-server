# fake_server.py
# FINAL — 100% Railway Compatible Fake TDS Server

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import json
import base64
import gzip
import os

app = FastAPI()

PDF_SUM_ANSWER = 60
IMAGE_OCR_ANSWER = 777
AUDIO_ANSWER = 12
PUZZLE_ANSWER = 42

def wrap_atob(x: str):
    return base64.b64encode(x.encode()).decode()


def get_base_url():
    # Railway sets RAILWAY_PUBLIC_DOMAIN
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if domain:
        return f"https://{domain}"
    return "http://localhost:8001"

BASE_URL = get_base_url()


@app.get("/", response_class=HTMLResponse)
async def root():
    return f"""
    <h2>Fake TDS Quiz Server OK</h2>
    <p>BASE_URL = {BASE_URL}</p>
    <ul>
        <li><a href="{BASE_URL}/pdf-demo">PDF Demo</a></li>
        <li><a href="{BASE_URL}/image-demo">Image Demo</a></li>
        <li><a href="{BASE_URL}/audio-demo">Audio Demo</a></li>
        <li><a href="{BASE_URL}/puzzle-demo">Puzzle Demo</a></li>
    </ul>
    """


@app.get("/pdf-demo", response_class=HTMLResponse)
async def pdf_demo():
    csv = "name,value\nA,10\nB,20\nC,30\n"
    b64 = base64.b64encode(csv.encode()).decode()

    instructions = json.dumps({
        "task": "Compute sum of CSV values",
        "file_data_uri": f"data:text/csv;base64,{b64}",
        "submit_url": f"{BASE_URL}/submit",
        "url": f"{BASE_URL}/pdf-demo"
    })

    return HTMLResponse(f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    """)


@app.get("/image-demo", response_class=HTMLResponse)
async def image_demo():
    instructions = json.dumps({
        "task": "OCR image",
        "image_path": "/static/fake.png",
        "submit_url": f"{BASE_URL}/submit",
        "url": f"{BASE_URL}/image-demo"
    })
    return HTMLResponse(f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    <p>Expected answer = {IMAGE_OCR_ANSWER}</p>
    """)


@app.get("/audio-demo", response_class=HTMLResponse)
async def audio_demo():

    audio_b64 = base64.b64encode(b"numbers 3 4 5").decode()

    instructions = json.dumps({
        "task": "Decode audio, sum numbers",
        "audio_data_uri": f"data:audio/wav;base64,{audio_b64}",
        "submit_url": f"{BASE_URL}/submit",
        "url": f"{BASE_URL}/audio-demo"
    })

    return HTMLResponse(f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    <p>Expected answer = {AUDIO_ANSWER}</p>
    """)


@app.get("/puzzle-demo", response_class=HTMLResponse)
async def puzzle_demo():

    payload = {"secret_sum": PUZZLE_ANSWER}
    gz = gzip.compress(json.dumps(payload).encode())
    b64 = base64.b64encode(gz).decode()

    instructions = json.dumps({
        "task": "Decode and gunzip",
        "payload_gz_b64": b64,
        "submit_url": f"{BASE_URL}/submit",
        "url": f"{BASE_URL}/puzzle-demo"
    })

    return HTMLResponse(f"""
    <div id="result"></div>
    <script>
      document.querySelector("#result").innerHTML = atob(`{wrap_atob(instructions)}`);
    </script>
    <p>Expected answer = {PUZZLE_ANSWER}</p>
    """)


@app.post("/submit")
async def submit(req: Request):
    try:
        data = await req.json()
    except:
        raise HTTPException(400, "invalid json")

    url = data.get("url")
    answer = data.get("answer")

    if not url:
        return {"correct": False, "reason": "missing url", "url": None}

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

    try:
        ans = float(answer)
    except:
        return {"correct": False, "reason": "not numeric", "url": next_url}

    return {
        "correct": ans == expected,
        "reason": "" if ans == expected else "Wrong answer",
        "url": next_url
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("fake_server:app", host="0.0.0.0", port=port)
