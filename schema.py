from typing import Dict, Any, List, Tuple, Optional

CRM_SCHEMA: Dict[str, Dict[str, Any]] = {
    "customers": {
        "fields": ["id", "name", "company", "industry", "location", "customer_type", "email", "phone", "created_at"],
        "field_types": {
            "id": "string",
            "name": "string",
            "company": "string",
            "industry": "string",
            "location": "string",
            "customer_type": "string",
            "email": "string",
            "phone": "string",
            "created_at": "date"
        },
        "allowed_filters": ["id", "name", "company", "industry", "location", "customer_type", "email", "phone", "created_at", "updated_at"],
        "relationships": {
            "deals": {"foreign_key": "customer_id", "target_table": "deals"},
            "leads": {"foreign_key": "customer_id", "target_table": "leads"},
            "interactions": {"foreign_key": "customer_id", "target_table": "interactions"},
            "notes": {"foreign_key": "customer_id", "target_table": "notes"}
        }
    },
    "leads": {
        "fields": ["id", "customer_id", "lead_name", "source", "status", "lead_score", "expected_value", "assigned_to", "created_at", "updated_at"],
        "field_types": {
            "id": "string",
            "customer_id": "string",
            "lead_name": "string",
            "source": "string",
            "status": "string",
            "lead_score": "integer",
            "expected_value": "float",
            "assigned_to": "string",
            "created_at": "date",
            "updated_at": "date"
        },
        "allowed_filters": ["id", "customer_id", "lead_name", "name", "source", "status", "lead_score", "expected_value", "assigned_to", "customer_name", "customer_company", "assigned_to_name", "created_at", "updated_at"],
        "relationships": {
            "customer": {"foreign_key": "customer_id", "target_table": "customers"},
            "salesperson": {"foreign_key": "assigned_to", "target_table": "salespeople"}
        }
    },
    "deals": {
        "fields": ["id", "customer_id", "title", "value", "status", "probability", "owner_id", "expected_close", "created_at", "updated_at"],
        "field_types": {
            "id": "string",
            "customer_id": "string",
            "title": "string",
            "value": "float",
            "status": "string",
            "probability": "float",
            "owner_id": "string",
            "expected_close": "date",
            "created_at": "date",
            "updated_at": "date"
        },
        "allowed_filters": ["id", "customer_id", "title", "value", "status", "probability", "owner_id", "expected_close", "customer_name", "customer_company", "industry", "location", "owner_name", "created_at", "updated_at"],
        "relationships": {
            "customer": {"foreign_key": "customer_id", "target_table": "customers"},
            "salesperson": {"foreign_key": "owner_id", "target_table": "salespeople"},
            "interactions": {"foreign_key": "deal_id", "target_table": "interactions"},
            "notes": {"foreign_key": "deal_id", "target_table": "notes"}
        }
    },
    "interactions": {
        "fields": ["id", "customer_id", "deal_id", "type", "subject", "summary", "created_by", "created_at"],
        "field_types": {
            "id": "string",
            "customer_id": "string",
            "deal_id": "string",
            "type": "string",
            "subject": "string",
            "summary": "string",
            "created_by": "string",
            "created_at": "date"
        },
        "allowed_filters": ["id", "customer_id", "deal_id", "type", "subject", "created_by", "customer_name", "created_by_name", "created_at"],
        "relationships": {
            "customer": {"foreign_key": "customer_id", "target_table": "customers"},
            "deal": {"foreign_key": "deal_id", "target_table": "deals"},
            "salesperson": {"foreign_key": "created_by", "target_table": "salespeople"}
        }
    },
    "notes": {
        "fields": ["id", "customer_id", "deal_id", "author_id", "content", "created_at"],
        "field_types": {
            "id": "string",
            "customer_id": "string",
            "deal_id": "string",
            "author_id": "string",
            "content": "string",
            "created_at": "date"
        },
        "allowed_filters": ["id", "customer_id", "deal_id", "author_id", "customer_name", "author_name", "created_at"],
        "relationships": {
            "customer": {"foreign_key": "customer_id", "target_table": "customers"},
            "deal": {"foreign_key": "deal_id", "target_table": "deals"},
            "salesperson": {"foreign_key": "author_id", "target_table": "salespeople"}
        }
    },
    "salespeople": {
        "fields": ["id", "name", "email"],
        "field_types": {
            "id": "string",
            "name": "string",
            "email": "string"
        },
        "allowed_filters": ["id", "name", "email"],
        "relationships": {
            "deals": {"foreign_key": "owner_id", "target_table": "deals"},
            "leads": {"foreign_key": "assigned_to", "target_table": "leads"}
        }
    }
}

UNSUPPORTED_FIELDS = [
    "annual_revenue", "revenue", "annual_turnover", "turnover", "happiness_score",
    "happiness", "mood", "satisfaction", "nps", "profit", "profit_margin"
]

UNSUPPORTED_OPERATIONS = [
    "send_email", "send_mail", "send_sms", "call_phone", "delete_customer", "drop_table"
]

def validate_query_plan(plan: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates the LLM-generated Query Plan against the CRM Schema Registry.
    Returns (is_valid, error_message or unsupported_reason).
    """
    intent = plan.get("intent")
    if intent in ("CONFIRM_ACTION", "CANCEL_ACTION", "SELECT_CANDIDATE", "AT_RISK", "GENERAL_HELP"):
        return True, None

    if intent == "UNSUPPORTED":
        return False, plan.get("unsupported_reason") or "This query or field is not supported in the CRM database."

    entity = plan.get("entity")
    if not entity or entity not in CRM_SCHEMA:
        return False, f"Unknown CRM entity '{entity}'. Valid entities are: {', '.join(CRM_SCHEMA.keys())}."

    schema_info = CRM_SCHEMA[entity]
    allowed_filters = set(schema_info["allowed_filters"])

    # Check filters for non-existent fields
    filters = plan.get("filters") or []
    for f in filters:
        field = f.get("field")
        if not field:
            continue
        field_low = field.lower().strip()
        if field_low in UNSUPPORTED_FIELDS:
            return False, f"I can't filter {entity} by '{field}' because that field is not available in the CRM database."

        if field_low not in allowed_filters:
            # Check if field exists in any CRM table
            all_known = set()
            for ent_data in CRM_SCHEMA.values():
                all_known.update(ent_data["allowed_filters"])
            if field_low not in all_known:
                return False, f"Field '{field}' does not exist in the CRM schema. Available fields for {entity} are: {', '.join(schema_info['fields'])}."

    # Check requested attribute
    attr = plan.get("attribute")
    if attr:
        attr_low = attr.lower().strip()
        if attr_low in UNSUPPORTED_FIELDS:
            return False, f"The attribute '{attr}' is not present in the CRM database."

    # Check aggregation field
    agg = plan.get("aggregation")
    if agg:
        agg_field = agg.get("agg_field")
        if agg_field and agg_field.lower() in UNSUPPORTED_FIELDS:
            return False, f"Cannot perform aggregation on '{agg_field}' because that field does not exist in the CRM database."

    return True, None
