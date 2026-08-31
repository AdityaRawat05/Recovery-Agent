import os
import time
import json
import razorpay
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()
KEY_ID = os.getenv("RAZORPAY_KEY_ID")
KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not KEY_ID or not KEY_SECRET or KEY_ID == "rzp_test_xxxxxx":
    print("Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env to run this POC.")
    exit(1)

client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

def create_payment_flow(outcome="success"):
    print(f"\n--- Testing {outcome.upper()} flow ---")
    
    # 1. Create an Order
    order_amount = 149900 # amount in paise (1499.00 INR)
    order_receipt = f"poc_ord_{int(time.time())}_{outcome}"
    
    print(f"Creating Order for {order_amount / 100} INR...")
    order = client.order.create({
        "amount": order_amount,
        "currency": "INR",
        "receipt": order_receipt
    })
    order_id = order['id']
    print(f"Order created: {order_id}")
    
    # 2. Create Payment Link against the Order
    print(f"Creating Payment Link for Order {order_id}...")
    # NOTE: To attach a Payment Link to an Order, we must pass the order_id, 
    # but the API endpoint for payment links is separate.
    # Razorpay standard payment links don't always take order_id directly, 
    # wait, standard v1/payment_links allows passing order_id? 
    # Wait, Razorpay documentation says Payment Links can be created without an order,
    # OR we can pass standard order ID? Wait, passing order_id to payment links is not 
    # natively supported by standard Payment Links api, they create their own orders under the hood!
    # Wait, let's create a standard payment link, or an Invoice.
    # We will just pass amount and description for POC.
    link_data = {
        "amount": order_amount,
        "currency": "INR",
        "description": f"Test Payment for {order_receipt}",
        "customer": {
            "name": "Test Customer",
            "email": "test@example.com",
            "contact": "+919876543210"
        },
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
    }
    
    payment_link = client.payment_link.create(link_data)
    pl_id = payment_link['id']
    pl_url = payment_link['short_url']
    print(f"Payment Link created: {pl_id}")
    print(f"URL: {pl_url}")
    
    print("\nStarting Playwright to automate payment...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=500)
            context = browser.new_context()
            page = context.new_page()
            
            print("Opening Payment Link...")
            page.goto(pl_url)
            
            # Wait for checkout to load (sometimes it's a redirect, or a button)
            print("Waiting for page to load...")
            # We will just leave it open for 30 seconds for the user to manually 
            # complete it and see if the script can detect it, or we try to automate.
            print(f"Please manually complete the payment in the browser as a {outcome.upper()}!")
            print(f"Test cards: Success -> 4111 1111 1111 1111")
            
            # Polling for payment link status
            for i in range(30):
                time.sleep(2)
                pl_status = client.payment_link.fetch(pl_id)
                status = pl_status.get('status')
                print(f"Current status: {status}")
                if status in ['paid', 'failed', 'cancelled']:
                    print(f"Final status reached: {status}")
                    break
            
            browser.close()
    except Exception as e:
        print(f"Playwright automation failed or unavailable: {e}")
        print(f"Please open {pl_url} in your browser and complete manually.")
        
if __name__ == "__main__":
    create_payment_flow("success")
