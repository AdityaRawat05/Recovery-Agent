# policy/policy_rules.py

GLOBAL_MAX_ATTEMPTS = 3
MIN_ORDER_VALUE_PAISE = 5000  # ₹50

# Policy mapping based on Security & Access rules
# diagnosis -> rule dictionary
POLICY_TABLE = {
    "bank_issue": {
        "allowed_action": "retry",
        "category_max_attempts": 2,
        "delay_minutes": 15,
        "escalate_on_cap": True
    },
    "funds_issue": {
        "allowed_action": "retry",
        "category_max_attempts": 3,
        "delay_minutes": 24 * 60,
        "escalate_on_cap": False
    },
    "card_issue": {
        "allowed_action": "nudge",
        "category_max_attempts": 2,
        "delay_minutes": 48 * 60,
        "escalate_on_cap": False
    },
    "fraud_blocked": {
        "allowed_action": "no_action",
        "category_max_attempts": 0,
        "delay_minutes": 0,
        "escalate_on_cap": True
    }
}
