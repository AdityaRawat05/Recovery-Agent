# diagnoser/diagnoser.py

def diagnose(event):
    """
    Takes a flagged event and returns a diagnosis category.
    Possible categories: bank_issue, card_issue, funds_issue, fraud_blocked
    """
    failure_reason = event.get("failure_reason")
    
    # Mapping based on typical failure reasons
    mapping = {
        "bank_timeout": "bank_issue",
        "gateway_outage": "bank_issue",
        "insufficient_funds": "funds_issue",
        "expired_card": "card_issue",
        "wrong_otp": "card_issue",
        "invalid_card": "fraud_blocked",
        "fraud_flagged": "fraud_blocked"
    }
    
    # Default to bank_issue if reason is unknown, 
    # to be safe or explicitly handle unknown cases.
    diagnosis = mapping.get(failure_reason, "bank_issue")
    
    diagnosed_event = dict(event)
    diagnosed_event["diagnosis"] = diagnosis
    diagnosed_event["diagnosis_confidence"] = 1.0 # Rule-based determinism
    
    return diagnosed_event

def run_diagnoser(flagged_events):
    return [diagnose(e) for e in flagged_events]
