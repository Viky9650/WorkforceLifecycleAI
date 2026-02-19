import json
from pathlib import Path
from datetime import datetime

STORE_DIR = Path("store")
RUNS_DIR = STORE_DIR / "runs"
CHAT_DIR = STORE_DIR / "chat"
KT_DIR = STORE_DIR / "kt"

for d in [RUNS_DIR, CHAT_DIR, KT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def timestamp():
    return datetime.utcnow().isoformat().replace(":", "-")

def write_json(path: Path, payload: dict):
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)

def save_run(action: str, name: str, payload: dict):
    fname = f"{timestamp()}_{action}_{name}.json"
    path = RUNS_DIR / fname
    write_json(path, payload)
    return str(path)

def save_chat(question: str, payload: dict):
    fname = f"{timestamp()}_chat.json"
    path = CHAT_DIR / fname
    write_json(path, payload)
    return str(path)

def save_kt(name: str, payload: dict):
    fname = f"{name}_kt.json"
    path = KT_DIR / fname
    write_json(path, payload)
    return str(path)
