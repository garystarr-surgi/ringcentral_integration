import frappe
from frappe.utils import now_datetime
import json

@frappe.whitelist(allow_guest=True)
def handle_call_webhook(call_data=None):
    """
    Receives and processes the webhook payload from RingCentral when a call is completed.
    
    The API must be configured with allow_guest=True since RingCentral calls it as an unauthenticated external service.
    
    :param call_data: The JSON payload sent by RingCentral.
    """
    
    if frappe.request and frappe.request.method == 'POST':
        try:
            # 1. Get data from POST request body
            data = json.loads(frappe.request.data)
            
            # Extract key call details
            event_id = data.get("uuid")
            event_type = data.get("event")
            
            # --- Assuming the webhook structure provides necessary call info ---
            # NOTE: Actual RC webhooks for call events vary. We will use placeholders.
            
            # Extract relevant call leg data
            call_info = data.get("body", {})
            from_number = call_info.get("from", {}).get("phoneNumber") or call_info.get("from", {}).get("extensionNumber")
            to_number = call_info.get("to", {}).get("phoneNumber") or call_info.get("to", {}).get("extensionNumber")
            call_duration = call_info.get("duration") # Duration in seconds

            # Determine if the call was incoming or outgoing relative to the ERPNext organization
            if to_number in ["YOUR_ORGANIZATION_MAIN_NUMBER", "OTHER_ORGANIZATION_NUMBERS"]:
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

            # 3. Fetch (Simulated) Transcript and create log entry
            call_transcript = get_simulated_transcript(event_id, call_duration)
            
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

def get_simulated_transcript(call_id, duration):
    """
    Placeholder for fetching the actual transcript from the RingCentral API.
    In a real app, this would make an API call using the stored API keys.
    """
    
    minutes = round(duration / 60, 1) if duration else 0
    
    transcript = f"""
    --- Call Transcript (ID: {call_id}) ---
    
    **Summary:** This was an automated simulation of a call log. In a live system, this 
    area would contain the full, retrieved transcription text from RingCentral.
    
    **Actionable Insights (AI-Generated):**
    - Customer expressed interest in a new product line (Product X).
    - Requires a follow-up email with pricing details by end of day.
    
    **Call Duration:** {minutes} minutes
    """
    return transcript

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
    communication.custom_ringcentral_id = event_id # Requires a custom field on Communication DocType
    
    # Call duration (requires a custom field on Communication DocType)
    communication.custom_call_duration = duration 

    communication.insert(ignore_permissions=True)
    
    frappe.msgprint(f"Successfully logged {communication_type} for {customer}")
    return communication.name
