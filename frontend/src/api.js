const BASE_URL = typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000/api"
    : "/api";

export async function fetchOverview() {
    const res = await fetch(`${BASE_URL}/overview`);
    if (!res.ok) throw new Error("Failed to fetch overview data");
    return res.json();
}

export async function fetchCustomers(search = "", industry = "All", location = "All", page = 1) {
    const params = new URLSearchParams({ search, industry, location, page: page.toString(), page_size: "20" });
    const res = await fetch(`${BASE_URL}/customers?${params}`);
    if (!res.ok) throw new Error("Failed to fetch customers");
    return res.json();
}

export async function fetchCustomerDetail(id) {
    const res = await fetch(`${BASE_URL}/customers/${id}`);
    if (!res.ok) throw new Error("Failed to fetch customer 360 profile");
    return res.json();
}

export async function fetchLeads(search = "", status = "All", assigned_to = "All", page = 1) {
    const params = new URLSearchParams({ search, status, assigned_to, page: page.toString(), page_size: "20" });
    const res = await fetch(`${BASE_URL}/leads?${params}`);
    if (!res.ok) throw new Error("Failed to fetch leads");
    return res.json();
}

export async function fetchDeals(search = "", status = "All", owner_name = "All", industry = "All", page = 1) {
    const params = new URLSearchParams({ search, status, owner_name, industry, page: page.toString(), page_size: "20" });
    const res = await fetch(`${BASE_URL}/deals?${params}`);
    if (!res.ok) throw new Error("Failed to fetch deals");
    return res.json();
}

export async function updateDealStatus(dealId, newStatus) {
    const res = await fetch(`${BASE_URL}/deals/${dealId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update deal status");
    }
    return res.json();
}

export async function assignDeal(dealId, salespersonName) {
    const res = await fetch(`${BASE_URL}/deals/${dealId}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ salesperson_name: salespersonName })
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to assign deal");
    }
    return res.json();
}

export async function fetchAtRiskDeals(daysThreshold = 14, page = 1) {
    const params = new URLSearchParams({ days_threshold: daysThreshold.toString(), page: page.toString(), page_size: "20" });
    const res = await fetch(`${BASE_URL}/at-risk-deals?${params}`);
    if (!res.ok) throw new Error("Failed to fetch at-risk deals");
    return res.json();
}

export async function fetchAuditLogs(page = 1) {
    const params = new URLSearchParams({ page: page.toString(), page_size: "25" });
    const res = await fetch(`${BASE_URL}/audit-logs?${params}`);
    if (!res.ok) throw new Error("Failed to fetch audit logs");
    return res.json();
}

export async function fetchFilterOptions() {
    const res = await fetch(`${BASE_URL}/filters/options`);
    if (!res.ok) throw new Error("Failed to fetch filter options");
    return res.json();
}

export async function sendAiChat(message, sessionId, contextType = null, contextId = null, candidateId = null, candidateIndex = null, action = null) {
    const res = await fetch(`${BASE_URL}/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message,
            session_id: sessionId,
            context_type: contextType,
            context_id: contextId,
            candidate_id: candidateId,
            candidate_index: candidateIndex,
            action: action
        })
    });
    if (!res.ok) throw new Error("Failed to communicate with AI Copilot");
    return res.json();
}

export async function fetchConversations() {
    const res = await fetch(`${BASE_URL}/ai/conversations`);
    if (!res.ok) throw new Error("Failed to fetch conversation history");
    return res.json();
}

export async function fetchChatMessages(sessionId) {
    const res = await fetch(`${BASE_URL}/ai/conversations/${sessionId}`);
    if (!res.ok) throw new Error("Failed to fetch conversation messages");
    return res.json();
}

export async function deleteConversation(sessionId) {
    const res = await fetch(`${BASE_URL}/ai/conversations/${sessionId}`, {
        method: "DELETE"
    });
    if (!res.ok) throw new Error("Failed to delete conversation");
    return res.json();
}

export async function createNote(customerId, content, dealId = null) {
    const res = await fetch(`${BASE_URL}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: customerId, content, deal_id: dealId })
    });
    if (!res.ok) throw new Error("Failed to save note");
    return res.json();
}
