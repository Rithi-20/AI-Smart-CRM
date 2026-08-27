# 💼 SmartCRM AI Copilot

A production-grade, full-stack **AI-Powered CRM Assistant** built with **FastAPI**, **React (Vite)**, **SQLite (WAL Mode)**, and **Hugging Face Inference API** (`Qwen/Qwen2.5-72B-Instruct`).

---

## ✨ Key Features

- **🧠 Schema-Aware Intent Planner**: Uses Hugging Face LLM (`Qwen/Qwen2.5-72B-Instruct`) to convert natural language queries into deterministic SQLite query plans.
- **💬 Natural Language Answer Synthesis**: Generates clean, professional answers grounded strictly in retrieved CRM database facts.
- **⚡ Two-Phase Entity Resolution & Disambiguation**: Deterministically resolves customer/deal names. When multiple matching names are found (e.g. two *Rahuls*), interactive **Option 1**, **Option 2** UI buttons are presented for safe candidate selection.
- **📝 Single-Paragraph Chat History Summarization**: Synthesizes session interaction histories into clear, narrative single-paragraph summaries.
- **📜 Immutable Audit Log**: Automatically records all CRM mutations (`UPDATE_DEAL_STATUS`, `ASSIGN_LEAD`, `ADD_NOTE`) with `action_type`, `target_entity`, `after_value`, `performed_by`, and `timestamp`.
- **🎨 Modern React UI**: Built with React, Vite, Tailwind CSS, custom markdown parsing, and tab navigation (`Customers`, `Leads`, `Deals`, `Interactions`, `Audit Log`, `AI Copilot`).

---

## 🏛️ Architecture Overview

```
                                +---------------------------+
                                |      React + Vite UI      |
                                | (Dashboard & AI Drawer)   |
                                +-------------+-------------+
                                              |
                                              | HTTP REST API
                                              v
                                +---------------------------+
                                |      FastAPI Backend      |
                                |     (main.py / app.py)    |
                                +-------------+-------------+
                                              |
                                              | Agent Control Loop
                                              v
+---------------------------+       +---------------------------+       +---------------------------+
| Hugging Face LLM API      | <---> |    Agent Core Engine      | <---> |   Typed CRM Tool Layer    |
| (Qwen/Qwen2.5-72B)        |       |        (agent.py)         |       |      (tools.py & db.py)   |
+---------------------------+       +---------------------------+       +-------------+-------------+
                                                                                      |
                                                                                      | SQL Queries (WAL)
                                                                                      v
                                                                        +---------------------------+
                                                                        |      SQLite Database      |
                                                                        |        (crm.db)           |
                                                                        +---------------------------+
```

---

## 🗄️ Database Schema (`crm.db`)

```sql
CREATE TABLE salespeople (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);

CREATE TABLE customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    company TEXT NOT NULL,
    industry TEXT NOT NULL,
    location TEXT NOT NULL,
    customer_type TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE leads (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    lead_name TEXT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    lead_score INTEGER NOT NULL,
    expected_value REAL NOT NULL,
    assigned_to TEXT REFERENCES salespeople(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE deals (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    title TEXT NOT NULL,
    value REAL NOT NULL,
    status TEXT NOT NULL,
    probability INTEGER NOT NULL,
    owner_id TEXT REFERENCES salespeople(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE interactions (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    deal_id TEXT REFERENCES deals(id),
    type TEXT NOT NULL,
    subject TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_by TEXT REFERENCES salespeople(id),
    created_at TEXT NOT NULL
);

CREATE TABLE notes (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    deal_id TEXT REFERENCES deals(id),
    author_id TEXT REFERENCES salespeople(id),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE action_log (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    target_table TEXT NOT NULL,
    target_id TEXT NOT NULL,
    after_value TEXT,
    performed_by TEXT NOT NULL DEFAULT 'ai_agent',
    timestamp TEXT NOT NULL
);
```

---

## ⚡ Setup & Deployment Instructions

### 1. Prerequisites
- Python 3.10 or higher
- Node.js 18+ and npm

### 2. Environment Configuration
Create a `.env` file in the root directory:

```env
# Hugging Face API Token (Free from https://huggingface.co/settings/tokens)
HF_TOKEN=your_huggingface_api_token_here
```

### 3. Install Backend Dependencies
```bash
pip install fastapi uvicorn pydantic requests python-dotenv huggingface_hub
```

### 4. Install Frontend Dependencies & Build Static Assets (Optional for Production)
```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. Seed Database
```bash
python seed_db.py
```

### 6. Run Application
Run the single production main script:
```bash
python main.py
```

Open **`http://localhost:8000`** in your web browser!

---

## 🧪 Example Test Queries Supported

- `"How many leads are in Contacted status?"`
- `"List the customers who belong to the Manufacturing industry"`
- `"Show deals worth over ₹20,000"`
- `"Summarize my conversation history with Rahul"`
- `"Move GreenTech - Solar Monitoring System to Won"`
- `"Assign deal GreenTech to Priya Menon"`
- `"Add note to Rahul Sharma: Customer requested enterprise contract draft"`
