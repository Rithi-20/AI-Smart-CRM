import sqlite3
import json
import re
from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional
from db import execute_query, generate_next_id, get_connection

CURRENT_DATE_STR = "2026-08-10"

def get_current_date() -> date:
    return date.fromisoformat(CURRENT_DATE_STR)

def safe_parse_date(dt_str: Any) -> date:
    ref_date = get_current_date()
    if not dt_str:
        return ref_date
    raw_dt = str(dt_str).strip().split()[0].split("T")[0]
    try:
        return date.fromisoformat(raw_dt)
    except Exception:
        return ref_date

# ==========================================
# OVERVIEW & ANALYTICS DATA SERVICES
# ==========================================

def get_overview_kpis() -> Dict[str, Any]:
    """
    Returns dynamically calculated Overview KPIs strictly from SQLite.
    """
    cust_res = execute_query("SELECT COUNT(*) as count FROM customers")
    total_customers = cust_res[0]['count'] if cust_res else 0

    lead_res = execute_query("SELECT COUNT(*) as count FROM leads")
    total_leads = lead_res[0]['count'] if lead_res else 0

    active_deals_res = execute_query("SELECT COUNT(*) as count, COALESCE(SUM(value), 0.0) as val FROM deals WHERE status NOT IN ('Won', 'Lost')")
    active_deals = active_deals_res[0]['count'] if active_deals_res else 0
    pipeline_value = active_deals_res[0]['val'] if active_deals_res else 0.0

    won_res = execute_query("SELECT COALESCE(SUM(value), 0.0) as val FROM deals WHERE status = 'Won'")
    won_revenue = won_res[0]['val'] if won_res else 0.0

    lost_res = execute_query("SELECT COALESCE(SUM(value), 0.0) as val FROM deals WHERE status = 'Lost'")
    lost_revenue = lost_res[0]['val'] if lost_res else 0.0

    at_risk_list = get_at_risk_deals_data(days_threshold=14)
    at_risk_count = len(at_risk_list)

    return {
        "total_customers": total_customers,
        "total_leads": total_leads,
        "active_deals": active_deals,
        "pipeline_value": pipeline_value,
        "won_revenue": won_revenue,
        "lost_revenue": lost_revenue,
        "at_risk_count": at_risk_count
    }

def get_pipeline_by_status() -> List[Dict[str, Any]]:
    """
    Groups deals by status to return count and total value per stage.
    """
    query = """
    SELECT status, COUNT(*) as count, COALESCE(SUM(value), 0.0) as total_value
    FROM deals
    GROUP BY status
    ORDER BY CASE status
        WHEN 'New' THEN 1
        WHEN 'Contacted' THEN 2
        WHEN 'Qualified' THEN 3
        WHEN 'Proposal' THEN 4
        WHEN 'Won' THEN 5
        WHEN 'Lost' THEN 6
        ELSE 7
    END
    """
    return execute_query(query)

def get_leads_by_status() -> List[Dict[str, Any]]:
    """
    Groups leads by status to return count per status.
    """
    query = "SELECT status, COUNT(*) as count FROM leads GROUP BY status"
    return execute_query(query)

def get_pipeline_by_salesperson() -> List[Dict[str, Any]]:
    """
    Groups active deals by salesperson.
    """
    query = """
    SELECT s.name as salesperson, COALESCE(SUM(d.value), 0.0) as total_value, COUNT(d.id) as deal_count
    FROM deals d
    LEFT JOIN salespeople s ON d.owner_id = s.id
    WHERE d.status NOT IN ('Won', 'Lost')
    GROUP BY s.name
    ORDER BY total_value DESC
    """
    return execute_query(query)

def get_deals_by_industry() -> List[Dict[str, Any]]:
    """
    Groups deals by customer industry.
    """
    query = """
    SELECT c.industry, COUNT(d.id) as deal_count, COALESCE(SUM(d.value), 0.0) as total_value
    FROM deals d
    JOIN customers c ON d.customer_id = c.id
    GROUP BY c.industry
    ORDER BY deal_count DESC
    """
    return execute_query(query)

def get_monthly_deal_trend() -> List[Dict[str, Any]]:
    """
    Returns created deal count per month.
    """
    query = """
    SELECT SUBSTR(created_at, 1, 7) as month, COUNT(*) as deal_count, COALESCE(SUM(value), 0.0) as total_value
    FROM deals
    GROUP BY SUBSTR(created_at, 1, 7)
    ORDER BY month ASC
    """
    return execute_query(query)

def get_at_risk_deals_data(days_threshold: int = 14) -> List[Dict[str, Any]]:
    """
    Calculates at-risk deals dynamically from SQLite based on updated_at staleness.
    """
    ref_date = get_current_date()
    query = """
    SELECT d.id, d.title, d.value, d.status, d.updated_at, d.customer_id,
           c.name as customer_name, c.company as customer_company,
           s.name as owner_name
    FROM deals d
    JOIN customers c ON d.customer_id = c.id
    LEFT JOIN salespeople s ON d.owner_id = s.id
    WHERE d.status NOT IN ('Won', 'Lost')
    ORDER BY d.value DESC
    """
    rows = execute_query(query)
    at_risk = []
    for r in rows:
        last_updated = safe_parse_date(r.get("updated_at"))
        days_stale = (ref_date - last_updated).days
        if days_stale >= days_threshold:
            r["days_stale"] = days_stale
            r["suggested_next_action"] = f"Follow up with {r['customer_name']} regarding deal #{r['id']} ({r['title']})."
            at_risk.append(r)
    return at_risk

# ==========================================
# CUSTOMER 360 & DIRECTORY SERVICES
# ==========================================

def get_all_customers(search: str = "", industry: str = "All", location: str = "All") -> List[Dict[str, Any]]:
    """
    Retrieves filtered customer list with aggregated active deals and deal values.
    """
    query = """
    SELECT c.id, c.name, c.company, c.industry, c.location, c.customer_type, c.email, c.phone, c.created_at,
           COUNT(d.id) as active_deals,
           COALESCE(SUM(CASE WHEN d.status NOT IN ('Won','Lost') THEN d.value ELSE 0 END), 0.0) as total_deal_value
    FROM customers c
    LEFT JOIN deals d ON c.id = d.customer_id
    WHERE 1=1
    """
    params = []
    if search:
        query += " AND (LOWER(c.name) LIKE LOWER(?) OR LOWER(c.company) LIKE LOWER(?) OR LOWER(c.email) LIKE LOWER(?) OR LOWER(c.phone) LIKE LOWER(?))"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern])

    if industry != "All":
        query += " AND c.industry = ?"
        params.append(industry)

    if location != "All":
        query += " AND c.location = ?"
        params.append(location)

    query += " GROUP BY c.id ORDER BY c.id ASC"
    return execute_query(query, tuple(params))

def get_paginated_customers(search: str = "", industry: str = "All", location: str = "All", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    all_rows = get_all_customers(search=search, industry=industry, location=location)
    total_records = len(all_rows)
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_rows = all_rows[start_idx:end_idx]
    return {
        "items": paginated_rows,
        "total_records": total_records,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "start_record": start_idx + 1 if total_records > 0 else 0,
        "end_record": min(end_idx, total_records)
    }

def get_customer_360(customer_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches 360-degree customer profile: basic details, deals, leads, interactions, notes, and AI insights.
    """
    cust_rows = execute_query("SELECT * FROM customers WHERE id = ?", (customer_id,))
    if not cust_rows:
        return None
    cust = cust_rows[0]

    deals = execute_query("SELECT * FROM deals WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
    leads = execute_query("SELECT * FROM leads WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
    interactions = execute_query("SELECT * FROM interactions WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
    notes = execute_query("SELECT * FROM notes WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))

    total_val = sum(d["value"] for d in deals if d["status"] not in ("Won", "Lost"))
    ai_insight = {
        "summary": f"Customer {cust['name']} ({cust['company']}) has {len(deals)} total deal(s) with ₹{total_val:,.2f} active pipeline.",
        "recommended_action": f"Schedule follow-up call with {cust['name']} regarding recent inquiries." if deals else "Reach out for introductory call.",
        "risk_level": "High" if any((get_current_date() - safe_parse_date(d.get('updated_at'))).days >= 14 for d in deals if d.get('status') not in ('Won','Lost')) else "Normal"
    }

    return {
        "customer": cust,
        "deals": deals,
        "leads": leads,
        "interactions": interactions,
        "notes": notes,
        "ai_insights": ai_insight
    }

# ==========================================
# LEADS & DEALS SERVICES
# ==========================================

def get_all_leads(search: str = "", status: str = "All", assigned_to: str = "All") -> List[Dict[str, Any]]:
    """
    Retrieves filtered lead list.
    """
    query = """
    SELECT l.id, l.customer_id, c.name as customer_name, c.company as customer_company,
           l.source, l.status, l.lead_score, l.expected_value, s.name as assigned_to_name,
           l.created_at, l.updated_at
    FROM leads l
    JOIN customers c ON l.customer_id = c.id
    LEFT JOIN salespeople s ON l.assigned_to = s.id
    WHERE 1=1
    """
    params = []
    if search:
        query += " AND (LOWER(c.name) LIKE LOWER(?) OR LOWER(c.company) LIKE LOWER(?) OR LOWER(l.id) = LOWER(?))"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, search])

    if status != "All":
        query += " AND l.status = ?"
        params.append(status)

    if assigned_to != "All":
        query += " AND s.name = ?"
        params.append(assigned_to)

    query += " ORDER BY l.id ASC"
    return execute_query(query, tuple(params))

def get_paginated_leads(search: str = "", status: str = "All", assigned_to: str = "All", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    all_rows = get_all_leads(search=search, status=status, assigned_to=assigned_to)
    total_records = len(all_rows)
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_rows = all_rows[start_idx:end_idx]
    return {
        "items": paginated_rows,
        "total_records": total_records,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "start_record": start_idx + 1 if total_records > 0 else 0,
        "end_record": min(end_idx, total_records)
    }

def get_all_deals(search: str = "", status: str = "All", owner_name: str = "All", industry: str = "All") -> List[Dict[str, Any]]:
    """
    Retrieves filtered deal list with days since update calculation.
    """
    ref_date = get_current_date()
    query = """
    SELECT d.id, d.title, d.value, d.status, d.probability, d.expected_close,
           c.name as customer_name, c.company as customer_company, c.industry,
           s.name as owner_name, d.created_at, d.updated_at
    FROM deals d
    JOIN customers c ON d.customer_id = c.id
    LEFT JOIN salespeople s ON d.owner_id = s.id
    WHERE 1=1
    """
    params = []
    if search:
        query += " AND (LOWER(d.title) LIKE LOWER(?) OR LOWER(c.name) LIKE LOWER(?) OR LOWER(c.company) LIKE LOWER(?) OR LOWER(d.id) = LOWER(?))"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, search])

    if status != "All":
        query += " AND d.status = ?"
        params.append(status)

    if owner_name != "All":
        query += " AND s.name = ?"
        params.append(owner_name)

    if industry != "All":
        query += " AND c.industry = ?"
        params.append(industry)

    query += " ORDER BY d.id ASC"
    rows = execute_query(query, tuple(params))

    for r in rows:
        last_updated = safe_parse_date(r.get("updated_at"))
        r["days_stale"] = (ref_date - last_updated).days
        r["risk"] = "High Risk" if r["days_stale"] >= 14 and r["status"] not in ("Won", "Lost") else "Low Risk"

    return rows

def get_paginated_deals(search: str = "", status: str = "All", owner_name: str = "All", industry: str = "All", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    all_rows = get_all_deals(search=search, status=status, owner_name=owner_name, industry=industry)
    total_records = len(all_rows)
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_rows = all_rows[start_idx:end_idx]
    return {
        "items": paginated_rows,
        "total_records": total_records,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "start_record": start_idx + 1 if total_records > 0 else 0,
        "end_record": min(end_idx, total_records)
    }

# ==========================================
# INTERACTIONS & NOTES & AUDIT SERVICES
# ==========================================

def get_all_interactions(type_filter: str = "All") -> List[Dict[str, Any]]:
    """
    Retrieves interaction records.
    """
    query = """
    SELECT i.id, i.customer_id, c.name as customer_name, c.company as customer_company,
           i.deal_id, d.title as deal_title, i.type, i.subject, i.summary, s.name as created_by_name, i.created_at
    FROM interactions i
    JOIN customers c ON i.customer_id = c.id
    LEFT JOIN deals d ON i.deal_id = d.id
    LEFT JOIN salespeople s ON i.created_by = s.id
    WHERE 1=1
    """
    params = []
    if type_filter != "All":
        query += " AND i.type = ?"
        params.append(type_filter)

    query += " ORDER BY i.created_at DESC"
    return execute_query(query, tuple(params))

def get_paginated_interactions(type_filter: str = "All", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    all_rows = get_all_interactions(type_filter=type_filter)
    total_records = len(all_rows)
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_rows = all_rows[start_idx:end_idx]
    return {
        "items": paginated_rows,
        "total_records": total_records,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "start_record": start_idx + 1 if total_records > 0 else 0,
        "end_record": min(end_idx, total_records)
    }

def get_all_notes() -> List[Dict[str, Any]]:
    """
    Retrieves note records.
    """
    query = """
    SELECT n.id, n.customer_id, c.name as customer_name, c.company as customer_company,
           n.deal_id, d.title as deal_title, s.name as author_name, n.content, n.created_at
    FROM notes n
    JOIN customers c ON n.customer_id = c.id
    LEFT JOIN deals d ON n.deal_id = d.id
    LEFT JOIN salespeople s ON n.author_id = s.id
    ORDER BY n.created_at DESC
    """
    return execute_query(query)

def get_paginated_notes(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    all_rows = get_all_notes()
    total_records = len(all_rows)
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_rows = all_rows[start_idx:end_idx]
    return {
        "items": paginated_rows,
        "total_records": total_records,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "start_record": start_idx + 1 if total_records > 0 else 0,
        "end_record": min(end_idx, total_records)
    }

def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves system audit logs from action_log table.
    """
    query = "SELECT id, action_type, target_table, target_id, after_value, performed_by, timestamp FROM action_log ORDER BY id DESC LIMIT ?"
    return execute_query(query, (limit,))

def get_customer_360(customer_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves full Customer 360 profile from SQLite.
    """
    cust_rows = execute_query("SELECT id, name, company, industry, location, customer_type, email, phone, created_at FROM customers WHERE id = ?", (customer_id,))
    if not cust_rows:
        return None
    c = cust_rows[0]
    deals = execute_query("SELECT id, title, value, status, probability, owner_id FROM deals WHERE customer_id = ?", (customer_id,))
    leads = execute_query("SELECT id, source, status, lead_score, expected_value, assigned_to FROM leads WHERE customer_id = ?", (customer_id,))
    interactions = execute_query("SELECT id, type, subject, summary, created_by, created_at FROM interactions WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
    notes = execute_query("SELECT id, content, author_id, created_at FROM notes WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
    
    return {
        "customer": c,
        "deals": deals,
        "leads": leads,
        "interactions": interactions,
        "notes": notes
    }

def get_customer_history_summary(customer_id: str) -> Dict[str, Any]:
    """
    Retrieves chronologically ordered interaction history and notes for a customer from SQLite,
    and returns a structured CRM activity summary.
    """
    cust_rows = execute_query("SELECT id, name, company, industry, location, email, phone FROM customers WHERE id = ?", (customer_id,))
    if not cust_rows:
        return {"success": False, "message": f"Customer ID '{customer_id}' not found.", "summary": "Customer not found."}

    c = cust_rows[0]
    interactions = execute_query(
        """
        SELECT i.created_at, i.type, i.subject, i.summary, s.name as created_by_name, d.title as deal_title
        FROM interactions i
        LEFT JOIN salespeople s ON i.created_by = s.id
        LEFT JOIN deals d ON i.deal_id = d.id
        WHERE i.customer_id = ?
        ORDER BY i.created_at ASC
        """,
        (customer_id,)
    )

    notes = execute_query(
        """
        SELECT n.created_at, n.content, s.name as author_name, d.title as deal_title
        FROM notes n
        LEFT JOIN salespeople s ON n.author_id = s.id
        LEFT JOIN deals d ON n.deal_id = d.id
        WHERE n.customer_id = ?
        ORDER BY n.created_at ASC
        """,
        (customer_id,)
    )

    deals = execute_query("SELECT id, title, value, status FROM deals WHERE customer_id = ?", (customer_id,))

    if not interactions and not notes:
        summary_text = f"Customer History — **{c['name']}** ({c['company']})\n\nThere is no recorded interaction history for this customer in the CRM database."
        return {"success": True, "customer": c, "summary": summary_text, "has_history": False}

    # Chronological merge
    timeline = []
    for i in interactions:
        sp_str = f" by {i['created_by_name']}" if i.get('created_by_name') else ""
        deal_str = f" [Deal: {i['deal_title']}]" if i.get('deal_title') else ""
        timeline.append({
            "date": i["created_at"],
            "type": "Interaction",
            "detail": f"{i['type']}: {i['subject']} — {i['summary']}{sp_str}{deal_str}"
        })
    for n in notes:
        sp_str = f" by {n['author_name']}" if n.get('author_name') else ""
        deal_str = f" [Deal: {n['deal_title']}]" if n.get('deal_title') else ""
        timeline.append({
            "date": n["created_at"],
            "type": "Note",
            "detail": f"Note: {n['content']}{sp_str}{deal_str}"
        })

    timeline.sort(key=lambda x: x["date"])

    lines = [
        f"Customer History — **{c['name']}**",
        f"Company: **{c['company']}** | Location: **{c['location']}** | Industry: **{c['industry']}**\n",
        f"Summary:",
        f"• **{c['name']}** has {len(interactions)} recorded interaction(s) and {len(notes)} note(s) in the CRM.",
        f"• Latest recorded activity was on **{timeline[-1]['date']}**.\n",
        "Recent Activity Timeline:"
    ]

    for item in timeline[-5:]:  # show recent items
        lines.append(f"• **[{item['date']}]** {item['detail']}")

    if deals:
        lines.append("\nCurrent Status:")
        for d in deals:
            lines.append(f"• Deal **{d['title']}**: ₹{int(d['value']):,} (`{d['status']}`)")

    summary_text = "\n".join(lines)
    return {"success": True, "customer": c, "summary": summary_text, "has_history": True, "timeline": timeline}

def get_paginated_audit_logs(page: int = 1, page_size: int = 25) -> Dict[str, Any]:
    all_rows = get_audit_logs(limit=200)
    total_records = len(all_rows)
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_rows = all_rows[start_idx:end_idx]
    return {
        "items": paginated_rows,
        "total_records": total_records,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "start_record": start_idx + 1 if total_records > 0 else 0,
        "end_record": min(end_idx, total_records)
    }

# ==========================================
# CHAT SESSIONS & MESSAGES SERVICES
# ==========================================

def ensure_chat_schema():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        context_type TEXT,
        context_id TEXT,
        context_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)
    cursor.execute("PRAGMA table_info(chat_sessions)")
    cols = [r[1] for r in cursor.fetchall()]
    if "context_json" not in cols:
        cursor.execute("ALTER TABLE chat_sessions ADD COLUMN context_json TEXT")
    conn.commit()
    conn.close()

def generate_chat_title(user_message: str) -> str:
    msg = user_message.strip()
    msg_low = msg.lower()

    # Match names
    for name in ["Rahul Kumar", "Rahul Sharma", "Arjun Sharma", "Meera Iyer", "Karthik Reddy", "Divya Nair", "Sanjay Gupta", "Rohan Deshmukh", "Kavita Verma", "Aman Patel", "Priya Menon", "Ravi Kumar", "Rahul", "Arjun", "Karthik", "Meera", "Divya", "Sanjay", "Rohan", "Kavita", "Aman", "Priya"]:
        if name.lower() in msg_low:
            disp_name = name.split()[0]
            if any(w in msg_low for w in ["email", "phone", "contact", "detail"]):
                return f"{disp_name} — Details"
            elif any(w in msg_low for w in ["deal", "status", "stage", "won", "lost"]):
                return f"{disp_name} — Deal Status"
            elif any(w in msg_low for w in ["history", "summarize", "activity"]):
                return f"{disp_name} — History"
            else:
                return f"{disp_name} — Search"

    # Match industries
    for ind in ["Manufacturing", "Retail", "Logistics", "Finance", "Healthcare", "IT Services", "IT"]:
        if ind.lower() in msg_low:
            disp_ind = "IT Services" if ind.lower() == "it" else ind.title()
            return f"{disp_ind} Customers"

    if any(w in msg_low for w in ["how many", "count of", "total number"]):
        return "Customer Count"
    if "stale" in msg_low or "at risk" in msg_low or "inactive" in msg_low:
        return "Stale High-Value Deals"

    clean = re.sub(r'[^\w\s]', '', msg).strip()
    words = clean.split()
    if len(words) <= 4:
        return clean.title()
    return " ".join(words[:4]).title()

def get_chat_sessions() -> List[Dict[str, Any]]:
    ensure_chat_schema()
    query = "SELECT id, title, context_type, context_id, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC"
    return execute_query(query)

def get_chat_messages(session_id: str) -> List[Dict[str, Any]]:
    ensure_chat_schema()
    query = "SELECT id, session_id, role, content, timestamp FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC"
    return execute_query(query, (session_id,))

def save_chat_message(session_id: str, role: str, content: str, title: Optional[str] = None, context_type: Optional[str] = None, context_id: Optional[str] = None):
    ensure_chat_schema()
    now_str = datetime.now(timezone.utc).isoformat()
    sess_check = execute_query("SELECT id, title FROM chat_sessions WHERE id = ?", (session_id,))
    msg_id = generate_next_id("chat_messages", "MSG")

    conn = get_connection()
    cursor = conn.cursor()

    if not sess_check:
        auto_title = title if (title and title != "CRM Chat") else generate_chat_title(content)
        cursor.execute(
            "INSERT INTO chat_sessions (id, title, context_type, context_id, context_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, auto_title, context_type, context_id, None, now_str, now_str)
        )
    else:
        cursor.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now_str, session_id))

    cursor.execute(
        "INSERT INTO chat_messages (id, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
        (msg_id, session_id, role, content, now_str)
    )

    conn.commit()
    conn.close()

def update_chat_session_context(session_id: str, context_dict: dict):
    ensure_chat_schema()
    now_str = datetime.now(timezone.utc).isoformat()
    ctx_str = json.dumps(context_dict)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chat_sessions SET context_json = ?, updated_at = ? WHERE id = ?", (ctx_str, now_str, session_id))
    conn.commit()
    conn.close()

def get_chat_session_context(session_id: str) -> Optional[dict]:
    ensure_chat_schema()
    rows = execute_query("SELECT context_json FROM chat_sessions WHERE id = ?", (session_id,))
    if rows and rows[0].get("context_json"):
        try:
            return json.loads(rows[0]["context_json"])
        except Exception:
            return None
    return None

def delete_chat_session(session_id: str) -> bool:
    ensure_chat_schema()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return True

# ==========================================
# MUTATION SERVICES (WITH AUTO AUDIT LOGGING)
# ==========================================

def update_deal_status_service(deal_id: str, new_status: str, performed_by: str = "ai_agent") -> Dict[str, Any]:
    """
    Updates deal status in SQLite and records action_log entry.
    """
    deal_rows = execute_query("SELECT id, title, status FROM deals WHERE id = ?", (deal_id,))
    if not deal_rows:
        return {"success": False, "message": f"Deal ID '{deal_id}' not found."}

    old_status = deal_rows[0]["status"]
    if old_status == new_status:
        return {"success": True, "message": f"Deal #{deal_id} is already in status '{new_status}'."}

    now_str = datetime.now().isoformat()
    today_str = CURRENT_DATE_STR

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE deals SET status = ?, updated_at = ? WHERE id = ?", (new_status, today_str, deal_id))

    log_id = generate_next_id("action_log", "LOG")
    cursor.execute(
        "INSERT INTO action_log (id, action_type, target_table, target_id, after_value, performed_by, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (log_id, "UPDATE_DEAL_STATUS", "deals", deal_id, f"status: {old_status} -> {new_status}", performed_by, now_str)
    )

    conn.commit()
    conn.close()

    return {"success": True, "message": f"Updated deal #{deal_id} status from '{old_status}' to '{new_status}'.", "deal_id": deal_id, "old_status": old_status, "new_status": new_status}

def add_note_service(customer_id: str, content: str, deal_id: Optional[str] = None, author_id: str = "EMP001", performed_by: str = "ai_agent") -> Dict[str, Any]:
    """
    Inserts a new note into SQLite and records action_log entry.
    """
    cust_rows = execute_query("SELECT id, name FROM customers WHERE id = ?", (customer_id,))
    if not cust_rows:
        return {"success": False, "message": f"Customer ID '{customer_id}' not found."}

    note_id = generate_next_id("notes", "NOTE")
    now_str = datetime.now().isoformat()
    today_str = CURRENT_DATE_STR

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notes (id, customer_id, deal_id, author_id, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (note_id, customer_id, deal_id, author_id, content, today_str)
    )

    log_id = generate_next_id("action_log", "LOG")
    cursor.execute(
        "INSERT INTO action_log (id, action_type, target_table, target_id, after_value, performed_by, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (log_id, "ADD_NOTE", "notes", note_id, f"content: {content} (customer_id={customer_id})", performed_by, now_str)
    )

    conn.commit()
    conn.close()

    return {"success": True, "message": f"Added note #{note_id} for customer {cust_rows[0]['name']} ({customer_id}).", "note_id": note_id}

def assign_lead_service(deal_id: str, salesperson_name: str, performed_by: str = "ai_agent") -> Dict[str, Any]:
    """
    Assigns a deal owner in SQLite and records action_log entry.
    """
    deal_rows = execute_query("SELECT d.id, d.title, d.owner_id, s.name as current_owner FROM deals d LEFT JOIN salespeople s ON d.owner_id = s.id WHERE d.id = ?", (deal_id,))
    if not deal_rows:
        return {"success": False, "message": f"Deal ID '{deal_id}' not found."}

    sp_rows = execute_query("SELECT id, name FROM salespeople WHERE LOWER(name) LIKE LOWER(?)", (f"%{salesperson_name}%",))
    if not sp_rows:
        return {"success": False, "message": f"Salesperson '{salesperson_name}' not found."}

    new_sp_id = sp_rows[0]["id"]
    new_sp_name = sp_rows[0]["name"]
    old_owner_name = deal_rows[0]["current_owner"] or "Unassigned"

    now_str = datetime.now().isoformat()
    today_str = CURRENT_DATE_STR

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE deals SET owner_id = ?, updated_at = ? WHERE id = ?", (new_sp_id, today_str, deal_id))

    log_id = generate_next_id("action_log", "LOG")
    cursor.execute(
        "INSERT INTO action_log (id, action_type, target_table, target_id, after_value, performed_by, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (log_id, "ASSIGN_LEAD", "deals", deal_id, f"owner: {old_owner_name} -> {new_sp_name} ({new_sp_id})", performed_by, now_str)
    )

    conn.commit()
    conn.close()

    return {"success": True, "message": f"Assigned deal #{deal_id} to {new_sp_name}.", "deal_id": deal_id, "new_owner": new_sp_name}

# ==========================================
# DYNAMIC FILTER LOOKUPS
# ==========================================

def get_distinct_industries() -> List[str]:
    rows = execute_query("SELECT DISTINCT industry FROM customers WHERE industry IS NOT NULL AND industry != '' ORDER BY industry")
    return [r["industry"] for r in rows]

def get_distinct_locations() -> List[str]:
    rows = execute_query("SELECT DISTINCT location FROM customers WHERE location IS NOT NULL AND location != '' ORDER BY location")
    return [r["location"] for r in rows]

def get_distinct_customer_types() -> List[str]:
    rows = execute_query("SELECT DISTINCT customer_type FROM customers WHERE customer_type IS NOT NULL AND customer_type != '' ORDER BY customer_type")
    return [r["customer_type"] for r in rows]

def get_distinct_salespeople() -> List[str]:
    rows = execute_query("SELECT DISTINCT name FROM salespeople WHERE name IS NOT NULL AND name != '' ORDER BY name")
    return [r["name"] for r in rows]

def get_distinct_lead_sources() -> List[str]:
    rows = execute_query("SELECT DISTINCT source FROM leads WHERE source IS NOT NULL AND source != '' ORDER BY source")
    return [r["source"] for r in rows]
