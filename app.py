import streamlit as st
import requests
import json
import uuid
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

# Import centralized CRM Service Layer (Single Source of Truth)
import crm_service

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="SmartCRM AI — Enterprise CRM Workspace",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global Custom CSS for Clean SaaS Light Theme, Compact Padding, and Search Bar Styling
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">

<style>
    /* Global Base */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    .stApp {
        background-color: #F7F8FC !important;
        color: #0F172A !important;
    }

    /* Remove Large Blank Space Above Content */
    .main .block-container {
        padding-top: 1.0rem !important;
        padding-bottom: 2rem !important;
        margin-top: 0 !important;
    }

    /* Sidebar Styling (Compact Dark Navy #111827) */
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
        background-color: #111827 !important;
        border-right: 1px solid #1F2937 !important;
        width: 240px !important;
    }

    /* Hide default radio elements */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        display: none !important;
    }

    /* Sidebar Navigation Button Pills */
    .stSidebar button {
        background-color: transparent !important;
        color: #9CA3AF !important;
        border: none !important;
        border-radius: 8px !important;
        text-align: left !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 9px 12px !important;
        width: 100% !important;
        margin-bottom: 2px !important;
        transition: all 0.15s ease-in-out !important;
    }
    .stSidebar button:hover {
        background-color: #1F2937 !important;
        color: #FFFFFF !important;
    }

    .active-nav-btn button {
        background-color: #4F46E5 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 4px rgba(79, 70, 229, 0.25) !important;
    }

    /* Compact Sidebar Header */
    .brand-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 4px 4px 14px 4px;
        border-bottom: 1px solid #1F2937;
        margin-bottom: 12px;
    }
    .brand-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.25rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.1;
    }
    .brand-subtitle {
        font-size: 0.7rem;
        color: #818CF8;
        font-weight: 600;
    }

    /* Modern Visually Obvious Search Box Styling */
    .stTextInput > div > div > input {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        height: 42px !important;
        padding: 0 14px !important;
        font-size: 0.9rem !important;
        color: #0F172A !important;
        font-weight: 500 !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4F46E5 !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15) !important;
    }

    /* Cards */
    .white-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        margin-bottom: 14px;
    }
    
    /* Interactive KPI Cards */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 14px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        text-align: left;
    }
    .kpi-header {
        font-size: 0.78rem;
        font-weight: 600;
        color: #64748B;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .kpi-value {
        font-family: 'Outfit', sans-serif;
        font-size: 1.45rem;
        font-weight: 800;
        color: #0F172A;
        margin: 4px 0 2px 0;
        white-space: nowrap;
    }
    .kpi-trend {
        font-size: 0.72rem;
        font-weight: 600;
        color: #10B981;
    }

    .section-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "🏠 Overview"

if "active_session_id" not in st.session_state:
    st.session_state["active_session_id"] = str(uuid.uuid4())

if "page_num" not in st.session_state:
    st.session_state["page_num"] = 1

if "show_ai_drawer" not in st.session_state:
    st.session_state["show_ai_drawer"] = False

# Navigation Items (10 Distinct Options)
NAV_ITEMS = [
    ("🏠 Overview", "🏠 Overview"),
    ("🤖 AI Assistant", "🤖 AI Assistant"),
    ("👥 Customers", "👥 Customers"),
    ("🎯 Leads", "🎯 Leads"),
    ("💰 Deals", "💰 Deals"),
    ("📞 Interactions", "📞 Interactions"),
    ("📝 Notes", "📝 Notes"),
    ("⚠️ At-Risk Deals", "⚠️ At-Risk Deals"),
    ("📊 Analytics", "📊 Analytics"),
    ("📜 Audit & Activity", "📜 Audit & Activity")
]

# Sidebar Menu (Button Pills)
with st.sidebar:
    st.markdown("""
    <div class="brand-header">
        <div style="font-size: 1.6rem; color: #6366F1;">⚡</div>
        <div>
            <div class="brand-title">SmartCRM AI</div>
            <div class="brand-subtitle">Enterprise CRM Workspace</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for label, page_key in NAV_ITEMS:
        is_active = (st.session_state["current_page"] == page_key)
        if is_active:
            st.markdown('<div class="active-nav-btn">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{page_key}"):
                st.session_state["current_page"] = page_key
                st.session_state["page_num"] = 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            if st.button(label, key=f"nav_{page_key}"):
                st.session_state["current_page"] = page_key
                st.session_state["page_num"] = 1
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background: #1F2937; border: 1px solid #374151; border-radius: 8px; padding: 10px; text-align: center;">
        <div style="font-size: 1.0rem;">👑</div>
        <div style="font-weight: 700; color: #FFFFFF; font-size: 0.8rem; margin-top: 2px;">SQLite Ground Truth</div>
        <div style="font-size: 0.7rem; color: #818CF8;">Live DB Engine</div>
    </div>
    """, unsafe_allow_html=True)

# Top Bar Header (Neutral CRM User)
current_p = st.session_state["current_page"]

header_col, user_col = st.columns([3, 1])
with header_col:
    st.markdown(f"""
    <div style="margin-bottom:8px;">
        <h1 style="font-family:'Outfit'; font-size:1.5rem; font-weight:800; color:#0F172A; margin:0;">{current_p}</h1>
        <div style="font-size:0.82rem; color:#64748B;">Real-time view of sales pipeline, customers, and AI copilot</div>
    </div>
    """, unsafe_allow_html=True)

with user_col:
    st.markdown("""
    <div style="display:flex; justify-content:flex-end; align-items:center; gap:12px; margin-top:2px;">
        <span style="font-size: 1.1rem; cursor:pointer;">🔔 <span style="background:#EF4444; color:white; font-size:0.65rem; padding:2px 6px; border-radius:10px; font-weight:bold;">Live</span></span>
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:34px; height:34px; border-radius:50%; background:#4F46E5; color:white; font-weight:bold; display:flex; align-items:center; justify-content:center; font-size:0.85rem;">CU</div>
            <div>
                <div style="font-weight:700; font-size:0.85rem; color:#0F172A;">CRM User</div>
                <div style="font-size:0.72rem; color:#64748B;">Sales Manager</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Helper: Render Floating AI Drawer Button & Drawer Panel (NO BLANK CONTAINER WHEN CLOSED)
def render_floating_ai_drawer(context_type: str = None, context_id: str = None):
    if current_p == "🤖 AI Assistant":
        return

    c_btn, _ = st.columns([1, 4])
    with c_btn:
        btn_label = "❌ Close AI Drawer" if st.session_state["show_ai_drawer"] else "⚡ Ask AI Copilot"
        if st.button(btn_label, key="toggle_ai_drawer", use_container_width=True):
            st.session_state["show_ai_drawer"] = not st.session_state["show_ai_drawer"]
            st.rerun()

    if st.session_state["show_ai_drawer"]:
        st.markdown("<div class='white-card' style='border:2px solid #6366F1; margin-top:8px;'>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:Outfit; font-size:1.05rem; font-weight:800; color:#4F46E5; margin-bottom:8px;'>⚡ AI Copilot Assistant {f'({context_type} ID: {context_id})' if context_id else ''}</div>", unsafe_allow_html=True)

        messages = crm_service.get_chat_messages(st.session_state["active_session_id"])
        for msg in messages:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

        user_input = st.chat_input("Ask AI copilot...")
        if user_input:
            resp = requests.post(f"{API_BASE_URL}/chat", json={
                "message": user_input,
                "session_id": st.session_state["active_session_id"],
                "context_type": context_type,
                "context_id": context_id
            })
            if resp.status_code == 200:
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# Helper: Pagination UI Component
def render_pagination(total_records: int, total_pages: int, current_page_num: int, start_rec: int, end_rec: int, page_key: str):
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
    with c1:
        st.caption(f"Showing **{start_rec}–{end_rec}** of **{total_records}** records")
    with c2:
        if st.button("← Previous", key=f"prev_{page_key}", disabled=(current_page_num <= 1), use_container_width=True):
            st.session_state["page_num"] = current_page_num - 1
            st.rerun()
    with c3:
        if st.button("Next →", key=f"next_{page_key}", disabled=(current_page_num >= total_pages), use_container_width=True):
            st.session_state["page_num"] = current_page_num + 1
            st.rerun()
    with c4:
        st.caption(f"Page **{current_page_num}** of **{total_pages}**")


# ==========================================
# PAGE 1: OVERVIEW DASHBOARD
# ==========================================
def render_overview():
    render_floating_ai_drawer()
    kpis = crm_service.get_overview_kpis()
    
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.markdown(f"<div class='kpi-card'><div class='kpi-header'>👥 Customers</div><div class='kpi-value'>{kpis['total_customers']}</div><div class='kpi-trend'>↑ Live SQLite</div></div>", unsafe_allow_html=True)
        if st.button("Customers →", key="btn_kpi_cust", use_container_width=True):
            st.session_state["current_page"] = "👥 Customers"
            st.session_state["page_num"] = 1
            st.rerun()

    with k2:
        st.markdown(f"<div class='kpi-card'><div class='kpi-header'>🎯 Total Leads</div><div class='kpi-value'>{kpis['total_leads']}</div><div class='kpi-trend'>↑ Live SQLite</div></div>", unsafe_allow_html=True)
        if st.button("Leads →", key="btn_kpi_leads", use_container_width=True):
            st.session_state["current_page"] = "🎯 Leads"
            st.session_state["page_num"] = 1
            st.rerun()

    with k3:
        st.markdown(f"<div class='kpi-card'><div class='kpi-header'>🤝 Active Deals</div><div class='kpi-value'>{kpis['active_deals']}</div><div class='kpi-trend'>↑ Live SQLite</div></div>", unsafe_allow_html=True)
        if st.button("Deals →", key="btn_kpi_deals", use_container_width=True):
            st.session_state["current_page"] = "💰 Deals"
            st.session_state["page_num"] = 1
            st.rerun()

    with k4:
        pipe_fmt = f"₹{kpis['pipeline_value']:,.0f}"
        st.markdown(f"<div class='kpi-card'><div class='kpi-header'>💰 Pipeline</div><div class='kpi-value'>{pipe_fmt}</div><div class='kpi-trend'>↑ Active</div></div>", unsafe_allow_html=True)
        if st.button("Analytics →", key="btn_kpi_pipe", use_container_width=True):
            st.session_state["current_page"] = "📊 Analytics"
            st.rerun()

    with k5:
        won_fmt = f"₹{kpis['won_revenue']:,.0f}"
        st.markdown(f"<div class='kpi-card'><div class='kpi-header'>🏆 Won Revenue</div><div class='kpi-value'>{won_fmt}</div><div class='kpi-trend'>↑ Closed</div></div>", unsafe_allow_html=True)
        if st.button("Won Deals →", key="btn_kpi_won", use_container_width=True):
            st.session_state["current_page"] = "💰 Deals"
            st.session_state["page_num"] = 1
            st.rerun()

    with k6:
        st.markdown(f"<div class='kpi-card'><div class='kpi-header'>⚠️ At-Risk</div><div class='kpi-value' style='color:#EF4444;'>{kpis['at_risk_count']}</div><div class='kpi-trend' style='color:#EF4444;'>Action Needed</div></div>", unsafe_allow_html=True)
        if st.button("Risk BI →", key="btn_kpi_risk", use_container_width=True):
            st.session_state["current_page"] = "⚠️ At-Risk Deals"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # CHARTS GRID
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='white-card'><div class='section-title'>Sales Pipeline Stage Distribution</div>", unsafe_allow_html=True)
        df_status = pd.DataFrame(crm_service.get_pipeline_by_status())
        if not df_status.empty:
            fig_status = px.bar(
                df_status, x='status', y='count', color='status', text='count',
                color_discrete_sequence=["#4F46E5", "#818CF8", "#F59E0B", "#06B6D4", "#10B981", "#EF4444"]
            )
            fig_status.update_layout(height=210, showlegend=False, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_status, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='white-card'><div class='section-title'>Lead Conversion Pipeline</div>", unsafe_allow_html=True)
        df_leads = pd.DataFrame(crm_service.get_leads_by_status())
        if not df_leads.empty:
            fig_leads = px.pie(
                df_leads, values='count', names='status', hole=0.55,
                color_discrete_sequence=["#4F46E5", "#818CF8", "#F59E0B", "#06B6D4", "#10B981", "#EF4444"]
            )
            fig_leads.update_layout(height=210, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_leads, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # DEALS REQUIRING ATTENTION TABLE
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>⚠️ Deals Requiring Immediate Sales Follow-Up</div>", unsafe_allow_html=True)
    at_risk_list = crm_service.get_at_risk_deals_data(days_threshold=14)
    if at_risk_list:
        df_risk = pd.DataFrame(at_risk_list)[['title', 'customer_name', 'value', 'status', 'days_stale', 'suggested_next_action']]
        df_risk['value'] = df_risk['value'].apply(lambda v: f"₹{v:,.0f}")
        df_risk.columns = ['Deal Title', 'Customer', 'Value', 'Status', 'Days Stale', 'Recommended Next Action']
        st.dataframe(df_risk, use_container_width=True, hide_index=True)
    else:
        st.success("No at-risk deals currently flagged.")
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 2: DEDICATED AI ASSISTANT & CHAT HISTORY
# ==========================================
def render_ai_assistant():
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("### 🤖 Dedicated AI Assistant Workspace")
    
    col_hist, col_chat = st.columns([1.1, 2.9], gap="medium")
    
    with col_hist:
        st.markdown("#### Conversation History")
        if st.button("➕ New Chat Session", key="btn_new_chat", use_container_width=True):
            st.session_state["active_session_id"] = str(uuid.uuid4())
            st.rerun()

        sessions = crm_service.get_chat_sessions()
        if sessions:
            for s in sessions:
                title_lbl = f"💬 {s['title'][:22]}..."
                is_active = (s["id"] == st.session_state["active_session_id"])
                if is_active:
                    st.markdown(f"**👉 {s['title'][:25]}**")
                else:
                    if st.button(title_lbl, key=f"sess_{s['id']}", use_container_width=True):
                        st.session_state["active_session_id"] = s["id"]
                        st.rerun()
        else:
            st.caption("No saved conversations yet.")

    with col_chat:
        st.markdown("#### Interactive Chat Workspace")
        messages = crm_service.get_chat_messages(st.session_state["active_session_id"])
        if not messages:
            st.info("👋 Ask natural language queries or command the AI assistant to inspect or mutate database records!")
        
        for msg in messages:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

        user_input = st.chat_input("Ask a question or issue a CRM command...")
        if user_input:
            resp = requests.post(f"{API_BASE_URL}/chat", json={
                "message": user_input,
                "session_id": st.session_state["active_session_id"]
            })
            if resp.status_code == 200:
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 3: CUSTOMERS DIRECTORY (PAGINATED & DYNAMIC FILTERS)
# ==========================================
def render_customers():
    render_floating_ai_drawer(context_type="Customer")
    
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("### 👥 Customer Directory")
    st.caption("Manage and understand customer relationships")

    # Dynamic Filter Lists from SQLite
    dyn_industries = ["All"] + crm_service.get_distinct_industries()
    dyn_locations = ["All"] + crm_service.get_distinct_locations()
    dyn_types = ["All"] + crm_service.get_distinct_customer_types()

    # Search Bar & Toolbar Filters
    search_term = st.text_input("Search", "", placeholder="🔍 Search customers, companies, emails or phone...", key="cust_search")
    
    f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
    with f1:
        ind_filter = st.selectbox("Industry", dyn_industries, key="cust_ind")
    with f2:
        loc_filter = st.selectbox("Location", dyn_locations, key="cust_loc")
    with f3:
        type_filter = st.selectbox("Customer Type", dyn_types, key="cust_type")
    with f4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear Filters", key="cust_clear", use_container_width=True):
            st.session_state["page_num"] = 1
            st.rerun()

    # Paginated Query
    res = crm_service.get_paginated_customers(
        search=search_term, industry=ind_filter, location=loc_filter,
        page=st.session_state["page_num"], page_size=10
    )

    df_cust = pd.DataFrame(res["items"])
    if not df_cust.empty:
        # Hide raw tech database IDs from main table display
        df_display = df_cust[['name', 'company', 'industry', 'location', 'email', 'phone', 'customer_type', 'active_deals', 'total_deal_value']].copy()
        df_display['total_deal_value'] = df_display['total_deal_value'].apply(lambda v: f"₹{v:,.0f}")
        df_display.columns = ['Customer Name', 'Company', 'Industry', 'Location', 'Email', 'Phone', 'Type', 'Active Deals', 'Total Value']
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        render_pagination(res["total_records"], res["total_pages"], res["current_page"], res["start_record"], res["end_record"], "cust")

        st.markdown("---")
        st.markdown("#### 🏢 Customer 360° Profile Inspector")
        # Format select options cleanly without exposing raw IDs as primary title
        cust_choices = {f"{r['name']} ({r['company']})": r['id'] for _, r in df_cust.iterrows()}
        selected_label = st.selectbox("Select Customer to Inspect", list(cust_choices.keys()), key="select_cust_360")
        
        if selected_label:
            selected_id = cust_choices[selected_label]
            c360 = crm_service.get_customer_360(selected_id)
            if c360:
                cust = c360["customer"]
                st.markdown(f"### {cust['name']} — {cust['company']}")
                st.write(f"**Email**: {cust['email']} | **Phone**: {cust['phone']} | **Industry**: {cust['industry']} | **Location**: {cust['location']} | **Account Type**: {cust['customer_type']}")
                
                col_deals, col_notes = st.columns(2)
                with col_deals:
                    st.markdown("##### Active Deals")
                    df_c_deals = pd.DataFrame(c360["deals"])
                    if not df_c_deals.empty:
                        df_c_deals_clean = df_c_deals[['title', 'value', 'status', 'probability', 'expected_close']].copy()
                        df_c_deals_clean['value'] = df_c_deals_clean['value'].apply(lambda v: f"₹{v:,.0f}")
                        df_c_deals_clean.columns = ['Deal Title', 'Value', 'Status', 'Prob (%)', 'Expected Close']
                        st.dataframe(df_c_deals_clean, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No active deals.")

                with col_notes:
                    st.markdown("##### Interaction & Notes History")
                    df_c_notes = pd.DataFrame(c360["notes"])
                    if not df_c_notes.empty:
                        df_c_notes_clean = df_c_notes[['created_at', 'content']].copy()
                        df_c_notes_clean.columns = ['Date', 'Note Content']
                        st.dataframe(df_c_notes_clean, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No notes recorded.")
    else:
        st.info("No matching customers found.")

    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 4: LEADS MANAGEMENT (PAGINATED & DYNAMIC FILTERS)
# ==========================================
def render_leads():
    render_floating_ai_drawer(context_type="Lead")
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("### 🎯 Lead Workspace")
    st.caption("Track and convert sales leads")

    dyn_salespeople = ["All"] + crm_service.get_distinct_salespeople()

    search_lead = st.text_input("Search Lead", "", placeholder="🔍 Search by customer or company...", key="lead_search")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st_filter = st.selectbox("Lead Status", ["All", "New", "Contacted", "Qualified", "Proposal", "Won", "Lost"], key="lead_st")
    with col2:
        sp_filter = st.selectbox("Assigned To", dyn_salespeople, key="lead_sp")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear Filters", key="lead_clear", use_container_width=True):
            st.session_state["page_num"] = 1
            st.rerun()

    res = crm_service.get_paginated_leads(search=search_lead, status=st_filter, assigned_to=sp_filter, page=st.session_state["page_num"], page_size=10)
    df_leads = pd.DataFrame(res["items"])
    if not df_leads.empty:
        df_display = df_leads[['customer_name', 'customer_company', 'source', 'status', 'lead_score', 'expected_value', 'assigned_to_name', 'created_at']].copy()
        df_display['expected_value'] = df_display['expected_value'].apply(lambda v: f"₹{v:,.0f}")
        df_display.columns = ['Customer Name', 'Company', 'Lead Source', 'Status', 'Lead Score', 'Expected Value', 'Assigned To', 'Created Date']
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        render_pagination(res["total_records"], res["total_pages"], res["current_page"], res["start_record"], res["end_record"], "leads")
    else:
        st.info("No matching leads found.")

    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 5: DEALS WORKSPACE (PAGINATED & DYNAMIC FILTERS)
# ==========================================
def render_deals():
    render_floating_ai_drawer(context_type="Deal")
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("### 💰 Deal Workspace & Pipeline Management")
    st.caption("Track your sales pipeline and deal activity")

    dyn_owners = ["All"] + crm_service.get_distinct_salespeople()
    dyn_industries = ["All"] + crm_service.get_distinct_industries()

    d_search = st.text_input("Search Deals", "", placeholder="🔍 Search deal title, customer, or company...", key="deal_search")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        d_status = st.selectbox("Stage", ["All", "New", "Contacted", "Qualified", "Proposal", "Won", "Lost"], key="deal_st")
    with col2:
        d_owner = st.selectbox("Salesperson", dyn_owners, key="deal_owner")
    with col3:
        d_ind = st.selectbox("Industry", dyn_industries, key="deal_ind")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear Filters", key="deal_clear", use_container_width=True):
            st.session_state["page_num"] = 1
            st.rerun()

    res = crm_service.get_paginated_deals(search=d_search, status=d_status, owner_name=d_owner, industry=d_ind, page=st.session_state["page_num"], page_size=10)
    df_deals = pd.DataFrame(res["items"])
    if not df_deals.empty:
        df_display = df_deals[['title', 'customer_name', 'value', 'status', 'probability', 'owner_name', 'expected_close', 'risk']].copy()
        df_display['value'] = df_display['value'].apply(lambda v: f"₹{v:,.0f}")
        df_display.columns = ['Deal Title', 'Customer', 'Value', 'Status', 'Prob (%)', 'Salesperson', 'Expected Close', 'Risk Status']
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        render_pagination(res["total_records"], res["total_pages"], res["current_page"], res["start_record"], res["end_record"], "deals")

        st.markdown("---")
        st.markdown("#### ⚡ Deal Quick Actions")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            deal_map = {f"{r['title']} ({r['customer_name']})": r['id'] for _, r in df_deals.iterrows()}
            selected_deal_label = st.selectbox("Select Deal", list(deal_map.keys()), key="deal_act_lbl")
        with col_b:
            new_st = st.selectbox("Update Status Stage", ["New", "Contacted", "Qualified", "Proposal", "Won", "Lost"], key="deal_act_st")
        with col_c:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Commit Status Change", use_container_width=True, key="btn_commit_deal"):
                target_deal_id = deal_map[selected_deal_label]
                res_act = crm_service.update_deal_status_service(target_deal_id, new_st, performed_by="user_ui")
                st.success(res_act["message"])
                st.rerun()
    else:
        st.info("No matching deals found.")

    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 6: INTERACTIONS LOG (PAGINATED)
# ==========================================
def render_interactions():
    render_floating_ai_drawer()
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("### 📞 Interaction History")
    st.caption("Logs of calls, meetings, emails, and demos")

    type_f = st.selectbox("Interaction Type", ["All", "Call", "Email", "Meeting", "Demo"], key="int_type")
    res = crm_service.get_paginated_interactions(type_filter=type_f, page=st.session_state["page_num"], page_size=10)
    df_int = pd.DataFrame(res["items"])
    if not df_int.empty:
        df_display = df_int[['created_at', 'customer_name', 'deal_title', 'type', 'subject', 'summary', 'created_by_name']].copy()
        df_display.columns = ['Date', 'Customer', 'Associated Deal', 'Type', 'Subject', 'Summary', 'Recorded By']
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        render_pagination(res["total_records"], res["total_pages"], res["current_page"], res["start_record"], res["end_record"], "int")
    else:
        st.info("No interaction records logged.")
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 7: NOTES MANAGER (PAGINATED)
# ==========================================
def render_notes():
    render_floating_ai_drawer()
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("### 📝 Customer & Deal Notes")
    
    with st.expander("➕ Add New Note", expanded=False):
        cust_rows = crm_service.get_all_customers()
        cust_options = {f"{c['name']} ({c['company']})": c['id'] for c in cust_rows}
        selected_cust_label = st.selectbox("Select Customer", list(cust_options.keys()), key="note_cust_sel")
        note_text = st.text_area("Note Content", key="note_text")
        if st.button("Save Note", key="btn_save_note"):
            if selected_cust_label and note_text:
                cid = cust_options[selected_cust_label]
                res = crm_service.add_note_service(cid, note_text, performed_by="user_ui")
                st.success(res["message"])
                st.rerun()
            else:
                st.error("Please enter note content.")

    res = crm_service.get_paginated_notes(page=st.session_state["page_num"], page_size=10)
    df_notes = pd.DataFrame(res["items"])
    if not df_notes.empty:
        df_display = df_notes[['created_at', 'customer_name', 'deal_title', 'author_name', 'content']].copy()
        df_display.columns = ['Date', 'Customer', 'Associated Deal', 'Author', 'Content']
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        render_pagination(res["total_records"], res["total_pages"], res["current_page"], res["start_record"], res["end_record"], "notes")
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 8: AT-RISK DEALS BI PAGE
# ==========================================
def render_at_risk():
    render_floating_ai_drawer()
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("### ⚠️ At-Risk Deals BI Workspace")
    thresh = st.slider("Inactivity Threshold (Days Stale)", min_value=1, max_value=60, value=14, key="risk_thresh")
    at_risk = crm_service.get_at_risk_deals_data(days_threshold=thresh)
    st.warning(f"Found {len(at_risk)} deal(s) with no update activity for at least {thresh} days.")
    if at_risk:
        df_risk = pd.DataFrame(at_risk)[['title', 'customer_name', 'value', 'status', 'days_stale', 'suggested_next_action']].copy()
        df_risk['value'] = df_risk['value'].apply(lambda v: f"₹{v:,.0f}")
        df_risk.columns = ['Deal Title', 'Customer', 'Value', 'Status', 'Days Stale', 'Recommended Next Action']
        st.dataframe(df_risk, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 9: EXECUTIVE ANALYTICS WORKSPACE
# ==========================================
def render_analytics():
    render_floating_ai_drawer()
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("### 📊 Executive Analytics & Pipeline Metrics")
    kpis = crm_service.get_overview_kpis()
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Active Pipeline", f"₹{kpis['pipeline_value']:,.0f}")
    with m2:
        st.metric("Total Won Revenue", f"₹{kpis['won_revenue']:,.0f}")
    with m3:
        st.metric("Total Lost Revenue", f"₹{kpis['lost_revenue']:,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Monthly Deal Creation Velocity")
        df_trend = pd.DataFrame(crm_service.get_monthly_deal_trend())
        if not df_trend.empty:
            fig_tr = px.line(df_trend, x='month', y='deal_count', markers=True)
            st.plotly_chart(fig_tr, use_container_width=True)
    with c2:
        st.markdown("#### Salesperson Pipeline Volume")
        df_sp = pd.DataFrame(crm_service.get_pipeline_by_salesperson())
        if not df_sp.empty:
            fig_sp = px.bar(df_sp, x='salesperson', y='total_value')
            st.plotly_chart(fig_sp, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 10: AUDIT & ACTIVITY LOG (PAGINATED)
# ==========================================
def render_audit():
    render_floating_ai_drawer()
    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("### 📜 System Audit & Mutation Activity Log")
    st.caption("Complete trace of manual and AI-driven database modifications")
    res = crm_service.get_paginated_audit_logs(page=st.session_state["page_num"], page_size=15)
    df_logs = pd.DataFrame(res["items"])
    if not df_logs.empty:
        df_display = df_logs[['timestamp', 'performed_by', 'action_type', 'target_table', 'before_value', 'after_value']].copy()
        df_display.columns = ['Timestamp', 'Performed By', 'Action Type', 'Target Table', 'Previous Value', 'New Updated Value']
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        render_pagination(res["total_records"], res["total_pages"], res["current_page"], res["start_record"], res["end_record"], "audit")
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE ROUTER EXECUTION
# ==========================================
PAGE_ROUTER = {
    "🏠 Overview": render_overview,
    "🤖 AI Assistant": render_ai_assistant,
    "👥 Customers": render_customers,
    "🎯 Leads": render_leads,
    "💰 Deals": render_deals,
    "📞 Interactions": render_interactions,
    "📝 Notes": render_notes,
    "⚠️ At-Risk Deals": render_at_risk,
    "📊 Analytics": render_analytics,
    "📜 Audit & Activity": render_audit
}

if current_p in PAGE_ROUTER:
    PAGE_ROUTER[current_p]()
else:
    render_overview()
