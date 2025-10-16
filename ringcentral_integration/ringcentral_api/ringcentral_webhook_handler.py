import frappe
from frappe.utils import now_datetime
import json

# --- START EDIT: Import the actual connection logic from the new file ---
from .rc_client import connect_to_ringcentral 
# --- END EDIT ---

@frappe.whitelist(allow_guest=True)
def handle_call_webhook(call_data=None):
    """
    Receives and processes the webhook payload from RingCentral when a call is completed.
    
    The API must be configured with allow_guest=True since RingCentral calls it as an unauthenticated external service.
    """
    
    if frappe.request and frappe.request.method == 'POST':
        try:
            # 1. Get data from POST request body
            data = json.loads(frappe.request.data)
            
            # Extract key call details
            # NOTE: Update these lines to match the actual RingCentral webhook payload structure!
            event_id = data.get("uuid")
            event_type = data.get("event")
            
            # Assuming the webhook structure provides necessary call info
            call_info = data.get("body", {})
            from_number = call_info.get("from", {}).get("phoneNumber") or call_info.get("from", {}).get("extensionNumber")
            to_number = call_info.get("to", {}).get("phoneNumber") or call_info.get("to", {}).get("extensionNumber")
            call_duration = call_info.get("duration") # Duration in seconds

            # --- IMPLEMENTATION: Securely fetch Organization Phone Numbers ---
            settings = frappe.get_cached_doc("RingCentral Settings")
            org_numbers_str = settings.organization_numbers or ""
            # Assuming organization_numbers is a comma-separated list of numbers and extensions
            org_numbers = [n.strip() for n in org_numbers_str.split(',') if n.strip()]

            # Determine if the call was incoming or outgoing relative to the ERPNext organization
            if to_number in org_numbers:
                # Assume external number is the customer/contact
                customer_phone = from_number
                communication_type = "Incoming Call"
            else:
                # Assume external number is the customer/contact
                customer_phone = to_number
                communication_type = "Outgoing Call"

            # 2. Find the Customer based on the phone number
            customer_name = find_customer_by_phone(customer_phone)
            
            if not customer_name:
                frappe.log_error(f"Customer not found for phone: {customer_phone}", "RingCentral Webhook Failed")
                return "Customer lookup failed", 404

            # 3. Fetch Transcript and create log entry
            # Calls the corrected get_transcript function
            call_transcript = get_transcript(event_id)
            
            create_call_communication(
                customer_name,
                communication_type,
                from_number,
                to_number,
                call_duration,
                call_transcript,
                event_id
            )
            
            frappe.db.commit()
            return "Call logged successfully", 200

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "RingCentral Webhook Error")
            return "Internal Server Error", 500
    
    # Handle non-POST requests (e.g., RingCentral validation attempts)
    return "OK", 200

def find_customer_by_phone(phone_number):
    """Searches for a Customer or Contact linked to the given phone number."""
    
    # Basic cleanup of phone number for matching (removes common formatting)
    cleaned_phone = "".join(filter(str.isdigit, phone_number or ""))
    
    if not cleaned_phone:
        return None
        
    # Search for Contact linked to the phone
    contact_name = frappe.db.get_value(
        "Contact", 
        {"primary_contact_no": ("like", f"%{cleaned_phone}%")},
        "name"
    )
    
    if contact_name:
        # Get the Customer linked to the Contact
        customer_link = frappe.db.get_value("Dynamic Link", {"link_doctype": "Customer", "parenttype": "Contact", "parent": contact_name}, "link_name")
        return customer_link

    # Fallback to search directly in Customer's primary fields (less common)
    customer_name = frappe.db.get_value(
        "Customer",
        {"phone_no": ("like", f"%{cleaned_phone}%")},
        "name"
    )
    return customer_name

# --- IMPLEMENTATION: Real Transcript Fetching (uses imported connect_to_ringcentral) ---
def get_transcript(call_id):
    """
    Connects to the RingCentral API using credentials from RingCentral Settings
    and fetches the text transcript for the given call ID.
    
    NOTE: Placeholder SDK functions (e.g., get_call_log_record, download_file) 
    are mocked in rc_client.py.
    """
    # 1️⃣ Fetch credentials from RingCentral Settings (using cached doc for efficiency)
    settings = frappe.get_cached_doc("RingCentral Settings")
    client_id = settings.client_id
    client_secret = settings.client_secret
    # Ensure you have a field named 'environment' on your Settings DocType
    env = settings.environment.lower()  
    
    # 2️⃣ Initialize your API Client using those credentials (imported from rc_client.py)
    rc_client = connect_to_ringcentral(client_id, client_secret, env) 

    # 3️⃣ Fetch the call log details using the call_id
    call_log_details = rc_client.get_call_log_record(call_id)

    # 4️⃣ Extract the transcript URI from the call log
    transcript_uri = call_log_details.get('transcriptUri')
    if not transcript_uri:
        # Log and stop processing if no transcript exists
        frappe.log_error(f"Transcript URI missing for Call ID: {call_id}", "RingCentral Transcript Error")
        return "Transcript not available (No URI found)."

    # 5️⃣ Download the transcript content
    transcript_data = rc_client.download_file(transcript_uri)

    # 6️⃣ Return the transcript text
    return transcript_data.text_content

def create_call_communication(customer, communication_type, from_num, to_num, duration, transcript, event_id):
    """Creates a new Communication document linked to the Customer."""
    
    subject = f"{communication_type}: {customer} ({from_num} to {to_num})"
    
    communication = frappe.new_doc("Communication")
    communication.communication_date = now_datetime()
    communication.subject = subject
    communication.communication_type = "Phone"
    communication.content = transcript
    communication.status = "Closed"
    
    # Link to the Customer
    communication.reference_doctype = "Customer"
    communication.reference_name = customer
    
    # Optional: Log the external RingCentral ID for traceability
    # These fields MUST be created in the Communication DocType via Customize Form
    communication.custom_ringcentral_id = event_id 
    
    # Call duration (requires a custom field on Communication DocType)
    communication.custom_call_duration = duration 

    communication.insert(ignore_permissions=True)
    
    frappe.msgprint(f"Successfully logged {communication_type} for {customer}")
    return communication.name
