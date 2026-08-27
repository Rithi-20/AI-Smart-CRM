import sqlite3
import os

SEED_SALESPEOPLE = [
    {"id": "EMP001", "name": "Ravi Kumar", "email": "ravi@company.com"},
    {"id": "EMP002", "name": "Ananya Rao", "email": "ananya@company.com"},
    {"id": "EMP003", "name": "Priya Menon", "email": "priya@company.com"},
    {"id": "EMP004", "name": "Vikram Sethi", "email": "vikram@company.com"},
    {"id": "EMP005", "name": "Neha Sharma", "email": "neha@company.com"}
]

SEED_CUSTOMERS = [
    {"id": "CUST001", "name": "Arjun Sharma", "company": "Nimbus Retail", "industry": "Retail", "location": "Mumbai", "customer_type": "Enterprise", "email": "arjun@nimbusretail.com", "phone": "+91-98765-11111", "created_at": "2026-06-01"},
    {"id": "CUST002", "name": "Meera Iyer", "company": "Coral Logistics", "industry": "Logistics", "location": "Bengaluru", "customer_type": "Mid-Market", "email": "meera@corallogistics.com", "phone": "+91-98765-22222", "created_at": "2026-06-05"},
    {"id": "CUST003", "name": "Karthik Reddy", "company": "Skyline FinTech", "industry": "Finance", "location": "Hyderabad", "customer_type": "Enterprise", "email": "karthik@skylinefintech.com", "phone": "+91-98765-33333", "created_at": "2026-06-10"},
    {"id": "CUST004", "name": "Divya Nair", "company": "Pixel Studios", "industry": "IT Services", "location": "Chennai", "customer_type": "SMB", "email": "divya@pixelstudios.com", "phone": "+91-98765-44444", "created_at": "2026-06-15"},
    {"id": "CUST005", "name": "Sanjay Gupta", "company": "GreenLeaf Foods", "industry": "Manufacturing", "location": "Delhi", "customer_type": "Enterprise", "email": "sanjay@greenleaffoods.com", "phone": "+91-98765-55555", "created_at": "2026-06-20"},
    {"id": "CUST006", "name": "Rohan Deshmukh", "company": "Apex Dynamics", "industry": "Manufacturing", "location": "Pune", "customer_type": "Mid-Market", "email": "rohan@apexdynamics.com", "phone": "+91-98765-66666", "created_at": "2026-07-01"},
    {"id": "CUST007", "name": "Kavita Verma", "company": "Zenith Healthcare", "industry": "Healthcare", "location": "Mumbai", "customer_type": "Enterprise", "email": "kavita@zenithhealth.com", "phone": "+91-98765-77777", "created_at": "2026-07-05"},
    {"id": "CUST008", "name": "Aman Patel", "company": "Nova Robotics", "industry": "IT Services", "location": "Bengaluru", "customer_type": "SMB", "email": "aman@novarobotics.com", "phone": "+91-98765-88888", "created_at": "2026-07-10"},
    {"id": "CUST009", "name": "Rahul Kumar", "company": "TechNova Solutions", "industry": "IT Services", "location": "Bengaluru", "customer_type": "Enterprise", "email": "rahul@technova.com", "phone": "+91-98765-99991", "created_at": "2026-07-12"},
    {"id": "CUST010", "name": "Rahul Sharma", "company": "GreenTech Systems", "industry": "Manufacturing", "location": "Delhi", "customer_type": "Mid-Market", "email": "rahul@greentech.com", "phone": "+91-98765-99992", "created_at": "2026-07-14"}
]

SEED_LEADS = [
    {"id": "LEAD001", "customer_id": "CUST001", "lead_name": "Arjun Sharma - POS Expansion Lead", "source": "Website", "status": "Contacted", "lead_score": 85, "expected_value": 25000.0, "assigned_to": "EMP001", "created_at": "2026-06-01", "updated_at": "2026-07-20"},
    {"id": "LEAD002", "customer_id": "CUST002", "lead_name": "Meera Iyer - Fleet Management Lead", "source": "Referral", "status": "New", "lead_score": 60, "expected_value": 15000.0, "assigned_to": "EMP002", "created_at": "2026-06-05", "updated_at": "2026-08-01"},
    {"id": "LEAD003", "customer_id": "CUST003", "lead_name": "Karthik Reddy - Compliance System Lead", "source": "LinkedIn", "status": "Contacted", "lead_score": 90, "expected_value": 42000.0, "assigned_to": "EMP001", "created_at": "2026-06-10", "updated_at": "2026-07-25"},
    {"id": "LEAD004", "customer_id": "CUST004", "lead_name": "Divya Nair - Cloud Upgrade Lead", "source": "Cold Call", "status": "Won", "lead_score": 95, "expected_value": 8000.0, "assigned_to": "EMP003", "created_at": "2026-06-15", "updated_at": "2026-07-30"},
    {"id": "LEAD005", "customer_id": "CUST005", "lead_name": "Sanjay Gupta - Supply Chain Lead", "source": "Website", "status": "Lost", "lead_score": 40, "expected_value": 60000.0, "assigned_to": "EMP002", "created_at": "2026-06-20", "updated_at": "2026-07-15"},
    {"id": "LEAD006", "customer_id": "CUST006", "lead_name": "Rohan Deshmukh - Automation Lead", "source": "Event", "status": "Contacted", "lead_score": 75, "expected_value": 35000.0, "assigned_to": "EMP004", "created_at": "2026-07-01", "updated_at": "2026-07-22"},
    {"id": "LEAD007", "customer_id": "CUST007", "lead_name": "Kavita Verma - Healthcare Portal Lead", "source": "Referral", "status": "New", "lead_score": 70, "expected_value": 50000.0, "assigned_to": "EMP005", "created_at": "2026-07-05", "updated_at": "2026-08-04"},
    {"id": "LEAD008", "customer_id": "CUST008", "lead_name": "Aman Patel - Firmware Lead", "source": "LinkedIn", "status": "Contacted", "lead_score": 80, "expected_value": 28000.0, "assigned_to": "EMP004", "created_at": "2026-07-10", "updated_at": "2026-07-21"}
]

SEED_DEALS = [
    {"id": "DEAL001", "customer_id": "CUST001", "title": "Nimbus Retail - POS Rollout", "value": 25000.0, "status": "Contacted", "probability": 40.0, "owner_id": "EMP001", "expected_close": "2026-09-15", "created_at": "2026-06-02", "updated_at": "2026-07-20"},
    {"id": "DEAL002", "customer_id": "CUST002", "title": "Coral Logistics - Fleet Tracking", "value": 15000.0, "status": "New", "probability": 20.0, "owner_id": "EMP002", "expected_close": "2026-10-01", "created_at": "2026-06-06", "updated_at": "2026-08-01"},
    {"id": "DEAL003", "customer_id": "CUST003", "title": "Skyline FinTech - Compliance Suite", "value": 42000.0, "status": "Contacted", "probability": 50.0, "owner_id": "EMP001", "expected_close": "2026-09-30", "created_at": "2026-06-11", "updated_at": "2026-07-25"},
    {"id": "DEAL004", "customer_id": "CUST004", "title": "Pixel Studios - Cloud Storage Upgrade", "value": 8000.0, "status": "Won", "probability": 100.0, "owner_id": "EMP003", "expected_close": "2026-07-30", "created_at": "2026-06-16", "updated_at": "2026-07-30"},
    {"id": "DEAL005", "customer_id": "CUST005", "title": "GreenLeaf Foods - Supply Chain ERP", "value": 60000.0, "status": "Lost", "probability": 0.0, "owner_id": "EMP002", "expected_close": "2026-07-15", "created_at": "2026-06-21", "updated_at": "2026-07-15"},
    {"id": "DEAL006", "customer_id": "CUST003", "title": "Skyline FinTech - Add-on Module", "value": 11000.0, "status": "New", "probability": 25.0, "owner_id": "EMP001", "expected_close": "2026-10-15", "created_at": "2026-07-01", "updated_at": "2026-08-05"},
    {"id": "DEAL007", "customer_id": "CUST006", "title": "Apex Dynamics - Automation Engine", "value": 35000.0, "status": "Contacted", "probability": 60.0, "owner_id": "EMP004", "expected_close": "2026-09-20", "created_at": "2026-07-02", "updated_at": "2026-07-22"},
    {"id": "DEAL008", "customer_id": "CUST007", "title": "Zenith Healthcare - Patient Portal", "value": 50000.0, "status": "New", "probability": 30.0, "owner_id": "EMP005", "expected_close": "2026-11-01", "created_at": "2026-07-06", "updated_at": "2026-08-04"},
    {"id": "DEAL009", "customer_id": "CUST008", "title": "Nova Robotics - Edge AI Firmware", "value": 28000.0, "status": "Contacted", "probability": 45.0, "owner_id": "EMP004", "expected_close": "2026-09-25", "created_at": "2026-07-11", "updated_at": "2026-07-21"},
    {"id": "DEAL010", "customer_id": "CUST009", "title": "TechNova - Enterprise License", "value": 45000.0, "status": "Contacted", "probability": 50.0, "owner_id": "EMP001", "expected_close": "2026-09-28", "created_at": "2026-07-12", "updated_at": "2026-07-22"},
    {"id": "DEAL011", "customer_id": "CUST010", "title": "GreenTech - Solar Monitoring System", "value": 32000.0, "status": "New", "probability": 30.0, "owner_id": "EMP002", "expected_close": "2026-10-10", "created_at": "2026-07-14", "updated_at": "2026-08-02"}
]

SEED_INTERACTIONS = [
    {"id": "INT001", "customer_id": "CUST001", "deal_id": "DEAL001", "type": "Call", "subject": "Initial Discovery Call", "summary": "Discussed POS rollout timeline and 10 location requirements.", "created_by": "EMP001", "created_at": "2026-06-03"},
    {"id": "INT002", "customer_id": "CUST001", "deal_id": "DEAL001", "type": "Demo", "subject": "Product Demonstration", "summary": "Showcased multi-store analytics and cloud sync.", "created_by": "EMP001", "created_at": "2026-07-20"},
    {"id": "INT003", "customer_id": "CUST002", "deal_id": "DEAL002", "type": "Email", "subject": "Proposal Sent", "summary": "Sent quote for 50 GPS tracking units.", "created_by": "EMP002", "created_at": "2026-06-07"},
    {"id": "INT004", "customer_id": "CUST003", "deal_id": "DEAL003", "type": "Meeting", "subject": "Legal & Compliance Sync", "summary": "Reviewed security compliance documentation.", "created_by": "EMP001", "created_at": "2026-06-12"},
    {"id": "INT005", "customer_id": "CUST004", "deal_id": "DEAL004", "type": "Email", "subject": "Contract Signed", "summary": "Received payment confirmation and finalized upgrade.", "created_by": "EMP003", "created_at": "2026-07-30"}
]

SEED_NOTES = [
    {"id": "NOTE001", "customer_id": "CUST001", "deal_id": "DEAL001", "author_id": "EMP001", "content": "Initial call went well, wants a demo next week.", "created_at": "2026-06-03"},
    {"id": "NOTE002", "customer_id": "CUST001", "deal_id": "DEAL001", "author_id": "EMP001", "content": "Demo done, requested pricing for 10 locations.", "created_at": "2026-07-20"},
    {"id": "NOTE003", "customer_id": "CUST002", "deal_id": "DEAL002", "author_id": "EMP002", "content": "Sent proposal for 50 vehicle tracking units.", "created_at": "2026-06-07"},
    {"id": "NOTE004", "customer_id": "CUST003", "deal_id": "DEAL003", "author_id": "EMP001", "content": "Legal team reviewing compliance terms.", "created_at": "2026-06-12"},
    {"id": "NOTE005", "customer_id": "CUST004", "deal_id": "DEAL004", "author_id": "EMP003", "content": "Payment received, onboarding completed.", "created_at": "2026-07-30"},
    {"id": "NOTE006", "customer_id": "CUST006", "deal_id": "DEAL007", "author_id": "EMP004", "content": "Initial discovery session held with Rohan.", "created_at": "2026-07-03"},
    {"id": "NOTE007", "customer_id": "CUST007", "deal_id": "DEAL008", "author_id": "EMP005", "content": "Kavita requested HIPAA compliance certification.", "created_at": "2026-07-07"},
    {"id": "NOTE008", "customer_id": "CUST008", "deal_id": "DEAL009", "author_id": "EMP004", "content": "Technical architecture review scheduled for next week.", "created_at": "2026-07-12"}
]

def init_db(db_path: str = "crm.db"):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. salespeople
    cursor.execute("""
    CREATE TABLE salespeople (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL
    );
    """)

    # 2. customers
    cursor.execute("""
    CREATE TABLE customers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        company TEXT,
        industry TEXT DEFAULT 'General',
        location TEXT DEFAULT 'Global',
        customer_type TEXT DEFAULT 'Enterprise',
        email TEXT,
        phone TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 3. leads
    cursor.execute("""
    CREATE TABLE leads (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        lead_name TEXT,
        source TEXT DEFAULT 'Website',
        status TEXT NOT NULL CHECK (status IN ('New','Contacted','Qualified','Proposal','Won','Lost')),
        lead_score INTEGER DEFAULT 50,
        expected_value REAL DEFAULT 0.0,
        assigned_to TEXT REFERENCES salespeople(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 4. deals
    cursor.execute("""
    CREATE TABLE deals (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        value REAL NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('New','Contacted','Qualified','Proposal','Won','Lost')),
        probability REAL DEFAULT 50.0,
        owner_id TEXT REFERENCES salespeople(id) ON DELETE SET NULL,
        expected_close TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 5. interactions
    cursor.execute("""
    CREATE TABLE interactions (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        deal_id TEXT REFERENCES deals(id) ON DELETE SET NULL,
        type TEXT NOT NULL,
        subject TEXT NOT NULL,
        summary TEXT,
        created_by TEXT REFERENCES salespeople(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL
    );
    """)

    # 6. notes
    cursor.execute("""
    CREATE TABLE notes (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        deal_id TEXT REFERENCES deals(id) ON DELETE SET NULL,
        author_id TEXT REFERENCES salespeople(id) ON DELETE SET NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # 7. action_log
    cursor.execute("""
    CREATE TABLE action_log (
        id TEXT PRIMARY KEY,
        action_type TEXT NOT NULL,
        target_table TEXT NOT NULL,
        target_id TEXT NOT NULL,
        before_value TEXT,
        after_value TEXT,
        performed_by TEXT NOT NULL DEFAULT 'ai_agent',
        timestamp TEXT NOT NULL
    );
    """)

    # 8. chat_sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        context_type TEXT,
        context_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 9. chat_messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)

    # Populate Seed Data
    for s in SEED_SALESPEOPLE:
        cursor.execute("INSERT INTO salespeople (id, name, email) VALUES (?, ?, ?)", (s["id"], s["name"], s["email"]))

    for c in SEED_CUSTOMERS:
        cursor.execute("INSERT INTO customers (id, name, company, industry, location, customer_type, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (c["id"], c["name"], c["company"], c["industry"], c["location"], c["customer_type"], c["email"], c["phone"], c["created_at"]))

    for l in SEED_LEADS:
        cursor.execute("INSERT INTO leads (id, customer_id, lead_name, source, status, lead_score, expected_value, assigned_to, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (l["id"], l["customer_id"], l.get("lead_name", ""), l["source"], l["status"], l["lead_score"], l["expected_value"], l["assigned_to"], l["created_at"], l["updated_at"]))

    for d in SEED_DEALS:
        cursor.execute("INSERT INTO deals (id, customer_id, title, value, status, probability, owner_id, expected_close, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (d["id"], d["customer_id"], d["title"], d["value"], d["status"], d["probability"], d["owner_id"], d["expected_close"], d["created_at"], d["updated_at"]))

    for i in SEED_INTERACTIONS:
        cursor.execute("INSERT INTO interactions (id, customer_id, deal_id, type, subject, summary, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (i["id"], i["customer_id"], i["deal_id"], i["type"], i["subject"], i["summary"], i["created_by"], i["created_at"]))

    for n in SEED_NOTES:
        cursor.execute("INSERT INTO notes (id, customer_id, deal_id, author_id, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       (n["id"], n["customer_id"], n["deal_id"], n["author_id"], n["content"], n["created_at"]))

    conn.commit()
    conn.close()
    print("Database initialized and seeded successfully with formatted string IDs.")

if __name__ == "__main__":
    init_db()

