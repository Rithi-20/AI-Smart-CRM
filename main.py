import os
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import db
import crm_service
from agent import run_agent_turn

load_dotenv()

app = FastAPI(title="SmartCRM AI Enterprise API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    from seed_db import init_db
    from db import DB_PATH
    if not os.path.exists(DB_PATH):
        init_db(DB_PATH)

class ContextModel(BaseModel):
    page: Optional[str] = None
    customer_id: Optional[str] = None
    deal_id: Optional[str] = None
    lead_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[ContextModel] = None
    candidate_id: Optional[str] = None
    candidate_index: Optional[int] = None
    action: Optional[str] = None

class StatusUpdatePayload(BaseModel):
    status: str

class AssignPayload(BaseModel):
    salesperson_name: str

class NotePayload(BaseModel):
    customer_id: str
    content: str
    deal_id: Optional[str] = None

# ==========================================
# CRM REST API ENDPOINTS
# ==========================================

@app.get("/api/overview")
def get_overview():
    return {
        "kpis": crm_service.get_overview_kpis(),
        "pipeline_by_status": crm_service.get_pipeline_by_status(),
        "leads_by_status": crm_service.get_leads_by_status(),
        "pipeline_by_salesperson": crm_service.get_pipeline_by_salesperson(),
        "deals_requiring_attention": crm_service.get_at_risk_deals_data(days_threshold=14)
    }

@app.get("/api/customers")
def get_customers(
    search: str = "",
    industry: str = "All",
    location: str = "All",
    customer_type: str = "All",
    min_deals: int = Query(default=0, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    data = crm_service.get_paginated_customers(search=search, industry=industry, location=location, page=page, page_size=page_size)
    items = data.get("items", [])
    if customer_type != "All":
        items = [c for c in items if c.get("customer_type") == customer_type]
    if min_deals > 0:
        items = [c for c in items if c.get("active_deals", 0) >= min_deals]
    data["items"] = items
    data["total_records"] = len(items)
    return data

@app.get("/api/customers/{customer_id}")
def get_customer_detail(customer_id: str):
    profile = crm_service.get_customer_360(customer_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Customer not found")
    return profile

@app.get("/api/customers/{customer_id}/ai-summary")
def get_customer_ai_summary(customer_id: str):
    res = crm_service.get_customer_history_summary(customer_id)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

@app.get("/api/leads")
def get_leads(
    search: str = "",
    status: str = "All",
    assigned_to: str = "All",
    source: str = "All",
    min_score: int = Query(default=0, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    data = crm_service.get_paginated_leads(search=search, status=status, assigned_to=assigned_to, page=page, page_size=page_size)
    items = data.get("items", [])
    if source != "All":
        items = [l for l in items if l.get("source") == source]
    if min_score > 0:
        items = [l for l in items if (l.get("lead_score") or 0) >= min_score]
    data["items"] = items
    data["total_records"] = len(items)
    return data

@app.get("/api/deals")
def get_deals(
    search: str = "",
    status: str = "All",
    owner_name: str = "All",
    industry: str = "All",
    value_tier: str = "All",
    risk: str = "All",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    data = crm_service.get_paginated_deals(search=search, status=status, owner_name=owner_name, industry=industry, page=page, page_size=page_size)
    items = data.get("items", [])
    if risk != "All":
        items = [d for d in items if d.get("risk") == risk]
    if value_tier == "high":
        items = [d for d in items if (d.get("value") or 0) >= 50000]
    elif value_tier == "mid":
        items = [d for d in items if 20000 <= (d.get("value") or 0) < 50000]
    elif value_tier == "low":
        items = [d for d in items if (d.get("value") or 0) < 20000]
    data["items"] = items
    data["total_records"] = len(items)
    return data

@app.patch("/api/deals/{deal_id}/status")
def update_deal_status(deal_id: str, payload: StatusUpdatePayload):
    res = crm_service.update_deal_status_service(deal_id, payload.status, performed_by="react_ui")
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.post("/api/deals/{deal_id}/assign")
def assign_deal(deal_id: str, payload: AssignPayload):
    res = crm_service.assign_lead_service(deal_id, payload.salesperson_name, performed_by="react_ui")
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.get("/api/at-risk-deals")
def get_at_risk(
    days_threshold: int = Query(default=14, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    all_at_risk = crm_service.get_at_risk_deals_data(days_threshold=days_threshold)
    total = len(all_at_risk)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    items = all_at_risk[start_idx:start_idx + page_size]
    return {
        "items": items,
        "total_records": total,
        "total_pages": total_pages,
        "current_page": page,
        "days_threshold": days_threshold
    }

@app.get("/api/audit-logs")
def get_audit_logs_endpoint(
    action_type: str = "All",
    performed_by: str = "All",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100)
):
    data = crm_service.get_paginated_audit_logs(page=page, page_size=page_size)
    items = data.get("items", [])
    if action_type != "All":
        items = [log for log in items if log.get("action_type") == action_type]
    if performed_by != "All":
        items = [log for log in items if log.get("performed_by") == performed_by]
    data["items"] = items
    data["total_records"] = len(items)
    return data

@app.get("/api/filters/options")
def get_filter_options():
    return {
        "industries": crm_service.get_distinct_industries(),
        "locations": crm_service.get_distinct_locations(),
        "customer_types": crm_service.get_distinct_customer_types(),
        "salespeople": crm_service.get_distinct_salespeople(),
        "lead_sources": crm_service.get_distinct_lead_sources()
    }

# ==========================================
# MAIN AI AGENT COPILOT CHAT ENDPOINTS
# ==========================================

@app.post("/api/ai/chat")
@app.post("/chat")
@app.post("/api/chats/{session_id}/messages")
def chat_endpoint(request: ChatRequest, session_id: Optional[str] = None):
    sess_id = session_id or request.session_id or request.conversation_id or "default_session"
    ctx_type = request.context.page if request.context else None
    ctx_id = (request.context.customer_id or request.context.deal_id or request.context.lead_id) if request.context else None

    # Fetch history
    db_messages = crm_service.get_chat_messages(sess_id)
    history = [{"role": m["role"], "content": m["content"]} for m in db_messages]

    # Save user message FIRST
    crm_service.save_chat_message(sess_id, "user", request.message, context_type=ctx_type, context_id=ctx_id)

    # Run agent engine safely
    try:
        agent_res, actions_taken = run_agent_turn(
            user_message=request.message,
            conversation_history=history,
            session_id=sess_id,
            context_type=ctx_type,
            context_id=ctx_id,
            candidate_id=request.candidate_id,
            candidate_index=request.candidate_index,
            action=request.action
        )

        reply_text = agent_res.get("reply", "")
        state_str = agent_res.get("state", "ANSWER")
        req_clar = agent_res.get("requires_clarification", False)
        req_conf = agent_res.get("requires_confirmation", False)
        opts = agent_res.get("options", [])
    except Exception as err:
        reply_text = f"I'm sorry, I encountered an issue processing your request: {str(err)}"
        state_str = "ANSWER"
        req_clar = False
        req_conf = False
        opts = []
        actions_taken = []

    # Save assistant message
    crm_service.save_chat_message(sess_id, "assistant", reply_text, context_type=ctx_type, context_id=ctx_id)

    return {
        "conversation_id": sess_id,
        "session_id": sess_id,
        "reply": reply_text,
        "state": state_str,
        "requires_clarification": req_clar,
        "requires_confirmation": req_conf,
        "options": opts,
        "action": None,
        "actions_taken": actions_taken
    }

@app.get("/api/ai/conversations")
@app.get("/api/chats")
def get_conversations():
    return crm_service.get_chat_sessions()

@app.post("/api/ai/conversations")
@app.post("/api/chats")
def create_conversation(body: Dict[str, Any] = Body(default={})):
    sess_id = body.get("session_id") or f"sess_{os.urandom(4).hex()}"
    title = body.get("title") or "New Chat Session"
    crm_service.save_chat_message(sess_id, "assistant", "Hello! How can I assist your sales team today?", title=title)
    return {"id": sess_id, "session_id": sess_id, "title": title}

@app.get("/api/ai/conversations/{session_id}")
@app.get("/api/chats/{session_id}/messages")
def get_conversation_history(session_id: str):
    from agent import get_session_state
    # Restore context into memory
    get_session_state(session_id)
    return crm_service.get_chat_messages(session_id)

@app.delete("/api/ai/conversations/{session_id}")
@app.delete("/api/chats/{session_id}")
def delete_conversation(session_id: str):
    from agent import clear_session_state
    clear_session_state(session_id)
    crm_service.delete_chat_session(session_id)
    return {"success": True, "message": f"Chat session '{session_id}' deleted."}

frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")

if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="API route not found")
    
    dist_index = os.path.join(frontend_dist, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
        
    dev_index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(dev_index):
        return FileResponse(dev_index)
        
    return {"message": "SmartCRM AI API active."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
