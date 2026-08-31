import os
from dotenv import load_dotenv

load_dotenv()
DETECTION_THRESHOLD = float(os.getenv("DETECTION_THRESHOLD", "3.0"))

# Assume a global baseline for simplicity unless calculated dynamically.
# For our generator, base failure rate is ~10%.
BASELINE_FAILURE_RATE = 0.10

class SpikeDetector:
    def __init__(self, threshold_multiplier=DETECTION_THRESHOLD, window_size=20):
        self.threshold_multiplier = threshold_multiplier
        self.window_size = window_size
        self.segment_windows = {}

    def detect(self, events):
        """
        Takes a chronological list of events.
        Returns a list of flagged events that were part of a spike.
        """
        flagged_events = []
        
        for event in events:
            segment = (event["bank"], event["payment_method"])
            
            if segment not in self.segment_windows:
                self.segment_windows[segment] = []
                
            window = self.segment_windows[segment]
            window.append(event)
            
            # keep only the last `window_size` events
            if len(window) > self.window_size:
                window.pop(0)
                
            # Need at least a minimal number of events in the window to detect a spike
            if len(window) >= 5:
                failed_count = sum(1 for e in window if e["status"] == "failed")
                total_attempts = len(window)
                current_failure_rate = failed_count / total_attempts
                
                # Check for spike
                if current_failure_rate >= self.threshold_multiplier * BASELINE_FAILURE_RATE:
                    # Flag this event if it is a failed event
                    if event["status"] == "failed":
                        # To avoid modifying the original dict directly (optional)
                        flagged_event = dict(event)
                        flagged_event["detection_reason"] = (
                            f"Spike detected for segment {segment}. "
                            f"Current rate: {current_failure_rate:.1%} >= Threshold: {self.threshold_multiplier * BASELINE_FAILURE_RATE:.1%}"
                        )
                        flagged_event["confidence"] = min(1.0, current_failure_rate)
                        flagged_events.append(flagged_event)
                        
        return flagged_events

def run_detector(events):
    detector = SpikeDetector()
    return detector.detect(events)

if __name__ == "__main__":
    import json
    with open("data/events.json") as f:
        events = json.load(f)
    flagged = run_detector(events)
    print(f"Total events: {len(events)}")
    print(f"Flagged events: {len(flagged)}")
