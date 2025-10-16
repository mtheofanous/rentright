import streamlit as st
import sqlite3
import re
import hashlib
import smtplib
from email.mime.text import MIMEText
from uuid import uuid4
import os
from pathlib import Path
from html import escape
import uuid
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo 
import requests
from functools import lru_cache
from json import JSONDecodeError
import json
import io
import shutil
from PIL import Image, ImageDraw, ImageFont

# Safe import: utils_vault may rely on missing secrets (KeyError)
VAULT_OK = True
VAULT_ERR = None
try:
    from utils_vault import encrypt_bytes, decrypt_bytes, sha256_bytes
except Exception as e:
    # Fallback: disable vault but keep the app running
    import hashlib
    def encrypt_bytes(b: bytes) -> bytes: return b
    def decrypt_bytes(b: bytes) -> bytes: return b
    def sha256_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
    VAULT_OK = False
    VAULT_ERR = e



# ⚠️ set_page_config must be the first Streamlit command
st.set_page_config(page_title="RentRight", page_icon="🏠", layout="centered")

import streamlit as st

# --- UI controls (put in sidebar if you like) ---
with st.sidebar:
    st.markdown("### Display settings")
    base_font_px = st.slider("Base text size (px)", 13, 22, 16, 1)
    content_width_px = st.slider("Content width (px)", 800, 1400, 1024, 8)
    side_gutter_px = st.slider("Side padding (px)", 0, 64, 16, 2)
    compact_headers = st.checkbox("Slightly smaller headings", value=True)

# --- CSS injector ---
heading_scale = 1 if compact_headers else 1.12
st.markdown(
    f"""
    <style>
      /* 1) Content column width (works with layout="centered") */
      .appview-container .main .block-container {{
        max-width: {content_width_px}px;   /* ← your in-between width */
        padding-left: {side_gutter_px}px;
        padding-right: {side_gutter_px}px;
      }}

      /* 2) Base typography scale */
      html, body, [data-testid="stAppViewContainer"] {{
        font-size: {base_font_px}px;
        line-height: 1.55;
      }}

      /* 3) Headings (scale with the base size) */
      h1 {{ font-size: {round(base_font_px*2.0*heading_scale)}px; }}
      h2 {{ font-size: {round(base_font_px*1.6*heading_scale)}px; }}
      h3 {{ font-size: {round(base_font_px*1.35*heading_scale)}px; }}
      h4, h5, h6 {{ font-size: {round(base_font_px*1.15*heading_scale)}px; }}

      /* 4) Markdown body text + tables */
      .markdown-text-container, [data-testid="stMarkdownContainer"] {{
        font-size: {base_font_px}px;
      }}

      /* 5) Make inputs match the base size a bit better */
      .stTextInput > div > div input,
      .stTextArea textarea,
      .stSelectbox [data-baseweb="select"] div,
      .stNumberInput input {{
        font-size: {max(base_font_px-1, 12)}px;
      }}
      label, .st-emotion-cache-16idsys p, .st-emotion-cache-10trblm p {{
        font-size: {max(base_font_px-2, 11)}px;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)



# === Language selector & translation ===
if "lang" not in st.session_state:
    st.session_state["lang"] = "Ελληνικά" 
    # default
TRANSLATIONS_EL = {
    "**Created:**": "**Δημιουργήθηκε:**",
    "**Email:**": "**Email:**",
    "**Score:**": "**Βαθμολογία:**",
    "**Status:**": "**Κατάσταση:**",
    "**Tenant:**": "**Ενοικιαστής:**",
    "**To landlord:**": "Στον Ιδιοκτήτη",
    "Property filters": "Φίλτρα αναζήτησης",
    "Phone (optional)": "Τηλέφωνο (προαιρετικό)",
    "Show phone to others?": "Εμφάνιση τηλεφώνου σε άλλους;",
    "Enter a valid phone number.": "Εισάγετε ένα έγκυρο τηλέφωνο.",
    "Active": "Ενεργός",
    "Inactive": "Ανενεργός",
    "Admin": "Διαχειριστής",
    "Anywhere":"Παντού",
    "Address": "Διεύθυνση",
    "Address is required.": "Απαιτείται διεύθυνση.",
    "Add": "Προσθήκη",
    "Add Contact": "Προσθήκη Επαφής",
    "Add contact": "Προσθήκη Επαφής",
    "Add Previous Landlord": "Προσθήκη Προηγούμενου Ιδιοκτήτη",
    "Add previous landlord": "Προσθήκη προηγούμενου ιδιοκτήτη",
    "Add property": "Προσθήκη ακινήτου",
    "Administrator Dashboard": "Πίνακας Διαχειριστή",
    "All": "Όλα",
    "Age": "Ηλικία",
    "Marital status": "Οικογενειακή κατάσταση",
    "Monthly salary (€)":"Μηνιαίος μισθός (€)",
    "Pets": "Κατοικίδια",
    "Number of tenants": "Αριθμός ενοίκων",
    "Contract type": "Tύπος σύμβασης",
    "All reference requests": "Όλα τα αιτήματα σύστασης",
    "All Reference Requests": "Όλα τα Αιτήματα Σύστασης",
    "Any": "Οποιοδήποτε",
    "App Base URL": "Βασικό URL Εφαρμογής",
    "Apartment in good condition": "Καλή κατάσταση",
    "Are you sure you want to cancel this reference request?": "Είσαι σίγουρος ότι θέλεις να ακυρώσεις αυτό το αίτημα;",
    "Are you sure you want to delete this previous landlord and all related data?": "Θέλεις σίγουρα να διαγράψεις αυτόν τον προηγούμενο ιδιοκτήτη και όλα τα σχετικά δεδομένα;",
    "Avg score": "Μ.Ο. βαθμολογίας",
    "Average": "Μέσος όρος",
    "Base URL for Links": "Βασικό URL για Συνδέσμους",
    "Single": "Ελεύθερος/η",
    "Married": "Παντρεμένος/η",
    "Divorced": "Διαζευγμένος/η",
    "A few words about yourself": "Πες μας λίγα λόγια για εσένα",
    "Widowed": "Χήρος/α",
    "Permanent": "Μόνιμη",
    "Temporary": "Προσωρινή",
    "Freelancer": "Ελεύθερος επαγγελματίας",
    "Other": "Άλλο",
    "Cancel Reference": "Ακύρωση Σύστασης",
    "Cancel request": "Ακύρωση αιτήματος",
    "Cancel this reference request?": "Ακύρωση αυτού του αιτήματος σύστασης;",
    "Can’t add contact": "Αδυναμία προσθήκης επαφής",
    "Can’t add property": "Αδυναμία προσθήκης ακινήτου",
    "Can’t delete": "Αδυναμία διαγραφής",
    "Can’t read the saved file": "Αδυναμία ανάγνωσης του αποθηκευμένου αρχείου",
    "Can’t save changes": "Αδυναμία αποθήκευσης αλλαγών",
    "Cancel Request": "Ακύρωση αιτήματος",
    "Change password": "Αλλαγή κωδικού",
    "Changes saved.": "Οι αλλαγές αποθηκεύτηκαν.",
    "City": "Πόλη",
    "Comments": "Σχόλια",
    "Comments (optional)": "Σχόλια (προαιρετικά)",
    "Completed": "Ολοκληρωμένα",
    "Confirm password": "Επιβεβαίωση κωδικού",
    "Connected": "Συνδεδεμένος",
    "Connected.": "Συνδέθηκε.",
    "Connect": "Σύνδεση",
    "Connect to view full answers": "Συνδεθείτε για να δείτε όλες τις απαντήσεις",
    "Contract is locked awaiting landlord consent.": "Το συμβόλαιο παραμένει κλειδωμένο, αναμένεται συναίνεση ιδιοκτήτη",
    "Contract locked until landlord consents": "Το συμβόλαιο είναι κλειδωμένο μέχρι να συναινέσει ο ιδιοκτήτης",
    "Contract Status:": "Κατάσταση Συμβολαίου:",
    "Contract verified — no upload needed.": "Το συμβόλαιο επιβεβαιώθηκε — δεν απαιτείται μεταφόρτωση.",
    "Contract verified successfully.": "Το συμβόλαιο επικυρώθηκε με επιτυχία.",
    "Create Account": "Δημιουργία Λογαριασμού",
    "Delete": "Διαγραφή",
    "Delete previous landlord": "Διαγραφή προηγούμενου ιδιοκτήτη",
    "Disconnected": "Αποσυνδέθηκε",
    "Disconnected.": "Αποσυνδέθηκε.",
    "District": "Περιοχή",
    "Download contract": "Λήψη συμβολαίου",
    "Edit": "Επεξεργασία",
    "Email": "Email",
    "Email & App Settings": "Ρυθμίσεις Email & Εφαρμογής",
    "Email delivery failed": "Αποτυχία αποστολής email",
    "Profile details":"Προσωπικά στοιχεία",
    "Email Settings (SMTP)": "Ρυθμίσεις Email (SMTP)",
    "Enter a valid email.": "Εισάγετε έγκυρο email.",
    "Enter at least a city or a district.": "Εισαγάγετε τουλάχιστον πόλη ή περιφερειακή ενότητα.",
    "Enter the landlord’s address.": "Εισαγάγετε τη διεύθυνση του ιδιοκτήτη.",
    "Enter the landlord’s name.": "Εισαγάγετε το όνομα του ιδιοκτήτη.",
    "Enter an address.": "Εισαγάγετε διεύθυνση.",
    "e.g. Maria or nikos@example.com": "π.χ. Μαρία ή nikos@example.com",
    "e.g. Maria Papadopoulou or papadop": "π.χ. Μαρία Παπαδοπούλου ή papadop",
    "Find Landlords": "Αναζήτηση Ιδιοκτητών",
    "Find tenants": "Εύρεση ενοικιαστών",
    "Find Tenants": "Εύρεση Ενοικιαστών",
    "Find Tenants (Open to Rent)": "Εύρεση ενοικιαστών (Ανοιχτός για ενοικίαση)",
    "Find landlords": "Αναζήτηση ιδιοκτητών",
    "Floor": "Όροφος",
    "Job position": "Τίτλος εργασίας",
    "For more details": "Για περισσότερες λεπτομέρειες",
    "For more details visit": "Για περισσότερες λεπτομέρειες",
    "Full name": "Πλήρες όνομα",
    "Future Landlords (Contacts)": "Μελλοντικοί Ιδιοκτήτες (Επαφές)",
    "Future landlords":"Υποψήφιοι Ιδιοκτήτες",
    "Good condition": "Καλή κατάσταση",
    "Hide": "Απόκρυψη",
    "I’m looking for a place": "Αναζητώ κατοικία",
    "I'm currently looking for a place": "Αναζητώ αυτήν την περίοδο σπίτι",
    "Incorrect email or password. Please try again.": "Λάθος email ή κωδικός. Παρακαλώ δοκιμάστε ξανά.",
    "In contacts": "Στις επαφές",
    "Invitation sent.": "Η πρόσκληση στάλθηκε.",
    "Invitation sent successfully.": "Η πρόσκληση στάλθηκε με επιτυχία.",
    "Invited": "Προσκεκλημένος",
    "Landlord": "Ιδιοκτήτης",
    "Agent": "Μεσίτης",
    "Agent Dashboard": "Πίνακας Μεσίτη",
    "Agency / Business name": "Επωνυμία Μεσιτικού",
    "AFM (9 digits)": "ΑΦΜ (9 ψηφία)",
    "AMK / Registry (optional)": "ΑΜΚ / Μητρώο (προαιρετικό)",
    "Please enter your agency / business name.": "Παρακαλώ εισάγετε την επωνυμία του μεσιτικού.",
    "Please enter a valid AFM (9 digits).": "Παρακαλώ εισάγετε έγκυρο ΑΦΜ (9 ψηφία).",
    "Real Estate Agent verification": "Επαλήθευση Μεσίτη",
    "Landlord Dashboard": "Πίνακας Ιδιοκτήτη",
    "Landlord email": "Email ιδιοκτήτη",
    "Landlord name": "Όνομα ιδιοκτήτη",
    "Latest answers": "Τελευταίες απαντήσεις",
    "Latest status": "Τελευταία κατάσταση",
    "Let landlords know you’re looking and share your criteria.": "Ενημερώνει τους ιδιοκτήτες ότι αναζητάτε και εμφανίζει τα κριτήριά σας.",
    "Listing URL (optional)": "Σύνδεσμος αγγελίας (προαιρετικό)",
    "Logged in as": "Συνδεθήκατε ως",
    "Logged in with email": "Συνδεθήκατε με email",
    "Looking in": "Αναζήτηση σε",
    "Max floor": "Μέγιστος όροφος",
    "Max price (€)": "Μέγιστη τιμή (€)",
    "Max rooms": "Μέγιστα δωμάτια",
    "Max size (m²)": "Μέγιστο μέγεθος (τ.μ.)",
    "Min floor": "Ελάχιστος όροφος",
    "Min price (€)": "Ελάχιστη τιμή (€)",
    "Min rooms": "Ελάχιστα δωμάτια",
    "Send invitation": "Αποστολή πρόσκλησης",
    "Previous landlords & references": "Προηγούμενοι ιδιοκτήτες & συστάσεις",
    "No relation": "Χωρίς σύνδεση",
    "Min size (m²)": "Ελάχιστο μέγεθος (τ.μ.)",
    "Missing SMTP details: host, port, username, password, sender, or recipient.": "Λείπουν στοιχεία SMTP: host, port, όνομα χρήστη, κωδικός, αποστολέας ή παραλήπτης.",
    "Municipality": "Δήμος",
    "Municipality (City)": "Δήμος (Πόλη)",
    "My Contacts": "Επαφές",
    "My properties": "Τα ακίνητά μου",
    "My Properties": "Τα Ακίνητά μου",
    "My References": "Συστάσεις",
    "Name": "Ονοματεπώνυμο",
    "New reference request": "Νέο αίτημα σύστασης",
    "No": "Όχι",
    "No actions": "Καμία ενέργεια",
    "No active reference request.": "Δεν υπάρχει ενεργό αίτημα σύστασης.",
    "No matches.": "Δεν βρέθηκαν αποτελέσματα.",
    "No previous landlords added yet.": "Δεν έχουν προστεθεί ακόμη προηγούμενοι ιδιοκτήτες.",
    "No previous landlords yet.": "Δεν έχουν προστεθεί προηγούμενοι ιδιοκτήτες.",
    "No properties yet.": "Δεν υπάρχουν ακόμη ακίνητα.",
    "No prospective tenants yet.": "Δεν υπάρχουν ακόμη υποψήφιοι ενοικιαστές.",
    "No reference found.": "Δεν βρέθηκε σύσταση.",
    "No reference requests have been created yet.": "Δεν έχουν δημιουργηθεί ακόμα αιτήματα σύστασης.",
    "No reference requests yet.": "Δεν υπάρχουν ακόμη αιτήματα σύστασης.",
    "None": "Καμία",
    "Not My Tenant / Cancel": "Δεν είναι ο ενοικιαστής μου / Ακύρωση",
    "Open listing": "Προβολή αγγελίας",
    "Open to Rent": "Ενοικίαση",
    "Open to rent": "Ανοιχτός για ενοικίαση",
    "Paid on time": "Πλήρωνε στην ώρα του",
    "Paid on time?": "Πλήρωνε στην ώρα του;",
    "Password": "Κωδικός",
    "Message": "Μήνυμα",
    "Disconnect": "Αποσύνδεση",
    "References": "Συστάσεις",
    "Hidden from tenants": "Κρυφό από ενοικιαστές",
    "Cancelled": "Ακυρωμένο",
    "Pending": "Εκκρεμεί",
    "Pending References (All Tenants)": "Εκκρεμείς Συστάσεις (Όλοι οι Ενοικιαστές)",
    "Please check your ranges: maximums must be greater than or equal to minimums.": "Ελέγξτε τα εύρη: τα μέγιστα πρέπει να είναι μεγαλύτερα ή ίσα από τα ελάχιστα.",
    "Please enter a valid email address.": "Παρακαλώ εισαγάγετε έγκυρη διεύθυνση email.",
    "Please enter at least a city or a district.": "Καταχωρίστε τουλάχιστον πόλη ή περιοχή.",
    "Please enter the landlord’s address.": "Παρακαλώ εισαγάγετε τη διεύθυνση του ιδιοκτήτη.",
    "Please enter the landlord’s name.": "Παρακαλώ εισαγάγετε το όνομα του ιδιοκτήτη.",
    "Please enter your full name.": "Παρακαλώ εισαγάγετε το πλήρες όνομά σας.",
    "Price": "Τιμή",
    "Price (€)": "Τιμή (€)",
    "Privacy & verification details": "Λεπτομέρειες απορρήτου & επαλήθευσης",
    "Privacy Notice": "Πολιτική Απορρήτου",
    "Prospective tenants": "Υποψήφιοι ενοικιαστές",
    "Prospective Tenants (Listed You as Future Landlord)": "Υποψήφιοι Ενοικιαστές (Σας έχουν δηλώσει ως μελλοντικό ιδιοκτήτη)",
    "Reference cancelled.": "Η σύσταση ακυρώθηκε.",
    "Reference details": "Λεπτομέρειες σύστασης",
    "Reference details are visible after you connect.": "Οι λεπτομέρειες συστάσεων είναι ορατές μετά τη σύνδεση.",
    "Reference for": "Σύσταση για",
    "Reference Link": "Σύνδεσμος Σύστασης",
    "Reference Requests Sent To You": "Αιτήματα σύστασης που σας στάλθηκαν",
    "Reference request emailed.": "Το αίτημα σύστασης εστάλη με email.",
    "Reference request sent successfully by email.": "Το αίτημα σύστασης στάλθηκε με επιτυχία μέσω email.",
    "Reference submitted successfully. Thank you!": "Η αναφορά υποβλήθηκε με επιτυχία. Ευχαριστούμε!",
    "Reference submitted successfully.": "Η σύσταση υποβλήθηκε με επιτυχία.",
    "Refresh": "Ανανέωση",
    "Region": "Περιφέρεια",
    "Regional unit":"Περιφερειακές Ενότητες",
    "Registered:": "Εγγράφηκε:",
    "Profile":"Προφίλ",
    "Reject": "Απόρριψη",
    "Rejected": "Απορρίφθηκε",
    "Rejected.": "Απορρίφθηκε.",
    "Remove": "Αφαίρεση",
    "Request cancelled and data deleted, but email notification failed: ": "Το αίτημα ακυρώθηκε και τα δεδομένα διαγράφηκαν, αλλά η ειδοποίηση email απέτυχε: ",
    "Request cancelled.": "Το αίτημα ακυρώθηκε.",
    "Request cancelled. Landlord notified; contract and responses deleted.": "Το αίτημα ακυρώθηκε. Ο ιδιοκτήτης ειδοποιήθηκε· το συμβόλαιο και οι απαντήσεις διαγράφηκαν.",
    "Request connection": "Αίτημα σύνδεσης",
    "Request kept.": "Το αίτημα διατηρήθηκε.",
    "Request Reference": "Αίτημα Σύστασης",
    "Request reference": "Αίτημα σύστασης",
    "Requests": "Αιτήματα",
    "Reset": "Επαναφορά",
    "Results limit": "Όριο αποτελεσμάτων",
    "Rooms": "Δωμάτια",
    "rooms": "Δωμάτια",
    "Role": "Ρόλος",
    "Save changes": "Αποθήκευση αλλαγών",
    "Save preferences": "Αποθήκευση προτιμήσεων",
    "Score": "Βαθμολογία",
    "Score:": "Βαθμολογία:",
    "Search": "Αναζήτηση",
    "Search by name or email": "Αναζήτηση με όνομα ή email",
    "Search landlords": "Αναζήτηση ιδιοκτητών",
    "Search landlords by property": "Αναζήτηση ιδιοκτητών ανά ακίνητο",
    "Search unavailable.": "Η αναζήτηση δεν είναι διαθέσιμη.",
    "Send Invitation": "Αποστολή Πρόσκλησης",
    "Send request by email": "Αίτημα μέσω email",
    "Send Test Email": "Αποστολή Δοκιμαστικού Email",
    "Send test to": "Αποστολή δοκιμής σε",
    "Share this link manually": "Μοιραστείτε αυτόν τον σύνδεσμο χειροκίνητα",
    "Share this link manually or try again": "Μοιραστείτε τον σύνδεσμο χειροκίνητα ή δοκιμάστε ξανά",
    "Show": "Εμφάνιση",
    "Sign In": "Σύνδεση",
    "Sign Out": "Αποσύνδεση",
    "No contacts yet": "Δεν έχετε επαφές",
    "Size": "Μέγεθος",
    "Size (m²)": "Μέγεθος (τ.μ.)",
    "SMTP test email body": "Αν λάβατε αυτό το email, η ρύθμιση SMTP λειτουργεί. ✅",
    "Start New Reference Request": "Αίτημα Σύστασης",
    "Status:": "Κατάσταση:",
    "Stops this request and deletes the contract and responses. Landlord is notified.": "Σταματά το αίτημα και διαγράφει συμβόλαιο και απαντήσεις. Ο ιδιοκτήτης ενημερώνεται.",
    "Street, number, city": "Οδός, αριθμός, πόλη",
    "Submit Reference": "Υποβολή σύστασης",
    "Tenant": "Ενοικιαστής",
    "Tenant Dashboard": "Πίνακας Ενοικιαστή",
    "Tenant preferences": "Προτιμήσεις ενοικιαστή",
    "Tenant:": "Ενοικιαστής:",
    "Thanks, your response is saved.": "Ευχαριστούμε, η απάντησή σας αποθηκεύτηκε.",
    "This email is already registered.": "Αυτό το email έχει ήδη καταχωρηθεί.",
    "This reference has already been submitted. Thank you!": "Αυτή η σύσταση έχει ήδη υποβληθεί. Ευχαριστούμε!",
    "Tip: leave a minimum as 0 if you have no minimum for that field.": "Συμβουλή: αφήστε το ελάχιστο ως 0 αν δεν έχετε ελάχιστο για το πεδίο.",
    "Type a name or email": "Πληκτρολογήστε όνομα ή email",
    "Unknown role:": "Άγνωστος ρόλος:",
    "Unpaid utilities": "Απλήρωτοι λογαριασμοί",
    "Upload tenancy contract (PDF or image)": "Μεταφόρτωση συμβολαίου μίσθωσης (PDF ή εικόνα)",
    "Upload Tenancy Contract (PDF or Image)": "Μεταφόρτωση Συμβολαίου Μίσθωσης (PDF ή Εικόνα)",
    "Replace Tenancy Contract (PDF or Image)": "Αντικατάσταση Συμβολαίου Μίσθωσης (PDF ή Εικόνα)",
    "Updated": "Ενημερώθηκε",
    "Updated:": "Ενημερώθηκε:",
    "Property characteristics": "Χαρακτηριστικά ακινήτου",
    "Use ‘Any’ to skip": "Χρησιμοποιήστε «Οποιοδήποτε» για παράλειψη",
    "Utilities unpaid": "Απλήρωτοι λογαριασμοί",
    "Valid or expired token error": "Μη έγκυρο ή ληγμένο διακριτικό σύστασης.",
    "Verified": "Επιβεβαιωμένο",
    "View Submitted Reference": "Προβολή Υποβληθείσας Σύστασης",
    "Visible properties": "Ορατά ακίνητα",
    "Visible to tenants": "Ορατό στους ενοικιαστές",
    "Welcome": "Καλώς ορίσατε, ",
    "Can’t find the landlord? Send a request by email.": "Δεν βρίσκεις τον ιδιοκτήτη; Στείλε αίτημα μέσω email.",
    "Yes": "Ναι",
    "🏠 RentRight — Landlord Reference Portal": "🏠 RentRight — Συστατικές επιστολές Ιδιοκτήτη",
    "Contract Status:": "Κατάσταση συμβολαίου:",
    "✅ Verified": "✅ Επιβεβαιωμένο",
    "Overall tenant score": "Συνολική αξιολόγηση ενοικιαστή",
    "Paid on time?": "Πλήρωνε στην ώρα του;",
    "Any unpaid utilities?": "Υπάρχουν απλήρωτοι λογαριασμοί κοινής ωφέλειας;",
    "Left in good condition?": "Παραδόθηκε σε καλή κατάσταση;",
    "Yes": "Ναι",
    "No": "Όχι",
    "Comments (optional)": "Σχόλια (προαιρετικά)",
    "Contract locked until landlord consents": "Το συμβόλαιο είναι κλειδωμένο μέχρι να δώσει συγκατάθεση ο ιδιοκτήτης",
    "Download contract": "Λήψη συμβολαίου",
    "Can’t read the saved file:": "Δεν είναι δυνατή η ανάγνωση του αποθηκευμένου αρχείου:",
    "No active reference request.": "Καμία ενεργή αίτηση σύστασης.",
    "New reference request": "Νέα αίτηση σύστασης",
    "Delete this previous landlord and all related data?": "Διαγραφή αυτού του προηγούμενου ιδιοκτήτη και όλων των σχετικών δεδομένων;",
    "Delete": "Διαγραφή",
    "Previous landlord deleted.": "Ο προηγούμενος ιδιοκτήτης διαγράφηκε.",
    "Previous landlord": "Προηγούμενος ιδιοκτήτης",
    "Can’t delete": "Αδυναμία διαγραφής",
    "Keep": "Διατήρηση",
    "Delete previous landlord": "Διαγραφή προηγούμενου ιδιοκτήτη",
    "✅ Verify Contract": "✅ Επικύρωση Συμβολαίου",
    "✅ Verified": "✅ Επιβεβαιωμένο",
    "✅ Verified Contract": "✅ Επικυρωμένο Συμβόλαιο",
    "⏳ Pending Review": "⏳ Αναμονή Ελέγχου",
    "ΑFΜ (9 digits)": "ΑΦΜ (9 ψηφία)",
    "Did the tenant pay on time?": "Πλήρωνε ο ενοικιαστής στην ώρα του;",
    "Did the tenant leave utilities unpaid?": "Άφησε ο ενοικιαστής απλήρωτους λογαριασμούς;",
    "Did the tenant leave the apartment in good condition?": "Άφησε ο ενοικιαστής το διαμέρισμα σε καλή κατάσταση;",
    "Optional comments": "Προαιρετικά σχόλια",
    "Permanent": "Μόνιμη",
    "Temporary": "Προσωρινή",
    "Freelancer": "Ελεύθερος επαγγελματίας",
    "Single": "Άγαμος/Άγαμη",
    "Married": "Έγγαμος/Έγγαμη",
    "Divorced": "Διαζευγμένος/Διαζευγμένη",
    "Widowed": "Χήρος/Χήρα",
    "Other": "Άλλο",
    "Upload": "Μεταφόρτωση",
    "My documents": "Τα έγγραφά μου",
    "Latest Payslips": "Πρόσφατα εκκαθαριστικά μισθοδοσίας",
    "Add your 1–3 most recent ones.": "Προσθέστε τα 1–3 πιο πρόσφατα.",
    "Tax Return": "Φορολογική δήλωση",
    "Used only to verify income.": "Χρησιμοποιείται μόνο για επαλήθευση εισοδήματος.",
    "Employment Contract": "Σύμβαση εργασίας",
    "Photo or PDF of your contract.": "Φωτογραφία ή PDF της σύμβασής σας.",
    "Upload documents for admin review. Documents are visible only to admins.":
        "Μεταφορτώστε έγγραφα για έλεγχο από διαχειριστές. Τα έγγραφα είναι ορατά μόνο σε αυτούς.",
    "Supported: PDF/PNG/JPG/WebP · up to 10 MB per file.":
        "Υποστηρίζονται: PDF/PNG/JPG/WebP · έως 10 MB ανά αρχείο.",
    "Please select at least one file before saving.":
        "Παρακαλώ επιλέξτε τουλάχιστον ένα αρχείο πριν την αποθήκευση.",
    "Please select a file before saving.":
        "Παρακαλώ επιλέξτε ένα αρχείο πριν την αποθήκευση.",
    "The file exceeds the 10 MB limit.": "Το αρχείο υπερβαίνει το όριο των 10 MB.",
    "file(s) uploaded. Status: Pending.": "Το(α) αρχείο(α) ανέβηκαν. Κατάσταση: Σε εκκρεμότητα.",
    "Upload failed: {err}": "Αποτυχία μεταφόρτωσης: {err}",
    "Upload failed for {name}: {err}": "Αποτυχία μεταφόρτωσης για {name}: {err}",
    "You haven't uploaded any documents yet.": "Δεν έχετε ανεβάσει ακόμη έγγραφα.",
    "Verified": "Επαληθευμένο",
    "Pending": "Σε εκκρεμότητα",
    "Rejected": "Απορρίφθηκε",
    "Uploaded": "Μεταφορτώθηκε",
    "Download": "Λήψη",
    "Delete": "Διαγραφή",
    "Confirm delete": "Επιβεβαίωση διαγραφής",
    "Cancel": "Ακύρωση",
    "Tenant: {tenant_name} — Address: {address}": "Ενοικιαστής: {tenant_name} — Διεύθυνση: {address}",
    "I confirm I was the landlord for this tenant and consent to the use and disclosure of my full name solely for verification of this reference.": "Επιβεβαιώνω ότι ήμουν ο ιδιοκτήτης αυτού του ενοικιαστή και συναινώ στη χρήση και γνωστοποίηση του πλήρους ονόματός μου αποκλειστικά για την επαλήθευση αυτής της σύστασης.",
    "RentRight processes your responses, and if the tenant has uploaded a tenancy contract, may decrypt and review it after your confirmation solely to verify this reference (lawful basis: legitimate interests). The contract remains encrypted and is not shown to you. You may object at any time as described in the Privacy Notice.": "Η RentRight επεξεργάζεται τις απαντήσεις σας και, εάν ο ενοικιαστής έχει ανεβάσει μισθωτήριο συμβόλαιο, μπορεί να το αποκρυπτογραφήσει και να το εξετάσει μετά την επιβεβαίωσή σας αποκλειστικά για την επαλήθευση αυτής της σύστασης (νομική βάση: έννομο συμφέρον). Το συμβόλαιο παραμένει κρυπτογραφημένο και δεν εμφανίζεται σε εσάς. Μπορείτε να αντιταχθείτε οποιαδήποτε στιγμή, όπως περιγράφεται στη Δήλωση Απορρήτου.",
}


if "selected_thread" not in st.session_state:
    st.session_state.selected_thread = None  # int | None
if "chat_open" not in st.session_state:
    st.session_state.chat_open = False


def tr(s: str) -> str:
    """Translate string s to Greek if the UI language is Greek; otherwise return s."""
    # 2) READ session_state safely. Do not create or modify it here.
    try:
        lang = st.session_state.get("lang", "English")
    except Exception:
        # In case this is executed before Streamlit fully initializes
        lang = "English"

    if isinstance(s, str) and lang.startswith("Ελλην"):
        return TRANSLATIONS_EL.get(s, s)
    return s


# --- Global style: tiny help "?" badge + tooltip ---

st.markdown("""
<style>
:root{
  /* Tweak these 3 to match your brand */
  --accent: #2563eb;                   /* primary */
  --help-bg: rgba(37,99,235,.12);      /* pill bg */
  --help-fg: #2563eb;                  /* pill text/border */
  --help-border: rgba(37,99,235,.35);
}

/* Tiny circular "?" */
.help-tip{
  display:inline-flex; align-items:center; justify-content:center;
  width:18px; height:18px;             /* size */
  border-radius:999px;
  font-size:12px; line-height:1; font-weight:700;
  background:var(--help-bg); color:var(--help-fg);
  border:1px solid var(--help-border);
  cursor:help; user-select:none; position:relative;
  margin-left:.35rem;
}

/* Tooltip bubble */
.help-tip__bubble{
  position:absolute; left:50%; top:calc(100% + 8px); transform:translateX(-50%);
  min-width:220px; max-width:320px;
  background:#111827; color:#F9FAFB;
  border-radius:8px; padding:10px 12px;
  font-size:12px; line-height:1.45;
  box-shadow:0 6px 24px rgba(0,0,0,.18);
  opacity:0; pointer-events:none; transition:opacity .15s ease;
  z-index:9999;
}
.help-tip__bubble:before{
  content:""; position:absolute; top:-6px; left:50%; transform:translateX(-50%);
  border-width:6px; border-style:solid;
  border-color:transparent transparent #111827 transparent;
}

/* show on hover/focus */
.help-tip:hover .help-tip__bubble,
.help-tip:focus .help-tip__bubble{ opacity:1; }

/* Dark-mode friendly tweaks */
@media (prefers-color-scheme: dark){
  :root{
    --help-bg: rgba(59,130,246,.18);
    --help-fg: #93C5FD;
    --help-border: rgba(147,197,253,.35);
  }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Thread rows (toggle) — default look */
div[data-testid="stSwitch"].thread-row{
  border:1px solid rgba(37,99,235,.25);
  border-radius:10px;
  padding:10px 12px;
  margin-bottom:8px;
  display:flex; align-items:center; gap:.6rem;
}

/* Avatar circle next to the label */
.thread-avatar{
  width:28px; height:28px; border-radius:999px;
  background:#EEF2FF; color:#1F2937; font-weight:700; font-size:12px;
  display:inline-flex; align-items:center; justify-content:center;
}

/* Blue highlight when the row is ON (clicked/open) */
div[data-testid="stSwitch"].thread-row:has(input:checked){
  background:#2563eb; color:white; border-color:#2563eb;
}

/* Make the label stretch so the whole row is clickable */
div[data-testid="stSwitch"].thread-row label{
  flex:1; cursor:pointer;
}
</style>
""", unsafe_allow_html=True)

def _ensure_tfl_css():
    st.markdown("""
    <style>
    .tfl-title{display:flex;align-items:center;gap:12px;margin-bottom:4px}
    .tfl-avatar{width:40px;height:40px;border-radius:999px;display:flex;align-items:center;justify-content:center;
                font-weight:700;color:#111;border:1px solid #e5e7eb;background:linear-gradient(135deg,#f8fafc,#e2e8f0)}
    .tfl-name{font-weight:700;font-size:1.05rem;margin:0}
    .tfl-email{color:#64748b;font-size:.9rem;margin-top:2px}
    .tfl-badge{padding:4px 10px;border-radius:999px;font-size:.85rem;font-weight:600;border:1px solid;display:inline-block}
    .tfl-badge--ok{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}
    .tfl-badge--info{background:#eff6ff;color:#1e40af;border-color:#bfdbfe}
    .tfl-badge--err{background:#fef2f2;color:#7f1d1d;border-color:#fecaca}
    .tfl-meta{color:#94a3b8;font-size:.85rem;margin-top:2px}
    .pill{display:inline-block;padding:2px 8px;border-radius:999px;background:#f1f5f9;color:#334155;font-size:.8rem;
        margin-right:6px;margin-bottom:4px;border:1px solid #e2e8f0}
    .prop-card{border:1px solid #e5e7eb;border-radius:12px;padding:10px 12px;margin-bottom:8px;background:#fff}
    .prop-title{font-weight:600;margin-bottom:2px}
    .prop-sub{color:#475569;font-size:.9rem;margin:4px 0 6px}
    .prop-foot{color:#64748b;font-size:.85rem}
    </style>
    """, unsafe_allow_html=True)

# ---- minimal CSS for Prospective Tenants cards ----
def _ensure_pt_css():
    st.markdown("""
    <style>
    .pt-title{display:flex;align-items:center;gap:12px;margin-bottom:4px}
    .pt-avatar{width:40px;height:40px;border-radius:999px;display:flex;align-items:center;justify-content:center;
            font-weight:700;color:#111;border:1px solid #e5e7eb;background:linear-gradient(135deg,#f8fafc,#e2e8f0)}
    .pt-name{font-weight:700;font-size:1.05rem;margin:0}
    .pt-email{color:#64748b;font-size:.9rem;margin-top:2px}
    .pt-badge{padding:4px 10px;border-radius:999px;font-size:.85rem;font-weight:600;border:1px solid;display:inline-block}
    .pt-badge--ok{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}
    .pt-badge--info{background:#eff6ff;color:#1e40af;border-color:#bfdbfe}
    .pt-badge--err{background:#fef2f2;color:#7f1d1d;border-color:#fecaca}
    .pt-meta{color:#94a3b8;font-size:.85rem;margin-top:2px}
    .pill{display:inline-block;padding:2px 8px;border-radius:999px;background:#f1f5f9;color:#334155;font-size:.8rem;
        margin-right:6px;margin-bottom:4px;border:1px solid #e2e8f0}
    .pill-score{background:#eef2ff;color:#3730a3;border-color:#c7d2fe}
    .pill-ok{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}
    .pill-no{background:#fef2f2;color:#7f1d1d;border-color:#fecaca}
    .pill-na{background:#f1f5f9;color:#334155;border-color:#e2e8f0}
    .ref-card{border:1px solid #e5e7eb;border-radius:12px;padding:10px 12px;margin-bottom:8px;background:#fff}
    .ref-header{display:flex;align-items:center;justify-content:space-between;gap:8px}
    .ref-title{font-weight:600;margin-bottom:2px}
    .ref-row{display:flex;flex-wrap:wrap;gap:6px 8px;margin-top:8px}
    .ref-comments{border-left:3px solid #e2e8f0;padding-left:10px;margin-top:8px;color:#334155}
    .ref-sub{color:#475569;font-size:.9rem;margin:4px 0 6px}
    .ref-foot{color:#64748b;font-size:.85rem}
    </style>
    """, unsafe_allow_html=True)

# === Docked chat drawer (fixed on the right) ===================================
def _ensure_chat_css():
    try:
        if st.session_state.get("_chat_css_done"):
            return
        st.session_state["_chat_css_done"] = True
    except Exception:
        pass

    st.markdown("""
    <style>
      .chat-docked {
        position: fixed;
        right: 12px;
        top: 72px;         /* below your page header */
        bottom: 12px;
        width: 360px;      /* adjust if you want wider/narrower */
        z-index: 999;
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,.08);
        padding: 10px 12px;
        overflow: hidden;
      }
      .chat-docked .chat-body {
        height: calc(100vh - 72px - 12px - 10px - 12px);
        display: flex;
        flex-direction: column;
      }
      .chat-docked .scroll {
        overflow-y: auto;
        flex: 1 1 auto;
      }
      .chat-docked .head {
        display:flex; align-items:center; justify-content:space-between;
        font-weight:600; margin-bottom:8px;
      }
      .chat-fab {
        position: fixed;
        right: 12px;
        bottom: 12px;
        z-index: 998;
      }
    </style>
    """, unsafe_allow_html=True)

def _initials(name: str, email: str) -> str:
    base = (name or "").strip() or (email or "").split("@")[0]
    parts = [p for p in base.replace(".", " ").split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return "?"


def chat_panel_docked():
    """
    Shows your existing chat_panel() inside a fixed right-side drawer when chat is open.
    Falls back to a floating 'Open chat' button when a partner is selected but the drawer is closed.
    """
    _ensure_chat_css()

    # If you already know the partner (ids set) but the drawer is closed, show a small FAB
    has_partner = bool(
        st.session_state.get("chat_with_tenant_id") or
        st.session_state.get("chat_with_landlord_id")
    )

    # Floating open button (when partner known but drawer hidden)
    if has_partner and not st.session_state.get("chat_open"):
        with st.container():
            if st.button("💬 Open chat", key="chat_fab", help="Open chat", use_container_width=False):
                st.session_state["chat_open"] = True
                st.rerun()

    # Drawer itself
    if st.session_state.get("chat_open"):
        st.markdown('<div class="chat-docked">', unsafe_allow_html=True)
        # header bar with a close button
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown('<div class="head">💬 Chat</div>', unsafe_allow_html=True)
        with c2:
            if st.button("✖", key="chat_close_btn"):
                st.session_state["chat_open"] = False
                st.rerun()

        # body → reuse your existing chat renderer
        with st.container():
            st.markdown('<div class="chat-body">', unsafe_allow_html=True)
            chat_panel()  # << uses your existing chat logic
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
# ================================================================================


def help_icon(text: str, key: str | None = None):
    """
    Renders a tiny circular "?" with a custom tooltip.
    Use next to headers, buttons, inputs, etc.
    """
    # unique id is optional; useful if you later add JS/a11y hooks
    _ = key or f"help_{uuid.uuid4().hex[:8]}"
    st.markdown(
        f'''
        <span class="help-tip" tabindex="0" aria-label="{escape(text)}">?
          <span class="help-tip__bubble">{escape(text)}</span>
        </span>
        ''',
        unsafe_allow_html=True
    )


# ===== Future-Landlord Contacts / Connections (FLC) — CANONICAL =====

# Small helper (safe to redefine)
def _canon_email(email: str) -> str:
    return (email or "").strip().lower()


# ---------- Tenant -> add contact (insert-only; do NOT wipe flags) ----------
def add_future_landlord_contact(tenant_id: int, email: str) -> int:
    email = _canon_email(email)
    c = get_conn()
    row = c.execute(
        "SELECT id FROM future_landlord_contacts WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, email),
    ).fetchone()
    if row:
        return int(row[0])
    c.execute(
        "INSERT INTO future_landlord_contacts (tenant_id, email, created_at) "
        "VALUES (?, ?, datetime('now'))",
        (tenant_id, email),
    )
    c.commit()
    return int(c.execute("SELECT last_insert_rowid()").fetchone()[0])


def invite_future_landlord(tenant_id: int, email: str,
                           tenant_name: str | None = None,
                           tenant_email: str | None = None):
    email = _canon_email(email)
    c = get_conn()

    # mark invited on the tenant contact
    add_future_landlord_contact(tenant_id, email)
    c.execute(
        "UPDATE future_landlord_contacts "
        "SET invited=1, invited_at=datetime('now') "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, email),
    )
    c.commit()

    # if a landlord/agent user exists with that email → create/refresh a PENDING connection
    try:
        row = c.execute(
            "SELECT id, role FROM users WHERE LOWER(email)=LOWER(?) AND role IN ('landlord','agent') LIMIT 1",
            (email,),
        ).fetchone()
        if row:
            landlord_id = int(row[0])
            _upsert_connection(landlord_id, tenant_id, "pending")
    except Exception:
        pass

    # send email (as before)
    try:
        base = st.session_state.get("app_base_url") or (st.secrets.get("APP_BASE_URL") if hasattr(st, "secrets") else "")
        join_link = (base or "").strip().rstrip("/")
        subject = f"Πρόσκληση στο RentRight από τον/την {tenant_name or ''}".strip()
        body = (
            "Καλησπέρα σας,\n\n"
            f"Ο/Η {tenant_name or '—'} ({tenant_email or '—'}) σας πρόσθεσε ως μελλοντικό/ή ιδιοκτήτη/ιδιοκτήτρια στο RentRight.\n"
            "Με αυτόν τον τρόπο επιθυμεί να παραμείνετε σε επαφή για πιθανή μελλοντική μίσθωση.\n\n"
            "Τι μπορείτε να κάνετε:\n"
            "- Συνδεθείτε ή δημιουργήστε έναν λογαριασμό στο RentRight.\n\n"
            + (f"Σύνδεσμος πρόσβασης:\n{join_link}\n" if join_link else "")
        )
        if 'send_email_smtp' in globals():
            ok, msg = send_email_smtp(email, subject, body)
        else:
            ok, msg = True, "queued"
        return ok, msg
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"





# ---------- Tenant -> cancel their outbound invite ----------
def flc_cancel_invite(tenant_id: int, landlord_email: str) -> None:
    email = _canon_email(landlord_email)
    c = get_conn()
    c.execute(
        "UPDATE future_landlord_contacts SET invited=0, invited_at=NULL "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, email),
    )
    c.commit()


# ---------- Landlord -> request connect (sets inbound_request=1 on tenant's contact row) ----------
def flc_request_connect(landlord_id: int, tenant_id: int) -> None:
    c = get_conn()
    ll = get_user_by_id(landlord_id) or {}
    email = _canon_email(ll.get("email") or "")
    if not email:
        return
    # ensure contact exists for tenant
    add_future_landlord_contact(tenant_id, email)
    # set inbound_request
    c.execute(
        "UPDATE future_landlord_contacts "
        "SET inbound_request=1, inbound_requested_at=datetime('now') "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, email),
    )
    c.commit()


# ---------- Landlord -> cancel their outbound request ----------
def flc_cancel_request(landlord_id: int, tenant_id: int) -> None:
    c = get_conn()
    ll = get_user_by_id(landlord_id) or {}
    email = _canon_email(ll.get("email") or "")
    if not email:
        return
    c.execute(
        "UPDATE future_landlord_contacts "
        "SET inbound_request=0, inbound_requested_at=NULL "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, email),
    )
    c.commit()


# ---------- Final state helpers ----------
def flc_get_status(landlord_id: int, tenant_id: int) -> str | None:
    c = get_conn()
    row = c.execute(
        "SELECT status FROM future_landlord_connections WHERE landlord_id=? AND tenant_id=?",
        (landlord_id, tenant_id),
    ).fetchone()
    return (row[0] if row else None)


def _upsert_connection(landlord_id: int, tenant_id: int, status: str) -> None:
    c = get_conn()
    now = "datetime('now')"
    # try update, else insert
    cur = c.execute(
        "UPDATE future_landlord_connections "
        "SET status=?, updated_at=" + now + " "
        "WHERE landlord_id=? AND tenant_id=?",
        (status, landlord_id, tenant_id),
    )
    if cur.rowcount == 0:
        c.execute(
            "INSERT INTO future_landlord_connections "
            "(landlord_id, tenant_id, status, created_at, updated_at) "
            "VALUES (?, ?, ?, " + now + ", " + now + ")",
            (landlord_id, tenant_id, status),
        )
    c.commit()


def _clear_pending_flags(tenant_id: int, landlord_email: str) -> None:
    email = _canon_email(landlord_email)
    c = get_conn()
    c.execute(
        "UPDATE future_landlord_contacts "
        "SET invited=0, invited_at=NULL, inbound_request=0, inbound_requested_at=NULL "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, email),
    )
    c.commit()


def flc_connect(landlord_id: int, tenant_id: int) -> None:
    c = get_conn()
    ll = get_user_by_id(landlord_id) or {}
    email = _canon_email(ll.get("email") or "")
    _upsert_connection(landlord_id, tenant_id, "connected")
    if email:
        _clear_pending_flags(tenant_id, email)


def flc_reject(landlord_id: int, tenant_id: int) -> None:
    # Break the link entirely (no 'rejected' footprint)
    c = get_conn()
    ll = get_user_by_id(landlord_id) or {}
    email = _canon_email(ll.get("email") or "")
    c.execute(
        "DELETE FROM future_landlord_connections WHERE landlord_id=? AND tenant_id=?",
        (landlord_id, tenant_id),
    )
    c.commit()
    if email:
        _clear_pending_flags(tenant_id, email)



def flc_disconnect(landlord_id: int, tenant_id: int) -> None:
    flc_reject(landlord_id, tenant_id)


# ---------- Derived status for badges/UI ----------
def flc_relation_status(landlord_id: int, tenant_id: int, landlord_email: str | None = None) -> str:
    final = (flc_get_status(landlord_id, tenant_id) or "").lower()
    if final == "connected":
        return final
    # pending?
    email = _canon_email(landlord_email or (get_user_by_id(landlord_id) or {}).get("email") or "")
    if not email:
        return "disconnected"
    c = get_conn()
    row = c.execute(
        "SELECT invited, inbound_request FROM future_landlord_contacts "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, email),
    ).fetchone()
    if not row:
        return "disconnected"
    invited, inbound = row
    if invited:
        return "pending_inbound"
    if inbound:
        return "pending_outbound"
    return "disconnected"



# ---------- Lists ----------
def flc_list_inbound_for_tenant(tenant_id: int):
    # Landlords who requested this tenant (inbound_request=1)
    c = get_conn()
    return c.execute(
        "SELECT id, email, inbound_requested_at "
        "FROM future_landlord_contacts "
        "WHERE tenant_id=? AND inbound_request=1 "
        "ORDER BY inbound_requested_at DESC",
        (tenant_id,),
    ).fetchall()

def flc_list_prospective_for_landlord(landlord_id: int):
    """
    Tenants relevant to this landlord:
    - tenant invited this email (flc.invited=1) or landlord requested (flc.inbound_request=1), or
    - there is a connection record (connected or pending)
    """
    c = get_conn()
    ll = get_user_by_id(landlord_id) or {}
    email = _canon_email(ll.get("email") or "")
    if not email:
        return []

    return c.execute(
        """
        SELECT t.id AS tenant_id,
               t.name AS tenant_name,
               flc.invited,
               flc.inbound_request,
               flc.invited_at,
               x.status AS connection_status,
               x.updated_at
        FROM users t
        LEFT JOIN future_landlord_contacts flc
               ON flc.tenant_id = t.id
              AND LOWER(flc.email)=LOWER(?)
        LEFT JOIN future_landlord_connections x
               ON x.landlord_id = ?
              AND x.tenant_id   = t.id
        WHERE (COALESCE(flc.invited,0)=1
               OR COALESCE(flc.inbound_request,0)=1
               OR x.status IN ('connected','pending'))
        ORDER BY COALESCE(x.updated_at, flc.invited_at) DESC
        """,
        (email, landlord_id),
    ).fetchall()




# ---------- Chat gate ----------
def can_chat_landlord_tenant(landlord_id: int, tenant_id: int) -> bool:
    return (flc_get_status(landlord_id, tenant_id) or "").lower() == "connected"


# ---------- Simple probes used by UI ----------
def tenant_has_invited(tenant_id: int, landlord_email: str) -> bool:
    email = _canon_email(landlord_email)
    c = get_conn()
    row = c.execute(
        "SELECT 1 FROM future_landlord_contacts "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?) AND invited=1 LIMIT 1",
        (tenant_id, email),
    ).fetchone()
    return bool(row)


def has_inbound_request(tenant_id: int, landlord_email: str) -> bool:
    c = get_conn()
    # old DB guard
    if "_table_has_column" in globals():
        if not _table_has_column(c, "future_landlord_contacts", "inbound_request"):
            return False
    email = _canon_email(landlord_email)
    row = c.execute(
        "SELECT inbound_request FROM future_landlord_contacts "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, email),
    ).fetchone()
    return bool(row and row[0])
# ===== End FLC canonical block =====

# === Label & status helpers (i18n-friendly) ===

def _to_bool(v):
    """Convert DB values like 1/0, '1'/'0', 'true'/'false' to Python bool or None."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(int(v))
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"1", "true", "yes", "y", "t"}:
            return True
        if s in {"0", "false", "no", "n", "f"}:
            return False
        return None
    # Fallback: Python truthiness, but only for known-ish types
    try:
        return bool(v)
    except Exception:
        return None

def _yn(v):
    """Pretty-print Yes/No for booleans; handle None as '—'."""
    b = _to_bool(v)
    if b is None:
        return "—"
    return tr("Yes") if b else tr("No")


def _yn(val):
    if val is True:  return tr("Yes")
    if val is False: return tr("No")
    return "—"

def _truncate(txt, n=140):
    if not txt: return None
    if len(txt) <= n: return txt
    cut = txt[:n].rsplit(" ", 1)[0]
    return cut + "…"



# 3) One status→label mapper (keep raw DB values in English)
STATUS_LABELS = {
    None: "not requested",
    "pending": "Pending",
    "completed": "Completed",
    "cancelled": "Cancelled",
}

def display_status_label(status: str | None) -> str:
    key = (status or "").lower() if status else None
    return tr(STATUS_LABELS.get(key, "not requested"))

# 4) Bold markdown label without duplicating "**...**" keys in translations
def md_label(key_with_colon: str) -> str:
    # e.g., md_label('Status:') -> "**Κατάσταση:**" (when lang is Greek)
    return f"**{tr(key_with_colon)}**"

# === Top-right language switcher (flags only) ===
def render_topbar_language():
    c1, c2 = st.columns([8, 2])
    with c2:
        choice = st.selectbox(
            "🌐 Language",
            ["🇬🇧", "🇬🇷"],
            key="lang_flag",
            index=0 if st.session_state.get("lang","English")=="English" else 1,
            label_visibility="collapsed",
        )
        st.session_state["lang"] = "English" if choice == "🇬🇧" else "Ελληνικά"

            
# render_topbar_language()


# --- SMTP HELPERS integrados con st.secrets y session_state ------------------------------------------------
#-STARTS HERE------------------------------------------------------------------------------------------------
def load_smtp_defaults():
    """Prefill desde st.secrets a session_state (una sola vez por sesión)."""
    ss = st.session_state
    sec = st.secrets if hasattr(st, "secrets") else {}
    ss.setdefault("app_base_url", sec.get("APP_BASE_URL", ""))

    ss.setdefault("smtp_host", sec.get("SMTP_HOST", ""))
    ss.setdefault("smtp_port", int(sec.get("SMTP_PORT", 587)))
    ss.setdefault("smtp_user", sec.get("SMTP_USER", ""))
    ss.setdefault("smtp_pass", sec.get("SMTP_PASS", ""))
    ss.setdefault("smtp_from", sec.get("SMTP_FROM", ss.get("smtp_user", "")))
    ss.setdefault("smtp_tls", bool(sec.get("SMTP_TLS", True)))


def get_smtp_config():
    """Devuelve la config efectiva (session_state con fallback a secrets)."""
    sec = st.secrets if hasattr(st, "secrets") else {}
    host = st.session_state.get("smtp_host") or sec.get("SMTP_HOST", "")
    port = int(st.session_state.get("smtp_port") or sec.get("SMTP_PORT", 587))
    user = st.session_state.get("smtp_user") or sec.get("SMTP_USER", "")
    pwd  = st.session_state.get("smtp_pass") or sec.get("SMTP_PASS", "")
    from_email = st.session_state.get("smtp_from") or sec.get("SMTP_FROM", user)
    use_tls = st.session_state.get("smtp_tls")
    if use_tls is None:
        use_tls = bool(sec.get("SMTP_TLS", True))
    return host, port, user, pwd, from_email, bool(use_tls)


def send_email_smtp(to_email: str, subject: str, body: str):
    """Envía correo por SMTP con STARTTLS (587). Usa secretos si existen."""
    host, port, user, pwd, from_email, use_tls = get_smtp_config()

    if not all([host, port, user, pwd, from_email, to_email]):
        return False, "Missing SMTP details: host, port, username, password, sender, or recipient."

    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        server = smtplib.SMTP(host, int(port), timeout=15)
        if use_tls:
            server.starttls()
        server.login(user, pwd)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        return True, "sent"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    
#-FINISH HERE------------------------------------------------------------------------------------------------

    
def get_latest_reference_for_pair(tenant_id: int, prev_landlord_id: int):
    cur = get_conn().cursor()
    cur.execute(
        """
        SELECT token, status, created_at
        FROM reference_requests
        WHERE tenant_id=? AND prev_landlord_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (tenant_id, prev_landlord_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {"token": row[0], "status": row[1], "created_at": row[2]}

HERE = Path(__file__).parent
CLOUD_DIRS = [Path("/mount/data"), Path("/mnt/data")]
WRITABLE_BASE = next((p for p in CLOUD_DIRS if p.exists()), HERE)
WRITABLE_BASE.mkdir(parents=True, exist_ok=True)

DB_PATH   = WRITABLE_BASE / "app.db"
SEED_PATH = HERE / "app_seed.db"   # ← your file name

# Optional: force reseed once by setting FORCE_SEED=1 in env/secrets
if os.environ.get("FORCE_SEED") == "1" and DB_PATH.exists():
    DB_PATH.unlink()

# Copy seed on cold start (or if file is 0 bytes)
if (not DB_PATH.exists() or DB_PATH.stat().st_size == 0) and SEED_PATH.exists():
    shutil.copyfile(SEED_PATH, DB_PATH)
    print(f"💾 Copied {SEED_PATH.name} → {DB_PATH}")

UPLOAD_DIR = WRITABLE_BASE / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------- Tenant Documents (upload/verify) ----------
DOC_TYPES = {
    "payslip": "Τελευταίες Μισθοδοσίες",
    "tax_return": "Εκκαθαριστικό Εφορίας",
    "employment_contract": "Σύμβαση Εργασίας",
}

DOC_UPLOAD_SUBDIR = UPLOAD_DIR / "tenant_docs"
DOC_UPLOAD_SUBDIR.mkdir(parents=True, exist_ok=True)

def td_save_upload(tenant_id: int, doc_type: str, uploaded_file):
    assert doc_type in DOC_TYPES, "Invalid document type"
    allowed = {"pdf", "png", "jpg", "jpeg", "webp"}
    name = uploaded_file.name or f"{doc_type}.pdf"
    ext = (name.rsplit(".",1)[-1] if "." in name else "pdf").lower()
    if ext not in allowed:
        raise ValueError("Μη υποστηριζόμενη κατάληξη αρχείου (επιτρεπτά: pdf, png, jpg, jpeg, webp).")
    raw = uploaded_file.read()
    size = len(raw)
    sha = sha256_bytes(raw)
    ciphertext = encrypt_bytes(raw)

    token = uuid4().hex
    safe_name = f"t{tenant_id}_{doc_type}_{token}.{ext}"
    fpath = DOC_UPLOAD_SUBDIR / safe_name
    with open(fpath, "wb") as f:
        f.write(ciphertext)

    now = datetime.utcnow().isoformat(timespec="seconds")
    get_conn().execute("""
        INSERT INTO tenant_documents
            (tenant_id, doc_type, filename, content_type, path, size_bytes, sha256, status, uploaded_at, status_updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (tenant_id, doc_type, name, uploaded_file.type or f"application/{ext}", str(fpath), size, sha, "pending", now, now))
    get_conn().commit()

def td_list_for_tenant(tenant_id: int):
    cur = get_conn().execute("""
        SELECT id, doc_type, filename, status, uploaded_at, status_updated_at
        FROM tenant_documents
        WHERE tenant_id=? ORDER BY uploaded_at DESC
    """, (tenant_id,))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

def td_list_pending():
    cur = get_conn().execute("""
        SELECT td.id, td.tenant_id, u.name, u.email, td.doc_type, td.filename, td.uploaded_at
        FROM tenant_documents td
        JOIN users u ON u.id=td.tenant_id
        WHERE td.status='pending'
        ORDER BY td.uploaded_at ASC
    """)
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

def td_list_by_status(status: str | None):
    """
    Admin view: return docs filtered by status.
    status in {'pending','verified','rejected'} or None for all.
    """
    c = get_conn()
    if status in ("pending", "verified", "rejected"):
        sql = """
        SELECT td.id, td.tenant_id, u.name, u.email, td.doc_type, td.filename,
               td.status, td.uploaded_at, td.status_updated_at
        FROM tenant_documents td
        JOIN users u ON u.id=td.tenant_id
        WHERE td.status = ?
        ORDER BY td.uploaded_at DESC
        """
        return c.execute(sql, (status,)).fetchall()
    else:
        sql = """
        SELECT td.id, td.tenant_id, u.name, u.email, td.doc_type, td.filename,
               td.status, td.uploaded_at, td.status_updated_at
        FROM tenant_documents td
        JOIN users u ON u.id=td.tenant_id
        ORDER BY td.uploaded_at DESC
        """
        return c.execute(sql).fetchall()


def td_set_status(doc_id: int, status: str, admin_id: int):
    assert status in ("pending","verified","rejected")
    now = datetime.utcnow().isoformat(timespec="seconds")
    get_conn().execute("""
        UPDATE tenant_documents
           SET status=?, status_updated_at=?, status_by=?
         WHERE id=?
    """, (status, now, admin_id, doc_id))
    get_conn().commit()

def td_read_bytes(doc_id: int):
    row = get_conn().execute("SELECT path FROM tenant_documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        return None
    path = Path(row[0])
    if not path.exists():
        return None
    data = path.read_bytes()
    try:
        return decrypt_bytes(data) or data
    except Exception:
        return data
    
def td_delete(doc_id: int, tenant_id: int) -> tuple[bool, str]:
    """
    Delete a tenant document the user owns:
      - removes the encrypted blob (if exists)
      - deletes DB row
    Returns (ok, message).
    """
    c = get_conn()
    row = c.execute(
        "SELECT path, filename FROM tenant_documents WHERE id=? AND tenant_id=?",
        (doc_id, tenant_id),
    ).fetchone()

    if not row:
        return False, "Not found or not owned by you."

    path, filename = row
    try:
        if path:
            p = Path(path)
            if p.exists():
                p.unlink(missing_ok=True)
    except Exception as e:
        # We still try to delete the DB row even if file removal fails
        pass

    try:
        c.execute("DELETE FROM tenant_documents WHERE id=? AND tenant_id=?", (doc_id, tenant_id))
        c.commit()
        return True, f"Deleted {filename or 'file'}."
    except Exception as e:
        return False, f"Delete failed: {e}"


def td_verified_map(tenant_id: int):
    rows = get_conn().execute("""
        SELECT doc_type, MAX(CASE WHEN status='verified' THEN 1 ELSE 0 END) AS v
        FROM tenant_documents
        WHERE tenant_id=?
        GROUP BY doc_type
    """, (tenant_id,)).fetchall()
    out = {k: False for k in DOC_TYPES.keys()}
    for doc_type, v in rows:
        out[doc_type] = bool(v)
    return out


# (Optional sanity check)
try:
    for p in (WRITABLE_BASE, UPLOAD_DIR):
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        try:
            # Python 3.8+: missing_ok is fine; otherwise guard with exists()
            probe.unlink(missing_ok=True)
        except TypeError:
            if probe.exists():
                probe.unlink()
except Exception as e:
    # Make sure you have: import streamlit as st
    st.error(f"Base directory not writable: {WRITABLE_BASE}\n{e}")



# ---------- Utilities ----------
@st.cache_resource
def get_conn():
    # one shared connection per process/session (cache this with st.cache_resource if you like)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row  

    # Try WAL, but gracefully fall back if the FS doesn't support it
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        # Fallback for network/readonly-ish mounts
        conn.execute("PRAGMA journal_mode=DELETE;")

    # Reasonable defaults for stability
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")  # wait up to 5s if locked
    return conn

# ---- Schema helpers & safe migrations (tenant_profiles) -----------------------


def ensure_tenant_profile_schema():
    """
    Add missing columns used by the tenant profile UI to tenant_profiles.

    Fixes OperationalError: no such column: age on older DBs.
    Columns ensured:
      - age INTEGER
      - monthly_salary INTEGER
      - marital_status TEXT
      - job_position TEXT
      - contract_type TEXT
      - pets INTEGER DEFAULT 0
      - num_tenants INTEGER DEFAULT 1
      - about TEXT
    """
    conn = get_conn()
    try:
        cur = conn.execute("PRAGMA table_info(tenant_profiles)")
        cols = {row[1] for row in cur.fetchall()}
    except Exception:
        # If table doesn't exist yet, nothing to alter (it will be created later)
        return

    alters = []
    if "age" not in cols:
        alters.append("ALTER TABLE tenant_profiles ADD COLUMN age INTEGER")
    if "monthly_salary" not in cols:
        alters.append("ALTER TABLE tenant_profiles ADD COLUMN monthly_salary INTEGER")
    if "marital_status" not in cols:
        alters.append("ALTER TABLE tenant_profiles ADD COLUMN marital_status TEXT")
    if "job_position" not in cols:
        alters.append("ALTER TABLE tenant_profiles ADD COLUMN job_position TEXT")
    if "contract_type" not in cols:
        alters.append("ALTER TABLE tenant_profiles ADD COLUMN contract_type TEXT")
    if "pets" not in cols:
        alters.append("ALTER TABLE tenant_profiles ADD COLUMN pets INTEGER DEFAULT 0")
    if "num_tenants" not in cols:
        alters.append("ALTER TABLE tenant_profiles ADD COLUMN num_tenants INTEGER DEFAULT 1")
    if "about" not in cols:
        alters.append("ALTER TABLE tenant_profiles ADD COLUMN about TEXT")

    for ddl in alters:
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            # Ignore benign races / already added
            pass

    if alters:
        conn.commit()

# Run once at import time so downstream queries don't crash
try:
    ensure_tenant_profile_schema()
except Exception:
    # Non-fatal: don't block the app if something unexpected happens
    pass


@st.cache_resource
def ensure_contracts_consent_column(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(reference_contracts)")
    cols = [r[1] for r in cur.fetchall()]
    if "consent_status" not in cols:
        cur.execute("ALTER TABLE reference_contracts ADD COLUMN consent_status TEXT NOT NULL DEFAULT 'locked'")
        conn.commit()
        

def _now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")

    


def _user_display_name_column() -> str:
    # Detect whether users has 'full_name' or 'name'
    cols = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    return "full_name" if "full_name" in cols else "name"

def flc_list_connected(landlord_id: int):
    name_col = _user_display_name_column()
    sql = f"""
        SELECT u.id, u.{name_col} AS display_name, u.email
        FROM future_landlord_connections c
        JOIN users u ON u.id = c.tenant_id
        WHERE c.landlord_id = ? AND c.status='connected'
        ORDER BY u.{name_col} COLLATE NOCASE
    """
    return conn.execute(sql, (landlord_id,)).fetchall()


def search_people_by_name_or_email(q: str, roles: tuple[str, ...] = ("landlord","agent","tenant"), limit: int = 25):
    """
    Búsqueda parcial por nombre o email, para múltiples roles.
    Devuelve filas: (id, name, email, role)
    """
    q = (q or "").strip()
    if not q:
        return []
    tokens = [t for t in re.split(r"\s+", q) if t]
    if not tokens:
        return []

    c = get_conn()
    conds = []
    params = []
    for t in tokens:
        like = f"%{t.lower()}%"
        conds.append("(LOWER(COALESCE(name,'')) LIKE ? OR LOWER(email) LIKE ?)")
        params.extend([like, like])

    roles_placeholders = ",".join("?" * len(roles))
    params_roles = list(roles)

    sql = f"""
        SELECT id, COALESCE(name, '') AS name, email, role
        FROM users
        WHERE role IN ({roles_placeholders})
          AND {" AND ".join(conds)}
        ORDER BY 
          (CASE WHEN COALESCE(name,'')='' THEN 1 ELSE 0 END),
          LOWER(COALESCE(name,email))
        LIMIT ?
    """
    params = params_roles + params + [limit]
    return c.execute(sql, params).fetchall() or []

def search_landlords_by_name_or_email(q: str, limit: int = 25):
    """
    Partial, case-insensitive search over landlords by name or email.
    Returns rows: (landlord_id, name, email)
    """
    q = (q or "").strip()
    if not q:
        return []
    tokens = [t for t in re.split(r"\s+", q) if t]
    if not tokens:
        return []

    c = get_conn()
    # one LIKE pair (name OR email) per token; AND them together
    conds = []
    params = []
    for t in tokens:
        like = f"%{t.lower()}%"
        conds.append("(LOWER(COALESCE(name,'')) LIKE ? OR LOWER(email) LIKE ?)")
        params.extend([like, like])

    sql = f"""
        SELECT id, COALESCE(name, '') AS name, email, role
        FROM users
        WHERE role IN ('landlord','agent') AND {" AND ".join(conds)}
        ORDER BY (CASE WHEN COALESCE(name,'')='' THEN 1 ELSE 0 END),
                 LOWER(COALESCE(name,email))
        LIMIT ?
    """
    params.append(limit)
    return c.execute(sql, params).fetchall() or []


def _rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


# ----- Φόρτωμα & ευρετήρια από ellada.json -----
# --- Greece location pickers (Region → Regional Unit → Municipality) ---ad_ellada():
    """
    Return structure:
    {
      "Region Name": {
          "Regional Unit Name": ["Municipality 1", "Municipality 2", ...],
          ...
      },
      ...
    }
    """
    import json, os
    # Adjust this path if your file lives elsewhere
    candidate_paths = [
        "ellada.json",
        "data/ellada.json",
        "assets/ellada.json",
        "static/ellada.json",
        os.path.join(os.path.dirname(__file__), "ellada.json"),
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
            break
    else:
        # Fallback: empty structure -> UI will gracefully degrade
        raw = {}

    # Normalize to Region -> Regional Unit -> [Municipalities]
    # Accepts either already-nested format or flat records with keys:
    #   region, regional_unit, municipality
    if isinstance(raw, dict) and raw:
        return raw

    regions = {}
    if isinstance(raw, list):
        for row in raw:
            reg = (row.get("region") or "").strip()
            ru  = (row.get("regional_unit") or "").strip()
            mun = (row.get("municipality") or "").strip()
            if not reg or not ru or not mun:
                continue
            regions.setdefault(reg, {}).setdefault(ru, [])
            if mun not in regions[reg][ru]:
                regions[reg][ru].append(mun)
    return regions


def greece_location_pickers(prefix: str = "otr", only: str | None = None,
                            parent_region: str | None = None,
                            parent_ru: str | None = None):
    """
    Renders 1 or 3 linked selectboxes:
      Περιφέρεια -> Περιφερειακή Ενότητα -> Δήμος (Πόλη)
    If only=None (default): renders all 3 and returns (region, regional_unit, municipality).
    If only='region': renders region selector only and returns region.
    If only='regional_unit': renders RU selector only and returns regional_unit.
    If only='municipality': renders municipality selector only and returns municipality.

    You can pass parent_region / parent_ru if you call RU or municipality pickers separately.
    """
    data, regions, _ = load_ellada_index("ellada.json")

    # Region ---------------------------------------------------------
    if only in (None, "region"):
        region_options = [tr("Any")] + (regions or [])
        region = st.selectbox(tr("Region"), options=region_options, key=f"{prefix}_region")
        region = None if region == tr("Any") else region
    else:
        # if we’re not showing region now, use the parent passed in
        region = parent_region

    # Regional unit --------------------------------------------------
    if only in (None, "regional_unit"):
        units = list_units(data, region) if region else []
        unit_options = [tr("Any")] + (units or [])
        regional_unit = st.selectbox(tr("Regional unit"), options=unit_options, key=f"{prefix}_ru")
        regional_unit = None if regional_unit == tr("Any") else regional_unit
    else:
        regional_unit = parent_ru

    # Municipality ---------------------------------------------------
    if only in (None, "municipality"):
        munis = list_municipalities(data, region, regional_unit) if (region and regional_unit) else []
        mun_options = [tr("Any")] + (munis or [])
        municipality = st.selectbox(tr("Municipality"), options=mun_options, key=f"{prefix}_mun")
        municipality = None if municipality == tr("Any") else municipality
    else:
        municipality = None

    if only == "region":
        return region
    if only == "regional_unit":
        return regional_unit
    if only == "municipality":
        return municipality
    return region, regional_unit, municipality



@st.cache_data(ttl=86400, show_spinner=False)
def load_ellada_index(json_path: str | None = None):
    """
    Load Region -> Peripheral Unit -> Municipalities from ellada.json.
    Tries common repo paths, handles BOM, validates structure,
    and falls back to a file_uploader if not found / invalid.
    Returns: (data, regions, muni_to_loc)
    """
    here = Path(__file__).parent
    candidates: list[Path] = []

    # 1) explicit arg (preferred)
    if json_path:
        candidates.append(Path(json_path))

    # 2) optional path from secrets
    try:
        secret_path = st.secrets.get("ELLADA_JSON_PATH", "")
        if secret_path:
            candidates.append(Path(secret_path))
    except Exception:
        pass

    # 3) typical repo locations
    candidates += [
        here / "data" / "ellada.json",
        here / "ellada.json",
        Path.cwd() / "data" / "ellada.json",
        Path.cwd() / "ellada.json",
        Path("/mnt/data/ellada.json"),  # last resort cache
    ]

    last_error = None
    data = None

    # Try each candidate; read with utf-8-sig to swallow BOM if present
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                break
            except JSONDecodeError as e:
                last_error = f"JSON parse error in {p}: {e}"
                continue
            except Exception as e:
                last_error = f"Error reading {p}: {e}"
                continue

    # Uploader fallback if not found / not parsed
    if data is None:
        uploaded = st.file_uploader("Ανεβάστε το ellada.json", type=["json"], key="ellada_upload")
        if not uploaded:
            msg = "Δεν βρέθηκε/διαβάστηκε το ellada.json."
            if last_error:
                msg += " " + last_error
            st.error(msg)
            st.stop()
        try:
            data = json.load(uploaded)
            # persist a copy so next rerun finds it
            try:
                Path("/mnt/data").mkdir(parents=True, exist_ok=True)
                with open("/mnt/data/ellada.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
            except Exception:
                pass
        except JSONDecodeError as e:
            st.error(f"Το αρχείο που ανεβάσατε δεν είναι έγκυρο JSON: {e}")
            st.stop()

    # Validate structure
    if not isinstance(data, dict) or "Περιφέρειες" not in data or not isinstance(data["Περιφέρειες"], list):
        st.error("Το ellada.json δεν έχει την αναμενόμενη δομή (χρειάζεται κλειδί 'Περιφέρειες' ως λίστα).")
        st.stop()

    regions = []
    muni_to_loc = {}  # Δήμος -> (Περιφέρεια, Π.Ε.)
    for reg in data.get("Περιφέρειες", []):
        if not isinstance(reg, dict):
            continue
        rname = reg.get("όνομα")
        units = reg.get("Περιφερειακές Ενότητες") or {}
        if not rname or not isinstance(units, dict):
            continue
        regions.append(rname)
        for unit_name, municipalities in units.items():
            if not isinstance(municipalities, list):
                continue
            for m in municipalities:
                if isinstance(m, str):
                    muni_to_loc[m] = (rname, unit_name)

    regions.sort(key=lambda s: s.casefold())

    if not regions:
        st.error("Το ellada.json φορτώθηκε, αλλά δεν βρέθηκαν Περιφέρειες με Δήμους.")
        st.stop()

    return data, regions, muni_to_loc

def list_units(data, region_name: str):
    for reg in data.get("Περιφέρειες", []):
        if reg.get("όνομα") == region_name:
            units = list((reg.get("Περιφερειακές Ενότητες") or {}).keys())
            units.sort(key=lambda s: s.casefold())
            return units
    return []

def list_municipalities(data, region_name: str, unit_name: str):
    for reg in data.get("Περιφέρειες", []):
        if reg.get("όνομα") == region_name:
            munis = (reg.get("Περιφερειακές Ενότητες") or {}).get(unit_name, []) or []
            munis = sorted(munis, key=lambda s: s.casefold())
            return munis
    return []

def format_dt(value, tz="Europe/Athens") -> str:
    """Return dd/mm/yyyy HH:MM in local time, robust to strings/naive dt."""
    if not value:
        return "—"
    # Parse
    if isinstance(value, str):
        v = value.strip()
        try:
            v = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(v)
        except Exception:
            # Fallbacks: trim microseconds/T if any
            v2 = v.split(".")[0].replace("T", " ")
            try:
                dt = datetime.strptime(v2, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return v2  # last resort: show cleaned string
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
    else:
        dt = value

    # Assume UTC if naive, then convert to target tz
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(ZoneInfo(tz))
    return local.strftime("%d/%m/%Y")

def add_column_if_missing(conn, table: str, col_def: str):
    """
    Add a column to `table` if missing.
    col_def example: "emailed_at TEXT" or "consent_status TEXT NOT NULL DEFAULT 'locked'"
    """
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    col_name = col_def.split()[0]
    if col_name not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        conn.commit()

def run_migrations(conn):
    """
    Run all DB migrations idempotently.
    Ensures all expected columns/tables exist on every run.
    """
    cur = conn.cursor()

    # 1) Τρέξε τη migration των εγγράφων ενοικιαστή (δεν μπλοκάρουμε αν αποτύχει)
    try:
        run_tenant_docs_migration(conn)
    except Exception as e:
        try:
            import streamlit as st
            st.warning(f"DB migration warning (tenant docs): {e}")
        except Exception:
            print(f"DB migration warning (tenant docs): {e}")

    # 2) Helper για προσθήκη στήλης αν λείπει
    def _add_column_if_missing(_conn, table, column_def):
        c = _conn.cursor()
        colname = column_def.split()[0]
        c.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in c.fetchall()}
        if colname not in existing:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
            _
    # --- Role CHECK migration to include 'agent' (SQLite workaround) ---
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        ddl = (row[0] or "") if row else ""
        if '"agent"' not in ddl and "'agent'" not in ddl:
            conn.execute("PRAGMA foreign_keys=off;")
            conn.execute("""
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT CHECK(role IN ("tenant","landlord","admin","agent")) NOT NULL,
                    created_at TEXT NOT NULL,
                    phone TEXT,
                    phone_visible INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                INSERT INTO users_new(id,email,name,password_hash,role,created_at,phone,phone_visible)
                SELECT id,email,name,password_hash,role,created_at,phone,phone_visible FROM users
            """)
            conn.execute("DROP TABLE users;")
            conn.execute("ALTER TABLE users_new RENAME TO users;")
            conn.execute("PRAGMA foreign_keys=on;")
    except Exception:
        pass

    # Ensure agent_profiles exists (idempotent)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_profiles (
            user_id INTEGER UNIQUE NOT NULL,
            agency_name TEXT NOT NULL,
            afm TEXT NOT NULL,
            amk TEXT,
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()

    add_col = globals().get("add_column_if_missing", _add_column_if_missing)

    # 3) Reference request fixes
    add_col(conn, "reference_requests", "emailed_at TEXT")
    add_col(conn, "reference_requests", "revoked_at TEXT")
    add_col(conn, "reference_requests", "revoked_by TEXT")
    add_col(conn, "reference_requests", "revoked_reason TEXT")

    # 4) Tenant profile columns (open-to-rent prefs)
    for col_def in [
        "open_to_rent INTEGER NOT NULL DEFAULT 0",
        "search_region TEXT",
        "search_city TEXT",
        "search_city_osm_id INTEGER",
        "search_city_osm_type TEXT",
        "search_district TEXT",
        "search_district_osm_id INTEGER",
        "search_district_osm_type TEXT",
        "size_min INTEGER",
        "size_max INTEGER",
        "rooms_min INTEGER",
        "rooms_max INTEGER",
        "floor_min INTEGER",
        "floor_max INTEGER",
        "price_min INTEGER",
        "price_max INTEGER",
    ]:
        add_col(conn, "tenant_profiles", col_def)

    # 5) **ΝΕΟ**: flags για αιτήματα από ιδιοκτήτη (landlord-origin)
    add_col(conn, "future_landlord_contacts", "inbound_request INTEGER NOT NULL DEFAULT 0")
    add_col(conn, "future_landlord_contacts", "inbound_requested_at TEXT")

    # 6) **ΝΕΟ**: πίνακας συνδέσεων landlord-tenant (για status & chat)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS future_landlord_connections (
            landlord_id INTEGER NOT NULL,
            tenant_id   INTEGER NOT NULL,
            status      TEXT NOT NULL DEFAULT 'connected' CHECK(status IN ('connected','rejected')),
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            PRIMARY KEY (landlord_id, tenant_id),
            FOREIGN KEY (landlord_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (tenant_id)   REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_flc_landlord ON future_landlord_connections(landlord_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_flc_tenant   ON future_landlord_connections(tenant_id)")
    
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            landlord_id INTEGER NOT NULL,
            address TEXT NOT NULL,
            listing_url TEXT,
            visible_to_tenants INTEGER NOT NULL DEFAULT 0,
            region TEXT,
            district TEXT,
            city TEXT,
            size_m2 INTEGER,
            rooms INTEGER,
            floor INTEGER,
            price INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (landlord_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lp_landlord ON landlord_properties(landlord_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lp_visible ON landlord_properties(visible_to_tenants)")

    conn.commit()


    return True



def run_chat_migrations(conn):
    cur = conn.cursor()

    # 1 thread per landlord-tenant pair
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_threads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        landlord_id INTEGER NOT NULL,
        tenant_id   INTEGER NOT NULL,
        created_at  TEXT NOT NULL,
        UNIQUE(landlord_id, tenant_id),
        FOREIGN KEY (landlord_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (tenant_id)   REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_threads_l_t ON chat_threads(landlord_id, tenant_id)")

    # messages
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id  INTEGER NOT NULL,
        sender_id  INTEGER NOT NULL,
        body       TEXT NOT NULL,
        created_at TEXT NOT NULL,
        read_at    TEXT,
        FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE,
        FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_thread ON chat_messages(thread_id, id)")
    conn.commit()


def init_db():
    conn = get_conn()
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT CHECK(role IN ("tenant","landlord","admin","agent")) NOT NULL,
            created_at TEXT NOT NULL,
            phone TEXT,
            phone_visible INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenant_profiles (
            tenant_id INTEGER UNIQUE NOT NULL,
            future_landlord_email TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_profiles (
            user_id INTEGER UNIQUE NOT NULL,
            agency_name TEXT NOT NULL,
            afm TEXT NOT NULL,
            amk TEXT,
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS previous_landlords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            afm TEXT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reference_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            tenant_id INTEGER NOT NULL,
            prev_landlord_id INTEGER NOT NULL,
            landlord_email TEXT NOT NULL,
            created_at TEXT NOT NULL,
            emailed_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            filled_at TEXT,
            confirm_landlord INTEGER,
            score INTEGER,
            paid_on_time INTEGER,
            utilities_unpaid INTEGER,
            good_condition INTEGER,
            comments TEXT,
            FOREIGN KEY (tenant_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (prev_landlord_id) REFERENCES previous_landlords(id) ON DELETE CASCADE
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reference_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            tenant_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            content_type TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','verified','rejected')),
            status_updated_at TEXT,
            status_by TEXT,
            uploaded_at TEXT NOT NULL,
            consent_status TEXT NOT NULL DEFAULT 'locked', 
            FOREIGN KEY (tenant_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (token) REFERENCES reference_requests(token) ON DELETE CASCADE
        )
    """)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS future_landlord_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL,
            invited INTEGER NOT NULL DEFAULT 0,
            invited_at TEXT,
            UNIQUE(tenant_id, email),
            FOREIGN KEY (tenant_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


    conn.commit()
    return conn

def can_chat_landlord_landlord(l1: int, l2: int) -> bool:
    a, b = _lp_canon(l1, l2)
    row = get_conn().execute(
        "SELECT 1 FROM landlord_peers WHERE a_landlord_id=? AND b_landlord_id=? AND status='connected'",
        (a, b)
    ).fetchone()
    return bool(row)


# --- Tenant Documents: schema migration -------------------------------------------
def run_tenant_docs_migration(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS tenant_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL CHECK (doc_type IN ('payslip','tax_return','employment_contract')),
        filename TEXT NOT NULL,
        content_type TEXT NOT NULL,
        path TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        sha256 TEXT,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','verified','rejected')),
        status_updated_at TEXT,
        status_by INTEGER,
        uploaded_at TEXT NOT NULL,
        FOREIGN KEY (tenant_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_td_tenant ON tenant_documents(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_td_status ON tenant_documents(status)")
    conn.commit()


conn = init_db()

# Run lightweight migrations so old DBs gain new columns
try:
    run_migrations(conn)
except Exception as e:
    st.warning(f"DB migration warning: {e}")
    
try:
    run_chat_migrations(conn)
except Exception as e:
    st.warning(f"Chat migration warning: {e}")



def _table_has_column(conn_or_none, table: str, column: str) -> bool:
    c = conn_or_none or get_conn()
    cur = c.execute(f"PRAGMA table_info({table})")
    return any(row[1].lower() == column.lower() for row in cur.fetchall())

    
#===============================================================================================================================================
# chat helpers
#===============================================================================================================================================


def can_chat(landlord_id: int, tenant_id: int) -> bool:
    lid, tid = _thread_canon_pair(landlord_id, tenant_id)

    uL = get_user_by_id(lid) or {}
    uT = get_user_by_id(tid) or {}
    rL = (uL.get("role") or "").lower()
    rT = (uT.get("role") or "").lower()

    # NEW: landlord/agent ↔ landlord/agent via landlord_peers
    if rL in ("landlord","agent") and rT in ("landlord","agent"):
        return can_chat_landlord_landlord(lid, tid)  # uses landlord_peers
    # existing:
    try:
        if flc_get_status(lid, tid) == "connected":
            return True
    except Exception:
        pass
    if rL == "tenant" and rT == "tenant":
        try:
            return (tp_get_status(lid, tid) or "").lower() == "connected"
        except Exception:
            return False
    return False


def get_or_create_thread(landlord_id: int, tenant_id: int) -> int | None:
    lid, tid = _thread_canon_pair(landlord_id, tenant_id)
    if not can_chat(lid, tid):
        return None
    c = get_conn()
    row = c.execute(
        "SELECT id FROM chat_threads WHERE landlord_id=? AND tenant_id=?",
        (lid, tid)
    ).fetchone()
    if row:
        return row[0]
    c.execute(
        "INSERT INTO chat_threads(landlord_id, tenant_id, created_at) VALUES (?,?,datetime('now'))",
        (lid, tid)
    )
    c.commit()
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def list_messages(thread_id: int, limit: int = 200):
    c = get_conn()
    rows = c.execute(
        "SELECT id, sender_id, body, created_at, read_at FROM chat_messages "
        "WHERE thread_id=? ORDER BY id DESC LIMIT ?",
        (thread_id, limit)
    ).fetchall()
    return rows[::-1]  # oldest→newest

def post_message(thread_id: int, sender_id: int, body: str):
    body = (body or "").strip()
    if not body:
        return
    c = get_conn()
    c.execute(
        "INSERT INTO chat_messages(thread_id, sender_id, body, created_at) VALUES (?,?,?,datetime('now'))",
        (thread_id, sender_id, body)
    )
    c.commit()
    
def get_thread_by_id(thread_id: int):
    """Return chat_threads row joined with both users."""
    c = get_conn()
    row = c.execute("""
        SELECT ct.id, ct.landlord_id, ct.tenant_id,
               lu.name  AS landlord_name, lu.email AS landlord_email,
               tu.name  AS tenant_name,   tu.email AS tenant_email
        FROM chat_threads ct
        JOIN users lu ON lu.id = ct.landlord_id
        JOIN users tu ON tu.id = ct.tenant_id
        WHERE ct.id = ?
    """, (thread_id,)).fetchone()
    return row

def list_threads_for_user(user_id: int, role: str):
    c = get_conn()
    if role in ("landlord","agent"):
        rows = c.execute("""
            SELECT ct.id, ct.landlord_id, ct.tenant_id,
                   CASE WHEN ct.landlord_id = ? THEN u2.name  ELSE u1.name  END AS partner_name,
                   CASE WHEN ct.landlord_id = ? THEN u2.email ELSE u1.email END AS partner_email
            FROM chat_threads ct
            JOIN users u1 ON u1.id = ct.landlord_id
            JOIN users u2 ON u2.id = ct.tenant_id
            WHERE ct.landlord_id = ? OR ct.tenant_id = ?
            ORDER BY ct.id DESC
        """, (user_id, user_id, user_id, user_id)).fetchall()
        return rows or []
    # tenant branch unchanged



def _initials_safe(name: str | None, email: str | None) -> str:
    base = (name or "").strip() or (email or "").split("@")[0]
    parts = [p for p in (base or "").replace(".", " ").split() if p]
    if len(parts) >= 2: return (parts[0][0] + parts[1][0]).upper()
    if parts: return parts[0][:2].upper()
    return "?"

def _thread_canon_pair(a: int, b: int) -> tuple[int, int]:
    uA = get_user_by_id(a) or {}
    uB = get_user_by_id(b) or {}
    rA = (uA.get("role") or "").lower()
    rB = (uB.get("role") or "").lower()

    # canonicalize tenant↔tenant (already existed)
    if rA == "tenant" and rB == "tenant":
        return (a, b) if a < b else (b, a)
    # NEW: canonicalize landlord/agent ↔ landlord/agent
    if rA in ("landlord","agent") and rB in ("landlord","agent"):
        return (a, b) if a < b else (b, a)
    # landlord↔tenant stays as given
    return (a, b)


def get_thread_id_if_exists(landlord_id: int, tenant_id: int) -> int | None:
    lid, tid = _thread_canon_pair(landlord_id, tenant_id)
    c = get_conn()
    row = c.execute(
        "SELECT id FROM chat_threads WHERE landlord_id=? AND tenant_id=?",
        (lid, tid)
    ).fetchone()
    return row[0] if row else None

def get_unread_count(thread_id: int, reader_id: int) -> int:
    if not thread_id:
        return 0
    c = get_conn()
    row = c.execute(
        "SELECT COUNT(*) FROM chat_messages "
        "WHERE thread_id=? AND sender_id<>? AND read_at IS NULL",
        (thread_id, reader_id)
    ).fetchone()
    return int(row[0] or 0)

def mark_thread_read(thread_id: int, reader_id: int):
    if not thread_id:
        return
    c = get_conn()
    c.execute(
        "UPDATE chat_messages SET read_at=datetime('now') "
        "WHERE thread_id=? AND sender_id<>? AND read_at IS NULL",
        (thread_id, reader_id)
    )
    c.commit()


@st.cache_resource
def _load_avatar_font():
    # Try a bundled font; fall back to default
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except Exception:
        return ImageFont.load_default()

def _avatar_image_from_initials(initials: str, size: int = 48,
                                bg: str = "#EEF2FF", fg: str = "#1F2937") -> io.BytesIO:
    """Return a PNG image (BytesIO) of a circular avatar with initials."""
    initials = (initials or "?")[:2].upper()
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # circle background
    draw.ellipse([0, 0, size - 1, size - 1], fill=bg)

    # text
    font = _load_avatar_font()
    # textbbox is more accurate than textsize when available
    try:
        bbox = draw.textbbox((0, 0), initials, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = draw.textsize(initials, font=font)

    tx = (size - tw) / 2
    ty = (size - th) / 2 - 1
    draw.text((tx, ty), initials, font=font, fill=fg)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _initials(name: str | None, email: str | None) -> str:
    base = (name or "").strip() or (email or "").split("@")[0]
    parts = [p for p in (base or "").replace(".", " ").split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return "?"

def row_get(row, key, default=None):
    """Works for dict and sqlite3.Row."""
    try:
        return row.get(key, default)  # dict-like
    except AttributeError:
        try:
            return row[key]           # sqlite3.Row
        except Exception:
            return default
        
def row_get_any(row, keys: tuple[str, ...], default=None):
    for k in keys:
        try:
            v = row[k]
            if v is not None:
                return v
        except Exception:
            pass
    return default

def chat_panel(key_ns: str = "chat"):
    if not st.session_state.get("chat_open"):
        return

    me = st.session_state.get("user") or {}
    role = (st.session_state.get("chat_role") or "").strip().lower()

    landlord_id, tenant_id = None, None
    partner_user = None

    # ------------------- Determine partner IDs for tenant / landlord-tenant chat -------------------
    if role == "tenant":
        tenant_id = me.get("id")
        landlord_id = st.session_state.get("chat_with_landlord_id")
        if landlord_id:
            partner_user = get_user_by_id(landlord_id)
    elif role in ("landlord", "agent"):
        landlord_id = me.get("id")
        tenant_id = st.session_state.get("chat_with_tenant_id")
        if tenant_id:
            partner_user = get_user_by_id(tenant_id)

    # ------------------- Handle peer chat (tenant↔tenant or landlord/agent↔landlord/agent) -------------------
    peer_mode = st.session_state.get("chat_peer_mode")
    selected = st.session_state.get("selected_thread")
    thread_id = None

    if peer_mode in {"t2t", "lp"}:
        # get other user id safely
        other = None
        if selected:
            try:
                a_str, b_str = str(selected).split("-", 1)
                a = int(a_str)
                b = int(b_str)
                other = b if a == me.get("id") else a
            except Exception:
                other = None

        # fallback if selected_thread is empty but we know who we’re chatting with
        if not other:
            other = (
                st.session_state.get("chat_with_landlord_id")
                or st.session_state.get("chat_with_tenant_id")
            )

        if other:
            try:
                if peer_mode == "t2t":
                    ok = (tp_get_status(me.get("id"), other) or "").lower() == "connected"
                elif peer_mode == "lp":
                    ok = (lp_get_status(me.get("id"), other) or "").lower() == "connected"
                else:
                    ok = True
            except Exception:
                ok = True

            if not ok:
                st.warning(tr("Chat is available only after you connect."))
                return

            thread_id = get_or_create_thread(me.get("id"), other)
            partner_user = get_user_by_id(other)

    # ------------------- Fallback: landlord ↔ tenant chat -------------------
    if thread_id is None and landlord_id and tenant_id:
        if not can_chat(int(landlord_id), int(tenant_id)):
            st.warning(tr("Chat is available only after you connect."))
            return
        thread_id = get_or_create_thread(int(landlord_id), int(tenant_id))
        partner_user = partner_user or get_user_by_id(
            tenant_id if role in ("landlord", "agent") else landlord_id
        )

    if not thread_id:
        st.warning(tr("Chat unavailable."))
        return

    # ------------------- Header -------------------
    partner_name = ((partner_user or {}).get("name") or "").strip()
    partner_email = ((partner_user or {}).get("email") or "").strip()
    partner_display = partner_name or partner_email or tr("Unknown")

    my_initials = _initials(me.get("name"), me.get("email"))
    partner_initials = _initials(partner_name, partner_email)
    my_avatar_img = _avatar_image_from_initials(my_initials)
    partner_avatar_img = _avatar_image_from_initials(partner_initials)

    c1, c2 = st.columns([8, 2])
    with c1:
        st.subheader(f"💬 {tr('Chat with')} {partner_display}")


    # ------------------- Messages -------------------
    try:
        msgs = list_messages(thread_id, limit=200) or []
    except Exception:
        msgs = []

    for m in msgs:
        sender_id = row_get(m, "sender_id", 0)
        body = row_get(m, "body", "")
        created = row_get(m, "created_at", "")
        is_me = int(sender_id or 0) == int(me.get("id") or 0)
        avatar_img = my_avatar_img if is_me else partner_avatar_img

        with st.chat_message("user", avatar=avatar_img):
            st.markdown(body or "")
            if created:
                st.caption(created)

    # ------------------- Input -------------------
    text = st.chat_input(placeholder=tr("Type a message…"), key=f"{key_ns}:input")
    if text is not None:
        post_message(thread_id, me.get("id"), text)
        st.rerun()




#-------finish------------------------------------------------------------------------------------------------------------


def _tp_now():
    return datetime.utcnow().isoformat(timespec="seconds")

def _tp_canon(t1: int, t2: int):
    return (t1, t2) if t1 < t2 else (t2, t1)

def tp_get_row(t1: int, t2: int):
    if not (t1 and t2 and t1 != t2):
        return None
    a, b = _tp_canon(t1, t2)
    row = get_conn().execute(
        "SELECT a_tenant_id, b_tenant_id, status, initiator_id, created_at, updated_at "
        "FROM tenant_peers WHERE a_tenant_id=? AND b_tenant_id=?",
        (a, b)
    ).fetchone()
    if not row:
        return None
    keys = ["a_tenant_id","b_tenant_id","status","initiator_id","created_at","updated_at"]
    return dict(zip(keys, row))

# >>> ADD after _tp_now, _tp_canon, tp_get_row <<<

def tp_request(inviter_id: int, invitee_id: int):
    """Create or refresh a pending roommate request between two tenants."""
    if not (inviter_id and invitee_id) or inviter_id == invitee_id:
        return
    a, b = _tp_canon(inviter_id, invitee_id)
    now = _tp_now()
    c = get_conn()
    row = c.execute(
        "SELECT status FROM tenant_peers WHERE a_tenant_id=? AND b_tenant_id=?",
        (a, b)
    ).fetchone()
    if row:
        # Don't overwrite a connected link; re-open only if rejected
        if (row[0] or "").lower() in ("rejected", "pending"):
            c.execute(
                "UPDATE tenant_peers SET status='pending', initiator_id=?, updated_at=? "
                "WHERE a_tenant_id=? AND b_tenant_id=?",
                (inviter_id, now, a, b)
            )
    else:
        c.execute(
            "INSERT INTO tenant_peers (a_tenant_id, b_tenant_id, status, initiator_id, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (a, b, "pending", inviter_id, now, now)
        )
    c.commit()


def tp_accept(my_id: int, other_id: int):
    a, b = _tp_canon(my_id, other_id)
    c = get_conn()
    c.execute(
        "UPDATE tenant_peers SET status='connected', updated_at=? WHERE a_tenant_id=? AND b_tenant_id=?",
        (_tp_now(), a, b),
    )
    c.commit()


def tp_reject(my_id: int, other_id: int):
    a, b = _tp_canon(my_id, other_id)
    c = get_conn()
    c.execute(
        "UPDATE tenant_peers SET status='rejected', updated_at=? WHERE a_tenant_id=? AND b_tenant_id=?",
        (_tp_now(), a, b),
    )
    c.commit()


def tp_list_for_tenant(my_id: int):
    """
    Returns a list of dicts describing roommate links relevant to `my_id`.
    Each row includes: other_id, other_name, other_email, status, initiator_id, updated_at.
    """
    c = get_conn()
    rows = c.execute(
        """
        SELECT 
          CASE WHEN a_tenant_id=? THEN b_tenant_id ELSE a_tenant_id END AS other_id,
          status, initiator_id, created_at, updated_at
        FROM tenant_peers
        WHERE a_tenant_id=? OR b_tenant_id=?
        ORDER BY updated_at DESC, created_at DESC
        """,
        (my_id, my_id, my_id),
    ).fetchall()

    out = []
    for other_id, status, initiator_id, created_at, updated_at in rows:
        u = get_user_by_id(other_id) or {}
        out.append({
            "other_id": other_id,
            "other_name": (u.get("name") or "").strip(),
            "other_email": (u.get("email") or "").strip(),
            "status": (status or "").lower(),
            "initiator_id": initiator_id,
            "updated_at": updated_at,
        })
    return out


def tp_get_status(t1: int, t2: int) -> str | None:
    r = tp_get_row(t1, t2)
    return r["status"] if r else None

def tp_request_connect(requester_id: int, target_id: int):
    if requester_id == target_id:
        return
    a, b = _tp_canon(requester_id, target_id)
    now = _tp_now()
    c = get_conn()
    existing = tp_get_row(requester_id, target_id)
    if existing:
        # If rejected, allow re-request; if pending/connected, just refresh
        new_status = "pending" if existing["status"] in ("rejected",) else existing["status"]
        c.execute("""
            UPDATE tenant_peers
               SET status=?, initiator_id=?, updated_at=?
             WHERE a_tenant_id=? AND b_tenant_id=?
        """, (new_status, requester_id, now, a, b))
    else:
        c.execute("""
            INSERT INTO tenant_peers (a_tenant_id, b_tenant_id, status, initiator_id, created_at, updated_at)
            VALUES (?,?,?,?,?,?)
        """, (a, b, "pending", requester_id, now, now))
    c.commit()



def tp_disconnect(current_tenant_id: int, other_tenant_id: int):
    # store as rejected so it won't show as connected anymore
    tp_reject(current_tenant_id, other_tenant_id)



# ---------- Auth helpers ----------------------------------------------------------------------------------------------------------
def hash_password(password: str, salt: str = "static_salt_change_me") -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()

def create_user(email: str, name: str, password: str, role: str, *, phone: str | None = None, phone_visible: int = 0):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users(email, name, password_hash, role, created_at, phone, phone_visible) VALUES (?,?,?,?,?,?,?)",
        (
            email.lower().strip(),
            name.strip(),
            hash_password(password),
            role,
            datetime.utcnow().isoformat(),
            phone,
            int(bool(phone_visible)),
        ),
    )
    conn.commit()



def get_user_by_email(email: str):
    cur = conn.cursor()
    cur.execute("SELECT id, email, name, password_hash, role, phone, phone_visible FROM users WHERE email = ?", (email.lower().strip(),))
    row = cur.fetchone()
    if row:
        keys = ["id","email","name","password_hash","role","phone","phone_visible"]
        return dict(zip(keys, row))
    return None


# Starts here


def ensure_tenant_peers_schema():
    c = get_conn()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tenant_peers (
            a_tenant_id INTEGER NOT NULL,
            b_tenant_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending','connected','rejected')),
            initiator_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (a_tenant_id, b_tenant_id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_tenant_peers_status ON tenant_peers(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tenant_peers_initiator ON tenant_peers(initiator_id)")
    c.commit()

# call it once at import
try:
    ensure_tenant_peers_schema()
except Exception:
    pass

#==============================================================================
#NEW fix flows
def ensure_landlord_peers_schema():
    c = get_conn()
    c.execute("""
        CREATE TABLE IF NOT EXISTS landlord_peers (
            a_landlord_id INTEGER NOT NULL,
            b_landlord_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending','connected','rejected')),
            initiator_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (a_landlord_id, b_landlord_id),
            FOREIGN KEY (a_landlord_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (b_landlord_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_lp_status ON landlord_peers(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_lp_initiator ON landlord_peers(initiator_id)")
    c.commit()

def _lp_now():
    return datetime.utcnow().isoformat(timespec="seconds")

def _lp_canon(l1: int, l2: int):
    return (l1, l2) if l1 < l2 else (l2, l1)

def lp_get_row(l1: int, l2: int):
    if not (l1 and l2) or l1 == l2:
        return None
    a, b = _lp_canon(l1, l2)
    row = get_conn().execute(
        "SELECT a_landlord_id, b_landlord_id, status, initiator_id, created_at, updated_at "
        "FROM landlord_peers WHERE a_landlord_id=? AND b_landlord_id=?",
        (a, b)
    ).fetchone()
    if not row:
        return None
    k = ["a_landlord_id","b_landlord_id","status","initiator_id","created_at","updated_at"]
    return dict(zip(k, row))

def lp_get_status(l1: int, l2: int) -> str | None:
    r = lp_get_row(l1, l2)
    return (r or {}).get("status")

def lp_request(inviter_id: int, invitee_id: int):
    if inviter_id == invitee_id:
        return
    a, b = _lp_canon(inviter_id, invitee_id)
    now = _lp_now()
    c = get_conn()
    row = c.execute("SELECT status FROM landlord_peers WHERE a_landlord_id=? AND b_landlord_id=?", (a, b)).fetchone()
    if row:
        new_status = "pending" if (row[0] or "").lower() in ("rejected","pending") else row[0]
        c.execute(
            "UPDATE landlord_peers SET status=?, initiator_id=?, updated_at=? WHERE a_landlord_id=? AND b_landlord_id=?",
            (new_status, inviter_id, now, a, b)
        )
    else:
        c.execute(
            "INSERT INTO landlord_peers (a_landlord_id, b_landlord_id, status, initiator_id, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (a, b, "pending", inviter_id, now, now)
        )
    c.commit()

def lp_accept(my_id: int, other_id: int):
    a, b = _lp_canon(my_id, other_id)
    get_conn().execute(
        "UPDATE landlord_peers SET status='connected', updated_at=? WHERE a_landlord_id=? AND b_landlord_id=? AND status='pending'",
        (_lp_now(), a, b)
    ).connection.commit()

def lp_reject(my_id: int, other_id: int):
    a, b = _lp_canon(my_id, other_id)
    get_conn().execute(
        "UPDATE landlord_peers SET status='rejected', updated_at=? WHERE a_landlord_id=? AND b_landlord_id=?",
        (_lp_now(), a, b)
    ).connection.commit()

def lp_disconnect(my_id: int, other_id: int):
    lp_reject(my_id, other_id)

# call it once at import
try:
    ensure_landlord_peers_schema()
except Exception:
    pass

def lp_list_peers_for_landlord(my_id: int, statuses=("pending","connected")):
    """
    Return [(other_id, status, initiator_id, updated_at)...] for my landlord/agent network.
    """
    c = get_conn()
    q = """
        SELECT
            CASE WHEN a_landlord_id=? THEN b_landlord_id ELSE a_landlord_id END AS other_id,
            status, initiator_id, updated_at
        FROM landlord_peers
        WHERE (a_landlord_id=? OR b_landlord_id=?)
          AND status IN ({})
        ORDER BY updated_at DESC
    """.format(",".join("?"*len(statuses)))
    rows = c.execute(q, (my_id, my_id, my_id, *statuses)).fetchall()
    return rows or []


# ends here========================================================================================================

def ensure_tenant_profile_row(tenant_id: int):
    """Make sure tenant_profiles has a row for this tenant."""
    cur = conn.cursor()
    row = cur.execute("SELECT tenant_id FROM tenant_profiles WHERE tenant_id=?", (tenant_id,)).fetchone()
    if not row:
        cur.execute(
            "INSERT INTO tenant_profiles(tenant_id, future_landlord_email, updated_at) VALUES (?,?,?)",
            (tenant_id, None, datetime.utcnow().isoformat()),
        )
        conn.commit()
        
        
def ensure_contacts_schema():
    """
    Generic user<->user contacts table for any role combinations.
    One canonical row (a_user_id < b_user_id) per pair.
    status: 'none' | 'pending' | 'connected' | 'rejected'
    initiator_id set when status='pending'
    """
    c = get_conn()
    c.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            a_user_id INTEGER NOT NULL,
            b_user_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('none','pending','connected','rejected')),
            initiator_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (a_user_id, b_user_id),
            FOREIGN KEY (a_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (b_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status)")
    c.commit()

        
def load_open_to_rent_prefs(tenant_id: int) -> dict:
    ensure_tenant_profile_row(tenant_id)
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT open_to_rent,
               search_city, search_city_osm_id, search_city_osm_type,
               search_district, search_district_osm_id, search_district_osm_type,
               size_min, size_max, rooms_min, rooms_max,
               floor_min, floor_max, price_min, price_max, updated_at
        FROM tenant_profiles WHERE tenant_id=?
        """,
        (tenant_id,),
    ).fetchone()
    keys = [
        "open_to_rent",
        "search_city", "search_city_osm_id", "search_city_osm_type",
        "search_district", "search_district_osm_id", "search_district_osm_type",
        "size_min", "size_max", "rooms_min", "rooms_max",
        "floor_min", "floor_max", "price_min", "price_max", "updated_at",
    ]
    return dict(zip(keys, row)) if row else {}

def save_open_to_rent_prefs(
    tenant_id: int,
    open_to_rent: bool,
    city: str | None,
    district: str | None,
    size_min: int | None, size_max: int | None,
    rooms_min: int | None, rooms_max: int | None,
    floor_min: int | None, floor_max: int | None,
    price_min: int | None, price_max: int | None,
    # OSM metadata
    city_osm_id: int | None = None,
    city_osm_type: str | None = None,
    district_osm_id: int | None = None,
    district_osm_type: str | None = None,
    # NEW:
    region: str | None = None,
):
    ensure_tenant_profile_row(tenant_id)
    now = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE tenant_profiles
           SET open_to_rent=?,
               search_region=?,
               search_city=?, search_city_osm_id=?, search_city_osm_type=?,
               search_district=?, search_district_osm_id=?, search_district_osm_type=?,
               size_min=?, size_max=?,
               rooms_min=?, rooms_max=?,
               floor_min=?, floor_max=?,
               price_min=?, price_max=?,
               updated_at=?
         WHERE tenant_id=?
        """,
        (
            1 if open_to_rent else 0,
            (region or "").strip() or None,
            (city or "").strip() or None, city_osm_id, (city_osm_type or None),
            (district or "").strip() or None, district_osm_id, (district_osm_type or None),
            size_min, size_max,
            rooms_min, rooms_max,
            floor_min, floor_max,
            price_min, price_max,
            now, tenant_id
        ),
    )
    conn.commit()


    
def load_profile_details(tenant_id: int) -> dict:
    c = get_conn()
    # ensure a row exists so SELECT never fails
    c.execute("""
        INSERT INTO tenant_profiles (tenant_id, updated_at)
        VALUES (?, datetime('now'))
        ON CONFLICT(tenant_id) DO NOTHING
    """, (tenant_id,))
    row = c.execute("""
        SELECT age, monthly_salary, marital_status, job_position,
               contract_type, pets, num_tenants, about
        FROM tenant_profiles WHERE tenant_id=?
    """, (tenant_id,)).fetchone()
    return dict(row) if row else {}


def save_profile_details(tenant_id: int, **data):
    c = get_conn()
    c.execute("""
        INSERT INTO tenant_profiles (tenant_id, updated_at)
        VALUES (?, datetime('now'))
        ON CONFLICT(tenant_id) DO NOTHING
    """, (tenant_id,))

    fields, params = [], []
    for k in ("age","monthly_salary","marital_status","job_position",
              "contract_type","pets","num_tenants","about"):
        if k in data:
            fields.append(f"{k}=?")
            params.append(data[k])

    if fields:
        params.append(tenant_id)
        c.execute(f"""
            UPDATE tenant_profiles
               SET {", ".join(fields)}, updated_at=datetime('now')
             WHERE tenant_id=?
        """, params)
    c.commit()



# properties helpers
# Start here-------------------------------------------------------
def _norm_url(u: str | None) -> str | None:
    if not u: 
        return None
    u = u.strip()
    if not u:
        return None
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    return u

def _none_if_blank_num(x):
    # Treat "", None, 0 as None for optional numeric fields
    if x in (None, ""):
        return None
    try:
        xi = int(x)
        return xi if xi != 0 else None
    except Exception:
        return None

def lp_add_property(
    landlord_id: int,
    address: str,
    listing_url: str | None,
    visible: bool,
    region: str | None = None,
    district: str | None = None,
    city: str | None = None,
    size_m2: int | None = None,
    rooms: int | None = None,
    floor: int | None = None,
    price: int | None = None,
) -> int:
    c = get_conn()
    now = _now_iso()
    listing_url = _norm_url(listing_url)
    vis = 1 if visible else 0
    size_m2 = _none_if_blank_num(size_m2)
    rooms   = _none_if_blank_num(rooms)
    floor   = _none_if_blank_num(floor)
    price   = _none_if_blank_num(price)
    cur = c.execute(
        """
        INSERT INTO landlord_properties
        (landlord_id, address, listing_url, visible_to_tenants,
         region, district, city, size_m2, rooms, floor, price,
         created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            landlord_id, address.strip(), listing_url, vis,
            (region or None), (district or None), (city or None),
            size_m2, rooms, floor, price,
            now, now,
        ),
    )
    c.commit()
    return cur.lastrowid

def lp_list_properties(landlord_id: int):
    c = get_conn()
    rows = c.execute(
        """
        SELECT id, address, listing_url, visible_to_tenants,
               created_at, updated_at,
               region, district, city, size_m2, rooms, floor, price
        FROM landlord_properties
        WHERE landlord_id = ?
        ORDER BY updated_at DESC, id DESC
        """,
        (landlord_id,),
    ).fetchall()
    return rows or []

def lp_update_property(
    prop_id: int,
    landlord_id: int,
    address: str,
    listing_url: str | None,
    visible: bool,
    region: str | None,
    district: str | None,
    city: str | None,
    size_m2: int | None,
    rooms: int | None,
    floor: int | None,
    price: int | None,
):
    c = get_conn()
    now = _now_iso()
    listing_url = _norm_url(listing_url)
    vis = 1 if visible else 0
    size_m2 = _none_if_blank_num(size_m2)
    rooms   = _none_if_blank_num(rooms)
    floor   = _none_if_blank_num(floor)
    price   = _none_if_blank_num(price)
    c.execute(
        """
        UPDATE landlord_properties
        SET address=?, listing_url=?, visible_to_tenants=?,
            region=?, district=?, city=?, size_m2=?, rooms=?, floor=?, price=?,
            updated_at=?
        WHERE id=? AND landlord_id=?
        """,
        (
            address.strip(), listing_url, vis,
            (region or None), (district or None), (city or None),
            size_m2, rooms, floor, price,
            now, prop_id, landlord_id,
        ),
    )
    c.commit()

def lp_toggle_visibility(prop_id: int, landlord_id: int, visible: bool):
    c = get_conn()
    now = _now_iso()
    vis = 1 if visible else 0
    c.execute(
        """
        UPDATE landlord_properties
        SET visible_to_tenants=?, updated_at=?
        WHERE id=? AND landlord_id=?
        """,
        (vis, now, prop_id, landlord_id),
    )
    c.commit()

def lp_delete_property(prop_id: int, landlord_id: int):
    c = get_conn()
    c.execute("DELETE FROM landlord_properties WHERE id=? AND landlord_id=?", (prop_id, landlord_id))
    c.commit()


def _url_domain(u: str | None) -> str | None:
    if not u:
        return None
    try:
        return u.split("://", 1)[-1].split("/", 1)[0]
    except Exception:
        return u
    
def lp_list_visible_properties(landlord_id: int):
    """Visible properties for a landlord (address + listing + location/specs)."""
    c = get_conn()
    rows = c.execute(
        """
        SELECT id, address, listing_url, updated_at,
               region, district, city, size_m2, rooms, floor, price
        FROM landlord_properties
        WHERE landlord_id = ? AND visible_to_tenants = 1
        ORDER BY updated_at DESC, id DESC
        """,
        (landlord_id,),
    ).fetchall()
    return rows or []

#finish here ---------------------------------------------------------------------
def search_landlords_by_property_location(
    region: str | None = None,
    regional_unit: str | None = None,
    municipality: str | None = None,
    size_min: int | None = None, size_max: int | None = None,
    rooms_min: int | None = None, rooms_max: int | None = None,
    floor_min: int | None = None, floor_max: int | None = None,
    price_min: int | None = None, price_max: int | None = None,
    limit: int = 50,
):
    """
    Find landlords that have at least one VISIBLE property matching the filters.
    Returns rows of matching properties with landlord info:
      (prop_id, landlord_id, landlord_name, landlord_email,
       address, listing_url, region, regional_unit, municipality,
       size_m2, rooms, floor, price, updated_at)
    """
    c = get_conn()
    sql = """
    SELECT
      lp.id            AS prop_id,
      u.id             AS landlord_id,
      COALESCE(u.name,'') AS landlord_name,
      u.email          AS landlord_email,
      lp.address, lp.listing_url,
      lp.region       AS region,
      lp.district     AS regional_unit,   -- DB column 'district' == Regional Unit
      lp.city         AS municipality,    -- DB column 'city'     == Municipality
      lp.size_m2, lp.rooms, lp.floor, lp.price,
      lp.updated_at
    FROM landlord_properties lp
    JOIN users u ON u.id = lp.landlord_id AND u.role IN ('landlord','agent')
    WHERE lp.visible_to_tenants = 1
      AND (? IS NULL OR lp.region   = ?)
      AND (? IS NULL OR lp.district = ?)
      AND (? IS NULL OR lp.city     = ?)
      AND (? IS NULL OR lp.size_m2 >= ?)
      AND (? IS NULL OR lp.size_m2 <= ?)
      AND (? IS NULL OR lp.rooms    >= ?)
      AND (? IS NULL OR lp.rooms    <= ?)
      AND (? IS NULL OR lp.floor    >= ?)
      AND (? IS NULL OR lp.floor    <= ?)
      AND (? IS NULL OR lp.price    >= ?)
      AND (? IS NULL OR lp.price    <= ?)
    ORDER BY lp.updated_at DESC, lp.id DESC
    LIMIT ?
    """
    params = [
        region,  region,
        regional_unit, regional_unit,
        municipality,  municipality,
        size_min, size_min,
        size_max, size_max,
        rooms_min, rooms_min,
        rooms_max, rooms_max,
        floor_min, floor_min,
        floor_max, floor_max,
        price_min, price_min,
        price_max, price_max,
        limit,
    ]
    return c.execute(sql, params).fetchall() or []

 
def storage_delete(storage_key: str):
    # Replace with S3/GCS delete if you use cloud storage
    if storage_key and os.path.isfile(storage_key):
        try:
            os.remove(storage_key)
        except Exception:
            pass  # log if needed

def delete_contract_hard(token: str):
    c = get_contract_by_token(token)
    if not c:
        return
    storage_key = c.get("storage_key") or c.get("path")
    storage_delete(storage_key)
    conn.execute("DELETE FROM reference_contracts WHERE token=?", (token,))
    conn.commit()

def _table_exists(name: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return bool(row)

def delete_landlord_responses(token: str):
    """
    Deletes any responses the landlord submitted for this token.
    Tries multiple common table/column patterns safely.
    """
    # Prefer token-keyed tables
    token_tables = ["reference_responses", "reference_form_responses", "reference_submissions"]
    for t in token_tables:
        if _table_exists(t):
            try:
                conn.execute(f"DELETE FROM {t} WHERE token=?", (token,))
            except Exception:
                pass

    # Also attempt request_id-keyed tables if present
    req_row = conn.execute("SELECT id FROM reference_requests WHERE token=?", (token,)).fetchone()
    if req_row:
        request_id = req_row[0]
        id_tables = ["reference_answers", "reference_responses", "reference_submissions"]
        for t in id_tables:
            if _table_exists(t):
                try:
                    conn.execute(f"DELETE FROM {t} WHERE request_id=?", (request_id,))
                except Exception:
                    pass
    conn.commit()





def get_user_by_id(uid: int):
    cur = conn.cursor()
    cur.execute("SELECT id, email, name, role FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if row:
        keys = ["id","email","name","role"]
        return dict(zip(keys, row))
    return None
def ensure_admin_exists():
    """Create admin user if missing."""
    admin = get_user_by_email("admin@gmail.com")
    if not admin:
        # name can be anything; password '123' as requested
        create_user("admin@gmail.com", "Admin", "123", "admin")
        
ensure_admin_exists()

# ---------- Validation ----------

def is_valid_email(s: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s or "") is not None


def is_valid_afm(s: str) -> bool:
    return bool(re.fullmatch(r"\d{9}", (s or "").strip()))


def role_icon(role: str) -> str:
    if role == "agent":
        return "🏢"
    if role == "landlord":
        return "🔑"
    if role == "tenant":
        return "🤷‍♀️"
    return ""

# ---------- Auth UI ----------

def login_form():
    st.subheader(tr('Sign In'))
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input(tr('Email'))
        password = st.text_input(tr('Password'), type="password")
        submitted = st.form_submit_button(tr('Sign In'))

    if not submitted:
        return

    user = get_user_by_email(email)
    if not user or user["password_hash"] != hash_password(password):
        st.error(tr('Incorrect email or password. Please try again.'))
        return  # don't st.stop()

    # success → set session and rerun immediately (no sleep)
    st.session_state.user = {k: user[k] for k in ["id","email","name","role"]}
    st.session_state["just_logged_in"] = True
    st.rerun()


def signup_form():
    st.subheader(tr('Create Account'))
    with st.form("signup_form"):
        name = st.text_input(tr('Full name'))
        email = st.text_input(tr('Email'))
        phone = st.text_input(tr('Phone (optional)'), placeholder="+3069XXXXXXXX")
        phone_visible = st.checkbox(tr('Show phone to others?'), value=False)
        role = st.selectbox(tr('Role'), ["tenant","landlord","agent"], format_func=lambda x: x.capitalize())
        # Extra fields for Agent verification (Greek market)
        agency_name = afm = amk = None
        if role == "agent":
            st.markdown(f"### {tr('Real Estate Agent verification')}")
            agency_name = st.text_input(tr("Agency / Business name"))
            afm = st.text_input(tr("AFM (9 digits)"))
            amk = st.text_input(tr("AMK / Registry (optional)"), placeholder="π.χ. ΑΜΚ / Μητρώο")
        password = st.text_input(tr('Password'), type="password")
        password2 = st.text_input(tr('Confirm password'), type="password")
        submitted = st.form_submit_button(tr('Create Account'))
    if submitted:
        if not name.strip():
            st.error(tr('Please enter your full name.'))
            return
        if not is_valid_email(email):
            st.error(tr('Please enter a valid email address.'))
            return
            # NEW: basic phone validation (optional field)
        if phone and not re.match(r"^\+?[0-9]{7,15}$", phone.strip()):
            st.error(tr('Enter a valid phone number.'))
            return
        if password != password2:
            st.error(tr('Passwords do not match. Please try again.'))
            return
        if get_user_by_email(email):
            st.error(tr('This email is already registered.'))
            return
                # Agent-specific validation
        if role == "agent":
            try:
                conn = get_conn()
                u = get_user_by_email(email)
                if u:
                    conn.execute(
                        "INSERT OR REPLACE INTO agent_profiles(user_id, agency_name, afm, amk, verified, created_at) VALUES (?,?,?,?,0,?)",
                        (u["id"], (agency_name or "").strip(), (afm or "").strip(), (amk or "").strip(), datetime.utcnow().isoformat())
                    )
                    conn.commit()
            except Exception:
                st.warning("Agent profile saved with limited details.")

        if role == "agent":
            if not (agency_name or "").strip():
                st.error(tr('Please enter your agency / business name.'))
                return
            if not is_valid_afm(afm):
                st.error(tr('Please enter a valid AFM (9 digits).'))
                return
        create_user(email, name, password, role, phone=phone.strip() or None, phone_visible=1 if phone_visible else 0)
        st.success(tr('Your account has been created. Please sign in to continue.'))
        # 🔁 redirect back to landing/login
        st.session_state.signup_done = True
        st.rerun()

        
def auth_gate():
    if "user" not in st.session_state:
        st.session_state.user = None

    # If user just signed up, show a one-time success + only the Login form
    if st.session_state.get("signup_done"):
        st.success(tr('Your account has been created — please sign in.'))
        login_form()
        # reset so it doesn't persist across reruns
        st.session_state.signup_done = False
        return

    # Default: both tabs
    tab1, tab2 = st.tabs([tr('Sign In'),tr('Create Account')])
    with tab1:
        login_form()
    with tab2:
        signup_form()



def logout_button():
    if st.button("➜]", help=tr("Sign Out")):  # removed the stray ']'
        # Clear sensitive session state
        for key in ["user", "auth_token", "roles", "permissions", "logout_confirm"]:
            st.session_state.pop(key, None)
        st.rerun()

  
    
   
def open_chat_unified(*, viewer_role: str, me_id: int, other_id: int, other_role: str | None = None, other_name: str | None = None):
    st.session_state["chat_open"] = True
    st.session_state["selected_thread"] = f"{me_id}-{other_id}"
    st.session_state["chat_role"] = "landlord" if viewer_role in ("landlord","agent") else "tenant"

    if viewer_role in ("landlord","agent") and other_role == "tenant":
        st.session_state["chat_with_landlord_id"] = me_id
        st.session_state["chat_with_tenant_id"] = other_id
        st.session_state["chat_peer_mode"] = "flc"
    elif viewer_role == "tenant" and other_role in ("landlord","agent"):
        st.session_state["chat_with_landlord_id"] = other_id
        st.session_state["chat_with_tenant_id"] = me_id
        st.session_state["chat_peer_mode"] = "flc"
    elif viewer_role == "tenant" and (other_role or "tenant") == "tenant":
        st.session_state["chat_with_landlord_id"] = other_id
        st.session_state["chat_with_tenant_id"] = me_id
        st.session_state["chat_peer_mode"] = "t2t"
    else:
        st.session_state["chat_with_landlord_id"] = other_id
        st.session_state["chat_with_tenant_id"] = me_id
        st.session_state["chat_peer_mode"] = "lp"

    try:
        tid = get_or_create_thread(me_id, other_id)
        if tid:
            mark_thread_read(tid, me_id)
    except Exception:
        pass

    st.rerun()
        
        
        
def render_flc_actions(
    *,
    viewer_role: str,                 # "tenant" | "landlord" | "agent"
    landlord_id: int,
    tenant_id: int,
    parent=None,                      # e.g., a Streamlit column; defaults to st
    key_ns: str = "flc",
    # Tenant-side flags (only used when viewer_role == "tenant")
    tenant_other_email: str | None = None,
    tenant_in_contacts: bool = False,  # you already compute this in search
    # Visibility toggles (defaults: safe for search)
    show_add_contact: bool = True,     # tenant: show "Add contact"
    show_request: bool = True,         # LL/Agent: "Request"
    show_accept: bool = True,          # LL/Agent: when pending_inbound
    show_reject: bool = True,          # LL/Agent: when pending_inbound
    show_cancel: bool = True,          # LL/Agent: when pending_outbound
    show_disconnect: bool = False,     # LL/Agent: when connected (usually hide in search)
    show_status_caption: bool = True,
    labels: dict | None = None,
) -> str:
    """
    Flexible actions for the Landlord/Agent ↔ Tenant relationship.
    Returns relation: 'connected' | 'pending_inbound' | 'pending_outbound' | 'disconnected'
    """
    container = parent or st

    _L = {
        "add_contact": tr("Add contact"),
        "request": tr("Request"),
        "accept": tr("Accept"),
        "reject": tr("Reject"),
        "cancel": tr("Cancel request"),
        "disconnect": tr("Disconnect"),
        "cap_connected": tr("Connected"),
        "cap_inbound": tr("Pending (inbound)"),
        "cap_outbound": tr("Pending (outbound)"),
        "cap_none": tr("No relation"),
        "added": tr("Contact added."),
        "sent": tr("Request sent."),
        "ok": tr("Connected."),
        "rej": tr("Rejected."),
        "cxl": tr("Cancelled."),
        "disc": tr("Disconnected."),
        "cant_add": tr("Can’t add contact"),
    }
    if labels: _L.update(labels)

    def kk(sfx: str) -> str:
        return f"{key_ns}:{sfx}:{landlord_id}:{tenant_id}"

    # Handlers
    def _refresh(msg=None, info=False):
        try: st.cache_data.clear()
        except Exception: pass
        if msg: (st.info if info else st.success)(msg)
        st.rerun()

    def _do_request():
        flc_request_connect(landlord_id, tenant_id); _refresh(_L["sent"])

    def _do_accept():
        flc_connect(landlord_id, tenant_id); _refresh(_L["ok"])

    def _do_reject():
        flc_reject(landlord_id, tenant_id); _refresh(_L["rej"], info=True)

    def _do_cancel():
        flc_cancel_request(landlord_id, tenant_id); _refresh(_L["cxl"], info=True)

    def _do_disconnect():
        flc_disconnect(landlord_id, tenant_id); _refresh(_L["disc"], info=True)

    # Relation
    rel = (flc_relation_status(landlord_id, tenant_id) or "disconnected").lower()

    # Tenant-side (invite by email into future_landlord_contacts)
    if viewer_role == "tenant":
        if not tenant_in_contacts and show_add_contact and tenant_other_email:
            if container.button(_L["add_contact"], key=kk("tenant_add")):
                try:
                    add_future_landlord_contact(tenant_id, tenant_other_email)
                    _refresh(_L["added"])
                except Exception as e:
                    container.error(f"{_L['cant_add']}: {e}")
        else:
            if show_status_caption:
                cap = {
                    "connected": f"✅ {_L['cap_connected']}",
                    "pending_inbound": f"⏳ {_L['cap_inbound']}",
                    "pending_outbound": f"⏳ {_L['cap_outbound']}",
                }.get(rel, f"➕ {_L['cap_none']}")
                container.caption(cap)
        return rel

    # Landlord/Agent viewer side
    actions = []
    if rel == "connected":
        if show_disconnect: actions.append((_L["disconnect"], "disc", _do_disconnect))
    elif rel == "pending_inbound":
        if show_accept: actions.append((_L["accept"], "acc", _do_accept))
        if show_reject: actions.append((_L["reject"], "rej", _do_reject))
    elif rel == "pending_outbound":
        if show_cancel: actions.append((_L["cancel"], "cxl", _do_cancel))
    else:  # disconnected
        if show_request: actions.append((_L["request"], "req", _do_request))

    cols = container.columns(max(2, len(actions)) if actions else 2)
    for i, (label, sfx, fn) in enumerate(actions):
        if cols[i].button(label, key=kk(sfx)): fn()

    if show_status_caption:
        if rel == "connected": container.caption(f"✅ {_L['cap_connected']}")
        elif rel == "pending_inbound": container.caption(f"⏳ {_L['cap_inbound']}")
        elif rel == "pending_outbound": container.caption(f"⏳ {_L['cap_outbound']}")
        else: container.caption(f"➕ {_L['cap_none']}")

    return rel

def render_landlord_peer_actions(
    *,
    me_id: int,
    other_id: int,
    parent=None,
    key_ns: str = "lp",
    viewer_role: str = "landlord",     # agents share landlord UI
    show_request: bool = True,
    show_accept: bool = True,
    show_reject: bool = True,
    show_cancel: bool = True,
    show_disconnect: bool = False,
    show_open_chat: bool = True,       # <- show "Open chat" when connected
    show_status_caption: bool = True,
    labels: dict | None = None
) -> str:
    """
    Landlord/Agent ↔ Landlord/Agent peer actions (lp_*).
    Returns: 'connected' | 'pending' | 'rejected' | 'disconnected'
    """
    container = parent or st

    _L = {
        "request": tr("Request"),
        "accept": tr("Accept"),
        "reject": tr("Reject"),
        "cancel": tr("Cancel request"),
        "disconnect": tr("Disconnect"),
        "chat": tr("Message"),
        "cap_connected": tr("Connected"),
        "cap_pending": tr("Pending"),
        "cap_none": tr("No relation"),
        "sent": tr("Request sent."),
        "ok": tr("Connected."),
        "rej": tr("Rejected."),
        "cxl": tr("Cancelled."),
        "disc": tr("Disconnected."),
    }
    if labels:
        _L.update(labels)

    def kk(sfx: str) -> str:
        return f"{key_ns}:{sfx}:{me_id}:{other_id}"

    def _refresh(msg=None, info=False):
        try: st.cache_data.clear()
        except Exception: pass
        if msg: (st.info if info else st.success)(msg)
        st.rerun()

    # Handlers
    def _do_request():     lp_request(me_id, other_id);     _refresh(_L["sent"])
    def _do_accept():      lp_accept(me_id, other_id);      _refresh(_L["ok"])
    def _do_reject():      lp_reject(me_id, other_id);      _refresh(_L["rej"], info=True)
    def _do_cancel():      lp_reject(me_id, other_id);      _refresh(_L["cxl"], info=True)  # your cancel = reject
    def _do_disconnect():  lp_disconnect(me_id, other_id);  _refresh(_L["disc"], info=True)

    def _open_chat():
        open_chat_unified(
            viewer_role=viewer_role,
            me_id=me_id,
            other_id=other_id
            # other_role not required; unified opener sets peer_mode="lp"
        )

    # Status + initiator (sqlite3.Row safe)
    stt = (lp_get_status(me_id, other_id) or "").lower()   # 'pending'|'connected'|'rejected'|None
    row = lp_get_row(me_id, other_id) or {}
    try:
        initiator = int(row.get("initiator_id") or 0)
    except Exception:
        try: initiator = int(row["initiator_id"] or 0)
        except Exception: initiator = 0
    inbound = bool(initiator and initiator != me_id)

    # Build actions
    actions = []

    if stt == "connected":
        # ---- NEW: unread + 'is open' styling for the chat button ----
        unread = 0
        try:
            tid_existing = get_thread_id_if_exists(me_id, other_id)
            if tid_existing:
                unread = int(get_unread_count(tid_existing, me_id) or 0)
        except Exception:
            pass

        sel = str(st.session_state.get("selected_thread") or "")
        is_open = bool(
            st.session_state.get("chat_open") and
            sel in {f"{me_id}-{other_id}", f"{other_id}-{me_id}"}
        )

        chat_label = f"{_L['chat']} ({unread})" if unread > 0 else _L["chat"]
        chat_btn_type = "primary" if (unread > 0 or is_open) else "secondary"

        if show_open_chat:
            actions.append((chat_label, "chat", _open_chat, chat_btn_type))

        if show_disconnect:
            actions.append((_L["disconnect"], "disc", _do_disconnect, "secondary"))

    elif stt == "pending":
        if inbound:
            if show_accept: actions.append((_L["accept"], "acc", _do_accept, "primary"))
            if show_reject: actions.append((_L["reject"], "rej", _do_reject, "secondary"))
        else:
            if show_cancel: actions.append((_L["cancel"], "cxl", _do_cancel, "secondary"))

    elif stt in ("rejected", None, "", "disconnected"):
        if show_request:
            actions.append((_L["request"], "req", _do_request, "primary"))

    # Render buttons (support 'type' if available in your Streamlit version)
    cols = container.columns(max(2, len(actions)) if actions else 2)
    for i, (label, sfx, fn, btn_type) in enumerate(actions):
        # If your Streamlit doesn't support 'type=', remove it from the call.
        if cols[i].button(label, key=kk(sfx), type=btn_type):
            fn()

    # Status caption
    if show_status_caption:
        if stt == "connected":
            container.caption(f"✅ {_L['cap_connected']}")
        elif stt == "pending":
            container.caption(f"⏳ {_L['cap_pending']}")
        else:
            container.caption(f"➕ {_L['cap_none']}")

    return stt or "disconnected"



def render_tenant_peer_actions(
    *,
    me_id: int,
    other_id: int,
    other_name: str | None = None,
    parent=None,                      # e.g., a Streamlit column (colR); if None, uses st
    key_ns: str = "t2t",
    # Per-button visibility toggles (all True by default)
    show_add_request: bool = True,    # "Add contact" when disconnected/rejected
    show_accept: bool = True,         # "Accept" when inbound pending
    show_reject: bool = True,         # "Reject" when inbound pending
    show_cancel: bool = True,         # "Cancel request" when you sent the request
    show_open_chat: bool = True,      # "Open chat" when connected
    show_disconnect: bool = True,     # "Disconnect" when connected
    # Status caption under the buttons
    show_status_caption: bool = True,
    # (unused now, but kept for API compatibility)
    nav_tab_key: str = "Messages",
    # Label overrides (optional)
    labels: dict | None = None
) -> str:
    """
    Unified Tenant↔Tenant action row.
    Returns the current status: 'connected' | 'pending' | 'disconnected' | 'rejected'
    """
    container = parent or st

    # --- Labels ---
    _labels = {
        "add": tr("Add contact"),
        "accept": tr("Accept"),
        "reject": tr("Reject"),
        "cancel": tr("Cancel request"),
        "chat": tr("Message"),
        "disconnect": tr("Disconnect"),
        "cap_connected": tr("Connected"),
        "cap_pending": tr("Pending"),
        "cap_none": tr("No relation"),
    }
    if labels:
        _labels.update(labels)

    # --- Helpers (defined BEFORE use) ---
    def _refresh(ok_msg=None, info=False):
        try:
            st.cache_data.clear()
        except Exception:
            pass
        if ok_msg:
            (st.info if info else st.success)(ok_msg)
        st.rerun()

    def _send_request():
        tp_request_connect(me_id, other_id)
        _refresh(tr("Request sent."))

    def _accept():
        tp_accept(me_id, other_id)
        _refresh(tr("Connected."))

    def _reject():
        tp_reject(me_id, other_id)
        _refresh(tr("Rejected."), info=True)

    def _cancel():
        tp_disconnect(me_id, other_id)
        _refresh(tr("Cancelled."), info=True)

    def _disconnect():
        tp_disconnect(me_id, other_id)
        _refresh(tr("Disconnected."), info=True)

    def _open_chat():
        open_chat_unified(
            viewer_role="tenant",
            me_id=me_id,
            other_id=other_id,
            other_role="tenant",
            other_name=other_name
        )

    # --- Current relation ---
    try:
        tp = tp_get_row(me_id, other_id)  # {status, initiator_id, ...} or None
    except Exception:
        tp = None

    status = ((tp or {}).get("status") or "disconnected").lower()
    initiator = int((tp or {}).get("initiator_id") or 0)
    inbound = bool(initiator and initiator != me_id)

    def kk(suffix: str) -> str:
        return f"{key_ns}:{suffix}:{other_id}"

    # --- Build visible actions for this state ---
    # Each action: (label, key_suffix, handler, btn_type)
    actions = []

    if status in ("", "disconnected", "rejected"):
        if show_add_request:
            actions.append((_labels["add"], "request", _send_request, "primary"))

    elif status == "pending":
        if inbound:
            if show_accept:
                actions.append((_labels["accept"], "accept", _accept, "primary"))
            if show_reject:
                actions.append((_labels["reject"], "reject", _reject, "secondary"))
        else:
            if show_cancel:
                actions.append((_labels["cancel"], "cancel", _cancel, "secondary"))

    elif status == "connected":
        # --- compute unread + whether this thread is currently open ---
        unread = 0
        try:
            tid_existing = get_thread_id_if_exists(me_id, other_id)
            if tid_existing:
                unread = int(get_unread_count(tid_existing, me_id) or 0)
        except Exception:
            pass

        sel = str(st.session_state.get("selected_thread") or "")
        is_open = bool(
            st.session_state.get("chat_open") and
            sel in {f"{me_id}-{other_id}", f"{other_id}-{me_id}"}
        )

        chat_label = f"{tr('Message')} ({unread})" if unread > 0 else tr("Message")
        chat_btn_type = "primary" if (unread > 0 or is_open) else "secondary"

        if show_open_chat:
            actions.append((chat_label, "chat", _open_chat, chat_btn_type))
        if show_disconnect:
            actions.append((_labels["disconnect"], "disconnect", _disconnect, "secondary"))

    # --- Layout & render buttons ---
    cols = container.columns(max(2, len(actions)) if actions else 2)
    for i, action in enumerate(actions):
        # Support both 3-tuple and 4-tuple (label, suffix, handler[, btn_type])
        if len(action) == 4:
            label, suffix, handler, btn_type = action
        else:
            label, suffix, handler = action
            btn_type = "secondary"
        if cols[i].button(label, key=kk(suffix), type=btn_type):
            handler()

    # --- Status caption ---
    if show_status_caption:
        if status == "connected":
            container.caption(f"✅ {_labels['cap_connected']}")
        elif status == "pending":
            container.caption(f"⏳ {_labels['cap_pending']}")
        else:
            container.caption(f"➕ {_labels['cap_none']}")

    return status




#=====================================================================================================================
# SEARCH USERS
#======================================================================================================================

def search_users(
    *,
    current_user_id: int,
    current_role: str,                     # "tenant" | "landlord" | "agent"
    key_ns: str = "people",
    roles_to_search: tuple[str, ...] = ("landlord","agent","tenant"),
    max_results: int = 25,
    title: str | None = None,
    help_text: str | None = None,
    transient_prefixes: tuple[str, ...] = ("ld_otr_", "otr_", "prospects"),
    ):
    """
    Unified people search (name/email) for all roles.
    - Tenants: can add LL/Agent contacts (future_landlord_contacts) or invite tenant-peers (tenant_peers).
    - Landlords/Agents: read-only by default (status shown if applicable). Customize later if needed.

    Expects existing helpers/functions:
      - search_people_by_name_or_email(q, roles, limit)
      - role_icon, tr, get_conn
      - flc_get_status(landlord_id, tenant_id)
      - add_future_landlord_contact(tenant_id, email)
      - tp_get_row(a_tid, b_tid)
      - tp_request_connect(inviter_id, invitee_id)
      - tp_accept(a_tid, b_tid), tp_reject(a_tid, b_tid), tp_disconnect(a_tid, b_tid)
      - st, st.cache_data, st.rerun, help_icon (optional)
    """
    
    

    # ---------- shared css ----------
    try:
        _ensure_tfl_css()
    except Exception:
        pass

    # ---------- helpers ----------
    def _initials(name, email):
        base = (name or "").strip() or (email or "").split("@")[0]
        parts = [p for p in base.replace(".", " ").split() if p]
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        if parts:
            return parts[0][:2].upper()
        return "?"

    def k(uid, suffix):
        return f"{key_ns}:{suffix}:{uid}"

    def _clear_transient():
        for kk in list(st.session_state.keys()):
            if kk.startswith(transient_prefixes):
                st.session_state.pop(kk, None)

    current_role = (current_role or "").strip().lower()

    # ---------- UI: header ----------
    c1, c2 = st.columns([6, 0.3])
    with c1:
        st.markdown(f"**{title or tr('Search people')}**")
    with c2:
        if help_text:
            try:
                help_icon(help_text, key=f"{key_ns}:help_search_people")
            except Exception:
                pass

    q = st.text_input(
        tr("Type a name or email"),
        key=f"{key_ns}:search_q",
        placeholder=tr("e.g. Maria Papadopoulou or maria@example.com"),
    )

    if not (q and len(q.strip()) >= 2):
        return  # don’t render results list yet

    # ---------- search ----------
    try:
        results = search_people_by_name_or_email(q, roles=roles_to_search, limit=max_results)
    except Exception:
        results = []
        st.warning(tr("Search unavailable."))

    if not results:
        st.caption(tr("No matches."))
        return

    # ---------- per-result card ----------
    for (other_id, other_name, other_email, other_role) in results:
        other_role = (other_role or "").strip().lower()
        me_id = current_user_id

        # Relationship state flags
        rel_status = None      # for LL/Agent connection status
        in_contacts = False
        invited = 0
        inbound_req = 0

        # Tenant-specific mapping (supports LL/Agent + peer tenant)
        if current_role == "tenant" and other_role in ("landlord", "agent", "tenant"):
            # LL/Agent: FLC status and presence in future_landlord_contacts by email
            if other_role in ("landlord", "agent"):
                try:
                    rel_status = flc_get_status(other_id, me_id)  # order: landlord_id, tenant_id
                except Exception:
                    rel_status = None

                try:
                    c = get_conn()
                    rowc = c.execute(
                        "SELECT id, invited, inbound_request FROM future_landlord_contacts "
                        "WHERE tenant_id=? AND LOWER(email)=LOWER(?) LIMIT 1",
                        (me_id, (other_email or "").strip().lower()),
                    ).fetchone()
                except Exception:
                    rowc = None

                in_contacts = bool(rowc)
                invited = int(rowc[1]) if rowc else 0
                inbound_req = int(rowc[2]) if rowc else 0

            # Tenant peer: use tenant_peers
            if other_role == "tenant":
                try:
                    tp = tp_get_row(me_id, other_id)  # dict or None
                except Exception:
                    tp = None
                if tp:
                    stt = (tp.get("status") or "").lower()
                    if stt in ("pending", "connected"):
                        in_contacts = True
                        if stt == "pending":
                            initiator = int(tp.get("initiator_id") or 0)
                            invited = 1 if initiator == me_id else 0
                            inbound_req = 1 if initiator and initiator != me_id else 0
                        rel_status = stt  # reuse for badge rendering below

        # ---------- card layout ----------
        with st.container(border=True):
            colL, colM, colR = st.columns([5, 3, 4])

            # Left: avatar + identity + role chip
            display_title = (other_name or other_email or f"User #{other_id}").strip()
            try:
                icon = role_icon(other_role)
            except Exception:
                icon = ""
            initials = _initials(other_name, other_email)
            role_chip = (other_role.capitalize() if other_role else "User")

            colL.markdown(
                f"""
                <div class="tfl-title">
                  <div class="tfl-avatar">{initials}</div>
                  <div>
                    <div class="tfl-name">{icon} {display_title} <span class="pill">{role_chip}</span></div>
                    <div class="tfl-email"><a href="mailto:{other_email}">{other_email}</a></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Middle: relationship badge
            # Middle: relationship badge
            if other_id == me_id:
                colM.markdown(
                    f"<span class='tfl-badge tfl-badge--info'>{tr('Me')}</span>",
                    unsafe_allow_html=True,
                )
            else:
                # Tenant view shows more states
                if current_role == "tenant" and other_role in ("landlord","agent","tenant"):
                    st_l = (rel_status or "").lower()
                    if st_l == "connected":
                        colM.markdown(
                            f"<span class='tfl-badge tfl-badge--ok'>{tr('Connected')}</span>",
                            unsafe_allow_html=True,
                        )
                    elif invited or inbound_req or st_l in {"pending","pending_inbound","pending_outbound"}:
                        colM.markdown(
                            f"<span class='tfl-badge tfl-badge--info'>{tr('Pending')}</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        colM.markdown(
                            f"<span class='tfl-badge'>{tr('No relation')}</span>",
                            unsafe_allow_html=True,
                        )

                else:
                    # Landlord/Agent searching: show LA→Tenant status
                    if current_role in ("landlord","agent") and other_role == "tenant":
                        rel = (flc_relation_status(me_id, other_id) or "").lower()  # connected | pending_inbound | pending_outbound | disconnected
                        if rel == "connected":
                            colM.markdown('<span class="tfl-badge tfl-badge--ok">{}</span>'.format(tr("Connected")), unsafe_allow_html=True)
                        elif rel in ("pending_inbound", "pending_outbound"):
                            colM.markdown('<span class="tfl-badge tfl-badge--info">{}</span>'.format(tr("Pending")), unsafe_allow_html=True)
                        else:
                            colM.markdown('<span class="tfl-badge">{}</span>'.format(tr("No relation")), unsafe_allow_html=True)

                    # Landlord/Agent ↔ Landlord/Agent (existing block stays as-is)
                    elif current_role in ("landlord","agent") and other_role in ("landlord","agent"):
                        stt = (lp_get_status(me_id, other_id) or "").lower()
                        if stt == "connected":
                            colM.markdown(f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
                        elif stt == "pending":
                            colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
                        else:
                            colM.markdown(f'<span class="tfl-badge">{tr("No relation")}</span>', unsafe_allow_html=True)
                    else:
                        colM.markdown(
                            f'<span class="tfl-badge">{tr("No relation")}</span>',
                            unsafe_allow_html=True,
                        )

 
            # Right: actions
            if other_id == me_id:
                colR.caption(tr("No actions"))
                continue
            
            # Tenant actions
            if current_role == "tenant" and other_role in ("landlord","agent"):
                # OLD behavior kept: add LL/Agent to Future Landlord Contacts
                render_flc_actions(
                    viewer_role="tenant",
                    landlord_id=other_id,
                    tenant_id=me_id,
                    parent=colR,
                    key_ns=f"{key_ns}:flc:t2l:search",
                    tenant_other_email=other_email,
                    tenant_in_contacts=in_contacts,
                    show_add_contact=True,          # show “Add contact”
                    show_status_caption=False
                    # (others ignored for tenants)
                    )

                
            elif current_role == "tenant" and other_role == "tenant":
                render_tenant_peer_actions(
                    me_id=me_id,
                    other_id=other_id,
                    other_name=other_name,
                    parent=colR,
                    key_ns=f"{key_ns}:t2t:search",
                    show_add_request=True,
                    show_accept=True,
                    show_reject=True,
                    show_cancel=False,
                    show_open_chat=False,
                    show_disconnect=False,
                    show_status_caption=False,
                    nav_tab_key="Open chat"
                )



                    
            # --- NEW: Landlord/Agent → Tenant actions ---
            elif current_role in ("landlord","agent") and other_role == "tenant":
                render_flc_actions(
                    viewer_role=current_role,
                    landlord_id=me_id,
                    tenant_id=other_id,
                    parent=colR,
                    key_ns=f"{key_ns}:flc:l2t:search",
                    show_request=True,
                    show_accept=True,
                    show_reject=True,
                    show_cancel=True,
                    show_disconnect=False,          # keep Search safe; show in Contacts if you want
                    show_status_caption=False
                    )


            else:
                # Landlord/Agent ↔ Landlord/Agent peer actions
                if current_role in ("landlord", "agent") and other_role in ("landlord", "agent"):
                    render_landlord_peer_actions(
                        me_id=me_id,
                        other_id=other_id,
                        parent=colR,
                        key_ns=f"{key_ns}:lp:search",
                        show_request=True,
                        show_accept=True,
                        show_reject=True,
                        show_cancel=True,
                        show_disconnect=False,
                        show_open_chat= False,
                        show_status_caption=False
                    )
      

# =====================================================================================================================
# PEOPLE HUB (My Contacts + Find Users)
# =====================================================================================================================


def people_hub(role: str | None = None):
    """
    Unified hub with two tabs:
      - My Contacts: tenant sees the unified contacts() view; landlord/agent sees tenants and their LL/Agent network.
      - Find Users: role-aware search results/actions via search_users(...).

    Requirements (helpers used here must exist):
      - contacts()                                  # tenant's unified contacts
      - search_users(current_user_id, current_role, ...)
      - tenant_profile(tid, landlord_id=..., inbound_request=..., key_ns=...)
      - flc_list_prospective_for_landlord(landlord_id)           # tenants tied to this LL/Agent
      - flc_relation_status(landlord_id, tenant_id)               # connected | pending_inbound | pending_outbound | disconnected
      - render_landlord_peer_actions(me_id, other_id, ...)        # LL/Agent ↔ LL/Agent actions (lp_* underneath)
      - lp_list_peers_for_landlord(my_id, statuses=("pending","connected"))  # helper you added for landlord_peers
      - get_user_by_id(user_id), tr(), role_icon(), get_conn(), st
    """
    # Resolve current user / role
    user = st.session_state.get("user") or {}
    my_id = int(user.get("id") or 0)
    current_role = (role or user.get("role") or "").strip().lower()

    # Tabs
    tab_contacts, tab_search = st.tabs([tr("My Contacts"), tr("Find Users")])

    # ===================================================================
    # TAB 1: MY CONTACTS
    # ===================================================================
    with tab_contacts:
        if current_role == "tenant":
            # Tenant: use your unified contacts list (future_landlord_contacts + tenant_peers)
            st.subheader(tr("My Contacts"))
            try:
                contacts()
            except Exception as e:
                st.error(f"{tr('Unable to load contacts')}: {e}")

        elif current_role in ("landlord", "agent"):

            try:
                rows = flc_list_prospective_for_landlord(my_id) or []
            except Exception:
                rows = []

            if not rows:
                st.caption(tr("No tenants yet."))
            else:
                for r in rows:
                    # Expect r to carry tenant_id (tid); adapt keys if your row schema differs
                    # NEW
                    tid = int(row_get_any(r, ("tenant_id", "id"), 0) or 0)

                    if not tid:
                        continue

                    # Relation for button states inside tenant_profile (landlord mode)
                    rel = (flc_relation_status(my_id, tid) or "disconnected").lower()
                    inbound = (rel == "pending_inbound")
                    outbound = (rel == "pending_outbound")

                    with st.container(border=True):
                        # Render the profile using your landlord-mode actions (tenant_profile handles LL actions)
                        tenant_profile(
                            tid,
                            landlord_id=my_id,
                            inbound_request=outbound,   # tenant_profile shows "Cancel request" when outbound
                            key_ns=f"lh:tenants:{my_id}:{tid}"
                        )

            try:
                peer_rows = lp_list_peers_for_landlord(my_id, statuses=("pending", "connected"))
            except Exception:
                peer_rows = []

            if not peer_rows:
                st.caption(tr("No peers yet."))
            else:
                for prow in peer_rows:
                    # prow is sqlite3.Row; make it dict-like
                    try:
                        other_id  = int(prow["other_id"])
                        status_lp = (prow["status"] or "").lower()
                        initiator = int(prow["initiator_id"] or 0)
                    except Exception:
                        other_id, status_lp, initiator = int(prow[0]), (prow[1] or "").lower(), int(prow[2] or 0)

                    inbound = bool(initiator and initiator != my_id)

                    u = get_user_by_id(other_id) or {}
                    other_name = (u.get("name") or "").strip()
                    other_email = (u.get("email") or "").strip()
                    other_role = (u.get("role") or "").strip().lower()

                    with st.container(border=True):
                        _ensure_tfl_css()  # make sure shared CSS is loaded

                        L, M, R = st.columns([5, 3, 5])

                        # Identity (avatar + role chip)
                        disp = other_name or other_email or f"User #{other_id}"
                        try:
                            icon = role_icon(other_role)
                        except Exception:
                            icon = ""
                        initials = _initials(other_name, other_email)
                        role_chip = tr("Landlord") if other_role == "landlord" else (tr("Agent") if other_role == "agent" else "")

                        L.markdown(f"""
                        <div class="tfl-title">
                        <div class="tfl-avatar">{initials}</div>
                        <div>
                            <div class="tfl-name">{icon} {disp} {f'<span class="pill">{role_chip}</span>' if role_chip else ''}</div>
                            <div class="tfl-email"><a href="mailto:{other_email}">{other_email}</a></div>
                        </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Status badge (match tenant style)
                        if status_lp == "connected":
                            M.markdown(
                                f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>',
                                unsafe_allow_html=True
                            )
                        elif status_lp == "pending":
                            M.markdown(
                                f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>',
                                unsafe_allow_html=True
                            )
                        else:
                            M.caption(tr("No relation"))


                        # Actions (request / accept / reject / cancel / disconnect)
                        render_landlord_peer_actions(
                            me_id=my_id,
                            other_id=other_id,
                            parent=R,
                            key_ns=f"lp:contacts:{other_id}",
                            show_request=True,
                            show_accept=True,
                            show_reject=True,
                            show_cancel=True,
                            show_disconnect=True,
                            show_open_chat=True,
                            show_status_caption=False,
                            labels={"chat": tr("Message")}
                        )

                        # --- Peer properties (only when connected) ---
                        # Ensure the same CSS classes used in contacts()
                        try:
                            _ensure_tfl_css()   # if you have this at module scope
                        except Exception:
                            # If _ensure_tfl_css is nested inside another function, you can inline it here once:
                            try:
                                st.markdown("""
                                <style>
                                .tfl-title{display:flex;align-items:center;gap:12px;margin-bottom:4px}
                                .tfl-avatar{width:40px;height:40px;border-radius:999px;display:flex;align-items:center;justify-content:center;
                                            font-weight:700;color:#111;border:1px solid #e5e7eb;background:linear-gradient(135deg,#f8fafc,#e2e8f0)}
                                .tfl-name{font-weight:700;font-size:1.05rem;margin:0}
                                .tfl-email{color:#64748b;font-size:.9rem;margin-top:2px}
                                .tfl-badge{padding:4px 10px;border-radius:999px;font-size:.85rem;font-weight:600;border:1px solid;display:inline-block}
                                .tfl-badge--ok{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}
                                .tfl-badge--info{background:#eff6ff;color:#1e40af;border-color:#bfdbfe}
                                .tfl-badge--err{background:#fef2f2;color:#7f1d1d;border-color:#fecaca}
                                .tfl-meta{color:#94a3b8;font-size:.85rem;margin-top:2px}
                                .pill{display:inline-block;padding:2px 8px;border-radius:999px;background:#f1f5f9;color:#334155;font-size:.8rem;
                                    margin-right:6px;margin-bottom:4px;border:1px solid #e2e8f0}
                                .prop-card{border:1px solid #e5e7eb;border-radius:12px;padding:10px 12px;margin-bottom:8px;background:#fff}
                                .prop-title{font-weight:600;margin-bottom:2px}
                                .prop-sub{color:#475569;font-size:.9rem;margin:4px 0 6px}
                                .prop-foot{color:#64748b;font-size:.85rem}
                                </style>
                                """, unsafe_allow_html=True)
                            except Exception:
                                pass

                        # --- Peer properties (only when connected) ---
                        if status_lp == "connected":
                            # Use the SAME source as contacts(): only *visible* properties
                            vprops = lp_list_visible_properties(other_id)
                            if vprops:
                                with st.expander(tr("Visible properties"), expanded=False):
                                    for pid, addr, url, upd, region, district, city, size_m2, rooms, floor, price in vprops:
                                        where = " — ".join([x for x in [region, district, city] if x])
                                        chips = []
                                        if where:   chips.append(f'<span class="pill">{where}</span>')
                                        if size_m2: chips.append(f'<span class="pill">{int(size_m2):,} m²</span>')
                                        if rooms:   chips.append(f'<span class="pill">{int(rooms)} {tr("rooms")}</span>')
                                        if floor not in (None, 0): chips.append(f'<span class="pill">{tr("Floor")} {int(floor)}</span>')
                                        if price:   chips.append(f'<span class="pill">€{int(price):,}</span>')
                                        chips_html = " ".join(chips)

                                        # same link + footer text as contacts()
                                        try:
                                            domain = url.split('://', 1)[-1].split('/', 1)[0] if url else None
                                        except Exception:
                                            domain = url
                                        link_html = f' 🔗 <a href="{url}">{domain or tr("Open listing")}</a>' if url else ""

                                        st.markdown(
                                            f"""
                                            <div class="prop-card">
                                            <div class="prop-title">• {addr}</div>
                                            <div class="prop-sub">{chips_html}</div>
                                            <div class="prop-foot">{tr('Updated')}: {format_dt(upd)}</div>
                                            <div class="prop-foot">{tr('For more details')}: {link_html}</div>
                                            </div>
                                            """,
                                            unsafe_allow_html=True
                                        )
                            else:
                                st.caption(tr("No properties visible."))
                        else:
                            st.caption("🔒 " + tr("Visible after you connect."))

                  
    # ===================================================================
    # TAB 2: FIND USERS (search)
    # ===================================================================
    with tab_search:
        try:
            help_txt = tr("Search by name or email. Actions adapt to your role.")
            search_users(
                current_user_id=my_id,
                current_role=current_role,
                key_ns="people",
                roles_to_search=("landlord", "agent", "tenant"),
                max_results=25,
                title=tr("Find Users"),
                help_text=help_txt,
            )
        except Exception as e:
            st.error(f"{tr('Search unavailable')}: {e}")




#=====================================================================================================================
# LANDLORDS AGENTS PROFILE
#======================================================================================================================
def render_landlord_agent_contact_row(
    *,
    cid: int,
    name: str,
    email: str,
    role_norm: str,
    landlord_id: int | None,
    tenant_id: int,
    status_ll: str | None,
    invited: int,
    inbound_request: int,
    k,                          # key builder: k(uid, "suffix")
    _initials,                  # your initials helper
    _clear_transient,           # your transient cleaner
    show_properties: bool = True,
    row_uid: str | None = None, # <- NEW: unique row id for widget keys
    ):
        """
        Renders ONE landlord/agent contact row:
        - Left: avatar, name/email, role chip
        - Middle: relationship badge
        - Right: actions (Message/Disconnect, Connect/Decline, Invite/Remove)
        - Properties (expander) only if connected

        Expects your existing globals: st, tr, role_icon, get_conn, invite_future_landlord,
        tp_request, flc_connect, flc_disconnect, flc_reject, get_thread_id_if_exists,
        get_or_create_thread, mark_thread_read, remove_future_landlord_contact,
        lp_list_visible_properties, _url_domain, format_dt, help_icon, get_user_by_email.
        """
        # Derive a unique row uid if the caller didn't pass one
        if not row_uid:
            # include multiple dimensions to avoid collisions across sections/pages
            row_uid = f"ll:{landlord_id or 'none'}:{tenant_id}:{cid}:{(email or '').lower()}"

        colL, colM, colR = st.columns([6, 3, 6])

        # --- Left: identity ---
        try:
            icon = role_icon(role_norm) if role_norm else ""
        except Exception:
            icon = ""

        chip = ""
        if role_norm in ("landlord", "agent"):
            chip = f'<span class="pill">{tr("Landlord") if role_norm=="landlord" else tr("Agent")}</span>'

        display_title = name or email
        colL.markdown(
            f"""
            <div class="tfl-title">
            <div class="tfl-avatar">{_initials(name, email)}</div>
            <div>
                <div class="tfl-name">{icon} {display_title} {chip}</div>
                <div class="tfl-email"><a href="mailto:{email}">{email}</a></div>
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # --- Middle: badge ---
        if status_ll == "connected":
            colM.markdown(f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
        elif inbound_request:
            colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
        elif invited:
            colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Invited")}</span>', unsafe_allow_html=True)
        else:
            colM.markdown(f'<span class="tfl-badge">{tr("No relation")}</span>', unsafe_allow_html=True)

        # --- Right: actions ---
        if status_ll == "connected":
            a1, a2 = colR.columns(2)

            pair_key = f"{landlord_id}-{tenant_id}"
            me_id = st.session_state.user["id"]
            thread_id_existing = get_thread_id_if_exists(landlord_id, tenant_id)
            unread = get_unread_count(thread_id_existing, me_id)

            chat_is_open = (
                st.session_state.get("chat_open", False)
                and st.session_state.get("selected_thread") == pair_key
            )

            if chat_is_open:
                btn_label = tr("Message")
                btn_type  = "primary"
            else:
                base = tr("Message")
                btn_label = f"{base} ({unread})" if (unread or 0) > 0 else base
                btn_type  = "secondary" if (unread or 0) == 0 else "primary"

            if a1.button(btn_label, key=k(row_uid, "chat_toggle"), type=btn_type):
                if chat_is_open:
                    st.session_state.chat_open = False
                    st.session_state.selected_thread = None
                else:
                    st.session_state["chat_role"] = "tenant"
                    st.session_state["chat_with_landlord_id"] = landlord_id
                    st.session_state["chat_with_tenant_id"] = tenant_id
                    st.session_state.selected_thread = pair_key
                    st.session_state.chat_open = True
                    tid = get_or_create_thread(landlord_id, tenant_id)
                    mark_thread_read(tid, me_id)
                st.rerun()

            if a2.button(tr("Disconnect"), key=k(row_uid, "disconnect_connected")):
                flc_disconnect(landlord_id, tenant_id)
                try: st.cache_data.clear()
                except Exception: pass
                _clear_transient()
                st.warning(tr("Disconnected."))
                st.rerun()

        elif inbound_request:
            ahelp, _ = colR.columns([0.18, 1])
            try:
                with ahelp:
                    help_icon(tr("Approve to connect and share your status. Decline to reject the request."),
                            key=k(row_uid, "help_inbound"))
            except Exception:
                pass

            b1, b2 = colR.columns(2)
            if b1.button(tr("Connect"), key=k(row_uid, "accept_inbound")):
                flc_connect(landlord_id, tenant_id)
                c = get_conn()
                c.execute("UPDATE future_landlord_contacts SET inbound_request=0, inbound_requested_at=NULL WHERE id=?", (cid,))
                c.commit()
                try: st.cache_data.clear()
                except Exception: pass
                _clear_transient()
                st.success(tr("Connected."))
                st.rerun()

            if b2.button(tr("Disconnect"), key=k(row_uid, "decline_inbound")):
                flc_reject(landlord_id, tenant_id)
                c = get_conn()
                c.execute("UPDATE future_landlord_contacts SET inbound_request=0, inbound_requested_at=NULL WHERE id=?", (cid,))
                c.commit()
                try: st.cache_data.clear()
                except Exception: pass
                _clear_transient()
                st.info(tr("Disconnected."))
                st.rerun()
        else:
            # check if already invited
            invited = tenant_has_invited(tenant_id, email)
            status_badge = tr("Invited") if invited else tr("No relation")
            st.markdown(f"**{status_badge}**")

            b1, b2 = colR.columns(2)

            # If already invited -> disable button
            if invited:
                b1.button(tr("Send invitation"), disabled=True, key=k(row_uid, "send_invite_plain"))
            else:
                if b1.button(tr("Send invitation"), key=k(row_uid, "send_invite_plain")):
                    invitee_user = get_user_by_email(email)

                    # If email belongs to a TENANT, route to roommate invite instead of LL invite
                    if invitee_user and (invitee_user.get("role") or "").strip().lower() == "tenant":
                        try:
                            tp_request(inviter_id=tenant_id, invitee_id=invitee_user["id"])
                            try: st.cache_data.clear()
                            except Exception: pass
                            _clear_transient()
                            st.success(tr("Invitation sent."))
                            st.rerun()
                        except Exception as e:
                            st.error(f"{tr('Can’t send invitation')}: {e}")
                    else:
                        ok, msg = invite_future_landlord(
                            tenant_id, email,
                            st.session_state.user.get("name"),
                            st.session_state.user.get("email"),
                        )
                        if ok:
                            try: st.cache_data.clear()
                            except Exception: pass
                            _clear_transient()
                            st.success(tr("Invitation sent."))
                            st.rerun()
                        else:
                            st.error(f"{tr('Can’t send invitation')}: {msg}")


            if b2.button(tr("Remove"), key=k(row_uid, "remove_plain")):
                remove_future_landlord_contact(cid, tenant_id)
                try: st.cache_data.clear()
                except Exception: pass
                _clear_transient()
                st.info(tr("Contact removed."))
                st.rerun()

        # --- Properties (only when connected) ---
        if show_properties and (status_ll == "connected") and landlord_id:
            vprops = lp_list_visible_properties(landlord_id)
            if vprops:
                with st.expander(tr("Visible properties"), expanded=False):
                    for pid, addr, url, upd, region, district, city, size_m2, rooms, floor, price in vprops:
                        where = " — ".join([x for x in [region, district, city] if x])
                        chips = []
                        if where:   chips.append(f'<span class="pill">{where}</span>')
                        if size_m2: chips.append(f'<span class="pill">{int(size_m2):,} m²</span>')
                        if rooms:   chips.append(f'<span class="pill">{int(rooms)} {tr("rooms")}</span>')
                        if floor not in (None, 0): chips.append(f'<span class="pill">{tr("Floor")} {int(floor)}</span>')
                        if price:   chips.append(f'<span class="pill">€{int(price):,}</span>')
                        chips_html = " ".join(chips)
                        link_html = f' 🔗 <a href="{url}">{_url_domain(url) or tr("Open listing")}</a>' if url else ""
                        st.markdown(
                            f"""
                            <div class="prop-card">
                            <div class="prop-title">• {addr}</div>
                            <div class="prop-sub">{chips_html}</div>
                            <div class="prop-foot">{tr('Updated')}: {format_dt(upd)}</div>
                            <div class="prop-foot">{tr('For more details')}: {link_html}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            else:
                st.caption(tr("No properties visible."))

        else:
            st.caption("🔒 " + tr("Visible after you connect."))

#=====================================================================================================================
# TENANT PROFILE
#======================================================================================================================
def tenant_profile(
    tid,
    landlord_id=None,
    inbound_request=False,
    peer_mode: bool = False,
    key_ns: str = "prospects",
    # NEW: optionally show Tenant↔Tenant buttons from inside the card
    show_peer_actions: bool = False,
    peer_actions_kwargs: dict | None = None,  # pass show_* toggles, labels, nav_tab_key, etc.
):

    """
    Renders a tenant profile card.

    - Landlord mode (default): landlord_id is an int; status/actions come from FLC (flc_*).
    - Peer mode (tenant↔tenant): pass landlord_id=None (or peer_mode=True). Status from tenant_peers.
      Actions (chat / disconnect) are rendered by the caller card; here we only show details.
    """
    _ensure_pt_css()

    # ── Widget key namespace ───────────────────────────────────────────────────────
    def pk(tid_val: int, name: str) -> str:
        # include the caller's namespace to avoid duplicate keys across list rows
        return f"{key_ns}:{name}:{tid_val}"

    def _pt_initials(name, email):
        base = (name or "").strip() or (email or "").split("@")[0]
        parts = [p for p in base.replace(".", " ").split() if p]
        if len(parts) >= 2: return (parts[0][0] + parts[1][0]).upper()
        if parts: return parts[0][:2].upper()
        return "?"

    # Fallback for _yn if missing here
    try:
        _yn  # noqa: F401
    except Exception:
        def _yn(v):
            if v is True: return "✅"
            if v is False: return "❌"
            return "—"

    # Resolve tenant before rendering identity
    tenant_user = get_user_by_id(tid) or {}
    tenant_name  = (tenant_user.get("name")  or "").strip()
    tenant_email = (tenant_user.get("email") or "").strip()
    tenant_phone = (tenant_user.get("phone") or "").strip()
    tenant_phone_visible = int(tenant_user.get("phone_visible") or 0)

    # Detect peer context (tenant↔tenant from Contacts)
    is_peer_ctx = bool(peer_mode or landlord_id in (None, "", 0))
    me_id = st.session_state.user["id"] if st.session_state.get("user") else None

    # Status
    if is_peer_ctx:
        try:
            status = (tp_get_status(me_id, tid) or "").lower()
        except Exception:
            status = None
    else:
        try:
            status = flc_get_status(landlord_id, tid)
        except Exception:
            status = None

    # Header row: identity • badge • actions
    role_norm = ((tenant_user.get("role") or "").strip().lower()) or "tenant"
    is_tenant = (role_norm == "tenant")

    colL, colM, colR = st.columns([6, 3, 6])

    # Left: avatar + name/email (+ phone if visible)
    display_title = tenant_name or tenant_email or f"Tenant #{tid}"
    initials = _pt_initials(tenant_name, tenant_email)
    phone_html = f'<div class="pt-phone">📞 {tenant_phone}</div>' if (tenant_phone and tenant_phone_visible) else ""

    try:
        icon = role_icon(role_norm) if role_norm else ""
    except Exception:
        icon = ""

    chip = f'<span class="pill">{tr("Tenant")}</span>' if is_tenant else ""

    colL.markdown(
        f"""
        <div class="pt-title">
          <div class="pt-avatar">{initials}</div>
          <div>
            <div class="pt-name">{icon} {display_title} {chip}</div>
            <div class="pt-email"><a href="mailto:{tenant_email}">{tenant_email}</a></div>
            {phone_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Middle: status badge
    # Middle: status badge
    if is_peer_ctx:
        s_l = (status or "").lower()
        if s_l == "connected":
            colM.markdown(f'<span class="pt-badge pt-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
        elif s_l == "pending":
            colM.markdown(f'<span class="pt-badge pt-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
        elif s_l == "rejected":
            colM.markdown(f'<span class="pt-badge pt-badge--err">{tr("Rejected")}</span>', unsafe_allow_html=True)
        else:
            colM.markdown(f'<span class="pt-badge">{tr("No relation")}</span>', unsafe_allow_html=True)
    else:
        # Landlord mode (unchanged)
        if status == "connected":
            colM.markdown(f'<span class="pt-badge pt-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
        elif status == "rejected":
            colM.markdown(f'<span class="pt-badge pt-badge--err">{tr("Rejected")}</span>', unsafe_allow_html=True)
        else:
            colM.markdown(f'<span class="pt-badge pt-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)


    # Right column
    # Right column
    if is_peer_ctx:
        # Optional inline Tenant↔Tenant actions (disabled by default)
        if show_peer_actions and me_id:
            # Build a friendly display name for chat
            peer_display_name = (tenant_name or tenant_email or f"Tenant #{tid}")
            # Defaults for the helper if caller didn't pass any
            _kwargs = {
                "show_add_request": True,
                "show_accept": True,
                "show_reject": True,
                "show_cancel": True,
                "show_open_chat": True,
                "show_disconnect": True,
                "show_status_caption": False,  # we already show a badge in middle column
                "nav_tab_key": "Open chat",
            }
            if isinstance(peer_actions_kwargs, dict):
                _kwargs.update(peer_actions_kwargs)

            render_tenant_peer_actions(
                me_id=me_id,
                other_id=tid,
                other_name=peer_display_name,
                parent=colR,
                key_ns=f"{key_ns}:t2t:profile:{tid}",
                **_kwargs,
            )
        else:
            # keep read-only card if not enabled
            pass
    else:
        # Landlord mode actions only (UNCHANGED)
                # Landlord mode actions only
        if status == "connected":
            a1, a2 = colR.columns(2)

            # --- unread + "is open" state for styling & label ---
            try:
                me_id = int(st.session_state.user["id"])
            except Exception:
                me_id = None

            # existing thread (if any) → unread for me
            unread = 0
            try:
                tid_existing = get_thread_id_if_exists(landlord_id, tid)
                if tid_existing and me_id:
                    unread = int(get_unread_count(tid_existing, me_id) or 0)
            except Exception:
                pass

            # is this specific chat open right now?
            sel = str(st.session_state.get("selected_thread") or "")
            is_open = bool(
                st.session_state.get("chat_open")
                and sel in {f"{landlord_id}-{tid}", f"{tid}-{landlord_id}"}
            )

            # label + style
            base = tr("Message") 
            btn_label = f"{base} ({unread})" if unread > 0 else base
            btn_type  = "primary" if (unread > 0 or is_open) else "secondary"

            # --- button: open/close chat (unified) ---
            if a1.button(btn_label, key=pk(tid, "chat_toggle"), type=btn_type):
                if is_open:
                    # close this thread view
                    st.session_state["chat_open"] = False
                    st.session_state["selected_thread"] = None
                    st.rerun()
                else:
                    open_chat_unified(
                        viewer_role="landlord",
                        me_id=landlord_id,
                        other_id=tid,
                        other_role="tenant",
                        other_name=display_title
                    )

            # --- button: disconnect ---
            if a2.button(tr("Disconnect"), key=pk(tid, "disconnect")):
                flc_disconnect(landlord_id, tid)
                try: st.cache_data.clear()
                except Exception: pass
                st.warning(tr("Disconnected."))
                st.rerun()

    

        elif status == "rejected":
            colR.caption(tr("No actions"))
        else:
            if inbound_request:
                if colR.button(tr("Cancel request"), key=pk(tid, "cancel_request")):
                    flc_cancel_request(landlord_id, tid)
                    try: st.cache_data.clear()
                    except Exception: pass
                    st.info(tr("Request cancelled."))
                    st.rerun()
            else:
                c1, c2 = colR.columns(2)
                if c1.button(tr("Connect"), key=pk(tid, "connect")):
                    flc_connect(landlord_id, tid)
                    try: st.cache_data.clear()
                    except Exception: pass
                    st.success(tr("Connected."))
                    st.rerun()
                if c2.button(tr("Reject"), key=pk(tid, "reject")):
                    flc_reject(landlord_id, tid)
                    try: st.cache_data.clear()
                    except Exception: pass
                    st.info(tr("Rejected."))
                    st.rerun()


    # ---- Open to rent one-liner (Active only) ----
    def open_to_rent_tokens(tenant_id: int):
        c = get_conn()
        try:
            cols = {r[1] for r in c.execute("PRAGMA table_info(tenant_profiles)").fetchall()}
        except Exception:
            return None
        if "open_to_rent" not in cols:
            return None
        id_col = "tenant_id" if "tenant_id" in cols else ("user_id" if "user_id" in cols else None)
        if not id_col:
            return None
        wanted = [
            "open_to_rent","search_region","search_district","search_city",
            "size_min","size_max","rooms_min","rooms_max",
            "floor_min","floor_max","price_min","price_max",
        ]
        select_cols = [cname for cname in wanted if cname in cols]
        if not select_cols:
            return None
        sql_cols = ", ".join([f'"{cname}"' for cname in select_cols])
        row = c.execute(f'SELECT {sql_cols} FROM tenant_profiles WHERE "{id_col}"=?', (tenant_id,)).fetchone()
        if not row:
            return None
        data = dict(zip(select_cols, row))
        o2r = data.get("open_to_rent")
        try:
            active = int(o2r) == 1
        except Exception:
            active = str(o2r).strip().lower() in {"1","true","yes","y"}
        if not active:
            return None
        def fmt_num(v):
            if v is None or v == "" or (isinstance(v, (int, float)) and v == 0): return None
            try: return f"{int(v):,}"
            except Exception: return str(v)
        def rng(lo, hi):
            lo_f, hi_f = fmt_num(lo), fmt_num(hi)
            if lo_f and hi_f: return f"{lo_f}–{hi_f}"
            return lo_f or hi_f or None
        where = " — ".join([x for x in [data.get("search_region"), data.get("search_district"), data.get("search_city")] if x]) or None
        size  = rng(data.get("size_min"),  data.get("size_max"))
        rooms = rng(data.get("rooms_min"), data.get("rooms_max"))
        floor = rng(data.get("floor_min"), data.get("floor_max"))
        price = rng(data.get("price_min"), data.get("price_max"))
        return {
            "where": where,
            "size":  f"{size} m²" if size else None,
            "rooms": f"{rooms} {tr('rooms')}" if rooms else None,
            "floor": f"{tr('Floor')} {floor}" if floor else None,
            "price": f"€{price}" if price else None,
        }

    o2r = open_to_rent_tokens(tid)
    if o2r:
        chips = []
        if o2r["where"]: chips.append(f'<span class="pill">{o2r["where"]}</span>')
        if o2r["size"]:  chips.append(f'<span class="pill">{o2r["size"]}</span>')
        if o2r["rooms"]: chips.append(f'<span class="pill">{o2r["rooms"]}</span>')
        if o2r["floor"]: chips.append(f'<span class="pill">{o2r["floor"]}</span>')
        if o2r["price"]: chips.append(f'<span class="pill">{o2r["price"]}</span>')
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0 2px 0">'
            f'  <span class="pt-badge pt-badge--ok">{tr("Open to rent")}</span>'
            f'  <div>{" ".join(chips)}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Show document badges only when connected
    if status == "connected":
        try:
            render_tenant_doc_badges_inline(tid)
        except Exception:
            pass

    # ---- References summary ----
    refs = list_latest_references_for_tenant_dict(tid) or []
    refs = [r for r in refs if (r.get("status") or "").lower() != "cancelled"]
    st.caption(f"{tr('References')}: {len(refs)}")

    # ---- Reference details (only when connected) ----
    def _status_badge_html(s):
        try:
            lab = display_status_label(s) if s else "—"
        except Exception:
            lab = (s or "—").title()
        s_l = (s or "").lower()
        cls = "pt-badge pt-badge--info"
        if s_l == "completed":
            cls = "pt-badge pt-badge--ok"
        elif s_l in {"rejected", "declined"}:
            cls = "pt-badge pt-badge--err"
        return f'<span class="{cls}">{lab}</span>'

    if status == "connected":
        refs_full = list_latest_references_for_tenant_dict(tid) or []
        refs_full = [r for r in refs_full if (r.get("status") or "").lower() != "cancelled"]
        if refs_full:
            completed_scores = [
                r.get("score") for r in refs_full
                if (r.get("status") or "").lower() == "completed" and r.get("score") is not None
            ]
            avg_score = round(sum(completed_scores) / len(completed_scores)) if completed_scores else None
            st.markdown(f"{tr('Score')}: {avg_score if avg_score is not None else '—'}")
            with st.expander(tr("Reference details"), expanded=False):
                for r in refs_full:
                    prev_email = (r.get("prev_email") or "—").strip()
                    status_lr  = r.get("status") or ""
                    score_lr   = r.get("score")
                    paid_on    = r.get("paid_on_time")
                    util_unp   = r.get("utilities_unpaid")
                    good_cond  = r.get("good_condition")
                    comments   = r.get("comments")
                    score_chip = ""
                    if (status_lr or "").lower() == "completed" and score_lr is not None:
                        score_chip = f'<span class="pill pill-score">{tr("Score")}: {int(score_lr)}/10</span>'
                    def yn(v): return "✅" if v is True else ("❌" if v is False else "—")
                    paid_cls = "pill-ok" if paid_on is True else "pill-no" if paid_on is False else "pill-na"
                    util_cls = "pill-no" if util_unp is True else "pill-ok" if util_unp is False else "pill-na"
                    cond_cls = "pill-ok" if good_cond is True else "pill-no" if good_cond is False else "pill-na"
                    chips_html = " ".join(filter(None, [
                        score_chip,
                        f'<span class="pill {paid_cls}">{tr("Paid on time")}: {yn(paid_on)}</span>',
                        f'<span class="pill {util_cls}">{tr("Unpaid utilities")}: {yn(util_unp)}</span>',
                        f'<span class="pill {cond_cls}">{tr("Good condition")}: {yn(good_cond)}</span>',
                    ]))
                    st.markdown(
                        f"""
                        <div class="ref-card">
                          <div class="ref-header">
                            <div class="ref-title">{tr('Previous landlord')}: <a href="mailto:{prev_email}">{prev_email}</a></div>
                            <div>{_status_badge_html(status_lr)}</div>
                          </div>
                          <div class="ref-row">{chips_html}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if comments:
                        st.markdown(f"**{tr('Comments')}**")
                        st.markdown(f"<div class='ref-comments'>{comments}</div>", unsafe_allow_html=True)
    else:
        # Optional lock note when there are refs at all
        try:
            if list_latest_references_for_tenant(tid):
                st.caption("🔒 " + tr("Reference details are visible after you connect."))
        except Exception:
            pass


def contacts():
    """
    Unified contacts view for tenants:
    - Landlords & Agents from future_landlord_contacts
    - Roommates (tenants) from tenant_peers (cid < 0)
    """
    
    try:
        _ensure_tfl_css()
    except Exception:
        pass
   

    NSC = "tfl_contacts"

    def k(uid, name):
        """uid can be int or string; we’ll pass a composite string per row."""
        return f"{NSC}:{name}:{uid}"


    def _initials(name, email):
        base = (name or "").strip() or (email or "").split("@")[0]
        parts = [p for p in base.replace(".", " ").split() if p]
        if len(parts) >= 2: return (parts[0][0] + parts[1][0]).upper()
        if parts: return parts[0][:2].upper()
        return "?"

    def _clear_transient():
        for key in list(st.session_state.keys()):
            if key.startswith(("ld_otr_", "otr_", "prospects")):
                del st.session_state[key]

    tenant_id = st.session_state.user["id"]

    rows = list_future_landlord_contacts(tenant_id) or []
    
    # --- NEW: de-duplicate by normalized email ---
    seen = set()
    unique_rows = []
    for r in rows:
        # rows: (cid, email, created_at, invited, invited_at, inbound_request, inbound_requested_at)
        em = (r[1] or "").strip().lower()
        if em in seen:
            continue
        seen.add(em)
        unique_rows.append(r)
    rows = unique_rows
    if not rows:
        st.caption(tr("No contacts yet"))
        return

    for idx, (cid, email, created_at, invited, invited_at, inbound_request, inbound_requested_at) in enumerate(rows):
        # Resolve identity
        u = get_user_by_email(email)
        role_norm = (u.get("role") or "").strip().lower() if u else ""
        name = (u.get("name") or "").strip() if u else ""

        is_landlord_agent = role_norm in ("landlord", "agent")
        is_tenant_peer = cid < 0  # NEGATIVE id encodes tenant-peers
        landlord_id = u["id"] if (u and is_landlord_agent) else None

        # --- Landlord / Agent row -------------------------------------------------
        if is_landlord_agent:
            try:
                status_ll = flc_get_status(landlord_id, tenant_id)  # 'connected'|'rejected'|None
            except Exception:
                status_ll = None
                
            row_uid = f"{idx}:ll:{landlord_id or 'none'}:{tenant_id}:{cid}:{(email or '').lower()}"

            with st.container(border=True):
                render_landlord_agent_contact_row(
                    cid=cid,
                    name=name,
                    email=email,
                    role_norm=role_norm,
                    landlord_id=landlord_id,
                    tenant_id=tenant_id,
                    status_ll=status_ll,
                    invited=int(invited or 0),
                    inbound_request=int(inbound_request or 0),
                    k=k,
                    _initials=_initials,
                    _clear_transient=_clear_transient,
                    show_properties=True,
                    row_uid=row_uid, 
                )
            continue

        # --- Tenant ↔ Tenant row --------------------------------------------------
        if is_tenant_peer:
            other_tid = -cid

            with st.container(border=True):
                row_uid = f"tp:{other_tid}:{tenant_id}:{cid}"

                
                tenant_profile(
                    other_tid,
                    landlord_id=None,
                    peer_mode=True,
                    show_peer_actions=True,
                    peer_actions_kwargs={
                        "show_add_request": True,
                        "show_accept": True,
                        "show_reject": True,
                        "show_cancel": True,
                        "show_open_chat": True,
                        "show_disconnect": True,
                        "show_status_caption": False,  # we already show the badge in colM
                        "nav_tab_key": "Messages",
                    },
                )


        # Keep row_uid resolution AFTER the peer block for non-peer cases only
        if is_landlord_agent and landlord_id:
            row_uid = f"ll:{landlord_id}:{tenant_id}:{cid}"
        elif is_tenant_peer:
            # Already defined above for peers
            pass
        else:
            # fallback if we somehow don’t have ids; email keeps it unique enough
            row_uid = f"u:{(email or '').lower()}:{tenant_id}:{cid}"

            # try:
            #     chat_panel()
            # except Exception:
            #     pass


#======================================================================================================================================================
# PROPERTIES FILTERS for properties characteristics and find tenant
#========================================================================================================================================================

def render_tenant_filters(prefix="otr"):
    """
    Renders location + range filters using your existing greece_location_pickers().
    Returns a dict with normalized values ready for search_open_to_rent_tenants.
    Call with different prefixes in different sections to avoid key collisions.
    """
    # --- LOCATION ---
    region, regional_unit, municipality = greece_location_pickers(prefix=prefix)

    def _norm_any(v):
        if v is None:
            return ""
        s = str(v).strip().lower()
        # Treat common "Any" tokens as empty
        if s in {"", "any", "—", "-", "— any —"}:
            return ""
        return str(v)

    region_norm   = _norm_any(region)
    district_norm = _norm_any(regional_unit)
    city_norm     = _norm_any(municipality)

    # --- RANGES ---
    c1, c2 = st.columns(2)
    size_min_val = c1.number_input(
        tr("Min size (m²)"), min_value=0, max_value=10000, value=0, step=1,
        key=f"{prefix}_size_min"
    )
    size_max_val = c2.number_input(
        tr("Max size (m²)"), min_value=0, max_value=10000, value=0, step=1,
        key=f"{prefix}_size_max"
    )

    r1, r2 = st.columns(2)
    rooms_min_val = r1.number_input(
        tr("Min rooms"), min_value=0, max_value=50, value=0, step=1,
        key=f"{prefix}_rooms_min"
    )
    rooms_max_val = r2.number_input(
        tr("Max rooms"), min_value=0, max_value=50, value=0, step=1,
        key=f"{prefix}_rooms_max"
    )

    f1, f2 = st.columns(2)
    floor_min_val = f1.number_input(
        tr("Min floor"), min_value=-5, max_value=100, value=0, step=1,
        key=f"{prefix}_floor_min"
    )
    floor_max_val = f2.number_input(
        tr("Max floor"), min_value=-5, max_value=100, value=0, step=1,
        key=f"{prefix}_floor_max"
    )

    p1, p2 = st.columns(2)
    price_min_val = p1.number_input(
        tr("Min price (€)"), min_value=0, max_value=1_000_000, value=0, step=50,
        key=f"{prefix}_price_min"
    )
    price_max_val = p2.number_input(
        tr("Max price (€)"), min_value=0, max_value=1_000_000, value=0, step=50,
        key=f"{prefix}_price_max"
    )

    def _none_if_zero(v):
        try:
            return None if int(v) == 0 else int(v)
        except Exception:
            return None

    return {
        # location (region is optional; include if your search uses it)
        "region":   region_norm,
        "district": district_norm,
        "city":     city_norm,
        # ranges
        "size_min":  _none_if_zero(size_min_val),
        "size_max":  _none_if_zero(size_max_val),
        "rooms_min": _none_if_zero(rooms_min_val),
        "rooms_max": _none_if_zero(rooms_max_val),
        "floor_min": (None if floor_min_val == 0 else floor_min_val),
        "floor_max": (None if floor_max_val == 0 else floor_max_val),
        "price_min": _none_if_zero(price_min_val),
        "price_max": _none_if_zero(price_max_val),
    }


# ---------- Tenant data helpers ----------

# UPLOAD_DIR = Path("uploads") / "contracts"

def get_user_id_by_email(email: str) -> int | None:
    if not email:
        return None
    row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    return row[0] if row else None



def safe_filename(name: str) -> str:
    base = os.path.basename(name or "contract")
    return re.sub(r"[^A-Za-z0-9._-]", "_", base)

def get_contract_by_token(token: str):
    cur = conn.cursor()
    cur.execute(
        "SELECT filename, content_type, path, size_bytes, uploaded_at, status, status_updated_at, status_by "
        "FROM reference_contracts WHERE token=?",
        (token,),
    )
    row = cur.fetchone()
    if row:
        keys = ["filename","content_type","path","size_bytes","uploaded_at","status","status_updated_at","status_by"]
        return dict(zip(keys, row))
    return None


def save_contract_upload(token: str, tenant_id: int, uploaded_file) -> tuple[bool, str]:
    req = get_reference_request_by_token(token)
    if not req:
        return False, "Reference request not found."
    if req["tenant_id"] != tenant_id:
        return False, "You cannot upload to a request that is not yours."

    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
    name = safe_filename(uploaded_file.name)
    ext = Path(name).suffix.lower()
    if ext not in allowed_exts:
        return False, "Only PDF, PNG, JPG, JPEG, or WEBP files are allowed."

    # Read bytes
    try:
        raw = uploaded_file.getbuffer()
        data = bytes(raw)
        size = len(data)
    except Exception:
        data = uploaded_file.read()
        size = len(data)

    if size > 15 * 1024 * 1024:
        return False, "File too large (max 15 MB)."

    # # Encrypt before storing (Data Vault)
    # from utils_vault import encrypt_bytes, sha256_bytes
    ciphertext = encrypt_bytes(data)
    digest = sha256_bytes(data)

    # Save encrypted blob under uploads/contracts/<token>/<filename>.bin
    folder = UPLOAD_DIR / token
    folder.mkdir(parents=True, exist_ok=True)
    bin_name = name + ".bin"
    path = folder / bin_name
    with open(path, "wb") as f:
        f.write(ciphertext)

    now = datetime.utcnow().isoformat()
    cur = conn.cursor()
    existing = get_contract_by_token(token)
    if existing:
        cur.execute(
            """
            UPDATE reference_contracts
               SET filename=?, content_type=?, path=?, size_bytes=?,
                   uploaded_at=?, status='pending', status_updated_at=?, status_by=NULL,
                   consent_status='locked'
             WHERE token=?
            """,
            (name, getattr(uploaded_file, "type", None) or "application/octet-stream",
             str(path), size, now, now, token),
        )
    else:
        cur.execute(
            """
            INSERT INTO reference_contracts(token, tenant_id, filename, content_type, path, size_bytes,
                                            status, status_updated_at, status_by, uploaded_at, consent_status)
            VALUES (?,?,?,?,?,?, 'pending', ?, NULL, ?, 'locked')
            """,
            (token, tenant_id, name, getattr(uploaded_file, "type", None) or "application/octet-stream",
             str(path), size, now, now),
        )
    conn.commit()
    return True, "Uploaded."

def set_contract_status(token: str, status: str, by_email: str) -> tuple[bool, str]:
    status = (status or "").lower().strip()
    if status not in {"pending","verified","rejected"}:
        return False, "Invalid status."
    if not get_contract_by_token(token):
        return False, "No contract uploaded for this request."

    # Require landlord consent before any verification
    cur = conn.cursor()
    row = cur.execute("SELECT consent_status FROM reference_contracts WHERE token=?", (token,)).fetchone()
    consent = (row[0] if row else "locked")
    if consent != "consented" and status == "verified":
        return False, "Cannot verify: landlord consent is required."

    cur.execute(
        "UPDATE reference_contracts SET status=?, status_updated_at=?, status_by=? WHERE token=?",
        (status, datetime.utcnow().isoformat(), by_email, token),
    )
    conn.commit()

    # ⬇️ If contract is now verified, try to promote the reference
    if status == "verified":
        promote_reference_if_ready(token)

    return True, "Status updated."

def get_tenant_saved_preferences(tenant_id: int) -> dict | None:
    """
    Read the tenant_profiles preference fields WITHOUT checking open_to_rent.
    Returns a dict with keys (if columns exist): search_region, search_district, search_city,
    size_min, size_max, rooms_min, rooms_max, floor_min, floor_max, price_min, price_max
    """
    c = get_conn()
    try:
        cols = {r[1] for r in c.execute("PRAGMA table_info(tenant_profiles)").fetchall()}
    except Exception:
        return None

    # Determine id column in your tenant_profiles
    id_col = "tenant_id" if "tenant_id" in cols else ("user_id" if "user_id" in cols else None)
    if not id_col:
        return None

    wanted = [
        "search_region", "search_district", "search_city",
        "size_min", "size_max",
        "rooms_min", "rooms_max",
        "floor_min", "floor_max",
        "price_min", "price_max",
    ]
    select_cols = [cname for cname in wanted if cname in cols]
    if not select_cols:
        return None

    sql_cols = ", ".join([f'"{cname}"' for cname in select_cols])
    row = c.execute(f'SELECT {sql_cols} FROM tenant_profiles WHERE "{id_col}"=?', (tenant_id,)).fetchone()
    if not row:
        return None

    data = dict(zip(select_cols, row))

    # Normalize numerics to ints when possible
    for k in ["size_min","size_max","rooms_min","rooms_max","floor_min","floor_max","price_min","price_max"]:
        if k in data and data[k] is not None and data[k] != "":
            try:
                data[k] = int(data[k])
            except Exception:
                pass
    return data


def contract_status_badge(status: str) -> str:
    s = (status or "pending").lower()
    if s == "verified":
        return tr('✅ Verified Contract')
    if s == "rejected":
        return tr('❌ Rejected Contract')
    return tr('⏳ Pending Review')

def load_tenant_profile(tenant_id: int):
    cur = conn.cursor()
    cur.execute("SELECT future_landlord_email, updated_at FROM tenant_profiles WHERE tenant_id = ?", (tenant_id,))
    row = cur.fetchone()
    if row:
        return {"future_landlord_email": row[0], "updated_at": row[1]}
    return None


def upsert_tenant_profile(tenant_id: int, future_landlord_email: str | None):
    now = datetime.utcnow().isoformat()
    cur = conn.cursor()
    exists = load_tenant_profile(tenant_id)
    if exists:
        cur.execute(
            "UPDATE tenant_profiles SET future_landlord_email = ?, updated_at = ? WHERE tenant_id = ?",
            (future_landlord_email.strip() if future_landlord_email else None, now, tenant_id),
        )
    else:
        cur.execute(
            "INSERT INTO tenant_profiles(tenant_id, future_landlord_email, updated_at) VALUES (?,?,?)",
            (tenant_id, future_landlord_email.strip() if future_landlord_email else None, now),
        )
    conn.commit()


def add_previous_landlord(tenant_id: int, email: str, name: str, address: str): # afm: str,
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO previous_landlords(tenant_id, email, name, address, created_at) VALUES (?,?,?,?,?)",
        (tenant_id, email.strip(), name.strip(), address.strip(), datetime.utcnow().isoformat()),
    )
    conn.commit()


def list_previous_landlords(tenant_id: int): # afm,
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, name, address, created_at FROM previous_landlords WHERE tenant_id = ? ORDER BY id DESC",
        (tenant_id,),
    )
    return cur.fetchall()


def delete_previous_landlord(entry_id: int, tenant_id: int):
    cur = conn.cursor()
    cur.execute("DELETE FROM previous_landlords WHERE id = ? AND tenant_id = ?", (entry_id, tenant_id))
    conn.commit()

# ---------- References helpers ------------------------------------------
def load_contract_plaintext(token: str) -> bytes | None:
    """Return decrypted contract bytes if consented; else None."""
    contract = get_reference_request_by_token(token) and get_contract_by_token(token)
    contract = get_contract_by_token(token)
    if not contract:
        return None
    # Enforce landlord consent before allowing decryption
    cur = conn.cursor()
    row = cur.execute("SELECT consent_status FROM reference_contracts WHERE token=?", (token,)).fetchone()
    consent = (row[0] if row else "locked")
    if consent != "consented":
        return None
    try:
        with open(contract["path"], "rb") as f:
            cipher = f.read()
        from utils_vault import decrypt_bytes
        return decrypt_bytes(cipher)
    except Exception:
        return None
    
def generate_token() -> str:
    return uuid4().hex


def create_reference_request(tenant_id: int, prev_landlord_id: int, landlord_email: str) -> dict:
    token = generate_token()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reference_requests(token, tenant_id, prev_landlord_id, landlord_email, created_at, status) VALUES (?,?,?,?,?,?)",
        (token, tenant_id, prev_landlord_id, landlord_email, datetime.utcnow().isoformat(), 'pending'),
    )
    conn.commit()
    return {"token": token}


def get_reference_request_by_token(token: str):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, token, tenant_id, prev_landlord_id, landlord_email, created_at, status, filled_at, confirm_landlord, score, paid_on_time, utilities_unpaid, good_condition, comments FROM reference_requests WHERE token = ?",
        (token,),
    )
    row = cur.fetchone()
    if not row:
        return None
    keys = [
        "id","token","tenant_id","prev_landlord_id","landlord_email","created_at","status","filled_at",
        "confirm_landlord","score","paid_on_time","utilities_unpaid","good_condition","comments"
    ]
    return dict(zip(keys, row))
# ---------- Status helpers ----------
def effective_reference_status(raw_status: str | None, token: str) -> str:
    if raw_status in ("cancelled", "revoked"):
        return raw_status
    contract = get_contract_by_token(token)
    if contract and contract.get("status") != "verified":
        return "pending"
    return raw_status or "pending"



def promote_reference_if_ready(token: str) -> bool:
    """
    Promote a reference to 'completed' IFF:
      - the reference exists,
      - it's not already completed,
      - the contract for this token is VERIFIED,
      - and the landlord already submitted the reference (confirm_landlord=1).
    Returns True if a promotion happened.
    """
    details = get_reference_request_by_token(token)
    if not details or details["status"] == "completed":
        return False

    contract = get_contract_by_token(token)
    if not (contract and contract.get("status") == "verified"):
        return False

    # Make sure the form was actually submitted by the landlord.
    if not details.get("confirm_landlord"):
        return False

    cur = conn.cursor()
    cur.execute("UPDATE reference_requests SET status='completed' WHERE token=?", (token,))
    conn.commit()
    return True



def mark_reference_completed(token: str, confirm_landlord: bool, score: int,
                             paid_on_time: bool, utilities_unpaid: bool,
                             good_condition: bool, comments: str | None):
    # Gate completion on contract verification
    contract = get_contract_by_token(token)
    is_verified = bool(contract and contract.get("status") == "verified")
    new_status = "completed" if is_verified else "pending"

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE reference_requests
        SET status=?, filled_at=?, confirm_landlord=?, score=?, paid_on_time=?, utilities_unpaid=?, good_condition=?, comments=?
        WHERE token=?
        """,
        (
            new_status,
            datetime.utcnow().isoformat(),
            1 if confirm_landlord else 0,
            score,
            1 if paid_on_time else 0,
            1 if utilities_unpaid else 0,
            1 if good_condition else 0,
            comments.strip() if comments else None,
            token,
        ),
    )

    # If a contract exists for this token and is still locked, flip to 'consented' upon landlord's confirmation
    if confirm_landlord and contract:
        cur.execute("UPDATE reference_contracts SET consent_status='consented' WHERE token=? AND consent_status='locked'", (token,))

    conn.commit()

def list_reference_requests_global(status: str | None = None):
    """List reference requests across all users. If status is given, filter by it."""
    cur = conn.cursor()
    if status:
        cur.execute(
            "SELECT token, tenant_id, landlord_email, created_at, status, score "
            "FROM reference_requests WHERE status=? ORDER BY id DESC",
            (status,),
        )
    else:
        cur.execute(
            "SELECT token, tenant_id, landlord_email, created_at, status, score "
            "FROM reference_requests ORDER BY id DESC"
        )
    return cur.fetchall()


def list_reference_requests_for_tenant(tenant_id: int):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT rr.id, rr.token, rr.landlord_email, rr.created_at, rr.status, rr.score
        FROM reference_requests rr
        WHERE rr.tenant_id = ?
        ORDER BY rr.id DESC
        """,
        (tenant_id,),
    )
    return cur.fetchall()


def list_reference_requests_for_landlord(landlord_email: str, status: str | None = None):
    cur = conn.cursor()
    if status:
        cur.execute(
            "SELECT token, tenant_id, created_at, status, score FROM reference_requests WHERE landlord_email = ? AND status = ? ORDER BY id DESC",
            (landlord_email, status),
        )
    else:
        cur.execute(
            "SELECT token, tenant_id, created_at, status, score FROM reference_requests WHERE landlord_email = ? ORDER BY id DESC",
            (landlord_email,),
        )
    return cur.fetchall()

def cancel_reference_request(token: str):
    cur = conn.cursor()
    cur.execute(
        "UPDATE reference_requests "
        "SET status='cancelled', filled_at=? "
        "WHERE token=? AND status='pending'",
        (datetime.utcnow().isoformat(), token),
    )
    conn.commit()
    
def revoke_reference_request(token: str, admin_email: str, reason: str | None = None):
    """
    Mark a reference as 'revoked' with audit trail.
    Default policy: only allow revoking COMPLETED references.
    Change the WHERE clause to include 'pending' if you also want to allow that.
    """
    cur = conn.cursor()
    cur.execute(
        "UPDATE reference_requests "
        "SET status='revoked', revoked_at=?, revoked_by=?, revoked_reason=? "
        "WHERE token=? AND status='completed'",
        (datetime.utcnow().isoformat(), (admin_email or "").strip(), (reason or "").strip() or None, token),
    )
    conn.commit()


def list_prospective_tenants(landlord_email: str):
    """Unique tenants who listed this landlord (single field or multi list)."""
    cur = get_conn().cursor()
    cur.execute(
        """
        SELECT u.id, u.name, u.email, MAX(src.updated_at) AS last_update
        FROM (
            SELECT tp.tenant_id AS tenant_id, tp.updated_at AS updated_at
            FROM tenant_profiles tp
            WHERE LOWER(tp.future_landlord_email) = LOWER(?)
            UNION ALL
            SELECT flc.tenant_id AS tenant_id, COALESCE(flc.invited_at, flc.created_at) AS updated_at
            FROM future_landlord_contacts flc
            WHERE LOWER(flc.email) = LOWER(?)
        ) src
        JOIN users u ON u.id = src.tenant_id
        GROUP BY u.id, u.name, u.email
        ORDER BY last_update DESC
        """,
        (landlord_email, landlord_email),
    )
    return cur.fetchall()




#-----------HELPER FOR ADMIN AND TENANT DASHBOARD (BUILD REFERENCE LINK)------------------------------------------------

def build_reference_link(token: str) -> str:
    base = st.session_state.get("app_base_url") or (st.secrets.get("APP_BASE_URL") if hasattr(st, "secrets") else "")
    if base:
        base = base.strip().rstrip("/")
        return f"{base}/?ref={token}"
    # fallback that still works when clicked inside the app
    return f"?ref={token}"

#-----------------------------------------------------------------------------------------------------------------------------
#---------------EMAILS---------------------------------------------------------------------------------------------------------
#-STARTS HERE-----------------------------------------------------------------------------------------------------------------------------


def email_reference_request(
    tenant_name: str, tenant_email: str,
    landlord_email: str, link: str, address: str
):
    subject = f"RentRight • Αίτημα σύστασης για τον/την {tenant_name}"

    body = (
        "Καλησπέρα,\n\n"
        f"Ο/Η {tenant_name} ({tenant_email}) σας δήλωσε ως προηγούμενο ιδιοκτήτη "
        f"για το ακίνητο στη διεύθυνση: {address}.\n"
        "Ζητάει μια σύντομη σύσταση ενοικίασης.\n\n"
        "Τι χρειάζεται να κάνετε:\n"
        "1) Επιβεβαιώστε ότι ήσασταν ο ιδιοκτήτης\n"
        "2) Απαντήστε σε μερικές γρήγορες ερωτήσεις (≈1–2 λεπτά)\n\n"
        "Ανοίξτε την ασφαλή φόρμα εδώ:\n"
        f"{link}\n\n"
        "Γιατί το ζητάμε:\n"
        "- Οι απαντήσεις σας βοηθούν έναν μελλοντικό ιδιοκτήτη να επιβεβαιώσει "
        "ότι ο/η ενοικιαστής υπήρξε αξιόπιστος και συνεπής.\n"
        "- Χρησιμοποιούμε αυτές τις πληροφορίες μόνο για τη συγκεκριμένη σύσταση.\n\n"
        "Απόρρητο & ασφάλεια:\n"
        "- Οποιοδήποτε μισθωτήριο έχει ανεβάσει ο ενοικιαστής παραμένει κρυπτογραφημένο και κλειδωμένο.\n"
        "- Ξεκλειδώνεται μόνο εάν επιβεβαιώσετε ότι ήσασταν ο ιδιοκτήτης και αποκλειστικά για σκοπούς επαλήθευσης.\n"
        "- Δεν κοινοποιούμε τις απαντήσεις σας για άλλους σκοπούς.\n\n"
        "Αν ο σύνδεσμος δεν ανοίγει, αντιγράψτε και επικολλήστε τον στον περιηγητή σας.\n\n"
        "Για τυχόν ερωτήσεις, μπορείτε να απαντήσετε απευθείας σε αυτό το email.\n\n"
        "Σας ευχαριστούμε,\n"
        "Η ομάδα RentRight"
    )

    return send_email_smtp(landlord_email, subject, body)

def email_reference_cancellation_smtp(
    tenant_name: str,
    tenant_email: str,
    landlord_email: str,
    landlord_name: str | None,
    landlord_address: str | None,
    token: str,
    cancelled_at: str | None,
):
    subject = "Ακύρωση αιτήματος σύστασης — διαγραφή δεδομένων"
    body = f"""Καλησπέρα {landlord_name or 'σας'},

Ο/Η {tenant_name} ακύρωσε το αίτημα σύστασης ενοικίασης.

Τι σημαίνει αυτό:
• Ο σύνδεσμος σύστασης με το token {token} έχει πλέον απενεργοποιηθεί.
• Το ανεβασμένο μισθωτήριο συμβόλαιο διαγράφηκε οριστικά.
• Τυχόν απαντήσεις που υποβάλατε στη φόρμα σύστασης διαγράφηκαν οριστικά.

Διεύθυνση στο αρχείο: {landlord_address or '—'}
Ώρα ακύρωσης: {cancelled_at or '—'}

Για οποιαδήποτε απορία, μπορείτε να απαντήσετε στο {tenant_email}.
"""
    # Χρήση του υπάρχοντος SMTP helper
    return send_email_smtp(landlord_email, subject, body)

#-FINISH HERE-----------------------------------------------------------------------------------------------------------------------------





#------------------------------------------------------------------------------------------------------------------------------------    
#---------HELPER OF ADMIN DASHBOARD (SEARCH TENANTS)------------------------------------------------------------------------------- 
# STARTS HERE------------------------------------------------------------------------------------------------------------------------------------     

def cleanup_old_contracts(days_locked: int = 30, days_rejected: int = 30):
    """Delete encrypted blobs for expired locked/rejected contracts and mark as DELETED in place (path left dangling)."""
    import os
    from datetime import datetime, timedelta
    cur = conn.cursor()
    cutoff_locked   = (datetime.utcnow() - timedelta(days=days_locked)).isoformat()
    cutoff_rejected = (datetime.utcnow() - timedelta(days=days_rejected)).isoformat()

    # Locked & old
    rows = cur.execute("""
        SELECT token, path, uploaded_at FROM reference_contracts
        WHERE consent_status='locked' AND uploaded_at < ?
    """, (cutoff_locked,)).fetchall()
    for token, path, up_at in rows:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        # Mark as deleted by clearing path
        cur.execute("UPDATE reference_contracts SET path='', status='rejected' WHERE token=?", (token,))

    # Rejected & old
    rows = cur.execute("""
        SELECT token, path, uploaded_at FROM reference_contracts
        WHERE status='rejected' AND uploaded_at < ?
    """, (cutoff_rejected,)).fetchall()
    for token, path, up_at in rows:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        cur.execute("UPDATE reference_contracts SET path='' WHERE token=?", (token,))

    conn.commit()
    
# FINISH HERE------------------------------------------------------------------------------------------------------------------------------------     
    
#=============================================================================================
#DOCUMENTS

def render_tenant_documents_ui(current_user):
    # --- Light CSS for cards & badges (idempotent) ---
    st.markdown("""
    <style>
    .doc-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
    @media (max-width: 1100px){ .doc-grid{grid-template-columns:repeat(2,1fr)} }
    @media (max-width: 740px){ .doc-grid{grid-template-columns:1fr} }
    .pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.85rem;font-weight:600;border:1px solid;white-space:nowrap}
    .pill--ok{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}
    .pill--info{background:#eff6ff;color:#1e40af;border-color:#bfdbfe}
    .pill--err{background:#fef2f2;color:#7f1d1d;border-color:#fecaca}
    .row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .muted{color:#94a3b8;font-size:.85rem}
    .filename{font-weight:600}
    .file-row{display:flex;align-items:center;gap:10px;justify-content:space-between;border:1px solid #e5e7eb;padding:8px 10px;border-radius:10px;margin-bottom:6px;background:#fff}
    .file-left{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    </style>
    """, unsafe_allow_html=True)

    def _status_badge(status: str) -> str:
        s = (status or "").lower()
        if s == "verified":  return f'<span class="pill pill--ok">✅ {tr("Verified")}</span>'
        if s == "pending":   return f'<span class="pill pill--info">⏳ {tr("Pending")}</span>'
        return f'<span class="pill pill--err">❌ {tr("Rejected")}</span>'

    def _filesize(n):
        try:
            n = int(n)
        except Exception:
            return "—"
        for unit in ["B","KB","MB","GB"]:
            if n < 1024:
                return f"{n:.0f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    st.caption(tr("Upload documents for admin review. Documents are visible only to admins."))

    tab_up, tab_list = st.tabs([f"📤 {tr('Upload')}", f"📁 {tr('My documents')}"])

    # -------------------- TAB: Upload --------------------
    with tab_up:
        st.info(tr("Supported: PDF/PNG/JPG/WebP · up to 10 MB per file."))

        upload_specs = [
            ("payslip",              tr("Latest Payslips"),        tr("Add your 1–3 most recent ones.")),
            ("tax_return",           tr("Tax Return"),             tr("Used only to verify income.")),
            ("employment_contract",  tr("Employment Contract"),    tr("Photo or PDF of your contract."))
        ]
        icons = {
            "payslip": "💶",
            "tax_return": "📄",
            "employment_contract": "📝",
        }

        st.markdown('<div class="doc-grid">', unsafe_allow_html=True)
        for dtype, title, hint in upload_specs:
            icon = icons.get(dtype, "📎")
            with st.expander(f"{icon}  {title}", expanded=False):
                st.markdown(
                    f"<div style='color:#64748b; font-size:0.9rem;'>{hint}</div>"
                    "<hr style='margin:10px 0; border:none; height:1px; background:#f1f5f9;'>",
                    unsafe_allow_html=True
                )

                # Multi-upload form
                with st.form(key=f"form_{dtype}", clear_on_submit=True):
                    files = st.file_uploader(
                        label="",  # remove label bar
                        type=["pdf","png","jpg","jpeg","webp"],
                        key=f"up_{dtype}",
                        label_visibility="hidden",
                        accept_multiple_files=True,
                    )
                    submitted = st.form_submit_button("💾 " + tr("Save"))
                    if submitted:
                        if not files:
                            st.warning(tr("Please select at least one file before saving."))
                        else:
                            any_error = False
                            for uf in files:
                                size_ok = getattr(uf, "size", None)
                                if size_ok is not None and size_ok > 10 * 1024 * 1024:
                                    st.error(tr("One of the files exceeds the 10 MB limit: ") + f"{uf.name}")
                                    any_error = True
                            if not any_error:
                                saved = 0
                                for uf in files:
                                    try:
                                        td_save_upload(current_user["id"], dtype, uf)
                                        saved += 1
                                    except Exception as e:
                                        st.error(tr("Upload failed for {name}: {err}").format(name=uf.name, err=e))
                                        any_error = True
                                if saved and not any_error:
                                    st.success(f"✅ {saved} " + tr("file(s) uploaded. Status: Pending."))
                                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # -------------------- TAB: My documents --------------------
    with tab_list:
        rows = td_list_for_tenant(current_user["id"])
        if not rows:
            st.info(tr("You haven't uploaded any documents yet."))
            return

        from collections import defaultdict
        by_type = defaultdict(list)
        for r in rows:
            by_type[r["doc_type"]].append(r)
        for k in list(by_type.keys()):
            by_type[k].sort(key=lambda x: x["uploaded_at"], reverse=True)

        for dtype in ["payslip","tax_return","employment_contract"]:
            docs = by_type.get(dtype, [])
            if not docs:
                continue

            label = tr(DOC_TYPES.get(dtype, dtype))
            st.markdown(f"### {label}")

            # Show all files for this type, most recent first
            for r in docs:
                with st.container(border=True):
                    left, right = st.columns([5, 2], vertical_alignment="center")
                    with left:
                        st.markdown(
                            f"""
                            <div class="file-left">
                              {_status_badge(r['status'])}
                              <span class="filename">{r['filename']}</span>
                              <span class="muted">• {tr('Uploaded')}: {format_dt(r['uploaded_at'])}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    with right:
                        # Download (if we can read bytes)
                        try:
                            data = td_read_bytes(r["id"])
                        except Exception:
                            data = None
                        if data:
                            st.download_button(
                                tr("Download"),
                                data=data,
                                file_name=r["filename"] or f"{dtype}.pdf",
                                mime="application/octet-stream",
                                key=f"dl_{r['id']}"
                            )

                        # Delete with 2-step confirmation
                        ckey = f"confirm_del_{r['id']}"
                        if st.session_state.get(ckey):
                            c1, c2 = st.columns([4,4])
                            with c1:
                                if st.button("🗑️" + tr("Confirm"), key=f"do_del_{r['id']}", type="primary"):
                                    ok, msg = td_delete(r["id"], current_user["id"])
                                    if ok:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            with c2:
                                if st.button(tr("Cancel"), key=f"cancel_del_{r['id']}"):
                                    st.session_state[ckey] = False
                                    st.rerun()
                        else:
                            if st.button("🗑️ ", key=f"ask_del_{r['id']}"):
                                st.session_state[ckey] = True
                                st.rerun()

            st.divider()


#---------TENANT DASHBOARD HELPERS---------------------------------------------------
#-STARTS HERE-----------------------------------------------------------------------

        
def delete_previous_landlord_completely(tenant_id: int, prev_landlord_id: int):
    """
    Fully remove a previous landlord and ALL related data for this tenant.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT token FROM reference_requests WHERE tenant_id=? AND prev_landlord_id=?",
        (tenant_id, prev_landlord_id),
    )
    tokens = [r[0] for r in cur.fetchall()]

    for tok in tokens:
        try: delete_landlord_responses(tok)
        except Exception: pass
        try: delete_contract_hard(tok)
        except Exception: pass
        cur.execute("DELETE FROM reference_requests WHERE token=?", (tok,))

    delete_previous_landlord(prev_landlord_id, tenant_id)
    conn.commit()

def list_future_landlord_contacts(tenant_id: int):
    """
    Unified contacts list for the tenant:
    - Landlords/Agents from future_landlord_contacts
    - Tenants from tenant_peers
    Always returns 7-tuple:
      (id, email, created_at, invited, invited_at, inbound_request, inbound_requested_at)

    NOTE: For tenant-peers we encode the contact "id" as NEGATIVE(other_tenant_id).
    This lets tenant_contacts() call remove_future_landlord_contact() unchanged.
    """
    c = get_conn()
    cur = c.cursor()

    # --- Landlords & Agents (exclude emails that belong to TENANTS) ---
    cur.execute(
        """
            SELECT c.id, c.email, c.created_at, c.invited, c.invited_at,
                COALESCE(c.inbound_request, 0) AS inbound_request,
                c.inbound_requested_at
            FROM future_landlord_contacts AS c
            LEFT JOIN users u ON LOWER(u.email) = LOWER(c.email)
            WHERE c.tenant_id = ?
            ORDER BY c.id DESC

        """,
        (tenant_id,),
    )
    la_rows = list(cur.fetchall())

    # --- Tenants (from tenant_peers) -> map to the same 7-tuple shape ---
    cur.execute(
        """
        SELECT
            CASE WHEN a_tenant_id = ? THEN b_tenant_id ELSE a_tenant_id END AS other_tid,
            tp.created_at,
            tp.initiator_id,
            tp.status
        FROM tenant_peers tp
        WHERE (tp.a_tenant_id = ? OR tp.b_tenant_id = ?)
          AND tp.status IN ('pending','connected')
        """,
        (tenant_id, tenant_id, tenant_id),
    )
    tenant_peers_raw = cur.fetchall()

    tenant_rows = []
    for other_tid, created_at, initiator_id, status in tenant_peers_raw:
        # resolve the other tenant's email
        u = c.execute("SELECT email FROM users WHERE id=?", (other_tid,)).fetchone()
        other_email = u[0] if u else None

        # map tenant-peers state to invited/inbound flags (pending only)
        invited = 1 if (status == "pending" and initiator_id == tenant_id) else 0
        inbound_request = 1 if (status == "pending" and initiator_id != tenant_id) else 0
        invited_at = created_at if invited else None
        inbound_requested_at = created_at if inbound_request else None

        # NEGATIVE id encodes "this is a tenant contact"
        contact_id = -int(other_tid)

        tenant_rows.append((
            contact_id,                 # id (negative → tenant)
            other_email,                # email
            created_at,                 # created_at
            invited,                    # invited (0/1)
            invited_at,                 # invited_at
            inbound_request,            # inbound_request (0/1)
            inbound_requested_at,       # inbound_requested_at
        ))

    # merge + sort by most-recent activity we have
    def _ts(x):
        # x[2] = created_at; x[6] = inbound_requested_at; x[4] = invited_at
        return (x[6] or x[4] or x[2] or "")
    merged = la_rows + tenant_rows
    merged.sort(key=_ts, reverse=True)
    return merged


def remove_future_landlord_contact(contact_id: int, tenant_id: int):
    """
    Remove a contact regardless of type, and clean up the counterpart if it exists:
      - If contact_id > 0 → remove FLC row; also drop tenant_peers if that email is a tenant.
      - If contact_id < 0 → remove tenant_peers; also drop any FLC row for that tenant's email.
    """
    c = get_conn()
    cur = c.cursor()

    if contact_id < 0:
        # Tenant contact encoded as NEGATIVE(other_tenant_id)
        other_tid = -contact_id
        a, b = (tenant_id, other_tid) if tenant_id < other_tid else (other_tid, tenant_id)
        # delete the tenant_peers row regardless of order
        cur.execute("DELETE FROM tenant_peers WHERE a_tenant_id=? AND b_tenant_id=?", (a, b))

        # ALSO: remove any FLC row pointing at that tenant's email
        row = cur.execute("SELECT email FROM users WHERE id=?", (other_tid,)).fetchone()
        if row and row[0]:
            cur.execute("DELETE FROM future_landlord_contacts WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
                        (tenant_id, row[0]))
    else:
        # Landlord/agent contact
        # Fetch email first so we can check if it's actually a tenant
        row = cur.execute(
            "SELECT email FROM future_landlord_contacts WHERE id = ? AND tenant_id = ?",
            (contact_id, tenant_id)
        ).fetchone()
        cur.execute(
            "DELETE FROM future_landlord_contacts WHERE id = ? AND tenant_id = ?",
            (contact_id, tenant_id),
        )
        if row and row[0]:
            u = get_user_by_email(row[0])
            if u and (u.get("role") or "").lower() == "tenant":
                other_tid = u["id"]
                a, b = (tenant_id, other_tid) if tenant_id < other_tid else (other_tid, tenant_id)
                cur.execute("DELETE FROM tenant_peers WHERE a_tenant_id=? AND b_tenant_id=?", (a, b))

    c.commit()

    
#-FINISH HERE-----------------------------------------------------------------------

# ===============================================================================================================================    
# ========== LANDLORD DASHBOARD HELPERS =======================================================================================
# STARTS HERE ==================================================================================================================
# ------------ Tenant Document Badges (Landlord view) ------------------------------
def _has_tenant_docs_table() -> bool:
    try:
        c = get_conn()
        cols = {r[1] for r in c.execute("PRAGMA table_info(tenant_documents)").fetchall()}
        return bool(cols)
    except Exception:
        return False

def _td_doc_statuses_for_tenant(tenant_id: int):
    """
    Returns a dict {doc_type: 'verified'|'pending'|'rejected'} consolidated per type.
    Priority: verified > pending > rejected.
    Returns {} if no rows. Returns None if table doesn't exist.
    """
    if not _has_tenant_docs_table():
        return None
    c = get_conn()
    rows = c.execute("SELECT doc_type, status FROM tenant_documents WHERE tenant_id=?", (tenant_id,)).fetchall()
    if not rows:
        return {}
    prio = {"verified": 3, "pending": 2, "rejected": 1}
    agg = {}
    for doc_type, status in rows:
        s = (status or "").lower()
        if s not in prio:
            continue
        if doc_type not in agg or prio[s] > prio.get(agg[doc_type], 0):
            agg[doc_type] = s
    return agg

_DOC_LABELS_EL = {
    "payslip": "Μισθοδοσίες",
    "tax_return": "Εκκαθαριστικό",
    "employment_contract": "Σύμβαση Εργασίας",
}

def render_tenant_doc_badges_inline(tenant_id: int):
    """
    Inline pills with verification status for landlord's contacts card.
    """
    statuses = _td_doc_statuses_for_tenant(tenant_id)
    if statuses is None:
        # table missing → do nothing
        return
    order = ["payslip", "tax_return", "employment_contract"]
    chips = []
    for dt in order:
        s = statuses.get(dt, None)
        label = _DOC_LABELS_EL.get(dt, dt)
        if s == "verified":
            chips.append(f'<span class="pill pill-ok">✅ {label}</span>')
        elif s == "pending":
            chips.append(f'<span class="pill">⏳ {label}</span>')
        elif s == "rejected":
            chips.append(f'<span class="pill pill-no">❌ {label}</span>')
        else:
            # not provided → neutral/NA
            chips.append(f'<span class="pill pill-na">— {label}</span>')
    if not chips:
        return
    html = (
        '<div style="display:flex;align-items:center;gap:10px;margin:4px 0 0 0">'
        f'  <div>{" ".join(chips)}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def list_latest_references_for_tenant(tenant_id: int):
    """Return each previous landlord with the latest (most recent) reference request, if any, and its answers."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pl.id AS prev_id,
               pl.name AS prev_name,
               pl.email AS prev_email,
               pl.address AS prev_address,
               rr.token,
               rr.status,
               rr.score,
               rr.paid_on_time,
               rr.utilities_unpaid,
               rr.good_condition,
               rr.comments,
               rr.created_at,
               rr.filled_at
        FROM previous_landlords pl
        LEFT JOIN reference_requests rr
          ON rr.prev_landlord_id = pl.id
         AND rr.tenant_id = pl.tenant_id
         AND rr.id = (
              SELECT MAX(id) FROM reference_requests
               WHERE prev_landlord_id = pl.id AND tenant_id = pl.tenant_id
           )
        WHERE pl.tenant_id = ?
        ORDER BY pl.id DESC
        """,
        (tenant_id,),
    )
    return cur.fetchall()


def list_latest_references_for_tenant_dict(tenant_id: int) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            pl.id            AS prev_id,
            pl.name          AS prev_name,
            pl.email         AS prev_email,
            pl.afm           AS prev_afm,
            pl.address       AS prev_addr,
            rr.token         AS token,
            rr.status        AS status,
            rr.score         AS score,
            rr.paid_on_time  AS paid_on_time,
            rr.utilities_unpaid AS utilities_unpaid,
            rr.good_condition   AS good_condition,
            rr.comments      AS comments,
            rr.created_at    AS created_at,
            rr.filled_at     AS filled_at
        FROM previous_landlords pl
        LEFT JOIN reference_requests rr
          ON rr.prev_landlord_id = pl.id
         AND rr.tenant_id       = pl.tenant_id
         AND rr.id = (
              SELECT MAX(id)
              FROM reference_requests
              WHERE prev_landlord_id = pl.id AND tenant_id = pl.tenant_id
          )
        WHERE pl.tenant_id = ?
        ORDER BY pl.id DESC
        """,
        (tenant_id,),
    )
    rows = cur.fetchall()  # sqlite3.Row objects
    return [dict(r) for r in rows]


def search_open_to_rent_tenants(
    q: str | None = None,
    region: str | None = None,
    city: str | None = None,
    district: str | None = None,
    size_min: int | None = None, size_max: int | None = None,
    rooms_min: int | None = None, rooms_max: int | None = None,
    floor_min: int | None = None, floor_max: int | None = None,
    price_min: int | None = None, price_max: int | None = None,
    limit: int = 100
):
    """
    Return tenants with open_to_rent=1 matching free-text (name/email)
    and optional filters (city/district + range overlaps for size/rooms/floor/price).
    """
    cur = conn.cursor()

    clauses = ["tp.open_to_rent = 1"]
    params = {}
    
    cols = {r[1] for r in cur.execute("PRAGMA table_info(tenant_profiles)").fetchall()}
    # Free-text on users.name / users.email
    if q:
        clauses.append("(LOWER(u.name) LIKE LOWER(:q) OR LOWER(u.email) LIKE LOWER(:q))")
        params["q"] = f"%{q.strip()}%"

    if "search_region" in cols and region:
        clauses.append("LOWER(tp.search_region) = LOWER(:region)")
        params["region"] = region.strip()

    if city:
        clauses.append("LOWER(tp.search_city) = LOWER(:city)")
        params["city"] = city.strip()
    if district:
        clauses.append("LOWER(tp.search_district) = LOWER(:district)")
        params["district"] = district.strip()


    # Range-overlap logic:
    # For each dimension, show a tenant if their preferred range overlaps the landlord's filter range.
    def add_range_overlap(field_min: str, field_max: str, f_min_val, f_max_val):
        # Only add a WHERE if at least one bound provided
        if f_min_val is None and f_max_val is None:
            return
        # NULLs in tenant prefs mean "no bound" → use huge defaults via COALESCE
        # Overlap condition: (tenant_max >= filter_min) AND (tenant_min <= filter_max)
        cmin = f"COALESCE(tp.{field_min}, -9999999)"
        cmax = f"COALESCE(tp.{field_max},  9999999)"

        if f_min_val is not None:
            clauses.append(f"{cmax} >= :{field_min}_needs_at_least")
            params[f"{field_min}_needs_at_least"] = int(f_min_val)
        if f_max_val is not None:
            clauses.append(f"{cmin} <= :{field_max}_needs_at_most")
            params[f"{field_max}_needs_at_most"] = int(f_max_val)

    add_range_overlap("size_min",  "size_max",  size_min,  size_max)
    add_range_overlap("rooms_min", "rooms_max", rooms_min, rooms_max)
    add_range_overlap("floor_min", "floor_max", floor_min, floor_max)
    add_range_overlap("price_min", "price_max", price_min, price_max)

    where_sql = " AND ".join(clauses) if clauses else "1=1"

    sql = f"""
        SELECT
            u.id            AS tenant_id,
            u.name          AS tenant_name,
            u.email         AS tenant_email,
            tp.updated_at   AS prefs_updated_at,

            tp.search_city, tp.search_district,
            tp.size_min, tp.size_max,
            tp.rooms_min, tp.rooms_max,
            tp.floor_min, tp.floor_max,
            tp.price_min, tp.price_max
        FROM tenant_profiles tp
        JOIN users u ON u.id = tp.tenant_id
        WHERE {where_sql}
        ORDER BY tp.updated_at DESC
        LIMIT :limit
    """
    params["limit"] = int(limit)
    cur.execute(sql, params)
    return cur.fetchall()

def quick_reference_summary(tenant_id: int):
    """
    Returns compact info for search cards + normalized answers for latest completed ref.
    """
    try:
        refs = list_latest_references_for_tenant_dict(tenant_id) or []
    except Exception:
        refs = []

    # Ignore cancelled refs
    refs = [r for r in refs if (r.get("status") or "").lower() != "cancelled"]

    if not refs:
        return {
            "have": False, "total": 0, "latest_status": None,
            "latest_score": None, "avg_score": None, "completed_count": 0,
            "latest_answers": None,
        }

    total = len(refs)
    latest = refs[0]  # expected latest-first
    latest_status = (latest.get("status") or "").strip()
    latest_is_completed = (latest_status or "").lower() == "completed"
    latest_score = latest.get("score") if latest_is_completed else None

    completed = [r for r in refs if (r.get("status") or "").lower() == "completed"]
    scores = [r.get("score") for r in completed if r.get("score") is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    latest_answers = None
    if latest_is_completed:
        latest_answers = {
            "paid_on_time":     _to_bool(latest.get("paid_on_time")),
            "utilities_unpaid": _to_bool(latest.get("utilities_unpaid")),
            "good_condition":   _to_bool(latest.get("good_condition")),
            "comments":         latest.get("comments"),
            "prev_email":       latest.get("prev_email"),
        }

    return {
        "have": True,
        "total": total,
        "latest_status": latest_status,
        "latest_score": latest_score,
        "avg_score": avg_score,
        "completed_count": len(completed),
        "latest_answers": latest_answers,
    }


# FINISH HERE ==================================================================================================================

#--------------------------------------------------------------------------------------------------------------------------------
# ---------- Landlord Reference Portal (public) ---------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------------------------

def reference_portal(token: str):
    # ✅ If redirected after submit, show ONLY the success message and stop
    if (st.query_params.get("done") == "1"):
        st.success(tr("Reference submitted successfully. Thank you!"))
        return

    st.title(tr('🏠 RentRight — Landlord Reference Portal'))
    data = get_reference_request_by_token(token)
    if not data:
        st.error(tr('Invalid or expired reference token.'))
        return

    # If you still want to block re-submissions once DB is completed:
    if data["status"] == "completed":
        st.success(tr('This reference has already been submitted. Thank you!'))
        st.stop()
        
    # --- Fetch tenant name & email
    tenant = get_user_by_id(data["tenant_id"])
    tenant_name = tenant["name"] if tenant else f"Tenant #{data['tenant_id']}"
    tenant_email = tenant["email"] if tenant else "—"

    # --- Fetch the address from previous_landlords via prev_landlord_id
    address = "—"
    if data.get("prev_landlord_id"):
        cur = conn.cursor()
        cur.execute("SELECT address FROM previous_landlords WHERE id=?", (data["prev_landlord_id"],))
        row = cur.fetchone()
        if row:
            address = row[0]

    # --- Info banner with richer details
    st.info(
        f"{tr('Reference for')} **{tenant_name}** ({tenant_email})\n\n"
        f"📍 {tr('Address')}: {address}"
        )

    with st.form("reference_form"):
        # ✅ Short attestation + limited consent (no contract shown to landlord)
        confirm = st.checkbox(
            tr("I confirm I was the landlord for this tenant and consent to the use and disclosure of my full name solely for verification of this reference.")
        )

        # Context line with placeholders (avoids PII inside the checkbox itself)
        st.caption(
            tr("Tenant: {tenant_name} — Address: {address}")
            .format(tenant_name=tenant_name, address=address)
        )

        # Transparency (legitimate interests + right to object)
        with st.expander(tr("Privacy & verification details")):
            p = tr("RentRight processes your responses, and if the tenant has uploaded a tenancy contract, may decrypt and review it after your confirmation solely to verify this reference (lawful basis: legitimate interests). The contract remains encrypted and is not shown to you. You may object at any time as described in the Privacy Notice.")
            if st.session_state.get("privacy_url"):
                p += f" {tr('Privacy Notice')}: {st.session_state['privacy_url']}"
            st.write(p)


        score = st.slider(tr('Overall tenant score'), min_value=1, max_value=10, value=8)
        paid_on_time = st.radio(tr('Did the tenant pay on time?'), [tr("Yes"),tr("No")], horizontal=True)
        utilities_unpaid = st.radio(tr('Did the tenant leave utilities unpaid?'), [tr("No"),tr("Yes")], horizontal=True)
        good_condition = st.radio(tr('Did the tenant leave the apartment in good condition?'), [tr("Yes"),tr("No")], horizontal=True)
        comments = st.text_area(tr('Optional comments'))

        col_a, col_b = st.columns([1, 1])
        submit = col_a.form_submit_button(tr('Submit Reference'))
        cancel_btn = col_b.form_submit_button(tr('Not My Tenant / Cancel'))

    if submit:
        if not confirm:
            st.error(tr('Please confirm you were the landlord.'))
            return

        mark_reference_completed(
            token,
            confirm_landlord=True,
            score=int(score),
            paid_on_time=(paid_on_time == "Yes"),
            utilities_unpaid=(utilities_unpaid == "Yes"),
            good_condition=(good_condition == "Yes"),
            comments=comments,
        )

        # redirect to a thank-you page
        try:
            st.query_params.clear()
            st.query_params["page"] = "submitted"
        except Exception:
            st.experimental_set_query_params(page="submitted")
        st.rerun()

    if cancel_btn:
        # landlord says “not my tenant” → just cancel the request
        cancel_reference_request(token)
        try:
            st.query_params.clear()
            st.query_params["page"] = "cancelled"
        except Exception:
            st.experimental_set_query_params(page="cancelled")
        st.rerun()

#------------------------------------------------------------------------------------------------------------------------------
#-----------ADMIN DASHBOARD----------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------------------------


def render_admin_verifications_ui(current_user):
    st.header("Έγγραφα προς Επαλήθευση (Tenants)")
    pending = td_list_pending()
    if not pending:
        st.success("Καμία εκκρεμότητα.")
        return
    for row in pending:
        title = f"{DOC_TYPES.get(row['doc_type'], row['doc_type'])} • {row['filename']} — {row['name']} <{row['email']}> • {format_dt(row['uploaded_at'])}"
        with st.expander(title):
            if st.button("Προεπισκόπηση", key=f"prev_{row['id']}"):
                data = td_read_bytes(row["id"])
                if data:
                    if str(row["filename"]).lower().endswith((".png",".jpg",".jpeg",".webp")):
                        st.image(data)
                    else:
                        st.download_button("Λήψη αρχείου", data=data, file_name=row["filename"])
                else:
                    st.warning("Δεν βρέθηκε αρχείο.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Επιβεβαίωση (Verify)", key=f"ok_{row['id']}"):
                    td_set_status(row["id"], "verified", current_user["id"])
                    st.success("Επιβεβαιώθηκε.")
                    st.rerun()
            with c2:
                if st.button("❌ Απόρριψη (Reject)", key=f"rej_{row['id']}"):
                    td_set_status(row["id"], "rejected", current_user["id"])
                    st.info("Απορρίφθηκε.")
                    st.rerun()

def render_admin_documents_tabs(current_user):
    st.subheader(tr("Tenant Documents Review"))

    # Map “Completed/Cancelled” wording to our doc statuses
    tabs = st.tabs([tr("Pending"), tr("Completed"), tr("Cancelled")])

    # Pending = pending
    with tabs[0]:
        rows = td_list_by_status("pending")
        if not rows:
            st.info(tr("No actions"))
        for r in rows:
            title = f"{DOC_TYPES.get(r['doc_type'], r['doc_type'])} • {r['filename']} — {r['name']} <{r['email']}> • {format_dt(r['uploaded_at'])}"
            with st.expander(title, expanded=False):
                # Preview/Download
                if st.button(tr("Preview"), key=f"prev_p_{r['id']}"):
                    data = td_read_bytes(r["id"])
                    if data:
                        if str(r["filename"]).lower().endswith((".png",".jpg",".jpeg",".webp")):
                            st.image(data)
                        else:
                            st.download_button(tr("Download"), data=data, file_name=r["filename"])
                    else:
                        st.warning(tr("Can’t read the saved file"))
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ " + tr("Verify"), key=f"ok_p_{r['id']}"):
                        td_set_status(r["id"], "verified", current_user["id"])
                        st.success(tr("Verified"))
                        st.rerun()
                with c2:
                    if st.button("❌ " + tr("Reject"), key=f"rej_p_{r['id']}"):
                        td_set_status(r["id"], "rejected", current_user["id"])
                        st.info(tr("Rejected."))
                        st.rerun()

    # Completed = verified
    with tabs[1]:
        rows = td_list_by_status("verified")
        if not rows:
            st.info(tr("No actions"))
        for r in rows:
            subtitle = f"{DOC_TYPES.get(r['doc_type'], r['doc_type'])} • {r['filename']} — {r['name']} <{r['email']}>"
            meta = f"{tr('Created')}: {format_dt(r['uploaded_at'])} · {tr('Updated')}: {format_dt(r['status_updated_at'])}"
            with st.expander(subtitle + " • " + meta, expanded=False):
                # Always allow seeing the file again
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(tr("Preview"), key=f"prev_v_{r['id']}"):
                        data = td_read_bytes(r["id"])
                        if data:
                            if str(r["filename"]).lower().endswith((".png",".jpg",".jpeg",".webp")):
                                st.image(data)
                            else:
                                st.download_button(tr("Download"), data=data, file_name=r["filename"])
                        else:
                            st.warning(tr("Can’t read the saved file"))

                with c2:
                    if st.button("❌ " + tr("Reject"), key=f"rej_v_{r['id']}"):
                        td_set_status(r["id"], "rejected", current_user["id"])
                        st.info(tr("Rejected."))
                        st.rerun()

    # Cancelled = rejected
    with tabs[2]:
        rows = td_list_by_status("rejected")
        if not rows:
            st.info(tr("No actions"))
        for r in rows:
            subtitle = f"{DOC_TYPES.get(r['doc_type'], r['doc_type'])} • {r['filename']} — {r['name']} <{r['email']}>"
            meta = f"{tr('Created')}: {format_dt(r['uploaded_at'])} · {tr('Updated')}: {format_dt(r['status_updated_at'])}"
            with st.expander(subtitle + " • " + meta, expanded=False):
                # Always allow seeing the file again
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(tr("Preview"), key=f"prev_r_{r['id']}"):
                        data = td_read_bytes(r["id"])
                        if data:
                            if str(r["filename"]).lower().endswith((".png",".jpg",".jpeg",".webp")):
                                st.image(data)
                            else:
                                st.download_button(tr("Download"), data=data, file_name=r["filename"])
                        else:
                            st.warning(tr("Can’t read the saved file"))
                with c2:
                    if st.button("✅ " + tr("Verify"), key=f"ok_r_{r['id']}"):
                        td_set_status(r["id"], "verified", current_user["id"])
                        st.success(tr("Verified"))
                        st.rerun()

def migrate_flc_tenants_to_peers(dry_run: bool = False):
    """
    Move tenant emails from future_landlord_contacts -> tenant_peers (pending).
    Idempotent: uses tp_request() and your PK(a_tenant_id,b_tenant_id) to avoid dupes.
    Returns counts for logging.
    """
    c = get_conn()
    rows = c.execute("""
        SELECT flc.id AS flc_id, flc.tenant_id AS me_id, u.id AS other_tid
        FROM future_landlord_contacts flc
        JOIN users u ON LOWER(u.email)=LOWER(flc.email)
        WHERE TRIM(LOWER(u.role))='tenant'
    """).fetchall()

    migrated = 0
    deleted  = 0
    for r in rows:
        flc_id   = int(r["flc_id"])
        me_id    = int(r["me_id"])
        other_id = int(r["other_tid"])

        if not dry_run:
            # create/refresh a roommate request (pending) using your app logic
            try:
                tp_request(inviter_id=me_id, invitee_id=other_id)
            except Exception:
                pass
            # remove the old FLC row
            c.execute("DELETE FROM future_landlord_contacts WHERE id=?", (flc_id,))
            deleted += 1

        migrated += 1

    if not dry_run:
        c.commit()
        try:
            st.cache_data.clear()
        except Exception:
            pass
    return {"found": len(rows), "migrated": migrated, "deleted": deleted}



def admin_dashboard():
    # periodic cleanup on admin view
    try:
        cleanup_old_contracts()
    except Exception:
        pass
    
    
    st.caption(f"{tr('Logged in as')} {st.session_state.user['email']}")

    st.divider()
    render_admin_documents_tabs(st.session_state.user)
    st.divider()
    
    with st.expander("Maintenance (admins)", expanded=False):
        c1, c2 = st.columns(2)
    if c1.button("Dry run: preview migration"):
        res = migrate_flc_tenants_to_peers(dry_run=True)
        st.info(f"Would migrate {res['found']} contacts.")
    if c2.button("Run migration now"):
        res = migrate_flc_tenants_to_peers(dry_run=False)
        st.success(f"Migrated {res['migrated']} and deleted {res['deleted']} old rows.")
        st.rerun()


    # ---------------- Settings moved from sidebar ----------------
    with st.expander(tr('Email & App Settings')):
        st.subheader(tr('Email Settings (SMTP)'))
        st.session_state.smtp_host = st.text_input("SMTP host", value=st.session_state.get("smtp_host", ""))
        st.session_state.smtp_port = st.number_input("SMTP port", value=int(st.session_state.get("smtp_port", 587)))
        st.session_state.smtp_user = st.text_input("SMTP username", value=st.session_state.get("smtp_user", ""))
        st.session_state.smtp_pass = st.text_input("SMTP password", type="password", value=st.session_state.get("smtp_pass", ""))
        st.session_state.smtp_from = st.text_input("From email (optional)", value=st.session_state.get("smtp_from", ""))
        st.session_state.smtp_tls = st.checkbox("Use TLS", value=st.session_state.get("smtp_tls", True))

        st.markdown("---")
        st.subheader(tr('App Base URL'))
        st.session_state.app_base_url = st.text_input(
            tr('Base URL for Links'),
            value=st.session_state.get("app_base_url", ""),
            help="e.g., https://yourdomain.com"
        )
                # --- SMTP quick test ---
        st.markdown("---")
        st.caption(tr('Send Test Email'))
        test_to = st.text_input(
            tr('Send test to'),
            value=st.session_state.get("smtp_user", ""),
            key="admin_test_to",
        )
        if st.button(tr('Send test email'), key="admin_send_test_email"):
            try:
                ok, msg = send_email_smtp(
                    to_email=test_to,
                    subject="RentRight SMTP Test",
                    body="If you received this email, your SMTP configuration is working. ✅",
                )
            except NameError:
                # Fallback si no existe send_email_smtp()
                host = st.session_state.get("smtp_host")
                port = int(st.session_state.get("smtp_port", 587))
                user = st.session_state.get("smtp_user")
                pwd = st.session_state.get("smtp_pass")
                from_email = st.session_state.get("smtp_from") or user
                use_tls = st.session_state.get("smtp_tls", True)
                try:
                    _msg = MIMEText("If you received this email, your SMTP configuration is working. ✅", "plain")
                    _msg["Subject"] = "RentRight SMTP Test"
                    _msg["From"] = from_email
                    _msg["To"] = test_to
                    server = smtplib.SMTP(host, port, timeout=15)
                    if use_tls:
                        server.starttls()
                    server.login(user, pwd)
                    server.sendmail(from_email, [test_to], _msg.as_string())
                    server.quit()
                    ok, msg = True, "sent"
                except Exception as e:
                    ok, msg = False, f"{type(e).__name__}: {e}"

            if ok:
                st.success(tr('Test email sent successfully.'))
            else:
                st.error(f"{tr('Failed to send email:')} {msg}")

    st.markdown("---")

    # ---------------- Pending references management ----------------
    st.subheader(tr('Pending References (All Tenants)'))

    # Pull everything, then compute effective status using contract state
    all_reqs = list_reference_requests_global()
    def eff(rec):
        token, tenant_id, landlord_email, created_at, status, score = rec
        return effective_reference_status(status, token)

    pending_reqs   = [r for r in all_reqs if eff(r) == "pending"]
    completed_reqs = [r for r in all_reqs if eff(r) == "completed"]
    cancelled_reqs = [r for r in all_reqs if eff(r) in ("cancelled", "revoked")]

    c1, c2, c3 = st.columns(3)
    c1.metric(tr("Pending"), len(pending_reqs))
    c2.metric(tr("Completed"), len(completed_reqs))
    c3.metric(tr('Cancelled'), len(cancelled_reqs))

    tab_pending, tab_completed, tab_cancelled = st.tabs([tr('Pending'), tr('Completed'), tr('Cancelled')])
    

    def render_admin_reqs(reqs, prefix: str):
        if not reqs:
            st.info(tr('No requests available.'))
            return

        for (token, tenant_id, landlord_email, created_at, status, score) in reqs:
            tenant = get_user_by_id(tenant_id)
            tenant_label = tenant["name"] if tenant else f"Tenant #{tenant_id}"
            final_status = effective_reference_status(status, token)

            # Fetch request details and previous landlord info
            details = get_reference_request_by_token(token)
            pl_name = pl_email = pl_addr = "—"
            if details and details.get("prev_landlord_id"):
                cur = conn.cursor()
                cur.execute(
                    "SELECT name, email, address FROM previous_landlords WHERE id=?",
                    (details["prev_landlord_id"],),
                )
                row = cur.fetchone()
                if row:
                    pl_name, pl_email, pl_addr = row

            
            with st.container(border=True):
                cols = st.columns([3, 3, 3, 2])

                # Localized display status
                display_status = {
                    "pending": tr("Pending"),
                    "completed": tr("Completed"),
                    "cancelled": tr("Cancelled"),
                }.get(str(final_status).lower(), final_status)

                cols[0].markdown(f"{tr('**Tenant:**')} {tenant_label} ({tenant['email'] if tenant else '—'})")
                cols[1].markdown(f"{tr('**To landlord:**')} {landlord_email}")
                cols[2].markdown(f"{tr('**Created:**')} {format_dt(created_at)}")
                cols[3].markdown(f"{tr('**Status:**')} {display_status}")

                # ⬇️ Previous landlord line (translated)
                st.caption(f"{tr('Previous landlord:')} **{pl_name}** ({pl_email}) · {tr('Address:')} {pl_addr}")

                # link = build_reference_link(token)
                # st.text_input(tr('Reference Link'), value=link, key=f"{prefix}_link_{token}", disabled=True)

                # --- Contract section ---
                contract = get_contract_by_token(token)
                if contract:
                    consent_row = conn.cursor().execute("SELECT consent_status FROM reference_contracts WHERE token=?", (token,)).fetchone()
                    consent_badge = f"{tr('Consent')}: {consent_row[0] if consent_row else 'locked'}"
                    st.markdown(f"**Contract:** {contract['filename']} · {contract_status_badge(contract['status'])} · {consent_badge}")
                    st.caption(
                        f"Uploaded: {contract['uploaded_at']} • "
                        f"Last status update: {contract['status_updated_at'] or '—'}"
                        + (f" • by {contract['status_by']}" if contract['status_by'] else "")
                    )
                    try:
                        data_plain = load_contract_plaintext(token)
                        if data_plain is None:
                            st.warning(tr("Contract is locked awaiting landlord consent."))
                        else:
                            st.download_button(
                                tr('Download Contract'),
                                data=data_plain,
                                file_name=contract['filename'],
                                mime=contract['content_type'],
                                key=f"{prefix}_dl_{token}",
                            )
                    except Exception as e:
                        st.warning(f"Unable to read the saved file: {e}")
                else:
                    st.caption(tr('No contract uploaded yet.'))
                    
                    
                is_completed = str(final_status).lower() == "completed"
                is_revoked   = str(final_status).lower() == "revoked"
                
                if is_revoked:
                    st.error(tr("Revoked by admin"))
                    if details and (details.get("revoked_by") or details.get("revoked_at") or details.get("revoked_reason")):
                        st.caption(f"{tr('By')}: {details.get('revoked_by','—')} • {format_dt(details.get('revoked_at'))}")
                        if details.get("revoked_reason"):
                            st.write(f"**{tr('Reason')}:** {details['revoked_reason']}")

                ac1, ac2 = st.columns(2)

                if is_completed and not is_revoked:
                    # Revoke flow
                    with st.popover(tr("Revoke Reference")):
                        reason = st.text_area(tr("Reason (shown in audit)"), key=f"{prefix}_rev_reason_{token}")
                        if st.button(tr("Confirm Revoke"), key=f"{prefix}_rev_confirm_{token}", type="primary"):
                            revoke_reference_request(token, st.session_state.user.get("email","admin@rentright"), reason)
                            st.warning(tr("Reference revoked."))
                            st.rerun()
                else:

                    show_verify = (str(final_status).lower() != "completed")
                    show_cancel = (str(final_status).lower() != "cancelled")

                    if show_verify:
                        if ac1.button(tr('✅ Verify Contract'), key=f"{prefix}_verify_{token}"):
                            ok, msg = set_contract_status(token, "verified", st.session_state.user["email"])
                            if ok:
                                promote_reference_if_ready(token)  # keep your existing promotion
                                st.success(tr('Contract verified successfully.'))
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        ac1.caption(tr('Already completed — no verification needed.'))

                    if show_cancel:
                        if ac2.button(tr('Cancel Reference'), key=f"{prefix}_cancel_{token}"):
                            cancel_reference_request(token)
                            st.warning(tr('Reference cancelled.'))
                            st.rerun()
                    else:
                        ac2.caption(tr('Already cancelled.'))

    with tab_pending:
        render_admin_reqs(pending_reqs, "admin_pending")
    with tab_completed:
        render_admin_reqs(completed_reqs, "admin_completed")
    with tab_cancelled:
        render_admin_reqs(cancelled_reqs, "admin_cancelled")

    st.markdown("---")
    # logout_button()

#-----------------------------------------------------------------------------------------------------------------------------
# ----------------TENANT DASHBOARD-------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------
    
def tenant_dashboard():
    
    tenant_id = st.session_state.user["id"]
    tenant_email = (st.session_state.user.get("email") or "").strip().lower()
    tenant_name = (st.session_state.user.get("name") or "").strip()  # fallback if name in session

    # Try DB lookup if name not in session
    if not tenant_name:
        c = get_conn()
        row = c.execute("SELECT name FROM users WHERE id=? LIMIT 1", (tenant_id,)).fetchone()
        if row:
            tenant_name = (row[0] or "").strip()

    if tenant_name:
        user = st.session_state.user
        name = user.get("name", "")
        role = user.get("role", "")
        st.subheader(f"{role_icon(role)} {tr('Welcome')}, {name}")
    else:
        st.subheader(tr("Welcome"))

    st.caption(f"{tr('Logged in with email')}: {tenant_email}")
    
    # ---------- NAV BUTTONS (set active page only) ----------
    nav1, nav3, nav4 = st.columns(3)

    # ---------- NAV STATE (TENANT) ----------
    if "tenant_page" not in st.session_state:
        st.session_state["tenant_page"] = "find_landlords"  # default

    # keep any legacy "page" readers in sync (optional but safe)
    st.session_state["page"] = st.session_state["tenant_page"]

    def _go(page_key: str):
        # clean transient UI flags if you want
        for k in list(st.session_state.keys()):
            if k.startswith(("tfl:", "tfl_", "tfl_contacts:", "ld_otr_", "otr_", "prospects")):
                st.session_state.pop(k, None)
        st.session_state["tenant_page"] = page_key
        st.session_state["page"] = page_key
        st.rerun()


    def tenant_contacts():
        return people_hub("tenant")
   

    def tenant_open_to_rent_section():
        # Header + compact help
        c1, c2 = st.columns([6, 0.6])
        with c1:
            st.subheader(f"**{tr('Open to rent')}**")
        with c2:
            help_icon(tr("Let landlords know what you’re looking and share your criteria."), key="help_otr_header")

        tid = st.session_state.user["id"]
        prefs = load_open_to_rent_prefs(tid)

        # If reset asked, we force defaults (zeros/False) instead of loading prefs.
        force_defaults = st.session_state.pop("otr_force_defaults", False)

        if ("otr_keys_inited" not in st.session_state) or force_defaults:
            if force_defaults:
                # Defaults
                st.session_state["otr_open_flag"]  = False
                st.session_state["otr_size_min"]   = 0
                st.session_state["otr_size_max"]   = 0
                st.session_state["otr_rooms_min"]  = 0
                st.session_state["otr_rooms_max"]  = 0
                st.session_state["otr_floor_min"]  = 0
                st.session_state["otr_floor_max"]  = 0
                st.session_state["otr_price_min"]  = 0
                st.session_state["otr_price_max"]  = 0
            else:
                # From saved prefs
                st.session_state["otr_open_flag"]  = bool(prefs.get("open_to_rent"))
                st.session_state["otr_size_min"]   = int(prefs.get("size_min")  or 0)
                st.session_state["otr_size_max"]   = int(prefs.get("size_max")  or 0)
                st.session_state["otr_rooms_min"]  = int(prefs.get("rooms_min") or 0)
                st.session_state["otr_rooms_max"]  = int(prefs.get("rooms_max") or 0)
                st.session_state["otr_floor_min"]  = int(prefs.get("floor_min") or 0)
                st.session_state["otr_floor_max"]  = int(prefs.get("floor_max") or 0)
                st.session_state["otr_price_min"]  = int(prefs.get("price_min") or 0)
                st.session_state["otr_price_max"]  = int(prefs.get("price_max") or 0)

            st.session_state["otr_keys_inited"] = True

        # Defaults
        region = district = city = ""

        with st.container(border=True):
            data, regions, muni_idx = load_ellada_index("ellada.json")

            # If we just pressed Reset, skip preselect from saved prefs this run
            reset_preselect = st.session_state.pop("otr_reset_preselect", False)

            saved_city = "" if reset_preselect else (prefs.get("search_city") or "").strip()
            saved_dist = "" if reset_preselect else (prefs.get("search_district") or "").strip()

            # Try to infer Region/Unit from saved values
            pre_region, pre_unit = (None, None)
            if saved_city and saved_city in muni_idx:
                pre_region, pre_unit = muni_idx[saved_city]
            elif saved_dist:
                for reg in data.get("Περιφέρειες", []):
                    units = (reg.get("Περιφερειακές Ενότητες") or {})
                    if saved_dist in units:
                        pre_region = reg.get("όνομα")
                        pre_unit = saved_dist
                        break

            ANY = tr("Any")

            # If we just pressed Reset, or on first run (no key yet), seed pickers to Any
            if reset_preselect or ("loc_region" not in st.session_state):
                st.session_state["loc_region"] = ANY
            if reset_preselect or ("loc_unit" not in st.session_state):
                st.session_state["loc_unit"] = ANY
            if reset_preselect or ("loc_city" not in st.session_state):
                st.session_state["loc_city"] = ANY

            # Active / Inactive toggle with a small help icon (important UX)
            cb1, cb2 = st.columns([1, 0.08])
            with cb1:
                open_flag = st.checkbox(
                    tr("I’m looking for a place"),
                    key="otr_open_flag",
                )
            with cb2:
                help_icon(tr("Turn on to appear in landlord searches. You can hide this anytime."), key="help_otr_toggle")

            with st.expander(tr("Property characteristics"), expanded=False):
                
                # prop = render_tenant_filters(prefix="prop")
                
                prefix = "otr"
                filt = render_tenant_filters(prefix=prefix)
   
                # ---- Save / Reset -------------------------------------------------------
                col_save, col_reset = st.columns([1, 1])

                def _i(x):  # None -> 0, else int
                    return 0 if x is None else int(x)

                if col_save.button(tr("Save preferences")):
                    region_clean   = filt["region"] or ""
                    city_clean     = filt["city"] or ""
                    district_clean = filt["district"] or ""

                    if not city_clean and not district_clean:
                        st.warning(tr("Enter at least a city or a district."))
                    else:
                        try:
                            save_open_to_rent_prefs(
                                tid, bool(st.session_state["otr_open_flag"]),
                                city_clean, district_clean,
                                _i(filt["size_min"]),  _i(filt["size_max"]),
                                _i(filt["rooms_min"]), _i(filt["rooms_max"]),
                                _i(filt["floor_min"]), _i(filt["floor_max"]),
                                _i(filt["price_min"]), _i(filt["price_max"]),
                                city_osm_id=None, city_osm_type=None,
                                district_osm_id=None, district_osm_type=None,
                                region=region_clean, 
                            )
                        except TypeError:
                            # older signature fallback
                            save_open_to_rent_prefs(
                                tid, bool(st.session_state["otr_open_flag"]),
                                city_clean, district_clean,
                                _i(filt["size_min"]),  _i(filt["size_max"]),
                                _i(filt["rooms_min"]), _i(filt["rooms_max"]),
                                _i(filt["floor_min"]), _i(filt["floor_max"]),
                                _i(filt["price_min"]), _i(filt["price_max"]),
                            )
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.success(tr("Preferences saved."))

                #-------------------------------------------------
                if col_reset.button(tr("Reset")):
                    for k in (
                        f"{prefix}_loc_region", f"{prefix}_loc_unit", f"{prefix}_loc_city",
                        f"{prefix}_size_min", f"{prefix}_size_max",
                        f"{prefix}_rooms_min", f"{prefix}_rooms_max",
                        f"{prefix}_floor_min", f"{prefix}_floor_max",
                        f"{prefix}_price_min", f"{prefix}_price_max",
                        "otr_open_flag", "otr_keys_inited"
                    ):
                        st.session_state.pop(k, None)

                    st.session_state["otr_force_defaults"]  = True
                    st.session_state["otr_reset_preselect"] = True
                    st.rerun()

                    
            # --- Profile details (own Edit/Save flow) -------------------------------------
            tid = st.session_state.user["id"]
            _prof = load_profile_details(tid)

            # one-time default for edit mode
            if "profile_editing" not in st.session_state:
                st.session_state["profile_editing"] = False

            _ensure_pt_css()

            with st.expander(tr("Profile details"), expanded=False):
                # Header row with Edit / Save / Cancel
                b1, _ = st.columns([3, 9])

                if not st.session_state["profile_editing"]:
                    # Read-only summary chips
                    p = _prof or {}
                    def _val(x, dash="—"): return (str(x).strip() if (x not in (None, "", 0)) else dash)
                    _pets = tr("Yes") if p.get("pets") in (1, True) else tr("No") if p.get("pets") in (0, False) else "—"
                    chips = []
                    if p.get("age"):              chips.append(f'<span class="pill">{tr("Age")}: {int(p["age"])}</span>')
                    if p.get("marital_status"):   chips.append(f'<span class="pill">{tr("Marital status")}: {p["marital_status"]}</span>')
                    if p.get("contract_type"):    chips.append(f'<span class="pill">{tr("Contract type")}: {p["contract_type"]}</span>')
                    if p.get("monthly_salary") is not None:
                        chips.append(f'<span class="pill">{tr("Monthly salary (€)")}: {int(p["monthly_salary"]):,}</span>')
                    chips.append(f'<span class="pill">{tr("Pets")}: {_pets}</span>')
                    if p.get("num_tenants"):      chips.append(f'<span class="pill">{tr("Number of occupants")}: {int(p["num_tenants"])}</span>')

                    about_html = ""
                    if _val(p.get("about"), None):
                        from html import escape
                        about_html = f"<div class='ref-comments'>{escape(p.get('about'))}</div>"

                    st.markdown(
                        f"""
                        <div class="ref-card">
                        <div class="ref-header">
                            <div class="ref-title">{tr("Profile details")}</div>
                        </div>
                        <div class="ref-row">{' '.join(chips) or '—'}</div>
                        {about_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if b1.button(tr("Edit"), key="btn_profile_edit"):
                        st.session_state["profile_editing"] = True
                        st.rerun()

                else:

                    # ✅ Actual form (submit button MUST be inside this context)
                    with st.form("profile_details_form", clear_on_submit=False):
                        c1, c2 = st.columns(2)
                        with c1:
                            age = st.number_input(
                                tr("Age"), min_value=18, max_value=100, step=1,
                                value=int((_prof or {}).get("age") or 18),
                                key="profile_age"
                            )
                            monthly_salary = st.number_input(
                                tr("Monthly salary (€)"), min_value=0, max_value=1_000_000, step=100,
                                value=int((_prof or {}).get("monthly_salary") or 0),
                                key="profile_salary"
                            )
                            marital_status_opts = ["Single","Married","Divorced","Widowed"]
                            marital_status_idx = (
                                marital_status_opts.index(((_prof or {}).get("marital_status") or "Single"))
                                if ((_prof or {}).get("marital_status") in marital_status_opts) else 0
                            )
                            marital_status = st.selectbox(
                                tr("Marital status"),
                                [tr(x) for x in marital_status_opts],
                                index=marital_status_idx,
                                key="profile_marital"
                            )
                            pets = st.radio(
                                tr("Pets"), [tr("Yes"), tr("No")], horizontal=True,
                                index=(0 if ((_prof or {}).get("pets") in (1, True)) else 1),
                                key="profile_pets"
                            )
                            num_tenants = st.number_input(
                                tr("Number of occupants"), min_value=1, max_value=10, step=1,
                                value=int((_prof or {}).get("num_tenants") or 1),
                                key="profile_num_tenants"
                            )
                        with c2:
                            job_position = st.text_input(
                                tr("Job position"), value=(_prof or {}).get("job_position") or "",
                                key="profile_job_position"
                            )
                            contract_type_opts = ["Permanent","Temporary","Freelancer","Other"]
                            contract_type_idx = (
                                contract_type_opts.index(((_prof or {}).get("contract_type") or "Permanent"))
                                if ((_prof or {}).get("contract_type") in contract_type_opts) else 0
                            )
                            contract_type = st.selectbox(
                                tr("Contract type"),
                                [tr(x) for x in contract_type_opts],
                                index=contract_type_idx,
                                key="profile_contract"
                            )
                        about = st.text_area(
                            tr("A few words about yourself"),
                            value=(_prof or {}).get("about") or "",
                            key="profile_about"
                        )

                        # 🔘 This is the button Streamlit needs INSIDE the form
                        save_clicked = st.form_submit_button(tr("Save profile details"))

                    if save_clicked:
                        marital_map = {
                            tr("Single"): "Single", tr("Married"): "Married",
                            tr("Divorced"): "Divorced", tr("Widowed"): "Widowed",
                        }
                        contract_map = {
                            tr("Permanent"): "Permanent", tr("Temporary"): "Temporary",
                            tr("Freelancer"): "Freelancer", tr("Other"): "Other",
                        }

                        save_profile_details(
                            tid,
                            age=int(st.session_state["profile_age"]),
                            monthly_salary=int(st.session_state["profile_salary"]),
                            marital_status=marital_map.get(st.session_state["profile_marital"], "Single"),
                            job_position=st.session_state["profile_job_position"].strip(),
                            contract_type=contract_map.get(st.session_state["profile_contract"], "Permanent"),
                            pets=(1 if st.session_state["profile_pets"] == tr("Yes") else 0),
                            num_tenants=int(st.session_state["profile_num_tenants"]),
                            about=st.session_state["profile_about"].strip(),
                        )
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.success(tr("Changes saved."))
                        st.session_state["profile_editing"] = False
                        st.rerun()


        # --- Compact summary (uses current widget values) ---------------------------
        def _fmt_range(lo, hi, suffix=""):
            has_lo = lo not in (None, 0, "0", "")
            has_hi = hi not in (None, 0, "0", "")
            if not has_lo and not has_hi:
                return None
            lo_txt = f"{int(lo):,}" if has_lo else "—"
            hi_txt = f"{int(hi):,}" if has_hi else "—"
            return f"{lo_txt}–{hi_txt}{suffix}"

        latest_region = region if (region and region != "—") else ""
        latest_district = district if (district and district != "—") else ""
        latest_city = city if (city and city != "—") else ""
        loc_txt = " — ".join([x.strip() for x in [latest_region, latest_district, latest_city] if x])

        size_txt  = _fmt_range(st.session_state["otr_size_min"],  st.session_state["otr_size_max"],  " m²")
        rooms_txt = _fmt_range(st.session_state["otr_rooms_min"], st.session_state["otr_rooms_max"], f" {tr('rooms')}")
        floor_txt = _fmt_range(st.session_state["otr_floor_min"], st.session_state["otr_floor_max"])
        price_txt = _fmt_range(st.session_state["otr_price_min"], st.session_state["otr_price_max"])

        bits = []
        if size_txt:  bits.append(size_txt)
        if rooms_txt: bits.append(rooms_txt)
        if floor_txt: bits.append(tr("Floor") + " " + floor_txt)
        if price_txt: bits.append("€" + price_txt.replace("–", "–€"))

        details_txt = " · ".join(bits)
        state_label = tr("Active") if st.session_state["otr_open_flag"] else tr("Inactive")

        if loc_txt and details_txt:
            st.caption(f"{tr('Status:')} {state_label} · {tr('Looking in')}: {loc_txt} · {details_txt}")
        elif loc_txt:
            st.caption(f"{tr('Status:')} {state_label} · {tr('Looking in')}: {loc_txt}")
        elif details_txt:
            st.caption(f"{tr('Status:')} {state_label} · {details_txt}")
        else:
            st.caption(f"{tr('Status:')} {state_label} · {tr('Looking in')}: {tr('Anywhere')}")
            
    # === Previous landlords + reference requests ===    
    
    def previous_landlords_references():
        # Header
        st.subheader(tr("Previous landlords & references"))

        # --- Add previous landlord form --------------------------------------------
        with st.form("previous_landlord_form"):
            col1, col2 = st.columns([1, 1])
            with col1:
                pl_email = st.text_input(tr("Landlord email"))
                # pl_afm = st.text_input(tr('Tax ID (9 digits)'))
            with col2:
                pl_name = st.text_input(tr("Landlord name"))
                pl_address = st.text_input(tr("Address"))
            add = st.form_submit_button(tr("Add previous landlord"))

        if add:
            if not (pl_email and is_valid_email(pl_email)):
                st.error(tr("Enter a valid email."))
            # elif not is_valid_afm(pl_afm):
            #     st.error(tr('Tax ID must be exactly 9 digits.'))
            elif not pl_name.strip():
                st.error(tr("Enter the landlord’s name."))
            elif not pl_address.strip():
                st.error(tr("Enter the landlord’s address."))
            else:
                add_previous_landlord(st.session_state.user["id"], pl_email, pl_name, pl_address)  # pl_afm,
                st.success(tr("Previous landlord added."))

        rows = list_previous_landlords(st.session_state.user["id"]) or []

        # --- List of all requests per previous landlord ----------------------------
        st.subheader(tr("All reference requests"))

        if rows:
            for (pid, email, name, address, created_at) in rows:  # afm,
                with st.expander(f"{name} • {email} • {address}", False):

                    # Load all requests for this landlord
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT token, status, created_at, score FROM reference_requests WHERE prev_landlord_id=? ORDER BY id DESC",
                        (pid,),
                    )
                    reqs = cur.fetchall()

                    # Helper: find an active (non-final) request
                    def pick_active_request(reqs_list):
                        for (tok, status, created_at2, score) in reqs_list:
                            final_status = effective_reference_status(status, tok)
                            if str(final_status).lower() not in ("completed", "cancelled"):
                                return (tok, status, created_at2, score)
                        return None

                    active_req = pick_active_request(reqs)
                    suppress_key = f"suppress_autodraft_{pid}"

                    # ===== No active request path =====
                    if not active_req:
                        # Latest request (reqs are DESC by id)
                        latest = reqs[0] if reqs else None
                        latest_tok = latest_status = None
                        if latest:
                            latest_tok, latest_status, latest_created, latest_score = latest
                            latest_final = effective_reference_status(latest_status, latest_tok).lower()
                        else:
                            latest_final = None

                        if latest and latest_final == "completed":
                            # Completed summary (no Start/Delete)
                            details = get_reference_request_by_token(latest_tok)
                            contract_i = get_contract_by_token(latest_tok)

                            # Contract status
                            if contract_i:
                                st.markdown(f"**{tr('Contract Status:')}** {contract_status_badge(contract_i['status'])}")
                            else:
                                st.markdown(f"**{tr('Contract Status:')}** {tr('✅ Verified')}")

                            # Answers
                            if details:
                                st.write(f"**{tr('Overall tenant score')}:** {details.get('score')}/10")
                                st.write(f"**{tr('Paid on time?')}:** {tr('Yes') if details.get('paid_on_time') else tr('No')}")
                                st.write(f"**{tr('Any unpaid utilities?')}:** {tr('Yes') if details.get('utilities_unpaid') else tr('No')}")
                                st.write(f"**{tr('Left in good condition?')}:** {tr('Yes') if details.get('good_condition') else tr('No')}")
                                if details.get('comments'):
                                    st.write("**" + tr("Comments (optional)") + ":**")
                                    st.write(details['comments'])

                            # Optional download if consented
                            if contract_i:
                                try:
                                    data_plain_i = load_contract_plaintext(latest_tok)
                                    if data_plain_i is None:
                                        st.warning(tr("Contract locked until landlord consents"))
                                    else:
                                        st.download_button(
                                            tr("Download contract"),
                                            data=data_plain_i,
                                            file_name=contract_i["filename"],
                                            mime=contract_i.get("content_type") or contract_i.get("mime_type"),
                                            key=f"dl_{latest_tok}",
                                        )
                                except Exception as e:
                                    st.warning(f"{tr('Can’t read the saved file:')} {e}")

                        else:
                            # No requests OR latest was cancelled → Start/Delete
                            st.caption(tr("No active reference request."))
                            col_start, col_delete = st.columns([1, 1])

                            # Start
                            if col_start.button(tr("New reference request"), key=f"start_{pid}"):
                                rec = create_reference_request(st.session_state.user["id"], pid, email)
                                st.session_state.pop(suppress_key, None)
                                st.rerun()

                            # Delete (2-step)
                            del_confirm_key = f"confirm_delete_prev_{pid}"
                            if st.session_state.get(del_confirm_key, False):
                                st.warning(tr("Delete this previous landlord and all related data?"))
                                col_yes, col_no = st.columns([1, 1])
                                if col_yes.button(tr("Delete"), key=f"yes_del_prev_{pid}"):
                                    try:
                                        delete_previous_landlord_completely(st.session_state.user["id"], pid)
                                        st.success(tr("Previous landlord deleted."))
                                    except Exception as e:
                                        st.error(f"{tr('Can’t delete')}: {e}")
                                    finally:
                                        st.session_state.pop(del_confirm_key, None)
                                    st.rerun()
                                if col_no.button(tr("Keep"), key=f"no_del_prev_{pid}"):
                                    st.session_state.pop(del_confirm_key, None)
                                    st.rerun()
                            else:
                                if col_delete.button(tr("Delete previous landlord"), key=f"del_prev_{pid}"):
                                    st.session_state[del_confirm_key] = True
                                    st.rerun()
                        continue

                    # ===== Active request path =============================================
                    tok, status, created_at2, score = active_req
                    final_status = effective_reference_status(status, tok)

                    # Email already sent?
                    row = conn.execute("SELECT emailed_at FROM reference_requests WHERE token=?", (tok,)).fetchone()
                    emailed_at = row[0] if row else None
                    final_norm = str(final_status).strip().lower()

                    # Only allow requesting if not emailed yet and not final
                    can_request = (emailed_at is None) and (final_norm not in ("completed", "cancelled"))

                    contract = get_contract_by_token(tok)

                    # Layout: left = upload/request; right = history
                    c_left, c_right = st.columns([1, 2])

                    with c_left:
                        if contract:
                            # Current contract info + download + request
                            try:
                                data_plain = load_contract_plaintext(tok)
                                if data_plain is None:
                                    st.warning(tr("Contract locked until landlord consents"))
                                else:
                                    st.download_button(
                                        tr("Download contract"),
                                        data=data_plain,
                                        file_name=contract["filename"],
                                        mime=contract.get("content_type") or contract.get("mime_type"),
                                        key=f"dl_{tok}",
                                    )
                            except Exception as e:
                                st.warning(f"{tr('Can’t read the saved file')}: {e}")

                            # Request reference
                            if contract and can_request:
                                if st.button(tr("Request reference"), key=f"req_{pid}"):
                                    link = build_reference_link(tok)
                                    ok, msg = email_reference_request(
                                        st.session_state.user["name"], st.session_state.user["email"], email, link, address
                                    )
                                    if ok:
                                        conn.execute(
                                            "UPDATE reference_requests SET status=?, emailed_at=CURRENT_TIMESTAMP WHERE token=?",
                                            ("pending", tok),
                                        )
                                        conn.commit()
                                        st.success(tr("Reference request emailed."))
                                        st.rerun()
                                    else:
                                        st.warning(f"{tr('Email delivery failed')} ({msg}). {tr('Share this link manually')}:")
                                        st.code(link)

                            # Cancel while pending/pending review
                            if final_norm in ("pending", "pending review", "pending_review"):
                                confirm_key = f"confirm_cancel_{tok}"

                                # Step 1: button
                                if not st.session_state.get(confirm_key, False):
                                    if st.button(tr("Cancel request"), key=f"cancel_{pid}"):
                                        st.session_state[confirm_key] = True
                                        st.rerun()

                                # Step 2: confirmation UI
                                if st.session_state.get(confirm_key, False):
                                    st.warning(tr("Cancel this reference request?"))
                                    col_yes, col_no = st.columns([1, 1])

                                    with col_yes:
                                        if st.button(tr("Cancel request"), key=f"confirm_cancel_yes_{pid}"):
                                            # (A) Email landlord first
                                            row = conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()
                                            cancelled_at = row[0] if row else None
                                            ok_mail, msg_mail = email_reference_cancellation_smtp(
                                                tenant_name=st.session_state.user["name"],
                                                tenant_email=st.session_state.user["email"],
                                                landlord_email=email,
                                                landlord_name=name,
                                                landlord_address=address,
                                                token=tok,
                                                cancelled_at=cancelled_at,
                                            )

                                            # (B) Hard-delete data
                                            delete_landlord_responses(tok)
                                            delete_contract_hard(tok)
                                            conn.execute("DELETE FROM reference_requests WHERE token=?", (tok,))
                                            conn.commit()

                                            # (C) Clean up state
                                            st.session_state.pop(confirm_key, None)
                                            st.session_state[f"suppress_autodraft_{pid}"] = True

                                            # (D) Feedback
                                            if ok_mail:
                                                st.success(tr("Request cancelled. Landlord notified; contract and responses deleted."))
                                            else:
                                                st.warning(tr("Request cancelled and data deleted, but email notification failed: ") + str(msg_mail))

                                            st.rerun()

                                    with col_no:
                                        if st.button(tr("Keep"), key=f"confirm_cancel_no_{pid}"):
                                            st.session_state.pop(confirm_key, None)
                                            st.info(tr("Request kept."))
                                            st.rerun()

                        else:
                            # No file yet → uploader only
                            uploaded = st.file_uploader(
                                tr("Upload tenancy contract (PDF or image)"),
                                type=["pdf", "png", "jpg", "jpeg", "webp"],
                                key=f"up_{tok}",
                            )
                            if uploaded is not None:
                                ok, msg = save_contract_upload(tok, st.session_state.user["id"], uploaded)
                                if ok:
                                    # After saving, immediately email the landlord (first time only)
                                    link = build_reference_link(tok)
                                    ok_mail, msg_mail = email_reference_request(
                                        st.session_state.user["name"],
                                        st.session_state.user["email"],
                                        email,
                                        link,
                                        address
                                    )
                                    if ok_mail:
                                        conn.execute(
                                            "UPDATE reference_requests SET status=?, emailed_at=CURRENT_TIMESTAMP WHERE token=?",
                                            ("pending", tok),
                                        )
                                        conn.commit()
                                        st.success(tr("Contract uploaded. Email sent to landlord."))
                                        st.rerun()
                                    else:
                                        st.warning(
                                            f"{tr('Contract uploaded, but email failed')} ({msg_mail}). "
                                            f"{tr('Share this link manually or try again')}:"
                                        )
                                        st.code(link)
                                        # Do NOT set emailed_at → the Request button remains visible after rerun
                                        st.rerun()
                                else:
                                    st.error(msg)

                    with c_right:
                        # Request history
                        if reqs:
                            for (tok_i, status_i, created_at_i, score_i) in reqs:
                                final_i = effective_reference_status(status_i, tok_i)
                                contract_i = get_contract_by_token(tok_i)
                                final_i_lower = str(final_i).lower()

                                if final_i_lower in ("completed", "cancelled"):
                                    if final_i_lower == "completed":
                                        colA, colB, colC = st.columns([2, 2, 2])
                                        if score_i is not None:
                                            colB.write(f"{tr('Score')}: **{score_i}**/10")

                                        if contract_i:
                                            st.markdown(f"**{tr('Contract Status:')}** {contract_status_badge(contract_i['status'])}")
                                            try:
                                                data_plain_i = load_contract_plaintext(tok_i)
                                                if data_plain_i is None:
                                                    st.warning(tr("Contract locked until landlord consents"))
                                                else:
                                                    st.download_button(
                                                        tr("Download contract"),
                                                        data=data_plain_i,
                                                        file_name=contract_i["filename"],
                                                        mime=contract_i.get("content_type") or contract_i.get("mime_type"),
                                                        key=f"dl_{tok_i}",
                                                    )
                                            except Exception as e:
                                                st.warning(f"{tr('Can’t read the saved file')}: {e}")
                                        else:
                                            st.markdown(tr("Contract verified — no upload needed."))
                                    else:
                                        details = get_reference_request_by_token(tok_i)
                                        cancelled_when = details.get("filled_at") if details else None

                                else:
                                    # Non-final historical entries: show status only
                                    if contract_i:
                                        st.markdown(f"**{tr('Contract Status:')}** {contract_status_badge(contract_i['status'])}")
                        else:
                            st.caption(tr("No reference requests yet."))
        else:
            st.info(tr("No previous landlords yet."))
        st.divider()
        
        with st.container(border=True):
            render_tenant_documents_ui(st.session_state.user)
        st.divider()
            


    current_page = st.session_state.get("tenant_page", "my_contacts")
    

    with nav1:
        is_active = current_page == "my_contacts"
        if st.button(tr("My Contacts"), key="btn_my_contacts",
                    use_container_width=True,
                    type=("primary" if is_active else "secondary")):
            _go("my_contacts")

    # with nav2:
    #     is_active = current_page == "find_landlords"
    #     if st.button(tr("Search"), key="btn_find_landlords",
    #                 use_container_width=True,
    #                 type=("primary" if is_active else "secondary")):
    #         _go("find_landlords")

    with nav3:
        is_active = current_page == "open_to_rent"
        if st.button(tr("Profile"), key="btn_open_to_rent",
                    use_container_width=True,
                    type=("primary" if is_active else "secondary")):
            _go("open_to_rent")

    with nav4:
        is_active = current_page == "prev_refs"
        if st.button(tr("My References"), key="btn_prev_refs",
                    use_container_width=True,
                    type=("primary" if is_active else "secondary")):
            _go("prev_refs")

    page = st.session_state.tenant_page
    if page == "my_contacts":
        tenant_contacts()
    # elif page == "find_landlords":
    #     tenant_future_landlords_section()
    elif page == "open_to_rent":
        tenant_open_to_rent_section()
    elif page == "prev_refs":
        previous_landlords_references()
        
    chat_panel_docked()
        

# -----------------------------------------------------------------------------------------------------------------------
# ---------- Landlord Dashboard -------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------

def landlord_dashboard():
    
    if "doc_pill_css" not in st.session_state:
        st.session_state["doc_pill_css"] = True
        st.markdown("""
        <style>
        .pill{display:inline-block;padding:2px 8px;border-radius:999px;border:1px solid #ddd;font-size:12px}
        .pill-ok{border-color:#2e7d32}
        .pill-no{border-color:#c62828}
        .pill-na{opacity:0.6}
        </style>
        """, unsafe_allow_html=True)


    landlord_id = st.session_state.user["id"]
    landlord_email = (st.session_state.user.get("email") or "").strip().lower()
    landlord_name = (st.session_state.user.get("name") or "").strip()  # fallback if name is in session

    # Try DB lookup if name not stored in session
    if not landlord_name:
        c = get_conn()
        row = c.execute("SELECT name FROM users WHERE id=? LIMIT 1", (landlord_id,)).fetchone()
        if row:
            landlord_name = (row[0] or "").strip()

    if landlord_name:
        user = st.session_state.user
        name = user.get("name", "")
        role = user.get("role", "")
        st.subheader(f"{role_icon(role)} {tr('Welcome')}, {name}")
    else:
        st.subheader(tr("Welcome"))

    st.caption(f"{tr('Logged in with email')}: {landlord_email}")
    
    # ---------- NAV BUTTONS (set active page only) ----------
    nav1, nav2, nav3, nav4 = st.columns(4)

    # ---------- NAV STATE ----------
    if "landlord_page" not in st.session_state:
        st.session_state["landlord_page"] = "my_contacts"  # default

    def _go(page_key: str):
        # optional: clear per-page transient flags
        for k in list(st.session_state.keys()):
            if k.startswith(("tfl:", "tfl_", "tfl_contacts:", "ld_otr_", "otr_", "prospects")):
                st.session_state.pop(k, None)
                
        # single source of truth
        st.session_state["landlord_page"] = page_key
        # keep legacy key in sync if used elsewhere
        st.session_state["page"] = page_key
        st.rerun()


    # =============================================================================
    # Prospective Tenants (landlord view)
    # =============================================================================

    def my_tenants():
        return people_hub("landlord")
    # =============================================================================
    # My Properties
    # =============================================================================
    def my_properties():
        LP_NS = "myprops"  # namespacing to avoid widget-key collisions
        def lpk(id_: int | str, name: str) -> str:
            return f"{LP_NS}:{name}:{id_}"

        
        st.markdown("""
        <style>
        .prop-card{border:1px solid #e6e6e6;border-radius:14px;padding:14px 16px;margin:12px 0;background:#fff}
        .prop-title{font-weight:700;margin-bottom:6px;font-size:16px}
        .prop-sub{margin:6px 0 8px 0}
        .pill{display:inline-block;padding:4px 10px;border-radius:999px;border:1px solid #e6e6e6;
            font-size:12px;line-height:1.2;background:#fafafa}
        .pill.badge{border-color:#d6e8ff;background:#f2f7ff}
        .prop-foot{font-size:12px;color:#666;margin-top:2px}
        .prop-foot a{text-decoration:none}
        .meta-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:4px}
        .divider{height:1px;background:#f0f0f0;margin:8px 0 4px 0}
        .toolbar-row{height:0} /* anchor for spacing; real widgets follow but visually belong to the card */
        </style>
        """, unsafe_allow_html=True)


        # ---------- Add property ----------
        with st.expander("🏠 " + tr("Add property"), expanded=False):
            # Live pickers (outside form)
            
            col1, col2, col3 = st.columns(3)

            with col1:
                region = greece_location_pickers(prefix="lp_add", only="region")

            with col2:
                regional_unit = greece_location_pickers(prefix="lp_add", only="regional_unit", parent_region=region)

            with col3:
                municipality = greece_location_pickers(prefix="lp_add", only="municipality",
                                                    parent_region=region, parent_ru=regional_unit)


            # Form (clear on submit)
            with st.form(lpk("add", "form"), clear_on_submit=True):
                addr = st.text_input(tr("Address"), key=lpk("add", "addr"),
                                    placeholder=tr("Street, number, city"))
                url  = st.text_input(tr("Listing URL (optional)"), key=lpk("add", "url"),
                                    placeholder="https://www.xe.gr/property/...")
                s1, s2, s3, s4 = st.columns(4)
                with s1:
                    size_m2 = st.number_input(tr("Size (m²)"), min_value=0, max_value=10000,
                                            step=10, value=0, key=lpk("add", "size"))
                with s2:
                    rooms = st.number_input(tr("Rooms"), min_value=0, max_value=50,
                                            step=1, value=0, key=lpk("add", "rooms"))
                with s3:
                    floor = st.number_input(tr("Floor"), min_value=-5, max_value=100,
                                            step=1, value=0, key=lpk("add", "floor"))
                with s4:
                    price = st.number_input(tr("Price (€)"), min_value=0, max_value=1_000_000,
                                            step=50, value=0, key=lpk("add", "price"))
                vis  = st.checkbox(tr("Visible to tenants"), key=lpk("add", "vis"), value=False)

                c1, _ = st.columns([1, 5])
                submitted = c1.form_submit_button(tr("Add property"))

            if submitted:
                address = (addr or "").strip()
                if not address:
                    st.error(tr("Enter an address."))
                else:
                    try:
                        lp_add_property(
                            st.session_state.user["id"],
                            address,
                            url,
                            vis,
                            region=region,
                            district=regional_unit,
                            city=municipality,
                            size_m2=size_m2,
                            rooms=rooms,
                            floor=floor,
                            price=price,
                        )
                        try: st.cache_data.clear()
                        except Exception: pass
                        # Reset live pickers
                        for k in ("lp_add_region", "lp_add_ru", "lp_add_mun"):
                            st.session_state.pop(k, None)
                        st.success(tr("Property added."))
                        st.rerun()
                    except Exception as e:
                        st.error(f"{tr('Can’t add property')}: {e}")

        # ---------- List properties ----------
        props = lp_list_properties(st.session_state.user["id"])
        if not props:
            st.caption(tr("No properties yet."))
            return

        for (prop_id, address, listing_url, visible_to_tenants, created_at, updated_at,
            region, district, city, size_m2, rooms, floor, price) in props:

            # Compute display pieces
            where = " — ".join([x for x in [region, district, city] if x])
            
            with st.container(border=True):
                # Header (title + chips + visibility)
                st.markdown(f"### • {address}")

                # Chips line
                chips = []
                if where:                 chips.append(f'<span class="pill">{where}</span>')
                if size_m2:               chips.append(f'<span class="pill">{int(size_m2):,} m²</span>')
                if rooms:                 chips.append(f'<span class="pill">{int(rooms)} {tr("rooms")}</span>')
                if floor not in (None,0): chips.append(f'<span class="pill">{tr("Floor")} {int(floor)}</span>')
                if price:                 chips.append(f'<span class="pill">€{int(price):,}</span>')
                chips_html = " ".join(chips)

                vis_badge = (
                    f'<span class="pill badge">{tr("Visible to tenants")}</span>'
                    if int(visible_to_tenants or 0) == 1
                    else f'<span class="pill">{tr("Hidden from tenants")}</span>'
                )

                st.markdown(
                    f"""
                    <div class="prop-sub">{chips_html}</div>
                    <div class="meta-row">{vis_badge}</div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

                # Footer meta + link (still inside the same container)
                try:
                    domain = (listing_url.split('://', 1)[-1].split('/', 1)[0]) if listing_url else None
                except Exception:
                    domain = listing_url
                link_html = f' 🔗 <a href="{listing_url}">{domain or tr("Open listing")}</a>' if listing_url else ""

                st.markdown(
                    f"""
                    <div class="prop-foot">{tr('Updated')}: {format_dt(updated_at)}</div>
                    <div class="prop-foot">{tr('For more details')}: {link_html}</div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown('<div class="divider" style="margin-top:10px;"></div>', unsafe_allow_html=True)

                # Actions (Show/Hide + Delete) — inside the same container
                ac1, _spacer, ac2 = st.columns([3,6,3])
                with ac1:
                    if int(visible_to_tenants or 0) == 1:
                        if st.button(tr("Hide"), key=lpk(prop_id, "hide")):
                            lp_toggle_visibility(prop_id, st.session_state.user["id"], False)
                            try: st.cache_data.clear()
                            except Exception: pass
                            st.rerun()
                    else:
                        if st.button(tr("Show"), key=lpk(prop_id, "show")):
                            lp_toggle_visibility(prop_id, st.session_state.user["id"], True)
                            try: st.cache_data.clear()
                            except Exception: pass
                            st.rerun()
                with ac2:
                    if st.button(tr("Delete"), key=lpk(prop_id, "delete")):
                        lp_delete_property(prop_id, st.session_state.user["id"])
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.warning(tr("Property deleted."))
                        st.rerun()

                # Edit expander — under the buttons and still inside the container
                with st.expander("✏️ " + tr("Edit"), expanded=False):
                    e_addr = st.text_input(tr("Address"), value=address, key=lpk(prop_id, "edit_addr"))
                    e_url  = st.text_input(tr("Listing URL (optional)"), value=(listing_url or ""), key=lpk(prop_id, "edit_url"))

                    # Side-by-side location pickers using your updated function with `only=...`
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        reg_new = greece_location_pickers(prefix=f"lp_edit_{prop_id}", only="region")
                    with ec2:
                        ru_new = greece_location_pickers(
                            prefix=f"lp_edit_{prop_id}",
                            only="regional_unit",
                            parent_region=reg_new or region,
                        )
                    with ec3:
                        muni_new = greece_location_pickers(
                            prefix=f"lp_edit_{prop_id}",
                            only="municipality",
                            parent_region=reg_new or region,
                            parent_ru=ru_new or district,
                        )

                    es1, es2, es3, es4 = st.columns(4)
                    with es1:
                        size_new = st.number_input(tr("Size (m²)"), min_value=0, max_value=10000, step=1,
                                                value=int(size_m2 or 0), key=lpk(prop_id, "edit_size"))
                    with es2:
                        rooms_new = st.number_input(tr("Rooms"), min_value=0, max_value=50, step=1,
                                                    value=int(rooms or 0), key=lpk(prop_id, "edit_rooms"))
                    with es3:
                        floor_new = st.number_input(tr("Floor"), min_value=-5, max_value=100, step=1,
                                                    value=int(floor or 0), key=lpk(prop_id, "edit_floor"))
                    with es4:
                        price_new = st.number_input(tr("Price (€)"), min_value=0, max_value=1_000_000, step=50,
                                                    value=int(price or 0), key=lpk(prop_id, "edit_price"))

                    e_vis = st.checkbox(tr("Visible to tenants"),
                                        value=bool(int(visible_to_tenants or 0)),
                                        key=lpk(prop_id, "edit_vis"))

                    s1, _ = st.columns([3, 5])
                    if s1.button(tr("Save changes"), key=lpk(prop_id, "save")):
                        try:
                            if not (e_addr or "").strip():
                                st.error(tr("Address is required."))
                            else:
                                region_final   = reg_new or region
                                district_final = ru_new or district
                                city_final     = muni_new or city
                                lp_update_property(
                                    prop_id, st.session_state.user["id"],
                                    e_addr, e_url, e_vis,
                                    region_final, district_final, city_final,
                                    size_new, rooms_new, floor_new, price_new,
                                )
                                try: st.cache_data.clear()
                                except Exception: pass
                                st.success(tr("Changes saved."))
                                st.rerun()
                        except Exception as e:
                            st.error(f"{tr('Can’t save changes')}: {e}")

        
        # === Reference requests that were sent to this landlord ===
    def my_references():
        st.subheader(tr('Reference Requests Sent To You'))

        # Quick stats
        all_reqs = list_reference_requests_for_landlord(landlord_email)
        pending_reqs = [r for r in all_reqs if r[3] == "pending"]
        completed_reqs = [r for r in all_reqs if r[3] == "completed"]
        cancelled_reqs = [r for r in all_reqs if r[3] == "cancelled"]

        c1, c2, c3 = st.columns(3)
        c1.metric(tr('Pending'), len(pending_reqs))
        c2.metric(tr('Completed'), len(completed_reqs))
        c3.metric(tr('Cancelled'), len(cancelled_reqs))

        tab_all, tab_pending, tab_completed, tab_cancelled = st.tabs([tr('All'), tr('Pending'), tr('Completed'), tr('Cancelled')])
        
        def render_requests(reqs, prefix: str):
            if not reqs:
                st.info(tr('No requests found.'))
                return

            for (token, tenant_id, created_at, status, score) in reqs:
                tenant = get_user_by_id(tenant_id)  # name + email
                tenant_label = tenant["name"] if tenant else f"Tenant #{tenant_id}"
                tenant_email = tenant["email"] if tenant else "—"

                # Pull address from previous_landlords by prev_landlord_id on this request
                details = get_reference_request_by_token(token)
                address = "—"
                if details and details.get("prev_landlord_id"):
                    cur = conn.cursor()
                    cur.execute("SELECT address FROM previous_landlords WHERE id=?", (details["prev_landlord_id"],))
                    row = cur.fetchone()
                    if row:
                        address = row[0]

                with st.container(border=True):
                    cols = st.columns([3, 2, 3, 2])
                    # Map status to localized display text (handles lowercase DB values)
                    display_status = {
                        "pending": tr("Pending"),
                        "completed": tr("Completed"),
                        "cancelled": tr("Cancelled"),
                    }.get(str(status).lower(), status)

                    cols[0].markdown(
                        f"{tr('**Tenant:**')} {tenant_label}<br/>{tr('**Email:**')} {tenant_email}",
                        unsafe_allow_html=True
                    )
                    cols[1].markdown(f"{tr('**Status:**')} {display_status}")
                    cols[2].markdown(f"{tr('**Created:**')} {format_dt(created_at)}")
                    cols[3].markdown(f"{tr('**Score:**')} {score if score is not None else '—'}")

                    st.caption(f"📍 **{tr('Address')}:** {address}")
                    
                    # ... inside render_requests(reqs, prefix) loop, after st.caption(Address) ...

                    contract = get_contract_by_token(token)  # ⬅️ NEW: gate the form on contract presence

                    if str(status).lower() == "pending":
                        # If the landlord already submitted earlier, show read-only summary
                        if details and details.get("confirm_landlord"):
                            with st.expander(tr('Respond Now'), expanded=True):
                                st.info(tr("Thanks, your response is saved."))
                                st.write(f"**{tr('Overall tenant score')}** {details.get('score')}/10")
                                st.write(f"**{tr('Did the tenant pay on time?')}** {tr('Yes') if details.get('paid_on_time') else tr('No')}")
                                st.write(f"**{tr('Did the tenant leave utilities unpaid?')}** {tr('Yes') if details.get('utilities_unpaid') else tr('No')}")
                                st.write(f"**{tr('Did the tenant leave the apartment in good condition?')}** {tr('Yes') if details.get('good_condition') else tr('No')}")
                                if details.get('comments'):
                                    st.write("**" + tr('Optional comments') + ":**")
                                    st.write(details['comments'])

                        # 🚫 No contract yet → DO NOT show the form
                        elif not contract:
                            st.warning(tr('No contract uploaded yet.'))
                            st.caption(tr('The tenant must upload the tenancy contract before you can respond.'))

                        # ✅ Contract exists → show the form
                        else:
                            with st.expander(tr('Respond Now')):
                                with st.form(f"{prefix}_landlord_response_{token}"):
                                    confirm = st.checkbox(
                                        tr("I confirm I was the landlord for this tenant and consent to the use and disclosure of my full name solely for verification of this reference."),
                                        key=f"{prefix}_confirm_{token}"
                                    )
                                    st.caption(
                                        tr("Tenant: {tenant_name} — Address: {address}")
                                        .format(tenant_name=tenant_label, address=address)
                                    )
                                    with st.expander(tr("Privacy & verification details")):
                                        p = tr("RentRight processes your responses, and if the tenant has uploaded a tenancy contract, may decrypt and review it after your confirmation solely to verify this reference (lawful basis: legitimate interests). The contract remains encrypted and is not shown to you. You may object at any time as described in the Privacy Notice.")
                                        if st.session_state.get("privacy_url"):
                                            p += f" {tr('Privacy Notice')}: {st.session_state['privacy_url']}"
                                        st.write(p)

                                    s = st.slider(
                                        tr('Overall tenant score'), 1, 10, 8,
                                        key=f"{prefix}_score_{token}"
                                    )
                                    paid_on_time = st.radio(
                                        tr('Did the tenant pay on time?'), [tr("Yes"), tr("No")],
                                        horizontal=True, key=f"{prefix}_paid_{token}"
                                    )
                                    utilities_unpaid = st.radio(
                                        tr('Did the tenant leave utilities unpaid?'), [tr("No"), tr("Yes")],
                                        horizontal=True, key=f"{prefix}_utilities_{token}"
                                    )
                                    good_condition = st.radio(
                                        tr('Did the tenant leave the apartment in good condition?'), [tr("Yes"), tr("No")],
                                        horizontal=True, key=f"{prefix}_condition_{token}"
                                    )
                                    comments = st.text_area(
                                        tr('Optional comments'),
                                        key=f"{prefix}_comments_{token}"
                                    )

                                    col_a, col_b = st.columns([1, 1])
                                    submit = col_a.form_submit_button(tr('Submit Reference'))
                                    cancel_btn = col_b.form_submit_button(tr('Not My Tenant / Cancel'))

                                if submit:
                                    if not confirm:
                                        st.error(tr('Please confirm you were the landlord.'))
                                    else:
                                        mark_reference_completed(
                                            token,
                                            confirm_landlord=True,
                                            score=int(s),
                                            paid_on_time=(paid_on_time == tr("Yes")),
                                            utilities_unpaid=(utilities_unpaid == tr("Yes")),
                                            good_condition=(good_condition == tr("Yes")),
                                            comments=comments,
                                        )
                                        st.success(tr('Reference submitted successfully.'))
                                        st.rerun()

                                if cancel_btn:
                                    cancel_reference_request(token)
                                    st.warning(tr('Request cancelled.'))
                                    st.rerun()


                    elif status == "completed":
                        with st.expander(tr('View submitted reference')):
                            details = get_reference_request_by_token(token)
                            if details:
                                def _yn(v):  # tiny helper
                                    return tr('Yes') if bool(v) else tr('No')

                                st.write(f"{tr('Confirmed landlord')}: {_yn(details.get('confirm_landlord'))}")
                                st.write(f"{tr('Score')}: {details.get('score', '—')}/10")
                                st.write(f"{tr('Paid on time')}: {_yn(details.get('paid_on_time'))}")
                                st.write(f"{tr('Unpaid utilities')}: {_yn(details.get('utilities_unpaid'))}")
                                st.write(f"{tr('Apartment in good condition')}: {_yn(details.get('good_condition'))}")

                                comments = details.get('comments')
                                if comments:
                                    st.markdown(f"**{tr('Comments')}:**")
                                    st.write(comments)
                            else:
                                st.caption(tr('No reference found.'))

        with tab_all:
            render_requests(all_reqs, "all")
        with tab_pending:
            render_requests(pending_reqs, "pending")
        with tab_completed:
            render_requests(completed_reqs, "completed")
        with tab_cancelled:
            render_requests(cancelled_reqs, "cancelled")
            
    # página actual (asumo que la guardas así al navegar)
    current_page = st.session_state.get("landlord_page", "my_contacts")

    with nav1:
        is_active = current_page == "my_contacts"
        if st.button(tr("My Contacts"), key="lnd_my_contacts",
                    use_container_width=True,
                    type=("primary" if is_active else "secondary")):
            _go("my_contacts")

    with nav2:
        is_active = current_page == "my_properties"
        if st.button(tr("My Properties"), key="lnd_my_properties",
                    use_container_width=True,
                    type=("primary" if is_active else "secondary")):
            _go("my_properties")

    with nav4:
        is_active = current_page == "my_refs"
        if st.button(tr("My References"), key="lnd_my_refs",
                    use_container_width=True,
                    type=("primary" if is_active else "secondary")):
            _go("my_refs")


    # ---------- FULL-WIDTH PAGE RENDER ----------
    page = st.session_state["landlord_page"]
    if page == "my_contacts":
        my_tenants()        
    elif page == "my_properties":
        my_properties()
    # elif page == "find_tenants":
    #     find_tenants()
    elif page == "my_refs":
        my_references()
        
    chat_panel_docked()
        
def reference_submitted_page():
    # Show ONLY the success text and stop
    st.success(tr("Reference submitted successfully. Thank you!"))
    st.stop()
    
def reference_cancelled_page():
    st.warning(tr("Request cancelled."))
    st.stop()

# ---------- App ----------
def main():
    load_smtp_defaults()
    params = st.query_params

    # ✅ direct routes
    if params.get("page") == "submitted":
        reference_submitted_page(); return
    if params.get("page") == "cancelled":
        reference_cancelled_page(); return

    token = params.get("ref")
    if token:
        reference_portal(token); return
        
        
       # --- Header ---
    col_left, col_r2, col_r3 = st.columns([3,6,1])

    with col_r2:
        render_topbar_language()

    with col_r3:
        logout_button()  # your emoji version, e.g., "➜" or 🇬🇷 for language


    with col_left: st.title("🏠 RentRight")
    if st.button("🔄", key="refresh"):
        st.rerun()

    user = st.session_state.get("user")
    if user:
        role = user.get("role")
        if role == "tenant":
            tenant_dashboard(); return
        elif role in ("landlord", "agent"):
            landlord_dashboard(); return   # agent shares landlord UI
        elif role == "admin":
            admin_dashboard(); return
        else:
            st.error(f"Unknown role: {role}"); return
    else:
        # Only show login/signup if NOT logged in
        auth_gate(); return


if __name__ == "__main__":
    main()


