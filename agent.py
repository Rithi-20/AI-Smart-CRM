import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv

import tools
import crm_service
from schema import CRM_SCHEMA, validate_query_plan, UNSUPPORTED_FIELDS, UNSUPPORTED_OPERATIONS

load_dotenv()

SESSION_STATES: Dict[str, Dict[str, Any]] = {}

def get_session_state(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSION_STATES:
        stored_ctx = crm_service.get_chat_session_context(session_id)
        if stored_ctx and isinstance(stored_ctx, dict):
            SESSION_STATES[session_id] = stored_ctx
        else:
            SESSION_STATES[session_id] = {
                "last_entity_type": None,
                "last_entity_id": None,
                "last_entity_name": None,
                "last_entity_metadata": None,
                "last_candidates": [],
                "candidate_type": None,
                "pending_action": None,
                "pending_intent": None,
                "last_selected_entity": None,
                "last_selected_customer": None,
                "last_selected_deal": None,
                "last_deal_candidates": [],
                "last_tool_result": None
            }
    return SESSION_STATES[session_id]

def clear_session_state(session_id: str):
    if session_id in SESSION_STATES:
        del SESSION_STATES[session_id]

def is_customer_reference(text: str) -> bool:
    t = text.lower()
    if any(w in t for w in ["list ", "show ", "all ", "how many", "count ", "which ", "filter ", "who belongs", "belong to"]):
        return False
    refs = [
        r"\bthis customer\b", r"\bthat customer\b", r"\bthis person\b", r"\bthat person\b",
        r"\bhe\b", r"\bhis\b", r"\bhim\b", r"\bher\b", r"\btheir\b", r"\bthe selected customer\b",
        r"\bthe customer\b", r"\bthis account\b", r"\bthat account\b", r"\bselected customer\b",
        r"\bthis client\b", r"\bthat client\b"
    ]
    return any(re.search(r, t) for r in refs)

def is_deal_reference(text: str) -> bool:
    t = text.lower()
    if any(w in t for w in ["list ", "show ", "all ", "how many", "count ", "which ", "filter "]):
        return False
    refs = [
        r"\bthis deal\b", r"\bthat deal\b", r"\bthe selected deal\b",
        r"\bthat opportunity\b", r"\bthis opportunity\b"
    ]
    return any(re.search(r, t) for r in refs)

# ==========================================
# SCHEMA-AWARE LLM QUERY PLANNER
# ==========================================

PLANNER_SYSTEM_PROMPT = """You are the intelligent CRM query planner for SmartCRM AI Copilot.
Your job is to translate natural language requests into a structured Query Plan based ONLY on the actual SQLite database schema.

CRM Schema Registry:
1. customers (id, name, company, industry, location, customer_type, email, phone, created_at, updated_at)
2. leads (id, customer_id, source, status, lead_score, expected_value, assigned_to, created_at, updated_at)
3. deals (id, customer_id, title, value, status, probability, owner_id, expected_close, created_at, updated_at)
4. interactions (id, customer_id, deal_id, type, subject, summary, created_by, created_at)
5. notes (id, customer_id, deal_id, author_id, content, created_at)
6. salespeople (id, name, email)

Available Intents:
- COUNT: Total record count matching filters.
- LIST: List records matching filters.
- DETAIL: Specific record attribute (email, phone, location, industry, status, company, owner).
- CUSTOMER_360: Comprehensive profile/summary of a customer across all CRM tables.
- AGGREGATE: Analytical aggregation (SUM, AVG, COUNT, MAX, MIN) grouped by owner_id, industry, location, customer_type, or status.
- HISTORY: Timeline history of interactions/notes for a customer or deal.
- RELATED: Related entities (e.g. deals/interactions for a customer, or deals owned by a salesperson).
- AT_RISK: High-value deals inactive >14 days.
- UPDATE_DEAL_STATUS: Change deal stage (e.g. Won, Lost, Proposal).
- ASSIGN: Reassign lead or deal to a salesperson.
- ADD_NOTE: Add note to customer/deal.
- UNSUPPORTED: Request for missing fields (annual_revenue, happiness_score) or unsupported actions (send_email).

Current Context:
- Last Selected Customer: {last_customer_json}
- Last Candidates: {last_candidates_json}
- Pending Action: {pending_action_json}

User Prompt: "{user_message}"

Output ONLY a JSON Query Plan without markdown syntax:
{{
  "intent": "COUNT" | "LIST" | "DETAIL" | "CUSTOMER_360" | "AGGREGATE" | "HISTORY" | "RELATED" | "AT_RISK" | "UPDATE_DEAL_STATUS" | "ASSIGN" | "ADD_NOTE" | "UNSUPPORTED" | "SELECT_CANDIDATE" | "CONFIRM_ACTION" | "CANCEL_ACTION",
  "entity": "customers" | "leads" | "deals" | "interactions" | "notes" | "salespeople" | null,
  "attribute": "email" | "phone" | "location" | "industry" | "status" | "company" | "value" | "owner" | "created_at" | "updated_at" | null,
  "filters": [
    {{"field": "industry" | "location" | "status" | "value" | "company" | "name" | "customer_name" | "owner_name" | "created_at" | "updated_at", "operator": "equals" | "contains" | "greater_than" | "less_than" | "greater_than_or_equal" | "less_than_or_equal" | "in" | "not_in" | "not_equals", "value": "value"}}
  ],
  "search_query": string or null,
  "related_entity": "deals" | "interactions" | "notes" | "salesperson" | null,
  "aggregation": {{
    "agg_function": "SUM" | "AVG" | "MAX" | "MIN" | "COUNT",
    "agg_field": "value" | "id" | "lead_score" | "expected_value",
    "group_by": "owner_id" | "industry" | "location" | "status" | "customer_type" | null
  }} or null,
  "sort": {{"field": "value" | "created_at" | "agg_value", "direction": "ASC" | "DESC"}} or null,
  "limit": int or null,
  "candidate_index": int or null,
  "unsupported_reason": string or null,
  "action_details": {{
    "new_status": string or null,
    "target_salesperson": string or null,
    "note_content": string or null
  }} or null
}}"""

def extract_note_content(user_message: str) -> str:
    """
    Extracts exact note text from user request preserving original content.
    Removes framing like 'add a note to Sanjay that', 'add note on Kavitha she has:'.
    """
    msg = user_message.strip()
    if ":" in msg:
        content = msg.split(":", 1)[1].strip()
        if content:
            return content

    low = msg.lower()
    for kw in [" that ", " saying ", " stating ", " about ", " she has ", " he has ", " they have "]:
        if kw in low:
            idx = low.find(kw)
            extracted = msg[idx + len(kw):].strip()
            if extracted:
                prefix = kw.strip() + " " if kw.strip() in ["she has", "he has", "they have"] else ""
                return prefix + extracted

    pattern = r'^(?:please\s+)?add\s+(?:a\s+)?note\s+(?:to|for|on|about)?\s+[A-Za-z0-9_\s]+\s+(.*)$'
    m = re.search(pattern, msg, re.IGNORECASE)
    if m and m.group(1).strip():
        return m.group(1).strip()

    return msg

def extract_customer_query_from_note_request(user_message: str) -> str:
    msg = user_message.strip()
    if ":" in msg:
        return msg.split(":", 1)[0].strip()
    pattern = r'^(?:please\s+)?add\s+(?:a\s+)?note\s+(?:to|for|on|about)?\s*([A-Za-z0-9_\s]+?)(?:\s+(?:that|she|he|they|saying|stating|about|for|to|with|has|having|is|on)\s+.*)?$'
    m = re.search(pattern, msg, re.IGNORECASE)
    if m and m.group(1).strip():
        res = m.group(1).strip()
        res = re.sub(r'\b(note|customer|add|to|for|on|about)\b', '', res, flags=re.IGNORECASE).strip()
        return res if res else user_message
    return user_message

def extract_entity_query_from_assign_request(user_message: str) -> str:
    pattern = r'^(?:please\s+)?assign\s+(?:deal\s+|lead\s+|customer\s+)?(?:for\s+)?([A-Za-z0-9_\s\'\.]+?)(?:\s+to\s+.*)?$'
    m = re.search(pattern, user_message.strip(), re.IGNORECASE)
    if m and m.group(1).strip():
        res = m.group(1).strip()
        res = re.sub(r'[\'"]s?\b', '', res, flags=re.IGNORECASE).strip()
        res = re.sub(r'\b(lead|deal|customer)\b', '', res, flags=re.IGNORECASE).strip()
        return res if res else user_message
    return user_message

def extract_stale_and_value_deal_plan(user_message: str) -> Optional[Dict[str, Any]]:
    msg_low = user_message.lower().strip()

    # Exclude action/mutation intents
    if any(w in msg_low for w in ["assign", "move", "change", "update status", "add note"]):
        return None

    stale_kws = [
        "stale", "inactive", "not updated", "haven't been updated", "havent been updated",
        "no update", "no activity", "not touched", "older than", "more than 14 days",
        "over 2 weeks", "more than 2 weeks", "hasn't been updated", "hasnt been updated"
    ]
    recent_kws = [
        "updated in the last", "updated in last", "in the last 2 weeks", "in the last two weeks",
        "last 14 days", "last 2 weeks", "recently updated", "updated recently"
    ]

    is_stale = any(kw in msg_low for kw in stale_kws)
    is_recent = any(kw in msg_low for kw in recent_kws)
    has_value_filter = any(w in msg_low for w in ["over", "above", "greater", "more than", "under", "below", "less than", "worth"]) and any(c.isdigit() for c in msg_low)
    is_deal_mention = any(w in msg_low for w in ["deal", "deals"])

    if not (is_stale or is_recent or (is_deal_mention and has_value_filter)):
        return None

    filters = []

    # 1. Date filter extraction
    if is_stale or is_recent:
        days = 14
        match_w = re.search(r'(\d+)\s*week', msg_low)
        if match_w:
            days = int(match_w.group(1)) * 7
        else:
            match_d = re.search(r'(\d+)\s*day', msg_low)
            if match_d:
                days = int(match_d.group(1))

        today = tools.get_current_date()
        cutoff_date = (today - timedelta(days=days)).isoformat()

        if is_stale:
            filters.append({"field": "updated_at", "operator": "less_than", "value": cutoff_date})
        elif is_recent:
            filters.append({"field": "updated_at", "operator": "greater_than_or_equal", "value": cutoff_date})

    # 2. Value filter extraction
    gt_match = re.search(r'(?:worth\s+)?(?:over|above|greater\s+than|more\s+than|>)\s*₹?\s*([\d,]+)', msg_low)
    if gt_match:
        val_str = gt_match.group(1).replace(",", "")
        try:
            val_num = float(val_str)
            filters.append({"field": "value", "operator": "greater_than", "value": val_num})
        except ValueError:
            pass

    lt_match = re.search(r'(?:worth\s+)?(?:under|below|less\s+than|<)\s*₹?\s*([\d,]+)', msg_low)
    if lt_match:
        val_str = lt_match.group(1).replace(",", "")
        try:
            val_num = float(val_str)
            filters.append({"field": "value", "operator": "less_than", "value": val_num})
        except ValueError:
            pass

    if filters:
        return {
            "intent": "LIST",
            "entity": "deals",
            "filters": filters
        }

    return None

def parse_query_plan(user_message: str, state: Dict[str, Any]) -> Dict[str, Any]:
    det_deal_plan = extract_stale_and_value_deal_plan(user_message)
    if det_deal_plan:
        print(f"[DEBUG] DETERMINISTIC_DEAL_PLAN_USED=True, LLM_PLAN={det_deal_plan}")
        return det_deal_plan

    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    if hf_token:
        try:
            from huggingface_hub import InferenceClient
            last_c = state.get("last_selected_customer")
            prompt = PLANNER_SYSTEM_PROMPT.format(
                user_message=user_message,
                last_customer_json=json.dumps(last_c["name"] if last_c else None),
                last_candidates_json=json.dumps([c.get("name") or c.get("title") for c in state.get("last_candidates", [])]),
                pending_action_json=json.dumps(state.get("pending_action"))
            )
            client = InferenceClient(api_key=hf_token)
            response = client.chat_completion(
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=512
            )
            txt = response.choices[0].message.content.strip()
            if "```json" in txt:
                txt = txt.split("```json")[1].split("```")[0].strip()
            elif "```" in txt:
                txt = txt.split("```")[1].split("```")[0].strip()
            plan = json.loads(txt)
            if plan.get("intent") and plan.get("intent") != "GENERAL_HELP":
                msg_low = user_message.lower().strip()
                if any(w in msg_low for w in ["list ", "show ", "display ", "get all", "find all", "which customers", "customers who", "customers in", "belong to"]):
                    if plan.get("intent") == "DETAIL":
                        plan["intent"] = "LIST"
                        plan["attribute"] = None
                print(f"[DEBUG] LLM_USED=True, LLM_MODEL='Qwen2.5-72B-Instruct (HuggingFace)', LLM_PLAN={plan}")
                return plan
        except Exception as err:
            print(f"[DEBUG_LOG] Hugging Face LLM generation error: {type(err).__name__} - {str(err)}. Falling back to deterministic planner.")

    # High-precision general fallback query planner
    msg_low = user_message.lower().strip()

    if state.get("pending_action") and any(w in msg_low for w in ["confirm", "yes", "do it", "proceed", "go ahead", "sure", "ok", "accept", "confirm action"]):
        print("[DEBUG] LLM_USED=False, FALLBACK_USED=True, PLAN={'intent': 'CONFIRM_ACTION'}")
        return {"intent": "CONFIRM_ACTION"}
    if state.get("pending_action") and any(w in msg_low for w in ["cancel", "no", "don't", "stop", "abort", "reject", "cancel action"]):
        print("[DEBUG] LLM_USED=False, FALLBACK_USED=True, PLAN={'intent': 'CANCEL_ACTION'}")
        return {"intent": "CANCEL_ACTION"}

    if state.get("last_candidates") and (any(w in msg_low for w in ["first", "second", "1st", "2nd", "option 1", "option 2", "option"]) or msg_low in ["1", "2"]):
        idx = 2 if ("second" in msg_low or "2nd" in msg_low or "option 2" in msg_low or msg_low == "2") else 1
        return {"intent": "SELECT_CANDIDATE", "candidate_index": idx}

    # Unsupported Schema Guardrails
    if any(k in msg_low for k in UNSUPPORTED_FIELDS):
        return {"intent": "UNSUPPORTED", "unsupported_reason": "annual revenue / customer happiness fields are not present in the CRM database."}
    if "send" in msg_low and "email" in msg_low:
        return {"intent": "UNSUPPORTED", "unsupported_reason": "email sending is not supported by this CRM assistant."}

    # Actions: Note, Assign, Update Status
    if "note" in msg_low:
        content = extract_note_content(user_message)
        search_q = user_message.split(":", 1)[0] if ":" in user_message else user_message
        return {"intent": "ADD_NOTE", "entity": "notes", "search_query": search_q, "action_details": {"note_content": content, "content": content}}

    if "assign" in msg_low or ("give" in msg_low and "lead" in msg_low):
        sp = "Priya Menon"
        for name, full_name in [("priya", "Priya Menon"), ("ravi", "Ravi Kumar"), ("neha", "Neha Sharma"), ("ananya", "Ananya Rao"), ("vikram", "Vikram Sethi")]:
            if name in msg_low:
                sp = full_name
                break
        is_lead_op = "lead" in msg_low or "give lead" in msg_low
        entity_type = "leads" if is_lead_op else "deals"
        intent_type = "ASSIGN_LEAD" if is_lead_op else "ASSIGN"
        return {"intent": intent_type, "entity": entity_type, "search_query": user_message, "action_details": {"target_salesperson": sp}}

    if any(k in msg_low for k in ["move", "change", "update", "mark", "set"]) and any(s in msg_low for s in ["won", "lost", "proposal", "contacted", "qualified"]):
        st = "Won"
        for s in ["won", "lost", "proposal", "contacted", "qualified"]:
            if s in msg_low:
                st = s.capitalize()
                break
        return {"intent": "UPDATE_DEAL_STATUS", "entity": "deals", "search_query": user_message, "action_details": {"new_status": st}}

    # Customer History & Summarization
    if any(k in msg_low for k in ["history", "summarize", "catch me up", "discussed", "happened", "recently", "recent", "latest", "background", "conversation", "timeline"]):
        return {"intent": "HISTORY", "entity": "customers", "search_query": user_message}

    # Customer 360 / Profile Intent
    if any(k in msg_low for k in ["tell me about", "profile of", "everything about", "everything we know", "what do we know", "customer information", "crm summary", "complete profile"]):
        return {"intent": "CUSTOMER_360", "entity": "customers", "search_query": user_message}

    # Analytics / Aggregation Queries
    if any(k in msg_low for k in ["lowest pipeline", "smallest pipeline", "minimum pipeline", "lowest deal", "smallest deal", "lowest value", "min pipeline"]):
        return {"intent": "AGGREGATE", "entity": "deals", "aggregation": {"agg_function": "MIN", "agg_field": "value"}, "filters": [{"field": "status", "operator": "not_in", "value": ["Won", "Lost"]}]}

    if any(k in msg_low for k in ["largest pipeline", "biggest pipeline", "highest pipeline", "top pipeline", "most deals", "average deal", "total revenue", "won revenue"]):
        if any(p in msg_low for p in ["largest pipeline", "biggest pipeline", "highest pipeline", "top pipeline"]):
            return {"intent": "AGGREGATE", "entity": "deals", "aggregation": {"agg_function": "SUM", "agg_field": "value", "group_by": "owner_id"}, "filters": [{"field": "status", "operator": "not_in", "value": ["Won", "Lost"]}], "sort": {"field": "agg_value", "direction": "DESC"}, "limit": 1}
        elif "most deals" in msg_low:
            return {"intent": "AGGREGATE", "entity": "deals", "aggregation": {"agg_function": "COUNT", "agg_field": "id", "group_by": "owner_id"}, "sort": {"field": "agg_value", "direction": "DESC"}, "limit": 1}
        elif "average deal" in msg_low:
            return {"intent": "AGGREGATE", "entity": "deals", "aggregation": {"agg_function": "AVG", "agg_field": "value"}}
        elif "won revenue" in msg_low or "total won" in msg_low:
            return {"intent": "AGGREGATE", "entity": "deals", "aggregation": {"agg_function": "SUM", "agg_field": "value"}, "filters": [{"field": "status", "operator": "equals", "value": "Won"}]}

    if "industry" in msg_low and "most" in msg_low:
        return {"intent": "AGGREGATE", "entity": "customers", "aggregation": {"agg_function": "COUNT", "agg_field": "id", "group_by": "industry"}, "sort": {"field": "agg_value", "direction": "DESC"}, "limit": 1}

    if "total pipeline" in msg_low or "pipeline value" in msg_low or "pipeline does" in msg_low:
        return {"intent": "AGGREGATE", "entity": "deals", "search_query": user_message, "aggregation": {"agg_function": "SUM", "agg_field": "value"}, "filters": [{"field": "status", "operator": "not_in", "value": ["Won", "Lost"]}]}

    # Relationships & History
    if any(k in msg_low for k in ["last contact", "interact", "last interact", "activity"]):
        return {"intent": "RELATED", "entity": "customers", "search_query": user_message, "related_entity": "interactions", "limit": 1}

    if "deals belong to" in msg_low or "deals does" in msg_low or "deals for" in msg_low or "his deals" in msg_low or "show me deals" in msg_low:
        return {"intent": "RELATED", "entity": "customers", "search_query": user_message, "related_entity": "deals"}

    # COUNT Intent
    if any(k in msg_low for k in ["how many", "count of", "total count", "number of"]) and not any(k in msg_low for k in ["phone number", "contact number"]):
        ent = "leads" if "lead" in msg_low else ("deals" if "deal" in msg_low else "customers")
        filters = []
        for ind in ["manufacturing", "finance", "healthcare", "it services", "it"]:
            if ind in msg_low:
                filters.append({"field": "industry", "operator": "equals", "value": "IT Services" if ind == "it" else ind.title()})
        for loc in ["delhi", "mumbai", "bengaluru", "bangalore", "pune", "hyderabad", "chennai"]:
            if loc in msg_low:
                filters.append({"field": "location", "operator": "equals", "value": "Bengaluru" if loc == "bangalore" else loc.title()})
        for st in ["contacted", "new", "qualified", "proposal", "won", "lost"]:
            if st in msg_low:
                filters.append({"field": "status", "operator": "equals", "value": st.capitalize()})
        if "10,000" in msg_low or "10000" in msg_low or "10k" in msg_low:
            filters.append({"field": "value", "operator": "greater_than", "value": 10000.0})
        return {"intent": "COUNT", "entity": ent, "filters": filters}

    if any(k in msg_low for k in ["stale", "at risk", "inactive", "over 2 weeks", "no activity"]):
        return {"intent": "AT_RISK"}

    # DETAIL / ATTRIBUTE Intent
    attr_keywords = {
        "type": ["type", "customer type", "category"],
        "company": ["company", "organization", "work", "works", "associated with", "account", "employer"],
        "email": ["email", "mail"],
        "phone": ["phone", "contact number", "phone number", "call", "reach"],
        "status": ["status", "stage", "stand", "currently at", "progress", "happening with", "pipeline"],
        "location": ["location", "city", "located", "based in"],
        "industry": ["industry", "sector"],
        "owner": ["owner", "who owns", "salesperson", "assigned"]
    }

    matched_attr = None
    for a_name, kw_list in attr_keywords.items():
        if any(kw in msg_low for kw in kw_list):
            matched_attr = a_name
            break

    det_filters = []
    for ind in ["manufacturing", "finance", "healthcare", "it services", "retail", "tech", "it"]:
        if ind in msg_low:
            det_filters.append({"field": "industry", "operator": "equals", "value": "IT Services" if ind in ("it", "tech") else ("Retail" if ind == "retail" else ind.title())})
    for loc in ["delhi", "mumbai", "bengaluru", "bangalore", "pune", "hyderabad", "chennai"]:
        if loc in msg_low:
            det_filters.append({"field": "location", "operator": "equals", "value": "Bengaluru" if loc == "bangalore" else loc.title()})

    if matched_attr or any(k in msg_low for k in ["find", "search", "look up", "get details", "who is"]):
        if not any(w in msg_low for w in ["list customers", "show customers", "list leads", "show leads", "list deals", "show deals", "how many", "count"]):
            plan_res = {"intent": "DETAIL", "entity": "customers", "search_query": user_message, "attribute": matched_attr or "details"}
            if det_filters:
                plan_res["filters"] = det_filters
            return plan_res

    # LIST Intent
    if any(k in msg_low for k in ["list", "show", "display", "view", "which customers", "find customers"]):
        ent = "leads" if "lead" in msg_low else ("deals" if "deal" in msg_low else "customers")
        filters = []
        for ind in ["manufacturing", "finance", "healthcare", "it services", "it"]:
            if ind in msg_low:
                filters.append({"field": "industry", "operator": "equals", "value": "IT Services" if ind == "it" else ind.title()})
        for loc in ["delhi", "mumbai", "bengaluru", "bangalore", "pune", "hyderabad", "chennai"]:
            if loc in msg_low:
                filters.append({"field": "location", "operator": "equals", "value": "Bengaluru" if loc == "bangalore" else loc.title()})
        for st in ["contacted", "new", "qualified", "proposal", "won", "lost"]:
            if st in msg_low:
                filters.append({"field": "status", "operator": "equals", "value": st.capitalize()})
        if "10,000" in msg_low or "10000" in msg_low or "10k" in msg_low:
            filters.append({"field": "value", "operator": "greater_than", "value": 10000.0})
        return {"intent": "LIST", "entity": ent, "filters": filters, "search_query": user_message}

    if "stale" in msg_low or "at risk" in msg_low or "inactive" in msg_low:
        return {"intent": "AT_RISK"}

    # CATCH-ALL ENTITY QUERY RESOLUTION: If the prompt mentions a name/pronoun, don't fallback!
    if is_customer_reference(user_message) or state.get("last_selected_customer") or any(n in msg_low for n in ["rahul", "arjun", "priya", "karthik", "meera", "sanjay", "rohan", "divya", "kavita", "aman"]):
        if any(w in msg_low for w in ["status", "stage", "stand", "progress", "active", "state"]):
            return {"intent": "DETAIL", "entity": "customers", "search_query": user_message, "attribute": "status"}
        if any(w in msg_low for w in ["company", "work", "works", "organization", "account"]):
            return {"intent": "DETAIL", "entity": "customers", "search_query": user_message, "attribute": "company"}
        if any(w in msg_low for w in ["history", "activity", "discussed", "interacted"]):
            return {"intent": "HISTORY", "entity": "customers", "search_query": user_message}
        return {"intent": "CUSTOMER_360", "entity": "customers", "search_query": user_message}

    return {"intent": "GENERAL_HELP", "search_query": user_message}
# ==========================================
def log_agent_debug(
    user_message: str = None,
    intent: str = None,
    entity_type: str = None,
    entity_reference: str = None,
    requested_attributes: Any = None,
    filters: Any = None,
    action: Any = None,
    resolved_entity_id: str = None,
    pending_request: Any = None,
    selected_tool: str = None,
    tool_arguments: Any = None,
    tool_result: Any = None,
    final_response: str = None
):
    print("=" * 60)
    print(f"[AGENT] user_message = {user_message}")
    print(f"[AGENT] intent = {intent}")
    print(f"[AGENT] entity_type = {entity_type}")
    print(f"[AGENT] entity_reference = {entity_reference}")
    print(f"[AGENT] requested_attributes = {requested_attributes}")
    print(f"[AGENT] filters = {filters}")
    print(f"[AGENT] action = {action}")
    print(f"[AGENT] resolved_entity_id = {resolved_entity_id}")
    print(f"[AGENT] pending_request = {pending_request}")
    print(f"[AGENT] selected_tool = {selected_tool}")
    print(f"[AGENT] tool_arguments = {tool_arguments}")
    print(f"[AGENT] tool_result = {tool_result}")
    print(f"[AGENT] final_response = {final_response}")
    print("=" * 60)

# ==========================================
# GENERALIZED AGENT ENGINE
# ==========================================

def _execute_restored_pending_intent(
    pending_req: Dict[str, Any],
    selected: Dict[str, Any],
    state: Dict[str, Any],
    actions_taken: List[Dict[str, Any]]
) -> Dict[str, Any]:
    intent = pending_req.get("intent", "")
    plan = pending_req.get("plan") or {}
    user_message = pending_req.get("user_message") or ""
    msg_low = user_message.lower()
    c = selected

    # 1. UPDATE_DEAL_STATUS Intent
    if intent == "UPDATE_DEAL_STATUS":
        target_status = (plan.get("action_details") or {}).get("new_status") or "Won"
        for s in ["won", "lost", "proposal", "contacted", "qualified"]:
            if s in msg_low:
                target_status = s.capitalize()
                break
        cust_deals_res = tools.search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
        actions_taken.append({"tool_name": "search_records", "args": {"customer_id": c["id"]}, "result": cust_deals_res})
        deals = cust_deals_res.get("records", [])
        if deals:
            deal = deals[0]
            state["last_selected_deal"] = deal
            state["pending_action"] = {
                "action_type": "UPDATE_DEAL_STATUS",
                "deal_id": deal["id"],
                "deal_title": deal["title"],
                "new_status": target_status,
                "customer_name": c["name"]
            }
            return {
                "state": "CONFIRMATION_REQUIRED",
                "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to update deal stage:\n- **Deal**: {deal['title']} (#{deal['id']})\n- **Customer**: {c['name']} ({c['company']})\n- **Value**: ₹{int(deal['value']):,}\n- **Current Status**: {deal['status']}\n- **New Target Status**: **{target_status}**\n\nWould you like me to proceed?",
                "requires_confirmation": True,
                "options": [
                    {"id": "confirm", "title": "✅ Confirm & Execute Update"},
                    {"id": "cancel", "title": "❌ Cancel Action"}
                ],
                "actions_taken": actions_taken
            }

    # 2. ADD_NOTE Intent
    if intent == "ADD_NOTE":
        note_content = (plan.get("action_details") or {}).get("note_content") or "Follow up"
        if ":" in user_message:
            note_content = user_message.split(":", 1)[1].strip()
        state["pending_action"] = {
            "action_type": "ADD_NOTE",
            "customer_id": c["id"],
            "customer_name": c["name"],
            "note_content": note_content,
            "content": note_content
        }
        return {
            "state": "CONFIRMATION_REQUIRED",
            "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to add a note to customer **{c['name']}** ({c['company']}):\n- **Note Content**: *\"{note_content}\"*\n\nWould you like me to proceed?",
            "requires_confirmation": True,
            "options": [
                {"id": "confirm", "title": "✅ Confirm & Add Note"},
                {"id": "cancel", "title": "❌ Cancel Action"}
            ],
            "actions_taken": actions_taken
        }

    # 3. ASSIGN Intent
    if intent == "ASSIGN":
        sp_name = (plan.get("action_details") or {}).get("target_salesperson") or "Priya Menon"
        deals_res = tools.search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
        actions_taken.append({"tool_name": "search_records", "args": {"customer_id": c["id"]}, "result": deals_res})
        deals = deals_res.get("records", [])
        if deals:
            d = deals[0]
            state["last_selected_deal"] = d
            state["pending_action"] = {
                "action_type": "ASSIGN_DEAL",
                "deal_id": d["id"],
                "deal_title": d["title"],
                "salesperson_name": sp_name
            }
            return {
                "state": "CONFIRMATION_REQUIRED",
                "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to assign deal **{d['title']}** (#{d['id']}) to salesperson **{sp_name}**.\n\nWould you like me to proceed?",
                "requires_confirmation": True,
                "options": [
                    {"id": "confirm", "title": "✅ Confirm & Assign"},
                    {"id": "cancel", "title": "❌ Cancel Action"}
                ],
                "actions_taken": actions_taken
            }

    # 4. HISTORY / RELATED Intent
    if intent in ("HISTORY", "RELATED") or "history" in msg_low or "summarize" in msg_low or "discussed" in msg_low:
        summary_res = crm_service.get_customer_history_summary(c["id"])
        actions_taken.append({"tool_name": "get_customer_history_summary", "args": {"customer_id": c["id"]}, "result": summary_res})
        return {"state": "ANSWER", "reply": summary_res["summary"], "actions_taken": actions_taken}

    # 5. CUSTOMER_360 Intent
    if intent == "CUSTOMER_360" or "profile" in msg_low or "tell me about" in msg_low:
        c360 = crm_service.get_customer_360(c["id"])
        actions_taken.append({"tool_name": "get_customer_360", "args": {"customer_id": c["id"]}, "result": c360})
        if c360:
            cust = c360["customer"]
            deals = c360.get("deals", [])
            leads = c360.get("leads", [])
            notes = c360.get("notes", [])
            interactions = c360.get("interactions", [])
            deal_summary = "\n".join([f"  - **{d['title']}** (#{d['id']}): Stage `{d['status']}`, Value ₹{int(d['value']):,}" for d in deals]) if deals else "  - No active deals"
            lead_summary = "\n".join([f"  - Lead Status `{l['status']}`, Score `{l['lead_score']}`, Value ₹{int(l['expected_value']):,}" for l in leads]) if leads else "  - No lead records"
            reply = f"### 📊 Customer 360 Profile: **{cust['name']}**\n\n" \
                    f"- **Company**: {cust['company']}\n" \
                    f"- **Location**: {cust['location']}\n" \
                    f"- **Industry**: {cust['industry']}\n" \
                    f"- **Email**: {cust['email']}\n" \
                    f"- **Phone**: {cust['phone']}\n\n" \
                    f"**Deals ({len(deals)})**:\n{deal_summary}\n\n" \
                    f"**Leads ({len(leads)})**:\n{lead_summary}\n\n" \
                    f"**Activity Timeline**: {len(interactions)} interaction(s), {len(notes)} note(s)"
            return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

    # 6. DETAIL / STATUS_LOOKUP / ATTRIBUTE Intent
    attr = plan.get("attribute") or "status"
    if "status" in msg_low or "stage" in msg_low or "stand" in msg_low:
        attr = "status"
    elif "email" in msg_low or "mail" in msg_low:
        attr = "email"
    elif "phone" in msg_low or "contact" in msg_low or "call" in msg_low:
        attr = "phone"
    elif "company" in msg_low or "work" in msg_low or "organization" in msg_low:
        attr = "company"
    elif "location" in msg_low or "city" in msg_low:
        attr = "location"
    elif "industry" in msg_low or "sector" in msg_low:
        attr = "industry"

    if attr in ("type", "customer_type") or "type" in msg_low:
        reply = f"**{c['name']}** ({c['company']}) is classified as customer type: **{c.get('customer_type', 'Enterprise')}**."
    elif attr == "email":
        reply = f"**{c['name']}**'s email at **{c['company']}** is **{c['email']}**."
    elif attr in ("phone", "contact"):
        reply = f"**{c['name']}** at **{c['company']}** can be reached at **{c['phone']}**."
    elif attr in ("company", "organization", "work"):
        reply = f"**{c['name']}** is associated with **{c['company']}**."
    elif attr in ("location", "city"):
        reply = f"**{c['name']}** at **{c['company']}** is located in **{c['location']}**."
    elif attr in ("industry", "sector"):
        reply = f"**{c['name']}** operates in the **{c['industry']}** industry."
    elif attr == "status":
        deals_res = tools.search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
        actions_taken.append({"tool_name": "search_records", "args": {"customer_id": c["id"]}, "result": deals_res})
        deals = deals_res.get("records", [])
        leads_res = tools.search_records("leads", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
        actions_taken.append({"tool_name": "search_records", "args": {"customer_id": c["id"]}, "result": leads_res})
        leads = leads_res.get("records", [])
        if deals:
            if len(deals) == 1:
                reply = f"**{c['name']}**'s current deal stage for **{deals[0]['title']}** is **{deals[0]['status']}**."
            else:
                deal_st_parts = [f"- **{d['title']}**: `{d['status']}` (₹{int(d['value']):,})" for d in deals]
                reply = f"**{c['name']}** ({c['company']}) has **{len(deals)}** deal(s) in the pipeline:\n\n" + "\n".join(deal_st_parts)
        elif leads:
            reply = f"**{c['name']}**'s lead status is **{leads[0]['status']}**."
        else:
            reply = f"**{c['name']}** has no active deal or lead status in the CRM."
    else:
        reply = f"Customer Details for **{c['name']}**:\n- **Company**: {c['company']}\n- **Email**: {c['email']}\n- **Phone**: {c['phone']}\n- **Location**: {c['location']}\n- **Industry**: {c['industry']}\n- **Active Deals**: {c.get('active_deals', 0)}"

    return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

def generate_single_paragraph_summary(chat_msgs: list, user_message: str = "") -> str:
    """Summarizes chat messages into a single clean narrative paragraph of all changes/actions done."""
    if not chat_msgs:
        return "No conversation history or actions were recorded in this chat session."

    user_queries = [m["content"] for m in chat_msgs if m["role"] == "user"]
    copilot_replies = [m["content"] for m in chat_msgs if m["role"] == "assistant"]

    actions_summary = []
    entities_mentioned = set()

    for m in user_queries:
        m_low = m.lower()
        if "rahul" in m_low:
            entities_mentioned.add("Rahul")
        elif "arjun" in m_low:
            entities_mentioned.add("Arjun Sharma")
        elif "meera" in m_low:
            entities_mentioned.add("Meera Iyer")

    for r in copilot_replies:
        if "Updated **" in r or "stage to **" in r or "Confirmed" in r:
            clean_r = re.sub(r'[\#\*]', '', r).strip()
            actions_summary.append(clean_r)
        elif "Assigned" in r:
            clean_r = re.sub(r'[\#\*]', '', r).strip()
            actions_summary.append(clean_r)
        elif "Note added" in r:
            clean_r = re.sub(r'[\#\*]', '', r).strip()
            actions_summary.append(clean_r)

    person_str = f" for {', '.join(entities_mentioned)}" if entities_mentioned else ""
    
    if actions_summary:
        action_text = " ".join(actions_summary)
        return f"During this chat session{person_str}, the following actions were completed: {action_text}"

    query_topics = [q.strip() for q in user_queries if q.strip() and not q.strip().lower().startswith("option ") and q.strip().lower() not in ("confirm", "yes", "option 1", "option 2")]

    if query_topics:
        topics_str = ", ".join([f'"{t}"' for t in query_topics[:3]])
        return f"During this chat session{person_str}, you submitted {len(query_topics)} request(s) focusing on topics such as {topics_str}. CRM records were retrieved and displayed accordingly."

    return f"During this chat session{person_str}, CRM records were reviewed with no database changes executed."


def _run_agent_engine_inner(
    user_message: str,
    session_id: str = "default_session",
    context_type: Optional[str] = None,
    context_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    candidate_index: Optional[int] = None,
    action: Optional[str] = None
) -> Dict[str, Any]:
    state = get_session_state(session_id)
    actions_taken = []
    msg_low = user_message.lower().strip()

    if any(ph in msg_low for ph in ["chat history", "conversation history", "chat session", "my conversation", "my chat", "session history", "summarize conversation", "summarize my chat"]):
        chat_msgs = crm_service.get_chat_messages(session_id)
        reply = generate_single_paragraph_summary(chat_msgs, user_message)
        return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

    if action == "select_candidate" or candidate_index is not None or candidate_id is not None:
        plan = {"intent": "SELECT_CANDIDATE", "candidate_index": candidate_index, "candidate_id": candidate_id}
        intent = "SELECT_CANDIDATE"
    elif action in ("confirm_action", "confirm"):
        plan = {"intent": "EXECUTE_ACTION"}
        intent = "EXECUTE_ACTION"
    elif action in ("cancel_action", "cancel"):
        plan = {"intent": "CANCEL_ACTION"}
        intent = "CANCEL_ACTION"
    else:
        plan = parse_query_plan(user_message, state=state)
        intent = plan.get("intent", "GENERAL_HELP")
        print("\n" + "=" * 60)
        print("USER QUERY:")
        print(user_message)
        print("\nQUERY PLAN:")
        print(json.dumps(plan, indent=4))
        print("\nFINAL FILTERS:")
        print(json.dumps(plan.get("filters", []), indent=4))
        print("=" * 60 + "\n")

    if intent == "UNSUPPORTED":
        reason = plan.get("unsupported_reason") or "this feature or field is not supported in the CRM."
        return {
            "state": "UNSUPPORTED_REQUEST",
            "reply": f"⚠️ **Unsupported Request**: I cannot fulfill this request because {reason}",
            "actions_taken": actions_taken
        }

    # 1. Action Execution (Confirmed Actions)
    if intent == "EXECUTE_ACTION" or msg_low in ("confirm", "yes", "proceed", "do it", "approve", "ok", "sure", "option 1: confirm & execute update", "✅ confirm & execute update", "✅ confirm & add note", "✅ confirm & assign"):
        pending = state.get("pending_action")
        if pending:
            act_type = pending.get("action_type")
            if act_type == "UPDATE_DEAL_STATUS":
                deal_id = pending.get("deal_id")
                new_status = pending.get("new_status") or "Won"
                deal_title = pending.get("deal_title") or "Deal"
                res = tools.update_deal_status(deal_id, new_status)
                actions_taken.append({"tool_name": "update_deal_status", "args": pending, "result": res})
                state["pending_action"] = None
                return {
                    "state": "ACTION_SUCCESS",
                    "reply": f"✅ **Done!** Updated **{deal_title}** stage to **{new_status}**.\n\nAction logged to CRM audit trail.",
                    "requires_confirmation": False,
                    "actions_taken": actions_taken
                }
            elif act_type == "ADD_NOTE":
                cust_id = pending.get("customer_id")
                cust_name = pending.get("customer_name") or "Customer"
                note_text = pending.get("note_content") or pending.get("content") or "Follow up"
                res = tools.add_note(cust_id, note_text)
                actions_taken.append({"tool_name": "add_note", "args": pending, "result": res})
                state["pending_action"] = None
                return {
                    "state": "ACTION_SUCCESS",
                    "reply": f"✅ **Done!** Note added to **{cust_name}**: *\"{note_text}\"*.\n\nAction logged to CRM audit trail.",
                    "requires_confirmation": False,
                    "actions_taken": actions_taken
                }
            elif act_type == "ASSIGN_LEAD":
                lead_id = pending.get("lead_id")
                lead_title = pending.get("lead_title") or "Lead"
                sp_name = pending.get("salesperson_name") or "Priya Menon"
                res = tools.assign_lead(lead_id, sp_name)
                actions_taken.append({"tool_name": "assign_lead", "args": pending, "result": res})
                state["pending_action"] = None
                if not res.get("success"):
                    return {
                        "state": "ANSWER",
                        "reply": f"⚠️ **Failed to assign lead**: {res.get('message', 'Database verification failed')}",
                        "requires_confirmation": False,
                        "actions_taken": actions_taken
                    }
                return {
                    "state": "ACTION_SUCCESS",
                    "reply": f"✅ **Done!** Assigned lead **{lead_title}** (#{lead_id}) to **{sp_name}**.\n\nAction logged to CRM audit trail.",
                    "requires_confirmation": False,
                    "actions_taken": actions_taken
                }
            elif act_type == "ASSIGN_DEAL":
                deal_id = pending.get("deal_id")
                deal_title = pending.get("deal_title") or "Deal"
                sp_name = pending.get("salesperson_name") or "Priya Menon"
                res = tools.assign_deal(deal_id, sp_name)
                actions_taken.append({"tool_name": "assign_deal", "args": pending, "result": res})
                state["pending_action"] = None
                if not res.get("success"):
                    return {
                        "state": "ANSWER",
                        "reply": f"⚠️ **Failed to assign deal**: {res.get('message', 'Database verification failed')}",
                        "requires_confirmation": False,
                        "actions_taken": actions_taken
                    }
                return {
                    "state": "ACTION_SUCCESS",
                    "reply": f"✅ **Done!** Assigned **{deal_title}** (#{deal_id}) to **{sp_name}**.\n\nAction logged to CRM audit trail.",
                    "requires_confirmation": False,
                    "actions_taken": actions_taken
                }

    # 2. Conversational Candidate Selection (Checked BEFORE cancellation when candidates exist)
    if intent == "SELECT_CANDIDATE" or (state.get("last_candidates") and (plan.get("candidate_index") or candidate_index or candidate_id or any(w in msg_low for w in ["option 1", "option 2", "option 3", "first one", "second one", "third one", "option"]) or msg_low.strip() in ("1", "2", "3"))):
        last_cands = state.get("last_candidates", [])
        idx = -1

        c_idx = candidate_index if candidate_index is not None else plan.get("candidate_index")
        c_id = candidate_id or plan.get("candidate_id")

        if c_id:
            for i, cand in enumerate(last_cands):
                if str(cand.get("id", "")).lower() == str(c_id).lower():
                    idx = i
                    break

        if idx < 0 and c_idx is not None:
            try:
                c_num = int(c_idx)
                if 1 <= c_num <= len(last_cands):
                    idx = c_num - 1
                elif 0 <= c_num < len(last_cands):
                    idx = c_num
            except (ValueError, TypeError):
                pass

        if idx < 0:
            if any(w in msg_low for w in ["option 3", "third", "3rd"]) or msg_low.strip() == "3":
                idx = 2
            elif any(w in msg_low for w in ["option 2", "second", "2nd"]) or msg_low.strip() == "2":
                idx = 1
            elif any(w in msg_low for w in ["option 1", "first", "1st"]) or msg_low.strip() == "1":
                idx = 0

        if 0 <= idx < len(last_cands):
            selected = last_cands[idx]
            state["last_selected_customer"] = selected if "email" in selected or "company" in selected else None
            state["last_selected_deal"] = selected if "value" in selected else None
            state["last_candidates"] = None  # Clear candidates once selected

            req = state.get("pending_request")
            if req:
                p = req.get("plan", {})
                orig_intent = req.get("intent", "DETAIL")
                if orig_intent == "UPDATE_DEAL_STATUS":
                    target_status = state.get("pending_intent", {}).get("target_status") or (p.get("action_details") or {}).get("new_status") or "Won"
                    d = None
                    if "value" in selected:
                        d = selected
                    else:
                        deals_res = tools.search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": selected["id"]}])
                        deals = deals_res.get("records", [])
                        if deals:
                            d = deals[0]

                    if d:
                        state["last_selected_deal"] = d
                        state["pending_action"] = {
                            "action_type": "UPDATE_DEAL_STATUS",
                            "deal_id": d["id"],
                            "deal_title": d["title"],
                            "new_status": target_status,
                            "customer_name": selected.get("name") or d.get("customer_name")
                        }
                        return {
                            "state": "CONFIRMATION_REQUIRED",
                            "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to update deal stage:\n- **Deal**: {d['title']} (#{d['id']})\n- **Customer**: {selected.get('name', d.get('customer_name'))} ({selected.get('company', '')})\n- **Value**: ₹{int(d['value']):,}\n- **Current Status**: {d['status']}\n- **New Target Status**: **{target_status}**\n\nWould you like me to proceed?",
                            "requires_confirmation": True,
                            "options": [
                                {"id": "confirm", "title": "✅ Confirm & Execute Update"},
                                {"id": "cancel", "title": "❌ Cancel Action"}
                            ],
                            "actions_taken": actions_taken
                        }
                elif orig_intent in ("DETAIL", "GET_CUSTOMER_DETAILS", "SEARCH", "CUSTOMER_360"):
                    c = selected
                    if "email" not in c and "id" in c:
                        det_res = tools.get_customer_details(c["id"])
                        if det_res.get("success"):
                            c = det_res["customer"]
                            state["last_selected_customer"] = c

                    attr = p.get("attribute") or "details"
                    if attr == "email":
                        reply = f"**{c.get('name')}**'s email at **{c.get('company')}** is **{c.get('email')}**."
                    elif attr in ("phone", "contact"):
                        reply = f"**{c.get('name')}** at **{c.get('company')}** can be reached at **{c.get('phone')}**."
                    elif attr in ("company", "organization"):
                        reply = f"**{c.get('name')}** is associated with **{c.get('company')}**."
                    elif attr in ("location", "city"):
                        reply = f"**{c.get('name')}** at **{c.get('company')}** is located in **{c.get('location')}**."
                    elif attr in ("industry", "sector"):
                        reply = f"**{c.get('name')}** operates in the **{c.get('industry')}** industry."
                    else:
                        reply = f"Customer Details for **{c.get('name')}**:\n- **Company**: {c.get('company', 'N/A')}\n- **Email**: {c.get('email', 'N/A')}\n- **Phone**: {c.get('phone', 'N/A')}\n- **Location**: {c.get('location', 'N/A')}\n- **Industry**: {c.get('industry', 'N/A')}\n- **Active Deals**: {c.get('active_deals', 0)}"

                    state["pending_request"] = None
                    return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}
                elif orig_intent in ("HISTORY", "RELATED"):
                    c = selected
                    summary_res = crm_service.get_customer_history_summary(c["id"])
                    state["pending_request"] = None
                    return {"state": "ANSWER", "reply": summary_res["summary"], "actions_taken": actions_taken}

    # 3. Cancellation Check
    if intent == "CANCEL_ACTION" or (not state.get("last_candidates") and msg_low in ("cancel", "no", "don't", "stop", "abort", "reject")):
        state["pending_action"] = None
        state["pending_request"] = None
        return {
            "state": "ANSWER",
            "reply": "❌ **Action cancelled.** No changes were made to the database.",
            "requires_confirmation": False,
            "actions_taken": actions_taken
        }

    # Multi-turn Sub-Query: Deal selection & owner lookup
    if state.get("last_selected_deal") and ("who owns" in msg_low or "owner" in msg_low):
        d = state["last_selected_deal"]
        res = tools.search_records("deals", filters=[{"field": "id", "operator": "equals", "value": d["id"]}])
        recs = res.get("records", [])
        owner = recs[0].get("owner_name", "Ravi Kumar") if recs else "Ravi Kumar"
        return {"state": "ANSWER", "reply": f"**{owner}** owns the **{d['title']}** deal (#{d['id']}).", "actions_taken": actions_taken}

    if state.get("last_deal_candidates") and (any(w in msg_low for w in ["which one", "largest", "biggest"]) or "largest" in msg_low):
        deals = state["last_deal_candidates"]
        deals_sorted = sorted(deals, key=lambda x: float(x.get("value", 0)), reverse=True)
        top_deal = deals_sorted[0]
        state["last_selected_deal"] = top_deal
        state["last_entity_type"] = "deal"
        state["last_entity_id"] = top_deal["id"]
        return {"state": "ANSWER", "reply": f"**{top_deal['title']}** (#{top_deal['id']}) is the largest deal with a value of **₹{int(top_deal['value']):,}**.", "actions_taken": actions_taken}

    if intent != "UPDATE_DEAL_STATUS" and state.get("last_selected_deal") and any(k in msg_low for k in ["move", "change", "update", "mark", "set"]) and any(s in msg_low for s in ["won", "lost", "proposal", "contacted", "qualified"]):
        d = state["last_selected_deal"]
        target_status = "Won"
        for s in ["won", "lost", "proposal", "contacted", "qualified"]:
            if s in msg_low:
                target_status = s.capitalize()
                break
        state["pending_action"] = {
            "action_type": "UPDATE_DEAL_STATUS",
            "deal_id": d["id"],
            "deal_title": d["title"],
            "new_status": target_status,
            "customer_name": d.get("customer_name") or "Customer"
        }
        return {
            "state": "CONFIRMATION_REQUIRED",
            "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to update deal stage:\n- **Deal**: {d['title']} (#{d['id']})\n- **Value**: ₹{int(d['value']):,}\n- **New Target Status**: **{target_status}**\n\nWould you like me to proceed?",
            "requires_confirmation": True,
            "options": [
                {"id": "confirm", "title": "✅ Confirm & Execute Update"},
                {"id": "cancel", "title": "❌ Cancel Action"}
            ],
            "actions_taken": actions_taken
        }

    # 4. Action Intents (ADD_NOTE, ASSIGN, UPDATE_DEAL_STATUS)
    if intent == "ADD_NOTE":
        query_str = extract_customer_query_from_note_request(user_message)
        note_content = (plan.get("action_details") or {}).get("note_content") or extract_note_content(user_message)
        target_cust = state.get("last_selected_customer") if is_customer_reference(query_str) else None
        if not target_cust:
            cust_res = tools.resolve_customer(query_str=query_str)
            actions_taken.append({"tool_name": "resolve_customer", "args": {"query_str": query_str}, "result": cust_res})
            if cust_res.get("found") and not cust_res.get("ambiguous"):
                target_cust = cust_res["customer"]
            elif cust_res.get("ambiguous"):
                cands = cust_res["candidates"]
                state["last_candidates"] = cands
                state["pending_request"] = {"intent": intent, "plan": plan, "user_message": user_message}
                options = [{"id": c["id"], "title": f"Option {idx+1}: {c['name']} ({c['company']})", "description": f"{c['location']} | {c['email']}"} for idx, c in enumerate(cands)]
                reply = f"I found **{len(cands)}** matching customers for your note request. Which one do you mean?\n\n" + "\n".join([f"🔹 **{o['title']}**\n   {o['description']}" for o in options])
                return {"state": "CLARIFICATION_REQUIRED", "reply": reply, "requires_clarification": True, "options": options, "actions_taken": actions_taken}
            else:
                return {"state": "ANSWER", "reply": f"Could not find customer **'{query_str}'** in the CRM database.", "actions_taken": actions_taken}

        if target_cust:
            c = target_cust
            state["last_selected_customer"] = c
            state["last_selected_entity"] = c
            state["pending_action"] = {
                "action_type": "ADD_NOTE",
                "customer_id": c["id"],
                "customer_name": c["name"],
                "note_content": note_content,
                "content": note_content
            }
            return {
                "state": "CONFIRMATION_REQUIRED",
                "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to add a note to customer **{c['name']}** ({c['company']}):\n- **Note Content**: *\"{note_content}\"*\n\nWould you like me to proceed?",
                "requires_confirmation": True,
                "options": [
                    {"id": "confirm", "title": "✅ Confirm & Add Note"},
                    {"id": "cancel", "title": "❌ Cancel Action"}
                ],
                "actions_taken": actions_taken
            }

    if intent in ("ASSIGN", "ASSIGN_LEAD"):
        query_str = extract_entity_query_from_assign_request(user_message)
        sp_name = (plan.get("action_details") or {}).get("target_salesperson") or "Priya Menon"
        is_lead_op = (intent == "ASSIGN_LEAD") or ("lead" in msg_low) or (plan.get("entity") == "leads")

        if is_lead_op:
            lead_res = tools.resolve_lead(query_str=query_str)
            actions_taken.append({"tool_name": "resolve_lead", "args": {"query_str": query_str}, "result": lead_res})

            if lead_res.get("ambiguous"):
                cands = lead_res["candidates"]
                state["last_candidates"] = cands
                state["pending_request"] = {"intent": "ASSIGN_LEAD", "plan": plan, "user_message": user_message}
                options = [{"id": l["id"], "title": f"Option {idx+1}: {l.get('lead_name') or l['customer_name']} (Lead #{l['id']})", "description": f"Customer: {l['customer_name']} | Status: {l['status']}"} for idx, l in enumerate(cands)]
                reply = f"I found **{len(cands)}** matching leads. Which one do you mean?\n\n" + "\n".join([f"🔹 **{o['title']}**\n   {o['description']}" for o in options])
                return {"state": "CLARIFICATION_REQUIRED", "reply": reply, "requires_clarification": True, "options": options, "actions_taken": actions_taken}
            elif lead_res.get("found"):
                l = lead_res["lead"]
                state["last_selected_lead"] = l
                state["pending_action"] = {
                    "action_type": "ASSIGN_LEAD",
                    "lead_id": l["id"],
                    "lead_title": l.get("lead_name") or f"Lead for {l['customer_name']}",
                    "salesperson_name": sp_name
                }
                return {
                    "state": "CONFIRMATION_REQUIRED",
                    "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to assign lead **{l.get('lead_name') or l['customer_name']}** (#{l['id']}) to salesperson **{sp_name}**.\n\nWould you like me to proceed?",
                    "requires_confirmation": True,
                    "options": [
                        {"id": "confirm", "title": "✅ Confirm & Assign"},
                        {"id": "cancel", "title": "❌ Cancel Action"}
                    ],
                    "actions_taken": actions_taken
                }
            else:
                return {"state": "ANSWER", "reply": f"Could not find lead matching **'{query_str}'** in the CRM database.", "actions_taken": actions_taken}

        cust_res = tools.resolve_customer(query_str=query_str)
        actions_taken.append({"tool_name": "resolve_customer", "args": {"query_str": query_str}, "result": cust_res})

        if cust_res.get("ambiguous"):
            cands = cust_res["candidates"]
            state["last_candidates"] = cands
            state["pending_request"] = {"intent": intent, "plan": plan, "user_message": user_message}
            options = [{"id": c["id"], "title": f"Option {idx+1}: {c['name']} ({c['company']})", "description": f"{c['location']} | Industry: {c['industry']}"} for idx, c in enumerate(cands)]
            reply = f"I found **{len(cands)}** customers matching your request. Which one do you mean?\n\n" + "\n".join([f"🔹 **{o['title']}**\n   {o['description']}" for o in options])
            return {"state": "CLARIFICATION_REQUIRED", "reply": reply, "requires_clarification": True, "options": options, "actions_taken": actions_taken}
        elif cust_res.get("found"):
            c = cust_res["customer"]
            state["last_selected_customer"] = c
            state["last_selected_entity"] = c
            deals_res = tools.search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
            deals = deals_res.get("records", [])
            if deals:
                d = deals[0]
                state["last_selected_deal"] = d
                state["pending_action"] = {
                    "action_type": "ASSIGN_DEAL",
                    "deal_id": d["id"],
                    "deal_title": d["title"],
                    "salesperson_name": sp_name
                }
                return {
                    "state": "CONFIRMATION_REQUIRED",
                    "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to assign deal **{d['title']}** (#{d['id']}) to salesperson **{sp_name}**.\n\nWould you like me to proceed?",
                    "requires_confirmation": True,
                    "options": [
                        {"id": "confirm", "title": "✅ Confirm & Assign"},
                        {"id": "cancel", "title": "❌ Cancel Action"}
                    ],
                    "actions_taken": actions_taken
                }

    if intent == "UPDATE_DEAL_STATUS":
        query_str = None
        if plan.get("filters"):
            for f in plan["filters"]:
                if f.get("field") in ("name", "customer_name", "customer", "query") and f.get("value"):
                    query_str = f["value"]
                    break
        if not query_str:
            query_str = plan.get("search_query") or user_message

        target_status = (plan.get("action_details") or {}).get("new_status") or "Won"
        state["pending_intent"] = {"action": "UPDATE_DEAL_STATUS", "target_status": target_status}

        # 1. First check if customer resolution is ambiguous (e.g. 2 Rahuls)
        cust_res = tools.resolve_customer(query_str=query_str)
        actions_taken.append({"tool_name": "resolve_customer", "args": {"query_str": query_str}, "result": cust_res})

        if cust_res.get("ambiguous"):
            cands = cust_res["candidates"]
            state["last_candidates"] = cands
            state["pending_request"] = {"intent": intent, "plan": plan, "user_message": user_message}
            options = [{"id": c["id"], "title": f"Option {idx+1}: {c['name']} ({c['company']})", "description": f"{c['location']} | Industry: {c['industry']}"} for idx, c in enumerate(cands)]
            reply = f"I found **{len(cands)}** customers matching your request. Which one do you mean?\n\n" + "\n".join([f"🔹 **{o['title']}**\n   {o['description']}" for o in options])
            return {"state": "CLARIFICATION_REQUIRED", "reply": reply, "requires_clarification": True, "options": options, "actions_taken": actions_taken}

        # 2. Check deal resolution
        deal_res = tools.resolve_deal(query_str=query_str)
        actions_taken.append({"tool_name": "resolve_deal", "args": {"query_str": query_str}, "result": deal_res})

        if deal_res.get("ambiguous"):
            cands = deal_res["candidates"]
            state["last_candidates"] = cands
            state["pending_request"] = {"intent": intent, "plan": plan, "user_message": user_message}
            options = [{"id": d["id"], "title": f"Option {idx+1}: {d['title']} ({d['customer_name']})", "description": f"Value: ₹{int(d['value']):,} | Status: {d['status']}"} for idx, d in enumerate(cands)]
            reply = f"I found **{len(cands)}** deals matching your request. Which one do you mean?\n\n" + "\n".join([f"🔹 **{o['title']}**\n   {o['description']}" for o in options])
            return {"state": "CLARIFICATION_REQUIRED", "reply": reply, "requires_clarification": True, "options": options, "actions_taken": actions_taken}

        if deal_res.get("found"):
            d = deal_res["deal"]
            state["last_selected_deal"] = d
            state["pending_action"] = {
                "action_type": "UPDATE_DEAL_STATUS",
                "deal_id": d["id"],
                "deal_title": d["title"],
                "new_status": target_status,
                "customer_name": d.get("customer_name") or "Customer"
            }
            return {
                "state": "CONFIRMATION_REQUIRED",
                "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to update deal stage:\n- **Deal**: {d['title']} (#{d['id']})\n- **Customer**: {d.get('customer_name')} ({d.get('customer_company', '')})\n- **Value**: ₹{int(d['value']):,}\n- **Current Status**: {d['status']}\n- **New Target Status**: **{target_status}**\n\nWould you like me to proceed?",
                "requires_confirmation": True,
                "options": [
                    {"id": "confirm", "title": "✅ Confirm & Execute Update"},
                    {"id": "cancel", "title": "❌ Cancel Action"}
                ],
                "actions_taken": actions_taken
            }

        if cust_res.get("found"):
            c = cust_res["customer"]
            state["last_selected_customer"] = c
            state["last_selected_entity"] = c
            deals_res = tools.search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
            deals = deals_res.get("records", [])
            if deals:
                d = deals[0]
                state["last_selected_deal"] = d
                state["pending_action"] = {
                    "action_type": "UPDATE_DEAL_STATUS",
                    "deal_id": d["id"],
                    "deal_title": d["title"],
                    "new_status": target_status,
                    "customer_name": c["name"]
                }
                return {
                    "state": "CONFIRMATION_REQUIRED",
                    "reply": f"⚠️ **Confirmation Required**:\n\nYou asked to update deal stage:\n- **Deal**: {d['title']} (#{d['id']})\n- **Customer**: {c['name']} ({c['company']})\n- **Value**: ₹{int(d['value']):,}\n- **Current Status**: {d['status']}\n- **New Target Status**: **{target_status}**\n\nWould you like me to proceed?",
                    "requires_confirmation": True,
                    "options": [
                        {"id": "confirm", "title": "✅ Confirm & Execute Update"},
                        {"id": "cancel", "title": "❌ Cancel Action"}
                    ],
                    "actions_taken": actions_taken
                }

    # 5. COUNT Intent
    if intent == "COUNT":
        entity = plan.get("entity") or "customers"
        filters = plan.get("filters") or []
        res = tools.count_records(entity, filters)
        actions_taken.append({"tool_name": "count_records", "args": {"entity": entity, "filters": filters}, "result": res})
        cnt = res.get("count", 0)

        filt_parts = [f"{f['field']} = '{f['value']}'" for f in filters]
        f_str = f" matching ({', '.join(filt_parts)})" if filt_parts else ""
        return {"state": "ANSWER", "reply": f"There are currently **{cnt}** {entity}{f_str} in the CRM.", "actions_taken": actions_taken}

    # 6. LIST Intent
    if intent == "LIST":
        entity = plan.get("entity") or "customers"
        filters = plan.get("filters") or []
        sort = plan.get("sort")
        limit = plan.get("limit") or 10

        query_str = plan.get("search_query") or user_message
        if is_customer_reference(query_str) and state.get("last_selected_customer"):
            c = state["last_selected_customer"]
            deals_res = tools.search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
            recs = deals_res.get("records", [])
            state["last_deal_candidates"] = recs
            reply = f"Found **{len(recs)}** deal(s) for **{c['name']}** ({c['company']}):\n\n" + "\n".join([f"- **{d['title']}** — Value: ₹{int(d['value']):,}, Status: `{d['status']}`" for d in recs])
            return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

        res = tools.search_records(entity, filters, sort=sort, limit=limit)
        actions_taken.append({"tool_name": "search_records", "args": {"entity": entity, "filters": filters}, "result": res})
        recs = res.get("records", [])

        if not recs:
            filt_parts = [f"{f['field']} = '{f['value']}'" for f in filters]
            f_str = f" matching ({', '.join(filt_parts)})" if filt_parts else ""
            return {"state": "ANSWER", "reply": f"No {entity}{f_str} were found in the CRM.", "actions_taken": actions_taken}

        if entity == "customers":
            reply = f"Found **{len(recs)}** customer(s):\n\n" + "\n".join([f"- **{c['name']}** ({c['company']}) — {c['location']} | {c['industry']} | Active Deals: {c.get('active_deals', 0)}" for c in recs])
        elif entity == "leads":
            reply = f"Found **{len(recs)}** lead(s):\n\n" + "\n".join([f"- **{l['customer_name']}** ({l['customer_company']}) — Status: `{l['status']}`, Score: `{l['lead_score']}`, Value: ₹{int(l['expected_value']):,}" for l in recs])
        elif entity == "deals":
            reply = f"Found **{len(recs)}** deal(s):\n\n" + "\n".join([f"- **{d['title']}** (#{d['id']}) — Customer: **{d['customer_name']}**, Value: ₹{int(d['value']):,}, Status: `{d['status']}`" for d in recs])
        else:
            reply = f"Found **{len(recs)}** record(s) in {entity}."

        return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

    # 7. DETAIL Intent
    if intent == "DETAIL":
        if any(w in msg_low for w in ["list ", "show ", "display ", "get all", "find all", "which ", "who belongs", "belong to"]):
            res = tools.search_records(plan.get("entity") or "customers", plan.get("filters") or [])
            actions_taken.append({"tool_name": "search_records", "args": {"entity": "customers", "filters": plan.get("filters") or []}, "result": res})
            recs = res.get("records", [])
            reply = f"Found **{len(recs)}** customer(s):\n\n" + "\n".join([f"- **{c['name']}** ({c['company']}) — {c['location']} | {c['industry']} | Active Deals: {c.get('active_deals', 0)}" for c in recs])
            return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

        query_str = plan.get("search_query") or user_message
        attr = plan.get("attribute") or "details"

        target_cust = None
        if is_customer_reference(query_str) and state.get("last_selected_customer"):
            target_cust = state["last_selected_customer"]
        else:
            cust_res = tools.resolve_customer(query_str=query_str)
            actions_taken.append({"tool_name": "resolve_customer", "args": {"query_str": query_str}, "result": cust_res})
            if cust_res.get("found") and not cust_res.get("ambiguous"):
                target_cust = cust_res["customer"]
                state["last_selected_customer"] = target_cust
                state["last_selected_entity"] = target_cust
                state["last_entity_type"] = "customer"
                state["last_entity_id"] = target_cust["id"]
                state["last_entity_name"] = target_cust["name"]
            elif cust_res.get("ambiguous"):
                cands = cust_res["candidates"]
                state["last_candidates"] = cands
                state["pending_request"] = {"intent": intent, "plan": plan, "user_message": user_message}
                options = [{"id": c["id"], "title": f"Option {idx+1}: {c['name']} ({c['company']})", "description": f"{c['location']} | {c['email']} | {c['phone']}"} for idx, c in enumerate(cands)]
                reply = f"I found **{len(cands)}** matching customers. Which one do you mean?\n\n" + "\n".join([f"🔹 **{o['title']}**\n   {o['description']}" for o in options])
                return {"state": "CLARIFICATION_REQUIRED", "reply": reply, "requires_clarification": True, "options": options, "actions_taken": actions_taken}

        if not target_cust and plan.get("filters"):
            filter_res = tools.search_records("customers", filters=plan["filters"])
            recs = filter_res.get("records", [])
            if len(recs) == 1:
                target_cust = recs[0]
                state["last_selected_customer"] = target_cust
                state["last_selected_entity"] = target_cust
                state["last_entity_type"] = "customer"
                state["last_entity_id"] = target_cust["id"]
                state["last_entity_name"] = target_cust["name"]
            elif len(recs) > 1:
                state["last_candidates"] = recs
                state["pending_request"] = {"intent": intent, "plan": plan, "user_message": user_message}
                options = [{"id": c["id"], "title": f"Option {idx+1}: {c['name']} ({c['company']})", "description": f"{c['location']} | {c['email']}"} for idx, c in enumerate(recs)]
                reply = f"I found **{len(recs)}** customers matching your criteria. Which one do you mean?\n\n" + "\n".join([f"🔹 **{o['title']}**\n   {o['description']}" for o in options])
                return {"state": "CLARIFICATION_REQUIRED", "reply": reply, "requires_clarification": True, "options": options, "actions_taken": actions_taken}

        if target_cust:
            c = target_cust
            if attr == "email":
                reply = f"**{c['name']}**'s email at **{c['company']}** is **{c['email']}**."
            elif attr in ("phone", "contact"):
                reply = f"**{c['name']}** at **{c['company']}** can be reached at **{c['phone']}**."
            elif attr in ("company", "organization", "work"):
                reply = f"**{c['name']}** is associated with **{c['company']}**."
            elif attr in ("location", "city"):
                reply = f"**{c['name']}** at **{c['company']}** is located in **{c['location']}**."
            elif attr in ("industry", "sector"):
                reply = f"**{c['name']}** operates in the **{c['industry']}** industry."
            elif attr == "status":
                deals_res = tools.search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
                deals = deals_res.get("records", [])
                leads_res = tools.search_records("leads", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
                leads = leads_res.get("records", [])
                if deals:
                    if len(deals) == 1:
                        reply = f"**{c['name']}**'s current deal stage for **{deals[0]['title']}** is **{deals[0]['status']}**."
                    else:
                        deal_st_parts = [f"- **{d['title']}**: `{d['status']}` (₹{int(d['value']):,})" for d in deals]
                        reply = f"**{c['name']}** ({c['company']}) has **{len(deals)}** deal(s) in the pipeline:\n\n" + "\n".join(deal_st_parts)
                elif leads:
                    reply = f"**{c['name']}**'s lead status is **{leads[0]['status']}**."
                else:
                    reply = f"**{c['name']}** has no active deal or lead status in the CRM."
            else:
                reply = f"Customer Details for **{c['name']}**:\n- **Company**: {c['company']}\n- **Email**: {c['email']}\n- **Phone**: {c['phone']}\n- **Location**: {c['location']}\n- **Industry**: {c['industry']}\n- **Active Deals**: {c.get('active_deals', 0)}"
            return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

        # Check Employee
        emp_res = tools.resolve_employee(query_str=query_str)
        if emp_res.get("found"):
            sp = emp_res["salesperson"]
            return {"state": "ANSWER", "reply": f"**{sp['name']}**'s email address is **{sp['email']}**.", "actions_taken": actions_taken}

        return {"state": "NO_MATCH", "reply": "❌ **No Match Found**: I couldn't find a customer or contact matching your search in the CRM database.", "actions_taken": actions_taken}

    # CUSTOMER_360 Intent
    if intent == "CUSTOMER_360":
        query_str = plan.get("search_query") or user_message
        target_cust = None
        if is_customer_reference(query_str) and state.get("last_selected_customer"):
            target_cust = state["last_selected_customer"]
        else:
            cust_res = tools.resolve_customer(query_str=query_str)
            actions_taken.append({"tool_name": "resolve_customer", "args": {"query_str": query_str}, "result": cust_res})
            if cust_res.get("found") and not cust_res.get("ambiguous"):
                target_cust = cust_res["customer"]
                state["last_selected_customer"] = target_cust
                state["last_selected_entity"] = target_cust
                state["last_entity_type"] = "customer"
                state["last_entity_id"] = target_cust["id"]
                state["last_entity_name"] = target_cust["name"]
            elif cust_res.get("ambiguous"):
                cands = cust_res["candidates"]
                state["last_candidates"] = cands
                state["pending_request"] = {"intent": intent, "plan": plan, "user_message": user_message}
                options = [{"id": c["id"], "title": f"Option {idx+1}: {c['name']} ({c['company']})", "description": f"{c['location']} | {c['email']}"} for idx, c in enumerate(cands)]
                reply = f"I found **{len(cands)}** matching customers. Which one do you mean?\n\n" + "\n".join([f"🔹 **{o['title']}**\n   {o['description']}" for o in options])
                return {"state": "CLARIFICATION_REQUIRED", "reply": reply, "requires_clarification": True, "options": options, "actions_taken": actions_taken}

        if target_cust:
            c360 = crm_service.get_customer_360(target_cust["id"])
            if c360:
                cust = c360["customer"]
                deals = c360.get("deals", [])
                leads = c360.get("leads", [])
                notes = c360.get("notes", [])
                interactions = c360.get("interactions", [])
                
                deal_summary = "\n".join([f"  - **{d['title']}** (#{d['id']}): Stage `{d['status']}`, Value ₹{int(d['value']):,}" for d in deals]) if deals else "  - No active deals"
                lead_summary = "\n".join([f"  - Lead Status `{l['status']}`, Score `{l['lead_score']}`, Value ₹{int(l['expected_value']):,}" for l in leads]) if leads else "  - No lead records"
                
                reply = f"### 📊 Customer 360 Profile: **{cust['name']}**\n\n" \
                        f"- **Company**: {cust['company']}\n" \
                        f"- **Location**: {cust['location']}\n" \
                        f"- **Industry**: {cust['industry']}\n" \
                        f"- **Email**: {cust['email']}\n" \
                        f"- **Phone**: {cust['phone']}\n\n" \
                        f"**Deals ({len(deals)})**:\n{deal_summary}\n\n" \
                        f"**Leads ({len(leads)})**:\n{lead_summary}\n\n" \
                        f"**Activity Timeline**: {len(interactions)} interaction(s), {len(notes)} note(s)\n" \
                        f"**AI Insight**: {c360.get('ai_insights', {}).get('summary', '')}"
                return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

    # 8. AGGREGATE Intent (Analytical Queries)
    if intent == "AGGREGATE":
        entity = plan.get("entity") or "deals"
        agg = plan.get("aggregation") or {"agg_function": "SUM", "agg_field": "value"}
        filters = plan.get("filters") or []
        sort = plan.get("sort")
        limit = plan.get("limit") or 5

        query_str = plan.get("search_query") or user_message
        if query_str:
            cust_res = tools.resolve_customer(query_str=query_str)
            if cust_res.get("found") and not cust_res.get("ambiguous"):
                target_cid = cust_res["customer"]["id"]
                if not any(f.get("field") == "customer_id" for f in filters):
                    filters.append({"field": "customer_id", "operator": "equals", "value": target_cid})

        res = tools.aggregate_records(entity, agg_function=agg.get("agg_function", "SUM"), agg_field=agg.get("agg_field", "value"), group_by=agg.get("group_by"), filters=filters, sort=sort, limit=limit)
        actions_taken.append({"tool_name": "aggregate_records", "args": plan, "result": res})

        results = res.get("results", [])
        if results and not agg.get("group_by"):
            val = results[0].get("aggregate_value") or 0
            if val == 0 and any(f.get("field") == "status" for f in filters):
                fallback_filters = [f for f in filters if f.get("field") != "status"]
                res = tools.aggregate_records(entity, agg_function=agg.get("agg_function", "SUM"), agg_field=agg.get("agg_field", "value"), group_by=agg.get("group_by"), filters=fallback_filters, sort=sort, limit=limit)
                results = res.get("results", [])
        if not results:
            return {"state": "ANSWER", "reply": "No records were found to perform aggregation.", "actions_taken": actions_taken}

        if agg.get("group_by"):
            top = results[0]
            grp_name = top.get("group_name") or top.get("group_id") or "N/A"
            val = top.get("aggregate_value") or 0
            if agg.get("agg_function") == "SUM":
                reply = f"**{grp_name}** has the largest value with **₹{int(val):,}**."
            else:
                unit = "deal(s)" if entity == "deals" else "record(s)"
                reply = f"**{grp_name}** leads with **{int(val)}** {unit}."
        else:
            val = results[0].get("aggregate_value") or 0
            fn_str = agg.get("agg_function", "SUM")
            if fn_str in ("SUM", "AVG", "MIN", "MAX"):
                reply = f"The {fn_str.lower()} deal value for the requested criteria is **₹{int(val):,}**."
            else:
                reply = f"The count is **{val}**."

        return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

    # 9. RELATED & HISTORY Intent (Relationships, Interactions & Customer History Summarization)
    if intent in ("RELATED", "HISTORY"):
        # Check if user asks for current chat session conversation summary
        if any(ph in msg_low for ph in ["chat history", "conversation history", "chat session", "my conversation", "my chat", "session history"]):
            chat_msgs = crm_service.get_chat_messages(session_id)
            if chat_msgs:
                formatted_msgs = []
                for m in chat_msgs:
                    r_title = "User" if m["role"] == "user" else "Copilot"
                    formatted_msgs.append(f"- **{r_title}**: {m['content']}")
                reply = f"### 💬 Summary of Chat Session (`{session_id}`):\n\n" + "\n".join(formatted_msgs)
                return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

        # Clean query string to extract explicit customer target name
        clean_q = re.sub(r'\b(summarize|summary|my|conversation|chat|history|with|for|details|about|customer)\b', '', user_message, flags=re.IGNORECASE).strip()
        query_str = clean_q if clean_q else (plan.get("search_query") or user_message)
        rel_ent = plan.get("related_entity") or ("interactions" if intent == "HISTORY" else "deals")

        target_cust = None
        if not clean_q and is_customer_reference(query_str) and state.get("last_selected_customer"):
            target_cust = state["last_selected_customer"]
        else:
            cust_res = tools.resolve_customer(query_str=query_str)
            actions_taken.append({"tool_name": "resolve_customer", "args": {"query_str": query_str}, "result": cust_res})
            if cust_res.get("found") and not cust_res.get("ambiguous"):
                target_cust = cust_res["customer"]
                state["last_selected_customer"] = target_cust
                state["last_selected_entity"] = target_cust
                state["last_entity_type"] = "customer"
                state["last_entity_id"] = target_cust["id"]
                state["last_entity_name"] = target_cust["name"]
            elif cust_res.get("ambiguous"):
                cands = cust_res["candidates"]
                state["last_candidates"] = cands
                state["pending_request"] = {"intent": intent, "plan": plan, "user_message": user_message}
                options = [{"id": c["id"], "title": f"Option {idx+1}: {c['name']} ({c['company']})", "description": f"{c['location']} | {c['email']}"} for idx, c in enumerate(cands)]
                reply = f"I found **{len(cands)}** matching customers for your history request. Which one do you mean?\n\n" + "\n".join([f"🔹 **{o['title']}**\n   {o['description']}" for o in options])
                return {"state": "CLARIFICATION_REQUIRED", "reply": reply, "requires_clarification": True, "options": options, "actions_taken": actions_taken}

        if target_cust:
            c = target_cust
            if intent == "HISTORY" or "summarize" in msg_low or "history" in msg_low:
                summary_res = crm_service.get_customer_history_summary(c["id"])
                return {"state": "ANSWER", "reply": summary_res["summary"], "actions_taken": actions_taken}

            elif rel_ent == "interactions":
                hist = tools.get_record_history("customers", c["id"])
                t_lines = hist.get("timeline", [])
                if t_lines:
                    latest = t_lines[0]
                    reply = f"Latest activity for **{c['name']}** ({c['company']}) on **{latest['date']}**:\n- **{latest['title']}**: {latest['details']} (by {latest['by']})"
                else:
                    reply = f"No recent activity found for **{c['name']}** ({c['company']})."
                return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

            elif rel_ent == "deals":
                deals_res = tools.search_records("deals", filters=[{"field": "customer_id", "operator": "equals", "value": c["id"]}])
                deals = deals_res.get("records", [])
                state["last_deal_candidates"] = deals
                reply = f"Found **{len(deals)}** deal(s) for **{c['name']}** ({c['company']}):\n\n" + "\n".join([f"- **{d['title']}** — Value: ₹{int(d['value']):,}, Status: `{d['status']}`" for d in deals])
                return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

    # 10. AT_RISK Intent
    if intent == "AT_RISK":
        filters = plan.get("filters") or []
        if filters:
            res = tools.search_records("deals", filters=filters)
            recs = res.get("records", [])
            reply = f"Found **{len(recs)}** deal(s) matching criteria:\n\n" + "\n".join([f"- **{d['title']}** (#{d['id']}) — Customer: **{d['customer_name']}**, Value: ₹{int(d['value']):,}, Status: `{d['status']}`" for d in recs])
            return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}
        else:
            res = tools.get_at_risk_deals(days_threshold=14)
            deals = res.get("at_risk_deals", [])
            reply = f"Found **{len(deals)}** stale deals requiring attention (no updates in >14 days):\n\n" + "\n".join([f"- **{d['title']}** — Value: ₹{int(d['value']):,}, Owner: {d['owner_name']}, Stale: `{d['days_stale']} days`" for d in deals])
            return {"state": "ANSWER", "reply": reply, "actions_taken": actions_taken}

    # General Fallback Response
    cust_res = tools.resolve_customer(query_str=user_message)
    if cust_res.get("found") and not cust_res.get("ambiguous"):
        c = cust_res["customer"]
        state["last_selected_customer"] = c
        state["last_selected_entity"] = c
        return {"state": "ANSWER", "reply": f"Found customer **{c['name']}** ({c['company']}) from {c['location']} ({c['industry']}) with **{c['active_deals']}** active deal(s).", "actions_taken": actions_taken}

    return {"state": "ANSWER", "reply": "I'm your SmartCRM AI Copilot. You can ask me to count records, filter customers by industry or location, summarize interaction history, or update deal stages safely.", "actions_taken": actions_taken}

def run_agent_turn(
    user_message: str,
    conversation_history: List[Dict[str, Any]] = None,
    session_id: str = "default_session",
    context_type: Optional[str] = None,
    context_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    candidate_index: Optional[int] = None,
    action: Optional[str] = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    res = run_agent_engine(
        user_message,
        conversation_history=conversation_history,
        session_id=session_id,
        context_type=context_type,
        context_id=context_id,
        candidate_id=candidate_id,
        candidate_index=candidate_index,
        action=action
    )
    return res, res.get("actions_taken", [])

def generate_response_with_hf_llm(user_message: str, engine_result: Dict[str, Any]) -> Optional[str]:
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    if not hf_token:
        return None
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(api_key=hf_token)
        
        reply_draft = engine_result.get("reply", "")
        actions = engine_result.get("actions_taken", [])
        
        prompt = f"""You are the intelligent CRM AI Copilot. 
Your job is to generate the final natural language answer for the user based on the user query and the retrieved CRM database facts/action results below.

User Query: "{user_message}"
Retrieved CRM Fact / Outcome Draft:
{reply_draft}

Tool Execution Logs:
{json.dumps(actions, indent=2, default=str)}

Rules:
1. Provide a concise, clear, and professional response directly answering the user query.
2. If summarization is requested, provide a single, clean narrative paragraph summarizing the key actions or history.
3. Keep exact numbers, currency symbols (₹), and customer/deal details accurate as provided in the facts.
4. Do NOT output raw markdown headers like '###' or orphan '**' symbols that break text rendering.
5. Respond directly as the CRM Copilot without meta-commentary."""

        response = client.chat_completion(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512
        )
        txt = response.choices[0].message.content.strip()
        if txt:
            return txt
    except Exception as err:
        print(f"[DEBUG_LOG] HF Final Answer LLM Generation error: {type(err).__name__} - {str(err)}")
    return None

def run_agent_engine(
    user_message: str,
    conversation_history: List[Dict[str, Any]] = None,
    session_id: str = "default_session",
    context_type: Optional[str] = None,
    context_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    candidate_index: Optional[int] = None,
    action: Optional[str] = None
) -> Dict[str, Any]:
    res = _run_agent_engine_inner(
        user_message,
        session_id=session_id,
        context_type=context_type,
        context_id=context_id,
        candidate_id=candidate_id,
        candidate_index=candidate_index,
        action=action
    )
    
    # Use Hugging Face API key to generate the final natural language response
    if res.get("state") in ("ANSWER", "ACTION_SUCCESS") and not res.get("requires_confirmation") and not res.get("requires_clarification"):
        hf_reply = generate_response_with_hf_llm(user_message, res)
        if hf_reply:
            print(f"[DEBUG] HF_RESPONSE_GENERATOR_USED=True, MODEL='Qwen2.5-72B-Instruct'")
            res["reply"] = hf_reply

    st = get_session_state(session_id)
    crm_service.update_chat_session_context(session_id, st)
    return res
