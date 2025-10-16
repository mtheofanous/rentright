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
from typing import Any, Callable, Dict
import time

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
    # NEW translation keys
    "New tenant interest in your property": "Νέο ενδιαφέρον ενοικιαστή για το ακίνητό σας",
    "Hello": "Γεια σας",
    "A tenant is interested in your property": "Ένας/Μία ενοικιαστής/ρια ενδιαφέρεται για το ακίνητό σας",
    "From": "Από",
    "Message": "Μήνυμα",
    "Listing": "Καταχώριση",
    "You can reply from your inbox or connect in the app to start chatting.": "Μπορείτε να απαντήσετε από το email σας ή να συνδεθείτε στην εφαρμογή για να ξεκινήσετε συνομιλία.",
    "Interested in": "Ενδιαφέρομαι για",
    "Availability": "Διαθεσιμότητα",
    "Today": "Σήμερα",
    "Weekdays after 18:00": "Καθημερινές μετά τις 18:00",
    "Weekend mornings": "Σαββατοκύριακο πρωί",
    "Include my profile highlights": "Συμπερίληψη βασικών στοιχείων προφίλ",
    "Includes profile highlights": "Περιλαμβάνει βασικά στοιχεία προφίλ",
    "I’m interested": "Ενδιαφέρομαι",
    "Send interest": "Αποστολή ενδιαφέροντος",
    "✅ Interested": "✅ Ενδιαφέρον καταχωρήθηκε",
    "Edit message": "Επεξεργασία μηνύματος",
    "Cancel interest": "Ακύρωση ενδιαφέροντος",
    "Interest sent to {n} contact(s)": "Το ενδιαφέρον στάλθηκε σε {n} επαφή/ές",
    "Message updated": "Το μήνυμα ενημερώθηκε",
    "Interest cancelled": "Το ενδιαφέρον ακυρώθηκε",
    "My interests": "Τα ενδιαφέροντά μου",
    "No owners linked to this property yet.": "Δεν έχουν συνδεθεί ακόμη ιδιοκτήτες με αυτό το ακίνητο.",
    "No interests yet — tap “I’m interested” on a listing to track it here.": "Δεν υπάρχουν ακόμη ενδιαφέροντα — πατήστε «Ενδιαφέρομαι» σε μια καταχώριση για να το παρακολουθήσετε εδώ.",

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

# ===== Boot hooks for dynamic fields (run once at startup) =====
def _boot_dynamic_fields():
    try:
        # Si hay registry guardado en JSON, cargarlo en memoria
        ensure_registry_loaded_once()
    except Exception:
        pass
    try:
        # Garantiza que existan las columnas nuevas en BD
        ensure_dynamic_fields_schema()
    except Exception:
        pass

_boot_dynamic_fields()
# ================================================================



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



def _initials(name: str, email: str) -> str:
    base = (name or "").strip() or (email or "").split("@")[0]
    parts = [p for p in base.replace(".", " ").split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return "?"


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


def invite_future_landlord(
    tenant_id: int,
    email: str,
    tenant_name: str | None = None,
    tenant_email: str | None = None,
):
    """
    Tenant invites a future landlord/agent by email.
    Effects:
      - Ensure a contact row exists for (tenant_id, email).
      - Set invited=1 + invited_at on that contact.
      - If a landlord/agent user exists with this email, create/refresh a 'pending' connection.
    Returns:
      (ok: bool, msg: str, details: dict)
      where details = {
         "invited": True/False,                   # contact row flagged invited
         "connection_created": True/False,        # pending connection row exists
         "relation_hint": "pending" | "invited_only" | "error"
      }
    """
    email = _canon_email(email)
    c = get_conn()

    # 1) Mark the contact invited (source of truth even if the other side hasn't signed up)
    add_future_landlord_contact(tenant_id, email)
    c.execute(
        """
        UPDATE future_landlord_contacts
           SET invited=1,
               invited_at=datetime('now')
         WHERE tenant_id=? AND LOWER(email)=LOWER(?)
        """,
        (tenant_id, email),
    )
    c.commit()

    connection_created = False

    # 2) If the email belongs to a registered landlord/agent, create/refresh PENDING connection
    try:
        row = c.execute(
            """
            SELECT id, role
              FROM users
             WHERE LOWER(email)=LOWER(?)
               AND role IN ('landlord','agent')
             LIMIT 1
            """,
            (email,),
        ).fetchone()

        if row:
            landlord_id = int(row[0])
            _upsert_connection(landlord_id, tenant_id, "pending")
            connection_created = True
    except Exception as _e:
        # Don't fail the invitation flow if the lookup flaked
        pass

    # 3) Email invite (best-effort)
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
            ok_email, msg_email = send_email_smtp(email, subject, body)
        else:
            ok_email, msg_email = True, "queued"
    except Exception as e:
        ok_email, msg_email = False, f"{type(e).__name__}: {e}"

    # 4) Structured status back to the UI
    details = {
        "invited": True,
        "connection_created": connection_created,
        # Hint for your badge logic:
        # - if True: show "Pending"
        # - if False: show "Pending (awaiting signup)" or similar
        "relation_hint": "pending" if connection_created else "invited_only",
    }

    # Keep your existing return signature (ok, msg), but enrich it:
    overall_ok = True if ok_email else False
    overall_msg = "Invitation sent." if ok_email else f"Invitation saved but email failed: {msg_email}"
    return overall_ok, overall_msg, details

#======================================== PROPERTIES NEW
def ensure_property_context_schema():
    c = get_conn()
    c.execute("""
    CREATE TABLE IF NOT EXISTS connection_contexts (
      id INTEGER PRIMARY KEY,
      connection_id INTEGER NOT NULL,
      context_type TEXT NOT NULL,     -- 'property'
      context_id INTEGER NOT NULL,    -- property_id
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(connection_id, context_type, context_id)
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cc_ctx ON connection_contexts (context_type, context_id)")
    c.commit()

def _get_or_create_flc_request(landlord_id: int, tenant_id: int) -> int | None:
    c = get_conn()
    row = c.execute("""
        SELECT id FROM flc_links
        WHERE landlord_id=? AND tenant_id=?
        ORDER BY id DESC LIMIT 1
    """, (landlord_id, tenant_id)).fetchone()
    if row:
        return int(row[0])

    # Mirror from legacy table if present; else create pending link
    row2 = c.execute("""
        SELECT status FROM future_landlord_connections
        WHERE landlord_id=? AND tenant_id=?
        ORDER BY created_at DESC LIMIT 1
    """, (landlord_id, tenant_id)).fetchone()
    status = (row2[0] if row2 else "pending")
    return _upsert_flc_link(landlord_id, tenant_id, status=status)


def attach_property_context(connection_id: int, property_id: int):
    """Tag a user↔user connection with a property so UI can show 'Connected for this property'."""
    c = get_conn()
    c.execute("""
        INSERT OR IGNORE INTO connection_contexts(connection_id, context_type, context_id)
        VALUES (?, 'property', ?)
    """, (connection_id, property_id))
    c.commit()



def list_property_contexts_for_pair(landlord_id: int, tenant_id: int) -> set[int]:
    """Return property_ids tagged on the latest landlord↔tenant connection."""
    c = get_conn()
    row = c.execute("""
        SELECT id FROM flc_links 
        WHERE landlord_id=? AND tenant_id=?
        ORDER BY id DESC LIMIT 1
    """, (landlord_id, tenant_id)).fetchone()
    if not row:
        return set()
    conn_id = int(row[0])
    ids = c.execute("""
        SELECT context_id FROM connection_contexts 
        WHERE connection_id=? AND context_type='property'
    """, (conn_id,)).fetchall()
    return {int(r) for (r,) in ids}


# NEW — list all property_ids the tenant has shown interest in (via connection_contexts)
def list_interested_properties_for_tenant(tenant_id):
    c = get_conn()
    rows = c.execute("""
        SELECT DISTINCT cc.context_id
          FROM connection_contexts cc
          JOIN flc_links fl ON fl.id = cc.connection_id
         WHERE fl.tenant_id = ?
           AND cc.context_type = 'property'
        UNION
        SELECT property_id
          FROM tenant_property_interests
         WHERE tenant_id = ?
    """, (tenant_id, tenant_id)).fetchall()
    return [r[0] for r in rows]





# NEW — tiny helper to read a property's brief
def get_property_brief(property_id: int):
    """
    Returns (id, address, listing_url, region, district, city, size_m2, rooms, floor, price, updated_at)
    or None.
    """
    c = get_conn()
    row = c.execute("""
        SELECT id, address, listing_url, region, district, city, size_m2, rooms, floor, price, updated_at
        FROM landlord_properties
        WHERE id = ?
    """, (property_id,)).fetchone()
    return row

def list_interested_tenants_for_property(property_id: int) -> list[int]:
    """
    Return unique tenant_ids who showed interest in this property,
    coming from:
      - connection_contexts (for any owner/agent linked to the property), and
      - tenant_property_interests (fallback store)
    """
    c = get_conn()

    # Owners/agents linked to this property (works for legacy via fallback)
    owner_ids = list_users_linked_to_property(property_id) or []

    # 1) Interests tagged on connections for any of the owners/agents
    rows_ctx = []
    if owner_ids:
        placeholders = ",".join("?" * len(owner_ids))
        rows_ctx = c.execute(f"""
            SELECT DISTINCT fl.tenant_id
              FROM connection_contexts cc
              JOIN flc_links fl ON fl.id = cc.connection_id
             WHERE cc.context_type = 'property'
               AND cc.context_id   = ?
               AND fl.landlord_id IN ({placeholders})
        """, (property_id, *owner_ids)).fetchall()

    # 2) Fallback interests (no owner known at the time)
    rows_fb = c.execute("""
        SELECT DISTINCT tenant_id
          FROM tenant_property_interests
         WHERE property_id = ?
    """, (property_id,)).fetchall()

    # Merge + unique
    ids = {int(r[0]) for r in rows_ctx} | {int(r[0]) for r in rows_fb}
    return sorted(ids)

def list_users_linked_to_property(property_id: int) -> list[int]:
    """Return all user_ids (owners/agents) linked to this property."""
    c = get_conn()
    rows = c.execute(
        "SELECT user_id FROM property_user_links WHERE property_id=?",
        (property_id,)
    ).fetchall()
    if rows:

        return [int(r) for (r,) in rows]

    # Fallback for legacy data: single landlord owner
    row = c.execute("SELECT landlord_id FROM landlord_properties WHERE id=?", (property_id,)).fetchone()
    return [int(row[0])] if row else []


def _send_interest_like_connect_for_property(*, tenant_id: int, property_id: int, note_text: str | None):
    """
    Record tenant interest:
      - ensure a flc_links pending row landlord↔tenant
      - tag it with this property in connection_contexts
      - persist the note (if you store it elsewhere, add that call)
    Returns: number of owners/agents touched.
    """
    c = get_conn()

    # 1) Find owners/agents for this property (robust fallback)
    owner_ids: set[int] = set()
    try:
        for name, email, _role in (list_property_uploaders(property_id) or []):
            u = get_user_by_email(email) or {}
            if u.get("id"):
                owner_ids.add(int(u["id"]))
    except Exception:
        pass

    if not owner_ids:
        c.execute(
            "INSERT OR IGNORE INTO tenant_property_interests(tenant_id, property_id) VALUES (?,?)",
            (tenant_id, property_id)
        )
        c.commit()
        return 0  # no owners touched, but interest is now persisted


    touched = 0
    for landlord_id in owner_ids:
        # 2) ensure a pending flc_links row (or mirror legacy)
        link_id = _get_or_create_flc_request(landlord_id, tenant_id)  # returns flc_links.id
        if not link_id:
            # Final fallback: force an upsert in flc_links
            link_id = _upsert_flc_link(landlord_id, tenant_id, status="pending")

        # 3) tag connection with this property
        if link_id:
            attach_property_context(link_id, property_id)

            # 4) (optional) store note_text somewhere dedicated, if you keep interest notes
            try:
                if note_text and note_text.strip():
                    c.execute(
                        "INSERT INTO connection_notes(connection_id, note, created_at) "
                        "VALUES (?, ?, datetime('now'))",
                        (link_id, note_text.strip())
                    )
                    c.commit()
            except Exception:
                # If you don't have connection_notes table, just skip.
                pass

            touched += 1

    return touched

def _remove_interest_for_property(tenant_id: int, property_id: int) -> None:
    c = get_conn()

    # 1) Drop simple persisted interest (when no owners were found earlier)
    c.execute(
        "DELETE FROM tenant_property_interests WHERE tenant_id=? AND property_id=?",
        (tenant_id, property_id),
    )

    # 2) Drop any property context tags on the latest landlord↔tenant link(s)
    #    for all owners/agents linked to this property.
    owner_ids = list_users_linked_to_property(property_id)
    for landlord_id in owner_ids:
        row = c.execute(
            "SELECT id FROM flc_links WHERE landlord_id=? AND tenant_id=? ORDER BY id DESC LIMIT 1",
            (landlord_id, tenant_id),
        ).fetchone()
        if row:
            link_id = int(row[0])
            c.execute(
                "DELETE FROM connection_contexts WHERE connection_id=? AND context_type='property' AND context_id=?",
                (link_id, property_id),
            )
    c.commit()


#============================Ends here========================================================

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
    ll = get_user_by_id(landlord_id) or {}
    email = _canon_email(ll.get("email") or "")
    _upsert_connection(landlord_id, tenant_id, "connected")
    _upsert_flc_link(landlord_id, tenant_id, status="connected")  # <-- ensure flc_links row exists/updated
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
def render_topbar_language(ns: str):
    """Language selector for topbar. Use a unique ns per placement, e.g. 'tenant_topbar' or 'landlord_topbar'."""
    # Stable internal values; pretty labels via format_func
    LANGS = {
        "en": "🇬🇧 English",
        "el": "🇬🇷 Ελληνικά",
    }
    codes = list(LANGS.keys())

    current_code = st.session_state.get("lang_code", "en")
    try:
        idx = codes.index(current_code)
    except ValueError:
        idx = 0

    selected_code = st.selectbox(
        "🌐 Language",                       # non-empty label (can be collapsed)
        options=codes,                       # stable internal values
        index=idx,
        key=f"{ns}:lang_select",             # 👈 unique key per placement
        format_func=lambda c: LANGS[c],
        label_visibility="collapsed",
    )

    # Save both a code and a friendly name if you want
    st.session_state["lang_code"] = selected_code
    st.session_state["lang"] = "English" if selected_code == "en" else "Ελληνικά"


            
def _upsert_flc_link(landlord_id: int, tenant_id: int, status: str = "pending") -> int:
    c = get_conn()
    # try update first
    c.execute("""
        UPDATE flc_links
           SET status=?, updated_at=datetime('now')
         WHERE landlord_id=? AND tenant_id=?
    """, (status, landlord_id, tenant_id))
    if c.total_changes == 0:
        c.execute("""
            INSERT INTO flc_links(landlord_id, tenant_id, status, created_at, updated_at)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
        """, (landlord_id, tenant_id, status))
    c.commit()
    row = c.execute("""
        SELECT id FROM flc_links
        WHERE landlord_id=? AND tenant_id=?
        ORDER BY id DESC LIMIT 1
    """, (landlord_id, tenant_id)).fetchone()
    return int(row[0]) if row else None



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
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        conn.execute("PRAGMA journal_mode=DELETE;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=15000;")  # was 5000
    return conn


#=================================================================
# ADMIN MANAGE PROPERTY CHARACTERISTICS 
#==================================================================================
#=================================================================
# ADMIN MANAGE PROPERTY CHARACTERISTICS
#==================================================================================
# ========== Dynamic Property Fields: single source of truth ==========

# Put the registry in a definitely writable folder next to your SQLite DB
# (change WRITABLE_BASE if you already have one; otherwise we create ./data)
try:
    WRITABLE_BASE  # already defined elsewhere?
except NameError:
    WRITABLE_BASE = Path(__file__).resolve().parent / "data"
WRITABLE_BASE.mkdir(parents=True, exist_ok=True)

PROPERTY_FIELDS_STORE = (WRITABLE_BASE / "property_fields.json").resolve()

# ---- Default registry (ships with the app) ----
# ---- Default registry (ships with the app) ----
PROPERTY_FIELDS: list[dict] = [
    {
        "name": "bathrooms", "column": "bathrooms", "sql_type": "INTEGER",
        "default": None, "active": True,
        "form": {"type": "number", "label": "Bathrooms", "min": 0, "max": 20, "step": 1},
        # 🔥 enable as RANGE filter in OTR
        "o2r_filter": {"mode": "range", "label_min": "Bathrooms min", "label_max": "Bathrooms max",
                       "col_min": "bathrooms_min", "col_max": "bathrooms_max"}
    },
    {
        "name": "year_built", "column": "year_built", "sql_type": "INTEGER",
        "default": None, "active": True,
        "form": {"type": "year", "label": "Year built", "min": 1900, "max": 2200},
        "o2r_filter": {"mode": "range", "label_min": "Year built min", "label_max": "Year built max",
                       "col_min": "year_built_min", "col_max": "year_built_max"}
    },
    {
        "name": "year_renovated", "column": "year_renovated", "sql_type": "INTEGER",
        "default": None, "active": True,
        "form": {"type": "year", "label": "Year renovated", "min": 1900, "max": 2200},
        "o2r_filter": {"mode": "range", "label_min": "Year renovated min", "label_max": "Year renovated max",
                       "col_min": "year_renovated_min", "col_max": "year_renovated_max"}
    },
    {
        "name": "furnished", "column": "furnished", "sql_type": "INTEGER",
        "default": 0, "active": True,
        "form": {"type": "checkbox", "label": "Furnished"},
        # 🔥 enable as BOOL filter in OTR (tenant_profiles column will be created)
        "o2r_filter": {"mode": "bool", "label": "Furnished", "col": "want_furnished"}
    },
    {
        "name": "pets", "column": "pets", "sql_type": "INTEGER",
        "default": 0, "active": True,
        "form": {"type": "checkbox", "label": "Pets"},
        "o2r_filter": {"mode": "bool", "label": "Pets allowed", "col": "want_pets"}
    },
]

def _num_hints_for_field(field_name: str, default_min: int, default_max: int, default_step: int = 1):
    """
    Look up min/max/step for a field from PROPERTY_FIELDS.form,
    fallback to the provided defaults.
    """
    try:
        for f in (PROPERTY_FIELDS or []):
            if f.get("name") == field_name:
                frm = (f.get("form") or {})
                mn   = int(frm.get("min", default_min))
                mx   = int(frm.get("max", default_max))
                step = int(frm.get("step", default_step))
                return mn, mx, step
    except Exception:
        pass
    return default_min, default_max, default_step

def _sanitize_filename(p: Path|str) -> Path:
    p = Path(p)
    clean = re.sub(r"[^A-Za-z0-9._/-]", "_", str(p))
    return Path(clean)

def load_property_fields_from_disk() -> list[dict] | None:
    path = _sanitize_filename(PROPERTY_FIELDS_STORE)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else None
    except Exception:
        return None

def save_property_fields_to_disk(fields: list[dict]) -> bool:
    """Persist the PROPERTY_FIELDS registry to disk."""
    path = _sanitize_filename(PROPERTY_FIELDS_STORE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fields, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        try:
            st.warning(f"Could not persist property_fields.json: {e}")
        except Exception:
            pass
        return False

# ---------- Schema helpers ----------
def _infer_sql_type(f: dict) -> str:
    t = (f.get("sql_type") or "").upper().strip()
    if t in {"INTEGER", "REAL", "TEXT"}:
        return t
    form_type = ((f.get("form") or {}).get("type") or "").lower()
    if form_type in {"number", "year", "checkbox"}: return "INTEGER"
    if form_type in {"text", "select"}: return "TEXT"
    return "TEXT"

def ensure_landlord_property_columns() -> None:
    """Add missing columns from PROPERTY_FIELDS to landlord_properties."""
    c = get_conn()
    try:
        existing = {row[1] for row in c.execute("PRAGMA table_info(landlord_properties)").fetchall()}
    except Exception:
        return
    changed = False
    for f in (PROPERTY_FIELDS or []):
        col = f.get("column") or f.get("name")
        if not col or col in existing:
            continue
        ddl_type = _infer_sql_type(f)
        try:
            c.execute(f'ALTER TABLE landlord_properties ADD COLUMN "{col}" {ddl_type}')
            changed = True
        except Exception as e:
            st.warning(f"Could not add column {col}: {e}")
    if changed:
        c.commit()

def ensure_tenant_profile_filters_for_fields() -> None:
    """
    Add OTR filter columns to tenant_profiles when fields declare o2r_filter.
    Supports 'range' (min/max int) and 'bool' (0/1).
    """
    c = get_conn()
    try:
        existing = {r[1] for r in c.execute("PRAGMA table_info(tenant_profiles)").fetchall()}
    except Exception:
        return
    def add(col, typ="INTEGER"):
        if col not in existing:
            try: c.execute(f'ALTER TABLE tenant_profiles ADD COLUMN "{col}" {typ}')
            except Exception: pass
    for f in (PROPERTY_FIELDS or []):
        cfg = f.get("o2r_filter")
        if not cfg: 
            continue
        mode = cfg.get("mode")
        if mode == "range":
            add(cfg.get("col_min"), "INTEGER")
            add(cfg.get("col_max"), "INTEGER")
        elif mode == "bool":
            add(cfg.get("col"), "INTEGER")
    c.commit()

def ensure_dynamic_fields_schema():
    """Ensure landlord_properties + tenant_profiles have the necessary columns."""
    ensure_landlord_property_columns()
    ensure_tenant_profile_filters_for_fields()

def ensure_registry_loaded_once() -> None:
    """
    Load the registry from disk and ensure DB schema matches it.
    Always merges disk with defaults by 'name' (idempotent).
    """
    global PROPERTY_FIELDS
    disk = load_property_fields_from_disk()
    if isinstance(disk, list) and disk:
        by_name = {f["name"]: f for f in disk if isinstance(f, dict) and "name" in f}
        merged: list[dict] = []
        # keep defaults, overridden by disk
        for f in PROPERTY_FIELDS:
            merged.append(by_name.get(f["name"], f))
        # add custom fields that aren't in defaults
        default_names = {d["name"] for d in merged}
        for nm, f in by_name.items():
            if nm not in default_names:
                merged.append(f)
        PROPERTY_FIELDS = merged

    ensure_dynamic_fields_schema()  # adds missing cols in both tables
    st.session_state["_dyn_fields_loaded_once"] = True


def sync_and_migrate_after_change() -> bool:
    """Persist to disk and ensure DB schema has the new/changed columns."""
    ok_file = save_property_fields_to_disk(PROPERTY_FIELDS if isinstance(PROPERTY_FIELDS, list) else [])
    try:
        ensure_dynamic_fields_schema()
        ok_schema = True
    except Exception as e:
        ok_schema = False
        st.warning(f"Schema migration failed: {e}")
    return bool(ok_file and ok_schema)

# ---------- UI / Insert helpers ----------
def render_property_extra_inputs(prefix: str) -> dict[str, Any]:
    """
    Render dynamic inputs and return a dict {column: value}.
    'prefix' is used to namespace Streamlit keys.
    """
    vals: dict[str, Any] = {}
    for f in (PROPERTY_FIELDS or []):
        if not f.get("active", True): 
            continue
        form = f.get("form") or {}
        key = f"{prefix}:{f['name']}"
        typ = (form.get("type") or "").lower()
        label = form.get("label", f['name'].replace("_", " ").title())
        if typ == "number":
            vals[f["column"]] = st.number_input(
                label, value=f.get("default") or 0,
                min_value=form.get("min", 0), max_value=form.get("max", 99999),
                step=form.get("step", 1), key=key
            )
        elif typ == "checkbox":
            vals[f["column"]] = 1 if st.checkbox(label, value=bool(f.get("default")), key=key) else 0
        elif typ == "year":
            vals[f["column"]] = st.number_input(
                label, value=f.get("default") or 2025,
                min_value=form.get("min", 1900), max_value=form.get("max", 2200),
                step=1, key=key
            ) or None
        elif typ == "select":
            opts = form.get("options") or []
            # make sure there's at least one option to render
            if not opts: opts = ["—"]
            vals[f["column"]] = st.selectbox(label, options=opts, key=key)
        else:  # text
            vals[f["column"]] = st.text_input(label, key=key)
    return vals

def lp_add_property_dynamic(
    landlord_id: int, address: str, listing_url: str | None, visible: bool,
    base_kwargs: dict[str, Any] | None = None,
    extra_columns: dict[str, Any] | None = None,
) -> int:
    """
    Insert into landlord_properties including any dynamic PROPERTY_FIELDS columns.
    Pass base_kwargs with the core fields you already collect (region, district, city, size_m2, rooms, floor, price).
    Pass extra_columns from render_property_extra_inputs(...).
    """
    c = get_conn()
    now = _now_iso()
    vis = 1 if visible else 0
    listing_url = _norm_url(listing_url)
    base_kwargs = base_kwargs or {}
    extra_columns = extra_columns or {}

    # static columns:
    static_cols = [
        "landlord_id","address","listing_url","visible_to_tenants",
        "region","district","city","size_m2","rooms","floor","price",
        "created_at","updated_at"
    ]
    static_vals = [
        landlord_id, (address or "").strip(), listing_url, vis,
        base_kwargs.get("region"), base_kwargs.get("district"), base_kwargs.get("city"),
        base_kwargs.get("size_m2"), base_kwargs.get("rooms"), base_kwargs.get("floor"),
        base_kwargs.get("price"), now, now
    ]

    # dynamic columns (in registry order):
    dyn_cols = [f["column"] for f in PROPERTY_FIELDS]
    dyn_vals = [extra_columns.get(f["column"]) for f in PROPERTY_FIELDS]

    cols_sql = ", ".join(static_cols + dyn_cols)
    qmarks = ", ".join(["?"] * (len(static_cols) + len(dyn_cols)))

    cur = c.execute(
        f"INSERT INTO landlord_properties ({cols_sql}) VALUES ({qmarks})",
        tuple(static_vals + dyn_vals)
    )
    c.commit()
    return int(cur.lastrowid)

def property_chips_from_row(row: dict) -> list[str]:
    """
    Build chips for property cards from both core and dynamic fields.
    """
    chips: list[str] = []
    # core examples:
    if row.get("region"):   chips.append(f'<span class="pill">{row["region"]}</span>')
    if row.get("district"): chips.append(f'<span class="pill">{row["district"]}</span>')
    if row.get("city"):     chips.append(f'<span class="pill">{row["city"]}</span>')
    if row.get("size_m2"):  chips.append(f'<span class="pill">m²: {int(row["size_m2"])}</span>')
    if row.get("rooms"):    chips.append(f'<span class="pill">{int(row["rooms"])} rooms</span>')
    if row.get("floor") not in (None, "", 0): chips.append(f'<span class="pill">Floor {int(row["floor"])}</span>')
    if row.get("price"):    chips.append(f'<span class="pill">€{int(row["price"])}</span>')

    # dynamic chips (label or custom chip)
    for f in (PROPERTY_FIELDS or []):
        if not f.get("active", True):
            continue
        col = f.get("column")
        val = row.get(col)
        chip_fn: Callable[[Any], str | None] = f.get("chip")
        if callable(chip_fn):
            try:
                html = chip_fn(val)
                if html:
                    chips.append(f'<span class="pill">{html}</span>')
            except Exception:
                pass
        else:
            form_type = (f.get("form") or {}).get("type")
            label = (f.get("form") or {}).get("label", f["name"].replace("_"," ").title())
            if val in (None, "", 0):  # hide falsy unless checkbox=1
                if form_type == "checkbox" and int(val or 0) == 1:
                    chips.append(f'<span class="pill">{label}</span>')
                continue
            if form_type == "checkbox":
                if int(val) == 1:
                    chips.append(f'<span class="pill">{label}</span>')
            elif form_type in {"number","year"}:
                try:
                    chips.append(f'<span class="pill">{label}: {int(val)}</span>')
                except Exception:
                    chips.append(f'<span class="pill">{label}: {val}</span>')
            else:
                chips.append(f'<span class="pill">{label}: {val}</span>')
    return chips

# ---------- OTR filters (optional) ----------


def render_o2r_extra_filters(prefix: str = "otr"):
    out: dict[str, Any] = {}
    fields = (PROPERTY_FIELDS or [])
    active = [f for f in fields if f.get("active", True) and f.get("o2r_filter")]

    if not active:
        st.caption("No active characteristics configured for filtering.")
        return out

    cols = st.columns(2)
    ci = 0

    for f in active:
        cfg  = f["o2r_filter"]
        mode = (cfg.get("mode") or "").lower()
        label = cfg.get("label") or (f.get("form", {}) or {}).get("label") or f.get("name", "").replace("_", " ").title()

        if mode == "range":
            cmin = cfg.get("col_min")
            cmax = cfg.get("col_max")
            if not cmin or not cmax:
                continue

            # 👇 pull numeric UI hints from the field's form
            mn, mx, step = _num_hints_for_field(f["name"], default_min=0, default_max=1_000_000, default_step=1)

            c1, c2 = cols[ci % 2].columns(2)
            lo = c1.number_input(cfg.get("label_min", f"{label} min"), mn, mx, mn, step=step, key=f"{prefix}:{f['name']}:min")
            hi = c2.number_input(cfg.get("label_max", f"{label} max"), mn, mx, mn, step=step, key=f"{prefix}:{f['name']}:max")

            out[cmin] = None if (lo == mn == 0) else int(lo)
            out[cmax] = None if (hi == mn == 0) else int(hi)
            ci += 1

        elif mode == "bool":
            col = cfg.get("col")
            if not col:
                continue
            choice = cols[ci % 2].selectbox(label, ["Any", "Yes", "No"], index=0, key=f"{prefix}:{f['name']}:bool")
            out[col] = None if choice == "Any" else (1 if choice == "Yes" else 0)
            ci += 1

        elif mode == "enum":
            col = cfg.get("col")
            if not col:
                continue
            opts = (f.get("form", {}) or {}).get("options") or []
            sel = cols[ci % 2].selectbox(label, ["Any"] + list(opts), index=0, key=f"{prefix}:{f['name']}:enum")
            out[col] = "" if sel == "Any" else str(sel)
            ci += 1

 
    return out



def o2r_sql_clauses_for_fields(filters: dict[str, Any]) -> tuple[list[str], list[Any]]:
    """
    Build WHERE clauses (& params) for dynamic OTR filters to use in property search SQL.
    These target columns stored in landlord_properties.
    """
    clauses, params = [], []
    for f in (PROPERTY_FIELDS or []):
        cfg = f.get("o2r_filter")
        if not cfg: 
            continue
        col = f["column"]
        mode = cfg.get("mode")
        if mode == "range":
            lo = filters.get(cfg["col_min"])
            hi = filters.get(cfg["col_max"])
            if lo is not None:
                clauses.append(f"COALESCE({col}, -999999) >= ?"); params.append(int(lo))
            if hi is not None:
                clauses.append(f"COALESCE({col},  999999) <= ?"); params.append(int(hi))
        elif mode == "bool":
            v = filters.get(cfg["col"])
            if v is not None:
                clauses.append(f"COALESCE({col},0) = ?"); params.append(int(v))
    return clauses, params

# ---- Schema helpers & safe migrations (tenant_profiles) -----------------------



# ===== OG preview persistent cache =====

def ensure_og_cache_schema():
    c = get_conn()
    c.execute("""
    CREATE TABLE IF NOT EXISTS og_preview_cache (
        url TEXT PRIMARY KEY,
        image_url TEXT,
        title TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.commit()

def _og_cache_get(url: str):
    c = get_conn()
    row = c.execute("SELECT image_url, title FROM og_preview_cache WHERE url=?", (url,)).fetchone()
    return {"image_url": row[0], "title": row[1]} if row else None

def _og_cache_set(url: str, image_url: str | None, title: str | None):
    c = get_conn()
    c.execute("""
        INSERT INTO og_preview_cache(url, image_url, title, updated_at)
        VALUES(?,?,?,datetime('now'))
        ON CONFLICT(url) DO UPDATE SET
          image_url=excluded.image_url,
          title=excluded.title,
          updated_at=datetime('now')
    """, (url, image_url, title))
    c.commit()

def ensure_flc_links_table():
    """
    Create a canonical flc_links table (landlord<->tenant connections) if it doesn't exist,
    and backfill from future_landlord_connections when available.
    Safe to call multiple times.
    """
    c = get_conn()

    # 1) Create the canonical table if missing
    c.execute("""
    CREATE TABLE IF NOT EXISTS flc_links (
        id INTEGER PRIMARY KEY,
        landlord_id INTEGER NOT NULL,
        tenant_id   INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','connected','rejected','cancelled')) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_flc_pair ON flc_links(landlord_id, tenant_id)")

    # 2) Backfill from your existing table if it exists (name may differ in your app)
    try:
        rows = c.execute("""
            SELECT id, landlord_id, tenant_id, status, created_at
            FROM future_landlord_connections
        """).fetchall()
        for rid, lid, tid, status, created in rows:
            c.execute("""
                INSERT OR IGNORE INTO flc_links(id, landlord_id, tenant_id, status, created_at)
                VALUES (?,?,?,?,?)
            """, (rid, lid, tid, (status or 'pending'), created))
    except Exception:
        # If that legacy table doesn't exist, just skip backfill.
        pass

    c.commit()

def ensure_tenant_interest_schema():
    c = get_conn()
    c.execute("""
    CREATE TABLE IF NOT EXISTS tenant_property_interests (
      tenant_id   INTEGER NOT NULL,
      property_id INTEGER NOT NULL,
      created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(tenant_id, property_id),
      FOREIGN KEY (tenant_id)   REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (property_id) REFERENCES landlord_properties(id) ON DELETE CASCADE
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_tpi_tenant ON tenant_property_interests(tenant_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tpi_property ON tenant_property_interests(property_id)")
    c.commit()


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

try:
    ensure_flc_links_table()
except Exception as e:
    st.warning(f"FLC table ensure failed: {e}")
    
try:
    ensure_tenant_interest_schema()
except Exception as e:
    st.warning(f"Tenant interest schema warning: {e}")
    
try:
    ensure_og_cache_schema()
except Exception as e:
    print(f"[WARN] Failed to initialize OG cache schema: {e}")

    
    



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
def load_ellada_index(json_path: str | None = None, show_uploader = True):
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
    if data is None and show_uploader:
        uploaded = st.file_uploader("Ανεβάστε το ellada.json", type=["json"], key="ellada_upload",label_visibility="collapsed")
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
    
    # --- NEW: property ↔ user links (owners/agents) ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS property_user_links (
    property_id INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,          -- landlord or agent
    role        TEXT DEFAULT 'owner' CHECK(role IN ('owner','agent')),
    PRIMARY KEY (property_id, user_id),
    FOREIGN KEY (property_id) REFERENCES landlord_properties(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)     REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pul_user ON property_user_links(user_id)")

    # Backfill single-owner data so existing listings are linked
    cur.execute("""
    INSERT OR IGNORE INTO property_user_links(property_id, user_id, role)
    SELECT id, landlord_id, 'owner'
    FROM landlord_properties
    """)
    conn.commit()

    # Ensure the context table (used to tag connections with property ids) exists
    try:
        ensure_property_context_schema()
    except Exception as e:
        st.warning(f"Context schema warning: {e}")

    # add this ↓
    try:
        ensure_tenant_interest_schema()
    except Exception as e:
        st.warning(f"Tenant interest schema warning: {e}")
        
    try:
        ensure_dynamic_fields_schema()
    except Exception as e:
        st.warning(f"Property characteristic warning: {e}")
        

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


LOCKED = "database is locked"

def run_write(sql: str, params: tuple=(), max_tries: int=5, sleep_s: float=0.15):
    c = get_conn()
    for i in range(max_tries):
        try:
            c.execute(sql, params)
            c.commit()
            return
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if LOCKED in msg:
                time.sleep(sleep_s)
                continue
            raise
    # final try; re-raise
    c.execute(sql, params)
    c.commit()

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
    
    
try:
    ensure_property_context_schema()
except Exception as e:
    st.warning(f"Context schema warning: {e}")

# add this ↓
try:
    ensure_tenant_interest_schema()
except Exception as e:
    st.warning(f"Tenant interest schema warning: {e}")





def _table_has_column(conn_or_none, table: str, column: str) -> bool:
    c = conn_or_none or get_conn()
    cur = c.execute(f"PRAGMA table_info({table})")
    return any(row[1].lower() == column.lower() for row in cur.fetchall())

    
#===============================================================================================================================================
# chat helpers
#===============================================================================================================================================
# helper (place near chat helpers)
def _has_accepted_between(landlord_id: int, tenant_id: int) -> bool:
    try:
        c = get_conn()
        row = c.execute("""
            SELECT 1
              FROM interest_statuses
             WHERE landlord_id=? AND tenant_id=? AND status='accepted_tenant'
             LIMIT 1
        """, (int(landlord_id), int(tenant_id))).fetchone()
        return bool(row)
    except Exception:
        return False

def can_chat(landlord_id: int, tenant_id: int) -> bool:
    lid, tid = _thread_canon_pair(landlord_id, tenant_id)

    uL = get_user_by_id(lid) or {}
    uT = get_user_by_id(tid) or {}
    rL = (uL.get("role") or "").lower()
    rT = (uT.get("role") or "").lower()

    # landlord/agent ↔ landlord/agent (peers)
    if rL in ("landlord","agent") and rT in ("landlord","agent"):
        return can_chat_landlord_landlord(lid, tid)

    # landlord/agent ↔ tenant
    try:
        if flc_get_status(lid, tid) == "connected":
            return True
    except Exception:
        pass
    # NEW: allow when any per-property interest is accepted
    if _has_accepted_between(lid, tid):
        return True

    # tenant ↔ tenant
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

def ensure_interest_status_schema():
    c = get_conn()
    c.execute("""
    CREATE TABLE IF NOT EXISTS interest_statuses (
        landlord_id INTEGER NOT NULL,
        tenant_id   INTEGER NOT NULL,
        property_id INTEGER NOT NULL,
        status      TEXT NOT NULL CHECK(status IN ('interested_tenant','accepted_tenant')),
        updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (landlord_id, tenant_id, property_id),
        FOREIGN KEY (landlord_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (tenant_id)   REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (property_id) REFERENCES landlord_properties(id) ON DELETE CASCADE
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_is_prop ON interest_statuses(property_id)")
    c.commit()

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


ensure_interest_status_schema()

def set_interest_status(landlord_id:int, tenant_id:int, property_id:int, status:str):
    c = get_conn()
    c.execute("""
        INSERT INTO interest_statuses(landlord_id, tenant_id, property_id, status, updated_at)
        VALUES(?,?,?,?,datetime('now'))
        ON CONFLICT(landlord_id,tenant_id,property_id) DO UPDATE SET
            status=excluded.status,
            updated_at=datetime('now')
    """, (landlord_id, tenant_id, property_id, status))
    c.commit()

def get_interest_status(landlord_id:int, tenant_id:int, property_id:int) -> str | None:
    c = get_conn()
    row = c.execute("""
        SELECT status FROM interest_statuses
        WHERE landlord_id=? AND tenant_id=? AND property_id=?
    """, (landlord_id, tenant_id, property_id)).fetchone()
    return (row[0] if row else None)

def landlord_reject_interest(landlord_id:int, tenant_id:int, property_id:int):
    c = get_conn()
    # drop per-property status
    c.execute("""
        DELETE FROM interest_statuses
        WHERE landlord_id=? AND tenant_id=? AND property_id=?
    """, (landlord_id, tenant_id, property_id))

    # remove property tag from the latest LL↔Tenant link so it disappears from "Interested tenants"
    row = c.execute(
        "SELECT id FROM flc_links WHERE landlord_id=? AND tenant_id=? ORDER BY id DESC LIMIT 1",
        (landlord_id, tenant_id)
    ).fetchone()
    if row:
        link_id = int(row[0])
        c.execute(
            "DELETE FROM connection_contexts WHERE connection_id=? AND context_type='property' AND context_id=?",
            (link_id, property_id)
        )

    # also remove fallback store (if it exists for this pair)
    c.execute(
        "DELETE FROM tenant_property_interests WHERE tenant_id=? AND property_id=?",
        (tenant_id, property_id),
    )
    c.commit()


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
    # INSERT OR IGNORE is simpler and avoids a SELECT race
    run_write(
        "INSERT OR IGNORE INTO tenant_profiles(tenant_id, future_landlord_email, updated_at) "
        "VALUES (?,?,datetime('now'))",
        (tenant_id, None)
    )

        


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
    c = get_conn()
    row = c.execute(
        """
        SELECT open_to_rent,
               search_city, search_city_osm_id, search_city_osm_type,
               search_district, search_district_osm_id, search_district_osm_type,
               size_min, size_max, rooms_min, rooms_max,
               floor_min, floor_max, price_min, price_max, updated_at,
               COALESCE(search_region, '') AS search_region
        FROM tenant_profiles WHERE tenant_id=?
        """,
        (tenant_id,),
    ).fetchone()
    if not row:
        return {}
    return dict(row)

def save_open_to_rent_prefs(
    tenant_id: int,
    open_to_rent: bool,
    city: str | None,
    district: str | None,
    size_min: int | None, size_max: int | None,
    rooms_min: int | None, rooms_max: int | None,
    floor_min: int | None, floor_max: int | None,
    price_min: int | None, price_max: int | None,
    city_osm_id: int | None = None, city_osm_type: str | None = None,
    district_osm_id: int | None = None, district_osm_type: str | None = None,
    region: str | None = None,
):
    ensure_tenant_profile_row(tenant_id)
    run_write(
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
               updated_at=datetime('now')
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
            tenant_id,
        ),
    )



    
def load_profile_details(tenant_id: int) -> dict:
    c = get_conn()
    run_write(
        "INSERT OR IGNORE INTO tenant_profiles (tenant_id, updated_at) VALUES (?, datetime('now'))",
        (tenant_id,)
    )
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




from urllib.parse import urljoin

def _extract_og_from_html(html: str) -> dict:
    def find(pattern):
        m = re.search(pattern, html, flags=re.IGNORECASE|re.DOTALL)
        return m.group(1).strip() if m else None
    # Try several common tags
    img = find(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']')
    if not img:
        img = find(r'<meta[^>]+name=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']')
    if not img:
        img = find(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']')
    if not img:
        img = find(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']')
    title = find(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']') \
            or find(r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)["\']') \
            or find(r'<title[^>]*>(.*?)</title>')
    return {"image": img, "title": title}

@st.cache_data(ttl=24*3600, show_spinner=False)
def _download_html(url: str) -> str | None:
    try:
        r = requests.get(
            url, timeout=6,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RentRight/1.0"},
            allow_redirects=True,
        )
        if not r.ok: 
            return None
        ct = r.headers.get("content-type","")
        if "text/html" not in ct:
            return None
        return r.text
    except Exception:
        return None

def _get_og_preview(url: str) -> dict:
    """
    Robust: prefer cached URL; if fetch fails, DON'T overwrite a good cache with None.
    """
    if not url:
        return {"image_url": None, "title": None}

    # Check DB cache first
    cached = _og_cache_get(url)
    # Fetch page (cached via st.cache_data)
    html = _download_html(url)
    if not html:
        return cached or {"image_url": None, "title": None}

    meta = _extract_og_from_html(html)
    img = meta.get("image")
    title = (meta.get("title") or "").strip() or None

    # Make absolute
    if img:
        if img.startswith("//"): img = "https:" + img
        elif img.startswith("/"): img = urljoin(url, img)

    # If we found a new image, persist it; else keep old one
    if img:
        _og_cache_set(url, img, title)
        return {"image_url": img, "title": title}
    else:
        # no new image: keep prior good one if present
        return cached or {"image_url": None, "title": title}


@st.cache_data(ttl=24*3600, show_spinner=False)
def _download_image_bytes(img_url: str) -> bytes | None:
    try:
        r = requests.get(
            img_url, timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RentRight/1.0"},
            allow_redirects=True,
        )
        if not r.ok:
            return None
        ct = (r.headers.get("content-type") or "").lower()
        if ("image/" not in ct) and (not img_url.lower().endswith((".png",".jpg",".jpeg",".webp",".gif"))):
            return None
        return r.content
    except Exception:
        return None

def _get_listing_thumbnail(url: str) -> bytes | None:
    """
    Returns image BYTES to display; robust to future refreshes.
    """
    prev = _og_cache_get(url) if url else None
    cached_url = (prev or {}).get("image_url") if prev else None

    # Try cached URL first
    if cached_url:
        b = _download_image_bytes(cached_url)
        if b: 
            return b

    # Else, re-derive OG; then download
    meta = _get_og_preview(url) if url else {"image_url": None}
    img_url = meta.get("image_url")
    if img_url:
        b = _download_image_bytes(img_url)
        if b:
            return b

    return None


def _tenant_reference_summary(tenant_id: int) -> dict:
    """
    Returns: {"completed": int, "avg_score": float|None}
    completed = count of references whose effective status is 'completed'
    avg_score computed over completed references with non-null score.
    """
    c = get_conn()
    rows = c.execute("""
        SELECT token, status, score
        FROM reference_requests
        WHERE tenant_id=?
    """, (tenant_id,)).fetchall() or []

    completed = 0
    scored = []
    for tok, raw_status, score in rows:
        # Use the app's effective status helper so contract verification is respected
        final_status = effective_reference_status(raw_status, tok)
        if str(final_status).lower() == "completed":
            completed += 1
            if score is not None:
                try:
                    scored.append(float(score))
                except Exception:
                    pass

    avg = (sum(scored)/len(scored)) if scored else None
    return {"completed": completed, "avg_score": avg}


def _tenant_verified_docs_count(tenant_id: int) -> int:
    """
    # of verified reference contracts for this tenant (proxy for 'has necessary papers uploaded & verified')
    """
    c = get_conn()
    row = c.execute("""
        SELECT COUNT(*) FROM reference_contracts
        WHERE tenant_id=? AND status='verified'
    """, (tenant_id,)).fetchone()
    return int(row[0] if row else 0)

def _compute_property_fit(property_row: dict, tenant_id: int) -> tuple[int, list[str]]:
    """
    Returns (score_0_100, reasons[])
    Uses:
      - Affordability (salary vs price)
      - Household size vs rooms
      - Size proximity (unknown size is neutral)
      - Floor preference proximity (if tenant set floor range in open-to-rent; else neutral)
      - References present (>=1 completed)
      - Verified documents present (>=1)
      - Contract type stability bonus (permanent/indefinite > fixed > freelance)
    """

    # --- Inputs from property ---
    price      = int(property_row.get("price") or 0)
    size_m2    = property_row.get("size_m2")
    rooms      = property_row.get("rooms")
    floor      = property_row.get("floor")

    # --- Tenant profile ---
    prof = load_profile_details(tenant_id)  # has monthly_salary, contract_type, num_tenants, etc. :contentReference[oaicite:3]{index=3}
    salary       = int(prof.get("monthly_salary") or 0)
    contract     = (prof.get("contract_type") or "").strip().lower()
    household    = int(prof.get("num_tenants") or 1)

    # Open-to-rent prefs (floor range, etc.)
    prefs = load_open_to_rent_prefs(tenant_id)  # has floor_min/floor_max if user set them :contentReference[oaicite:4]{index=4}
    floor_min = prefs.get("floor_min")
    floor_max = prefs.get("floor_max")

    # --- References / docs ---
    ref_summary = _tenant_reference_summary(tenant_id)
    has_reference = ref_summary["completed"] > 0
    verified_docs = _tenant_verified_docs_count(tenant_id)

    reasons = []
    score = 0.0

    # --- 1) Affordability (weight ~35)
    # Rule of thumb: rent <= 33% of net monthly income.
    if price and salary:
        ratio = price / max(salary, 1)
        if ratio <= 0.25:      s = 35
        elif ratio <= 0.33:    s = 30
        elif ratio <= 0.40:    s = 20
        elif ratio <= 0.50:    s = 10
        else:                  s = 0
        score += s
        reasons.append(f"Affordability: {int(s)}")
    else:
        score += 15  # neutral if unknowns
        reasons.append("Affordability: ~ (insufficient data)")

    # --- 2) Rooms vs household size (weight ~20)
    if rooms and household:
        if rooms >= household:
            s = 20
        elif rooms == household - 1:
            s = 12
        else:
            s = 4
        score += s
        reasons.append(f"Rooms vs people: {int(s)}")
    else:
        score += 10
        reasons.append("Rooms vs people: ~")

    # --- 3) Size proximity (weight ~15)
    # Soft target: 35 m² per person baseline.
    if size_m2 and household:
        target = 35 * max(household, 1)
        d = abs(size_m2 - target)
        if d <= 10:        s = 15
        elif d <= 20:      s = 12
        elif d <= 40:      s = 8
        else:              s = 3
        score += s
        reasons.append(f"Size match: {int(s)}")
    else:
        score += 7
        reasons.append("Size match: ~")

    # --- 4) Floor preference proximity (weight ~5)
    if floor is not None and (floor_min is not None or floor_max is not None):
        ok_lo = (floor_min is None) or (floor >= floor_min)
        ok_hi = (floor_max is None) or (floor <= floor_max)
        s = 5 if (ok_lo and ok_hi) else 1
        score += s
        reasons.append(f"Floor preference: {int(s)}")
    else:
        score += 3
        reasons.append("Floor preference: ~")

    # --- 5) References present (weight ~15)
    if has_reference:
        score += 15
        reasons.append("Reference present: +15")
    else:
        reasons.append("Reference missing: +0")

    # --- 6) Verified documents present (weight ~5)
    if verified_docs > 0:
        score += 5
        reasons.append("Verified docs: +5")
    else:
        reasons.append("Verified docs: +0")

    # --- 7) Contract type stability bonus (weight ~5)
    # You can tune labels to your exact taxonomy.
    bonus = 0
    if "indef" in contract or "permanent" in contract:
        bonus = 5
    elif "fixed" in contract or "full" in contract:
        bonus = 3
    elif "freelance" in contract or "self" in contract or "contractor" in contract:
        bonus = 1
    score += bonus
    if bonus:
        reasons.append(f"Employment stability: +{bonus}")

    return max(0, min(100, int(round(score)))), reasons

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



def _get_property_row(pid: int) -> dict | None:
    try:
        c = get_conn()
        cols = [r[1] for r in c.execute("PRAGMA table_info(landlord_properties)")]
        row = c.execute("SELECT * FROM landlord_properties WHERE id=?", (int(pid),)).fetchone()
        if not row:
            return None
        return dict(zip(cols, row))
    except Exception:
        return None


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
        



def list_property_uploaders(property_id: int) -> list[tuple[str, str, str]]:
    """
    Return [(name, email, display_role)] for users linked to a property.
    display_role is strictly 'landlord' or 'agent'.
    Any non-'agent' role is normalized to 'landlord' (no 'owner' anywhere).
    """
    c = get_conn()
    rows = []
    try:
        rows = c.execute("""
            SELECT
                COALESCE(u.name, '')  AS name,
                COALESCE(u.email, '') AS email,
                CASE
                  WHEN LOWER(IFNULL(pul.role,'')) = 'agent' THEN 'agent'
                  WHEN LOWER(IFNULL(u.role,''))   = 'agent' THEN 'agent'
                  ELSE 'landlord'
                END AS display_role
            FROM property_user_links pul
            JOIN users u ON u.id = pul.user_id
            WHERE pul.property_id = ?
            ORDER BY
                CASE WHEN display_role='landlord' THEN 0 ELSE 1 END,
                u.name
        """, (property_id,)).fetchall()
    except Exception:
        rows = []

    if rows:
        return [(r[0], r[1], r[2]) for r in rows]

    # Legacy fallback: single uploader from landlord_properties; still map to landlord/agent only
    try:
        row = c.execute("SELECT landlord_id FROM landlord_properties WHERE id=?", (property_id,)).fetchone()
        if row and row[0]:
            u = get_user_by_id(int(row[0])) or {}
            role = (u.get("role") or "").strip().lower()
            display_role = "agent" if role == "agent" else "landlord"
            return [(u.get("name") or "", u.get("email") or "", display_role)]
    except Exception:
        pass

    return []


  
# --- Compact chat widget for popovers (stateless; no global chat_open needed) ---
# --- Compact chat widget for popovers (stateless; no global chat_open needed) ---
def render_chat_popover_box(*, viewer_role: str, me_id: int, other_id: int, key_ns: str = "chat_pop"):
    """
    Renders a full chat UI for a given pair, suitable for use inside st.popover().
    - Stateless: does NOT rely on st.session_state['chat_open'].
    - Correctly orders (landlord_id, tenant_id) when creating/loading threads to avoid NULL thread_id errors.
    - NEW: allows chat if the pair has any per-property status == 'accepted_tenant'.
    """

    # ---- Resolve users ----
    me = get_user_by_id(me_id) or {}
    partner_user = get_user_by_id(other_id) or {}

    r_me = (me.get("role") or "").lower()
    r_other = (partner_user.get("role") or "").lower()
    partner_display = (partner_user.get("name") or partner_user.get("email") or tr("Unknown")).strip()

    # ---- Helper: LL↔Tenant allowed if connected OR accepted_tenant on any property ----
    def _has_accepted_between(landlord_id: int, tenant_id: int) -> bool:
        try:
            c = get_conn()
            row = c.execute(
                """
                SELECT 1
                FROM interest_statuses
                WHERE landlord_id=? AND tenant_id=? AND status='accepted_tenant'
                LIMIT 1
                """,
                (int(landlord_id), int(tenant_id))
            ).fetchone()
            return bool(row)
        except Exception:
            return False

    def _ll_t_allowed(landlord_id: int, tenant_id: int) -> bool:
        try:
            return bool(
                can_chat_landlord_tenant(int(landlord_id), int(tenant_id))
                or _has_accepted_between(int(landlord_id), int(tenant_id))
            )
        except Exception:
            # Be forgiving in UI; the DB/creation will still guard.
            return True

    # ---- Gate: only if connected / allowed (now includes accepted_tenant) ----
    ok = True
    try:
        if viewer_role == "tenant":
            if r_other == "tenant":
                ok = (tp_get_status(me_id, other_id) or "").lower() == "connected"
            else:
                # tenant (me) → landlord/agent (other)
                ok = _ll_t_allowed(
                    landlord_id=other_id if r_other in ("landlord", "agent") else me_id,
                    tenant_id=me_id
                )
        elif viewer_role in ("landlord", "agent"):
            # landlord/agent (me) → tenant (other)
            ok = _ll_t_allowed(landlord_id=me_id, tenant_id=other_id)
        else:
            # landlord/agent ↔ landlord/agent peers
            ok = (lp_get_status(me_id, other_id) or "").lower() == "connected"
    except Exception:
        ok = True

    if not ok:
        st.warning(tr("Chat is available only after you connect."))
        return

    # ---- Thread: create/get with correct ordering ----
    thread_id = None
    try:
        if r_me == "tenant" and r_other in ("landlord", "agent"):
            # Tenant → LL/Agent
            if not _ll_t_allowed(other_id, me_id):
                st.warning(tr("Chat is available only after you connect."))
                return
            thread_id = get_or_create_thread(other_id, me_id)

        elif r_me in ("landlord", "agent") and r_other == "tenant":
            # LL/Agent → Tenant
            if not _ll_t_allowed(me_id, other_id):
                st.warning(tr("Chat is available only after you connect."))
                return
            thread_id = get_or_create_thread(me_id, other_id)

        elif r_me == "tenant" and r_other == "tenant":
            # Tenant ↔ Tenant
            thread_id = get_or_create_thread(me_id, other_id)

        else:
            # LL/Agent ↔ LL/Agent peers
            thread_id = get_or_create_thread(me_id, other_id)

    except Exception:
        st.warning(tr("Could not open chat right now. Please try again."))
        return

    if not thread_id:
        st.warning(tr("Chat unavailable."))
        return

    # ---- Avatars ----
    my_initials = _initials(me.get("name"), me.get("email"))
    partner_initials = _initials(partner_user.get("name"), partner_user.get("email"))
    my_avatar_img = _avatar_image_from_initials(my_initials)
    partner_avatar_img = _avatar_image_from_initials(partner_initials)

    # ---- Header ----
    st.subheader(f"💬 {tr('Chat with')} {partner_display}")

    # ---- Messages ----
    try:
        msgs = list_messages(thread_id, limit=200) or []
    except Exception:
        msgs = []

    for m in msgs:
        sender_id = row_get(m, "sender_id", 0)
        body = row_get(m, "body", "")
        created = row_get(m, "created_at", "")
        is_me = int(sender_id or 0) == int(me_id)
        avatar = my_avatar_img if is_me else partner_avatar_img
        with st.chat_message("user", avatar=avatar):
            st.markdown(body or "")
            if created:
                st.caption(created)

    # ---- Input ----
    txt = st.chat_input(placeholder=tr("Type a message…"), key=f"{key_ns}:{me_id}:{other_id}")
    if txt is not None:
        try:
            if not thread_id:
                st.warning(tr("Chat unavailable."))
                return
            post_message(thread_id, me_id, txt)
        finally:
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
    if labels:
        _L.update(labels)

    def kk(sfx: str) -> str:
        return f"{key_ns}:{sfx}:{landlord_id}:{tenant_id}"

    # --- helpers -------------------------------------------------------------
    def _refresh(msg=None, info=False):
        try:
            st.cache_data.clear()
        except Exception:
            pass
        if msg:
            (st.info if info else st.success)(msg)
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

    # --- relation ------------------------------------------------------------
    rel = (flc_relation_status(landlord_id, tenant_id) or "disconnected").lower()

    # --- TENANT branch: add + invite, or show status -------------------------
    if viewer_role == "tenant":
        email_norm = (tenant_other_email or "").strip()
        if not tenant_in_contacts and show_add_contact and email_norm:
            if container.button(_L["add_contact"], key=kk("tenant_add")):
                try:
                    # One-click add & invite -> sets invited=1 and/or creates pending relation
                    invite_future_landlord(
                        tenant_id,
                        email_norm,
                        st.session_state.user.get("name"),
                        st.session_state.user.get("email"),
                    )

                    _refresh(_L["sent"])  # after rerun rel should be pending_outbound (or connected if auto-accepted)
                except Exception as e:
                    # Fallback: at least save the contact (no invite) and reflect that state
                    try:
                        add_future_landlord_contact(tenant_id, email_norm)
                        _refresh(_L["added"])
                    except Exception:
                        container.error(f"{_L['cant_add']}: {e}")
        else:
            if show_status_caption:
                if rel in ("connected", "pending_inbound", "pending_outbound"):
                    cap = {
                        "connected": f"✅ {_L['cap_connected']}",
                        "pending_inbound": f"⏳ {_L['cap_inbound']}",
                        "pending_outbound": f"⏳ {_L['cap_outbound']}",
                    }[rel]
                elif tenant_in_contacts:
                    cap = f"📒 {tr('In contacts')}"  # contact saved, no invite/connection yet
                else:
                    cap = f"➕ {_L['cap_none']}"
                container.caption(cap)
        return rel

    # --- LL/AGENT branch: action buttons based on current relation -----------
    # Only show what’s allowed by the visibility flags
    if viewer_role in ("landlord", "agent"):
        if rel == "disconnected":
            if show_request and container.button(_L["request"], key=kk("req")):
                _do_request()
        elif rel == "pending_inbound":
            row = container.columns(2)
            if show_accept and row[0].button(_L["accept"], key=kk("acc")):
                _do_accept()
            if show_reject and row[1].button(_L["reject"], key=kk("rej")):
                _do_reject()
        elif rel == "pending_outbound":
            if show_cancel and container.button(_L["cancel"], key=kk("cxl")):
                _do_cancel()
        elif rel == "connected":
            if show_disconnect and container.button(_L["disconnect"], key=kk("disc")):
                _do_disconnect()

        if show_status_caption:
            cap = {
                "connected": f"✅ {_L['cap_connected']}",
                "pending_inbound": f"⏳ {_L['cap_inbound']}",
                "pending_outbound": f"⏳ {_L['cap_outbound']}",
                "disconnected": f"➕ {_L['cap_none']}",
            }[rel]
            container.caption(cap)

        return rel

    # Fallback (unknown role)
    if show_status_caption:
        container.caption(f"➕ {_L['cap_none']}")
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

    # def _open_chat():
    #     open_chat_unified(
    #         viewer_role=viewer_role,
    #         me_id=me_id,
    #         other_id=other_id
    #         # other_role not required; unified opener sets peer_mode="lp"
    #     )

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
        # Preserve your "open" detection if you still track the old drawer state
        is_open = bool(
            st.session_state.get("chat_open") and
            sel in {f"{me_id}-{other_id}", f"{other_id}-{me_id}"}
        )

        # Label + primary intent
        chat_label   = f"{_L['chat']} ({unread})" if unread > 0 else _L["chat"]
        is_primary   = (unread > 0) or is_open

        # Unique wrapper id so CSS scopes to THIS trigger only
        html_id = f"pop-lp-{me_id}-{other_id}"

        # Render popover-first for chat (so it sits with other buttons visually)
        if show_open_chat and stt == "connected":
            container = parent or st
            with container:
                # Scope CSS to this popover only
                st.markdown(f'<div id="{html_id}">', unsafe_allow_html=True)

                # Use the dynamic label (shows unread count) as the popover trigger
                with st.popover(chat_label, use_container_width=True):
                    render_chat_popover_box(
                        viewer_role="landlord",   # same UI for agents
                        me_id=me_id,
                        other_id=other_id,
                        key_ns=f"chatpop:lp:{me_id}:{other_id}"
                    )

                st.markdown('</div>', unsafe_allow_html=True)

                # Emulate "primary" button styling when needed
                if is_primary:
                    st.markdown(
                        f"""
                        <style>
                        /* Only this specific popover trigger */
                        #{html_id} button {{
                            background: #1a73e8 !important;   /* primary blue */
                            color: #ffffff !important;
                            border: 1px solid #1a73e8 !important;
                            font-weight: 600 !important;
                            border-radius: 8px !important;
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )


        if show_disconnect:
            actions.append((_L["disconnect"], "disc", _do_disconnect, "secondary"))

    elif stt == "pending":
        if inbound:
            if show_accept: actions.append((_L["accept"], "acc", _do_accept, "secondary"))
            if show_reject: actions.append((_L["reject"], "rej", _do_reject, "secondary"))
        else:
            if show_cancel: actions.append((_L["cancel"], "cxl", _do_cancel, "secondary"))

    elif stt in ("rejected", None, "", "disconnected"):
        if show_request:
            actions.append((_L["request"], "req", _do_request, "secondary"))

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
            actions.append((_labels["add"], "request", _send_request, "secondary"))

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
        # Keep your "open" detection if you still track the old drawer state
        # Keep your "open" detection if you still track the old drawer state
        is_open = bool(
            st.session_state.get("chat_open")
            and sel in {f"{me_id}-{other_id}", f"{other_id}-{me_id}"}
        )

        # Label + "primary" intent (popover has no type, we'll style it)
        chat_label = f"{tr('Message')} ({unread})" if unread > 0 else tr("Message")
        is_primary = (unread > 0) or is_open

        # Unique wrapper id so CSS only affects this one trigger
        html_id = f"pop-t2t-{me_id}-{other_id}"

        if show_open_chat and status == "connected":
            container = parent or st
            with container:
                # Scope CSS to this popover only
                st.markdown(f'<div id="{html_id}">', unsafe_allow_html=True)

                # Use the dynamic label as the popover trigger
                with st.popover(chat_label, use_container_width=True):
                    render_chat_popover_box(
                        viewer_role="tenant",
                        me_id=me_id,
                        other_id=other_id,
                        key_ns=f"chatpop:t2t:{me_id}:{other_id}"
                    )

                st.markdown('</div>', unsafe_allow_html=True)

                # Emulate "primary" button style when needed
                if is_primary:
                    st.markdown(
                        f"""
                        <style>
                        /* Only this specific popover trigger */
                        #{html_id} button {{
                            background: #1a73e8 !important;   /* primary blue */
                            color: #ffffff !important;
                            border: 1px solid #1a73e8 !important;
                            font-weight: 600 !important;
                            border-radius: 8px !important;
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )



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
                colM.markdown(f"<span class='tfl-badge tfl-badge--info'>{tr('Me')}</span>", unsafe_allow_html=True)

            else:
                if current_role in ("landlord","agent") and other_role == "tenant":
                    rel = (flc_relation_status(me_id, other_id) or "disconnected").lower()
                    if rel == "connected":
                        colM.markdown(f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
                    elif rel in ("pending_inbound","pending_outbound"):
                        colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
                    else:
                        colM.markdown(f'<span class="tfl-badge">{tr("No relation")}</span>', unsafe_allow_html=True)

                elif current_role == "tenant" and other_role in ("landlord","agent"):
                    rel = (flc_relation_status(other_id, me_id) or "disconnected").lower()  # note arg order: landlord_id, tenant_id
                    if rel == "connected":
                        colM.markdown(f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
                    elif rel in ("pending_inbound","pending_outbound") or invited or inbound_req or in_contacts:
                        colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
                    else:
                        colM.markdown(f'<span class="tfl-badge">{tr("No relation")}</span>', unsafe_allow_html=True)

                elif current_role == "tenant" and other_role == "tenant":
                    tp = tp_get_row(me_id, other_id)
                    stt = (tp.get("status") if tp else "").lower()
                    if stt == "connected":
                        colM.markdown(f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
                    elif stt == "pending":
                        colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
                    else:
                        colM.markdown(f'<span class="tfl-badge">{tr("No relation")}</span>', unsafe_allow_html=True)

                else:
                    # landlord/agent ↔ landlord/agent peers
                    stt = (lp_get_status(me_id, other_id) or "").lower()
                    if stt == "connected":
                        colM.markdown(f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
                    elif stt == "pending":
                        colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
                    else:
                        colM.markdown(f'<span class="tfl-badge">{tr("No relation")}</span>', unsafe_allow_html=True)


 
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
                    show_cancel=False,
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
                        show_cancel=False,
                        show_disconnect=False,
                        show_open_chat= False,
                        show_status_caption=False
                    )
      

# =====================================================================================================================
# PEOPLE HUB (My Contacts + Find Users)
# =====================================================================================================================

def find_users(role: str | None = None):
    
    # Resolve current user / role
    user = st.session_state.get("user") or {}
    my_id = int(user.get("id") or 0)
    current_role = (role or user.get("role") or "").strip().lower()
    
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

                    L, M, R = st.columns([9, 6, 10])

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
                                    
                                    
                                    # === 4) EXTRA CHIPS (dynamic characteristics) ===
                                    try:
                                        if 'property_extra_chips' in globals():
                                            # If you have a dict for the current row, pass that; otherwise build one quickly:
                                            it2 = {
                                                "bathrooms": locals().get("bathrooms"),
                                                "year_built": locals().get("year_built"),
                                                "year_renovated": locals().get("year_renovated"),
                                                "furnished": locals().get("furnished"),
                                            }
                                            chips.extend(property_extra_chips(it2))
                                        else:
                                            extras = []
                                            b = locals().get("bathrooms", None)
                                            yb = locals().get("year_built", None)
                                            yr = locals().get("year_renovated", None)
                                            fu = locals().get("furnished", None)
                                            if b not in (None, 0):      extras.append(f'{int(b)} {tr("bathrooms")}')
                                            if yb:                      extras.append(f'{tr("Built")} {int(yb)}')
                                            if yr:                      extras.append(f'{tr("Renovated")} {int(yr)}')
                                            if fu is not None:          extras.append(tr("Furnished") if fu else tr("Unfurnished"))
                                            for label in extras:
                                                chips.append(f'<span class="pill">{escape(label)}</span>')
                                    except Exception:
                                        pass
                                    # === /EXTRA CHIPS ===

                                       
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
        elif inbound_request or invited:
            colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
        else:
            colM.markdown(f'<span class="tfl-badge">{tr("No relation")}</span>', unsafe_allow_html=True)


        # --- Right: actions ---
        if status_ll == "connected":
            a1, a2 = colR.columns(2)

            pair_key = f"{landlord_id}-{tenant_id}"
            me_id = st.session_state.user["id"]
            thread_id_existing = get_thread_id_if_exists(landlord_id, tenant_id)
            unread = get_unread_count(thread_id_existing, me_id)

            # --- compute "open" + label/style (popover has no real open state) ---
            chat_is_open = (
                st.session_state.get("chat_open", False)
                and st.session_state.get("selected_thread") == pair_key
            )

            base = tr("Message")
            btn_label = f"{base} ({unread})" if (unread or 0) > 0 else base

            # mimic your old btn_type logic
            btn_type = "primary" if ((unread or 0) > 0 or chat_is_open) else "secondary"
            is_primary = (btn_type == "primary")

            # unique wrapper so CSS only targets THIS popover trigger
            html_id = f"pop-t2l-{tenant_id}-{landlord_id}"

            with a1:
                # wrap so CSS is scoped
                st.markdown(f'<div id="{html_id}">', unsafe_allow_html=True)

                # use your dynamic label as the popover trigger
                with st.popover(btn_label, use_container_width=True):
                    render_chat_popover_box(
                        viewer_role="tenant",
                        me_id=tenant_id,
                        other_id=landlord_id,
                        key_ns=f"chatpop:t2l:{tenant_id}:{landlord_id}"
                    )

                st.markdown('</div>', unsafe_allow_html=True)

                # style the trigger like a primary button when btn_type says so
                if is_primary:
                    st.markdown(
                        f"""
                        <style>
                        /* Only this specific trigger */
                        #{html_id} button {{
                            background: #1a73e8 !important;   /* primary blue */
                            color: #ffffff !important;
                            border: 1px solid #1a73e8 !important;
                            font-weight: 600 !important;
                            border-radius: 8px !important;
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True
                    )



            if a2.button("✖", key=k(row_uid, "disconnect_connected")):
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
        # else:
        else:  # disconnected
            # If we've sent an outbound invite -> show Cancel request
            if invited:
                if colR.button(tr("Cancel request"), key=k(row_uid, "cancel_invite")):
                    try:
                        # 1) clear the invite flag (best-effort)
                        flc_cancel_invite(tenant_id, email)
                    except Exception:
                        pass
                    # 2) remove the saved contact so it disappears from "My Contacts"
                    remove_future_landlord_contact(cid, tenant_id)
                    try: st.cache_data.clear()
                    except Exception: pass
                    _clear_transient()
                    st.info(tr("Request cancelled."))
                    st.rerun()

            elif inbound_request:
                colR.caption(tr("No actions"))

            else:
                b1, b2 = colR.columns(2)

                # Send invitation (only when truly no relation yet)
                if b1.button(tr("Send invitation"), key=k(row_uid, "send_invite_plain")):
                    invitee_user = get_user_by_email(email)
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
                        ok, msg, _details = invite_future_landlord(
                            tenant_id=tenant_id,
                            email=email,
                            tenant_name=st.session_state.user.get("name"),
                            tenant_email=st.session_state.user.get("email"),
                        )
                        if ok:
                            try: st.cache_data.clear()
                            except Exception: pass
                            _clear_transient()
                            st.success(tr("Invitation sent."))
                            st.rerun()
                        else:
                            st.error(f"{tr('Can’t send invitation')}: {msg}")

                # Optional: keep removal ONLY when not invited yet; otherwise the Cancel button above is enough
                if b2.button(tr("Remove"), key=k(row_uid, "remove_plain")):
                    remove_future_landlord_contact(cid, tenant_id)
                    try: st.cache_data.clear()
                    except Exception: pass
                    _clear_transient()
                    st.info(tr("Contact removed."))
                    st.rerun()



        # --- Properties (only when connected) ---
        # --- Properties (only when connected) ---
        if show_properties and (status_ll == "connected") and landlord_id:
            vprops = lp_list_visible_properties(landlord_id)

            # Compute once; reuse for badge checks
            linked_pids = list_property_contexts_for_pair(landlord_id, tenant_id)

            # Optional: summary chip (outside the expander so it's always visible)
            try:
                if linked_pids:
                    st.markdown(
                        f'<div style="margin-top:6px;"><span class="pt-badge pt-badge--ok">'
                        f'{tr("Linked on")} {len(linked_pids)} '
                        f'{tr("property" if len(linked_pids) == 1 else "properties")}'
                        f'</span></div>',
                        unsafe_allow_html=True
                    )
            except Exception:
                pass

            if vprops:
                with st.expander(tr("Visible properties"), expanded=False):
                    for pid, addr, url, upd, region, district, city, size_m2, rooms, floor, price in vprops:
                        where = " — ".join([x for x in [region, district, city] if x])
                        chips = []
                        if where:   chips.append(f'<span class="pill">{where}</span>')
                        if size_m2: chips.append(f'<span class="pill">{int(size_m2):,} m²</span>')
                        if rooms:   chips.append(f'<span class="pill">{int(rooms)} {tr("rooms")}</span>')
                        if floor not in (None, 0): chips.append(f'<span class="pill">{tr("Floor")} {int(floor)}</span>')
                        
                        # === 4) EXTRA CHIPS (dynamic characteristics) ===
                        try:
                            if 'property_extra_chips' in globals():
                                # If you have a dict for the current row, pass that; otherwise build one quickly:
                                it2 = {
                                    "bathrooms": locals().get("bathrooms"),
                                    "year_built": locals().get("year_built"),
                                    "year_renovated": locals().get("year_renovated"),
                                    "furnished": locals().get("furnished"),
                                }
                                chips.extend(property_extra_chips(it2))
                            else:
                                extras = []
                                b = locals().get("bathrooms", None)
                                yb = locals().get("year_built", None)
                                yr = locals().get("year_renovated", None)
                                fu = locals().get("furnished", None)
                                if b not in (None, 0):      extras.append(f'{int(b)} {tr("bathrooms")}')
                                if yb:                      extras.append(f'{tr("Built")} {int(yb)}')
                                if yr:                      extras.append(f'{tr("Renovated")} {int(yr)}')
                                if fu is not None:          extras.append(tr("Furnished") if fu else tr("Unfurnished"))
                                for label in extras:
                                    chips.append(f'<span class="pill">{escape(label)}</span>')
                        except Exception:
                            pass
                        # === /EXTRA CHIPS ===

                        
                        if price:   chips.append(f'<span class="pill">€{int(price):,}</span>')
                        chips_html = " ".join(chips)
                        link_html = f' 🔗 <a href="{url}">{_url_domain(url) or tr("Open listing")}</a>' if url else ""

                        # Per-property context badge (compute inside the loop)
                        ctx_badge = ''
                        try:
                            if int(pid) in linked_pids:
                                ctx_badge = (
                                    '<span class="pt-badge pt-badge--ok" style="margin-left:6px;">'
                                    + tr("Connected for this property") +
                                    '</span>'
                                )
                        except Exception:
                            pass

                        st.markdown(
                            f"""
                            <div class="prop-card">
                            <div class="prop-title">• {addr} {ctx_badge}</div>
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
    tid: int,
    landlord_id: int | None = None,
    inbound_request: bool = False,
    peer_mode: bool = False,
    key_ns: str = "prospects",
    # NEW: show Tenant↔Tenant actions from inside the card
    show_peer_actions: bool = False,
    peer_actions_kwargs: dict | None = None,
    # NEW: per-property context to drive "interested_tenant"/"accepted_tenant"
    property_id: int | None = None,
    # NEW: allow toggling LL-side interest actions
    show_ll_interest_actions: bool = True,
):
    """
    Renders a tenant profile card.

    - Landlord mode (default): landlord_id is an int; status/actions come from FLC (flc_*).
      If property_id is given, per-property status from interest_statuses overrides generic FLC.
    - Peer mode (tenant↔tenant): pass landlord_id=None (or peer_mode=True). Status from tenant_peers.
    """
    # --- Safe i18n and CSS helpers ---
    try:
        _ = tr
    except Exception:
        _ = lambda s: s

    try:
        _ensure_pt_css()
    except Exception:
        pass

    # ── Widget key namespace ───────────────────────────────────────────────────────
    def pk(tid_val: int, name: str) -> str:
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
    try:
        tenant_user = get_user_by_id(tid) or {}
    except Exception:
        tenant_user = {}
    tenant_name  = (tenant_user.get("name")  or "").strip()
    tenant_email = (tenant_user.get("email") or "").strip()
    tenant_phone = (tenant_user.get("phone") or "").strip()
    try:
        tenant_phone_visible = int(tenant_user.get("phone_visible") or 0)
    except Exception:
        tenant_phone_visible = 0

    # Detect peer context (tenant↔tenant from Contacts)
    is_peer_ctx = bool(peer_mode or landlord_id in (None, "", 0))
    me_id = None
    try:
        me_id = int(st.session_state.get("user", {}).get("id"))
    except Exception:
        pass

    # -------------------- STATUS RESOLUTION --------------------
    status = None
    if is_peer_ctx:
        try:
            status = (tp_get_status(me_id, tid) or "").lower()
        except Exception:
            status = None
    else:
        # Landlord mode:
        # 1) Try per-property interest status
        per_prop_status = None
        if property_id not in (None, "", 0):
            try:
                per_prop_status = (get_interest_status(int(landlord_id), int(tid), int(property_id)) or "").lower()
            except Exception:
                per_prop_status = None

        # 2) Fallback to generic FLC status
        if per_prop_status in {"interested_tenant", "accepted_tenant"}:
            status = per_prop_status
        else:
            try:
                status = (flc_get_status(int(landlord_id), int(tid)) or "").lower()
            except Exception:
                status = None

    # Header row: identity • badge • actions
    role_norm = ((tenant_user.get("role") or "").strip().lower()) or "tenant"
    is_tenant = (role_norm == "tenant")

    colL, colM, colR = st.columns([6, 3, 6])

    # Left: avatar + name/email (+ phone if visible)
    display_title = tenant_name or tenant_email or f"{_('Tenant')} #{tid}"
    initials = _pt_initials(tenant_name, tenant_email)
    phone_html = f'<div class="pt-phone">📞 {tenant_phone}</div>' if (tenant_phone and tenant_phone_visible) else ""

    try:
        icon = role_icon(role_norm) if role_norm else ""
    except Exception:
        icon = ""

    chip = f'<span class="pill">{_("Tenant")}</span>' if is_tenant else ""
    from html import escape as _esc

    colL.markdown(
        f"""
        <div class="pt-title">
          <div class="pt-avatar">{_esc(initials)}</div>
          <div>
            <div class="pt-name">{_esc(icon)} {_esc(display_title)} {chip}</div>
            <div class="pt-email"><a href="mailto:{_esc(tenant_email)}">{_esc(tenant_email)}</a></div>
            {phone_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------- BADGE (MIDDLE) --------------------
    s_l = (status or "").lower()
    if is_peer_ctx:
        if s_l == "connected":
            colM.markdown(f'<span class="pt-badge pt-badge--ok">{_("Connected")}</span>', unsafe_allow_html=True)
        elif s_l.startswith("pending"):
            colM.markdown(f'<span class="pt-badge pt-badge--info">{_("Pending")}</span>', unsafe_allow_html=True)
        elif s_l == "rejected":
            colM.markdown(f'<span class="pt-badge pt-badge--err">{_("Rejected")}</span>', unsafe_allow_html=True)
        else:
            colM.markdown(f'<span class="pt-badge">{_("No relation")}</span>', unsafe_allow_html=True)
    else:
        # Landlord mode; add per-property statuses
        if s_l in {"connected", "accepted_tenant"}:
            lab = _("Connected") if s_l == "connected" else _("Accepted")
            colM.markdown(f'<span class="pt-badge pt-badge--ok">{lab}</span>', unsafe_allow_html=True)
        elif s_l == "interested_tenant":
            colM.markdown(f'<span class="pt-badge pt-badge--info">{_("Pending")}</span>', unsafe_allow_html=True)
        elif s_l == "rejected":
            colM.markdown(f'<span class="pt-badge pt-badge--err">{_("Rejected")}</span>', unsafe_allow_html=True)
        else:
            # default pending/none
            lab = _("Pending") if s_l.startswith("pending") else _("No relation")
            cls = "pt-badge pt-badge--info" if lab == _("Pending") else "pt-badge"
            colM.markdown(f'<span class="{cls}">{lab}</span>', unsafe_allow_html=True)
            
    # --- Optional Fit Score (only for interested_tenant / accepted_tenant) ---
    # --- Fit Score pill (only for per-property "interested_tenant" / "accepted_tenant") ---
    if s_l in {"interested_tenant", "accepted_tenant"} and property_id not in (None, "", 0):
        try:
            prop_row = _get_property_row(int(property_id))
            if prop_row:
                fit_score, _reasons = _compute_property_fit(prop_row, int(tid))
                # show only the score (no progress bar), using your pill style
                colM.markdown(
                    "<div class='pill' style='background:#eefbf2;border:1px solid #b8e6c5;'>"
                    f"Fit: {int(fit_score)}%</div>",
                    unsafe_allow_html=True
                )
        except Exception:
            # swallow errors to keep the card robust
            pass



    # -------------------- ACTIONS (RIGHT) --------------------
    if is_peer_ctx:
        # Optional inline Tenant↔Tenant actions (disabled by default)
        if show_peer_actions and me_id:
            peer_display_name = (tenant_name or tenant_email or f"{_('Tenant')} #{tid}")
            _kwargs = {
                "show_add_request": True,
                "show_accept": True,
                "show_reject": True,
                "show_cancel": True,
                "show_open_chat": True,
                "show_disconnect": True,
                "show_status_caption": False,
                "nav_tab_key": _("Open chat"),
            }
            if isinstance(peer_actions_kwargs, dict):
                _kwargs.update(peer_actions_kwargs)

            try:
                render_tenant_peer_actions(
                    me_id=me_id,
                    other_id=tid,
                    other_name=peer_display_name,
                    parent=colR,
                    key_ns=f"{key_ns}:t2t:profile:{tid}",
                    **_kwargs,
                )
            except Exception:
                pass
    else:
        # -------- Landlord mode ----------
        # If the interest is per-property and pending, show Accept/Reject here.
        if s_l == "interested_tenant" and show_ll_interest_actions and property_id not in (None, "", 0):
            b1, b2 = colR.columns(2)

            if b1.button("✅ " + _("Accept"), key=pk(tid, "accept_interest")):
                try:
                    set_interest_status(int(landlord_id), int(tid), int(property_id), "accepted_tenant")
                    # keep canonical link in sync (best-effort)
                    try:
                        _upsert_flc_link(int(landlord_id), int(tid), status="connected")
                    except Exception:
                        pass
                    try: st.cache_data.clear()
                    except Exception: pass
                    st.success(_("Accepted."))
                    st.rerun()
                except Exception as e:
                    st.error(f"{_('Couldn’t accept')}: {e}")

            if b2.button("🗑️ " + _("Reject"), key=pk(tid, "reject_interest")):
                try:
                    landlord_reject_interest(int(landlord_id), int(tid), int(property_id))
                    try: st.cache_data.clear()
                    except Exception: pass
                    st.info(_("Removed from Interested tenants."))
                    st.rerun()
                except Exception as e:
                    st.error(f"{_('Couldn’t reject')}: {e}")

        elif s_l in {"connected", "accepted_tenant"}:
            # Treat accepted_tenant like connected for chat/disconnect
            a1, a2 = colR.columns(2)
            # --- unread + "is open" state for styling & label ---
            unread = 0
            try:
                tid_existing = get_thread_id_if_exists(int(landlord_id), int(tid))
                if tid_existing and me_id:
                    unread = int(get_unread_count(tid_existing, int(me_id)) or 0)
            except Exception:
                pass

            sel = str(st.session_state.get("selected_thread") or "")
            pair_keys = {f"{landlord_id}-{tid}", f"{tid}-{landlord_id}"}
            is_open = bool(st.session_state.get("chat_open") and sel in pair_keys)

            base = "✉︎"
            u = int(unread or 0)
            btn_label = base if is_open else (f"{base} ({'99+' if u > 99 else u})" if u > 0 else base)
            is_primary = (u > 0) or is_open
            html_id = f"pop-l2t-{landlord_id}-{tid}"

            with a1:
                st.markdown(f'<div id="{html_id}">', unsafe_allow_html=True)
                try:
                    with st.popover(btn_label, use_container_width=True):
                        render_chat_popover_box(
                            viewer_role="landlord",
                            me_id=int(landlord_id),
                            other_id=int(tid),
                            key_ns=f"chatpop:l2t:{landlord_id}:{tid}"
                        )
                except Exception:
                    # Popover not available? Fallback to a simple button that opens chat somewhere else.
                    st.button(btn_label, key=pk(tid, "open_chat_fallback"))
                st.markdown('</div>', unsafe_allow_html=True)

                if is_primary:
                    st.markdown(
                        f"""
                        <style>
                        #{html_id} button {{
                            background: #1a73e8 !important;
                            color: #ffffff !important;
                            border: 1px solid #1a73e8 !important;
                            font-weight: 600 !important;
                            border-radius: 8px !important;
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True
                    )

            if a2.button("✖", key=pk(tid, "disconnect")):
                try:
                    flc_disconnect(int(landlord_id), int(tid))
                    try: st.cache_data.clear()
                    except Exception: pass
                    st.warning(_("Disconnected."))
                    st.rerun()
                except Exception as e:
                    st.error(f"{_('Couldn’t disconnect')}: {e}")

        elif s_l == "rejected":
            colR.caption(_("No actions"))
        else:
            # generic pending/none → offer connect/reject OR cancel inbound
            if inbound_request:
                if colR.button(_("Cancel request"), key=pk(tid, "cancel_request")):
                    try:
                        flc_cancel_request(int(landlord_id), int(tid))
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.info(_("Request cancelled."))
                        st.rerun()
                    except Exception as e:
                        st.error(f"{_('Couldn’t cancel')}: {e}")
            else:
                c1, c2 = colR.columns(2)
                if c1.button(_("Connect"), key=pk(tid, "connect")):
                    try:
                        flc_connect(int(landlord_id), int(tid))
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.success(_("Connected."))
                        st.rerun()
                    except Exception as e:
                        st.error(f"{_('Couldn’t connect')}: {e}")
                if c2.button(_("Reject"), key=pk(tid, "reject")):
                    try:
                        flc_reject(int(landlord_id), int(tid))
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.info(_("Rejected."))
                        st.rerun()
                    except Exception as e:
                        st.error(f"{_('Couldn’t reject')}: {e}")

    # ---- Open to rent one-liner (Active only) ----
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

        # Base (existing) preference columns
        wanted = [
            "open_to_rent","search_region","search_district","search_city",
            "size_min","size_max","rooms_min","rooms_max",
            "floor_min","floor_max","price_min","price_max",
        ]

        # 🔥 NEW: pull in dynamic OTR filter columns from PROPERTY_FIELDS if present
        try:
            # Only consider active fields that declare an o2r_filter
            for f in (PROPERTY_FIELDS if 'PROPERTY_FIELDS' in globals() else []):
                if not f.get("active", True):
                    continue
                cfg = f.get("o2r_filter")
                if not cfg:
                    continue
                mode = cfg.get("mode")
                if mode == "range":
                    # add min/max filter columns if they exist in tenant_profiles
                    if cfg.get("col_min") in cols: wanted.append(cfg["col_min"])
                    if cfg.get("col_max") in cols: wanted.append(cfg["col_max"])
                elif mode == "bool":
                    if cfg.get("col") in cols: wanted.append(cfg["col"])
        except Exception:
            pass

        # Only select columns that exist
        select_cols = [cname for cname in wanted if cname in cols]
        if not select_cols:
            return None
        sql_cols = ", ".join([f'"{cname}"' for cname in select_cols])
        row = c.execute(f'SELECT {sql_cols} FROM tenant_profiles WHERE "{id_col}"=?', (tenant_id,)).fetchone()
        if not row:
            return None
        data = dict(zip(select_cols, row))

        # Only if profile is active "open to rent"
        o2r = data.get("open_to_rent")
        try:
            active = int(o2r) == 1
        except Exception:
            active = str(o2r).strip().lower() in {"1","true","yes","y"}
        if not active:
            return None

        # Formatters
        def fmt_num(v):
            if v is None or v == "" or (isinstance(v, (int, float)) and v == 0): return None
            try: return f"{int(v):,}"
            except Exception: return str(v)
        def rng(lo, hi):
            lo_f, hi_f = fmt_num(lo), fmt_num(hi)
            if lo_f and hi_f: return f"{lo_f}–{hi_f}"
            return lo_f or hi_f or None

        # Baseline tokens
        where = " — ".join([x for x in [data.get("search_region"), data.get("search_district"), data.get("search_city")] if x]) or None
        size  = rng(data.get("size_min"),  data.get("size_max"))
        rooms = rng(data.get("rooms_min"), data.get("rooms_max"))
        floor = rng(data.get("floor_min"), data.get("floor_max"))
        price = rng(data.get("price_min"), data.get("price_max"))

        # 🔥 NEW: build extra tokens from dynamic characteristics
        extras = []
        try:
            for f in (PROPERTY_FIELDS if 'PROPERTY_FIELDS' in globals() else []):
                if not f.get("active", True):
                    continue
                cfg = f.get("o2r_filter")
                if not cfg:
                    continue
                label = (
                    (f.get("form", {}) or {}).get("label")
                    or f.get("name","").replace("_"," ").title()
                )

                mode = cfg.get("mode")
                if mode == "range":
                    lo = data.get(cfg.get("col_min"))
                    hi = data.get(cfg.get("col_max"))
                    v = rng(lo, hi)
                    if v:
                        # e.g., "Bathrooms 1–2" or "Year built 1990–2005"
                        extras.append(f"{label} {v}")
                elif mode == "bool":
                    raw = data.get(cfg.get("col"))
                    if raw is None:
                        continue
                    try:
                        b = int(raw) == 1
                    except Exception:
                        b = str(raw).strip().lower() in {"1","true","yes","y"}
                    # e.g., "Furnished: Yes/No"
                    extras.append(f"{label}: " + (str(_("Yes")) if b else str(_("No"))))
        except Exception:
            pass

        return {
            "where": where,
            "size":  f"{size} m²" if size else None,
            "rooms": f"{rooms} { _('rooms')}" if rooms else None,
            "floor": f"{_('Floor')} {floor}" if floor else None,
            "price": f"€{price}" if price else None,
            "extras": extras,  # <-- 🔥 NEW: list of extra tokens (strings)
        }


    o2r = open_to_rent_tokens(tid)
    if o2r:
        chips = []
        if o2r["where"]: chips.append(f'<span class="pill">{_esc(o2r["where"])}</span>')
        if o2r["size"]:  chips.append(f'<span class="pill">{_esc(o2r["size"])}</span>')
        if o2r["rooms"]: chips.append(f'<span class="pill">{_esc(o2r["rooms"])}</span>')
        if o2r["floor"]: chips.append(f'<span class="pill">{_esc(o2r["floor"])}</span>')
        if o2r["price"]: chips.append(f'<span class="pill">{_esc(o2r["price"])}</span>')

        # 🔥 NEW: append extra dynamic chips (bathrooms, furnished, years, etc.)
        try:
            for lbl in (o2r.get("extras") or []):
                chips.append(f'<span class="pill">{_esc(lbl)}</span>')
        except Exception:
            pass
        # 🔥 /NEW

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0 2px 0">'
            f'  <span class="pt-badge pt-badge--ok">{_("Open to rent")}</span>'
            f'  <div>{" ".join(chips)}</div>'
            f'</div>',
            unsafe_allow_html=True
        )


    # ---- Document badges + References only when connected OR interested/accepted ----
    if s_l in {"connected", "interested_tenant", "accepted_tenant"}:
        try:
            render_tenant_doc_badges_inline(tid)
        except Exception:
            pass

        # References summary + details
        try:
            refs_full = list_latest_references_for_tenant_dict(tid) or []
        except Exception:
            refs_full = []
        refs_full = [r for r in refs_full if (r.get("status") or "").lower() != "cancelled"]

        st.caption(f"{_('References')}: {len(refs_full)}")

        if refs_full:
            completed_scores = [
                r.get("score") for r in refs_full
                if (r.get("status") or "").lower() == "completed" and r.get("score") is not None
            ]
            avg_score = round(sum(completed_scores) / len(completed_scores)) if completed_scores else None
            st.markdown(f"{_('Score')}: {avg_score if avg_score is not None else '—'}")
            with st.expander(_("Reference details"), expanded=False):
                def _status_badge_html(s):
                    try:
                        lab = display_status_label(s) if s else "—"
                    except Exception:
                        lab = (s or "—").title()
                    s_lc = (s or "").lower()
                    cls = "pt-badge pt-badge--info"
                    if s_lc == "completed":
                        cls = "pt-badge pt-badge--ok"
                    elif s_lc in {"rejected", "declined"}:
                        cls = "pt-badge pt-badge--err"
                    return f'<span class="{cls}">{lab}</span>'

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
                        score_chip = f'<span class="pill pill-score">{_("Score")}: {int(score_lr)}/10</span>'
                    def yn(v): return "✅" if v is True else ("❌" if v is False else "—")
                    paid_cls = "pill-ok" if paid_on is True else "pill-no" if paid_on is False else "pill-na"
                    util_cls = "pill-no" if util_unp is True else "pill-ok" if util_unp is False else "pill-na"
                    cond_cls = "pill-ok" if good_cond is True else "pill-no" if good_cond is False else "pill-na"
                    chips_html = " ".join(filter(None, [
                        score_chip,
                        f'<span class="pill {paid_cls}">{_("Paid on time")}: {yn(paid_on)}</span>',
                        f'<span class="pill {util_cls}">{_("Unpaid utilities")}: {yn(util_unp)}</span>',
                        f'<span class="pill {cond_cls}">{_("Good condition")}: {yn(good_cond)}</span>',
                    ]))
                    st.markdown(
                        f"""
                        <div class="ref-card">
                          <div class="ref-header">
                            <div class="ref-title">{_('Previous landlord')}: <a href="mailto:{_esc(prev_email)}">{_esc(prev_email)}</a></div>
                            <div>{_status_badge_html(status_lr)}</div>
                          </div>
                          <div class="ref-row">{chips_html}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if comments:
                        st.markdown(f"**{_('Comments')}**")
                        from html import escape as _e2
                        st.markdown(f"<div class='ref-comments'>{_e2(str(comments))}</div>", unsafe_allow_html=True)
    else:
        try:
            # Optional lock note when there are refs at all
            if list_latest_references_for_tenant(tid):
                st.caption("🔒 " + _("Reference details are visible after you connect."))
        except Exception:
            pass


          # ---- Profile details (popover; only when connected) -------------------------
        # ---- Profile details (modern popover; only when connected) -------------------
    if status in ["connected", "interested_tenant", "accepted_tenant"]:
        try:
            prof = load_profile_details(int(tid)) or {}
        except Exception:
            prof = {}

        def _has_val(x):
            return x not in (None, "", 0, "0")

        if any(_has_val(prof.get(k)) for k in (
            "age","monthly_salary","marital_status","job_position",
            "contract_type","pets","num_tenants","about"
        )):
            # Build key-value rows
            rows = []
            def _yesno(v):
                if v in (1, True):  return tr("Yes")
                if v in (0, False): return tr("No")
                return "—"

            if _has_val(prof.get("age")):
                rows.append((tr("Age"), str(int(prof["age"]))))
            if _has_val(prof.get("marital_status")):
                rows.append((tr("Marital status"), prof["marital_status"]))
            if _has_val(prof.get("contract_type")):
                rows.append((tr("Contract type"), prof["contract_type"]))
            if prof.get("monthly_salary") is not None:
                try:
                    rows.append((tr("Monthly salary (€)"), f"{int(prof['monthly_salary']):,}"))
                except Exception:
                    rows.append((tr("Monthly salary (€)"), str(prof['monthly_salary'])))
            rows.append((tr("Pets"), _yesno(prof.get("pets"))))
            if _has_val(prof.get("num_tenants")):
                rows.append((tr("Number of occupants"), str(int(prof["num_tenants"]))))

            about_html = ""
            if _has_val(prof.get("about")):
                from html import escape
                about_html = f"<div class='profile-about'>{escape(str(prof.get('about')))}</div>"

            # Modern button look
            st.markdown(
                """
                <style>
                .profile-btn {
                    display:inline-block;
                    padding:6px 12px;
                    border-radius:8px;
                    background:#0A66C2;
                    color:white !important;
                    text-decoration:none;
                    font-weight:500;
                    font-size:14px;
                }
                .profile-btn:hover {
                    background:#084c90;
                }
                .profile-card-modern {
                    background:#FFFFFF;
                    border-radius:10px;
                    padding:12px;
                    box-shadow:0 2px 4px rgba(0,0,0,0.08);
                }
                .profile-row {
                    display:flex;
                    justify-content:space-between;
                    padding:4px 0;
                    border-bottom:1px solid #eee;
                }
                .profile-row:last-child {
                    border-bottom:none;
                }
                .profile-label {
                    font-weight:600;
                    color:#191919;
                }
                .profile-value {
                    color:#333;
                }
                .profile-about {
                    margin-top:10px;
                    padding-top:8px;
                    border-top:1px solid #eee;
                    color:#333;
                    font-size:14px;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # Popover or expander fallback
            if hasattr(st, "popover"):
                with st.popover("Profile details"):
                    st.markdown(
                        f"""
                        <div class="profile-card-modern">
                            {''.join(f'<div class="profile-row"><div class="profile-label">{k}</div><div class="profile-value">{v}</div></div>' for k,v in rows)}
                            {about_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                with st.expander("Profile details", expanded=False):
                    st.markdown(
                        f"""
                        <div class="profile-card-modern">
                            {''.join(f'<div class="profile-row"><div class="profile-label">{k}</div><div class="profile-value">{v}</div></div>' for k,v in rows)}
                            {about_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

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
                        label_visibility="collapsed",
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
    size_min: int | None = None,
    size_max: int | None = None,
    rooms_min: int | None = None,
    rooms_max: int | None = None,
    floor_min: int | None = None,
    floor_max: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    limit: int = 100,
    extras: dict | None = None,
):
    """
    Returns a list of tenants who are open to rent, matching the specified
    search filters. Includes both base filters and dynamic property
    characteristics (via `extras` dict from render_o2r_extra_filters()).
    """

    c = get_conn()
    cur = c.cursor()

    clauses = ["tp.open_to_rent = 1"]
    params = {}

    # Get tenant_profiles table columns (for safety)
    cols = {r[1] for r in cur.execute("PRAGMA table_info(tenant_profiles)").fetchall()}

    # --- Basic filters (location + query) ---
    if q:
        clauses.append("(LOWER(u.name) LIKE LOWER(:q) OR LOWER(u.email) LIKE LOWER(:q))")
        params["q"] = f"%{q.strip()}%"

    if region:
        clauses.append("LOWER(tp.search_region) = LOWER(:region)")
        params["region"] = region.strip()

    if city:
        clauses.append("LOWER(tp.search_city) = LOWER(:city)")
        params["city"] = city.strip()

    if district:
        clauses.append("LOWER(tp.search_district) = LOWER(:district)")
        params["district"] = district.strip()

    # --- Helper for range-overlap logic ---
    def add_range_overlap(field_min: str, field_max: str, f_min_val, f_max_val):
        """Adds SQL overlap condition for tenant range preferences."""
        if f_min_val is None and f_max_val is None:
            return
        cmin = f"COALESCE(tp.{field_min}, -9999999)"
        cmax = f"COALESCE(tp.{field_max},  9999999)"
        if f_min_val is not None:
            clauses.append(f"{cmax} >= :{field_min}_atleast")
            params[f"{field_min}_atleast"] = int(f_min_val)
        if f_max_val is not None:
            clauses.append(f"{cmin} <= :{field_max}_atmost")
            params[f"{field_max}_atmost"] = int(f_max_val)

    # --- Apply range filters for standard fields ---
    add_range_overlap("size_min", "size_max", size_min, size_max)
    add_range_overlap("rooms_min", "rooms_max", rooms_min, rooms_max)
    add_range_overlap("floor_min", "floor_max", floor_min, floor_max)
    add_range_overlap("price_min", "price_max", price_min, price_max)

    # --- Apply dynamic extras from PROPERTY_FIELDS ---
    if extras:
        for k, v in extras.items():
            if v is None:
                continue

            # RANGE filters (min/max pairs)
            if k.endswith("_min"):
                # match rows where property’s max >= given min
                col_min = k
                col_max = k[:-4] + "max"
                if col_max in cols:
                    clauses.append(f"COALESCE(tp.{col_max}, 9999999) >= :{k}")
                    params[k] = int(v)

            elif k.endswith("_max"):
                # match rows where property’s min <= given max
                col_max = k
                col_min = k[:-4] + "min"
                if col_min in cols:
                    clauses.append(f"COALESCE(tp.{col_min}, -9999999) <= :{k}")
                    params[k] = int(v)

            else:
                # Boolean filters (1 or 0)
                if k in cols:
                    clauses.append(f"COALESCE(tp.{k}, 0) = :{k}")
                    params[k] = int(v)

    # --- Final SQL ---
    sql = f"""
        SELECT DISTINCT u.id AS tenant_id,
                        u.name,
                        u.email,
                        tp.search_region,
                        tp.search_city,
                        tp.search_district,
                        tp.updated_at
        FROM tenant_profiles tp
        JOIN users u ON u.id = tp.tenant_id
        WHERE {' AND '.join(clauses)}
        ORDER BY tp.updated_at DESC
        LIMIT :limit
    """

    params["limit"] = int(limit)
    cur.execute(sql, params)
    rows = cur.fetchall()

    return [dict(r) for r in rows]

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
            st.query_params(page="submitted")
        st.rerun()

    if cancel_btn:
        # landlord says “not my tenant” → just cancel the request
        cancel_reference_request(token)
        try:
            st.query_params.clear()
            st.query_params["page"] = "cancelled"
        except Exception:
            st.query_params(page="cancelled")
        st.rerun()

#------------------------------------------------------------------------------------------------------------------------------
#-----------ADMIN DASHBOARD----------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------------------------
# ================================
# ADMIN: Manage Property Characteristics
# ================================
def admin_characteristics_page():
    import streamlit as st
    import json, os

    # Fallback: ensure we have an HTML escaper even if _esc_admin isn't defined
    try:
        _esc_admin
    except NameError:
        from html import escape as _esc_admin

    global PROPERTY_FIELDS, PROPERTY_FIELDS_STORE

    st.subheader(tr("Manage Property Characteristics"))

    # --- Load registry ONCE per session (avoid overwriting in-memory changes on each render) ---
    if not st.session_state.get("_dyn_fields_loaded_once"):
        try:
            ensure_registry_loaded_once()   # pulls from PROPERTY_FIELDS_STORE if it exists + ensures schema
        except Exception as e:
            st.warning(f"{tr('Could not load registry')}: {e}")
        st.session_state["_dyn_fields_loaded_once"] = True

    # ================== Add new characteristic (first, for immediate feedback) ==================
    st.markdown("### " + tr("Add new characteristic"))
    with st.form(key="adm:add_field"):
        cA, cB, cC = st.columns([2, 2, 2])
        with cA:
            name = st.text_input(tr("Internal name (snake_case)"), placeholder="pets")
            column = st.text_input(tr("DB column name"), placeholder="pets")
        with cB:
            form_type = st.selectbox(tr("Form type"), ["number", "checkbox", "year", "text", "select"])
            sql_type = st.selectbox(tr("SQL type"), ["INTEGER", "REAL", "TEXT"])
        with cC:
            label = st.text_input(tr("Label (UI)"), placeholder="Pets")
            default_text = st.text_input(tr("Default (text/number)"), value="")

        st.markdown("**" + tr("Open-to-Rent filter (optional)") + "**")
        mode = st.selectbox(tr("Filter mode"), ["None", "range", "bool"], index=0)
        col_min = col_max = col_bool = ""
        c1, c2, c3 = st.columns(3)
        if mode == "range":
            with c1:
                col_min = st.text_input(tr("Min column (tenant_profiles)"), placeholder="bathrooms_min")
            with c2:
                col_max = st.text_input(tr("Max column (tenant_profiles)"), placeholder="bathrooms_max")
            with c3:
                st.caption(tr("Will filter landlord_properties by the same field."))
        elif mode == "bool":
            with c1:
                col_bool = st.text_input(tr("Bool column (tenant_profiles)"), placeholder="want_pets")
            with c2, c3:
                st.caption(tr("0 = No, 1 = Yes"))

        submitted = st.form_submit_button(tr("Add characteristic"))
        if submitted:
            nm = (name or "").strip()
            coln = (column or nm).strip()
            if not nm or not coln:
                st.error(tr("Please provide internal name and column."))
            else:
                fld = {
                    "name": nm,
                    "column": coln,
                    "sql_type": sql_type,
                    "default": None if default_text == "" else default_text,
                    "active": True,
                    "form": {"type": form_type, "label": (label or nm).replace("_"," ").title()},
                }
                if form_type in {"number", "year"}:
                    try:
                        fld["default"] = int(default_text) if default_text != "" else None
                    except Exception:
                        fld["default"] = None
                elif form_type == "checkbox":
                    fld["default"] = 1 if str(default_text).strip().lower() in {"1","true","yes","y"} else 0

                if mode == "range":
                    cm = (col_min or f"{coln}_min").strip()
                    cx = (col_max or f"{coln}_max").strip()
                    fld["o2r_filter"] = {
                        "mode": "range",
                        "label_min": (label or nm).replace("_"," ").title() + " " + tr("min"),
                        "label_max": (label or nm).replace("_"," ").title() + " " + tr("max"),
                        "col_min": cm, "col_max": cx,
                    }
                elif mode == "bool":
                    cb = (col_bool or f"want_{coln}").strip()
                    fld["o2r_filter"] = {
                        "mode": "bool",
                        "label": (label or nm).replace("_"," ").title(),
                        "col": cb,
                    }

                # Append & persist
                if not isinstance(PROPERTY_FIELDS, list):
                    PROPERTY_FIELDS = []
                PROPERTY_FIELDS.append(fld)

                ok = sync_and_migrate_after_change()  # saves JSON + ensures schema
                path = str(PROPERTY_FIELDS_STORE)
                if ok:
                    st.success(tr("Added. Schema updated if needed."))
                else:
                    st.warning(tr("Added, but could not persist to disk; check file permissions."))
                st.session_state["_dyn_fields_loaded_once"] = False
                st.rerun()

    st.divider()

    # ================== Existing characteristics ==================
    st.caption(tr("Existing characteristics"))
    if not isinstance(PROPERTY_FIELDS, list) or not PROPERTY_FIELDS:
        st.info(tr("No characteristics defined yet. Use the form above to add one."))
    else:
        for idx, f in enumerate(PROPERTY_FIELDS):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 2])
                name = f.get("name", "")
                col  = f.get("column", name)
                lbl  = (f.get("form", {}) or {}).get("label", name.replace("_"," ").title())
                sqlt = f.get("sql_type", "TEXT")
                act  = bool(f.get("active", True))
                c1.markdown(f"**{_esc_admin(lbl)}**  \n`{_esc_admin(name)}` → `{_esc_admin(col)}`")
                c2.markdown(f"SQL: `{_esc_admin(sqlt)}`")
                o2r = f.get("o2r_filter")
                if o2r:
                    mode = o2r.get("mode")
                    if mode == "range":
                        c3.markdown(f"{tr('OTR filter')}: range  \n`{_esc_admin(o2r.get('col_min',''))}`, `{_esc_admin(o2r.get('col_max',''))}`")
                    elif mode == "bool":
                        c3.markdown(f"{tr('OTR filter')}: bool  \n`{_esc_admin(o2r.get('col',''))}`")
                    else:
                        c3.markdown(tr("OTR filter") + f": `{_esc_admin(str(mode))}`")
                else:
                    c3.markdown(tr("OTR filter") + ": —")

                with c4:
                    new_lbl = st.text_input(tr("Label"), value=lbl, key=f"adm:lbl:{idx}")
                with c5:
                    new_active = st.checkbox(tr("Active"), value=act, key=f"adm:act:{idx}")

                save_row, hide_row, show_row = st.columns(3)
                with save_row:
                    if st.button(tr("Save"), key=f"adm:save:{idx}"):
                        f.setdefault("form", {})
                        f["form"]["label"] = new_lbl.strip() or lbl
                        f["active"] = bool(new_active)
                        ok = sync_and_migrate_after_change()
                        st.success(tr("Saved"))
                        st.rerun()
                with hide_row:
                    if act and st.button(tr("Hide"), key=f"adm:hide:{idx}"):
                        f["active"] = False
                        ok = sync_and_migrate_after_change()
                        st.success(tr("Hidden"))
                        st.rerun()
                with show_row:
                    if (not act) and st.button(tr("Show"), key=f"adm:show:{idx}"):
                        f["active"] = True
                        ok = sync_and_migrate_after_change()
                        st.success(tr("Shown"))
                        st.rerun()

    # ================== Export / Import ==================
    # ================== Export / Import ==================
    st.divider()
    st.markdown("### " + tr("Export / Import"))
    cE, cI = st.columns(2)

    # --- EXPORT ---
    with cE:
        if st.button(tr("Export registry to JSON")):
            ok = save_property_fields_to_disk(PROPERTY_FIELDS)
            # path = str(PROPERTY_FIELDS_STORE)
            if ok:
                st.success(tr("Saved to"))
            else:
                st.error(tr("Could not save file."))

    # --- IMPORT (wrapped in a form to avoid infinite reruns) ---
    with cI:
        with st.form("adm:import_form", clear_on_submit=True):
            uploaded = st.file_uploader(
                tr("Import registry (JSON)"),
                type=["json"],
                accept_multiple_files=False,
                label_visibility="collapsed"
            )
            do_import = st.form_submit_button(tr("Import"))

            if do_import and uploaded is not None:
                try:
                    data = json.load(uploaded)
                    if isinstance(data, list):
                        for x in data:
                            if not isinstance(x, dict) or "name" not in x or "column" not in x:
                                raise ValueError("Bad item in registry.")
                        PROPERTY_FIELDS[:] = data
                        ok = sync_and_migrate_after_change()
                        if ok:
                            st.success(tr("Imported and applied."))
                            st.session_state["_dyn_fields_loaded_once"] = False
                            st.rerun()
                        else:
                            st.warning(tr("Imported, but could not persist to disk."))
                    else:
                        st.error(tr("Invalid JSON format (expected a list)."))
                except Exception as e:
                    st.error(f"{tr('Import failed')}: {e}")





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


    # --- 0) Periodic cleanup on admin view (safe) ---
    try:
        cleanup_old_contracts()
    except Exception:
        pass

    # --- 1) Header + sidebar display controls ---
    st.caption(f"{tr('Logged in as')} {st.session_state.user['email']}")

    with st.sidebar:
        st.markdown("### " + tr("Display settings"))
        base_font_px = st.slider(tr("Base text size (px)"), 8, 22, 16, 1)
        content_width_px = st.slider(tr("Content width (px)"), 450, 1400, 1024, 8)
        side_gutter_px = st.slider(tr("Side padding (px)"), 0, 128, 16, 2)
        compact_headers = st.checkbox(tr("Slightly smaller headings"), value=True)

    # --- 2) CSS injector (based on sidebar settings) ---
    heading_scale = 1 if compact_headers else 1.12
    st.markdown(
        f"""
        <style>
        .appview-container .main .block-container {{
            max-width: {content_width_px}px;
            padding-left: {side_gutter_px}px;
            padding-right: {side_gutter_px}px;
        }}
        html, body, [data-testid="stAppViewContainer"] {{
            font-size: {base_font_px}px;
            line-height: 1.55;
        }}
        h1 {{ font-size: {round(base_font_px*2.0*heading_scale)}px; }}
        h2 {{ font-size: {round(base_font_px*1.6*heading_scale)}px; }}
        h3 {{ font-size: {round(base_font_px*1.35*heading_scale)}px; }}
        h4, h5, h6 {{ font-size: {round(base_font_px*1.15*heading_scale)}px; }}
        .markdown-text-container, [data-testid="stMarkdownContainer"] {{
            font-size: {base_font_px}px;
        }}
        .stTextInput > div > div input,
        .stTextArea textarea,
        .stSelectbox [data-baseweb="select"] div,
        .stNumberInput input {{
            font-size: {max(base_font_px-1, 12)}px;
        }}
        label, .st-emotion-cache-16idsys p, .st-emotion-cache-10trblm p {{
            font-size: {max(base_font_px-2, 11)}px;
        }}
        /* small badges/pills used in admin lists */
        .pt-badge {{"}}
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button(tr("Sign out")):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

    # --- 3) Main admin tabs (clean UX) ---
    tab_overview, tab_docs, tab_chars, tab_settings, tab_maint, tab_refs = st.tabs([
        "🏠 " + tr("Overview"),
        "📄 " + tr("Documents"),
        "⚙️ " + tr("Characteristics"),
        "✉️ " + tr("Email & App Settings"),
        "🛠️ " + tr("Maintenance"),
        "🧾 " + tr("References"),
    ])

    # === OVERVIEW ===================================================================
    with tab_overview:
        st.subheader(tr("Admin Overview"))
        st.write(tr("Use the tabs above to manage documents, property characteristics, email settings, maintenance tasks, and references."))

    # === DOCUMENTS ==================================================================
    with tab_docs:
        st.subheader(tr("Admin Documents"))
        try:
            render_admin_documents_tabs(st.session_state.user)
        except Exception as e:
            st.error(f"{tr('Could not render documents')}: {e}")

    # === CHARACTERISTICS (NEW) ======================================================
    with tab_chars:
        try:
            admin_characteristics_page()   # from the function I gave you earlier
        except NameError:
            st.error(tr("admin_characteristics_page() is missing. Paste the admin page function first."))
        except Exception as e:
            st.error(f"{tr('Error loading characteristics page')}: {e}")

    # === EMAIL & APP SETTINGS =======================================================
    with tab_settings:
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

        st.markdown("---")
        st.caption(tr('Send Test Email'))
        test_to = st.text_input(
            tr('Send test to'),
            value=st.session_state.get("smtp_user", ""),
            key="admin_test_to",
        )
        if st.button(tr('Send test email'), key="admin_send_test_email"):
            host = st.session_state.get("smtp_host")
            port = int(st.session_state.get("smtp_port", 587))
            user = st.session_state.get("smtp_user")
            pwd = st.session_state.get("smtp_pass")
            from_email = st.session_state.get("smtp_from") or user
            use_tls = st.session_state.get("smtp_tls", True)
            ok, msg = False, ""
            try:
                _msg = MIMEText("If you received this email, your SMTP configuration is working. ✅", "plain")
                _msg["Subject"] = "RentRight SMTP Test"
                _msg["From"] = from_email
                _msg["To"] = test_to
                server = smtplib.SMTP(host, port, timeout=15)
                if use_tls:
                    server.starttls()
                if user and pwd:
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

    # === MAINTENANCE =================================================================
    with tab_maint:
        st.subheader(tr("Maintenance"))
        st.caption(tr("Admin-only utilities. Use with care."))

        c1, c2 = st.columns(2)
        if c1.button(tr("Dry run: preview migration")):
            try:
                res = migrate_flc_tenants_to_peers(dry_run=True)
                st.info(f"{tr('Would migrate')} {res.get('found',0)} {tr('contacts')}.")
            except Exception as e:
                st.error(f"{tr('Error')}: {e}")

        if c2.button(tr("Run migration now")):
            try:
                res = migrate_flc_tenants_to_peers(dry_run=False)
                st.success(f"{tr('Migrated')} {res.get('migrated',0)} · {tr('Deleted')} {res.get('deleted',0)}")
                st.rerun()
            except Exception as e:
                st.error(f"{tr('Error')}: {e}")

    # === REFERENCES ==================================================================
    with tab_refs:
        st.subheader(tr('Pending References (All Tenants)'))

        # Pull everything, compute effective status using contract state
        try:
            all_reqs = list_reference_requests_global()
        except Exception:
            all_reqs = []

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

            conn = get_conn()  # FIX: ensure we have a DB connection in this scope

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
                        "revoked": tr("Revoked"),
                    }.get(str(final_status).lower(), final_status)

                    cols[0].markdown(f"{tr('**Tenant:**')} {tenant_label} ({tenant['email'] if tenant else '—'})")
                    cols[1].markdown(f"{tr('**To landlord:**')} {landlord_email}")
                    cols[2].markdown(f"{tr('**Created:**')} {format_dt(created_at)}")
                    cols[3].markdown(f"{tr('**Status:**')} {display_status}")

                    st.caption(f"{tr('Previous landlord:')} **{pl_name}** ({pl_email}) · {tr('Address:')} {pl_addr}")

                    # --- Contract section ---
                    contract = get_contract_by_token(token)
                    if contract:
                        consent_row = conn.cursor().execute("SELECT consent_status FROM reference_contracts WHERE token=?", (token,)).fetchone()
                        consent_badge = f"{tr('Consent')}: {consent_row[0] if consent_row else 'locked'}"
                        st.markdown(f"**{tr('Contract')}:** {contract['filename']} · {contract_status_badge(contract['status'])} · {consent_badge}")
                        st.caption(
                            f"{tr('Uploaded')}: {contract['uploaded_at']} • "
                            f"{tr('Last status update')}: {contract['status_updated_at'] or '—'}"
                            + (f" • {tr('by')} {contract['status_by']}" if contract['status_by'] else "")
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
                            st.warning(f"{tr('Unable to read the saved file')}: {e}")
                    else:
                        st.caption(tr('No contract uploaded yet.'))

                    is_completed = str(final_status).lower() == "completed"
                    is_revoked   = str(final_status).lower() == "revoked"

                    ac1, ac2 = st.columns(2)

                    if is_revoked:
                        st.error(tr("Revoked by admin"))
                        if details and (details.get("revoked_by") or details.get("revoked_at") or details.get("revoked_reason")):
                            st.caption(f"{tr('By')}: {details.get('revoked_by','—')} • {format_dt(details.get('revoked_at'))}")
                            if details.get("revoked_reason"):
                                st.write(f"**{tr('Reason')}:** {details['revoked_reason']}")
                    elif is_completed:
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
                                    promote_reference_if_ready(token)
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




#-----------------------------------------------------------------------------------------------------------------------------
# ----------------TENANT DASHBOARD-------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------
    
def tenant_dashboard():
    tenant_id = st.session_state.user["id"]
    tenant_email = (st.session_state.user.get("email") or "").strip().lower()
    tenant_name = (st.session_state.user.get("name") or "").strip()  # fallback if name in session

    # ---- NAV STATE INIT (must happen before any read) ----
    st.session_state.setdefault("tenant_page", "my_contacts")
    st.session_state.setdefault("ui_mode", "page")     # 'page' or 'search'
    st.session_state["page"] = st.session_state["tenant_page"]  # legacy alias

    # Try DB lookup if name not in session
    if not tenant_name:
        c = get_conn()
        row = c.execute("SELECT name FROM users WHERE id=? LIMIT 1", (tenant_id,)).fetchone()
        if row:
            tenant_name = (row[0] or "").strip()

    # keep any legacy "page" readers in sync (optional but safe)
    st.session_state["page"] = st.session_state["tenant_page"]
    
    def tenant_open_to_rent_section():
        # --- tiny local helper to read min/max/step hints from PROPERTY_FIELDS ----
        def _hints(field_name: str, dmin: int, dmax: int, dstep: int = 1):
            try:
                for f in (PROPERTY_FIELDS or []):
                    if f.get("name") == field_name:
                        frm = (f.get("form") or {})
                        return int(frm.get("min", dmin)), int(frm.get("max", dmax)), int(frm.get("step", dstep))
            except Exception:
                pass
            return dmin, dmax, dstep

        # Header + compact help
        c1, c2 = st.columns([6, 0.6])
        with c1:
            st.subheader(f"**{tr('Open to rent')}**")
        with c2:
            help_icon(tr("Let landlords know what you’re looking and share your criteria."), key="help_otr_header")

        tid = st.session_state.user["id"]
        prefs = load_open_to_rent_prefs(tid)

        # If reset asked, force defaults (zeros/False) instead of loading prefs.
        force_defaults = st.session_state.pop("otr_force_defaults", False)

        # Initialize numeric & flag fields (once or when forced)
        if ("otr_keys_inited" not in st.session_state) or force_defaults:
            if force_defaults:
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

        # --- UI container ---------------------------------------------------------
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

            # --- Correct seeding for the 3-level location pickers -----------------
            prefix = "otr"
            ANY = tr("Any")
            if reset_preselect or (f"{prefix}_region" not in st.session_state):
                st.session_state[f"{prefix}_region"] = pre_region or ANY
            if reset_preselect or (f"{prefix}_ru" not in st.session_state):
                st.session_state[f"{prefix}_ru"] = pre_unit or ANY
            if reset_preselect or (f"{prefix}_mun" not in st.session_state):
                st.session_state[f"{prefix}_mun"] = saved_city or ANY

            # --- Active / Inactive toggle -----------------------------------------
            cb1, cb2 = st.columns([1, 0.08])
            with cb1:
                open_flag = st.checkbox(tr("I’m looking for a place"), key="otr_open_flag")
            with cb2:
                help_icon(tr("Turn on to appear in landlord searches. You can hide this anytime."), key="help_otr_toggle")

            # --- Sticky expander + Form to avoid auto-reruns while editing --------
            st.session_state.setdefault("otr_prop_expanded", True)

            with st.expander(tr("Property characteristics"), expanded=st.session_state["otr_prop_expanded"]):
                # Linked pickers OUTSIDE the form
                region_sel, ru_sel, mun_sel = greece_location_pickers(prefix=prefix)

                # Pull numeric UI hints from registry (editable via JSON)
                size_min,  size_max,  size_step  = _hints("size_m2", 0, 10000, 5)
                rooms_min, rooms_max, rooms_step = _hints("rooms",   0, 50,    1)
                floor_min, floor_max, floor_step = _hints("floor",  -5, 100,   1)
                price_min, price_max, price_step = _hints("price",   0, 1_000_000, 50)

                # Form batches widget changes; rerun only on submit
                # Form batches widget changes; rerun only on submit
                with st.form("otr_prefs_form", clear_on_submit=False):
                    # BASE RANGES (location is picked above)
                    c1, c2 = st.columns(2)
                    size_min_val = c1.number_input(
                        tr("Min size (m²)"),
                        min_value=size_min, max_value=size_max, step=size_step,
                        key=f"{prefix}_size_min"
                    )
                    size_max_val = c2.number_input(
                        tr("Max size (m²)"),
                        min_value=size_min, max_value=size_max, step=size_step,
                        key=f"{prefix}_size_max"
                    )

                    r1, r2 = st.columns(2)
                    rooms_min_val = r1.number_input(
                        tr("Min rooms"),
                        min_value=rooms_min, max_value=rooms_max, step=rooms_step,
                        key=f"{prefix}_rooms_min"
                    )
                    rooms_max_val = r2.number_input(
                        tr("Max rooms"),
                        min_value=rooms_min, max_value=rooms_max, step=rooms_step,
                        key=f"{prefix}_rooms_max"
                    )

                    f1, f2 = st.columns(2)
                    floor_min_val = f1.number_input(
                        tr("Min floor"),
                        min_value=floor_min, max_value=floor_max, step=floor_step,
                        key=f"{prefix}_floor_min"
                    )
                    floor_max_val = f2.number_input(
                        tr("Max floor"),
                        min_value=floor_min, max_value=floor_max, step=floor_step,
                        key=f"{prefix}_floor_max"
                    )

                    p1, p2 = st.columns(2)
                    price_min_val = p1.number_input(
                        tr("Min price (€)"),
                        min_value=price_min, max_value=price_max, step=price_step,
                        key=f"{prefix}_price_min"
                    )
                    price_max_val = p2.number_input(
                        tr("Max price (€)"),
                        min_value=price_min, max_value=price_max, step=price_step,
                        key=f"{prefix}_price_max"
                    )


                    # DYNAMIC EXTRAS — same helper as Find Tenants
                    try:
                        extras = render_o2r_extra_filters(prefix=prefix) if 'render_o2r_extra_filters' in globals() else {}
                    except Exception:
                        extras = {}

                    def _none_if_zero(v):
                        try: return None if int(v) == 0 else int(v)
                        except Exception: return None

                    def _norm_any(v):
                        if v is None: return ""
                        s = str(v).strip().lower()
                        return "" if s in {"", "any", "—", "-", "— any —"} else str(v)

                    filt = {
                        "region":   _norm_any(st.session_state.get(f"{prefix}_region")),
                        "district": _norm_any(st.session_state.get(f"{prefix}_ru")),
                        "city":     _norm_any(st.session_state.get(f"{prefix}_mun")),
                        "size_min":  _none_if_zero(size_min_val),
                        "size_max":  _none_if_zero(size_max_val),
                        "rooms_min": _none_if_zero(rooms_min_val),
                        "rooms_max": _none_if_zero(rooms_max_val),
                        "floor_min": (None if floor_min_val == 0 else floor_min_val),
                        "floor_max": (None if floor_max_val == 0 else floor_max_val),
                        "price_min": _none_if_zero(price_min_val),
                        "price_max": _none_if_zero(price_max_val),
                    }

                    col_save, col_reset = st.columns([1, 1])
                    save_clicked  = col_save.form_submit_button(tr("Save preferences"))
                    reset_clicked = col_reset.form_submit_button(tr("Reset"))

                def _i(x): return 0 if x is None else int(x)  # None -> 0, else int

                # --- Handle actions after the form (runs only when submitted) -----
                if save_clicked:
                    region_clean   = (filt.get("region")   or "").strip()
                    city_clean     = (filt.get("city")     or "").strip()
                    district_clean = (filt.get("district") or "").strip()

                    if not city_clean and not district_clean:
                        st.warning(tr("Enter at least a city or a district."))
                    else:
                        try:
                            save_open_to_rent_prefs(
                                tid, bool(st.session_state["otr_open_flag"]),
                                city_clean, district_clean,
                                _i(filt.get("size_min")),  _i(filt.get("size_max")),
                                _i(filt.get("rooms_min")), _i(filt.get("rooms_max")),
                                _i(filt.get("floor_min")), _i(filt.get("floor_max")),
                                _i(filt.get("price_min")), _i(filt.get("price_max")),
                                city_osm_id=None, city_osm_type=None,
                                district_osm_id=None, district_osm_type=None,
                                region=region_clean,
                            )
                        except TypeError:
                            # Older signature without OSM/region
                            save_open_to_rent_prefs(
                                tid, bool(st.session_state["otr_open_flag"]),
                                city_clean, district_clean,
                                _i(filt.get("size_min")),  _i(filt.get("size_max")),
                                _i(filt.get("rooms_min")), _i(filt.get("rooms_max")),
                                _i(filt.get("floor_min")), _i(filt.get("floor_max")),
                                _i(filt.get("price_min")), _i(filt.get("price_max")),
                            )

                        # Save dynamic extras into tenant_profiles
                        try:
                            extras_to_save = {k: v for k, v in (extras or {}).items() if v not in (None, "")}
                            if extras_to_save:
                                c = get_conn()
                                id_col = "tenant_id"
                                cols = {r[1] for r in c.execute("PRAGMA table_info(tenant_profiles)").fetchall()}
                                if id_col not in cols and "user_id" in cols:
                                    id_col = "user_id"
                                set_cols = [f"{col}=?" for col in extras_to_save.keys()]
                                params = list(extras_to_save.values()) + [tid]
                                c.execute(f"UPDATE tenant_profiles SET {', '.join(set_cols)}, updated_at=datetime('now') WHERE {id_col}=?", tuple(params))
                                c.commit()
                        except Exception:
                            pass

                        try: st.cache_data.clear()
                        except Exception: pass
                        st.success(tr("Preferences saved."))
                        st.session_state["otr_prop_expanded"] = True  # keep it open on the next run

                if reset_clicked:
                    # Clear the exact keys used by pickers and numeric fields
                    for k in (
                        f"{prefix}_region", f"{prefix}_ru", f"{prefix}_mun",
                        f"{prefix}_size_min", f"{prefix}_size_max",
                        f"{prefix}_rooms_min", f"{prefix}_rooms_max",
                        f"{prefix}_floor_min", f"{prefix}_floor_max",
                        f"{prefix}_price_min", f"{prefix}_price_max",
                        "otr_open_flag", "otr_keys_inited"
                    ):
                        st.session_state.pop(k, None)
                    st.session_state["otr_force_defaults"]  = True
                    st.session_state["otr_reset_preselect"] = True
                    st.session_state["otr_prop_expanded"]   = True
                    st.rerun()

        # --- Profile details (Pets removed) --------------------------------------
        tid = st.session_state.user["id"]
        _prof = load_profile_details(tid)

        if "profile_editing" not in st.session_state:
            st.session_state["profile_editing"] = False

        _ensure_pt_css()

        with st.expander(tr("Profile details"), expanded=False):
            b1, _ = st.columns([3, 9])

            if not st.session_state["profile_editing"]:
                p = _prof or {}
                def _val(x, dash="—"): return (str(x).strip() if (x not in (None, "", 0)) else dash)
                chips = []
                if p.get("age"):            chips.append(f'<span class="pill">{tr("Age")}: {int(p["age"])}</span>')
                if p.get("marital_status"): chips.append(f'<span class="pill">{tr("Marital status")}: {p["marital_status"]}</span>')
                if p.get("contract_type"):  chips.append(f'<span class="pill">{tr("Contract type")}: {p["contract_type"]}</span>')
                if p.get("monthly_salary") is not None:
                    chips.append(f'<span class="pill">{tr("Monthly salary (€)")}: {int(p["monthly_salary"]):,}</span>')
                if p.get("num_tenants"):    chips.append(f'<span class="pill">{tr("Number of occupants")}: {int(p["num_tenants"])}</span>')

                from html import escape
                about_html = f"<div class='ref-comments'>{escape(p.get('about'))}</div>" if _val(p.get("about"), None) else ""

                st.markdown(
                    f"""
                    <div class="ref-card">
                    <div class="ref-header"><div class="ref-title">{tr("Profile details")}</div></div>
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
                with st.form("profile_details_form", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        age = st.number_input(tr("Age"), min_value=18, max_value=100, step=1,
                                            value=int((_prof or {}).get("age") or 18), key="profile_age")
                        monthly_salary = st.number_input(tr("Monthly salary (€)"),
                                                        min_value=0, max_value=1_000_000, step=100,
                                                        value=int((_prof or {}).get("monthly_salary") or 0),
                                                        key="profile_salary")
                        marital_status_opts = ["Single","Married","Divorced","Widowed"]
                        marital_status_idx = (marital_status_opts.index(((_prof or {}).get("marital_status") or "Single"))
                                            if ((_prof or {}).get("marital_status") in marital_status_opts) else 0)
                        marital_status = st.selectbox(tr("Marital status"),
                                                    [tr(x) for x in marital_status_opts],
                                                    index=marital_status_idx, key="profile_marital")
                        num_tenants = st.number_input(tr("Number of occupants"),
                                                    min_value=1, max_value=10, step=1,
                                                    value=int((_prof or {}).get("num_tenants") or 1),
                                                    key="profile_num_tenants")
                    with c2:
                        job_position = st.text_input(tr("Job position"), value=(_prof or {}).get("job_position") or "",
                                                    key="profile_job_position")
                        contract_type_opts = ["Permanent","Temporary","Freelancer","Other"]
                        contract_type_idx = (contract_type_opts.index(((_prof or {}).get("contract_type") or "Permanent"))
                                            if ((_prof or {}).get("contract_type") in contract_type_opts) else 0)
                        contract_type = st.selectbox(tr("Contract type"),
                                                    [tr(x) for x in contract_type_opts],
                                                    index=contract_type_idx, key="profile_contract")
                    about = st.text_area(tr("A few words about yourself"),
                                        value=(_prof or {}).get("about") or "", key="profile_about")

                    save_clicked = st.form_submit_button(tr("Save profile details"))

                if save_clicked:
                    marital_map = {tr("Single"): "Single", tr("Married"): "Married",
                                tr("Divorced"): "Divorced", tr("Widowed"): "Widowed"}
                    contract_map = {tr("Permanent"): "Permanent", tr("Temporary"): "Temporary",
                                    tr("Freelancer"): "Freelancer", tr("Other"): "Other"}
                    try:
                        # keep previous pets silently if your fn requires it
                        prev_pets = (_prof or {}).get("pets")
                        save_profile_details(
                            tid,
                            age=int(st.session_state["profile_age"]),
                            monthly_salary=int(st.session_state["profile_salary"]),
                            marital_status=marital_map.get(st.session_state["profile_marital"], "Single"),
                            job_position=st.session_state["profile_job_position"].strip(),
                            contract_type=contract_map.get(st.session_state["profile_contract"], "Permanent"),
                            pets=prev_pets,
                            num_tenants=int(st.session_state["profile_num_tenants"]),
                            about=st.session_state["profile_about"].strip(),
                        )
                    except TypeError:
                        # signature without pets
                        save_profile_details(
                            tid,
                            age=int(st.session_state["profile_age"]),
                            monthly_salary=int(st.session_state["profile_salary"]),
                            marital_status=marital_map.get(st.session_state["profile_marital"], "Single"),
                            job_position=st.session_state["profile_job_position"].strip(),
                            contract_type=contract_map.get(st.session_state["profile_contract"], "Permanent"),
                            num_tenants=int(st.session_state["profile_num_tenants"]),
                            about=st.session_state["profile_about"].strip(),
                        )
                    try: st.cache_data.clear()
                    except Exception: pass
                    st.success(tr("Changes saved."))
                    st.session_state["profile_editing"] = False
                    st.rerun()

        # --- Compact summary ------------------------------------------------------
        ANY = tr("Any")
        raw_region   = st.session_state.get("otr_region") or (prefs.get("region") or "")
        raw_district = st.session_state.get("otr_ru")     or (prefs.get("search_district") or "")
        raw_city     = st.session_state.get("otr_mun")    or (prefs.get("search_city") or "")

        def _clean_loc(x: str) -> str:
            s = (x or "").strip()
            return "" if s in {"", "—", ANY} else s

        region   = _clean_loc(raw_region)
        district = _clean_loc(raw_district)
        city     = _clean_loc(raw_city)

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

    
    # def tenant_open_to_rent_section():
    #     # Header + compact help
    #     c1, c2 = st.columns([6, 0.6])
    #     with c1:
    #         st.subheader(f"**{tr('Open to rent')}**")
    #     with c2:
    #         help_icon(tr("Let landlords know what you’re looking and share your criteria."), key="help_otr_header")

    #     tid = st.session_state.user["id"]
    #     prefs = load_open_to_rent_prefs(tid)

    #     # If reset asked, we force defaults (zeros/False) instead of loading prefs.
    #     force_defaults = st.session_state.pop("otr_force_defaults", False)

    #     # Initialize numeric & flag fields (once or when forced)
    #     if ("otr_keys_inited" not in st.session_state) or force_defaults:
    #         if force_defaults:
    #             # Defaults
    #             st.session_state["otr_open_flag"]  = False
    #             st.session_state["otr_size_min"]   = 0
    #             st.session_state["otr_size_max"]   = 0
    #             st.session_state["otr_rooms_min"]  = 0
    #             st.session_state["otr_rooms_max"]  = 0
    #             st.session_state["otr_floor_min"]  = 0
    #             st.session_state["otr_floor_max"]  = 0
    #             st.session_state["otr_price_min"]  = 0
    #             st.session_state["otr_price_max"]  = 0
    #         else:
    #             # From saved prefs
    #             st.session_state["otr_open_flag"]  = bool(prefs.get("open_to_rent"))
    #             st.session_state["otr_size_min"]   = int(prefs.get("size_min")  or 0)
    #             st.session_state["otr_size_max"]   = int(prefs.get("size_max")  or 0)
    #             st.session_state["otr_rooms_min"]  = int(prefs.get("rooms_min") or 0)
    #             st.session_state["otr_rooms_max"]  = int(prefs.get("rooms_max") or 0)
    #             st.session_state["otr_floor_min"]  = int(prefs.get("floor_min") or 0)
    #             st.session_state["otr_floor_max"]  = int(prefs.get("floor_max") or 0)
    #             st.session_state["otr_price_min"]  = int(prefs.get("price_min") or 0)
    #             st.session_state["otr_price_max"]  = int(prefs.get("price_max") or 0)

    #         st.session_state["otr_keys_inited"] = True

    #     # --- UI container ---------------------------------------------------------
    #     with st.container(border=True):
    #         data, regions, muni_idx = load_ellada_index("ellada.json")

    #         # If we just pressed Reset, skip preselect from saved prefs this run
    #         reset_preselect = st.session_state.pop("otr_reset_preselect", False)

    #         saved_city = "" if reset_preselect else (prefs.get("search_city") or "").strip()
    #         saved_dist = "" if reset_preselect else (prefs.get("search_district") or "").strip()

    #         # Try to infer Region/Unit from saved values
    #         pre_region, pre_unit = (None, None)
    #         if saved_city and saved_city in muni_idx:
    #             pre_region, pre_unit = muni_idx[saved_city]
    #         elif saved_dist:
    #             for reg in data.get("Περιφέρειες", []):
    #                 units = (reg.get("Περιφερειακές Ενότητες") or {})
    #                 if saved_dist in units:
    #                     pre_region = reg.get("όνομα")
    #                     pre_unit = saved_dist
    #                     break

    #         # --- Correct seeding for the 3-level location pickers -----------------
    #         prefix = "otr"
    #         ANY = tr("Any")
    #         # Seed the exact keys used by the pickers/render_tenant_filters:
    #         if reset_preselect or (f"{prefix}_region" not in st.session_state):
    #             st.session_state[f"{prefix}_region"] = pre_region or ANY
    #         if reset_preselect or (f"{prefix}_ru" not in st.session_state):
    #             st.session_state[f"{prefix}_ru"] = pre_unit or ANY
    #         if reset_preselect or (f"{prefix}_mun" not in st.session_state):
    #             st.session_state[f"{prefix}_mun"] = saved_city or ANY

    #         # --- Active / Inactive toggle (kept as-is) ----------------------------
    #         cb1, cb2 = st.columns([1, 0.08])
    #         with cb1:
    #             open_flag = st.checkbox(tr("I’m looking for a place"), key="otr_open_flag")
    #         with cb2:
    #             help_icon(
    #                 tr("Turn on to appear in landlord searches. You can hide this anytime."),
    #                 key="help_otr_toggle"
    #             )

    #         # --- Sticky expander + Form to avoid auto-reruns while editing --------
    #         st.session_state.setdefault("otr_prop_expanded", True)

    #         with st.expander(tr("Property characteristics"),
    #                         expanded=st.session_state["otr_prop_expanded"]):

    #             # Linked pickers OUTSIDE the form
    #             prefix = "otr"
    #             region_sel, ru_sel, mun_sel = greece_location_pickers(prefix=prefix)

    #             # Form batches widget changes; rerun only on submit
    #             with st.form("otr_prefs_form", clear_on_submit=False):
    #                 # BASE RANGES (location is picked above)
    #                 c1, c2 = st.columns(2)
    #                 size_min_val = c1.number_input(tr("Min size (m²)"), 0, 10000, step=5, key=f"{prefix}_size_min")
    #                 size_max_val = c2.number_input(tr("Max size (m²)"), 0, 10000, step=5, key=f"{prefix}_size_max")

    #                 r1, r2 = st.columns(2)
    #                 rooms_min_val = r1.number_input(tr("Min rooms"), 0, 50, step=1, key=f"{prefix}_rooms_min")
    #                 rooms_max_val = r2.number_input(tr("Max rooms"), 0, 50, step=1, key=f"{prefix}_rooms_max")

    #                 f1, f2 = st.columns(2)
    #                 floor_min_val = f1.number_input(tr("Min floor"), -5, 100, step=1, key=f"{prefix}_floor_min")
    #                 floor_max_val = f2.number_input(tr("Max floor"), -5, 100, step=1, key=f"{prefix}_floor_max")

    #                 p1, p2 = st.columns(2)
    #                 price_min_val = p1.number_input(tr("Min price (€)"), 0, 1_000_000, step=50, key=f"{prefix}_price_min")
    #                 price_max_val = p2.number_input(tr("Max price (€)"), 0, 1_000_000, step=50, key=f"{prefix}_price_max")

    #                 # ⬇️ DYNAMIC EXTRAS — same helper as Find Tenants
    #                 try:
    #                     extras = render_o2r_extra_filters(prefix=prefix) if 'render_o2r_extra_filters' in globals() else {}
    #                 except Exception:
    #                     extras = {}

    #                 def _none_if_zero(v):
    #                     try:
    #                         return None if int(v) == 0 else int(v)
    #                     except Exception:
    #                         return None

    #                 def _norm_any(v):
    #                     if v is None:
    #                         return ""
    #                     s = str(v).strip().lower()
    #                     return "" if s in {"", "any", "—", "-", "— any —"} else str(v)

    #                 filt = {
    #                     "region":   _norm_any(st.session_state.get(f"{prefix}_region")),
    #                     "district": _norm_any(st.session_state.get(f"{prefix}_ru")),
    #                     "city":     _norm_any(st.session_state.get(f"{prefix}_mun")),
    #                     "size_min":  _none_if_zero(size_min_val),
    #                     "size_max":  _none_if_zero(size_max_val),
    #                     "rooms_min": _none_if_zero(rooms_min_val),
    #                     "rooms_max": _none_if_zero(rooms_max_val),
    #                     "floor_min": (None if floor_min_val == 0 else floor_min_val),
    #                     "floor_max": (None if floor_max_val == 0 else floor_max_val),
    #                     "price_min": _none_if_zero(price_min_val),
    #                     "price_max": _none_if_zero(price_max_val),
    #                 }

    #                 col_save, col_reset = st.columns([1, 1])
    #                 save_clicked  = col_save.form_submit_button(tr("Save preferences"))
    #                 reset_clicked = col_reset.form_submit_button(tr("Reset"))

    #             def _i(x):
    #                 """None -> 0, else int"""
    #                 return 0 if x is None else int(x)

    #             # --- Handle actions after the form (runs only when submitted) -----
    #             if save_clicked:
    #                 region_clean   = (filt.get("region")   or "").strip()
    #                 city_clean     = (filt.get("city")     or "").strip()
    #                 district_clean = (filt.get("district") or "").strip()

    #                 if not city_clean and not district_clean:
    #                     st.warning(tr("Enter at least a city or a district."))
    #                 else:
    #                     try:
    #                         save_open_to_rent_prefs(
    #                             tid, bool(st.session_state["otr_open_flag"]),
    #                             city_clean, district_clean,
    #                             _i(filt.get("size_min")),  _i(filt.get("size_max")),
    #                             _i(filt.get("rooms_min")), _i(filt.get("rooms_max")),
    #                             _i(filt.get("floor_min")), _i(filt.get("floor_max")),
    #                             _i(filt.get("price_min")), _i(filt.get("price_max")),
    #                             city_osm_id=None, city_osm_type=None,
    #                             district_osm_id=None, district_osm_type=None,
    #                             region=region_clean,
    #                         )
    #                     except TypeError:
    #                         # Fallback for older function signature without OSM/region args
    #                         save_open_to_rent_prefs(
    #                             tid, bool(st.session_state["otr_open_flag"]),
    #                             city_clean, district_clean,
    #                             _i(filt.get("size_min")),  _i(filt.get("size_max")),
    #                             _i(filt.get("rooms_min")), _i(filt.get("rooms_max")),
    #                             _i(filt.get("floor_min")), _i(filt.get("floor_max")),
    #                             _i(filt.get("price_min")), _i(filt.get("price_max")),
    #                         )

    #                     # 🔥 Save dynamic extras into tenant_profiles
    #                     try:
    #                         extras_to_save = {k: v for k, v in (extras or {}).items() if v not in (None, "")}
    #                         if extras_to_save:
    #                             c = get_conn()
    #                             # decide id column
    #                             id_col = "tenant_id"
    #                             cols = {r[1] for r in c.execute("PRAGMA table_info(tenant_profiles)").fetchall()}
    #                             if id_col not in cols and "user_id" in cols:
    #                                 id_col = "user_id"
    #                             set_cols = [f"{col}=?" for col in extras_to_save.keys()]
    #                             params = list(extras_to_save.values()) + [tid]
    #                             c.execute(f"UPDATE tenant_profiles SET {', '.join(set_cols)}, updated_at=datetime('now') WHERE {id_col}=?", tuple(params))
    #                             c.commit()
    #                     except Exception:
    #                         pass

    #                     try: st.cache_data.clear()
    #                     except Exception: pass
    #                     st.success(tr("Preferences saved."))
    #                     st.session_state["otr_prop_expanded"] = True  # keep it open on the next run

    #             if reset_clicked:
    #                 # Clear the exact keys used by pickers and numeric fields
    #                 for k in (
    #                     f"{prefix}_region", f"{prefix}_ru", f"{prefix}_mun",
    #                     f"{prefix}_size_min", f"{prefix}_size_max",
    #                     f"{prefix}_rooms_min", f"{prefix}_rooms_max",
    #                     f"{prefix}_floor_min", f"{prefix}_floor_max",
    #                     f"{prefix}_price_min", f"{prefix}_price_max",
    #                     "otr_open_flag", "otr_keys_inited"
    #                 ):
    #                     st.session_state.pop(k, None)

    #                 st.session_state["otr_force_defaults"]  = True
    #                 st.session_state["otr_reset_preselect"] = True
    #                 st.session_state["otr_prop_expanded"]   = True  # keep open after reset
    #                 st.rerun()

    #     # --- Profile details (own Edit/Save flow) -------------------------------------
    #     tid = st.session_state.user["id"]
    #     _prof = load_profile_details(tid)

    #     # one-time default for edit mode
    #     if "profile_editing" not in st.session_state:
    #         st.session_state["profile_editing"] = False

    #     _ensure_pt_css()

    #     with st.expander(tr("Profile details"), expanded=False):
    #         # Header row with Edit / Save / Cancel
    #         b1, _ = st.columns([3, 9])

    #         if not st.session_state["profile_editing"]:
    #             # Read-only summary chips (🐾 Pets removed)
    #             p = _prof or {}
    #             def _val(x, dash="—"): return (str(x).strip() if (x not in (None, "", 0)) else dash)
    #             chips = []
    #             if p.get("age"):              chips.append(f'<span class="pill">{tr("Age")}: {int(p["age"])}</span>')
    #             if p.get("marital_status"):   chips.append(f'<span class="pill">{tr("Marital status")}: {p["marital_status"]}</span>')
    #             if p.get("contract_type"):    chips.append(f'<span class="pill">{tr("Contract type")}: {p["contract_type"]}</span>')
    #             if p.get("monthly_salary") is not None:
    #                 chips.append(f'<span class="pill">{tr("Monthly salary (€)")}: {int(p["monthly_salary"]):,}</span>')
    #             if p.get("num_tenants"):      chips.append(f'<span class="pill">{tr("Number of occupants")}: {int(p["num_tenants"])}</span>')

    #             about_html = ""
    #             if _val(p.get("about"), None):
    #                 from html import escape
    #                 about_html = f"<div class='ref-comments'>{escape(p.get('about'))}</div>"

    #             st.markdown(
    #                 f"""
    #                 <div class="ref-card">
    #                 <div class="ref-header">
    #                     <div class="ref-title">{tr("Profile details")}</div>
    #                 </div>
    #                 <div class="ref-row">{' '.join(chips) or '—'}</div>
    #                 {about_html}
    #                 </div>
    #                 """,
    #                 unsafe_allow_html=True
    #             )

    #             if b1.button(tr("Edit"), key="btn_profile_edit"):
    #                 st.session_state["profile_editing"] = True
    #                 st.rerun()

    #         else:
    #             # ✅ Actual form (🐾 Pets input removed)
    #             with st.form("profile_details_form", clear_on_submit=True):
    #                 c1, c2 = st.columns(2)
    #                 with c1:
    #                     age = st.number_input(
    #                         tr("Age"), min_value=18, max_value=100, step=1,
    #                         value=int((_prof or {}).get("age") or 18),
    #                         key="profile_age"
    #                     )
    #                     monthly_salary = st.number_input(
    #                         tr("Monthly salary (€)"), min_value=0, max_value=1_000_000, step=100,
    #                         value=int((_prof or {}).get("monthly_salary") or 0),
    #                         key="profile_salary"
    #                     )
    #                     marital_status_opts = ["Single","Married","Divorced","Widowed"]
    #                     marital_status_idx = (
    #                         marital_status_opts.index(((_prof or {}).get("marital_status") or "Single"))
    #                         if ((_prof or {}).get("marital_status") in marital_status_opts) else 0
    #                     )
    #                     marital_status = st.selectbox(
    #                         tr("Marital status"),
    #                         [tr(x) for x in marital_status_opts],
    #                         index=marital_status_idx,
    #                         key="profile_marital"
    #                     )
    #                     num_tenants = st.number_input(
    #                         tr("Number of occupants"), min_value=1, max_value=10, step=1,
    #                         value=int((_prof or {}).get("num_tenants") or 1),
    #                         key="profile_num_tenants"
    #                     )
    #                 with c2:
    #                     job_position = st.text_input(
    #                         tr("Job position"), value=(_prof or {}).get("job_position") or "",
    #                         key="profile_job_position"
    #                     )
    #                     contract_type_opts = ["Permanent","Temporary","Freelancer","Other"]
    #                     contract_type_idx = (
    #                         contract_type_opts.index(((_prof or {}).get("contract_type") or "Permanent"))
    #                         if ((_prof or {}).get("contract_type") in contract_type_opts) else 0
    #                     )
    #                     contract_type = st.selectbox(
    #                         tr("Contract type"),
    #                         [tr(x) for x in contract_type_opts],
    #                         index=contract_type_idx,
    #                         key="profile_contract"
    #                     )
    #                 about = st.text_area(
    #                     tr("A few words about yourself"),
    #                     value=(_prof or {}).get("about") or "",
    #                     key="profile_about"
    #                 )

    #                 # 🔘 Button inside the form
    #                 save_clicked = st.form_submit_button(tr("Save profile details"))

    #             if save_clicked:
    #                 marital_map = {
    #                     tr("Single"): "Single", tr("Married"): "Married",
    #                     tr("Divorced"): "Divorced", tr("Widowed"): "Widowed",
    #                 }
    #                 contract_map = {
    #                     tr("Permanent"): "Permanent", tr("Temporary"): "Temporary",
    #                     tr("Freelancer"): "Freelancer", tr("Other"): "Other",
    #                 }

    #                 # 🐾 Pets removed: keep previous value (if your save requires it)
    #                 prev_pets = (_prof or {}).get("pets")
    #                 try:
    #                     save_profile_details(
    #                         tid,
    #                         age=int(st.session_state["profile_age"]),
    #                         monthly_salary=int(st.session_state["profile_salary"]),
    #                         marital_status=marital_map.get(st.session_state["profile_marital"], "Single"),
    #                         job_position=st.session_state["profile_job_position"].strip(),
    #                         contract_type=contract_map.get(st.session_state["profile_contract"], "Permanent"),
    #                         pets=prev_pets,  # keep existing value silently
    #                         num_tenants=int(st.session_state["profile_num_tenants"]),
    #                         about=st.session_state["profile_about"].strip(),
    #                     )
    #                 except TypeError:
    #                     # If the function signature doesn't require 'pets', call without it
    #                     save_profile_details(
    #                         tid,
    #                         age=int(st.session_state["profile_age"]),
    #                         monthly_salary=int(st.session_state["profile_salary"]),
    #                         marital_status=marital_map.get(st.session_state["profile_marital"], "Single"),
    #                         job_position=st.session_state["profile_job_position"].strip(),
    #                         contract_type=contract_map.get(st.session_state["profile_contract"], "Permanent"),
    #                         num_tenants=int(st.session_state["profile_num_tenants"]),
    #                         about=st.session_state["profile_about"].strip(),
    #                     )
    #                 try: st.cache_data.clear()
    #                 except Exception: pass
    #                 st.success(tr("Changes saved."))
    #                 st.session_state["profile_editing"] = False
    #                 st.rerun()

    #     # --- Location for compact summary (pull from pickers; fallback to saved prefs)
    #     ANY = tr("Any")

    #     raw_region   = st.session_state.get("otr_region") or (prefs.get("region") or "")
    #     raw_district = st.session_state.get("otr_ru")     or (prefs.get("search_district") or "")
    #     raw_city     = st.session_state.get("otr_mun")    or (prefs.get("search_city") or "")

    #     def _clean_loc(x: str) -> str:
    #         s = (x or "").strip()
    #         return "" if s in {"", "—", ANY} else s

    #     region   = _clean_loc(raw_region)
    #     district = _clean_loc(raw_district)
    #     city     = _clean_loc(raw_city)

    #     # --- Compact summary (uses current widget values) ---------------------------
    #     def _fmt_range(lo, hi, suffix=""):
    #         has_lo = lo not in (None, 0, "0", "")
    #         has_hi = hi not in (None, 0, "0", "")
    #         if not has_lo and not has_hi:
    #             return None
    #         lo_txt = f"{int(lo):,}" if has_lo else "—"
    #         hi_txt = f"{int(hi):,}" if has_hi else "—"
    #         return f"{lo_txt}–{hi_txt}{suffix}"

    #     latest_region = region if (region and region != "—") else ""
    #     latest_district = district if (district and district != "—") else ""
    #     latest_city = city if (city and city != "—") else ""
    #     loc_txt = " — ".join([x.strip() for x in [latest_region, latest_district, latest_city] if x])

    #     size_txt  = _fmt_range(st.session_state["otr_size_min"],  st.session_state["otr_size_max"],  " m²")
    #     rooms_txt = _fmt_range(st.session_state["otr_rooms_min"], st.session_state["otr_rooms_max"], f" {tr('rooms')}")
    #     floor_txt = _fmt_range(st.session_state["otr_floor_min"], st.session_state["otr_floor_max"])
    #     price_txt = _fmt_range(st.session_state["otr_price_min"], st.session_state["otr_price_max"])

    #     bits = []
    #     if size_txt:  bits.append(size_txt)
    #     if rooms_txt: bits.append(rooms_txt)
    #     if floor_txt: bits.append(tr("Floor") + " " + floor_txt)
    #     if price_txt: bits.append("€" + price_txt.replace("–", "–€"))

    #     details_txt = " · ".join(bits)
    #     state_label = tr("Active") if st.session_state["otr_open_flag"] else tr("Inactive")

    #     if loc_txt and details_txt:
    #         st.caption(f"{tr('Status:')} {state_label} · {tr('Looking in')}: {loc_txt} · {details_txt}")
    #     elif loc_txt:
    #         st.caption(f"{tr('Status:')} {state_label} · {tr('Looking in')}: {loc_txt}")
    #     elif details_txt:
    #         st.caption(f"{tr('Status:')} {state_label} · {details_txt}")
    #     else:
    #         st.caption(f"{tr('Status:')} {state_label} · {tr('Looking in')}: {tr('Anywhere')}")


    # def tenant_open_to_rent_section():
    #     # Header + compact help
    #     c1, c2 = st.columns([6, 0.6])
    #     with c1:
    #         st.subheader(f"**{tr('Open to rent')}**")
    #     with c2:
    #         help_icon(tr("Let landlords know what you’re looking and share your criteria."), key="help_otr_header")

    #     tid = st.session_state.user["id"]
    #     prefs = load_open_to_rent_prefs(tid)

    #     # If reset asked, we force defaults (zeros/False) instead of loading prefs.
    #     force_defaults = st.session_state.pop("otr_force_defaults", False)

    #     # Initialize numeric & flag fields (once or when forced)
    #     if ("otr_keys_inited" not in st.session_state) or force_defaults:
    #         if force_defaults:
    #             # Defaults
    #             st.session_state["otr_open_flag"]  = False
    #             st.session_state["otr_size_min"]   = 0
    #             st.session_state["otr_size_max"]   = 0
    #             st.session_state["otr_rooms_min"]  = 0
    #             st.session_state["otr_rooms_max"]  = 0
    #             st.session_state["otr_floor_min"]  = 0
    #             st.session_state["otr_floor_max"]  = 0
    #             st.session_state["otr_price_min"]  = 0
    #             st.session_state["otr_price_max"]  = 0
    #         else:
    #             # From saved prefs
    #             st.session_state["otr_open_flag"]  = bool(prefs.get("open_to_rent"))
    #             st.session_state["otr_size_min"]   = int(prefs.get("size_min")  or 0)
    #             st.session_state["otr_size_max"]   = int(prefs.get("size_max")  or 0)
    #             st.session_state["otr_rooms_min"]  = int(prefs.get("rooms_min") or 0)
    #             st.session_state["otr_rooms_max"]  = int(prefs.get("rooms_max") or 0)
    #             st.session_state["otr_floor_min"]  = int(prefs.get("floor_min") or 0)
    #             st.session_state["otr_floor_max"]  = int(prefs.get("floor_max") or 0)
    #             st.session_state["otr_price_min"]  = int(prefs.get("price_min") or 0)
    #             st.session_state["otr_price_max"]  = int(prefs.get("price_max") or 0)

    #         st.session_state["otr_keys_inited"] = True

    #     # --- UI container ---------------------------------------------------------
    #     with st.container(border=True):
    #         data, regions, muni_idx = load_ellada_index("ellada.json")

    #         # If we just pressed Reset, skip preselect from saved prefs this run
    #         reset_preselect = st.session_state.pop("otr_reset_preselect", False)

    #         saved_city = "" if reset_preselect else (prefs.get("search_city") or "").strip()
    #         saved_dist = "" if reset_preselect else (prefs.get("search_district") or "").strip()

    #         # Try to infer Region/Unit from saved values
    #         pre_region, pre_unit = (None, None)
    #         if saved_city and saved_city in muni_idx:
    #             pre_region, pre_unit = muni_idx[saved_city]
    #         elif saved_dist:
    #             for reg in data.get("Περιφέρειες", []):
    #                 units = (reg.get("Περιφερειακές Ενότητες") or {})
    #                 if saved_dist in units:
    #                     pre_region = reg.get("όνομα")
    #                     pre_unit = saved_dist
    #                     break

    #         # --- Correct seeding for the 3-level location pickers -----------------
    #         prefix = "otr"
    #         ANY = tr("Any")
    #         # Seed the exact keys used by the pickers/render_tenant_filters:
    #         if reset_preselect or (f"{prefix}_region" not in st.session_state):
    #             st.session_state[f"{prefix}_region"] = pre_region or ANY
    #         if reset_preselect or (f"{prefix}_ru" not in st.session_state):
    #             st.session_state[f"{prefix}_ru"] = pre_unit or ANY
    #         if reset_preselect or (f"{prefix}_mun" not in st.session_state):
    #             st.session_state[f"{prefix}_mun"] = saved_city or ANY

    #         # --- Active / Inactive toggle (kept as-is) ----------------------------
    #         cb1, cb2 = st.columns([1, 0.08])
    #         with cb1:
    #             open_flag = st.checkbox(tr("I’m looking for a place"), key="otr_open_flag")
    #         with cb2:
    #             help_icon(
    #                 tr("Turn on to appear in landlord searches. You can hide this anytime."),
    #                 key="help_otr_toggle"
    #             )

    #         # --- Sticky expander + Form to avoid auto-reruns while editing --------
    #         st.session_state.setdefault("otr_prop_expanded", True)

    #         with st.expander(tr("Property characteristics"),
    #                          expanded=st.session_state["otr_prop_expanded"]):

    #             # ⬇️ NEW: render the 3 linked pickers OUTSIDE the form
    #             prefix = "otr"
    #             region_sel, ru_sel, mun_sel = greece_location_pickers(prefix=prefix)

    #             # Form batches widget changes; rerun only on submit
    #             with st.form("otr_prefs_form", clear_on_submit=False):
    #                 # RANGES ONLY (location already chosen above)
    #                 c1, c2 = st.columns(2)
    #                 size_min_val = c1.number_input(tr("Min size (m²)"), 0, 10000, step=5, key=f"{prefix}_size_min")
    #                 size_max_val = c2.number_input(tr("Max size (m²)"), 0, 10000, step=5, key=f"{prefix}_size_max")

    #                 r1, r2 = st.columns(2)
    #                 rooms_min_val = r1.number_input(tr("Min rooms"), 0, 50, step=1, key=f"{prefix}_rooms_min")
    #                 rooms_max_val = r2.number_input(tr("Max rooms"), 0, 50, step=1, key=f"{prefix}_rooms_max")

    #                 f1, f2 = st.columns(2)
    #                 floor_min_val = f1.number_input(tr("Min floor"), -5, 100, step=1, key=f"{prefix}_floor_min")
    #                 floor_max_val = f2.number_input(tr("Max floor"), -5, 100, step=1, key=f"{prefix}_floor_max")

    #                 p1, p2 = st.columns(2)
    #                 price_min_val = p1.number_input(tr("Min price (€)"), 0, 1_000_000, step=50, key=f"{prefix}_price_min")
    #                 price_max_val = p2.number_input(tr("Max price (€)"), 0, 1_000_000, step=50, key=f"{prefix}_price_max")

    #                 def _none_if_zero(v):
    #                     try:
    #                         return None if int(v) == 0 else int(v)
    #                     except Exception:
    #                         return None

    #                 def _norm_any(v):
    #                     if v is None:
    #                         return ""
    #                     s = str(v).strip().lower()
    #                     return "" if s in {"", "any", "—", "-", "— any —"} else str(v)

    #                 filt = {
    #                     "region":   _norm_any(st.session_state.get(f"{prefix}_region")),
    #                     "district": _norm_any(st.session_state.get(f"{prefix}_ru")),
    #                     "city":     _norm_any(st.session_state.get(f"{prefix}_mun")),
    #                     "size_min":  _none_if_zero(size_min_val),
    #                     "size_max":  _none_if_zero(size_max_val),
    #                     "rooms_min": _none_if_zero(rooms_min_val),
    #                     "rooms_max": _none_if_zero(rooms_max_val),
    #                     "floor_min": (None if floor_min_val == 0 else floor_min_val),
    #                     "floor_max": (None if floor_max_val == 0 else floor_max_val),
    #                     "price_min": _none_if_zero(price_min_val),
    #                     "price_max": _none_if_zero(price_max_val),
    #                 }

    #                 col_save, col_reset = st.columns([1, 1])
    #                 save_clicked  = col_save.form_submit_button(tr("Save preferences"))
    #                 reset_clicked = col_reset.form_submit_button(tr("Reset"))

    #             def _i(x):
    #                 """None -> 0, else int"""
    #                 return 0 if x is None else int(x)

    #             # --- Handle actions after the form (runs only when submitted) -----
    #             if save_clicked:
    #                 region_clean   = (filt.get("region")   or "").strip()
    #                 city_clean     = (filt.get("city")     or "").strip()
    #                 district_clean = (filt.get("district") or "").strip()

    #                 if not city_clean and not district_clean:
    #                     st.warning(tr("Enter at least a city or a district."))
    #                 else:
    #                     try:
    #                         save_open_to_rent_prefs(
    #                             tid, bool(st.session_state["otr_open_flag"]),
    #                             city_clean, district_clean,
    #                             _i(filt.get("size_min")),  _i(filt.get("size_max")),
    #                             _i(filt.get("rooms_min")), _i(filt.get("rooms_max")),
    #                             _i(filt.get("floor_min")), _i(filt.get("floor_max")),
    #                             _i(filt.get("price_min")), _i(filt.get("price_max")),
    #                             city_osm_id=None, city_osm_type=None,
    #                             district_osm_id=None, district_osm_type=None,
    #                             region=region_clean,
    #                         )
    #                     except TypeError:
    #                         # Fallback for older function signature without OSM/region args
    #                         save_open_to_rent_prefs(
    #                             tid, bool(st.session_state["otr_open_flag"]),
    #                             city_clean, district_clean,
    #                             _i(filt.get("size_min")),  _i(filt.get("size_max")),
    #                             _i(filt.get("rooms_min")), _i(filt.get("rooms_max")),
    #                             _i(filt.get("floor_min")), _i(filt.get("floor_max")),
    #                             _i(filt.get("price_min")), _i(filt.get("price_max")),
    #                         )
    #                     try:
    #                         st.cache_data.clear()
    #                     except Exception:
    #                         pass
    #                     st.success(tr("Preferences saved."))
    #                     st.session_state["otr_prop_expanded"] = True  # keep it open on the next run

    #             if reset_clicked:
    #                 # Clear the exact keys used by pickers and numeric fields
    #                 for k in (
    #                     f"{prefix}_region", f"{prefix}_ru", f"{prefix}_mun",
    #                     f"{prefix}_size_min", f"{prefix}_size_max",
    #                     f"{prefix}_rooms_min", f"{prefix}_rooms_max",
    #                     f"{prefix}_floor_min", f"{prefix}_floor_max",
    #                     f"{prefix}_price_min", f"{prefix}_price_max",
    #                     "otr_open_flag", "otr_keys_inited"
    #                 ):
    #                     st.session_state.pop(k, None)

    #                 st.session_state["otr_force_defaults"]  = True
    #                 st.session_state["otr_reset_preselect"] = True
    #                 st.session_state["otr_prop_expanded"]   = True  # keep open after reset
    #                 st.rerun()

    #     # --- Profile details (own Edit/Save flow) -------------------------------------
    #     tid = st.session_state.user["id"]
    #     _prof = load_profile_details(tid)

    #     # one-time default for edit mode
    #     if "profile_editing" not in st.session_state:
    #         st.session_state["profile_editing"] = False

    #     _ensure_pt_css()

    #     with st.expander(tr("Profile details"), expanded=False):
    #         # Header row with Edit / Save / Cancel
    #         b1, _ = st.columns([3, 9])

    #         if not st.session_state["profile_editing"]:
    #             # Read-only summary chips
    #             p = _prof or {}
    #             def _val(x, dash="—"): return (str(x).strip() if (x not in (None, "", 0)) else dash)
    #             _pets = tr("Yes") if p.get("pets") in (1, True) else tr("No") if p.get("pets") in (0, False) else "—"
    #             chips = []
    #             if p.get("age"):              chips.append(f'<span class="pill">{tr("Age")}: {int(p["age"])}</span>')
    #             if p.get("marital_status"):   chips.append(f'<span class="pill">{tr("Marital status")}: {p["marital_status"]}</span>')
    #             if p.get("contract_type"):    chips.append(f'<span class="pill">{tr("Contract type")}: {p["contract_type"]}</span>')
    #             if p.get("monthly_salary") is not None:
    #                 chips.append(f'<span class="pill">{tr("Monthly salary (€)")}: {int(p["monthly_salary"]):,}</span>')
    #             chips.append(f'<span class="pill">{tr("Pets")}: {_pets}</span>')
    #             if p.get("num_tenants"):      chips.append(f'<span class="pill">{tr("Number of occupants")}: {int(p["num_tenants"])}</span>')

    #             about_html = ""
    #             if _val(p.get("about"), None):
    #                 from html import escape
    #                 about_html = f"<div class='ref-comments'>{escape(p.get('about'))}</div>"

    #             st.markdown(
    #                 f"""
    #                 <div class="ref-card">
    #                 <div class="ref-header">
    #                     <div class="ref-title">{tr("Profile details")}</div>
    #                 </div>
    #                 <div class="ref-row">{' '.join(chips) or '—'}</div>
    #                 {about_html}
    #                 </div>
    #                 """,
    #                 unsafe_allow_html=True
    #             )

    #             if b1.button(tr("Edit"), key="btn_profile_edit"):
    #                 st.session_state["profile_editing"] = True
    #                 st.rerun()

    #         else:
    #             # ✅ Actual form (submit button MUST be inside this context)
    #             with st.form("profile_details_form", clear_on_submit=True):
    #                 c1, c2 = st.columns(2)
    #                 with c1:
    #                     age = st.number_input(
    #                         tr("Age"), min_value=18, max_value=100, step=1,
    #                         value=int((_prof or {}).get("age") or 18),
    #                         key="profile_age"
    #                     )
    #                     monthly_salary = st.number_input(
    #                         tr("Monthly salary (€)"), min_value=0, max_value=1_000_000, step=100,
    #                         value=int((_prof or {}).get("monthly_salary") or 0),
    #                         key="profile_salary"
    #                     )
    #                     marital_status_opts = ["Single","Married","Divorced","Widowed"]
    #                     marital_status_idx = (
    #                         marital_status_opts.index(((_prof or {}).get("marital_status") or "Single"))
    #                         if ((_prof or {}).get("marital_status") in marital_status_opts) else 0
    #                     )
    #                     marital_status = st.selectbox(
    #                         tr("Marital status"),
    #                         [tr(x) for x in marital_status_opts],
    #                         index=marital_status_idx,
    #                         key="profile_marital"
    #                     )
    #                     pets = st.radio(
    #                         tr("Pets"), [tr("Yes"), tr("No")], horizontal=True,
    #                         index=(0 if ((_prof or {}).get("pets") in (1, True)) else 1),
    #                         key="profile_pets"
    #                     )
    #                     num_tenants = st.number_input(
    #                         tr("Number of occupants"), min_value=1, max_value=10, step=1,
    #                         value=int((_prof or {}).get("num_tenants") or 1),
    #                         key="profile_num_tenants"
    #                     )
    #                 with c2:
    #                     job_position = st.text_input(
    #                         tr("Job position"), value=(_prof or {}).get("job_position") or "",
    #                         key="profile_job_position"
    #                     )
    #                     contract_type_opts = ["Permanent","Temporary","Freelancer","Other"]
    #                     contract_type_idx = (
    #                         contract_type_opts.index(((_prof or {}).get("contract_type") or "Permanent"))
    #                         if ((_prof or {}).get("contract_type") in contract_type_opts) else 0
    #                     )
    #                     contract_type = st.selectbox(
    #                         tr("Contract type"),
    #                         [tr(x) for x in contract_type_opts],
    #                         index=contract_type_idx,
    #                         key="profile_contract"
    #                     )
    #                 about = st.text_area(
    #                     tr("A few words about yourself"),
    #                     value=(_prof or {}).get("about") or "",
    #                     key="profile_about"
    #                 )

    #                 # 🔘 This is the button Streamlit needs INSIDE the form
    #                 save_clicked = st.form_submit_button(tr("Save profile details"))

    #             if save_clicked:
    #                 marital_map = {
    #                     tr("Single"): "Single", tr("Married"): "Married",
    #                     tr("Divorced"): "Divorced", tr("Widowed"): "Widowed",
    #                 }
    #                 contract_map = {
    #                     tr("Permanent"): "Permanent", tr("Temporary"): "Temporary",
    #                     tr("Freelancer"): "Freelancer", tr("Other"): "Other",
    #                 }

    #                 save_profile_details(
    #                     tid,
    #                     age=int(st.session_state["profile_age"]),
    #                     monthly_salary=int(st.session_state["profile_salary"]),
    #                     marital_status=marital_map.get(st.session_state["profile_marital"], "Single"),
    #                     job_position=st.session_state["profile_job_position"].strip(),
    #                     contract_type=contract_map.get(st.session_state["profile_contract"], "Permanent"),
    #                     pets=(1 if st.session_state["profile_pets"] == tr("Yes") else 0),
    #                     num_tenants=int(st.session_state["profile_num_tenants"]),
    #                     about=st.session_state["profile_about"].strip(),
    #                 )
    #                 try: st.cache_data.clear()
    #                 except Exception: pass
    #                 st.success(tr("Changes saved."))
    #                 st.session_state["profile_editing"] = False
    #                 st.rerun()

    #     # --- Location for compact summary (pull from pickers; fallback to saved prefs)
    #     ANY = tr("Any")

    #     raw_region   = st.session_state.get("otr_region") or (prefs.get("region") or "")
    #     raw_district = st.session_state.get("otr_ru")     or (prefs.get("search_district") or "")
    #     raw_city     = st.session_state.get("otr_mun")    or (prefs.get("search_city") or "")

    #     def _clean_loc(x: str) -> str:
    #         s = (x or "").strip()
    #         return "" if s in {"", "—", ANY} else s

    #     region   = _clean_loc(raw_region)
    #     district = _clean_loc(raw_district)
    #     city     = _clean_loc(raw_city)

    #     # --- Compact summary (uses current widget values) ---------------------------
    #     def _fmt_range(lo, hi, suffix=""):
    #         has_lo = lo not in (None, 0, "0", "")
    #         has_hi = hi not in (None, 0, "0", "")
    #         if not has_lo and not has_hi:
    #             return None
    #         lo_txt = f"{int(lo):,}" if has_lo else "—"
    #         hi_txt = f"{int(hi):,}" if has_hi else "—"
    #         return f"{lo_txt}–{hi_txt}{suffix}"

    #     latest_region = region if (region and region != "—") else ""
    #     latest_district = district if (district and district != "—") else ""
    #     latest_city = city if (city and city != "—") else ""
    #     loc_txt = " — ".join([x.strip() for x in [latest_region, latest_district, latest_city] if x])

    #     size_txt  = _fmt_range(st.session_state["otr_size_min"],  st.session_state["otr_size_max"],  " m²")
    #     rooms_txt = _fmt_range(st.session_state["otr_rooms_min"], st.session_state["otr_rooms_max"], f" {tr('rooms')}")
    #     floor_txt = _fmt_range(st.session_state["otr_floor_min"], st.session_state["otr_floor_max"])
    #     price_txt = _fmt_range(st.session_state["otr_price_min"], st.session_state["otr_price_max"])

    #     bits = []
    #     if size_txt:  bits.append(size_txt)
    #     if rooms_txt: bits.append(rooms_txt)
    #     if floor_txt: bits.append(tr("Floor") + " " + floor_txt)
    #     if price_txt: bits.append("€" + price_txt.replace("–", "–€"))

    #     details_txt = " · ".join(bits)
    #     state_label = tr("Active") if st.session_state["otr_open_flag"] else tr("Inactive")

    #     if loc_txt and details_txt:
    #         st.caption(f"{tr('Status:')} {state_label} · {tr('Looking in')}: {loc_txt} · {details_txt}")
    #     elif loc_txt:
    #         st.caption(f"{tr('Status:')} {state_label} · {tr('Looking in')}: {loc_txt}")
    #     elif details_txt:
    #         st.caption(f"{tr('Status:')} {state_label} · {details_txt}")
    #     else:
    #         st.caption(f"{tr('Status:')} {state_label} · {tr('Looking in')}: {tr('Anywhere')}")
            
    #===========SEARCH PROPERTIES=================================================================
    
    #===========SEARCH PROPERTIES=================================================================

    # from html import escape  # <-- you were using escape() below; import it once.
    def search_properties():
        me = st.session_state.user
        me_id = int(me["id"])

        st.subheader(tr("Browse properties"))

        # --- Base filters (exactly like Find Tenants) -----------------------------
        # Renders location pickers + size/rooms/floor/price ranges
        try:
            base = render_tenant_filters(prefix="browse")  # stores values in session; returns nothing in your version
        except Exception as e:
            st.warning(f"{tr('Could not render base filters')}: {e}")

        # Pull normalized values from session_state (same keys as Find Tenants)
        ss = st.session_state
        region   = (ss.get("browse_region") or "").strip()
        district = (ss.get("browse_regional_unit") or ss.get("browse_district") or "").strip()
        city     = (ss.get("browse_municipality") or ss.get("browse_city") or "").strip()

        size_min  = ss.get("browse_size_min") or 0
        size_max  = ss.get("browse_size_max") or 0
        rooms_min = ss.get("browse_rooms_min") or 0
        rooms_max = ss.get("browse_rooms_max") or 0
        floor_min = ss.get("browse_floor_min") or 0
        floor_max = ss.get("browse_floor_max") or 0
        price_min = ss.get("browse_price_min") or 0
        price_max = ss.get("browse_price_max") or 0

        # --- Dynamic OTR characteristics (same helper as Find Tenants) -----------
        try:
            dyn_filters = render_o2r_extra_filters(prefix="browse")
        except Exception:
            dyn_filters = {}

        # --- Build SQL exactly the same way --------------------------------------
        c = get_conn()
        clauses, vals = ["visible_to_tenants=1"], []

        # Location (case-insensitive exact-ish; use LIKE to allow partials)
        if region:
            clauses.append("LOWER(COALESCE(region,'')) LIKE ?");   vals.append(f"%{region.lower()}%")
        if district:
            clauses.append("LOWER(COALESCE(district,'')) LIKE ?"); vals.append(f"%{district.lower()}%")
        if city:
            clauses.append("LOWER(COALESCE(city,'')) LIKE ?");     vals.append(f"%{city.lower()}%")

        # Ranges (mirrors the Find Tenants range logic but applied to property columns)
        if size_min:  clauses.append("COALESCE(size_m2, 0) >= ?");  vals.append(int(size_min))
        if size_max:  clauses.append("COALESCE(size_m2, 999999) <= ?"); vals.append(int(size_max))
        if rooms_min: clauses.append("COALESCE(rooms, 0) >= ?");    vals.append(int(rooms_min))
        if rooms_max: clauses.append("COALESCE(rooms, 999) <= ?");  vals.append(int(rooms_max))
        if floor_min: clauses.append("COALESCE(floor, -999) >= ?"); vals.append(int(floor_min))
        if floor_max: clauses.append("COALESCE(floor,  999) <= ?"); vals.append(int(floor_max))
        if price_min: clauses.append("COALESCE(price, 0) >= ?");    vals.append(int(price_min))
        if price_max: clauses.append("COALESCE(price, 999999999) <= ?"); vals.append(int(price_max))

        # Dynamic WHEREs from PROPERTY_FIELDS (same path you already use)
        try:
            extra_clauses, extra_params = o2r_sql_clauses_for_fields(dyn_filters)
            if extra_clauses: clauses.extend(extra_clauses)
            if extra_params:  vals.extend(extra_params)
        except Exception:
            pass  # keep base search working even if extras fail

        where_sql = " AND ".join(clauses)

        # --- Dynamic SELECT list so cards can display extra fields ----------------
        try:
            active_dyn_cols = [f["column"] for f in PROPERTY_FIELDS if f.get("active", True)]
        except Exception:
            active_dyn_cols = []
        dyn_select_sql = (", " + ", ".join(active_dyn_cols)) if active_dyn_cols else ""

        rows = c.execute(f"""
            SELECT id, landlord_id, address, listing_url, region, district, city,
                size_m2, rooms, floor, price, updated_at
                {dyn_select_sql}
            FROM landlord_properties
            WHERE {where_sql}
            ORDER BY updated_at DESC, id DESC
            LIMIT 200
        """, tuple(vals)).fetchall()

        # Convert to dicts (include dynamic columns)
        rows_dict = []
        for r in rows:
            it = {
                "id": r["id"],
                "landlord_id": r["landlord_id"],
                "address": r["address"],
                "listing_url": _norm_url(r["listing_url"]),
                "region": r["region"],
                "district": r["district"],
                "city": r["city"],
                "size_m2": r["size_m2"],
                "rooms": r["rooms"],
                "floor": r["floor"],
                "price": r["price"],
                "updated_at": r["updated_at"],
            }
            for col in active_dyn_cols:
                try:
                    it[col] = r[col]
                except Exception:
                    it[col] = None
            rows_dict.append(it)

        if not rows_dict:
            st.info(tr("No properties found with these filters."))
            return

        # --- Order & scoring (unchanged) -----------------------------------------
        order_by = st.radio(tr("Order by"), [tr("Best fit"), tr("Most recent")], horizontal=True)

        ref_info  = _tenant_reference_summary(me_id)
        has_ref   = (ref_info.get("completed", 0) > 0)
        has_docs  = (_tenant_verified_docs_count(me_id) > 0)

        for it in rows_dict:
            it["thumb_bytes"] = _get_listing_thumbnail(it["listing_url"]) if it["listing_url"] else None
            it["fit_score"], it["fit_reasons"] = _compute_property_fit(it, me_id)

        if order_by == tr("Best fit"):
            rows_dict.sort(key=lambda x: (-x["fit_score"], x["price"] or 10**9))

        # --- CSS & Cards (unchanged) ---------------------------------------------
        try:
            _ensure_tfl_css()
        except Exception:
            pass

        for it in rows_dict:
            chips = property_chips_from_row(it)
            with st.container(border=True):
                c1, c2 = st.columns([7, 5])
                with c1:
                    st.markdown(f"**{it['address'] or tr('Property')}**  "
                                + (" · " + " ".join(chips) if chips else ""),
                                unsafe_allow_html=True)
                    if it["listing_url"]:
                        st.caption(_og_title(it["listing_url"]) or it["listing_url"])
                    # Fit badges for tenant
                    pills = []
                    if has_ref:  pills.append(tr("Reference verified"))
                    if has_docs: pills.append(tr("Docs verified"))
                    if pills:
                        st.write(" · ".join(f"🪪 {p}" for p in pills))
                with c2:
                    if it["thumb_bytes"]:
                        st.image(it["thumb_bytes"], use_container_width=True)
                # Actions row (e.g., express interest) stays as you had it
                _tenant_property_actions(it["id"], me_id)


    # def search_properties():
    #     me = st.session_state.user
    #     me_id = int(me["id"])

    #     st.subheader(tr("Browse properties"))

    #     # --- Filters (static) ---
    #     c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
    #     with c1: region    = st.text_input(tr("Region")).strip()
    #     with c2: district  = st.text_input(tr("District")).strip()
    #     with c3: city      = st.text_input(tr("City")).strip()
    #     with c4: min_rooms = st.number_input(tr("Min rooms"), 0, 20, 0, step=1)
    #     with c5: max_price = st.number_input(tr("Max price (€)"), 0, 1_000_000, 0, step=50)

    #     # --- Filters (dynamic, optional) ---
    #     # If you have the dynamic registry + widgets, this will render any extra fields (bathrooms, furnished, years, etc.)
    #     try:
    #         dyn_filters = render_o2r_extra_filters(prefix="browse")
    #     except Exception:
    #         dyn_filters = {}

    #     # --- Build SQL ---
    #     c = get_conn()
    #     clauses, vals = ["visible_to_tenants=1"], []
    #     if region:
    #         clauses.append("LOWER(COALESCE(region,'')) LIKE ?");   vals.append(f"%{region.lower()}%")
    #     if district:
    #         clauses.append("LOWER(COALESCE(district,'')) LIKE ?"); vals.append(f"%{district.lower()}%")
    #     if city:
    #         clauses.append("LOWER(COALESCE(city,'')) LIKE ?");     vals.append(f"%{city.lower()}%")
    #     if min_rooms:
    #         clauses.append("COALESCE(rooms,0) >= ?");               vals.append(int(min_rooms))
    #     if max_price:
    #         clauses.append("COALESCE(price,0) <= ?");               vals.append(int(max_price))

    #     # Inject dynamic WHERE clauses built from PROPERTY_FIELDS (if available)
    #     try:
    #         extra_clauses, extra_params = o2r_sql_clauses_for_fields(dyn_filters)
    #         if extra_clauses: clauses.extend(extra_clauses)
    #         if extra_params:  vals.extend(extra_params)
    #     except Exception:
    #         pass  # keep base search working even if extras fail

    #     where_sql = " AND ".join(clauses)

    #     # --- Dynamic SELECT list (pull all active dynamic columns so cards can show them) ---
    #     try:
    #         active_dyn_cols = [f["column"] for f in PROPERTY_FIELDS if f.get("active", True)]
    #     except Exception:
    #         active_dyn_cols = []
    #     dyn_select_sql = (", " + ", ".join(active_dyn_cols)) if active_dyn_cols else ""

    #     rows = c.execute(f"""
    #         SELECT id, landlord_id, address, listing_url, region, district, city,
    #             size_m2, rooms, floor, price, updated_at
    #             {dyn_select_sql}
    #         FROM landlord_properties
    #         WHERE {where_sql}
    #         ORDER BY updated_at DESC, id DESC
    #         LIMIT 200
    #     """, tuple(vals)).fetchall()

    #     # Convert to dicts (include dynamic columns)
    #     rows_dict = []
    #     for r in rows:
    #         it = {
    #             "id": r["id"],
    #             "landlord_id": r["landlord_id"],
    #             "address": r["address"],
    #             "listing_url": _norm_url(r["listing_url"]),
    #             "region": r["region"],
    #             "district": r["district"],
    #             "city": r["city"],
    #             "size_m2": r["size_m2"],
    #             "rooms": r["rooms"],
    #             "floor": r["floor"],
    #             "price": r["price"],
    #             "updated_at": r["updated_at"],
    #         }
    #         # attach dynamic fields if any
    #         for col in active_dyn_cols:
    #             try:
    #                 it[col] = r[col]
    #             except Exception:
    #                 it[col] = None
    #         rows_dict.append(it)

    #     if not rows_dict:
    #         st.info(tr("No properties found with these filters."))
    #         return

    #     # Order preference
    #     order_by = st.radio(tr("Order by"), [tr("Best fit"), tr("Most recent")], horizontal=True)

    #     # Precompute tenant-strength (used as pills)
    #     ref_info  = _tenant_reference_summary(me_id)
    #     has_ref   = (ref_info.get("completed", 0) > 0)
    #     has_docs  = (_tenant_verified_docs_count(me_id) > 0)

    #     # Precompute Fit + thumbnail BYTES (robust)
    #     for it in rows_dict:
    #         it["thumb_bytes"] = _get_listing_thumbnail(it["listing_url"]) if it["listing_url"] else None
    #         it["fit_score"], it["fit_reasons"] = _compute_property_fit(it, me_id)

    #     if order_by == tr("Best fit"):
    #         rows_dict.sort(key=lambda x: (-x["fit_score"], x["price"] or 10**9))
    #     else:
    #         # keep SQL ordering by updated_at DESC
    #         pass

    #     # --- CSS (safe to call repeatedly) ---
    #     try:
    #         _ensure_tfl_css()
    #     except Exception:
    #         pass
    #     st.markdown("""
    #     <style>
    #     .pill{display:inline-block;padding:2px 8px;border-radius:999px;background:#f1f5f9;color:#334155;
    #         font-size:.8rem;margin-right:6px;margin-bottom:4px;border:1px solid #e2e8f0}
    #     .pill-ok{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}
    #     .prop-card{border:1px solid #e5e7eb;border-radius:12px;padding:10px 12px;margin-bottom:10px;background:#fff;position:relative}
    #     .prop-title{font-weight:600;margin-bottom:2px}
    #     .prop-sub{color:#475569;font-size:.9rem;margin:4px 0 6px}
    #     .prop-foot{color:#64748b;font-size:.85rem}
    #     .divider{height:1px;background:#f0f0f0;margin:8px 0 6px}
    #     </style>
    #     """, unsafe_allow_html=True)

    #     # --- Precompute interested property ids (tenant) ---
    #     try:
    #         interested_pids = set(list_interested_properties_for_tenant(me_id) or [])
    #     except Exception:
    #         interested_pids = set()

    #     # --- Cache contacts once (emails) for FLC actions ---
    #     try:
    #         rows_contacts = list_future_landlord_contacts(me_id) or []
    #         contact_emails = {(r[1] or "").strip().lower() for r in rows_contacts}
    #     except Exception:
    #         contact_emails = set()

    #     # --- Results ---
    #     for it in rows_dict:
    #         pid   = it["id"]
    #         addr  = it["address"]
    #         url   = it["listing_url"]
    #         reg   = it["region"]
    #         dis   = it["district"]
    #         cit   = it["city"]
    #         size  = it["size_m2"]
    #         rooms = it["rooms"]
    #         floor = it["floor"]
    #         price = it["price"]
    #         upd   = it["updated_at"]
    #         fit_score   = it["fit_score"]
    #         fit_reasons = it["fit_reasons"]
    #         thumb       = it["thumb_bytes"]  # bytes, not URL

    #         where = " — ".join([x for x in [reg, dis, cit] if x])

    #         # Chips (location + specs + price)
    #         chips = []
    #         if where:                 chips.append(f'<span class="pill">{escape(where)}</span>')
    #         if size:                  chips.append(f'<span class="pill">{int(size):,} m²</span>')
    #         if rooms:                 chips.append(f'<span class="pill">{int(rooms)} {tr("rooms")}</span>')
    #         if floor not in (None,0): chips.append(f'<span class="pill">{tr("Floor")} {int(floor)}</span>')
    #         if price:                 chips.append(f'<span class="pill">€{int(price):,}</span>')
    #         # Tenant strength pills
    #         chips.append(f"<span class='pill {'pill-ok' if has_ref else ''}'>Ref: {'Yes' if has_ref else 'No'}</span>")
    #         if has_docs:
    #             chips.append(f"<span class='pill pill-ok'>{tr('Verified')}</span>")

    #         # === 4) EXTRA CHIPS (dynamic characteristics) ===
    #         try:
    #             if 'property_extra_chips' in globals():
    #                 chips.extend(property_extra_chips(it))
    #             else:
    #                 extras = []
    #                 if (it.get("bathrooms") not in (None, 0)): extras.append(f'{int(it["bathrooms"])} {tr("bathrooms")}')
    #                 if it.get("year_built"):                  extras.append(f'{tr("Built")} {int(it["year_built"])}')
    #                 if it.get("year_renovated"):              extras.append(f'{tr("Renovated")} {int(it["year_renovated"])}')
    #                 if it.get("furnished") is not None:       extras.append(tr("Furnished") if it["furnished"] else tr("Unfurnished"))
    #                 for label in extras:
    #                     chips.append(f'<span class="pill">{escape(label)}</span>')
    #         except Exception:
    #             pass
    #         # === /EXTRA CHIPS ===

    #         chips_html = " ".join(chips)

    #         # Link domain
    #         try:
    #             domain = url.split('://', 1)[-1].split('/', 1)[0] if url else None
    #         except Exception:
    #             domain = url
    #         link_html = f' 🔗 <a href="{escape(url)}">{escape(domain) if domain else tr("Open listing")}</a>' if url else ""

    #         # Interested pill
    #         already_interested = pid in interested_pids

    #         # Layout
    #         with st.container(border=True):
    #             hdr_left, hdr_right = st.columns([10, 1], vertical_alignment="center")
    #             with hdr_left:
    #                 safe_addr = escape(addr or (str(cit) if cit else tr("Property")))
    #                 parts = []
    #                 if already_interested:
    #                     parts.append(f'<span class="tfl-badge tfl-badge--ok">{escape(tr("Interested"))}</span>')
    #                 parts.append(f"<strong>{safe_addr}</strong>")
    #                 st.markdown(" ".join(parts), unsafe_allow_html=True)

    #             with hdr_right:
    #                 with st.popover("⋯", use_container_width=False):
    #                     with st.expander(tr("Why this fit?")):
    #                         st.write(" · ".join(fit_reasons))
    #                     if already_interested:
    #                         if st.button(tr("Cancel interest"), key=f"pi_cancel:{pid}"):
    #                             linked_users = list_users_linked_to_property(pid)
    #                             for owner_id in linked_users:
    #                                 u = get_user_by_id(owner_id) or {}
    #                                 em = (u.get("email") or "").strip().lower()
    #                                 if em:
    #                                     try:
    #                                         flc_cancel_invite(me_id, em)
    #                                     except Exception:
    #                                         pass
    #                             _remove_interest_for_property(me_id, pid)
    #                             try:
    #                                 st.cache_data.clear()
    #                             except Exception:
    #                                 pass
    #                             st.success(tr("Interest cancelled"))
    #                             st.rerun()

    #             L, R = st.columns([3, 9], vertical_alignment="top")

    #             with L:
    #                 if thumb:
    #                     st.image(thumb, use_column_width=True)
    #                 else:
    #                     st.markdown(
    #                         '<div style="width:100%;aspect-ratio:4/3;background:#eef1f4;border:1px solid #dde3ea;'
    #                         'border-radius:8px;display:flex;align-items:center;justify-content:center;">'
    #                         '<span style="opacity:.6;">No photo</span>'
    #                         '</div>',
    #                         unsafe_allow_html=True
    #                     )

    #             with R:
    #                 st.markdown(
    #                     "<div class='pill' style='background:#eefbf2;border:1px solid #b8e6c5;'>"
    #                     f"Fit: {fit_score}%</div>",
    #                     unsafe_allow_html=True
    #                 )
    #                 st.progress(max(0.0, min(1.0, (fit_score or 0)/100.0)))

    #                 st.markdown(f'<div class="prop-sub">{chips_html}</div>', unsafe_allow_html=True)
    #                 st.markdown(f'<div class="prop-foot">{tr("Updated")}: {format_dt(upd)}</div>', unsafe_allow_html=True)

    #                 # Multiple links support
    #                 extra_links = []
    #                 urls_raw = (url or "").replace(";", ",").split(",")
    #                 urls_clean = [u.strip() for u in urls_raw if u.strip()]
    #                 if len(urls_clean) > 1:
    #                     for u in urls_clean:
    #                         try:
    #                             domain = u.split("://", 1)[-1].split("/", 1)[0]
    #                         except Exception:
    #                             domain = u
    #                         extra_links.append(f'🔗 <a href="{escape(u)}" target="_blank" rel="noopener noreferrer">{escape(domain)}</a>')
    #                     links_html = " · ".join(extra_links)
    #                     st.markdown(f'<div class="prop-foot">{tr("For more details")}: {links_html}</div>', unsafe_allow_html=True)
    #                 elif urls_clean:
    #                     try:
    #                         domain = urls_clean[0].split("://", 1)[-1].split("/", 1)[0]
    #                     except Exception:
    #                         domain = urls_clean[0]
    #                     st.markdown(
    #                         f'<div class="prop-foot">{tr("For more details")}: '
    #                         f'🔗 <a href="{escape(urls_clean[0])}" target="_blank" rel="noopener noreferrer">{escape(domain)}</a></div>',
    #                         unsafe_allow_html=True,
    #                     )
    #                 else:
    #                     st.markdown(f'<div class="prop-foot">{tr("For more details")}: {tr("No links available")}</div>', unsafe_allow_html=True)




    
    #             # ---- Interest micro-flow under the card (left column area) ----
    #             # ---- Interest micro-flow under the card (left column area) ----

    #             st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    #             if not already_interested:
    #                 with st.popover(tr("I’m interested"), use_container_width=True):

    #                     from html import escape as _esc  # ensure we have an escaper

    #                     st.caption(tr("Contacts for this property"))
    #                     uploaders = list_property_uploaders(pid)  # [(name, email, display_role)]
    #                     selected_key = f"selected_contacts_{pid}"
    #                     if selected_key not in st.session_state:
    #                         st.session_state[selected_key] = []

    #                     if not uploaders:
    #                         st.write(tr("No landlords/agents linked"))
    #                     else:
    #                         multiple = len(uploaders) > 1

    #                         # Keep session selections in sync with current list of uploaders (if list changed)
    #                         if multiple and st.session_state[selected_key]:
    #                             present = {em for _, em, _ in uploaders}
    #                             st.session_state[selected_key] = [
    #                                 em for em in st.session_state[selected_key] if em in present
    #                             ]

    #                         for idx_u, (up_name, up_email, link_role) in enumerate(uploaders):
    #                             role_norm    = (link_role or "").strip().lower()
    #                             display_role = "agent" if role_norm == "agent" else "landlord"
    #                             icon = role_icon(display_role) or ""
    #                             disp = (up_name or "").strip() or (up_email or "").split("@")[0] or tr("Unknown")
    #                             initials = _initials(disp, up_email) if '_initials' in globals() else (disp[:2] or "?").upper()
    #                             role_pill = tr("Landlord") if display_role == "landlord" else tr("Agent")

    #                             cA, cB, cC = st.columns([1, 6, 1])

    #                             with cA:
    #                                 st.markdown(f'<div class="tfl-avatar">{_esc(initials)}</div>', unsafe_allow_html=True)

    #                             with cB:
    #                                 st.markdown(
    #                                     (
    #                                         f'<div class="tfl-name">{_esc(icon)} {_esc(disp)} '
    #                                         f'<span class="pill">{_esc(role_pill)}</span></div>'
    #                                         f'<div class="tfl-email"><a href="mailto:{_esc(up_email or "")}">{_esc(up_email or "")}</a></div>'
    #                                     ),
    #                                     unsafe_allow_html=True
    #                                 )
    #                                 # Status label (optional)
    #                                 try:
    #                                     urow = get_user_by_email(up_email) or {}
    #                                     other_id = int(urow.get("id") or 0)
    #                                 except Exception:
    #                                     other_id = 0
    #                                 if other_id:
    #                                     rel = (flc_relation_status(other_id, me_id, landlord_email=up_email) or "disconnected").lower()
    #                                     if rel == "connected":
    #                                         st.markdown(f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
    #                                     elif rel.startswith("pending"):
    #                                         st.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
    #                                 else:
    #                                     st.caption(tr("User record not found"))

    #                             with cC:
    #                                 if multiple:
    #                                     checked = st.checkbox(
    #                                         "",
    #                                         key=f"select_contact_{pid}_{idx_u}",
    #                                         help=tr("Select to send interest to this contact"),
    #                                         value=(up_email in st.session_state[selected_key]),
    #                                     )
    #                                     # keep session selections in sync
    #                                     if checked and up_email not in st.session_state[selected_key]:
    #                                         st.session_state[selected_key].append(up_email)
    #                                     if not checked and up_email in st.session_state[selected_key]:
    #                                         st.session_state[selected_key].remove(up_email)

    #                     st.caption(tr("Optional note to the owner/agent"))
    #                     note = st.text_area(
    #                         tr("Message"),
    #                         key=f"pi_note:{pid}",
    #                         height=90,
    #                         placeholder=tr("e.g., Hi! I’d like to view this place. Tue after 18:00 works for me."),
    #                     )
    #                     chips = st.multiselect(
    #                         tr("Availability"),
    #                         options=[tr("Today"), tr("Weekdays after 18:00"), tr("Weekend mornings")],
    #                         key=f"pi_avail:{pid}",
    #                     )

    #                     if st.button(tr("Send interest"), key=f"pi_send:{pid}", use_container_width=True):
    #                         final_note = note.strip()
    #                         if chips:
    #                             final_note = (final_note + ("\n\n" if final_note else "")) + tr("Availability") + ": " + ", ".join(chips)
    #                         # Always append profile highlights
    #                         final_note = (final_note + ("\n\n" if final_note else "")) + tr("Includes profile highlights")

    #                         # Decide recipients
    #                         selected_emails = st.session_state.get(selected_key, [])
    #                         contact_param = None
    #                         if uploaders and len(uploaders) > 1:
    #                             if not selected_emails:
    #                                 st.warning(tr("Please select at least one contact."))
    #                                 st.stop()
    #                             contact_param = selected_emails  # send only to chosen contacts

    #                         try:
    #                             # Call helper (newer signature with contact_emails if available)
    #                             try:
    #                                 touched = _send_interest_like_connect_for_property(
    #                                     tenant_id=me_id,
    #                                     property_id=pid,
    #                                     note_text=final_note or None,
    #                                     contact_emails=contact_param,
    #                                 )
    #                             except TypeError:
    #                                 # Fallback: older signature without contact_emails
    #                                 touched = _send_interest_like_connect_for_property(
    #                                     tenant_id=me_id,
    #                                     property_id=pid,
    #                                     note_text=final_note or None,
    #                                 )

    #                             # ---- NEW: set per-property interest status for each recipient ----
    #                             # Determine whom we actually notified
    #                             recipient_emails = contact_param if contact_param else [em for _, em, _ in uploaders]
    #                             # Map emails -> user IDs and set status
    #                             set_count = 0
    #                             for em in recipient_emails:
    #                                 try:
    #                                     row = get_user_by_email(em) or {}
    #                                     ll_id = int(row.get("id") or 0)
    #                                 except Exception:
    #                                     ll_id = 0
    #                                 if ll_id:
    #                                     try:
    #                                         set_interest_status(ll_id, me_id, pid, "interested_tenant")
    #                                         set_count += 1
    #                                     except Exception as _e:
    #                                         # don’t break the UX; just surface a soft warning
    #                                         st.warning(tr("Saved interest but couldn’t tag status for {email}.").format(email=em))

    #                             st.success(tr("Interest sent to {n} contact(s)").format(n=(touched if isinstance(touched, int) else set_count or len(recipient_emails))))

    #                         except Exception as e:
    #                             st.error(f"{tr('Couldn’t save your interest')}: {type(e).__name__}: {e}")
    #                         finally:
    #                             try:
    #                                 st.cache_data.clear()
    #                             except Exception:
    #                                 pass
    #                             st.rerun()

    
    

                # st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

                # if not already_interested:
                #     with st.popover(tr("I’m interested"), use_container_width=True):

                #         st.caption(tr("Contacts for this property"))
                #         uploaders = list_property_uploaders(pid)  # [(name, email, display_role)]
                #         selected_key = f"selected_contacts_{pid}"
                #         if selected_key not in st.session_state:
                #             st.session_state[selected_key] = []

                #         if not uploaders:
                #             st.write(tr("No landlords/agents linked"))
                #         else:
                #             multiple = len(uploaders) > 1

                #             # Reset current selections if list changes length
                #             # (basic guard; optional)
                #             if multiple and st.session_state[selected_key]:
                #                 # keep only still-present emails
                #                 present = {em for _, em, _ in uploaders}
                #                 st.session_state[selected_key] = [
                #                     em for em in st.session_state[selected_key] if em in present
                #                 ]

                #             for idx_u, (up_name, up_email, link_role) in enumerate(uploaders):
                #                 role_norm    = (link_role or "").strip().lower()
                #                 display_role = "agent" if role_norm == "agent" else "landlord"
                #                 icon = role_icon(display_role) or ""
                #                 disp = (up_name or "").strip() or (up_email or "").split("@")[0] or tr("Unknown")
                #                 initials = _initials(disp, up_email) if '_initials' in globals() else (disp[:2] or "?").upper()
                #                 role_pill = tr("Landlord") if display_role == "landlord" else tr("Agent")

                #                 # One level of columns is OK here
                #                 cA, cB, cC = st.columns([1, 6, 1])
                #                 with cA:
                #                     st.markdown(f'<div class="tfl-avatar">{escape(initials)}</div>', unsafe_allow_html=True)
                #                 with cB:
                #                     st.markdown(
                #                         f'<div class="tfl-name">{escape(icon)} {escape(disp)} '
                #                         f'<span class="pill">{escape(role_pill)}</span></div>'
                #                         f'<div class="tfl-email"><a href="mailto:{escape(up_email or "")}">{escape(up_email or "")}</a></div>',
                #                         unsafe_allow_html=True
                #                     )
                #                     # Status label (optional)
                #                     try:
                #                         urow = get_user_by_email(up_email) or {}
                #                         other_id = int(urow.get("id") or 0)
                #                     except Exception:
                #                         other_id = 0
                #                     if other_id:
                #                         rel = (flc_relation_status(other_id, me_id, landlord_email=up_email) or "disconnected").lower()
                #                         if rel == "connected":
                #                             st.markdown(f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
                #                         elif rel.startswith("pending"):
                #                             st.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
                #                     else:
                #                         st.caption(tr("User record not found"))

                #                 with cC:
                #                     if multiple:
                #                         checked = st.checkbox(
                #                             "",
                #                             key=f"select_contact_{pid}_{idx_u}",
                #                             help=tr("Select to send interest to this contact"),
                #                             value=(up_email in st.session_state[selected_key]),
                #                         )
                #                         # keep session selections in sync
                #                         if checked and up_email not in st.session_state[selected_key]:
                #                             st.session_state[selected_key].append(up_email)
                #                         if not checked and up_email in st.session_state[selected_key]:
                #                             st.session_state[selected_key].remove(up_email)

                #         st.caption(tr("Optional note to the owner/agent"))
                #         note = st.text_area(
                #             tr("Message"),
                #             key=f"pi_note:{pid}",
                #             height=90,
                #             placeholder=tr("e.g., Hi! I’d like to view this place. Tue after 18:00 works for me."),
                #         )
                #         chips = st.multiselect(
                #             tr("Availability"),
                #             options=[tr("Today"), tr("Weekdays after 18:00"), tr("Weekend mornings")],
                #             key=f"pi_avail:{pid}",
                #         )

                #         if st.button(tr("Send interest"), key=f"pi_send:{pid}", use_container_width=True):
                #             final_note = note.strip()
                #             if chips:
                #                 final_note = (final_note + ("\n\n" if final_note else "")) + tr("Availability") + ": " + ", ".join(chips)
                #             # Always append profile highlights
                #             final_note = (final_note + ("\n\n" if final_note else "")) + tr("Includes profile highlights")

                #             # Decide recipients
                #             selected_emails = st.session_state.get(selected_key, [])
                #             contact_param = None
                #             if uploaders and len(uploaders) > 1:
                #                 if not selected_emails:
                #                     st.warning(tr("Please select at least one contact."))
                #                     st.stop()
                #                 contact_param = selected_emails  # send only to chosen contacts

                #             try:
                #                 # If your helper supports contact_emails, pass it; otherwise fallback gracefully
                #                 try:
                #                     touched = _send_interest_like_connect_for_property(
                #                         tenant_id=me_id,
                #                         property_id=pid,
                #                         note_text=final_note or None,
                #                         contact_emails=contact_param, "interested_tenant"
                #                     )
                #                 except TypeError:
                #                     # Older signature without contact_emails
                #                     touched = _send_interest_like_connect_for_property(
                #                         tenant_id=me_id,
                #                         property_id=pid,
                #                         note_text=final_note or None, "interested_tenant"
                #                     )
                #                 st.success(tr("Interest sent to {n} contact(s)").format(n=touched))
                #             except Exception as e:
                #                 st.error(f"Couldn’t save your interest: {type(e).__name__}: {e}")
                #             finally:
                #                 st.rerun()

    def tenant_my_interests():
        me_id = int(st.session_state.user["id"])

        st.subheader("⭐ " + tr("My interests"))

        try:
            mi_pids = sorted(list(list_interested_properties_for_tenant(me_id)))
        except Exception:
            mi_pids = []

        if not mi_pids:
            st.info(tr("No interests yet — tap “I’m interested” on a listing to track it here."))
            return

        # Reuse pills CSS
        try:
            _ensure_tfl_css()
        except Exception:
            pass

        from html import escape

        for ipid in mi_pids:
            br = get_property_brief(ipid)
            if not br:
                continue
            _id, addr, url, region, district, city, size_m2, rooms, floor, price, upd = br

            with st.container(border=True):
                # Title + link
                t1, t2 = st.columns([10,1])
                with t1:
                    line = f"**{escape(addr or (str(city) if city else tr('Property')))}**"
                    if url:
                        line += f" · [{tr('Open listing')}]({url})"
                    st.markdown(line)
                with t2:
                    with st.popover(":", use_container_width=True):
                        if st.button(tr("Cancel interest"), key=f"mi_cancel:{ipid}"):
                            linked_users = list_users_linked_to_property(ipid)
                            for owner_id in linked_users:
                                u = get_user_by_id(owner_id) or {}
                                em = (u.get("email") or "").strip().lower()
                                if em:
                                    try:
                                        flc_cancel_invite(me_id, em)
                                    except Exception:
                                        pass

                            _remove_interest_for_property(me_id, ipid)  # ← NEW
                            try: st.cache_data.clear()
                            except Exception: pass
                            st.success(tr("Interest cancelled"))
                            st.rerun()


                        
                    

                # Chips
                chips = []
                for label, val in [
                    (region, region), (district, district), (city, city),
                    (tr("m²"), size_m2), (tr("Rooms"), rooms), (tr("Floor"), floor), (tr("€"), price),
                ]:
                    if val not in (None, "", 0):
                        chips.append(f'<span class="pill">{escape(str(label))}: {escape(str(val))}</span>')
                if chips:
                    st.markdown(" ".join(chips), unsafe_allow_html=True)

                # Per-owner state & chat
                owners = list_users_linked_to_property(ipid)
                if not owners:
                    st.caption(tr("No owners linked to this property yet."))
                else:
                    for oid in owners:
                        u = get_user_by_id(oid) or {}
                        disp = (u.get("name") or u.get("email") or f"User #{oid}")
                        st.write(f"**{disp}**", unsafe_allow_html=True)

                        status = flc_relation_status(oid, me_id)  # 'connected' | 'pending_outbound' | etc.
                        if status == "connected":
                            st.markdown(f'<span class="pill pill-ok">{tr("Connected")}</span>', unsafe_allow_html=True)
                            with st.expander('Chat', expanded=False):
                                render_chat_popover_box(
                                    viewer_role="tenant",
                                    me_id=me_id,
                                    other_id=oid,
                                    key_ns=f"mi:chat:{ipid}:{oid}",
                                )
                        elif status in ("pending_outbound", "pending"):
                            st.markdown(f'<span class="pill">{tr("Pending")}</span>', unsafe_allow_html=True)
                        elif status == "rejected":
                            st.markdown(f'<span class="pill pill-no">{tr("Rejected")}</span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span class="pill">{tr("No relation")}</span>', unsafe_allow_html=True)



    # === Previous landlords + reference requests ===
    def previous_landlords_references():
        # Header
        st.subheader(tr("Previous landlords & references"))

        # DB handle for this section
        c = get_conn()

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
                    cur = c.cursor()
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
                                st.write(f"**{tr('Paid on time?')}:** {tr('Yes') if details.get('paid_on_time') else {tr('No')}}")
                                st.write(f"**{tr('Any unpaid utilities?')}:** {tr('Yes') if details.get('utilities_unpaid') else {tr('No')}}")
                                st.write(f"**{tr('Left in good condition?')}:** {tr('Yes') if details.get('good_condition') else {tr('No')}}")
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
                    row = c.execute("SELECT emailed_at FROM reference_requests WHERE token=?", (tok,)).fetchone()
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
                                        c.execute(
                                            "UPDATE reference_requests SET status=?, emailed_at=CURRENT_TIMESTAMP WHERE token=?",
                                            ("pending", tok),
                                        )
                                        c.commit()
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
                                            row = c.execute("SELECT CURRENT_TIMESTAMP").fetchone()
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
                                            c.execute("DELETE FROM reference_requests WHERE token=?", (tok,))
                                            c.commit()

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
                                label_visibility="collapsed"
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
                                        c.execute(
                                            "UPDATE reference_requests SET status=?, emailed_at=CURRENT_TIMESTAMP WHERE token=?",
                                            ("pending", tok),
                                        )
                                        c.commit()
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

   
    # ----------------- TOP BAR & MODE SWITCH -----------------

    def _ln_apply_css():
        st.markdown("""
        <style>
        :root{
            --ln-blue:#0A66C2;
            --ln-border:#E6E6E6;
            --ln-bg:#FFFFFF;
            --ln-masthead-h:56px;
        }
        .ln-masthead{
            position: sticky;
            top: 0;
            z-index: 2;
            min-height: var(--ln-masthead-h);
            background: var(--ln-bg);
            border-bottom: 1px solid var(--ln-border);
            padding: 8px 12px;
        }
        .ln-masthead:empty{ display: none; }
        .appview-container .main .block-container{
            padding-top: var(--ln-masthead-h);
        }
        .ln-logo{ font-weight:800; color:var(--ln-blue); }
        .ln-avatar{
            width:42px; height:42px; border-radius:50%;
            background:#e5e7eb; color:#374151;
            display:flex; align-items:center; justify-content:center;
            font-weight:700; font-size:15px; letter-spacing:.3px;
            overflow:hidden;
        }
        .ln-avatar img{ width:100%; height:100%; object-fit:cover; display:block; }
        </style>
        """, unsafe_allow_html=True)

    def _go(page_key: str):
        for k in list(st.session_state.keys()):
            if k.startswith(("tfl:", "tfl_", "tfl_contacts:", "ld_otr_", "otr_", "prospects")):
                st.session_state.pop(k, None)
        st.session_state["tenant_page"] = page_key
        st.session_state["page"] = page_key
        st.session_state["ui_mode"] = "page"
        st.session_state.pop("people:search_q", None)

    def _linkedin_masthead(avatar_url: str | None = None):
        _ln_apply_css()
        user = st.session_state.user
        initials = _initials(user.get("name"), user.get("email"))

        with st.container(border=False):
            st.markdown('<div class="ln-masthead">', unsafe_allow_html=True)
            left, center, right = st.columns([1, 4, 3])

            # LEFT
            with left:
                l1, l2 = st.columns(2)
                with l1:
                    if avatar_url:
                        st.markdown(
                            f"<div class='ln-avatar' title='{tr('Account')}'><img src='{avatar_url}' alt='{initials}'/></div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f"<div class='ln-avatar' title='{tr('Account')}'>{initials or '?'}</div>",
                            unsafe_allow_html=True
                        )
                with l2:
                    if st.button("🏠", key="ln_home", help=tr("Go to My Contacts"), type="secondary"):
                        _go("my_contacts")

            # CENTER
            with center:
                OPTIONS = ["users", "properties"]
                LABELS = {"users": tr("Search users"), "properties": tr("Search properties")}
                st.session_state.setdefault("header_search_target", "users")

                def _set_mode_from_target():
                    tgt = st.session_state.get("header_search_target", "users")
                    st.session_state["ui_mode"] = "search" if tgt == "users" else "search_properties"

                st.selectbox(
                    tr("Search in"),
                    options=OPTIONS,
                    key="header_search_target",
                    format_func=lambda v: LABELS[v],
                    label_visibility="collapsed",
                    on_change=_set_mode_from_target,
                )

            # RIGHT
            with right:
                ic1, ic2, ic3, ic4, ic5 = st.columns(5)

                with ic1:
                    st.button("👥", key="ln_nav_contacts", help=tr("My Contacts"),
                              type=("primary" if st.session_state["tenant_page"]=="my_contacts"
                                    and st.session_state["ui_mode"]=="page" else "secondary"),
                              on_click=_go, kwargs={"page_key":"my_contacts"})
                with ic2:
                    st.button("🧭", key="ln_nav_profile", help=tr("Open to Rent"),
                              type=("primary" if st.session_state["tenant_page"]=="open_to_rent"
                                    and st.session_state["ui_mode"]=="page" else "secondary"),
                              on_click=_go, kwargs={"page_key":"open_to_rent"})
                with ic3:
                    st.button("📄", key="ln_nav_refs", help=tr("Previous References"),
                              type=("primary" if st.session_state["tenant_page"]=="prev_refs"
                                    and st.session_state["ui_mode"]=="page" else "secondary"),
                              on_click=_go, kwargs={"page_key":"prev_refs"})
                with ic4:
                    st.button("⭐", key="ln_nav_interests", help=tr("My Interests"),
                            type=("primary" if st.session_state["tenant_page"]=="my_interests"
                                    and st.session_state["ui_mode"]=="page" else "secondary"),
                            on_click=_go, kwargs={"page_key":"my_interests"})

                with ic5:
                    with st.popover("👤", help=tr("Account")):
                        user = st.session_state.user
                        name = user.get("name", "")
                        role = user.get("role", "")
                        st.subheader(f"{role_icon(role)} {tr('Welcome')}, {name}")
                        st.caption(st.session_state.user.get("email") or "")
                        render_topbar_language("tenant_topbar")
                        st.button(tr("Account settings"))
                        if st.button(tr("Sign out")):
                            st.session_state.clear()
                            st.query_params.clear()
                            st.rerun()


    # Render masthead
    _linkedin_masthead(avatar_url=None)

    # ---------- MAIN VIEW ----------
    mode = st.session_state.get("ui_mode", "page")

    if mode == "search":
        # user/tenant search
        find_users("tenant")
    elif mode == "search_properties":
        # property search
        search_properties()
    else:
        # default navigation pages
        page = st.session_state.get("tenant_page", "my_contacts")
        if page == "my_contacts":
            people_hub("tenant")
        elif page == "open_to_rent":
            tenant_open_to_rent_section()
        elif page == "prev_refs":
            previous_landlords_references()
        elif page == "my_interests":                          # ✅ new
             tenant_my_interests()





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

    # # Try DB lookup if name not stored in session
    if not landlord_name:
        c = get_conn()
        row = c.execute("SELECT name FROM users WHERE id=? LIMIT 1", (landlord_id,)).fetchone()
        if row:
            landlord_name = (row[0] or "").strip()

    
 

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
            .toolbar-row{height:0}
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

                # 🔥 NEW: render dynamic characteristics INSIDE the form, BEFORE the button
                try:
                    extra_vals = render_property_extra_inputs(prefix="lp_add_dyn")
                except Exception:
                    extra_vals = {}

                vis  = st.checkbox(tr("Visible to tenants"), key=lpk("add", "vis"), value=False)

                c1, _ = st.columns([1, 5])
                submitted = c1.form_submit_button(tr("Add property"))

            # On submit:
            if submitted:
                address = (addr or "").strip()
                if not address:
                    st.error(tr("Enter an address."))
                else:
                    try:
                        new_id = lp_add_property_dynamic(
                            landlord_id=st.session_state.user["id"],
                            address=address,
                            listing_url=url,
                            visible=vis,
                            base_kwargs=dict(
                                region=region, district=regional_unit, city=municipality,
                                size_m2=size_m2, rooms=rooms, floor=floor, price=price
                            ),
                            extra_columns=extra_vals,
                        )
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.success(tr("Property added."))
                        st.rerun()
                    except Exception as e:
                        st.error(f"{tr('Can’t add property')}: {e}")

        # ---------- List properties ----------
        props = lp_list_properties(st.session_state.user["id"])
        if not props:
            st.caption(tr("No properties yet."))
            st.stop()

        me_id = st.session_state.user["id"]

        for (prop_id, address, listing_url, visible_to_tenants, created_at, updated_at,
            region, district, city, size_m2, rooms, floor, price) in props:

            where = " — ".join([x for x in [region, district, city] if x])
            
            # Load full row so we can read dynamic columns too
            try:
                full_row = _get_property_row(prop_id) or {}
            except Exception:
                full_row = {}


            # Interested tenants
            tenant_ids = list_interested_tenants_for_property(prop_id)
            interested_count = len(tenant_ids)

            with st.container(border=True):
                # ---------- Header ----------
                pr1, pr2 = st.columns([10,1])
                with pr1:
                    count_badge = f'<span class="pill badge">{tr("Interested")} ({interested_count})</span>'
                    st.markdown(f"### • {address} {count_badge}", unsafe_allow_html=True)
                with pr2:
                    st.markdown('<div style="position: relative;">', unsafe_allow_html=True)
                    with st.popover("⋯", help=tr("More")):
                        # Show/Hide toggle
                        if int(visible_to_tenants or 0) == 1:
                            if st.button("🙈 " + tr("Hide"), key=f"prop:{prop_id}:hide"):
                                lp_toggle_visibility(prop_id, me_id, False)
                                try: st.cache_data.clear()
                                except Exception: pass
                                st.rerun()
                        else:
                            if st.button("👁️ " + tr("Show"), key=f"prop:{prop_id}:show"):
                                lp_toggle_visibility(prop_id, me_id, True)
                                try: st.cache_data.clear()
                                except Exception: pass
                                st.rerun()

                        # Safer delete with confirm step
                        if st.button("🗑️ " + tr("Delete…"), key=f"prop:{prop_id}:delete_open"):
                            st.session_state["confirm_delete_prop"] = prop_id
                        if st.session_state.get("confirm_delete_prop") == prop_id:
                            st.warning(tr("Delete this property? This action cannot be undone."))
                            c1, c2 = st.columns(2)
                            if c1.button(tr("Yes, delete"), key=f"prop:{prop_id}:delete_yes"):
                                lp_delete_property(prop_id, me_id)
                                try: st.cache_data.clear()
                                except Exception: pass
                                st.success(tr("Property deleted."))
                                st.session_state.pop("confirm_delete_prop", None)
                                st.rerun()
                            if c2.button(tr("Cancel"), key=f"prop:{prop_id}:delete_no"):
                                st.session_state.pop("confirm_delete_prop", None)
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                #
                # Build chips (prefer helper if available to avoid duplicates)
                    try:
                        if 'property_chips_from_row' in globals():
                            # Use helper ONLY (it already includes core + dynamic)
                            chips = property_chips_from_row(full_row) or []
                        else:
                            # Manual fallback: core + dynamic
                            chips = []
                            # --- Core chips ---
                            if where:                 chips.append(f'<span class="pill">{where}</span>')
                            if size_m2:               chips.append(f'<span class="pill">{int(size_m2):,} m²</span>')
                            if rooms:                 chips.append(f'<span class="pill">{int(rooms)} {tr("rooms")}</span>')
                            if floor not in (None,0): chips.append(f'<span class="pill">{tr("Floor")} {int(floor)}</span>')
                            if price:                 chips.append(f'<span class="pill">€{int(price):,}</span>')
                            # --- Dynamic chips ---
                            for f in (PROPERTY_FIELDS if 'PROPERTY_FIELDS' in globals() else []):
                                if not f.get("active", True):
                                    continue
                                col = f.get("column")
                                val = full_row.get(col)
                                chip_fn = f.get("chip")
                                if callable(chip_fn):
                                    html = chip_fn(val)
                                    if html:
                                        chips.append(f'<span class="pill">{html}</span>')
                                else:
                                    form_type = (f.get("form") or {}).get("type")
                                    label = (f.get("form") or {}).get("label", f["name"].replace("_"," ").title())
                                    if val in (None, "", 0):
                                        continue
                                    if form_type == "checkbox":
                                        if int(val) == 1:
                                            chips.append(f'<span class="pill">{label}</span>')
                                    elif form_type in {"number","year"}:
                                        try:
                                            chips.append(f'<span class="pill">{label}: {int(val)}</span>')
                                        except Exception:
                                            chips.append(f'<span class="pill">{label}: {val}</span>')
                                    else:
                                        chips.append(f'<span class="pill">{label}: {val}</span>')
                    except Exception:
                        chips = []

                # --- /Dynamic characteristic chips ---

             
# --- /Dynamic characteristic chips ---

                vis_badge = (
                    f'<span class="pill badge">{tr("Visible to tenants")}</span>'
                    if int(visible_to_tenants or 0) == 1
                    else f'<span class="pill">{tr("Hidden from tenants")}</span>'
                )
                st.markdown(
                    f"""
                    <div class="prop-sub">{" ".join(chips)}</div>
                    <div class="meta-row">{vis_badge}</div>
                    """,
                    unsafe_allow_html=True
                )

                # ---------- Footer ----------
                st.markdown('<div class="divider" style="margin-top:10px;"></div>', unsafe_allow_html=True)
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

                # ---------- Edit ----------
                with st.expander("✏️ " + tr("Edit"), expanded=False):
                    # Load full row so we can prefill dynamic fields
                    try:
                        full_row = _get_property_row(prop_id) or {}
                    except Exception:
                        full_row = {}

                    e_addr = st.text_input(tr("Address"), value=address, key=f"prop:{prop_id}:edit_addr")
                    e_url  = st.text_input(tr("Listing URL (optional)"), value=(listing_url or ""), key=f"prop:{prop_id}:edit_url")

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
                                                value=int(size_m2 or 0), key=f"prop:{prop_id}:edit_size")
                    with es2:
                        rooms_new = st.number_input(tr("Rooms"), min_value=0, max_value=50, step=1,
                                                    value=int(rooms or 0), key=f"prop:{prop_id}:edit_rooms")
                    with es3:
                        floor_new = st.number_input(tr("Floor"), min_value=-5, max_value=100, step=1,
                                                    value=int(floor or 0), key=f"prop:{prop_id}:edit_floor")
                    with es4:
                        price_new = st.number_input(tr("Price (€)"), min_value=0, max_value=1_000_000, step=50,
                                                    value=int(price or 0), key=f"prop:{prop_id}:edit_price")

                    e_vis = st.checkbox(tr("Visible to tenants"),
                                        value=bool(int(visible_to_tenants or 0)),
                                        key=f"prop:{prop_id}:edit_vis")

                    # 🔥 NEW: render dynamic characteristics for EDIT, prefilled from DB row
                    extras_edit_values = {}
                    try:
                       
                        for f in (PROPERTY_FIELDS if 'PROPERTY_FIELDS' in globals() else []):
                            if not f.get("active", True):
                                continue
                            form = f.get("form") or {}
                            typ  = form.get("type")
                            label = form.get("label", f['name'].replace("_", " ").title())
                            col  = f["column"]
                            cur  = full_row.get(col)
                            key  = f"lp_edit_dyn:{prop_id}:{f['name']}"

                            if typ == "number":
                                extras_edit_values[col] = st.number_input(
                                    label, value=int(cur or 0), min_value=0, max_value=1_000_000, step=1, key=key
                                )
                            elif typ == "checkbox":
                                extras_edit_values[col] = 1 if st.checkbox(label, value=bool(cur or False), key=key) else 0
                            elif typ == "year":
                                extras_edit_values[col] = st.number_input(
                                    label, value=int(cur or 0), min_value=1900, max_value=2200, step=1, key=key
                                ) or None
                            elif typ == "select":
                                opts = list(form.get("options") or [])
                                if not opts:
                                    opts = ["—"]  # avoid empty options crash
                                # ensure current value is selectable
                                if cur is not None and cur not in opts:
                                    opts = [cur] + [o for o in opts if o != cur]
                                try:
                                    idx = opts.index(cur) if cur in opts else 0
                                except Exception:
                                    idx = 0
                                extras_edit_values[col] = st.selectbox(label, options=opts, index=idx, key=key)

                    except Exception:
                        pass

                    s1, _ = st.columns([3, 5])
                    if s1.button("💾 " + tr("Save changes"), key=f"prop:{prop_id}:save"):
                        try:
                            if not (e_addr or "").strip():
                                st.error(tr("Address is required."))
                            else:
                                region_final   = reg_new or region
                                district_final = ru_new or district
                                city_final     = muni_new or city

                                # Save core columns
                                lp_update_property(
                                    prop_id, me_id,
                                    e_addr, e_url, e_vis,
                                    region_final, district_final, city_final,
                                    size_new, rooms_new, floor_new, price_new,
                                )

                                # 🔥 Save dynamic columns in one UPDATE (if any)
                                try:
                                    if extras_edit_values:
                                        c = get_conn()
                                        set_cols = [f"{col}=?" for col in extras_edit_values.keys()]
                                        params  = list(extras_edit_values.values()) + [prop_id, me_id]
                                        c.execute(
                                            f"UPDATE landlord_properties SET {', '.join(set_cols)} WHERE id=? AND landlord_id=?",
                                        tuple(params))
                                        c.commit()
                                except Exception:
                                    # non-fatal: core update already saved
                                    pass

                                try: st.cache_data.clear()
                                except Exception: pass
                                st.success(tr("Changes saved."))
                                st.rerun()
                        except Exception as e:
                            st.error(f"{tr('Can’t save changes')}: {e}")

          

                # ---------- Interested tenants ----------
                # ---------- Interested tenants ----------
                # ---------- Interested tenants ----------
                st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

                with st.expander(tr("Interested tenants"), expanded=False):
                    if interested_count == 0:
                        st.caption(tr("No interest yet."))
                    else:
                        try: _ensure_tfl_css()
                        except Exception: pass

                        for tid in tenant_ids:
                            tenant_profile(
                                tid=tid,
                                landlord_id=me_id,
                                key_ns=f"lp:prop:{prop_id}",
                                property_id=prop_id,              # <<— important for per-property status + Accept/Reject
                                show_ll_interest_actions=True,    # <<— show per-property Accept/Reject when pending
                            )




    # =============================================================================
    # Find Tenants (Open to Rent) — with dynamic filters
    # =============================================================================
    
    # =============================================================================
    # Find Tenants (Open to Rent) — with dynamic filters
    # =============================================================================
    def find_tenants_page():
        st.subheader(tr("Find Tenants (Open to Rent)"))

        # Base filters
        try:
            render_tenant_filters(prefix="findten")
        except Exception as e:
            st.warning(f"{tr('Could not render base filters')}: {e}")

        # Dynamic filters
        try:
            extras = render_o2r_extra_filters(prefix="findten")
        except Exception as e:
            extras = {}
            st.warning(f"{tr('Could not render extra filters')}: {e}")

        # Collect base values from session_state (keys set by render_tenant_filters)
        ss = st.session_state
        base = dict(
            region=ss.get("findten_region") or None,
            city=ss.get("findten_city") or None,
            district=ss.get("findten_district") or None,
            size_min=ss.get("findten_size_min"),
            size_max=ss.get("findten_size_max"),
            rooms_min=ss.get("findten_rooms_min"),
            rooms_max=ss.get("findten_rooms_max"),
            floor_min=ss.get("findten_floor_min"),
            floor_max=ss.get("findten_floor_max"),
            price_min=ss.get("findten_price_min"),
            price_max=ss.get("findten_price_max"),
        )

        # Run search (prefers the version that accepts extras)
        try:
            try:
                rows = search_open_to_rent_tenants(extras=extras, **base) or []
            except TypeError:
                rows = search_open_to_rent_tenants(**base) or []
        except Exception as e:
            rows = []
            st.error(f"{tr('Search failed')}: {e}")

        if not rows:
            st.info(tr("No matching tenants found."))
            return

        # Cards
        try:
            _ensure_tfl_css()
        except Exception:
            pass

        landlord_id = int(st.session_state.user["id"])
        for r in rows:
            tid = int((r.get("tenant_id") if isinstance(r, dict) else None)
                    or (r.get("id") if isinstance(r, dict) else None)
                    or (r[0] if not isinstance(r, dict) and len(r) > 0 else 0))
            if not tid:
                continue
            with st.container(border=True):
                tenant_profile(
                    tid=tid,
                    landlord_id=landlord_id,
                    key_ns=f"findten:{landlord_id}:{tid}"
                )


    # def find_tenants_page():
    #     st.subheader(tr("Find Tenants (Open to Rent)"))

    #     # --- Filter widgets (standard set already in your codebase)
    #     # This draws the usual "Open to Rent" filters: location, budget, rooms, pets, etc.
    #     # It also fills st.session_state under the given prefix.
    #     try:
    #         render_tenant_filters(prefix="findten")
    #     except Exception as e:
    #         st.warning(f"{tr('Could not render base filters')}: {e}")

    #     # --- EXTRA dynamic filters (this is the part you asked about)
    #     # If you have defined the helper from our previous step, this will render
    #     # ANY new OTR characteristics as additional widgets under the same prefix.
    #     try:
    #         if 'render_o2r_extra_filters' in globals():
    #             render_o2r_extra_filters(prefix="findten")
    #     except Exception as e:
    #         st.warning(f"{tr('Could not render extra filters')}: {e}")

    #     # --- Run search using both base + dynamic filters bound to the same prefix
    #     try:
    #         rows = search_open_to_rent_tenants(prefix="findten") or []
    #     except Exception as e:
    #         rows = []
    #         st.error(f"{tr('Search failed')}: {e}")

    #     if not rows:
    #         st.info(tr("No matching tenants found."))
    #         return

    #     # --- Render tenant cards (landlord view actions are handled by tenant_profile)
    #     try:
    #         _ensure_tfl_css()
    #     except Exception:
    #         pass

    #     landlord_id = int(st.session_state.user["id"])
    #     for r in rows:
    #         # Accept either 'tenant_id' or 'id' from the row
    #         tid = int((r.get("tenant_id") if isinstance(r, dict) else None)
    #                   or (r.get("id") if isinstance(r, dict) else None)
    #                   or r[0] if not isinstance(r, dict) else 0)
    #         if not tid:
    #             continue
    #         with st.container(border=True):
    #             tenant_profile(
    #                 tid=tid,
    #                 landlord_id=landlord_id,
    #                 key_ns=f"findten:{landlord_id}:{tid}"
    #             )

   
        
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
    
    # ================== LINKEDIN-STYLE MASTHEAD (LANDLORD) ==================

    # ---- init state (unique keys for landlord to avoid collisions with tenant UI)
    st.session_state.setdefault("landlord_page", "my_contacts")
    st.session_state.setdefault("lnd_ui_mode", "page")   # 'page' or 'search'
    st.session_state["page"] = st.session_state["landlord_page"]  # (legacy alias if you use it elsewhere)

    def _ln_apply_css_lnd():
        st.markdown("""
        <style>
        :root{
            --ln-blue:#0A66C2;
            --ln-border:#E6E6E6;
            --ln-bg:#FFFFFF;
            --ln-masthead-h:56px; /* adjust height if needed */
        }

        /* Sticky LinkedIn-like header that doesn't overlap content */
        .ln-masthead{
            position: sticky;
            top: 0;
            z-index: 2; /* was 999 */
            min-height: var(--ln-masthead-h);
            background: var(--ln-bg);
            border-bottom: 1px solid var(--ln-border);
            padding: 8px 12px;
        }

        /* Hide the bar if masthead is empty */
        .ln-masthead:empty{ display: none; }

        /* Push page content below the masthead */
        .appview-container .main .block-container{
            padding-top: var(--ln-masthead-h);
        }

        .ln-logo{ font-weight:800; color:var(--ln-blue); }

        /* Avatar can show an <img> or initials text */
        .ln-avatar{
            width:42px; height:42px; border-radius:50%;
            background:#e5e7eb; color:#374151;
            display:flex; align-items:center; justify-content:center;
            font-weight:700; font-size:15px; letter-spacing:.3px;
            overflow:hidden;
        }
        .ln-avatar img{ width:100%; height:100%; object-fit:cover; display:block; }
        </style>
        """, unsafe_allow_html=True)


    def _go_lnd(page_key: str):
        # clear transient flags specific to your app (safe no-op if absent)
        for k in list(st.session_state.keys()):
            if k.startswith(("tfl:", "tfl_", "tfl_contacts:", "ld_otr_", "otr_", "prospects")):
                st.session_state.pop(k, None)
        st.session_state["landlord_page"] = page_key
        st.session_state["page"] = page_key
        st.session_state["lnd_ui_mode"] = "page"   # leave search
        st.session_state.pop("people:search_q", None)  # reset text next time

    def _open_search_lnd():
        st.session_state["lnd_ui_mode"] = "search"

    def _close_search_lnd():
        st.session_state["lnd_ui_mode"] = "page"

    def _linkedin_masthead_landlord(avatar_url: str | None = None):
        _ln_apply_css_lnd()
        
                
        user = st.session_state.user
        initials = _initials(user.get("name"), user.get("email"))
        
        with st.container():
            st.markdown('<div class="ln-masthead">', unsafe_allow_html=True)
            left, center, right = st.columns([1, 4, 3])

            # LEFT: brand / home
            with left:
                l1, l2 = st.columns(2)
                
                with l1:
                    if avatar_url:
                        st.markdown(
                            f"<div class='ln-avatar' title='{tr('Account')}'><img src='{avatar_url}' alt='{initials}'/></div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f"<div class='ln-avatar' title='{tr('Account')}'>{initials or '?'}</div>",
                            unsafe_allow_html=True
                        )
                with l2:
                    if st.button("🏠", key="lnd_home", help=tr("Go to My Contacts"), type="secondary"):
                    
                        _go_lnd("my_contacts")

 
            # CENTER: search (LinkedIn-style big pill)
            with center:
                search_label = tr("Search")

                def _on_header_search_change():
                    q = (st.session_state.get("ln_search_q") or "").strip()
                    st.session_state["people:search_q"] = q
                    st.session_state["lnd_ui_mode"] = "search"   # ✅ FIX: landlord flag
                                                 
                st.text_input(
                    search_label,
                    value=st.session_state.get("people:search_q", ""),
                    placeholder=tr("Name, email, criteria…"),
                    label_visibility="collapsed",
                    key="ln_search_q",
                    on_change=_on_header_search_change,
                )
   

            # RIGHT: icons + avatar (Contacts, Properties, References, Me)
            with right:
    
                ic1, icx, ic2, ic3, ic4 = st.columns(5)

                with ic1:
                    st.button(
                        "👥", key="lnd_nav_contacts", help=tr("My Contacts"),
                        type=("primary" if st.session_state["landlord_page"]=="my_contacts" and st.session_state["lnd_ui_mode"]=="page" else "secondary"),
                        on_click=_go_lnd, kwargs={"page_key":"my_contacts"}
                    )
                    
                with icx:
                    st.button(
                        "🧭", key="lnd_nav_findten", help=tr("Find Tenants (Open to Rent)"),
                        type=("primary" if st.session_state["landlord_page"]=="find_tenants"
                            and st.session_state["lnd_ui_mode"]=="page" else "secondary"),
                        on_click=_go_lnd, kwargs={"page_key":"find_tenants"}
                    )
    
                with ic2:
                    st.button(
                        "🏘️", key="lnd_nav_props", help=tr("My Properties"),
                        type=("primary" if st.session_state["landlord_page"]=="my_properties" and st.session_state["lnd_ui_mode"]=="page" else "secondary"),
                        on_click=_go_lnd, kwargs={"page_key":"my_properties"}
                    )
                with ic3:
                    st.button(
                        "📄", key="lnd_nav_refs", help=tr("My References"),
                        type=("primary" if st.session_state["landlord_page"]=="my_refs" and st.session_state["lnd_ui_mode"]=="page" else "secondary"),
                        on_click=_go_lnd, kwargs={"page_key":"my_refs"}
                    )
                with ic4:
                    # Use a visible label to avoid accessibility warnings
                    with st.popover("👤", help=tr("Account")):
                        user = st.session_state.user
                        name = user.get("name", "")
                        role = user.get("role", "")
                        st.subheader(f"{role_icon(role)} {tr('Welcome')}, {name}")
                        st.caption(st.session_state.user.get("email") or "")
                        
                        render_topbar_language("landlord_topbar")
                        
                        st.button(tr("Account settings"))
                        if st.button(tr("Sign out")):
                            st.session_state.clear()
                            st.query_params.clear()  # reset URL state
                            st.rerun()

    # ---------- render masthead
    _linkedin_masthead_landlord(avatar_url=None)

    # ---------- MAIN VIEW (mutually exclusive: search OR a page)
    if st.session_state["lnd_ui_mode"] == "search":
        # Only show the search UI (landlord role)
        find_users("landlord")
    else:
        page = st.session_state["landlord_page"]
        if page == "my_contacts":
            my_tenants()
        elif page == "my_properties":
            my_properties()
        elif page == "my_refs":
            my_references()
        elif page == "find_tenants":
            find_tenants_page()



        
def reference_submitted_page():
    # Show ONLY the success text and stop
    st.success(tr("Reference submitted successfully. Thank you!"))
    st.stop()
    
def reference_cancelled_page():
    st.warning(tr("Request cancelled."))
    st.stop()

# ---------- App ----------
# ---------- App ----------
def main():
    conn = get_conn()              # make sure we have a connection
    init_db()                      # create core tables if missing
    run_migrations(conn)           # your migrations (indexes, extras, etc.)
    ensure_registry_loaded_once()  # <-- NOW load JSON + add dynamic columns

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

    if st.button("🔄", key="refresh"):
        st.rerun()

    user = st.session_state.get("user")
    if user:
        role = user.get("role")
        if role == "tenant":
            tenant_dashboard(); return
        elif role in ("landlord", "agent"):
            landlord_dashboard(); return
        elif role == "admin":
            admin_dashboard(); return
        else:
            st.error(f"Unknown role: {role}"); return
    else:
        auth_gate(); return


if __name__ == "__main__":
    main()



