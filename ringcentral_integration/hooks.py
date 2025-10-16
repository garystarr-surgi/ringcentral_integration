# -*- coding: utf-8 -*-
from . import __version__ as app_version

app_name = "ringcentral_integration"
app_title = "RingCentral Integration"
app_publisher = "Gemini AI"
app_description = "Integrates RingCentral webhooks to log customer calls as Frappe Communications."
app_email = "support@example.com"
app_license = "mit"

# --- Whitelisted Methods (API Endpoints) ---
# This registers the Python function as a public API endpoint that RingCentral will call.
# The URL will be: [YourSite]/api/method/ringcentral_integration.ringcentral_api.rc_webhook_handler.handle_call_webhook
whitelisted_methods = [
    "ringcentral_integration.ringcentral_api.rc_webhook_handler.handle_call_webhook"
]

# --- Other configurations ---
# Enable translation for this app
# translate_messages = 'ringcentral_integration/translations/en.csv'

# Enable logging
# log_events = True
