import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Main.settings')
django.setup()

from DashBoard.views import SendRentReminderEmailView
import threading

def trigger_email():
    print("Triggering email for MEM002...")
    
    # We can just manually call the inner function used in SendRentReminderEmailView
    # But since it's nested inside post(), let's extract it or recreate the logic quickly.
    
    from DashBoard.views import http_session
    from django.core.mail import EmailMessage
    from django.conf import settings
    
    DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
    member_id = "MEM002"
    
    res = http_session.get(f"{DATABASE_URL}/members/{member_id}.json", timeout=5)
    if res.status_code != 200 or not res.json():
        print(f"Error: Member {member_id} not found.")
        return
        
    member_data = res.json()
    email = member_data.get("email", member_data.get("email_id"))
    name = member_data.get("name", "Member")
    rent_amt = member_data.get("monthly_rent", "0")
    
    if not email:
        print(f"Error: No email found for member {member_id}.")
        return

    title = "Action Required: Rent Payment Due Today"
    description = "This is an automated reminder that your monthly rent is due today."
    checkout_url = f"https://tinderbox-bouncing-superbowl.ngrok-free.dev/checkout?member_id={member_id}"

    body = f"Dear {name},\n\n"
    body += f"{description}\n\n"
    body += f"Monthly Rent Amount: ₹{rent_amt}\n\n"
    body += f"To make your payment securely online, please click the link below:\n{checkout_url}\n\n"
    body += "If you have already made the payment, please ignore this email.\n\n"
    body += "Best regards,\nPgAdmin Management"

    sender_email = settings.EMAIL_HOST_USER
    email_msg = EmailMessage(
        subject=title,
        body=body,
        from_email=sender_email, 
        to=[email],
    )
    
    email_msg.send(fail_silently=False)
    print(f"Success: Reminder email sent to {email}")

if __name__ == "__main__":
    trigger_email()
