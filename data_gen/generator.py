import json
import random
import datetime
from faker import Faker

fake = Faker()

# Probabilities for recoverability given a failure reason
RECOVERABILITY_PROBS = {
    "bank_timeout": 0.85,
    "gateway_outage": 0.90,
    "insufficient_funds": 0.70,
    "expired_card": 0.40,
    "wrong_otp": 0.60,
    "invalid_card": 0.05,
    "fraud_flagged": 0.05
}

BANKS = ["HDFC", "ICICI", "SBI", "Axis", "Kotak"]
PAYMENT_METHODS = ["card", "upi", "netbanking"]
CUSTOMER_SEGMENTS = ["new", "repeat", "loyal"]

def generate_events(n_events=250, seed=42, output_path="data/events.json"):
    random.seed(seed)
    Faker.seed(seed)
    
    events = []
    
    for i in range(1, n_events + 1):
        order_id = f"ord_{i:04d}"
        amount = random.randint(100, 5000) * 100 # amount in paise, min 100 INR to 5000 INR
        customer_id = f"cust_{random.randint(1, 1000):03d}"
        payment_method = random.choice(PAYMENT_METHODS)
        bank = random.choice(BANKS)
        customer_segment = random.choice(CUSTOMER_SEGMENTS)
        
        # Simulate base failure rate and spike
        # Let's say HDFC + card is our spike segment
        is_spike_segment = (bank == "HDFC" and payment_method == "card")
        
        # Base failure rate ~10%, spike failure rate ~40%
        failure_prob = 0.40 if is_spike_segment else 0.10
        
        status = "failed" if random.random() < failure_prob else "success"
        
        if status == "failed":
            failure_reason = random.choice(list(RECOVERABILITY_PROBS.keys()))
            recoverable_prob = RECOVERABILITY_PROBS[failure_reason]
            recoverable = random.random() < recoverable_prob
        else:
            failure_reason = None
            recoverable = None
            
        timestamp = (datetime.datetime.utcnow() - datetime.timedelta(minutes=random.randint(0, 60*24))).isoformat() + "Z"
        
        events.append({
            "order_id": order_id,
            "amount": amount,
            "customer_id": customer_id,
            "payment_method": payment_method,
            "bank": bank,
            "status": status,
            "failure_reason": failure_reason,
            "timestamp": timestamp,
            "customer_segment": customer_segment,
            "recoverable": recoverable
        })
    
    # Sort events by timestamp
    events.sort(key=lambda x: x['timestamp'])
    
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(events, f, indent=2)
        
    print(f"Generated {len(events)} events to {output_path}")

if __name__ == "__main__":
    generate_events()
