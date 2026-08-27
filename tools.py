import json
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union, Tuple
from db import execute_query, execute_write, log_action, generate_next_id

def get_current_date() -> date:
    return date.today()

def get_current_date_str() -> str:
    return get_current_date().isoformat()

CURRENT_DATE_STR = get_current_date_str()

def normalize_phone(phone_str: Optional[str]) -> str:
    if not phone_str:
        return ""
    digits = re.sub(r'\D', '', str(phone_str))
    return digits[-10:] if len(digits) >= 10 else digits

def clean_search_term(raw_str: str) -> str:
    if not raw_str:
        return ""
    stopwords = {
        "give", "me", "find", "get", "show", "what", "whats", "what's", "tell", "the",
        "email", "address", "phone", "number", "customer", "at", "with", "s", "for",
        "details", "contact", "lead", "deal", "assign", "move", "to", "won", "a", "an",
        "of", "is", "are", "in", "please", "my", "our", "history", "reach", "can", "you",
        "how", "where", "who", "stage", "mark", "set", "add", "note", "do", "we", "have",
        "has", "had", "would", "should", "could", "i", "about", "regarding", "from", "by",
        "on", "and", "or", "opportunity", "status", "change", "update", "close",
        "belong", "belongs", "belonging", "interact", "interaction", "activity", "active",
        "pipeline", "does", "last", "when", "did", "deals", "deal", "much", "salesperson"
    }
    clean_punct = re.sub(r'[^\w\s]', ' ', raw_str.lower())
    words = [w for w in clean_punct.split() if w not in stopwords]
    return " ".join(words).strip()

# ==========================================
# GENERIC CRM EXECUTION TOOLS ENGINE
# ==========================================

def build_filter_clause(entity: str, filters: List[Dict[str, Any]]) -> Tuple[str, List[Any]]:
    if not filters:
        return "", []

    field_map = {
        "customers": {
            "id": "c.id", "name": "c.name", "company": "c.company", "industry": "c.industry",
            "location": "c.location", "customer_type": "c.customer_type", "email": "c.email", "phone": "c.phone",
            "created_at": "c.created_at", "updated_at": "c.updated_at",
            "status": "COALESCE(d.status, l.status)"
        },
        "leads": {
            "id": "l.id", "lead_name": "l.lead_name", "name": "l.lead_name", "status": "l.status", "source": "l.source", "lead_score": "l.lead_score",
            "expected_value": "l.expected_value", "assigned_to": "l.assigned_to", "customer_id": "l.customer_id",
            "customer_name": "c.name", "customer_company": "c.company", "company": "c.company", "industry": "c.industry",
            "assigned_to_name": "s.name", "created_at": "l.created_at", "updated_at": "l.updated_at"
        },
        "deals": {
            "id": "d.id", "title": "d.title", "value": "d.value", "status": "d.status",
            "probability": "d.probability", "owner_id": "d.owner_id", "customer_id": "d.customer_id",
            "customer_name": "c.name", "customer_company": "c.company", "company": "c.company", "industry": "c.industry",
            "location": "c.location", "owner_name": "s.name", "created_at": "d.created_at", "updated_at": "d.updated_at"
        },
        "interactions": {
            "id": "i.id", "type": "i.type", "subject": "i.subject", "customer_id": "i.customer_id",
            "customer_name": "c.name", "created_by": "i.created_by", "created_by_name": "s.name", "created_at": "i.created_at"
        },
        "notes": {
            "id": "n.id", "customer_id": "n.customer_id", "customer_name": "c.name", "content": "n.content", "author_id": "n.author_id", "created_at": "n.created_at"
        },
        "salespeople": {
            "id": "s.id", "name": "s.name", "email": "s.email"
        }
    }

    schema_map = field_map.get(entity, {})
    where_clauses = []
    params = []

    for f in filters:
        raw_field = f.get("field", "")
        op = f.get("operator", "equals").lower()
        val = f.get("value")

        if not raw_field or val is None:
            continue

        col_name = schema_map.get(raw_field.lower(), f"{entity[0]}.{raw_field}")

        if op in ("equals", "="):
            where_clauses.append(f"LOWER({col_name}) = LOWER(?)")
            params.append(str(val))
        elif op in ("contains", "like"):
            where_clauses.append(f"LOWER({col_name}) LIKE LOWER(?)")
            params.append(f"%{val}%")
        elif op in ("greater_than_or_equal", ">="):
            where_clauses.append(f"{col_name} >= ?")
            params.append(val)
        elif op in ("greater_than", ">"):
            where_clauses.append(f"{col_name} > ?")
            params.append(val)
        elif op in ("less_than_or_equal", "<="):
            where_clauses.append(f"{col_name} <= ?")
            params.append(val)
        elif op in ("less_than", "<"):
            where_clauses.append(f"{col_name} < ?")
            params.append(val)
        elif op == "in" and isinstance(val, list):
            placeholders = ", ".join(["LOWER(?)"] * len(val))
            where_clauses.append(f"LOWER({col_name}) IN ({placeholders})")
            params.extend([str(v).lower() for v in val])
        elif op in ("not_in", "not in") and isinstance(val, list):
            placeholders = ", ".join(["LOWER(?)"] * len(val))
            where_clauses.append(f"LOWER({col_name}) NOT IN ({placeholders})")
            params.extend([str(v).lower() for v in val])
        elif op in ("not_equals", "!="):
            where_clauses.append(f"LOWER({col_name}) != LOWER(?)")
            params.append(str(val))

    where_str = " AND " + " AND ".join(where_clauses) if where_clauses else ""
    return where_str, params

def search_records(
    entity: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    sort: Optional[Dict[str, str]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generic search tool for all CRM entities supporting flexible schema filters.
    """
    filters = filters or []

    if entity == "customers":
        sql = """
        SELECT c.id, c.name, c.company, c.industry, c.location, c.customer_type, c.email, c.phone, c.created_at,
               COUNT(DISTINCT d.id) as active_deals, COALESCE(SUM(CASE WHEN d.status NOT IN ('Won','Lost') THEN d.value ELSE 0 END), 0.0) as pipeline_value
        FROM customers c
        LEFT JOIN deals d ON c.id = d.customer_id
        LEFT JOIN leads l ON c.id = l.customer_id
        WHERE 1=1
        """
        group_clause = " GROUP BY c.id"
        sort_field_map = {"value": "pipeline_value", "name": "c.name", "created_at": "c.created_at"}
    elif entity == "leads":
        sql = """
        SELECT l.id, l.customer_id, l.lead_name, c.name as customer_name, c.company as customer_company, c.industry,
               l.source, l.status, l.lead_score, l.expected_value, l.assigned_to, s.name as assigned_to_name,
               l.created_at, l.updated_at
        FROM leads l
        JOIN customers c ON l.customer_id = c.id
        LEFT JOIN salespeople s ON l.assigned_to = s.id
        WHERE 1=1
        """
        group_clause = ""
        sort_field_map = {"score": "l.lead_score", "value": "l.expected_value", "created_at": "l.created_at"}
    elif entity == "deals":
        sql = """
        SELECT d.id, d.customer_id, c.name as customer_name, c.company as customer_company, c.industry, c.location,
               d.title, d.value, d.status, d.probability, d.owner_id, s.name as owner_name,
               d.expected_close, d.created_at, d.updated_at
        FROM deals d
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN salespeople s ON d.owner_id = s.id
        WHERE 1=1
        """
        group_clause = ""
        sort_field_map = {"value": "d.value", "created_at": "d.created_at", "updated_at": "d.updated_at"}
    elif entity == "interactions":
        sql = """
        SELECT i.id, i.customer_id, c.name as customer_name, c.company as customer_company,
               i.deal_id, d.title as deal_title, i.type, i.subject, i.summary, i.created_by, s.name as created_by_name, i.created_at
        FROM interactions i
        JOIN customers c ON i.customer_id = c.id
        LEFT JOIN deals d ON i.deal_id = d.id
        LEFT JOIN salespeople s ON i.created_by = s.id
        WHERE 1=1
        """
        group_clause = ""
        sort_field_map = {"created_at": "i.created_at"}
    elif entity == "notes":
        sql = """
        SELECT n.id, n.customer_id, c.name as customer_name, n.deal_id, d.title as deal_title,
               n.author_id, s.name as author_name, n.content, n.created_at
        FROM notes n
        JOIN customers c ON n.customer_id = c.id
        LEFT JOIN deals d ON n.deal_id = d.id
        LEFT JOIN salespeople s ON n.author_id = s.id
        WHERE 1=1
        """
        group_clause = ""
        sort_field_map = {"created_at": "n.created_at"}
    elif entity == "salespeople":
        sql = "SELECT s.id, s.name, s.email FROM salespeople s WHERE 1=1"
        group_clause = ""
        sort_field_map = {"name": "s.name"}
    else:
        return {"success": False, "records": [], "count": 0, "message": f"Unsupported entity '{entity}'"}

    where_str, params = build_filter_clause(entity, filters)
    sql += where_str + group_clause

    if sort and "field" in sort:
        sf = sort["field"]
        s_col = sort_field_map.get(sf, sf)
        s_dir = "DESC" if sort.get("direction", "").upper() == "DESC" else "ASC"
        sql += f" ORDER BY {s_col} {s_dir}"

    if limit:
        sql += " LIMIT ?"
        params.append(limit)
        if offset:
            sql += " OFFSET ?"
            params.append(offset)

    try:
        rows = execute_query(sql, tuple(params))
        return {"success": True, "records": rows, "count": len(rows)}
    except Exception as err:
        return {"success": False, "records": [], "count": 0, "message": f"Database error: {str(err)}"}

def count_records(entity: str, filters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Generic count execution tool for all CRM entities.
    """
    table_map = {
        "customers": "customers c LEFT JOIN deals d ON c.id = d.customer_id LEFT JOIN leads l ON c.id = l.customer_id",
        "leads": "leads l JOIN customers c ON l.customer_id = c.id LEFT JOIN salespeople s ON l.assigned_to = s.id",
        "deals": "deals d JOIN customers c ON d.customer_id = c.id LEFT JOIN salespeople s ON d.owner_id = s.id",
        "interactions": "interactions i JOIN customers c ON i.customer_id = c.id LEFT JOIN salespeople s ON i.created_by = s.id",
        "notes": "notes n JOIN customers c ON n.customer_id = c.id LEFT JOIN salespeople s ON n.author_id = s.id",
        "salespeople": "salespeople s"
    }

    if entity not in table_map:
        return {"success": False, "count": 0, "message": f"Unsupported entity '{entity}'"}

    col_count = "DISTINCT c.id" if entity == "customers" else "*"
    sql = f"SELECT COUNT({col_count}) as count FROM {table_map[entity]} WHERE 1=1"
    where_str, params = build_filter_clause(entity, filters or [])
    sql += where_str

    try:
        rows = execute_query(sql, tuple(params))
        cnt = rows[0]["count"] if rows else 0
        return {"success": True, "count": cnt}
    except Exception as err:
        return {"success": False, "count": 0, "message": f"Database error: {str(err)}"}

def get_record(entity: str, identifier: str) -> Dict[str, Any]:
    """
    Retrieves a single CRM record by ID, exact name, phone, or email.
    """
    res = search_records(entity, filters=[{"field": "id", "operator": "equals", "value": identifier}])
    if res.get("records"):
        return {"success": True, "found": True, "record": res["records"][0]}

    # Fallback to name match
    if entity == "customers":
        res = search_records(entity, filters=[{"field": "name", "operator": "contains", "value": identifier}])
    elif entity == "salespeople":
        res = search_records(entity, filters=[{"field": "name", "operator": "contains", "value": identifier}])
    elif entity == "deals":
        res = search_records(entity, filters=[{"field": "title", "operator": "contains", "value": identifier}])

    recs = res.get("records", [])
    if len(recs) == 1:
        return {"success": True, "found": True, "record": recs[0]}
    elif len(recs) > 1:
        return {"success": True, "found": True, "ambiguous": True, "candidates": recs}
    return {"success": False, "found": False, "message": f"Record '{identifier}' not found in {entity}."}

def get_related_records(
    entity: str,
    record_id: str,
    related_entity: str,
    limit: Optional[int] = 10
) -> Dict[str, Any]:
    """
    Traverses CRM entity relationships (e.g. customer -> deals, customer -> interactions).
    """
    if entity == "customers":
        if related_entity == "deals":
            return search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": record_id}], limit=limit)
        elif related_entity in ("leads", "lead"):
            return search_records("leads", filters=[{"field": "customer_id", "operator": "equals", "value": record_id}], limit=limit)
        elif related_entity in ("interactions", "history"):
            return search_records("interactions", filters=[{"field": "customer_id", "operator": "equals", "value": record_id}], sort={"field": "created_at", "direction": "DESC"}, limit=limit)
        elif related_entity in ("notes", "note"):
            return search_records("notes", filters=[{"field": "customer_id", "operator": "equals", "value": record_id}], sort={"field": "created_at", "direction": "DESC"}, limit=limit)
    elif entity == "deals":
        if related_entity in ("interactions", "history"):
            return search_records("interactions", filters=[{"field": "deal_id", "operator": "equals", "value": record_id}], sort={"field": "created_at", "direction": "DESC"}, limit=limit)
    elif entity == "salespeople":
        if related_entity == "deals":
            return search_records("deals", filters=[{"field": "owner_id", "operator": "equals", "value": record_id}], limit=limit)
        elif related_entity == "leads":
            return search_records("leads", filters=[{"field": "assigned_to", "operator": "equals", "value": record_id}], limit=limit)

    return {"success": False, "records": [], "count": 0, "message": f"Relationship {entity} -> {related_entity} not supported."}

def get_record_history(entity: str, record_id: str) -> Dict[str, Any]:
    """
    Retrieves full timeline history (interactions + notes) for a customer or deal.
    """
    interactions_res = get_related_records(entity, record_id, "interactions", limit=20)
    notes_res = get_related_records(entity, record_id, "notes", limit=20)

    timeline = []
    for item in interactions_res.get("records", []):
        timeline.append({"type": "Interaction", "date": item["created_at"], "title": f"[{item['type']}] {item['subject']}", "details": item["summary"], "by": item["created_by_name"]})
    for item in notes_res.get("records", []):
        timeline.append({"type": "Note", "date": item["created_at"], "title": "Note Added", "details": item["content"], "by": item["author_name"]})

    timeline.sort(key=lambda x: x["date"], reverse=True)
    return {"success": True, "timeline": timeline, "count": len(timeline)}

def aggregate_records(
    entity: str,
    agg_function: str = "SUM",
    agg_field: str = "value",
    group_by: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    sort: Optional[Dict[str, str]] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generic analytical aggregation tool supporting SUM, AVG, COUNT, MAX, MIN grouped by CRM schema attributes.
    """
    agg_fn = agg_function.upper()
    if agg_fn not in ("SUM", "AVG", "COUNT", "MAX", "MIN"):
        agg_fn = "SUM"

    table_sql = {
        "deals": "FROM deals d JOIN customers c ON d.customer_id = c.id LEFT JOIN salespeople s ON d.owner_id = s.id",
        "leads": "FROM leads l JOIN customers c ON l.customer_id = c.id LEFT JOIN salespeople s ON l.assigned_to = s.id",
        "customers": "FROM customers c",
        "interactions": "FROM interactions i JOIN customers c ON i.customer_id = c.id LEFT JOIN salespeople s ON i.created_by = s.id"
    }.get(entity, "FROM deals d JOIN customers c ON d.customer_id = c.id LEFT JOIN salespeople s ON d.owner_id = s.id")

    field_map = {
        "value": "d.value", "lead_score": "l.lead_score", "expected_value": "l.expected_value", "id": "1"
    }
    col_expr = field_map.get(agg_field.lower(), "d.value" if entity == "deals" else "c.id")

    group_map = {
        "owner_id": ("s.id as group_id, s.name as group_name", "s.id"),
        "salesperson": ("s.id as group_id, s.name as group_name", "s.id"),
        "industry": ("c.industry as group_name", "c.industry"),
        "location": ("c.location as group_name", "c.location"),
        "customer_type": ("c.customer_type as group_name", "c.customer_type"),
        "status": ("d.status as group_name" if entity == "deals" else "l.status as group_name", "d.status" if entity == "deals" else "l.status"),
        "customer": ("c.id as group_id, c.name as group_name", "c.id")
    }

    if group_by and group_by.lower() in group_map:
        select_grp, sql_group_by = group_map[group_by.lower()]
        select_clause = f"SELECT {select_grp}, {agg_fn}({col_expr}) as aggregate_value"
        group_clause = f" GROUP BY {sql_group_by}"
    else:
        select_clause = f"SELECT {agg_fn}({col_expr}) as aggregate_value"
        group_clause = ""

    where_str, params = build_filter_clause(entity, filters or [])

    order_dir = "DESC"
    if sort and sort.get("direction", "").upper() == "ASC":
        order_dir = "ASC"

    order_clause = f" ORDER BY aggregate_value {order_dir}"
    limit_clause = f" LIMIT {limit}" if limit else ""

    sql = select_clause + " " + table_sql + " WHERE 1=1" + where_str + group_clause + order_clause + limit_clause
    rows = execute_query(sql, tuple(params))

    total_val = rows[0]["aggregate_value"] if (rows and not group_by) else None
    return {"success": True, "results": rows, "total": total_val, "count": len(rows)}

def update_record(entity: str, record_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates record fields in SQLite, verifies database write, and records action log.
    """
    if not changes:
        return {"success": False, "message": "No changes specified."}

    table_name = "deals" if entity == "deals" else ("leads" if entity == "leads" else "customers")
    set_clauses = [f"{k} = ?" for k in changes.keys()]
    params = list(changes.values()) + [record_id]

    sql = f"UPDATE {table_name} SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
    execute_write(sql, tuple(params))

    # Post-mutation Verification Query
    verified = execute_query(f"SELECT * FROM {table_name} WHERE id = ?", (record_id,))
    if not verified:
        return {"success": False, "error": f"Database mutation failed: Record {record_id} not found after update."}

    rec = verified[0]
    log_id = log_action(f"UPDATE_{entity.upper()}", table_name, record_id, json.dumps(changes))
    return {
        "success": True,
        "action": f"update_{entity}",
        "record_id": record_id,
        "audit_log_id": log_id,
        "message": f"Updated {entity} record '{record_id}' successfully.",
        "changes": changes,
        "verified_record": dict(rec)
    }

# ==========================================
# UNIVERSAL ENTITY RESOLUTION LAYER
# ==========================================

def resolve_customer(
    query_str: Optional[str] = None,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    customer_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Universal entity resolution for Customers following Search Priority.
    """
    all_custs = execute_query("""
        SELECT c.id, c.name, c.company, c.email, c.phone, c.industry, c.location, c.customer_type, c.created_at,
               COUNT(d.id) as active_deals, COALESCE(SUM(CASE WHEN d.status NOT IN ('Won','Lost') THEN d.value ELSE 0 END), 0.0) as pipeline_value
        FROM customers c
        LEFT JOIN deals d ON c.id = d.customer_id
        GROUP BY c.id
    """)

    if not all_custs:
        return {"success": False, "found": False, "candidates": [], "message": "No customers found in database."}

    raw_target = (query_str or "").strip()

    if customer_id or raw_target.upper().startswith("CUST"):
        t_id = customer_id or raw_target
        match = [c for c in all_custs if c["id"].lower() == t_id.lower()]
        if match:
            return {"success": True, "found": True, "ambiguous": False, "customer": match[0], "candidates": match}

    target_email = (email or raw_target).strip().lower()
    if target_email and "@" in target_email:
        match = [c for c in all_custs if c["email"].lower() == target_email]
        if match:
            return {"success": True, "found": True, "ambiguous": False, "customer": match[0], "candidates": match}

    target_phone = normalize_phone(phone or raw_target)
    if target_phone and len(target_phone) >= 7:
        match = [c for c in all_custs if normalize_phone(c["phone"]) == target_phone]
        if match:
            return {"success": True, "found": True, "ambiguous": False, "customer": match[0], "candidates": match}

    cleaned_term = clean_search_term(raw_target) if raw_target else ""
    target = cleaned_term or raw_target.strip().lower()

    target_name = (name or target).strip().lower()
    if target_name:
        match = [c for c in all_custs if c["name"].lower() == target_name]
        if len(match) == 1:
            return {"success": True, "found": True, "ambiguous": False, "customer": match[0], "candidates": match}
        elif len(match) > 1:
            return {"success": True, "found": True, "ambiguous": True, "count": len(match), "candidates": match}

    target_comp = (company or target).strip().lower()
    if target_comp:
        match = [c for c in all_custs if target_comp in c["company"].lower()]
        if len(match) == 1:
            return {"success": True, "found": True, "ambiguous": False, "customer": match[0], "candidates": match}
        elif len(match) > 1:
            return {"success": True, "found": True, "ambiguous": True, "count": len(match), "candidates": match}

    if target:
        # First priority: Full customer name inside target query
        exact_name_matches = [c for c in all_custs if c["name"].lower() in target]
        if len(exact_name_matches) == 1:
            return {"success": True, "found": True, "ambiguous": False, "customer": exact_name_matches[0], "candidates": exact_name_matches}
        elif len(exact_name_matches) > 1:
            return {"success": True, "found": True, "ambiguous": True, "count": len(exact_name_matches), "candidates": exact_name_matches}

        match = []
        for c in all_custs:
            c_name_low = c["name"].lower()
            c_first_name = c_name_low.split()[0]
            c_comp_low = c["company"].lower()
            if (target in c_name_low or 
                target in c_comp_low or 
                target in c["email"].lower() or 
                target in c["location"].lower() or
                target in c["industry"].lower() or
                c_comp_low in target or
                (len(c_first_name) >= 3 and c_first_name in target.split())):
                match.append(c)

        if not match:
            first_tok = target.split()[0] if target else ""
            if len(first_tok) >= 3:
                match = [c for c in all_custs if first_tok in c["name"].lower().split()[0]]

        if not match:
            target_norm = target.replace("th", "t").replace("ph", "f")
            for c in all_custs:
                c_norm = c["name"].lower().replace("th", "t").replace("ph", "f")
                if target_norm in c_norm or c_norm.split()[0] in target_norm:
                    match.append(c)

        if len(match) == 1:
            return {"success": True, "found": True, "ambiguous": False, "customer": match[0], "candidates": match}
        elif len(match) > 1:
            return {"success": True, "found": True, "ambiguous": True, "count": len(match), "candidates": match}

    return {"success": False, "found": False, "candidates": [], "message": "No customer found matching criteria."}

def resolve_deal(
    query_str: Optional[str] = None,
    deal_name: Optional[str] = None,
    customer_name: Optional[str] = None,
    company: Optional[str] = None,
    salesperson: Optional[str] = None,
    status: Optional[str] = None,
    deal_id: Optional[str] = None
) -> Dict[str, Any]:
    all_deals = execute_query("""
        SELECT d.id, d.customer_id, c.name as customer_name, c.company as customer_company, c.industry,
               d.title, d.value, d.status, d.probability, d.owner_id, s.name as owner_name, d.created_at, d.updated_at
        FROM deals d
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN salespeople s ON d.owner_id = s.id
    """)

    raw_target = (query_str or "").strip()
    target = clean_search_term(raw_target) if raw_target else ""

    if deal_id or raw_target.upper().startswith("DEAL"):
        t_id = deal_id or raw_target
        match = [d for d in all_deals if d["id"].lower() == t_id.lower()]
        if match:
            return {"success": True, "found": True, "ambiguous": False, "deal": match[0], "candidates": match}

    c_name = (customer_name or company or "").strip().lower()
    t_title = (deal_name or target).strip().lower()

    scored_deals = []
    for d in all_deals:
        title_low = (d.get("title") or "").lower()
        cust_low = (d.get("customer_name") or "").lower()
        comp_low = (d.get("customer_company") or "").lower()

        if salesperson and salesperson.lower() not in (d.get("owner_name") or "").lower():
            continue
        if status and status.lower() != (d.get("status") or "").lower():
            continue

        score = 0
        if t_title:
            if t_title == title_low:
                score += 20
            elif t_title in title_low:
                score += 10
            elif title_low in t_title:
                score += 8

            t_words = set(t_title.split())
            title_words = set(re.sub(r'[^\w\s]', ' ', title_low).split())
            comp_words = set(re.sub(r'[^\w\s]', ' ', comp_low).split())
            cust_words = set(re.sub(r'[^\w\s]', ' ', cust_low).split())

            common_title = t_words.intersection(title_words)
            common_comp = t_words.intersection(comp_words | cust_words)

            score += len(common_title) * 4 + len(common_comp) * 1

        if c_name and (c_name in cust_low or c_name in comp_low):
            score += 5

        if score > 0:
            scored_deals.append((score, d))

    if scored_deals:
        scored_deals.sort(key=lambda x: x[0], reverse=True)
        max_score = scored_deals[0][0]
        top_matches = [d for sc, d in scored_deals if sc == max_score]
        if len(top_matches) == 1:
            return {"success": True, "found": True, "ambiguous": False, "deal": top_matches[0], "candidates": top_matches}
        elif len(top_matches) > 1:
            return {"success": True, "found": True, "ambiguous": True, "count": len(top_matches), "candidates": top_matches}

    return {"success": False, "found": False, "candidates": [], "message": "No deal found matching criteria."}

def resolve_lead(
    query_str: Optional[str] = None,
    lead_name: Optional[str] = None,
    customer_name: Optional[str] = None,
    company: Optional[str] = None,
    lead_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resolves a lead by lead_id, exact lead_name, customer_name, company, or query_str.
    Supports ambiguity detection and returns explicit candidates with stable IDs.
    """
    all_leads = execute_query("""
        SELECT l.id, l.customer_id, l.lead_name, c.name as customer_name, c.company as customer_company,
               l.source, l.status, l.lead_score, l.expected_value, l.assigned_to, s.name as assigned_to_name,
               l.created_at, l.updated_at
        FROM leads l
        JOIN customers c ON l.customer_id = c.id
        LEFT JOIN salespeople s ON l.assigned_to = s.id
    """)

    if not all_leads:
        return {"success": False, "found": False, "candidates": [], "message": "No leads found in database."}

    # 1. By lead_id or LEAD prefix
    t_id = lead_id or (query_str if query_str and query_str.upper().startswith("LEAD") else None)
    if t_id:
        match = [l for l in all_leads if l["id"].lower() == t_id.lower()]
        if match:
            return {"success": True, "found": True, "ambiguous": False, "lead": match[0], "candidates": match}

    target = (query_str or "").strip()
    target_low = target.lower()
    l_name_target = (lead_name or "").strip().lower()
    c_name_target = (customer_name or "").strip().lower()
    comp_target = (company or "").strip().lower()

    # 2. Exact lead_name match
    if l_name_target:
        match = [l for l in all_leads if (l.get("lead_name") or "").lower() == l_name_target]
        if len(match) == 1:
            return {"success": True, "found": True, "ambiguous": False, "lead": match[0], "candidates": match}
        elif len(match) > 1:
            return {"success": True, "found": True, "ambiguous": True, "count": len(match), "candidates": match}

    # 3. Match lead_name in query_str
    if target_low:
        match_by_name = [l for l in all_leads if l.get("lead_name") and l["lead_name"].lower() in target_low]
        if len(match_by_name) == 1:
            return {"success": True, "found": True, "ambiguous": False, "lead": match_by_name[0], "candidates": match_by_name}
        elif len(match_by_name) > 1:
            return {"success": True, "found": True, "ambiguous": True, "count": len(match_by_name), "candidates": match_by_name}

    # 4. Match customer_name / company / query_str
    c_term = clean_search_term(target) or target_low
    matched = [
        l for l in all_leads 
        if (c_name_target and c_name_target in l["customer_name"].lower()) or
           (comp_target and comp_target in l["customer_company"].lower()) or
           (c_term and (c_term in l["customer_name"].lower() or c_term in l["customer_company"].lower() or (l.get("lead_name") and c_term in l["lead_name"].lower())))
    ]

    if len(matched) == 1:
        return {"success": True, "found": True, "ambiguous": False, "lead": matched[0], "candidates": matched}
    elif len(matched) > 1:
        return {"success": True, "found": True, "ambiguous": True, "count": len(matched), "candidates": matched}

    return {"success": False, "found": False, "candidates": [], "message": f"No lead found matching criteria."}

def resolve_employee(
    query_str: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    salesperson_id: Optional[str] = None
) -> Dict[str, Any]:
    all_sp = execute_query("SELECT id, name, email FROM salespeople")
    raw_target = (query_str or name or email or "").strip()
    target = clean_search_term(raw_target) if raw_target else raw_target.lower()

    if salesperson_id or raw_target.upper().startswith("EMP"):
        t_id = salesperson_id or raw_target
        match = [s for s in all_sp if s["id"].lower() == t_id.lower()]
        if match:
            return {"success": True, "found": True, "ambiguous": False, "salesperson": match[0], "candidates": match}

    if "@" in raw_target:
        match = [s for s in all_sp if s["email"].lower() == raw_target.lower()]
        if match:
            return {"success": True, "found": True, "ambiguous": False, "salesperson": match[0], "candidates": match}

    match = [s for s in all_sp if (target and (target in s["name"].lower() or s["name"].lower() in target or s["name"].split()[0].lower() in target))]
    if not match:
        match = [s for s in all_sp if s["name"].lower() in raw_target.lower() or s["name"].split()[0].lower() in raw_target.lower()]

    if len(match) == 1:
        return {"success": True, "found": True, "ambiguous": False, "salesperson": match[0], "candidates": match}
    elif len(match) > 1:
        return {"success": True, "found": True, "ambiguous": True, "count": len(match), "candidates": match}

    return {"success": False, "found": False, "candidates": [], "message": f"No salesperson/employee found matching '{target}'."}

# ==========================================
# DELEGATED SPECIFIC HELPERS
# ==========================================

def count_customers(industry: Optional[str] = None, location: Optional[str] = None, customer_type: Optional[str] = None, company: Optional[str] = None) -> Dict[str, Any]:
    filters = []
    if industry and industry != "All": filters.append({"field": "industry", "operator": "equals", "value": industry})
    if location and location != "All": filters.append({"field": "location", "operator": "equals", "value": location})
    if customer_type and customer_type != "All": filters.append({"field": "customer_type", "operator": "equals", "value": customer_type})
    if company: filters.append({"field": "company", "operator": "contains", "value": company})
    return count_records("customers", filters)

def count_leads(status: Optional[str] = None, source: Optional[str] = None, min_score: Optional[int] = None) -> Dict[str, Any]:
    filters = []
    if status: filters.append({"field": "status", "operator": "equals", "value": status})
    if source: filters.append({"field": "source", "operator": "equals", "value": source})
    if min_score: filters.append({"field": "lead_score", "operator": "greater_than", "value": min_score})
    return count_records("leads", filters)

def count_deals(status: Optional[str] = None, min_value: Optional[float] = None, max_value: Optional[float] = None, owner: Optional[str] = None) -> Dict[str, Any]:
    filters = []
    if status: filters.append({"field": "status", "operator": "equals", "value": status})
    if min_value: filters.append({"field": "value", "operator": "greater_than", "value": min_value})
    if max_value: filters.append({"field": "value", "operator": "less_than", "value": max_value})
    if owner: filters.append({"field": "owner_name", "operator": "contains", "value": owner})
    return count_records("deals", filters)

def search_customers(name: Optional[str] = None, company: Optional[str] = None, industry: Optional[str] = None, location: Optional[str] = None, customer_type: Optional[str] = None, query_str: Optional[str] = None) -> Dict[str, Any]:
    filters = []
    if query_str or name: filters.append({"field": "name", "operator": "contains", "value": query_str or name})
    if company: filters.append({"field": "company", "operator": "contains", "value": company})
    if industry and industry != "All": filters.append({"field": "industry", "operator": "equals", "value": industry})
    if location and location != "All": filters.append({"field": "location", "operator": "equals", "value": location})
    if customer_type and customer_type != "All": filters.append({"field": "customer_type", "operator": "equals", "value": customer_type})
    res = search_records("customers", filters)
    recs = res.get("records", [])
    return {"success": True, "found": bool(recs), "count": len(recs), "candidates": recs}

def search_leads(status: Optional[str] = None, source: Optional[str] = None, min_score: Optional[int] = None, min_value: Optional[float] = None) -> Dict[str, Any]:
    filters = []
    if status: filters.append({"field": "status", "operator": "equals", "value": status})
    if source: filters.append({"field": "source", "operator": "equals", "value": source})
    if min_score: filters.append({"field": "lead_score", "operator": "greater_than", "value": min_score})
    if min_value: filters.append({"field": "expected_value", "operator": "greater_than", "value": min_value})
    res = search_records("leads", filters)
    return {"success": True, "count": res["count"], "leads": res["records"]}

def search_deals(customer: Optional[str] = None, customer_id: Optional[str] = None, status: Optional[str] = None, salesperson: Optional[str] = None, industry: Optional[str] = None, min_value: Optional[float] = None, max_value: Optional[float] = None) -> Dict[str, Any]:
    filters = []
    if customer_id: filters.append({"field": "customer_id", "operator": "equals", "value": customer_id})
    elif customer: filters.append({"field": "customer_name", "operator": "contains", "value": customer})
    if status: filters.append({"field": "status", "operator": "equals", "value": status})
    if salesperson: filters.append({"field": "owner_name", "operator": "contains", "value": salesperson})
    if industry: filters.append({"field": "industry", "operator": "equals", "value": industry})
    if min_value: filters.append({"field": "value", "operator": "greater_than", "value": min_value})
    if max_value: filters.append({"field": "value", "operator": "less_than", "value": max_value})
    res = search_records("deals", filters)
    return {"success": True, "count": res["count"], "deals": res["records"]}

def get_customer_details(customer_id: str) -> Dict[str, Any]:
    res = get_record("customers", customer_id)
    if res.get("found"):
        return {"success": True, "customer": res["record"]}
    return {"success": False, "message": f"Customer '{customer_id}' not found."}

def get_customer_history(customer_id: str) -> Dict[str, Any]:
    return get_record_history("customers", customer_id)

def get_at_risk_deals(days_threshold: int = 14) -> Dict[str, Any]:
    curr_date = get_current_date_str()
    sql = """
    SELECT d.id, d.title, d.value, d.status, d.updated_at, c.name as customer_name, c.company as customer_company,
           s.name as owner_name, CAST((JULIANDAY(?) - JULIANDAY(d.updated_at)) AS INTEGER) as days_stale
    FROM deals d
    JOIN customers c ON d.customer_id = c.id
    LEFT JOIN salespeople s ON d.owner_id = s.id
    WHERE d.status NOT IN ('Won', 'Lost')
      AND (JULIANDAY(?) - JULIANDAY(d.updated_at)) >= ?
    ORDER BY days_stale DESC
    """
    rows = execute_query(sql, (curr_date, curr_date, days_threshold))
    return {"success": True, "count": len(rows), "at_risk_deals": rows}

def update_deal_status(deal_id: str, new_status: str) -> Dict[str, Any]:
    valid_statuses = {"new": "New", "contacted": "Contacted", "qualified": "Qualified", "proposal": "Proposal", "won": "Won", "lost": "Lost"}
    norm_status = valid_statuses.get(str(new_status).strip().lower(), str(new_status).capitalize())
    return update_record("deals", deal_id, {"status": norm_status})

def add_note(customer_id: str, content: str, deal_id: Optional[str] = None, author_id: Optional[str] = "EMP001") -> Dict[str, Any]:
    note_id = generate_next_id("notes", "NOTE")
    created_at = get_current_date_str()
    query = "INSERT INTO notes (id, customer_id, deal_id, author_id, content, created_at) VALUES (?, ?, ?, ?, ?, ?)"
    execute_write(query, (note_id, customer_id, deal_id, author_id or "EMP001", content, created_at))

    # Verification query
    verified = execute_query("SELECT id, customer_id, content FROM notes WHERE id = ?", (note_id,))
    if not verified:
        return {"success": False, "error": "Database mutation failed: Note was not inserted into SQLite."}

    log_id = log_action("ADD_NOTE", "notes", note_id, None, content)
    return {"success": True, "action": "add_note", "note_id": note_id, "audit_log_id": log_id, "verified_record": dict(verified[0]), "message": "Note added successfully."}

def assign_deal(deal_id: str, salesperson_name: str) -> Dict[str, Any]:
    sp_res = resolve_employee(query_str=salesperson_name)
    if not sp_res.get("found"):
        return {"success": False, "message": f"Salesperson '{salesperson_name}' not found."}
    sp = sp_res["salesperson"]
    res = update_record("deals", deal_id, {"owner_id": sp["id"]})
    if res.get("success"):
        res["assigned_salesperson"] = sp["name"]
    return res

def assign_lead(lead_id: str, salesperson_name: str) -> Dict[str, Any]:
    sp_res = resolve_employee(query_str=salesperson_name)
    if not sp_res.get("found"):
        return {"success": False, "message": f"Salesperson '{salesperson_name}' not found."}
    sp = sp_res["salesperson"]
    res = update_record("leads", lead_id, {"assigned_to": sp["id"]})
    if res.get("success"):
        res["assigned_salesperson"] = sp["name"]
    return res
