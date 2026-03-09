<!-- Header Banner -->
<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:6366f1,100:06b6d4&height=200&section=header&text=WorkforceLifecycleAI&fontSize=50&fontColor=ffffff&fontAlignY=38&desc=Agentic%20HR%20%2B%20IT%20Onboarding%20%26%20Offboarding%20Platform&descAlignY=58&descColor=e0f2fe" width="100%"/>

<br/>

![RAG Grounded](https://img.shields.io/badge/RAG-Grounded-6366f1?style=for-the-badge&logo=database&logoColor=white)
![MCP Tooling](https://img.shields.io/badge/MCP-Tooling-06b6d4?style=for-the-badge&logo=tools&logoColor=white)
![Audit Ready](https://img.shields.io/badge/Audit-Ready-10b981?style=for-the-badge&logo=shield&logoColor=white)
![Enterprise Demo](https://img.shields.io/badge/Enterprise-Demo-f59e0b?style=for-the-badge&logo=building&logoColor=white)

<br/>

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-FF6B6B?style=flat-square&logo=langchain&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini-4285F4?style=flat-square&logo=google&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-Vector_DB-8B5CF6?style=flat-square)
![HuggingFace](https://img.shields.io/badge/HuggingFace-FFD21E?style=flat-square&logo=huggingface&logoColor=black)

</div>

<br/>

---

## 👥 Team

| Name | Role |
|------|------|
| **Vickey Panjiyar** | DevOps / AI Engineer |

---

<br/>

## ❌ The Problem

> Organizations today face critical challenges managing employee lifecycle processes at scale.

<table>
<tr>
<td>

🔴 &nbsp;Manual access provisioning across multiple systems  
🔴 &nbsp;Delays in access revocation *(security risk)*  
🔴 &nbsp;No centralized audit trail  

</td>
<td>

🔴 &nbsp;Knowledge transfer loss during employee exit  
🔴 &nbsp;HR and IT teams working in silos  
🔴 &nbsp;No intelligent policy assistant  

</td>
</tr>
</table>

> **Enterprises require a secure, automated, AI-powered, and auditable lifecycle management system.**

<br/>

---

## 💡 Solution Overview

**WorkforceLifecycleAI** is an agentic HR + IT assistant that handles the full employee lifecycle — intelligently, automatically, and with a complete audit trail.

<br/>

<table>
<tr>
<td width="33%" align="center">

### 🚀 Onboarding
✅ Reads role-based policies  
✅ Provisions access via MCP tools  
✅ Sends Slack + Email notifications  
✅ Generates audit evidence  

</td>
<td width="33%" align="center">

### 🔒 Offboarding
✅ Revokes system access  
✅ Captures Knowledge Transfer (KT)  
✅ Indexes KT into RAG system  
✅ Stores full audit record  

</td>
<td width="33%" align="center">

### 🤖 AI Assistant
✅ Policy Q&A from YAML config  
✅ Knowledge Q&A via RAG  
✅ Chat powered by Gemini  
✅ Embeddings via HuggingFace  

</td>
</tr>
</table>

<br/>

---

## 🔐 Face Authentication (Login Gate)

WorkforceLifecycleAI uses an **on-device biometric login** powered by MediaPipe — no face data ever leaves the browser.

<table>
<tr>
<td width="50%" align="center">

### 🤖 How It Works
✅ Opens webcam in the browser  
✅ Detects face using MediaPipe FaceMesh (468 landmarks)  
✅ Tracks hand using MediaPipe Hands (21 landmarks)  
✅ Requires 👍 thumbs-up gesture held for ~18 frames  
✅ Sets a session cookie `face_auth=granted`  
✅ Middleware gates all routes until authenticated  

</td>
<td width="50%" align="center">

### 🛡️ Privacy & Security
✅ 100% on-device — zero data transmitted  
✅ Camera LED turns off immediately after auth  
✅ Session cookie expires after 1 hour  
✅ All pages protected by Next.js middleware  
✅ No face images stored anywhere  
✅ Works entirely in the browser (no backend call)  

</td>
</tr>
</table>

### 🔷 Face Auth Flow

```
User visits any page
      │
      ▼
Next.js Middleware checks face_auth cookie
      │
      ├─ Not authenticated → redirect to /login
      │
      ▼
FaceAuthAgent boots (MediaPipe loads on-device)
      │
      ▼
Webcam opens → Face detected (468 landmarks)
      │
      ▼
Thumbs-up gesture held for 18 consecutive frames
      │
      ▼
Cookie set: face_auth=granted (1hr expiry)
      │
      ▼
Camera LED off → Redirect to dashboard ✅
```

### Agent States

| State | Description |
|-------|-------------|
| `BOOTING` | Agent initialising |
| `REQUESTING_CAM` | Asking browser for camera permission |
| `LOADING_MODELS` | Downloading MediaPipe models |
| `SCANNING_FACE` | Looking for a face in the video feed |
| `FACE_LOCKED` | Face found — waiting for 👍 gesture |
| `GESTURE_DETECTED` | Thumbs-up seen — counting confirmation frames |
| `AUTHENTICATED` | Auth passed, cookie set |
| `REDIRECTING` | Camera off, navigating to dashboard |

### Frontend Dependencies (Face Auth)

Add these to `frontend/package.json`:

```json
"@mediapipe/face_mesh": "^0.4.1633559619",
"@mediapipe/hands": "^0.4.1646424915",
"@mediapipe/camera_utils": "^0.3.1640029074"
```

> Models are loaded from the jsDelivr CDN at runtime — no local model files needed.

<br/>

---

## 🧠 Architecture

### 🔷 Lifecycle Execution Flow

```
User Request
      │
      ▼
Orchestrator Agent
      │
      ▼
Provisioning Agent
      │
      ▼
MCP Tools (GitHub / IAM / Jira / etc.)
      │
      ▼
Notifications (Slack + Email)
      │
      ▼
Audit Trail Stored ✅
```

<br/>

### 🔷 Chat / RAG Flow

```
User Question
      │
      ▼
Retriever (FAISS)
      │
      ▼
HuggingFace Embeddings
      │
      ▼
Relevant Docs Retrieved
      │
      ▼
Gemini LLM
      │
      ▼
Grounded Response + Sources ✅
```

<br/>

---

## 🏗️ Technology Stack

| Layer | Technology |
|-------|-----------|
| 🖥️ **Backend** | FastAPI |
| 🤖 **Agent Orchestration** | LangGraph |
| 🧠 **LLM** | Google Gemini |
| 🔢 **Embeddings** | HuggingFace MiniLM |
| 📦 **Vector Database** | FAISS |
| 🛠️ **Tool Execution** | MCP Server |
| 🌐 **Frontend** | Next.js + Tailwind CSS |
| 📋 **Audit Storage** | JSON Run Artifacts |

<br/>

---

## 📁 Project Structure

```
WorkforceLifecycleAI/
│
├── 🤖 agents/           # Agent implementations
├── 🔌 api/              # FastAPI routes
├── 🛠️ mcp_server/       # MCP tool server
├── 📚 rag/              # RAG ingest + retriever
├── 📄 docs/             # Internal documentation
├── ⚙️ config/           # Role-based policies
├── 🌐 frontend/         # Next.js UI
└── 🗄️ store/            # Audit runs storage
```

<br/>

---

## 🛠️ Setup & Installation

### 1️⃣ Clone Repository

```bash
git clone https://github.com/<your-org>/WorkforceLifecycleAI.git
cd WorkforceLifecycleAI
```

### 2️⃣ Create Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3️⃣ Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4️⃣ Configure Environment Variables

Create a `.env` file in the project root:

```env
# Gemini
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_CHAT_MODEL=gemini-2.0-flash
CHAT_TEMPERATURE=0.2
MAX_CONTEXT_CHARS=2500

# MCP Server
MCP_BASE_URL=http://127.0.0.1:9001

# GitHub Integration (Optional)
GITHUB_TOKEN=your_github_pat
GITHUB_ORG=your_org_name
GITHUB_API_BASE=https://api.github.com
```

> ⚠️ **Never commit `.env` to GitHub.**

<br/>

---

## ▶️ Running the Application

### Step 1 — Start MCP Server

```bash
PYTHONPATH=. python -m uvicorn mcp_server.main:app --reload --port 9001
```

### Step 2 — Start Backend API

```bash
PYTHONPATH=. python -m uvicorn api.main:app --reload --port 9000
```

### Step 3 — Start Frontend

```bash
cd frontend
npm run dev
```

### OR — All steps combined with make file

```bash
make help
make dev
```

> 🌐 Open **http://localhost:3000**

<br/>

---

## 📚 RAG Setup — Build Knowledge Index

```bash
python -m rag.ingest
```

This command will:
- 📂 Read markdown files from `/docs`
- 🔢 Generate embeddings via HuggingFace
- 🗃️ Build a FAISS index in `/rag_index`

<br/>

---

## 🔐 Role-Based Policy Engine

Policies are defined in `config/access_policies.yml`:

```yaml
DevOps Engineer:
  systems:
    ["IAM", "Jira", "GitHub", "Confluence"]
```

> Policy questions are answered **deterministically** from this file — no hallucination.

<br/>

---

## 📦 MCP Tools Supported

<table>
<tr>
<td>

| Tool | Status |
|------|--------|
| IAM | 🟡 Mock |
| Jira | 🟡 Mock |
| Confluence | 🟡 Mock |
| GitHub | 🟢 Real API |
| DevOps Deploy App | 🟡 Mock |

</td>
<td>

| Tool | Status |
|------|--------|
| ServiceNow | 🟡 Mock |
| Outlook | 🟡 Mock |
| Teams | 🟡 Mock |
| Slack | 🟡 Mock |
| Email | 🟡 Mock |

</td>
</tr>
</table>

<br/>

---

## 💬 Example Questions

```
📌 Where is the onboarding document?
📌 What access is required for a DevOps Engineer?
📌 What happens during offboarding?
📌 List available roles
```

<br/>

---

## 🧾 Audit Trail

Every lifecycle run generates a structured audit artifact:

```json
{
  "audit_id": "run-20240301-xyz",
  "provisioning_status": { "IAM": "✅", "GitHub": "✅", "Jira": "✅" },
  "tool_evidence": [...],
  "notifications": { "slack": "sent", "email": "sent" }
}
```

> Ensures **compliance, traceability, and enterprise-grade accountability**.

<br/>

---

## 🚀 Future Enhancements

- [ ] 🔗 Real Slack API integration  
- [ ] 🔑 OAuth authentication  
- [ ] 📊 Admin dashboard  
- [ ] ☁️ Cloud deployment (AWS / GCP / Azure)  
- [ ] 👤 Role-based access control  

<br/>

---

## 🌟 Why This Project Matters

<table>
<tr>
<td align="center">🤖<br/><b>Agentic AI Orchestration</b></td>
<td align="center">⚖️<br/><b>Deterministic + Generative Hybrid</b></td>
<td align="center">🔒<br/><b>Secure Lifecycle Automation</b></td>
<td align="center">📋<br/><b>Enterprise-Grade Audit Thinking</b></td>
<td align="center">🧱<br/><b>Full-Stack AI Engineering</b></td>
</tr>
</table>

<br/>

---


<br/>

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:06b6d4,100:6366f1&height=120&section=footer" width="100%"/>

*Built with ❤️ by Vickey Panjiyar*

</div>
