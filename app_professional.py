import streamlit as st
import sqlite3
import re
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from uuid import uuid4
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo 
import requests
from functools import lru_cache
import json
from json import JSONDecodeError

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
    st.session_state["lang"] = "Ελληνικά"  # default

TRANSLATIONS_EL = {
        # Auth & common
        "Sign In": "Σύνδεση",
        "Create Account": "Δημιουργία Λογαριασμού",
        "Sign Out": "Αποσύνδεση",
        "Incorrect email or password. Please try again.": "Λάθος email ή κωδικός. Παρακαλώ δοκιμάστε ξανά.",
        "Your account has been created. Please sign in to continue.": "Ο λογαριασμός σας δημιουργήθηκε. Συνδεθείτε για να συνεχίσετε.",
        "Your account has been created — please sign in.": "Ο λογαριασμός σας δημιουργήθηκε — συνδεθείτε.",
        "Welcome, ": "Καλώς ορίσατε, ",
        "Please enter your full name.": "Παρακαλώ εισαγάγετε το πλήρες όνομά σας.",
        "Please enter a valid email address.": "Παρακαλώ εισαγάγετε έγκυρη διεύθυνση email.",
        "Passwords do not match. Please try again.": "Οι κωδικοί δεν ταιριάζουν. Δοκιμάστε ξανά.",
        "This email is already registered.": "Αυτό το email έχει ήδη καταχωρηθεί.",
        "Unknown role:": "Άγνωστος ρόλος:",
        "Logged in as": "Συνδεθήκατε ως",
        "Refresh": "Ανανέωση",
        # SMTP
        "Missing SMTP details: host, port, username, password, sender, or recipient.": "Λείπουν στοιχεία SMTP: host, port, όνομα χρήστη, κωδικός, αποστολέας ή παραλήπτης.",
        "Send Test Email": "Αποστολή Δοκιμαστικού Email",
        "Send test to": "Αποστολή δοκιμής σε",
        "If you received this email, your SMTP configuration is working. ✅": "Αν λάβατε αυτό το email, η ρύθμιση SMTP λειτουργεί. ✅",
        "Test email sent successfully.": "Το δοκιμαστικό email στάλθηκε με επιτυχία.",
        "Failed to send email:": "Αποτυχία αποστολής email:",
        # Sections
        "Tenant Dashboard": "Πίνακας Ενοικιαστή",
        "Landlord Dashboard": "Πίνακας Ιδιοκτήτη",
        "Administrator Dashboard": "Πίνακας Διαχειριστή",
        # Future Landlords
        "Future Landlords (Contacts)": "Μελλοντικοί Ιδιοκτήτες (Επαφές)",
        "Enter a landlord’s email address": "Εισάγετε το email του ιδιοκτήτη",
        "Add Contact": "Προσθήκη Επαφής",
        "Contact added and invitation sent successfully.": "Η επαφή προστέθηκε και η πρόσκληση στάλθηκε με επιτυχία.",
        "Contact added, but the email could not be sent:": "Η επαφή προστέθηκε, αλλά δεν ήταν δυνατή η αποστολή email:",
        "Unable to add contact:": "Αδυναμία προσθήκης επαφής:",
        "Delete Previous Landlord": "Διαγραφή Προηγούμενου Ιδιοκτήτη",
        "Are you sure you want to delete this previous landlord and all related data?": "Θέλεις σίγουρα να διαγράψεις αυτόν τον προηγούμενο ιδιοκτήτη και όλα τα σχετικά δεδομένα;",
        "Yes, delete": "Ναι, διαγραφή",
        "No, keep it": "Όχι, διατήρησέ το",
        "Previous landlord deleted permanently.": "Ο προηγούμενος ιδιοκτήτης διαγράφηκε οριστικά.",
        "Unable to delete": "Αδυναμία διαγραφής",
        "Send Invitation": "Αποστολή Πρόσκλησης",
        "Invited": "Προσκλήθηκε",
        "Invitation sent successfully.": "Η πρόσκληση στάλθηκε με επιτυχία.",
        "Unable to send invitation:": "Αδυναμία αποστολής πρόσκλησης:",
        "Contact removed.": "Η επαφή αφαιρέθηκε.",
        "Name": "Ονοματεπώνυμο",
        "Address": "Διεύθυνση",
        "No future landlord contacts yet.": "Δεν υπάρχουν ακόμα επαφές μελλοντικών ιδιοκτητών.",
        # Previous Landlords & References
        "Previous Landlords and References": "Προηγούμενοι Ιδιοκτήτες και Συστάσεις",
        "Reference submitted successfully. Thank you!":"Η αναφορά υποβλήθηκε με επιτυχία. Ευχαριστούμε!",
        "Tax ID (9 digits)": "ΑΦΜ (9 ψηφία)",
        "Add Previous Landlord": "Προσθήκη Προηγούμενου Ιδιοκτήτη",
        "Are you sure you want to cancel this reference request?": "Είσαι σίγουρος ότι θέλεις να ακυρώσεις αυτό το αίτημα;",
        "Yes, cancel it": "Ναι, ακύρωσε",
        'Cancel Request': "Ακύρωση αιτήματος",
        'Request cancelled — landlord notified, contract and responses permanently deleted.':'Αίτημα ακυρώθηκε — ο ιδιοκτήτης ειδοποιήθηκε, το συμβόλαιο και οι απαντήσεις διαγράφηκαν οριστικά.',
        'No, keep it': "Όχι, διατήρησέ το",
        'Start New Reference Request': 'Αίτημα Σύστασης',
        "Please enter the landlord’s name.": "Παρακαλώ εισαγάγετε το όνομα του ιδιοκτήτη.",
        "Please enter the landlord’s address.": "Παρακαλώ εισαγάγετε τη διεύθυνση του ιδιοκτήτη.",
        "Previous landlord added successfully.": "Ο προηγούμενος ιδιοκτήτης προστέθηκε με επιτυχία.",
        "Request Reference": "Αίτημα Σύστασης",
        "Reference request sent successfully by email.": "Το αίτημα σύστασης στάλθηκε με επιτυχία μέσω email.",
        "Email delivery failed (": "Η αποστολή email απέτυχε (",
        "Please share this link manually:": "Παρακαλώ κοινοποιήστε αυτόν τον σύνδεσμο χειροκίνητα:",
        # Contract
        "Contract Status:": "Κατάσταση Συμβολαίου:",
        "Contract is locked awaiting landlord consent.":"Το συμβόλαιο παραμένει κλειδωμένο, αναμένεται συναίνεση ιδιοκτήτη",
        "Download Contract": "Λήψη Συμβολαίου",
        "Replace Tenancy Contract (PDF or Image)": "Συμβολαίου Μίσθωσης (PDF ή Εικόνα)",
        "Upload Tenancy Contract (PDF or Image)": "Ανέβασε Συμβόλαιο Μίσθωσης (PDF ή Εικόνα)",
        "Contract uploaded. Status reset to Pending Review.": "Το συμβόλαιο μεταφορτώθηκε. Η κατάσταση επαναφέρθηκε σε Αναμονή Ελέγχου.",
        "Contract uploaded. Status set to Pending Review.": "Το συμβόλαιο μεταφορτώθηκε. Η κατάσταση ορίστηκε σε Αναμονή Ελέγχου.",
        "Unable to read the saved file:": "Δεν είναι δυνατή η ανάγνωση του αποθηκευμένου αρχείου:",
        "⏳ Pending Review": "⏳ Αναμονή Ελέγχου",
        "✅ Verified Contract": "✅ Επικυρωμένο Συμβόλαιο",
        "❌ Rejected Contract": "❌ Απορριφθέν Συμβόλαιο",
        "Thanks, your response is saved.": "Ευχαριστούμε, η απάντησή σας αποθηκεύτηκε.",
        "Pending References (All Tenants)": "Εκκρεμείς Συστάσεις (Όλοι οι Ενοικιαστές)",
        "No requests available.": "Δεν υπάρχουν διαθέσιμα αιτήματα.",
        "Reference Link": "Σύνδεσμος Σύστασης",
        "✅ Verify Contract": "✅ Επικύρωση Συμβολαίου",
        "Contract verified successfully.": "Το συμβόλαιο επικυρώθηκε με επιτυχία.",
        "Cancel Reference": "Ακύρωση Σύστασης",
        "Reference cancelled.": "Η σύσταση ακυρώθηκε.",
        # Landlord dashboard
        "Prospective Tenants (Listed You as Future Landlord)": "Υποψήφιοι Ενοικιαστές (Σας έχουν δηλώσει ως μελλοντικό ιδιοκτήτη)",
        "No tenants have listed you as a future landlord yet.": "Κανένας ενοικιαστής δεν σας έχει δηλώσει ακόμα ως μελλοντικό ιδιοκτήτη.",
        "Respond Now": "Απάντηση Τώρα",
        "Submit Reference": "Υποβολή Σύστασης",
        "Not My Tenant / Cancel": "Δεν είναι ο ενοικιαστής μου / Ακύρωση",
        "Please confirm you were the landlord.": "Παρακαλώ επιβεβαιώστε ότι ήσασταν ο ιδιοκτήτης.",
        "Reference submitted successfully.": "Η σύσταση υποβλήθηκε με επιτυχία.",
        "Request cancelled.": "Το αίτημα ακυρώθηκε.",
        "View Submitted Reference": "Προβολή Υποβληθείσας Σύστασης",
        # Public portal
        "🏠 RentRight — Landlord Reference Portal": "🏠 RentRight — Συστατικές επιστολές Ιδιοκτήτη",
        "Invalid or expired reference token.": "Μη έγκυρο ή ληγμένο διακριτικό σύστασης.",
        "This reference has already been submitted. Thank you!": "Αυτή η σύσταση έχει ήδη υποβληθεί. Ευχαριστούμε!",
        "Reference for": "Σύσταση για",
        "I confirm I was the landlord for this tenant.": "Επιβεβαιώνω ότι ήμουν ο ιδιοκτήτης αυτού του ενοικιαστή.",
        "Overall tenant score": "Συνολική αξιολόγηση ενοικιαστή",
        "Did the tenant pay on time?": "Πλήρωνε ο ενοικιαστής στην ώρα του;",
        "Did the tenant leave utilities unpaid?": "Άφησε απλήρωτους λογαριασμούς;",
        "Did the tenant leave the apartment in good condition?": "Παραδόθηκε το διαμέρισμα σε καλή κατάσταση;",
        "Optional comments": "Προαιρετικά σχόλια",
        "All Reference Requests": "Όλα τα Αιτήματα Σύστασης",
        "No reference requests have been created yet.": "Δεν έχουν δημιουργηθεί ακόμα αιτήματα σύστασης.",
        # Settings
        "Email & App Settings": "Ρυθμίσεις Email & Εφαρμογής",
        "Email Settings (SMTP)": "Ρυθμίσεις Email (SMTP)",
        "App Base URL": "Βασικό URL Εφαρμογής",
        "Base URL for Links": "Βασικό URL για Συνδέσμους",
        '**To landlord:**': 'Στον Ιδιοκτήτη',
        # Misc labels
        "Email": "Email",
        "Password": "Κωδικός",
        "Confirm password": "Επιβεβαίωση κωδικού",
        "Full name": "Πλήρες όνομα",
        "Role": "Ρόλος",
        "Tenant": "Ενοικιαστής",
        "Landlord": "Ιδιοκτήτης",
        "Admin": "Διαχειριστής",
        "completed": "Ολοκληρώθηκε",
        "I confirm that I was the landlord for this tenant. "
        "By checking this box, I consent to the use of the uploaded tenancy contract "
        "solely for verifying my relationship with the tenant and for completing this reference. "
        "The contract will remain encrypted and locked until I provide this confirmation. "
        "It will not be shared or used for any other purpose, in accordance with GDPR.":

        "Επιβεβαιώνω ότι ήμουν ο ιδιοκτήτης αυτού του ενοικιαστή. "
        "Με την επιλογή αυτού του πλαισίου συναινώ στη χρήση του ανεβασμένου μισθωτηρίου συμβολαίου "
        "αποκλειστικά για την επαλήθευση της σχέσης μου με τον ενοικιαστή και για τη συμπλήρωση αυτής της σύστασης. "
        "Το συμβόλαιο θα παραμείνει κρυπτογραφημένο και κλειδωμένο έως ότου δώσω αυτήν την επιβεβαίωση. "
        "Δεν θα κοινοποιηθεί ούτε θα χρησιμοποιηθεί για οποιονδήποτε άλλο σκοπό, σύμφωνα με τον GDPR.",
        "Reference Requests Sent To You": "Αιτήματα σύστασης που σας στάλθηκαν",
        "Pending": "Εκκρεμή",
        "Completed": "Ολοκληρωμένα",
        "Cancelled": "Ακυρωμένα",
        "All": "Όλα",
        "Tenant:": "Ενοικιαστής:",
        "Email:": "Email:",
        "Status:": "Κατάσταση:",
        "Created:": "Δημιουργήθηκε:",
        "Score:": "Βαθμολογία:",
        "**Tenant:**": "**Ενοικιαστής:**",
        "**Email:**": "**Email:**",
        "**Status:**": "**Κατάσταση:**",
        "**Created:**": "**Δημιουργήθηκε:**",
        "**Score:**": "**Βαθμολογία:**",
        "Yes": "Ναι",
        "No": " Όχι",
        "No previous landlords added yet.": "Δεν έχουν προστεθεί ακόμη προηγούμενοι ιδιοκτήτες.",
        "No active reference request.": "Δεν υπάρχει ενεργό αίτημα σύστασης.",
        'Reference from previous landlord': 'Σύσταση από προηγούμενο ιδιοκτήτη',
        # === Reference Portal (info banner + consent) ===
        "Reference for": "Σύσταση για",
        "Address": "Διεύθυνση",

        "I confirm I was the landlord for this tenant and consent to the use and disclosure of my full name solely for verification of this reference.":
        "Επιβεβαιώνω ότι ήμουν ο/η ιδιοκτήτης/ιδιοκτήτρια αυτού του ενοικιαστή και συναινώ στη χρήση και κοινοποίηση του πλήρους ονόματός μου αποκλειστικά για την επαλήθευση αυτής της σύστασης.",

        "Tenant: {tenant_name} — Address: {address}":
        "Ενοικιαστής/στρια: {tenant_name} — Διεύθυνση: {address}",

        "Privacy & verification details": "Λεπτομέρειες απορρήτου & επαλήθευσης",

        "RentRight processes your responses, and if the tenant has uploaded a tenancy contract, may decrypt and review it after your confirmation solely to verify this reference (lawful basis: legitimate interests). The contract remains encrypted and is not shown to you. You may object at any time as described in the Privacy Notice.":
        "Η RentRight επεξεργάζεται τις απαντήσεις σας και, αν ο ενοικιαστής έχει ανεβάσει μισθωτήριο συμβόλαιο, μπορεί να το αποκρυπτογραφήσει και να το εξετάσει μετά την επιβεβαίωσή σας, αποκλειστικά για να επαληθεύσει αυτή τη σύσταση (νομική βάση: έννομα συμφέροντα). Το συμβόλαιο παραμένει κρυπτογραφημένο και δεν εμφανίζεται σε εσάς. Μπορείτε να προβάλλετε αντίρρηση ανά πάσα στιγμή όπως περιγράφεται στην Πολιτική Απορρήτου.",

        "Privacy Notice": "Πολιτική Απορρήτου",

        # --- Form fields (in case any are missing) ---
        "Overall tenant score": "Συνολική βαθμολογία ενοικιαστή",
        "Did the tenant pay on time?": "Πλήρωνε ο ενοικιαστής στην ώρα του;",
        "Did the tenant leave utilities unpaid?": "Άφησε ο ενοικιαστής απλήρωτους λογαριασμούς;",
        "Did the tenant leave the apartment in good condition?": "Άφησε ο ενοικιαστής το διαμέρισμα σε καλή κατάσταση;",
        "Optional comments": "Προαιρετικά σχόλια",
        "Submit Reference": "Υποβολή σύστασης",
        "Previous landlord:": "Προηγούμενος ιδιοκτήτης",
        "Consent": "Συγκατάθεση",
        # Open to Rent
        "Open to Rent": "Διαθέσιμος/η για ενοικίαση",
        "I'm currently looking for a place": "Αναζητώ αυτήν την περίοδο σπίτι",
        "City": "Πόλη",
        "District": "Περιοχή",
        "Min size (m²)": "Ελάχιστο μέγεθος (τ.μ.)",
        "Max size (m²)": "Μέγιστο μέγεθος (τ.μ.)",
        "Min rooms": "Ελάχιστα δωμάτια",
        "Max rooms": "Μέγιστα δωμάτια",
        "Min floor": "Ελάχιστος όροφος",
        "Max floor": "Μέγιστος όροφος",
        "Min price (€)": "Ελάχιστη τιμή (€)",
        "Max price (€)": "Μέγιστη τιμή (€)",
        "Save preferences": "Αποθήκευση προτιμήσεων",
        "Preferences saved.": "Οι προτιμήσεις αποθηκεύτηκαν.",
        "Please enter at least a city or a district.": "Καταχωρίστε τουλάχιστον πόλη ή περιοχή.",
        "Please check your ranges: maximums must be greater than or equal to minimums.": "Ελέγξτε τα εύρη: τα μέγιστα πρέπει να είναι μεγαλύτερα ή ίσα από τα ελάχιστα.",
        "Tip: leave a minimum as 0 if you have no minimum for that field.": "Συμβουλή: αφήστε το ελάχιστο ως 0 αν δεν έχετε ελάχιστο για το πεδίο.",
        "rooms": "δωμάτια",
        "Looking in": "Αναζήτηση σε",
        "Active": "Ενεργό",
        "Inactive": "Ανενεργό",
        "Connected": "Connected",
        "Not invited yet": "Not invited yet",
        "Disconnect": "Disconnect",
        "Contact added, but the email could not be sent:": "Contact added, but the email could not be sent:",

    }


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




def _yn(val):
    if val is True:  return tr("Yes")
    if val is False: return tr("No")
    return "—"

def _truncate(txt, n=140):
    if not txt: return None
    if len(txt) <= n: return txt
    cut = txt[:n].rsplit(" ", 1)[0]
    return cut + "…"


def flc_request_from_landlord(landlord_id: int, tenant_id: int):
    """
    Called when LANDLORD clicks Connect.
    Create or update a row as 'pending'.
    """
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO flc (landlord_id, tenant_id, status, updated_at, created_at)
        VALUES (:lid, :tid, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(landlord_id, tenant_id)
        DO UPDATE SET status='pending', updated_at=CURRENT_TIMESTAMP
    """, {"lid": landlord_id, "tid": tenant_id})
    conn.commit()


def flc_tenant_accept(landlord_id: int, tenant_id: int):
    """Tenant accepts -> status becomes 'connected'."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE flc
        SET status='connected', updated_at=CURRENT_TIMESTAMP
        WHERE landlord_id=:lid AND tenant_id=:tid
    """, {"lid": landlord_id, "tid": tenant_id})
    conn.commit()


def flc_tenant_reject(landlord_id: int, tenant_id: int):
    """Tenant rejects -> status becomes 'rejected'."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE flc
        SET status='rejected', updated_at=CURRENT_TIMESTAMP
        WHERE landlord_id=:lid AND tenant_id=:tid
    """, {"lid": landlord_id, "tid": tenant_id})
    conn.commit()


def flc_get_status(landlord_id: int, tenant_id: int):
    """
    Returns 'connected' | 'rejected' | None from future_landlord_connections.
    """
    if not landlord_id or not tenant_id:
        return None
    c = get_conn()
    row = c.execute(
        "SELECT status FROM future_landlord_connections WHERE landlord_id=? AND tenant_id=?",
        (landlord_id, tenant_id)
    ).fetchone()
    return row[0] if row else None


def flc_list_inbound_for_tenant(tenant_id: int):
    """
    Returns rows of (contact_id, landlord_email, inbound_requested_at)
    for landlord-initiated pending requests targeting this tenant.
    """
    c = get_conn()
    cur = c.cursor()

    # If the column doesn't exist yet, return empty (or you could call run_migrations(c) then retry)
    if not _table_has_column(c, "future_landlord_contacts", "inbound_request"):
        return []

    # Order so non-null timestamps appear first and most recent first
    cur.execute(
        """
        SELECT id, email, inbound_requested_at
        FROM future_landlord_contacts
        WHERE tenant_id = ? AND inbound_request = 1
        ORDER BY (inbound_requested_at IS NULL) ASC,
                 inbound_requested_at DESC
        """,
        (tenant_id,),
    )
    return cur.fetchall()



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

# === End language utilities ===


# === Top-right language switcher (flags only) ===
def render_topbar_language():
    c1, c2 = st.columns([8, 2])
    with c2:
        choice = st.selectbox(
            "🌐 Language",
            ["ENG", "GR"],
            key="lang_flag",
            index=0 if st.session_state.get("lang","English")=="English" else 1,
            label_visibility="collapsed",
        )
        st.session_state["lang"] = "English" if choice == "ENG" else "Ελληνικά"

            
render_topbar_language()
# === End top-right language switcher (flags only) ===


# --- SMTP helpers integrados con st.secrets y session_state ---
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


# ---- 1. Define writable base ----
WRITABLE_BASE = Path(
    os.environ.get("STREAMLIT_DATA_DIR")
    or "/mount/data" if Path("/mount/data").exists()
    else tempfile.gettempdir()
)
WRITABLE_BASE.mkdir(parents=True, exist_ok=True)

# ---- 2. Define paths for DB + uploads ----
DB_PATH = WRITABLE_BASE / "app.db"
UPLOAD_DIR = WRITABLE_BASE / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# (Optional sanity check)
try:
    (WRITABLE_BASE / ".write_test").write_text("ok", encoding="utf-8")
    (WRITABLE_BASE / ".write_test").unlink(missing_ok=True)
except Exception as e:
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



@st.cache_resource
def ensure_contracts_consent_column(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(reference_contracts)")
    cols = [r[1] for r in cur.fetchall()]
    if "consent_status" not in cols:
        cur.execute("ALTER TABLE reference_contracts ADD COLUMN consent_status TEXT NOT NULL DEFAULT 'locked'")
        conn.commit()
        
from datetime import datetime

def _now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")

def flc_get_status(landlord_id: int, tenant_id: int) -> str | None:
    row = conn.execute(
        "SELECT status FROM future_landlord_connections WHERE landlord_id=? AND tenant_id=?",
        (landlord_id, tenant_id)
    ).fetchone()
    return row[0] if row else None

def flc_connect(landlord_id: int, tenant_id: int) -> None:
    now = _now_iso()
    conn.execute("""
        INSERT INTO future_landlord_connections (landlord_id, tenant_id, status, created_at, updated_at)
        VALUES (?, ?, 'connected', ?, ?)
        ON CONFLICT(landlord_id, tenant_id)
        DO UPDATE SET status='connected', updated_at=excluded.updated_at
    """, (landlord_id, tenant_id, now, now))
    conn.commit()

def flc_reject(landlord_id: int, tenant_id: int) -> None:
    now = _now_iso()
    conn.execute("""
        INSERT INTO future_landlord_connections (landlord_id, tenant_id, status, created_at, updated_at)
        VALUES (?, ?, 'rejected', ?, ?)
        ON CONFLICT(landlord_id, tenant_id)
        DO UPDATE SET status='rejected', updated_at=excluded.updated_at
    """, (landlord_id, tenant_id, now, now))
    conn.commit()
    
def flc_request_from_landlord(tenant_id: int, landlord_email: str) -> None:
    """Create/mark an inbound request for the tenant from this landlord."""
    email = (landlord_email or "").strip().lower()
    now = _now_iso()
    cur = get_conn().cursor()

    # Upsert contact with invited=1 so it shows up on the tenant side
    cur.execute("""
        INSERT INTO future_landlord_contacts (tenant_id, email, created_at, invited, invited_at)
        VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(tenant_id, email)
        DO UPDATE SET invited=1, invited_at=excluded.invited_at
    """, (tenant_id, email, now, now))

    # If there was an old "rejected", clear it so the pair can be seen again
    lid = get_user_id_by_email(email)
    if lid:
        cur.execute(
            "DELETE FROM future_landlord_connections WHERE landlord_id=? AND tenant_id=? AND status='rejected'",
            (lid, tenant_id)
        )

    get_conn().commit()
    
def flc_list_prospective_for_landlord(landlord_id: int):
    """
    Returns rows of tenants that are either:
      - tenant-origin pending/invited (invited=1), or
      - landlord-origin pending (inbound_request=1).
    Output: [(tenant_id, invited, invited_at, inbound_request, inbound_requested_at)]
    """
    c = get_conn()
    landlord = get_user_by_id(landlord_id)
    if not landlord:
        return []

    email = (landlord.get("email") or "").strip().lower()
    if not email:
        return []

    # Include BOTH signals: invited=1 (tenant-origin) OR inbound_request=1 (landlord-origin)
    rows = c.execute(
        """
        SELECT c.tenant_id, c.invited, c.invited_at, c.inbound_request, c.inbound_requested_at
        FROM future_landlord_contacts AS c
        WHERE LOWER(c.email) = ? AND (c.invited = 1 OR c.inbound_request = 1)
        ORDER BY COALESCE(c.inbound_requested_at, c.invited_at) DESC
        """,
        (email,),
    ).fetchall()

    return rows or []




def flc_disconnect(landlord_id: int, tenant_id: int) -> None:
    # We mark as rejected so it no longer appears in “Future Tenants”
    now = _now_iso()
    conn.execute("""
        INSERT INTO future_landlord_connections (landlord_id, tenant_id, status, created_at, updated_at)
        VALUES (?, ?, 'rejected', ?, ?)
        ON CONFLICT(landlord_id, tenant_id)
        DO UPDATE SET status='rejected', updated_at=excluded.updated_at
    """, (landlord_id, tenant_id, now, now))
    conn.commit()

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

def has_inbound_request(tenant_id: int, landlord_email: str) -> bool:
    c = get_conn()
    if not _table_has_column(c, "future_landlord_contacts", "inbound_request"):
        return False
    row = c.execute(
        "SELECT inbound_request FROM future_landlord_contacts WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, landlord_email)
    ).fetchone()
    return bool(row and row[0])


def flc_request_connect(landlord_id: int, tenant_id: int) -> None:
    """Landlord -> Tenant: create a pending request visible in tenant contacts and in landlord Prospective list."""
    c = get_conn()
    landlord = get_user_by_id(landlord_id)
    if not landlord:
        return
    # ensure contact row exists for the tenant with this landlord email
    add_future_landlord_contact(tenant_id, landlord["email"])
    now = _now_iso()
    c.execute(
        """
        UPDATE future_landlord_contacts
        SET inbound_request=1, inbound_requested_at=?
        WHERE tenant_id=? AND LOWER(email)=LOWER(?)
        """,
        (now, tenant_id, landlord["email"]),
    )
    c.commit()


def flc_cancel_request(landlord_id: int, tenant_id: int) -> None:
    c = get_conn()
    landlord = get_user_by_id(landlord_id)
    if not landlord:
        return
    c.execute(
        "UPDATE future_landlord_contacts SET inbound_request=0, inbound_requested_at=NULL "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, landlord["email"])
    )
    c.commit()

import re  # ⬅️ add once at top of file if not already imported

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
        SELECT id, COALESCE(name, ''), email
        FROM users
        WHERE role='landlord' AND {" AND ".join(conds)}
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
# --- Greece location pickers (Region → Regional Unit → Municipality) ---

@st.cache_resource
def load_ellada():
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


def greece_location_pickers(prefix: str = "otr"):
    """
    Renders 3 linked selectboxes:
      Περιφέρεια -> Περιφερειακή Ενότητα -> Δήμος (Πόλη)
    Returns (region, regional_unit, municipality) where any can be None.
    """
    # Load and get a *list* of region names, not top-level keys
    data, regions, _ = load_ellada_index("ellada.json")  # or omit the arg if you prefer the built-in path search

    # Region
    region_options = [tr("Any")] + (regions or [])
    region = st.selectbox(tr("Region"), options=region_options, key=f"{prefix}_region")
    region = None if region == tr("Any") else region

    # Regional Unit (depends on Region)
    units = list_units(data, region) if region else []
    unit_options = [tr("Any")] + (units or [])
    regional_unit = st.selectbox(tr("Regional unit"), options=unit_options, key=f"{prefix}_ru")
    regional_unit = None if regional_unit == tr("Any") else regional_unit

    # Municipality (depends on Regional Unit)
    munis = list_municipalities(data, region, regional_unit) if (region and regional_unit) else []
    mun_options = [tr("Any")] + (munis or [])
    municipality = st.selectbox(tr("Municipality"), options=mun_options, key=f"{prefix}_mun")
    municipality = None if municipality == tr("Any") else municipality

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
    # reference_requests: columns that newer code expects but old DBs may lack
    add_column_if_missing(conn, "reference_requests", "emailed_at TEXT")
    add_column_if_missing(conn, "reference_requests", "confirm_landlord INTEGER")
    add_column_if_missing(conn, "reference_requests", "score INTEGER")
    add_column_if_missing(conn, "reference_requests", "paid_on_time INTEGER")
    add_column_if_missing(conn, "reference_requests", "utilities_unpaid INTEGER")
    add_column_if_missing(conn, "reference_requests", "good_condition INTEGER")
    add_column_if_missing(conn, "reference_requests", "comments TEXT")

    # reference_contracts: make sure consent_status exists on old DBs
    add_column_if_missing(conn, "reference_contracts", "consent_status TEXT NOT NULL DEFAULT 'locked'")
    
    # --- Open-to-rent columns on tenant_profiles ---
    add_column_if_missing(conn, "tenant_profiles", "open_to_rent INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "tenant_profiles", "search_city TEXT")
    add_column_if_missing(conn, "tenant_profiles", "search_district TEXT")
    add_column_if_missing(conn, "tenant_profiles", "size_min INTEGER")
    add_column_if_missing(conn, "tenant_profiles", "size_max INTEGER")
    add_column_if_missing(conn, "tenant_profiles", "rooms_min INTEGER")
    add_column_if_missing(conn, "tenant_profiles", "rooms_max INTEGER")
    add_column_if_missing(conn, "tenant_profiles", "floor_min INTEGER")
    add_column_if_missing(conn, "tenant_profiles", "floor_max INTEGER")
    add_column_if_missing(conn, "tenant_profiles", "price_min INTEGER")
    add_column_if_missing(conn, "tenant_profiles", "price_max INTEGER")
    # NEW: OSM reference columns
    add_column_if_missing(conn, "tenant_profiles", "search_city_osm_id INTEGER")
    add_column_if_missing(conn, "tenant_profiles", "search_district_osm_id INTEGER")
    add_column_if_missing(conn, "tenant_profiles", "search_city_osm_type TEXT")
    add_column_if_missing(conn, "tenant_profiles", "search_district_osm_type TEXT")
    # --- Landlord->Tenant pending request flags on contacts
    add_column_if_missing(conn, "future_landlord_contacts", "inbound_request INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "future_landlord_contacts", "inbound_requested_at TEXT")
    


    conn.execute("CREATE INDEX IF NOT EXISTS idx_flc_tenant_email ON future_landlord_contacts(tenant_id, email)")
    conn.commit()


    # Landlord ↔ Tenant connections (for “future landlord” flow)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS future_landlord_connections (
    landlord_id INTEGER NOT NULL,
    tenant_id   INTEGER NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('connected','rejected')),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (landlord_id, tenant_id)
    )
    """)
    conn.commit()
    
    # --- Landlord properties (for Landlord Dashboard > My Properties)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS landlord_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_id INTEGER NOT NULL,
    address TEXT NOT NULL,
    listing_url TEXT,
    visible_to_tenants INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
    )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_landlord_properties_landlord ON landlord_properties(landlord_id)")
    conn.commit()
    
    # --- Landlord properties: extra metadata ---
    add_column_if_missing(conn, "landlord_properties", "region TEXT")
    add_column_if_missing(conn, "landlord_properties", "district TEXT")
    add_column_if_missing(conn, "landlord_properties", "city TEXT")
    add_column_if_missing(conn, "landlord_properties", "size_m2 INTEGER")
    add_column_if_missing(conn, "landlord_properties", "rooms INTEGER")
    add_column_if_missing(conn, "landlord_properties", "floor INTEGER")
    add_column_if_missing(conn, "landlord_properties", "price INTEGER")
    conn.commit()





        
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
            role TEXT CHECK(role IN ("tenant","landlord","admin")) NOT NULL,
            created_at TEXT NOT NULL
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

conn = init_db()

# Run lightweight migrations so old DBs gain new columns
try:
    run_migrations(conn)
except Exception as e:
    st.warning(f"DB migration warning: {e}")

def add_future_landlord_contact(tenant_id: int, email: str):
    email = (email or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError("Invalid email")

    conn = get_conn()
    cur = conn.cursor()

    # 1) Insert (or update timestamp if already there)
    cur.execute("""
        INSERT INTO future_landlord_contacts (tenant_id, email, created_at, invited)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(tenant_id, email)
        DO UPDATE SET created_at=excluded.created_at
    """, (tenant_id, email, datetime.utcnow().isoformat()))
    conn.commit()

    # 2) If this email belongs to a registered landlord and there is an old 'rejected' link,
    #    remove it so the UI no longer auto-hides this contact.
    landlord_user_id = get_user_id_by_email(email)
    if landlord_user_id:
        cur.execute(
            "DELETE FROM future_landlord_connections WHERE landlord_id=? AND tenant_id=? AND status='rejected'",
            (landlord_user_id, tenant_id)
        )
        conn.commit()



def _table_has_column(conn_or_none, table: str, column: str) -> bool:
    c = conn_or_none or get_conn()
    cur = c.execute(f"PRAGMA table_info({table})")
    return any(row[1].lower() == column.lower() for row in cur.fetchall())

def list_future_landlord_contacts(tenant_id: int):
    """
    Always returns 7 columns:
    (id, email, created_at, invited, invited_at, inbound_request, inbound_requested_at)
    """
    c = get_conn()
    cur = c.cursor()
    has_inbound = _table_has_column(c, "future_landlord_contacts", "inbound_request")

    if has_inbound:
        cur.execute(
            """
            SELECT id, email, created_at, invited, invited_at, inbound_request, inbound_requested_at
            FROM future_landlord_contacts
            WHERE tenant_id = ?
            ORDER BY id DESC
            """,
            (tenant_id,),
        )
        return cur.fetchall()
    else:
        cur.execute(
            """
            SELECT id, email, created_at, invited, invited_at
            FROM future_landlord_contacts
            WHERE tenant_id = ?
            ORDER BY id DESC
            """,
            (tenant_id,),
        )
        base = cur.fetchall()
        return [(id_, em, cr, inv, inv_at, 0, None) for (id_, em, cr, inv, inv_at) in base]

def has_inbound_request(tenant_id: int, landlord_email: str) -> bool:
    c = get_conn()
    if not _table_has_column(c, "future_landlord_contacts", "inbound_request"):
        return False
    row = c.execute(
        "SELECT inbound_request FROM future_landlord_contacts WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, landlord_email)
    ).fetchone()
    return bool(row and row[0])

def flc_request_connect(landlord_id: int, tenant_id: int) -> None:
    """Landlord -> Tenant: create a pending request visible to both sides."""
    c = get_conn()
    landlord = get_user_by_id(landlord_id)
    if not landlord:
        return
    add_future_landlord_contact(tenant_id, landlord["email"])
    now = _now_iso()
    c.execute(
        """
        UPDATE future_landlord_contacts
        SET inbound_request=1, inbound_requested_at=?
        WHERE tenant_id=? AND LOWER(email)=LOWER(?)
        """,
        (now, tenant_id, landlord["email"]),
    )
    c.commit()

def flc_cancel_request(landlord_id: int, tenant_id: int) -> None:
    c = get_conn()
    landlord = get_user_by_id(landlord_id)
    if not landlord:
        return
    c.execute(
        "UPDATE future_landlord_contacts SET inbound_request=0, inbound_requested_at=NULL "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
        (tenant_id, landlord["email"])
    )
    c.commit()

def flc_get_status(landlord_id: int, tenant_id: int):
    """
    Returns 'connected' | 'rejected' | None from future_landlord_connections.
    """
    if not landlord_id or not tenant_id:
        return None
    c = get_conn()
    row = c.execute(
        "SELECT status FROM future_landlord_connections WHERE landlord_id=? AND tenant_id=?",
        (landlord_id, tenant_id)
    ).fetchone()
    return row[0] if row else None

def _upsert_connection(landlord_id: int, tenant_id: int, status: str):
    now = _now_iso()
    c = get_conn()
    # insert or update
    c.execute(
        """
        INSERT INTO future_landlord_connections (landlord_id, tenant_id, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(landlord_id, tenant_id)
        DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at
        """,
        (landlord_id, tenant_id, status, now, now),
    )
    c.commit()

def flc_connect(landlord_id: int, tenant_id: int):
    _upsert_connection(landlord_id, tenant_id, "connected")
    # clear pending flags if any
    c = get_conn()
    landlord = get_user_by_id(landlord_id)
    if landlord:
        c.execute(
            "UPDATE future_landlord_contacts SET inbound_request=0, inbound_requested_at=NULL "
            "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
            (tenant_id, landlord["email"])
        )
        c.commit()

def flc_reject(landlord_id: int, tenant_id: int):
    _upsert_connection(landlord_id, tenant_id, "rejected")
    # clear pending flags if any
    c = get_conn()
    landlord = get_user_by_id(landlord_id)
    if landlord:
        c.execute(
            "UPDATE future_landlord_contacts SET inbound_request=0, inbound_requested_at=NULL "
            "WHERE tenant_id=? AND LOWER(email)=LOWER(?)",
            (tenant_id, landlord["email"])
        )
        c.commit()

def flc_disconnect(landlord_id: int, tenant_id: int):
    # In your current model, "disconnect" maps to 'rejected'
    flc_reject(landlord_id, tenant_id)

def flc_list_inbound_for_tenant(tenant_id: int):
    """
    Rows = (contact_id, email, inbound_requested_at) for landlord-origin pending requests.
    """
    c = get_conn()
    if not _table_has_column(c, "future_landlord_contacts", "inbound_request"):
        return []
    return c.execute(
        """
        SELECT id, email, inbound_requested_at
        FROM future_landlord_contacts
        WHERE tenant_id=? AND inbound_request=1
        ORDER BY (inbound_requested_at IS NULL) ASC, inbound_requested_at DESC
        """,
        (tenant_id,),
    ).fetchall()
    
def flc_list_prospective_for_landlord(landlord_id: int):
    """
    Rows = (tenant_id, invited, invited_at, inbound_request, inbound_requested_at)
    Includes:
      - tenant-origin pending (invited=1)
      - landlord-origin pending (inbound_request=1)
      - connected (from future_landlord_connections)
    """
    c = get_conn()
    landlord = get_user_by_id(landlord_id)
    if not landlord:
        return []

    email = (landlord.get("email") or "").strip().lower()
    if not email:
        return []

    # Add LEFT JOIN to connections and include x.status='connected'
    rows = c.execute(
        """
        SELECT c.tenant_id, c.invited, c.invited_at, c.inbound_request, c.inbound_requested_at
        FROM future_landlord_contacts AS c
        LEFT JOIN future_landlord_connections AS x
               ON x.landlord_id = ? AND x.tenant_id = c.tenant_id
        WHERE LOWER(c.email) = ?
          AND (c.invited = 1 OR c.inbound_request = 1 OR x.status = 'connected')
        ORDER BY COALESCE(c.inbound_requested_at, c.invited_at, x.updated_at) DESC
        """,
        (landlord_id, email),
    ).fetchall()

    return rows or []

def tenant_has_invited(tenant_id: int, landlord_email: str) -> bool:
    """Did the tenant add this landlord and send an invite? (tenant-origin pending)"""
    c = get_conn()
    row = c.execute(
        "SELECT 1 FROM future_landlord_contacts "
        "WHERE tenant_id=? AND LOWER(email)=LOWER(?) AND invited=1 LIMIT 1",
        (tenant_id, landlord_email),
    ).fetchone()
    return bool(row)

def flc_relation_status(landlord_id: int, tenant_id: int, landlord_email: str):
    """
    Returns a pair: (label, extra)
      label ∈ {'connected','pending','disconnected', None}
      extra  ∈ {'outbound','inbound', None}  # for pending
    Priority: pending (outbound OR inbound) > connected > disconnected > none
    """
    # 1) pending?
    try:
        outbound = has_inbound_request(tenant_id, landlord_email)  # landlord -> tenant
    except Exception:
        outbound = False
    try:
        inbound = tenant_has_invited(tenant_id, landlord_email)    # tenant -> landlord
    except Exception:
        inbound = False
    if outbound:
        return "pending", "outbound"
    if inbound:
        return "pending", "inbound"

    # 2) final states from connections table
    try:
        st = flc_get_status(landlord_id, tenant_id)  # 'connected'|'rejected'|None
    except Exception:
        st = None
    if st == "connected":
        return "connected", None
    if st == "rejected":
        return "disconnected", None

    return None, None


def remove_future_landlord_contact(contact_id: int, tenant_id: int):
    cur = get_conn().cursor()
    cur.execute(
        "DELETE FROM future_landlord_contacts WHERE id = ? AND tenant_id = ?",
        (contact_id, tenant_id),
    )
    get_conn().commit()


def invite_future_landlord(tenant_id: int, email: str, tenant_name: str, tenant_email: str):
    base = st.session_state.get("app_base_url") or (st.secrets.get("APP_BASE_URL") if hasattr(st, "secrets") else "")
    join_link = base if base else ""

    subject = f"Πρόσκληση στο RentRight από τον/την {tenant_name}"

    body = (
        "Καλησπέρα σας,\n\n"
        f"Ο/Η {tenant_name} ({tenant_email}) σας πρόσθεσε ως μελλοντικό/ή ιδιοκτήτη/ιδιοκτήτρια στο RentRight.\n"
        "Με αυτόν τον τρόπο επιθυμεί να παραμείνετε σε επαφή για πιθανή μελλοντική μίσθωση.\n\n"
        "Τι μπορείτε να κάνετε:\n"
        "- Συνδεθείτε ή δημιουργήστε έναν λογαριασμό στο RentRight, ώστε να ενημερώνεστε εύκολα και με ασφάλεια.\n"
        + (f"\nΣύνδεσμος πρόσβασης:\n{join_link}\n" if join_link else "")
        + (
            "\nΑν ο σύνδεσμος δεν εμφανίζεται, επισκεφθείτε την αρχική σελίδα του RentRight και συνδεθείτε/εγγραφείτε.\n"
            if not join_link else ""
        )
        + "\nΓια οποιαδήποτε απορία, μπορείτε να απαντήσετε απευθείας σε αυτό το email.\n\n"
        "Σας ευχαριστούμε,\n"
        "Η ομάδα RentRight"
    )

    ok, msg = send_email_smtp(email, subject, body)
    if ok:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE future_landlord_contacts SET invited = 1, invited_at = ? WHERE tenant_id = ? AND LOWER(email) = LOWER(?)",
            (datetime.utcnow().isoformat(), tenant_id, email),
        )
        conn.commit()
    return ok, msg




# ---------- Auth helpers ----------
def hash_password(password: str, salt: str = "static_salt_change_me") -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()

def create_user(email: str, name: str, password: str, role: str):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users(email, name, password_hash, role, created_at) VALUES (?,?,?,?,?)",
        (email.lower().strip(), name.strip(), hash_password(password), role, datetime.utcnow().isoformat()),
    )
    conn.commit()


def get_user_by_email(email: str):
    cur = conn.cursor()
    cur.execute("SELECT id, email, name, password_hash, role FROM users WHERE email = ?", (email.lower().strip(),))
    row = cur.fetchone()
    if row:
        keys = ["id","email","name","password_hash","role"]
        return dict(zip(keys, row))
    return None

# Starts here

def _table_has_column(table: str, col: str) -> bool:
    try:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        return col in cols
    except Exception:
        return False

def clear_tenant_future_landlord(tenant_id: int, landlord_email: str | None = None):
    """
    Clears the 'future landlord' reference from the tenant's profile so:
      - they no longer appear under Prospective Tenants
      - their own dashboard no longer shows the future landlord
    Works defensively: updates only the columns that exist.
    If landlord_email is provided and a matching email column exists, we match on it.
    """
    if not _table_has_column("tenant_profiles", "tenant_id"):
        return  # nothing to do

    # Candidate columns that might be present in your schema
    email_cols = ["future_landlord_email", "future_landlord"]      # pick whichever exists
    extra_cols = ["future_landlord_name", "future_landlord_phone",
                  "future_landlord_note", "future_landlord_status",
                  "future_landlord_updated_at"]

    # Build SET clause only for columns that exist
    set_bits = []
    for c in email_cols + extra_cols:
        if _table_has_column("tenant_profiles", c):
            set_bits.append(f"{c}=NULL")

    if not set_bits:
        return  # no known columns to clear

    # WHERE clause: by tenant_id; optionally match email if both landlord_email and email column exist
    where = "tenant_id=?"
    params = [tenant_id]

    match_col = next((c for c in email_cols if _table_has_column("tenant_profiles", c)), None)
    if landlord_email and match_col:
        # only clear if the stored email equals this landlord (protects against accidental clearing)
        where += f" AND ({match_col} IS NULL OR {match_col} = ?)"
        params.append(landlord_email)

    sql = f"UPDATE tenant_profiles SET {', '.join(set_bits)} WHERE {where}"
    conn.execute(sql, tuple(params))
    conn.commit()


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
    # OSM metadata (now includes types)
    city_osm_id: int | None = None,
    city_osm_type: str | None = None,          # "node" | "way" | "relation"
    district_osm_id: int | None = None,
    district_osm_type: str | None = None,      # "node" | "way" | "relation"
):
    ensure_tenant_profile_row(tenant_id)
    now = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE tenant_profiles
           SET open_to_rent=?,
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
    JOIN users u ON u.id = lp.landlord_id AND u.role = 'landlord'
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


def tenant_open_to_rent_section():
    st.subheader(tr("Open to Rent"))

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
    # Defaults for summary
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

        
                # Active / Inactive
        open_flag = st.checkbox(
            tr("I'm currently looking for a place"),
            key="otr_open_flag",
        )

        # REGION
        region_options = [ANY] + (regions or [])
        region_index = (region_options.index(pre_region) if (pre_region in region_options and not reset_preselect) else 0)
        region_sel = st.selectbox("Περιφέρεια", options=region_options, index=region_index, key="loc_region")

        # REGIONAL UNIT (depends on Region)
        units = list_units(data, region_sel) if (region_sel and region_sel != ANY) else []
        unit_options = [ANY] + (units or [])
        unit_index = (unit_options.index(pre_unit) if (pre_unit in unit_options and not reset_preselect) else 0)
        unit_sel = st.selectbox("Περιφερειακή Ενότητα", options=unit_options, index=unit_index, key="loc_unit")

        # MUNICIPALITY (depends on Unit)
        municipalities = list_municipalities(data, region_sel, unit_sel) if (region_sel and region_sel != ANY and unit_sel and unit_sel != ANY) else []
        city_options = [ANY] + (municipalities or [])
        city_index = (city_options.index(saved_city) if (saved_city in city_options and not reset_preselect) else 0)
        city_sel = st.selectbox("Δήμος (Πόλη)", options=city_options, index=city_index, key="loc_city")

        # Map to your schema (don’t save “Any” — treat as empty)
        region   = "" if region_sel == ANY else region_sel
        district = "" if unit_sel   == ANY else unit_sel
        city     = "" if city_sel   == ANY else city_sel

        c1, c2 = st.columns(2)
        size_min = c1.number_input(tr("Min size (m²)"), 0, 10000, key="otr_size_min")
        size_max = c2.number_input(tr("Max size (m²)"), 0, 10000, key="otr_size_max")

        r1, r2 = st.columns(2)
        rooms_min = r1.number_input(tr("Min rooms"), 0, 50, key="otr_rooms_min")
        rooms_max = r2.number_input(tr("Max rooms"), 0, 50, key="otr_rooms_max")

        f1, f2 = st.columns(2)
        floor_min = f1.number_input(tr("Min floor"), -5, 100, key="otr_floor_min")
        floor_max = f2.number_input(tr("Max floor"), -5, 100, key="otr_floor_max")

        p1, p2 = st.columns(2)
        price_min = p1.number_input(tr("Min price (€)"), 0, 1_000_000, key="otr_price_min")
        price_max = p2.number_input(tr("Max price (€)"), 0, 1_000_000, key="otr_price_max")
        


        # ---- Save / Reset -------------------------------------------------------
        col_save, col_reset = st.columns([1, 1])

        if col_save.button(tr("Save")):
            city_clean = "" if (city == "—") else (city or "")
            district_clean = "" if (district == "—") else (district or "")
            if not city_clean and not district_clean:
                st.warning(tr("Please enter at least a city or a district."))
            else:
                try:
                    save_open_to_rent_prefs(
                        tid, bool(st.session_state["otr_open_flag"]),
                        city_clean, district_clean,
                        int(st.session_state["otr_size_min"]), int(st.session_state["otr_size_max"]),
                        int(st.session_state["otr_rooms_min"]), int(st.session_state["otr_rooms_max"]),
                        int(st.session_state["otr_floor_min"]), int(st.session_state["otr_floor_max"]),
                        int(st.session_state["otr_price_min"]), int(st.session_state["otr_price_max"]),
                        city_osm_id=None, city_osm_type=None,
                        district_osm_id=None, district_osm_type=None,
                    )
                except TypeError:
                    save_open_to_rent_prefs(
                        tid, bool(st.session_state["otr_open_flag"]),
                        city_clean, district_clean,
                        int(st.session_state["otr_size_min"]), int(st.session_state["otr_size_max"]),
                        int(st.session_state["otr_rooms_min"]), int(st.session_state["otr_rooms_max"]),
                        int(st.session_state["otr_floor_min"]), int(st.session_state["otr_floor_max"]),
                        int(st.session_state["otr_price_min"]), int(st.session_state["otr_price_max"]),
                    )
                try:
                    st.cache_data.clear()
                except Exception:
                    pass
                st.success(tr("Preferences saved!"))

        if col_reset.button(tr("Reset")):
            for k in ("loc_region","loc_unit","loc_city",
                    "otr_open_flag",
                    "otr_size_min","otr_size_max",
                    "otr_rooms_min","otr_rooms_max",
                    "otr_floor_min","otr_floor_max",
                    "otr_price_min","otr_price_max",
                    "otr_keys_inited"):
                st.session_state.pop(k, None)

            st.session_state["otr_force_defaults"]  = True
            st.session_state["otr_reset_preselect"] = True
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
        role = st.selectbox(tr('Role'), ["tenant","landlord"], format_func=lambda x: x.capitalize())
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
        if password != password2:
            st.error(tr('Passwords do not match. Please try again.'))
            return
        if get_user_by_email(email):
            st.error(tr('This email is already registered.'))
            return
        create_user(email, name, password, role)
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
    if st.button(tr('Sign Out')):
        st.session_state.user = None
        st.rerun()

# ---------- Tenant data helpers ----------

# UPLOAD_DIR = Path("uploads") / "contracts"

def get_user_id_by_email(email: str) -> int | None:
    if not email:
        return None
    row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    return row[0] if row else None


# Pick a writable base directory
if Path("/mount/data").exists():
    WRITABLE_BASE = Path("/mount/data")
else:
    WRITABLE_BASE = Path(tempfile.gettempdir())

# Define uploads/contracts inside that base
UPLOAD_DIR = WRITABLE_BASE / "uploads" / "contracts"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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

# ---------- References helpers ----------
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
    """
    Returns the 'effective' status for showing in UI:
      - 'cancelled' stays cancelled.
      - If a contract exists but is not VERIFIED, treat the reference as 'pending'.
      - Otherwise return the raw status, defaulting to 'pending' when None.
    """
    if raw_status == "cancelled":
        return "cancelled"
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

def _table_has_column(conn, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1].lower() == column.lower() for row in cur.fetchall())

#     pl.afm AS prev_afm,
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



def build_reference_link(token: str) -> str:
    base = st.session_state.get("app_base_url") or (st.secrets.get("APP_BASE_URL") if hasattr(st, "secrets") else "")
    if base:
        base = base.strip().rstrip("/")
        return f"{base}/?ref={token}"
    # fallback that still works when clicked inside the app
    return f"?ref={token}"


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


# ---------- Landlord Reference Portal (public) ----------


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
    
def search_open_to_rent_tenants(
    q: str | None = None,
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

    # Free-text on users.name / users.email
    if q:
        clauses.append("(LOWER(u.name) LIKE LOWER(:q) OR LOWER(u.email) LIKE LOWER(:q))")
        params["q"] = f"%{q.strip()}%"

    # Exact matches on location preferences (stored strings)
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



def admin_dashboard():
    # periodic cleanup on admin view
    try:
        cleanup_old_contracts()
    except Exception:
        pass
    st.header(tr('Administrator Dashboard'))
    st.caption(f"Logged in as {st.session_state.user['email']}")

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
    cancelled_reqs = [r for r in all_reqs if eff(r) == "cancelled"]

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

                link = build_reference_link(token)
                st.text_input(tr('Reference Link'), value=link, key=f"{prefix}_link_{token}", disabled=True)

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


                # --- Admin actions (conditional) ---
                ac1, ac2 = st.columns(2)

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
    logout_button()

    
def tenant_dashboard():
    col_h1, col_h2, col_h3 = st.columns([5,1,2])
    with col_h1: st.header(tr('Tenant Dashboard'))
    with col_h2:
        if st.button("🔄", key="tenant_refresh"):
            st.rerun()
    with col_h3: logout_button()
    
    def tenant_future_landlords_section():
        """
        Tenant dashboard: manage 'Future Landlords (Contacts)'.
        - Namespaced widget keys to avoid Streamlit duplicate-key errors.
        - Shows landlord name (if available) + email.
        """
        st.subheader(tr("Future Landlords (Contacts)"))


        tenant_id = st.session_state.user["id"]
        
        def _clear_transient_search_flags():
            for k in list(st.session_state.keys()):
                if k.startswith(("ld_otr_", "otr_", "prospects")):
                    del st.session_state[k]

        # Namespace for widget keys in this section
        NS = "tfl"
        def k(cid, name):
            return f"{NS}:{name}:{cid}"

         # --- Search landlords by name or email (PARTIAL) ----------------------------
        with st.container(border=True):
            st.markdown(f"**{tr('Search landlords by name or email')}**")
            q = st.text_input(
                tr("Type a name, surname, or email"),
                key=f"{NS}:search_q",
                placeholder=tr("e.g. Maria Papadopoulou or papadop"),
            )

            if q and len(q.strip()) >= 2:
                try:
                    results = search_landlords_by_name_or_email(q, limit=25)
                except Exception:
                    results = []
                    st.warning(tr("Search is temporarily unavailable."))

                if not results:
                    st.caption(tr("No matches found."))
                else:
                    for (ll_id, ll_name, ll_email) in results:
                        # relation/contacts state
                        try:
                            rel_status = flc_get_status(ll_id, tenant_id)  # 'connected' | 'rejected' | None
                        except Exception:
                            rel_status = None

                        c = get_conn()
                        rowc = c.execute(
                            "SELECT id, invited, inbound_request FROM future_landlord_contacts "
                            "WHERE tenant_id=? AND LOWER(email)=LOWER(?) LIMIT 1",
                            (tenant_id, (ll_email or "").strip().lower()),
                        ).fetchone()
                        in_contacts = bool(rowc)
                        invited = int(rowc[1]) if rowc else 0
                        inbound_req = int(rowc[2]) if rowc else 0

                        with st.container(border=True):
                            cols = st.columns([5, 3, 4])

                            # Left: identity
                            title = (ll_name or ll_email or f"Landlord #{ll_id}").strip()
                            cols[0].markdown(f"**{title}**")
                            if ll_name and ll_email:
                                cols[0].caption(ll_email)

                            # Middle: status badge
                            if rel_status == "connected":
                                cols[1].success(tr("Connected"))
                            elif rel_status == "rejected":
                                cols[1].error(tr("Rejected"))
                            elif inbound_req:
                                cols[1].info(tr("Pending"))
                            elif invited:
                                cols[1].info(tr("Invited"))
                            elif in_contacts:
                                cols[1].caption(tr("In contacts"))
                            else:
                                cols[1].caption(tr("No relation"))

                            # Right: action
                            if in_contacts:
                                cols[2].caption(tr("Already in contacts"))
                            else:
                                if cols[2].button(tr("Add Contact"), key=k(ll_id, "search_add")):
                                    try:
                                        add_future_landlord_contact(tenant_id, ll_email)
                                        try: st.cache_data.clear()
                                        except Exception: pass
                                        st.success(tr("Contact added."))
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"{tr('Unable to add contact')}: {e}")
                                        

        # Friendly hint between search and add-by-email
        st.caption(tr("If you can’t find the landlord above, send a request to connect by email."))
        
        with st.expander("send a request to connect by email", expanded=False):
            # --- Add Contact (request to connect by email) ------------------------------
            with st.form(f"{NS}:add_contact_form", clear_on_submit=True):
                new_email = st.text_input(
                    tr("Landlord email"),
                    key=f"{NS}:new_email",
                    placeholder="name@example.com",
                )
                col_a, _ = st.columns([3, 6])
                submitted = col_a.form_submit_button(tr("Add Contact"))
                if submitted:
                    email = (new_email or "").strip()
                    if not email or "@" not in email:
                        st.error(tr("Please enter a valid email address."))
                    else:
                        try:
                            add_future_landlord_contact(tenant_id, email)
                            try: st.cache_data.clear()
                            except Exception: pass
                            _clear_transient_search_flags()
                            st.success(tr("Contact added."))
                            st.rerun()
                        except Exception as e:
                            st.error(f"{tr('Unable to add contact')}: {e}")

    def tenant_contancts():
        st.subheader(tr('Contacts'))

        # CSS every run
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

        _ensure_tfl_css()

        # Namespace + key builder (LOCAL to this function)
        NSC = "tfl_contacts"
        def k(cid, name):
            return f"{NSC}:{name}:{cid}"

        def _initials(name, email):
            base = (name or "").strip() or (email or "").split("@")[0]
            parts = [p for p in base.replace(".", " ").split() if p]
            if len(parts) >= 2: return (parts[0][0]+parts[1][0]).upper()
            if parts: return parts[0][:2].upper()
            return "?"

        def _clear_transient_search_flags():
            for key in list(st.session_state.keys()):
                if key.startswith(("ld_otr_", "otr_", "prospects")):
                    del st.session_state[key]

        tenant_id = st.session_state.user["id"]

        rows = list_future_landlord_contacts(tenant_id) or []
        if not rows:
            st.caption(tr("No future landlord contacts yet."))
            return

        for (cid, fl_email, created_at, invited, invited_at, inbound_request, inbound_requested_at) in rows:
            with st.container(border=True):
                landlord_user = get_user_by_email(fl_email)
                landlord_id = landlord_user["id"] if landlord_user and landlord_user.get("role") == "landlord" else None
                landlord_name = (landlord_user.get("name") or "").strip() if landlord_user else ""

                try:
                    status = flc_get_status(landlord_id, tenant_id) if landlord_id else None
                except Exception:
                    status = None

                colL, colM, colR = st.columns([6, 3, 3])

                display_title = landlord_name or fl_email
                initials = _initials(landlord_name, fl_email)
                meta_bits = []
                if landlord_name and fl_email: meta_bits.append(fl_email)
                if created_at: meta_bits.append(tr("Added") + f": {created_at}")
                if invited and invited_at: meta_bits.append(tr("Invited on") + f" {invited_at}")
                if inbound_request and inbound_requested_at: meta_bits.append(tr("Requested on") + f" {inbound_requested_at}")
                meta_line = " · ".join(meta_bits)

                colL.markdown(
                    f"""
                    <div class="tfl-title">
                    <div class="tfl-avatar">{initials}</div>
                    <div>
                        <div class="tfl-name">{display_title}</div>
                        <div class="tfl-email">{'' if landlord_name else ''}<a href="mailto:{fl_email}">{fl_email}</a></div>
                    </div>
                    </div>
                    <div class="tfl-meta">{meta_line}</div>
                    """,
                    unsafe_allow_html=True
                )

                # badges
                if status == "connected":
                    colM.markdown(f'<span class="tfl-badge tfl-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
                elif status == "rejected":
                    colM.markdown(f'<span class="tfl-badge tfl-badge--err">{tr("Rejected")}</span>', unsafe_allow_html=True)
                elif inbound_request:
                    colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)
                elif invited:
                    colM.markdown(f'<span class="tfl-badge tfl-badge--info">{tr("Invited")}</span>', unsafe_allow_html=True)
                else:
                    colM.markdown(f'<span class="tfl-badge">{tr("Not connected")}</span>', unsafe_allow_html=True)

                # actions
                if status == "connected":
                    if colR.button(tr("Disconnect"), key=k(cid, "disconnect_connected")):
                        if landlord_id: flc_disconnect(landlord_id, tenant_id)
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.warning(tr("Disconnected."))
                        _clear_transient_search_flags()
                        st.rerun()

                elif inbound_request:
                    b1, b2 = colR.columns(2)
                    if b1.button(tr("Connect"), key=k(cid, "accept_inbound")):
                        if landlord_id: flc_connect(landlord_id, tenant_id)
                        c = get_conn()
                        c.execute("UPDATE future_landlord_contacts SET inbound_request=0, inbound_requested_at=NULL WHERE id=?", (cid,))
                        c.commit()
                        try: st.cache_data.clear()
                        except Exception: pass
                        _clear_transient_search_flags()
                        st.success(tr("Connected."))
                        st.rerun()
                    if b2.button(tr("Disconnect"), key=k(cid, "decline_inbound")):
                        if landlord_id: flc_reject(landlord_id, tenant_id)
                        c = get_conn()
                        c.execute("UPDATE future_landlord_contacts SET inbound_request=0, inbound_requested_at=NULL WHERE id=?", (cid,))
                        c.commit()
                        try: st.cache_data.clear()
                        except Exception: pass
                        _clear_transient_search_flags()
                        st.info(tr("Disconnected."))
                        st.rerun()

                elif invited:
                    if colR.button(tr("Remove"), key=k(cid, "remove_invited")):
                        remove_future_landlord_contact(cid, tenant_id)
                        try: st.cache_data.clear()
                        except Exception: pass
                        _clear_transient_search_flags()
                        st.info(tr("Contact removed."))
                        st.rerun()

                else:
                    b1, b2 = colR.columns(2)
                    if b1.button(tr("Send Invitation"), key=k(cid, "send_invite_plain")):
                        ok, msg = invite_future_landlord(
                            tenant_id, fl_email,
                            st.session_state.user.get("name"),
                            st.session_state.user.get("email"),
                        )
                        if ok:
                            try: st.cache_data.clear()
                            except Exception: pass
                            _clear_transient_search_flags()
                            st.success(tr("Invitation sent successfully."))
                            st.rerun()
                        else:
                            st.error(f"{tr('Unable to send invitation')}: {msg}")
                    if b2.button(tr("Remove"), key=k(cid, "remove_plain")):
                        remove_future_landlord_contact(cid, tenant_id)
                        try: st.cache_data.clear()
                        except Exception: pass
                        _clear_transient_search_flags()
                        st.info(tr("Contact removed."))
                        st.rerun()

                # visible properties (unchanged render)...
                if landlord_id:
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
                                    <div class="prop-foot">{tr('Updated')}: {upd}{link_html}</div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )


    
    
    tenant_future_landlords_section()
    
    tenant_contancts()
    
    tenant_open_to_rent_section()

    
    # === Previous landlords + reference requests ===
    st.subheader(tr('Previous Landlords and References'))
    with st.form("previous_landlord_form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            pl_email = st.text_input(tr('Email'))
            # pl_afm = st.text_input(tr('Tax ID (9 digits)'))
        with col2:
            pl_name = st.text_input(tr('Name'))
            pl_address = st.text_input(tr('Address'))
        add = st.form_submit_button(tr('Add Previous Landlord'))
    if add:
        if not (pl_email and is_valid_email(pl_email)):
            st.error(tr('Please enter a valid email address.'))
        # elif not is_valid_afm(pl_afm):
        #     st.error(tr('Tax ID must be exactly 9 digits.'))
        elif not pl_name.strip():
            st.error(tr('Please enter your full name.'))
        elif not pl_address.strip():
            st.error(tr('Please enter the landlord’s address.'))
        else:
            add_previous_landlord(st.session_state.user["id"], pl_email, pl_name, pl_address) # pl_afm,
            st.success(tr('Previous landlord added successfully.'))

    rows = list_previous_landlords(st.session_state.user["id"]) or []
    st.subheader(tr('All Reference Requests'))
    if rows:
        for (pid, email, name, address, created_at) in rows: # afm,
            with st.expander(f"{name} • {email} • {address} ", False):

                # --- Load all requests for this landlord
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
                suppress_key = f'suppress_autodraft_{pid}'

                # ⛔️ Do NOT auto-create here — we want Start/Delete if nothing is active.

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
                        # ✅ Show completed summary (do NOT show Start/Delete)
                        details = get_reference_request_by_token(latest_tok)
                        contract_i = get_contract_by_token(latest_tok)

                        # Contract status
                        if contract_i:
                            st.markdown(f"**{tr('Contract Status:')}** {contract_status_badge(contract_i['status'])}")
                        else:
                            st.markdown(f"**{tr('Contract Status:')}** {tr('✅ Verified Contract')}")

                        # Answers
                        if details:
                            st.write(f"**{tr('Overall tenant score')}:** {details.get('score')}/10")
                            st.write(f"**{tr('Did the tenant pay on time?')}:** {tr('Yes') if details.get('paid_on_time') else tr('No')}")
                            st.write(f"**{tr('Did the tenant leave utilities unpaid?')}:** {tr('Yes') if details.get('utilities_unpaid') else tr('No')}")
                            st.write(f"**{tr('Did the tenant leave the apartment in good condition?')}:** {tr('Yes') if details.get('good_condition') else tr('No')}")
                            if details.get('comments'):
                                st.write("**" + tr('Optional comments') + ":**")
                                st.write(details['comments'])

                        # Optional download if consented
                        if contract_i:
                            try:
                                data_plain_i = load_contract_plaintext(latest_tok)
                                if data_plain_i is None:
                                    st.warning(tr('Contract is locked awaiting landlord consent.'))
                                else:
                                    st.download_button(
                                        tr('Download Contract'),
                                        data=data_plain_i,
                                        file_name=contract_i['filename'],
                                        mime=contract_i.get('content_type') or contract_i.get('mime_type'),
                                        key=f"dl_{latest_tok}",
                                    )
                            except Exception as e:
                                st.warning(f"{tr('Unable to read the saved file:')} {e}")

                    else:
                        # No requests OR latest was cancelled → show Start/Delete
                        st.caption(tr('No active reference request.'))
                        col_start, col_delete = st.columns([1, 1])

                        # Start
                        if col_start.button(tr('Start New Reference Request'), key=f"start_{pid}"):
                            rec = create_reference_request(st.session_state.user["id"], pid, email)
                            st.session_state.pop(suppress_key, None)
                            st.rerun()

                        # Delete (2-step)
                        del_confirm_key = f"confirm_delete_prev_{pid}"
                        if st.session_state.get(del_confirm_key, False):
                            st.warning(tr('Are you sure you want to delete this previous landlord and all related data?'))
                            col_yes, col_no = st.columns([1, 1])
                            if col_yes.button(tr('Yes, delete'), key=f"yes_del_prev_{pid}"):
                                try:
                                    delete_previous_landlord_completely(st.session_state.user["id"], pid)
                                    st.success(tr('Previous landlord deleted permanently.'))
                                except Exception as e:
                                    st.error(f"{tr('Unable to delete')}: {e}")
                                finally:
                                    st.session_state.pop(del_confirm_key, None)
                                st.rerun()
                            if col_no.button(tr('No, keep it'), key=f"no_del_prev_{pid}"):
                                st.session_state.pop(del_confirm_key, None)
                                st.rerun()
                        else:
                            if col_delete.button(tr('Delete Previous Landlord'), key=f"del_prev_{pid}"):
                                st.session_state[del_confirm_key] = True
                                st.rerun()

                    continue

                # Now we have an active request token we can use for uploads
                tok, status, created_at2, score = active_req
                final_status = effective_reference_status(status, tok)

                # NEW: check if we already sent the email
                row = conn.execute("SELECT emailed_at FROM reference_requests WHERE token=?", (tok,)).fetchone()
                emailed_at = row[0] if row else None
                final_norm = str(final_status).strip().lower()

                # Only allow requesting if we haven't emailed yet and it's not final
                can_request = (emailed_at is None) and (final_norm not in ("completed", "cancelled"))

                contract = get_contract_by_token(tok)

                # Layout: left = upload flow; right = history
                c_left, c_right = st.columns([1, 2])
                
                with c_left:
                    if contract:
                        # Show current contract info + download + replace-uploader
                        consent_row2 = conn.cursor().execute(
                            "SELECT consent_status FROM reference_contracts WHERE token=?",
                            (tok,)
                        ).fetchone()
                        consent_badge2 = f"Consent: {consent_row2[0] if consent_row2 else 'locked'}"

                        try:
                            data_plain = load_contract_plaintext(tok)
                            if data_plain is None:
                                st.warning(tr('Contract is locked awaiting landlord consent.'))
                            else:
                                st.download_button(
                                    tr('Download Contract'),
                                    data=data_plain,
                                    file_name=contract['filename'],
                                    mime=contract.get('content_type') or contract.get('mime_type'),
                                    key=f"dl_{tok}",
                                )
                        except Exception as e:
                            st.warning(f"{tr('Unable to read the saved file')}: {e}")

                        # # === NEW: control which buttons appear based on status ===
                        # final_norm = str(final_status).strip().lower()

        

                        if contract and can_request:
                            if st.button(tr('Request Reference'), key=f"req_{pid}"):
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
                                    st.success(tr('Reference request sent successfully by email.'))
                                    st.rerun()
                                else:
                                    st.warning(f"{tr('Email delivery failed')} ({msg}). {tr('Please share this link manually')}:")
                                    st.code(link)


                        # Only allow cancelling while still pending or pending review
                        # Only allow cancelling while still pending or pending review
                        if final_norm in ("pending", "pending review", "pending_review"):
                            confirm_key = f"confirm_cancel_{tok}"  # per-request flag

                            # Step 1: show the Cancel button
                            if not st.session_state.get(confirm_key, False):
                                if st.button(tr('Cancel Request'), key=f"cancel_{pid}"):
                                    st.session_state[confirm_key] = True
                                    st.rerun()

                            # Step 2: show confirmation UI
                            else:
                                st.warning(tr('Are you sure you want to cancel this reference request?'))
                                col_yes, col_no = st.columns([1, 1])

                                with col_yes:
                                    if st.button(tr('Yes, cancel it'), key=f"confirm_cancel_yes_{pid}"):
                                        # (A) Email landlord first (so we still have the data to mention)
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

                                        # (B) Hard-delete their responses + contract + request row
                                        delete_landlord_responses(tok)   # your helper from earlier
                                        delete_contract_hard(tok)        # your hard-delete helper
                                        conn.execute("DELETE FROM reference_requests WHERE token=?", (tok,))
                                        conn.commit()

                                        # (C) Clean up UI state and prevent auto-draft recreation on this landlord
                                        st.session_state.pop(confirm_key, None)
                                        st.session_state[f'suppress_autodraft_{pid}'] = True

                                        # (D) Feedback
                                        if ok_mail:
                                            st.success(tr('Request cancelled — landlord notified, contract and responses permanently deleted.'))
                                        else:
                                            st.warning(tr('Request cancelled and data deleted, but email notification failed: ') + str(msg_mail))

                                        st.rerun()


                                with col_no:
                                    if st.button(tr('No, keep it'), key=f"confirm_cancel_no_{pid}"):
                                        st.session_state.pop(confirm_key, None)
                                        st.info(tr('Request kept.'))
                                        st.rerun()


                    else:
                        # No file yet → uploader only
                        uploaded = st.file_uploader(
                            tr('Upload Tenancy Contract (PDF or Image)'),
                            type=["pdf", "png", "jpg", "jpeg", "webp"],
                            key=f"up_{tok}",
                        )
                        if uploaded is not None:
                            ok, msg = save_contract_upload(tok, st.session_state.user["id"], uploaded)
                            if ok:
                                # ✅ After saving, immediately email the landlord (first time only)
                                link = build_reference_link(tok)
                                ok_mail, msg_mail = email_reference_request(
                                    st.session_state.user["name"],
                                    st.session_state.user["email"],
                                    email,
                                    link,
                                    address
                                )
                                if ok_mail:
                                    # Mark as emailed so we never send twice
                                    conn.execute(
                                        "UPDATE reference_requests SET status=?, emailed_at=CURRENT_TIMESTAMP WHERE token=?",
                                        ("pending", tok),
                                    )
                                    conn.commit()
                                    st.success(tr('Contract uploaded and email sent to the landlord.'))
                                    st.rerun()
                                else:
                                    # Keep as Pending Review so the tenant can retry sending
                                    st.warning(f"{tr('Contract uploaded, but email delivery failed')} ({msg_mail}). "
                                            f"{tr('You can share this link manually or try again')}:")
                                    st.code(link)
                                    # Do NOT set emailed_at → the Request button will remain visible after rerun
                                    st.rerun()
                            else:
                                st.error(msg)

                with c_right:
                    # st.markdown(f"**{tr('Request History')}**")
                    if reqs:
                        for (tok_i, status_i, created_at_i, score_i) in reqs:
                            final_i = effective_reference_status(status_i, tok_i)
   

                            # Per-request contract block
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
                                                st.warning(tr('Contract is locked awaiting landlord consent'))
                                            else:
                                                st.download_button(
                                                    tr('Download Contract'),
                                                    data=data_plain_i,
                                                    file_name=contract_i['filename'],
                                                    mime=contract_i.get('content_type') or contract_i.get('mime_type'),
                                                    key=f"dl_{tok_i}",
                                                )
                                        except Exception as e:
                                            st.warning(f"{tr('Unable to read the saved file')}: {e}")
                                    else:
                                        st.markdown(tr('Contract verified — no file upload needed.'))
                                else:
                                    details = get_reference_request_by_token(tok_i)
                                    cancelled_when = details.get("filled_at") if details else None
         
                            else:
                                # Non-final historical entries (rare): show status only
                                if contract_i:
                                    st.markdown(f"**{tr('Contract Status:')}** {contract_status_badge(contract_i['status'])}")
                    else:
                        st.caption(tr('No reference requests have been created yet.'))
    else:
        st.info(tr('No previous landlords added yet.'))
    st.divider()


# ---------- Landlord Dashboard (enhanced) ----------
def landlord_dashboard():
    # --- Header ---
    col_h1, col_h2, col_h3 = st.columns([4, 1, 2])
    with col_h1:
        st.header(tr("Landlord Dashboard"))
    with col_h2:
        if st.button("🔄", key="landlord_refresh"):
            st.rerun()
    with col_h3:
        logout_button()

    landlord_id = st.session_state.user["id"]
    landlord_email = (st.session_state.user.get("email") or "").strip().lower()
    st.caption(f"{tr('Logged in as')} {landlord_email}")

    # =============================================================================
    # Prospective Tenants (landlord view)
    # =============================================================================
    st.subheader(tr("Prospective Tenants"))
    
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
        .ref-card{border:1px solid #e5e7eb;border-radius:12px;padding:10px 12px;margin-bottom:10px;background:#fff}
        .ref-header{display:flex;align-items:center;justify-content:space-between;gap:8px}
        .ref-title{font-weight:600}
        .ref-row{display:flex;flex-wrap:wrap;gap:6px 8px;margin-top:8px}
        .ref-comments{border-left:3px solid #e2e8f0;padding-left:10px;margin-top:8px;color:#334155}
        .ref-card{border:1px solid #e5e7eb;border-radius:12px;padding:10px 12px;margin-bottom:8px;background:#fff}
        .ref-title{font-weight:600;margin-bottom:2px}
        .ref-sub{color:#475569;font-size:.9rem;margin:4px 0 6px}
        .ref-foot{color:#64748b;font-size:.85rem}
        </style>
        """, unsafe_allow_html=True)
    

    def _pt_initials(name, email):
        base = (name or "").strip() or (email or "").split("@")[0]
        parts = [p for p in base.replace(".", " ").split() if p]
        if len(parts) >= 2: return (parts[0][0]+parts[1][0]).upper()
        if parts: return parts[0][:2].upper()
        return "?"
    _ensure_pt_css()


    # ── Widget key namespace ───────────────────────────────────────────────────────
    NSP = "prospects"
    def pk(tid: int, name: str) -> str:
        return f"{NSP}:{name}:{tid}"

    # ── Tiny helpers (scoped to this block) ────────────────────────────────────────
    def _to_bool(v):
        if v is None: return None
        if isinstance(v, bool): return v
        if isinstance(v, (int, float)): return bool(int(v))
        if isinstance(v, str):
            s = v.strip().lower()
            if s in {"1","true","yes","y","t"}: return True
            if s in {"0","false","no","n","f"}: return False
        return None

    def _yn(v):
        b = _to_bool(v)
        if b is None: return "—"
        return tr("Yes") if b else tr("No")

    def _fmt_num(x):
        try:
            return f"{int(x):,}"
        except Exception:
            return str(x) if x is not None else "—"

    def _rng(lo, hi, unit=""):
        if lo is None and hi is None: return f"—{unit}"
        return f"{_fmt_num(lo) if lo not in (None,0) else '—'}–{_fmt_num(hi) if hi not in (None,0) else '—'}{unit}"
    
    def open_to_rent_tokens(tenant_id: int):
        """
        Returns None if not Active.
        Else returns dict with pretty strings for chips:
        {"where", "size", "rooms", "floor", "price"}
        """
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
        sql_cols = ", ".join([f'"{cname}"' for cname in select_cols])

        row = c.execute(f'SELECT {sql_cols} FROM tenant_profiles WHERE "{id_col}"=?', (tenant_id,)).fetchone()
        if not row:
            return None
        data = dict(zip(select_cols, row))

        # Active?
        o2r = data.get("open_to_rent")
        try:
            active = int(o2r) == 1
        except Exception:
            active = str(o2r).strip() == "1"
        if not active:
            return None

        # Build pretty parts
        def fmt_num(v):
            if v is None or v == "" or (isinstance(v, (int, float)) and v == 0):
                return None
            try:
                return f"{int(v):,}"
            except Exception:
                return str(v)

        def rng(lo, hi):
            lo_f, hi_f = fmt_num(lo), fmt_num(hi)
            if not lo_f and not hi_f:
                return None
            return f"{lo_f or '—'}–{hi_f or '—'}"

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

    
    def open_to_rent_summary_line(tenant_id: int) -> str | None:
        """
        Status: Active · Looking in: Region — District — City · 60–100 m² · 1–3 rooms · Floor 2–4 · €500–€1,000
        Shown only when tenant_profiles.open_to_rent == 1. Robust to missing columns and id field.
        """
        c = get_conn()

        # Discover available columns
        try:
            cols_info = c.execute("PRAGMA table_info(tenant_profiles)").fetchall()
        except Exception:
            return None
        available = {row[1] for row in cols_info}

        if "open_to_rent" not in available:
            return None  # no O2R support

        # Determine id column (your DB uses tenant_id)
        id_col = "tenant_id" if "tenant_id" in available else ("user_id" if "user_id" in available else None)
        if not id_col:
            return None

        wanted = [
            "open_to_rent",
            "search_region", "search_district", "search_city",
            "size_min", "size_max",
            "rooms_min", "rooms_max",
            "floor_min", "floor_max",
            "price_min", "price_max",
        ]
        select_cols = [col for col in wanted if col in available]
        sql_cols = ", ".join([f'"{col}"' for col in select_cols])

        row = c.execute(
            f'SELECT {sql_cols} FROM tenant_profiles WHERE "{id_col}"=?',
            (tenant_id,),
        ).fetchone()
        if not row:
            return None

        data = dict(zip(select_cols, row))

        # Active?
        o2r = data.get("open_to_rent")
        try:
            active = int(o2r) == 1
        except Exception:
            active = str(o2r).strip() == "1"
        if not active:
            return None

        # Compose the line (Region may not exist in older DBs)
        region   = data.get("search_region")
        district = data.get("search_district")
        city     = data.get("search_city")
        where_txt = " — ".join([x for x in (region, district, city) if x]) or tr("Anywhere")

        def fmt_num(v):
            if v is None or v == "" or (isinstance(v, (int, float)) and v == 0):
                return "—"
            try:
                return f"{int(v):,}"
            except Exception:
                return str(v)

        def rng(lo, hi, unit=""):
            return f"{fmt_num(lo)}–{fmt_num(hi)}{unit}"

        size_txt  = rng(data.get("size_min"),  data.get("size_max"),  " m²")
        rooms_txt = f"{rng(data.get('rooms_min'), data.get('rooms_max'))} {tr('rooms')}"
        floor_txt = f"{tr('Floor')} {rng(data.get('floor_min'), data.get('floor_max'))}"
        price_txt = f"€{rng(data.get('price_min'), data.get('price_max'))}"

        return (
            f"{tr('Status')}: {tr('Active')} · "
            f"{tr('Looking in')}: {where_txt} · "
            f"{size_txt} · {rooms_txt} · {floor_txt} · {price_txt}"
        )

    
    # ── Data ───────────────────────────────────────────────────────────────────────
    rows = flc_list_prospective_for_landlord(landlord_id)  # invited=1 OR inbound_request=1 OR connected (via JOIN)

    if not rows:
        st.caption(tr("No prospective tenants yet."))
    else:
        for (tid, invited, invited_at, inbound_request, inbound_requested_at) in rows:
            with st.container(border=True):
                # Resolve tenant before rendering identity
                tenant_user = get_user_by_id(tid) or {}
                tenant_name  = (tenant_user.get("name")  or "").strip()
                tenant_email = (tenant_user.get("email") or "").strip()

                # Canonical connection status
                try:
                    status = flc_get_status(landlord_id, tid)  # 'connected' | 'rejected' | None
                except Exception:
                    status = None

                # Header row: identity • badge • actions
                colL, colM, colR = st.columns([6, 3, 5])

                # Left: avatar + name/email + meta
                display_title = tenant_name or tenant_email or f"Tenant #{tid}"
                initials = _pt_initials(tenant_name, tenant_email)


                colL.markdown(
                    f"""
                    <div class="pt-title">
                    <div class="pt-avatar">{initials}</div>
                    <div>
                        <div class="pt-name">{display_title}</div>
                        <div class="pt-email">{tenant_email}</div>
                    </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Middle: status badge
                if status == "connected":
                    colM.markdown(f'<span class="pt-badge pt-badge--ok">{tr("Connected")}</span>', unsafe_allow_html=True)
                elif status == "rejected":
                    colM.markdown(f'<span class="pt-badge pt-badge--err">{tr("Rejected")}</span>', unsafe_allow_html=True)
                else:
                    # origin = tr("You requested") if inbound_request else tr("Tenant listed you")
                    colM.markdown(f'<span class="pt-badge pt-badge--info">{tr("Pending")}</span>', unsafe_allow_html=True)

                # Right: actions (same logic as before)
                if status == "connected":
                    if colR.button(tr("Disconnect"), key=pk(tid, "disconnect")):
                        flc_disconnect(landlord_id, tid)
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.warning(tr("Disconnected."))
                        st.rerun()

                elif status == "rejected":
                    colR.caption(tr("No actions available"))

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

                # ---- Open to Rent one-liner (Active only) ----
                o2r = open_to_rent_tokens(tid)
                if o2r:
                    chips = []
                    if o2r["where"]: chips.append(f'<span class="pill">{o2r["where"]}</span>')
                    if o2r["size"]:  chips.append(f'<span class="pill">{o2r["size"]}</span>')
                    if o2r["rooms"]: chips.append(f'<span class="pill">{o2r["rooms"]}</span>')
                    if o2r["floor"]: chips.append(f'<span class="pill">{o2r["floor"]}</span>')
                    if o2r["price"]: chips.append(f'<span class="pill">{o2r["price"]}</span>')
                    chips_html = " ".join(chips)

                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0 2px 0">'
                        f'  <span class="pt-badge pt-badge--ok">{tr("Open to Rent")}</span>'
                        f'  <div>{chips_html}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                # ---- References summary ----
                refs = list_latest_references_for_tenant_dict(tid) or []
                refs = [r for r in refs if (r.get("status") or "").lower() != "cancelled"]

                total_refs = len(refs)
                latest_status = (refs[0].get("status") if refs else None) or None
                completed = [r for r in refs if (r.get("status") or "").lower() == "completed"]
                scores = [r.get("score") for r in completed if r.get("score") is not None]
                avg_score = round(sum(scores) / len(scores), 1) if scores else None
                
                st.caption(
                            "📄 "
                            + f"{tr('References')}: {len(refs)}"
                        )

                try:
                    latest_status_label = display_status_label(latest_status)
                except Exception:
                    latest_status_label = (latest_status or "—").title()

                
                # ---- Reference details (prettier) — only when connected ----
                    # ---- References (summary + details) ----------------------------------------
                def _to_bool(v):
                    if v is None: return None
                    if isinstance(v, bool): return v
                    if isinstance(v, (int,float)): return bool(int(v))
                    if isinstance(v, str):
                        s = v.strip().lower()
                        if s in {"1","true","yes","y","t"}: return True
                        if s in {"0","false","no","n","f"}: return False
                    return None

                def _yn(v):
                    b = _to_bool(v)
                    if b is None: return "—"
                    return tr("Yes") if b else tr("No")

                def _status_badge_html(s):
                    lab = display_status_label(s) if s else "—"
                    s_l = (s or "").lower()
                    cls = "pt-badge pt-badge--info"
                    if s_l == "completed": cls = "pt-badge pt-badge--ok"
                    elif s_l in {"rejected","declined"}: cls = "pt-badge pt-badge--err"
                    return f'<span class="{cls}">{lab}</span>'

                if status == "connected":
                    # Load only when connected
                    refs = list_latest_references_for_tenant_dict(tid) or []
                    refs = [r for r in refs if (r.get("status") or "").lower() != "cancelled"]

                    if refs:
                        completed_scores = [
                            r.get("score") for r in refs
                            if (r.get("status") or "").lower() == "completed" and r.get("score") is not None
                        ]
                        avg_score = round(sum(completed_scores) / len(completed_scores), 1) if completed_scores else None

                        st.markdown(
                            f"{tr('Avg score')}: {f'{avg_score}/10' if avg_score is not None else '—'}"
                        )

                        with st.expander(tr("Reference details"), expanded=False):
                            for r in refs:
                                prev_email = (r.get("prev_email") or "—").strip()
                                status_lr  = r.get("status") or ""
                                score_lr   = r.get("score")
                                paid_on    = _to_bool(r.get("paid_on_time"))
                                util_unp   = _to_bool(r.get("utilities_unpaid"))
                                good_cond  = _to_bool(r.get("good_condition"))
                                comments   = r.get("comments")

                                # Chip classes (clear & safe)
                                score_chip = ""
                                if (status_lr or "").lower() == "completed" and score_lr is not None:
                                    score_chip = f'<span class="pill pill-score">{md_label("Score:")} {int(score_lr)}/10</span>'
                                paid_cls = "pill-ok" if paid_on is True else "pill-no" if paid_on is False else "pill-na"
                                util_cls = "pill-no" if util_unp is True else "pill-ok" if util_unp is False else "pill-na"
                                cond_cls = "pill-ok" if good_cond is True else "pill-no" if good_cond is False else "pill-na"

                                chips_html = " ".join(filter(None, [
                                    score_chip,
                                    f'<span class="pill {paid_cls}">{tr("Paid on time")}: {_yn(paid_on)}</span>',
                                    f'<span class="pill {util_cls}">{tr("Utilities unpaid")}: {_yn(util_unp)}</span>',
                                    f'<span class="pill {cond_cls}">{tr("Apartment in good condition")}: {_yn(good_cond)}</span>',
                                ]))

                                st.markdown(
                                    f"""
                                    <div class="ref-card">
                                    <div class="ref-header">
                                        <div class="ref-title">{tr('From previous landlord')}: <a href="mailto:{prev_email}">{prev_email}</a></div>
                                        <div>{_status_badge_html(status_lr)}</div>
                                    </div>
                                    <div class="ref-row">{chips_html}</div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                                if comments:
                                    st.markdown(f"**{md_label('Comments:')}**")
                                    st.markdown(f"<div class='ref-comments'>{comments}</div>", unsafe_allow_html=True)

                else:
                    # Optional: show lock note ONLY if there are refs at all
                    try:
                        if list_latest_references_for_tenant(tid):
                            st.caption("🔒 " + tr("Reference details are visible after you connect."))
                    except Exception:
                        pass


                # def _to_bool(v):
                #     if v is None: return None
                #     if isinstance(v, bool): return v
                #     if isinstance(v, (int, float)): return bool(int(v))
                #     if isinstance(v, str):
                #         s = v.strip().lower()
                #         if s in {"1","true","yes","y","t"}: return True
                #         if s in {"0","false","no","n","f"}: return False
                #     return None
                # def _yn(v): 
                #     b = _to_bool(v)
                #     if b is None: return "—"
                #     return tr("Yes") if b else tr("No")

                # if status == "connected" and refs:
                #     with st.expander(tr("Reference details"), expanded=False):
                #         for r in refs:
                #             prev_email = r.get("prev_email") or "—"
                #             status_lr  = r.get("status")
                #             score_lr   = r.get("score")
                #             paid_on    = _yn(r.get("paid_on_time"))
                #             util_unp   = _yn(r.get("utilities_unpaid"))
                #             good_cond  = _yn(r.get("good_condition"))
                #             comments   = r.get("comments")

                #             st.markdown(
                #                 f"""
                #                 <div class="ref-card">
                #                 <div class="ref-title">{tr('From previous landlord')}: {prev_email}</div>
                #                 <div class="ref-sub">{md_label('Status:')} {display_status_label(status_lr)}</div>
                #                 <div class="ref-foot">
                #                     {'{} {}/10 · '.format(md_label('Score:'), int(score_lr)) if (status_lr or '').lower() == 'completed' and score_lr is not None else ''}
                #                     {tr('Paid on time')}: <b>{paid_on}</b> ·
                #                     {tr('Utilities unpaid')}: <b>{util_unp}</b> ·
                #                     {tr('Apartment in good condition')}: <b>{good_cond}</b>
                #                 </div>
                #                 </div>
                #                 """,
                #                 unsafe_allow_html=True
                #             )
                #             if comments:
                #                 st.markdown(md_label('Comments:'))
                #                 st.write(comments)
                # elif status != "connected":
                #     st.caption("🔒 " + tr("Reference details are visible after you connect."))

            # tenant_user = get_user_by_id(tid) or {}
            # tenant_name = (tenant_user.get("name") or "").strip()
            # tenant_email = (tenant_user.get("email") or "").strip()

            # # Card container
            # with st.container(border=True):
            #     top = st.columns([5, 3, 4])

            #     # ── Left: identity + meta
            #     title = tenant_name or tenant_email or f"Tenant #{tid}"
            #     meta = []
            #     if tenant_email: meta.append(tenant_email)
            #     if invited and invited_at: meta.append(tr("Invited on") + f" {invited_at}")
            #     if inbound_request and inbound_requested_at: meta.append(tr("Requested on") + f" {inbound_requested_at}")
            #     subtitle = " · ".join(meta)

            #     top[0].markdown(f"**{title}**")
            #     if subtitle: top[0].caption(subtitle)

            #     # ── Middle: status badge
            #     try:
            #         status = flc_get_status(landlord_id, tid)  # 'connected' | 'rejected' | None
            #     except Exception:
            #         status = None

            #     if status == "connected":
            #         top[1].success(tr("Connected"))
            #     elif status == "rejected":
            #         top[1].error(tr("Rejected"))
            #     else:
            #         origin = tr("You requested") if inbound_request else tr("Tenant listed you")
            #         top[1].info(tr("Pending") + f" · {origin}")

            #     # ── Right: actions
            #     if status == "connected":
            #         if top[2].button(tr("Disconnect"), key=pk(tid, "disconnect")):
            #             flc_disconnect(landlord_id, tid)
            #             try: st.cache_data.clear()
            #             except Exception: pass
            #             st.warning(tr("Disconnected."))
            #             st.rerun()
            #     elif status == "rejected":
            #         top[2].caption(tr("No actions available"))
            #     else:
            #         if inbound_request:
            #             if top[2].button(tr("Cancel request"), key=pk(tid, "cancel_request")):
            #                 flc_cancel_request(landlord_id, tid)
            #                 try: st.cache_data.clear()
            #                 except Exception: pass
            #                 st.info(tr("Request cancelled."))
            #                 st.rerun()
            #         else:
            #             c1, c2 = top[2].columns(2)
            #             if c1.button(tr("Connect"), key=pk(tid, "connect")):
            #                 flc_connect(landlord_id, tid)
            #                 try: st.cache_data.clear()
            #                 except Exception: pass
            #                 st.success(tr("Connected."))
            #                 st.rerun()
            #             if c2.button(tr("Reject"), key=pk(tid, "reject")):
            #                 flc_reject(landlord_id, tid)
            #                 try: st.cache_data.clear()
            #                 except Exception: pass
            #                 st.info(tr("Rejected."))
            #                 st.rerun()

            #     # ── Open to Rent one-liner (modern, compact)
            #     o2r_line = open_to_rent_summary_line(tid)
            #     if o2r_line:
            #         st.markdown(f"🟢 *{o2r_line}*")

            #     # ── References summary (always visible) ───────────────────────────
            #     refs = list_latest_references_for_tenant_dict(tid) or []
            #     refs = [r for r in refs if (r.get("status") or "").lower() != "cancelled"]

            #     total_refs = len(refs)
            #     latest_status = (refs[0].get("status") if refs else None) or None
            #     completed = [r for r in refs if (r.get("status") or "").lower() == "completed"]
            #     scores = [r.get("score") for r in completed if r.get("score") is not None]
            #     avg_score = round(sum(scores) / len(scores), 1) if scores else None

            #     try:
            #         latest_status_label = display_status_label(latest_status)
            #     except Exception:
            #         latest_status_label = (latest_status or "—").title()

            #     st.caption(
            #         "📄 "
            #         + f"{tr('References')}: {total_refs}  ·  "
            #         + f"{tr('Latest status')}: {latest_status_label}  ·  "
            #         + f"{tr('Avg score')}: {f'{avg_score}/10' if avg_score is not None else '—'}"
            #     )

            #     # ── Reference details (beautiful expander, only when connected) ──
            #     if status == "connected" and refs:
            #         with st.expander(tr("Reference details"), expanded=False):
            #             for r in refs:
            #                 prev_email = r.get("prev_email") or "—"
            #                 status_lr  = r.get("status")
            #                 score_lr   = r.get("score")
            #                 paid_on    = _yn(r.get("paid_on_time"))
            #                 util_unp   = _yn(r.get("utilities_unpaid"))
            #                 good_cond  = _yn(r.get("good_condition"))
            #                 comments   = r.get("comments")

            #                 st.markdown(f"**{tr('From previous landlord')}:** {prev_email}")
            #                 st.markdown(f"{md_label('Status:')} {display_status_label(status_lr)}")
            #                 if (status_lr or "").lower() == "completed" and score_lr is not None:
            #                     st.markdown(f"{md_label('Score:')} {score_lr}/10")
            #                 st.write(
            #                     f"- {tr('Paid on time')}: **{paid_on}**  \n"
            #                     f"- {tr('Utilities unpaid')}: **{util_unp}**  \n"
            #                     f"- {tr('Apartment in good condition')}: **{good_cond}**"
            #                 )
            #                 if comments:
            #                     st.markdown(md_label('Comments:'))
            #                     st.write(comments)
            #                 st.markdown("---")
            #     elif status != "connected":
            #         st.caption("🔒 " + tr("Reference details are visible after you connect."))
                    
    # =============================================================================
    # My Properties
    # =============================================================================

    st.subheader(tr("My Properties"))

    LP_NS = "myprops"  # namespacing to avoid widget-key collisions
    def lpk(id_: int | str, name: str) -> str:
        return f"{LP_NS}:{name}:{id_}"

    # --- Add property form --------------------------------------------------------
   
    with st.expander("**🏠 " + tr("Add a property") + "**", expanded=False):
    # st.markdown("**🏠 " + tr("Add a property") + "**")

        # 1) Live location pickers OUTSIDE the form (update immediately)
        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            # returns (region, regional_unit, municipality)
            # keys: lp_add_region / lp_add_ru / lp_add_mun
            region, regional_unit, municipality = greece_location_pickers(prefix="lp_add")  # :contentReference[oaicite:0]{index=0}

        # 2) The rest stays in a form (so we can clear_on_submit)
        with st.form(lpk("add", "form"), clear_on_submit=True):
            addr = st.text_input(tr("Address"), key=lpk("add", "addr"), placeholder=tr("Street, number, city"))
            url  = st.text_input(tr("Listing URL (optional)"), key=lpk("add", "url"),
                                placeholder="https://www.xe.gr/property/...")
            s1, s2, s3, s4 = st.columns(4)
            with s1:
                size_m2 = st.number_input(tr("Size (m²)"), min_value=0, max_value=10000, step=10, value=0, key=lpk("add", "size"))
            with s2:
                rooms = st.number_input(tr("Rooms"), min_value=0, max_value=50, step=1, value=0, key=lpk("add", "rooms"))
            with s3:
                floor = st.number_input(tr("Floor"), min_value=-5, max_value=100, step=1, value=0, key=lpk("add", "floor"))
            with s4:
                price = st.number_input(tr("Price (€)"), min_value=0, max_value=1_000_000, step=50, value=0, key=lpk("add", "price"))
            vis  = st.checkbox(tr("Visible to tenants"), key=lpk("add", "vis"), value=False)

            c1, _ = st.columns([1, 5])
            submitted = c1.form_submit_button(tr("Add"))

        if submitted:
            address = (addr or "").strip()
            if not address:
                st.error(tr("Please enter the address."))
            else:
                try:
                    lp_add_property(
                        st.session_state.user["id"],
                        address,
                        url,
                        vis,
                        region=region,                 # live value from picker
                        district=regional_unit,        # live value from picker
                        city=municipality,             # live value from picker
                        size_m2=size_m2,
                        rooms=rooms,
                        floor=floor,
                        price=price,
                    )
                    try: st.cache_data.clear()
                    except Exception: pass

                    # Optional: reset the pickers to Any after add
                    for k in ("lp_add_region", "lp_add_ru", "lp_add_mun"):
                        st.session_state.pop(k, None)

                    st.success(tr("Property added."))
                    st.rerun()
                except Exception as e:
                    st.error(f"{tr('Unable to add property')}: {e}")


    # --- List properties ----------------------------------------------------------
    props = lp_list_properties(st.session_state.user["id"])
    if not props:
        st.caption(tr("No properties yet."))
    else:
        for (prop_id, address, listing_url, visible_to_tenants, created_at, updated_at,
            region, district, city, size_m2, rooms, floor, price) in props:

            with st.container(border=True):
                head = st.columns([6, 3, 3])

                # Left: Address + link + compact spec line
                head[0].markdown(f"**{address}**")
                chips = []
                where = " — ".join([x for x in [region, district, city] if x])
                if where:
                    chips.append(where)
                spec_bits = []
                if size_m2: spec_bits.append(f"{int(size_m2)} m²")
                if rooms:   spec_bits.append(f"{int(rooms)} {tr('rooms')}")
                if floor is not None and floor != 0: spec_bits.append(f"{tr('Floor')} {int(floor)}")
                if price:   spec_bits.append(f"€{int(price):,}")
                if spec_bits:
                    chips.append(" · ".join(spec_bits))
                if chips:
                    head[0].caption(" · ".join(chips))

                if listing_url:
                    try:
                        domain = listing_url.split("://", 1)[-1].split("/", 1)[0]
                    except Exception:
                        domain = listing_url
                    head[0].caption(f"🔗 [{domain}]({listing_url})")

                # Middle: Visibility badge
                if int(visible_to_tenants or 0) == 1:
                    head[1].success("👁️ " + tr("Visible to tenants"))
                else:
                    head[1].info("🙈 " + tr("Hidden from tenants"))

                # Right: Quick actions (toggle + delete)
                cvis, cdel = head[2].columns(2)
                if int(visible_to_tenants or 0) == 1:
                    if cvis.button(tr("Hide"), key=lpk(prop_id, "hide")):
                        lp_toggle_visibility(prop_id, st.session_state.user["id"], False)
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.rerun()
                else:
                    if cvis.button(tr("Show"), key=lpk(prop_id, "show")):
                        lp_toggle_visibility(prop_id, st.session_state.user["id"], True)
                        try: st.cache_data.clear()
                        except Exception: pass
                        st.rerun()

                if cdel.button(tr("Delete"), key=lpk(prop_id, "delete")):
                    lp_delete_property(prop_id, st.session_state.user["id"])
                    try: st.cache_data.clear()
                    except Exception: pass
                    st.warning(tr("Property deleted."))
                    st.rerun()

                # Editable details (with pickers again; leave blank to keep old)
                with st.expander(tr("Edit details"), expanded=False):
                    e_addr = st.text_input(tr("Address"), value=address, key=lpk(prop_id, "edit_addr"))
                    e_url  = st.text_input(tr("Listing URL (optional)"), value=(listing_url or ""), key=lpk(prop_id, "edit_url"))

                    # New picks (not prefilled; if user leaves empty, we keep the old values on save)
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        reg_new, ru_new, muni_new = greece_location_pickers(prefix=f"lp_edit_{prop_id}")

                    # Numeric fields (pre-filled)
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

                    e_vis  = st.checkbox(tr("Visible to tenants"),
                                        value=bool(int(visible_to_tenants or 0)),
                                        key=lpk(prop_id, "edit_vis"))

                    s1, s2 = st.columns([1, 5])
                    if s1.button(tr("Save changes"), key=lpk(prop_id, "save")):
                        try:
                            if not (e_addr or "").strip():
                                st.error(tr("Address cannot be empty."))
                            else:
                                # Keep old location if no new selection is made
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
                                st.success(tr("Saved."))
                                st.rerun()
                        except Exception as e:
                            st.error(f"{tr('Unable to save changes')}: {e}")

                st.caption(f"{tr('Updated')}: {updated_at} · {tr('Created')}: {created_at}")

    # st.subheader(tr("My Properties"))

    # LP_NS = "myprops"  # namespacing to avoid widget-key collisions
    # def lpk(id_: int | str, name: str) -> str:
    #     return f"{LP_NS}:{name}:{id_}"

    # # --- Add property form --------------------------------------------------------
    # with st.container(border=True):
    #     st.markdown("**🏠 " + tr("Add a property") + "**")
    #     with st.form(lpk("add", "form"), clear_on_submit=True):
    #         addr = st.text_input(tr("Address"), key=lpk("add", "addr"), placeholder=tr("Street, number, city"))
    #         url  = st.text_input(tr("Listing URL (optional)"), key=lpk("add", "url"),
    #                             placeholder="https://www.xe.gr/property/...")
    #         vis  = st.checkbox(tr("Visible to tenants"), key=lpk("add", "vis"), value=False)
    #         c1, c2 = st.columns([1, 5])
    #         submitted = c1.form_submit_button(tr("Add"))
    #         if submitted:
    #             address = (addr or "").strip()
    #             if not address:
    #                 st.error(tr("Please enter the address."))
    #             else:
    #                 try:
    #                     lp_add_property(st.session_state.user["id"], address, url, vis)
    #                     try: st.cache_data.clear()
    #                     except Exception: pass
    #                     st.success(tr("Property added."))
    #                     st.rerun()
    #                 except Exception as e:
    #                     st.error(f"{tr('Unable to add property')}: {e}")

    # # --- List properties ----------------------------------------------------------
    # props = lp_list_properties(st.session_state.user["id"])
    # if not props:
    #     st.caption(tr("No properties yet."))
    # else:
    #     for (prop_id, address, listing_url, visible_to_tenants, created_at, updated_at) in props:
    #         with st.container(border=True):
    #             head = st.columns([6, 3, 3])

    #             # Left: Address + link
    #             head[0].markdown(f"**{address}**")
    #             if listing_url:
    #                 # show short domain label
    #                 try:
    #                     domain = listing_url.split("://", 1)[-1].split("/", 1)[0]
    #                 except Exception:
    #                     domain = listing_url
    #                 head[0].caption(f"🔗 [{domain}]({listing_url})")

    #             # Middle: Visibility badge
    #             if int(visible_to_tenants or 0) == 1:
    #                 head[1].success("👁️ " + tr("Visible to tenants"))
    #             else:
    #                 head[1].info("🙈 " + tr("Hidden from tenants"))

    #             # Right: Quick actions (toggle + delete)
    #             cvis, cdel = head[2].columns(2)
    #             if int(visible_to_tenants or 0) == 1:
    #                 if cvis.button(tr("Hide"), key=lpk(prop_id, "hide")):
    #                     lp_toggle_visibility(prop_id, st.session_state.user["id"], False)
    #                     try: st.cache_data.clear()
    #                     except Exception: pass
    #                     st.rerun()
    #             else:
    #                 if cvis.button(tr("Show"), key=lpk(prop_id, "show")):
    #                     lp_toggle_visibility(prop_id, st.session_state.user["id"], True)
    #                     try: st.cache_data.clear()
    #                     except Exception: pass
    #                     st.rerun()

    #             if cdel.button(tr("Delete"), key=lpk(prop_id, "delete")):
    #                 lp_delete_property(prop_id, st.session_state.user["id"])
    #                 try: st.cache_data.clear()
    #                 except Exception: pass
    #                 st.warning(tr("Property deleted."))
    #                 st.rerun()

    #             # Editable details (modern compact editor)
    #             with st.expander(tr("Edit details"), expanded=False):
    #                 e_addr = st.text_input(tr("Address"), value=address, key=lpk(prop_id, "edit_addr"))
    #                 e_url  = st.text_input(tr("Listing URL (optional)"), value=(listing_url or ""), key=lpk(prop_id, "edit_url"))
    #                 e_vis  = st.checkbox(tr("Visible to tenants"), value=bool(int(visible_to_tenants or 0)), key=lpk(prop_id, "edit_vis"))
    #                 s1, s2 = st.columns([1, 5])
    #                 if s1.button(tr("Save changes"), key=lpk(prop_id, "save")):
    #                     try:
    #                         if not (e_addr or "").strip():
    #                             st.error(tr("Address cannot be empty."))
    #                         else:
    #                             lp_update_property(prop_id, st.session_state.user["id"], e_addr, e_url, e_vis)
    #                             try: st.cache_data.clear()
    #                             except Exception: pass
    #                             st.success(tr("Saved."))
    #                             st.rerun()
    #                     except Exception as e:
    #                         st.error(f"{tr('Unable to save changes')}: {e}")

    #             # Footer meta
    #             st.caption(f"{tr('Updated')}: {updated_at} · {tr('Created')}: {created_at}")


    # =============================================================================
    # Find Tenants (Open to Rent)
    # =============================================================================
    st.subheader(tr("Find Tenants (Open to Rent)"))

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            q = st.text_input(
                tr("Search by name or email"),
                placeholder="e.g. Maria, nikos@example.com",
                key="otr_q",
            )
        with c2:
            limit = st.number_input(tr("Max results"), 1, 500, 100, key="otr_limit")

        with st.expander(tr("Filters (based on tenants' preferences)"), True):
            # Location pickers (Region → Regional Unit → Municipality)
            lc1, lc2, lc3 = st.columns(3)
            with lc1:
                region, regional_unit, municipality = greece_location_pickers(prefix="otr")
            city = municipality            # Municipality (Dimos)
            district = regional_unit       # Regional Unit (Perifereiaki Enotita)

            # Ranges
            r1c1, r1c2 = st.columns(2)
            size_min = r1c1.number_input(tr("Min size (m²)"), min_value=0, max_value=10000, value=0, step=1, key="otr_size_min") or None
            size_max = r1c2.number_input(tr("Max size (m²)"), min_value=0, max_value=10000, value=0, step=1, key="otr_size_max") or None

            r2c1, r2c2 = st.columns(2)
            rooms_min = r2c1.number_input(tr("Min rooms"), min_value=0, max_value=50, value=0, step=1, key="otr_rooms_min") or None
            rooms_max = r2c2.number_input(tr("Max rooms"), min_value=0, max_value=50, value=0, step=1, key="otr_rooms_max") or None

            r3c1, r3c2 = st.columns(2)
            floor_min_val = r3c1.number_input(tr("Min floor"), min_value=-5, max_value=100, value=0, step=1, key="otr_floor_min")
            floor_max_val = r3c2.number_input(tr("Max floor"), min_value=-5, max_value=100, value=0, step=1, key="otr_floor_max")
            floor_min = floor_min_val if floor_min_val != 0 else None
            floor_max = floor_max_val if floor_max_val != 0 else None

            r4c1, r4c2 = st.columns(2)
            price_min = r4c1.number_input(tr("Min price (€)"), min_value=0, max_value=1_000_000, value=0, step=50, key="otr_price_min") or None
            price_max = r4c2.number_input(tr("Max price (€)"), min_value=0, max_value=1_000_000, value=0, step=50, key="otr_price_max") or None

        # Sticky search flag so results persist after button clicks
        if "ld_otr_do_search" not in st.session_state:
            st.session_state["ld_otr_do_search"] = False

        cbtn1, cbtn2 = st.columns([1, 1])
        if cbtn1.button(tr("Search"), key="ld_otr_search_btn"):
            st.session_state["ld_otr_do_search"] = True
        if cbtn2.button(tr("Reset"), key="ld_otr_reset_btn"):
            st.session_state["ld_otr_do_search"] = False
            try: st.cache_data.clear()
            except Exception: pass
            st.rerun()

        if st.session_state["ld_otr_do_search"]:
            results = search_open_to_rent_tenants(
                q=q,
                city=city,
                district=district,
                size_min=size_min, size_max=size_max,
                rooms_min=rooms_min, rooms_max=rooms_max,
                floor_min=floor_min, floor_max=floor_max,
                price_min=price_min, price_max=price_max,
                limit=limit,
            )

            if not results:
                st.info(tr("No matching tenants found."))
            else:
                st.caption(f"{len(results)} {tr('result(s)')}")
                for r in results:
                    (
                        tenant_id, tenant_name, tenant_email, updated_at,
                        t_city, t_district,
                        t_smin, t_smax, t_rmin, t_rmax, t_fmin, t_fmax, t_pmin, t_pmax
                    ) = r

                    with st.container(border=True):
                        top = st.columns([5, 3, 4])

                        # Left: identity + quick prefs recap
                        title = tenant_name or f"Tenant #{tenant_id}"
                        top[0].markdown(f"**{title}** — {tenant_email}")
                        pref_bits = []
                        if t_city:     pref_bits.append(t_city)
                        if t_district: pref_bits.append(t_district)
                        range_bits = []
                        if t_smin or t_smax: range_bits.append(f"{tr('Size')} {t_smin or '—'}–{t_smax or '—'} m²")
                        if t_rmin or t_rmax: range_bits.append(f"{tr('Rooms')} {t_rmin or '—'}–{t_rmax or '—'}")
                        if t_fmin is not None or t_fmax is not None:
                            range_bits.append(f"{tr('Floor')} {t_fmin if t_fmin is not None else '—'}–{t_fmax if t_fmax is not None else '—'}")
                        if t_pmin or t_pmax: range_bits.append(f"{tr('Price')} €{t_pmin or '—'}–€{t_pmax or '—'}")
                        sub = " · ".join([", ".join(pref_bits)] + ([" | ".join(range_bits)] if range_bits else []))
                        if sub.strip(", · |"):
                            top[0].caption(sub)
                        # top[1].markdown(f"{tr('Updated')}: {format_dt(updated_at)}")

                        # Hide only final states, not pending
                        try:
                            status = flc_get_status(landlord_id, tenant_id)
                        except Exception:
                            status = None
 

                        # Right: outbound pending logic (landlord -> tenant)
                        # --- Status badge + actions (show for all: connected / pending / disconnected / none) ---
                        status_label, pending_dir = flc_relation_status(landlord_id, tenant_id, landlord_email)

                        # Middle column: status badge
                        if status_label == "connected":
                            top[1].success(tr("Connected"))
                        elif status_label == "pending":
                            top[1].info(tr("Pending"))
                        elif status_label == "disconnected":
                            top[1].error(tr("Disconnected"))
                        else:
                            top[1].caption(tr("No relation"))

                        # Right column: actions, depending on status/origin
                        if status_label == "connected":
                            pass


                        elif status_label == "pending":
                            pass


                        elif status_label == "disconnected":
                            # Show the status AND allow sending a new request
                            if top[2].button(tr("Ask to connect"), key=f"otr_req_{tenant_id}"):
                                flc_request_connect(landlord_id, tenant_id)
                                try: st.cache_data.clear()
                                except Exception: pass
                                st.rerun()

                        else:
                            # No relation yet
                            if top[2].button(tr("Ask to connect"), key=f"otr_req_{tenant_id}"):
                                flc_request_connect(landlord_id, tenant_id)
                                try: st.cache_data.clear()
                                except Exception: pass
                                st.rerun()


                        # --- References quick summary + (when connected) answers ---
                        ref = quick_reference_summary(tenant_id)

                        if not ref["have"]:
                            st.caption(f"📄 {tr('References')}: {tr('None')}")
                        else:
                            # Pretty status label if you have a helper; fall back if not.
                            try:
                                latest_status_label = display_status_label(ref["latest_status"])
                            except Exception:
                                latest_status_label = (ref["latest_status"] or "").title() or "—"

                            # Result priority: latest score (if latest completed) -> avg completed -> —
                            if ref["latest_score"] is not None:
                                result_txt = f"{ref['latest_score']}/10"
                            elif ref["avg_score"] is not None:
                                result_txt = f"{ref['avg_score']}/10 {tr('avg')}"
                            else:
                                result_txt = "—"

                            st.caption(
                                "📄 "
                                + f"{tr('References')}: {ref['total']}  ·  "
                                + f"{tr('Latest status')}: {latest_status_label}  ·  "
                                + f"{tr('Result')}: {result_txt}"
                            )

                            # If connected, show latest completed answers inline
                            # ref = quick_reference_summary(tenant_id)
                            # status_label computed earlier via flc_relation_status(...)

                            if status_label == "connected" and ref["latest_answers"]:
                                ans = ref["latest_answers"]
                                prev_from = ans.get("prev_email") or "—"
                                comments  = ans.get("comments")
                                with st.expander(tr("Latest reference answers"), expanded=False):
                                    st.write(
                                        f"- {tr('From previous landlord')}: **{prev_from}**  \n"
                                        f"- {tr('Paid on time')}: **{_yn(ans.get('paid_on_time'))}**  \n"
                                        f"- {tr('Utilities unpaid')}: **{_yn(ans.get('utilities_unpaid'))}**  \n"
                                        f"- {tr('Apartment in good condition')}: **{_yn(ans.get('good_condition'))}**"
                                    )
                                    if comments:
                                        st.markdown(f"- {md_label('Comments:')}")
                                        st.write(comments)

                            elif status_label != "connected":
                                # keep privacy consistent with your dashboard: details only after connect
                                st.caption(f"🔒 {tr('Connect to view full answers')}")

    # === Reference requests that were sent to this landlord ===
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
                    # ❌ no key here
                    with st.expander(tr('View Submitted Reference')):
                        details = get_reference_request_by_token(token)
                        if details:
                            st.write(f"Confirmed landlord: {'Yes' if details['confirm_landlord'] else 'No'}")
                            st.write(f"Score: {details['score']}/10")
                            st.write(f"Paid on time: {'Yes' if details['paid_on_time'] else 'No'}")
                            st.write(f"Utilities unpaid: {'Yes' if details['utilities_unpaid'] else 'No'}")
                            st.write(f"Apartment in good condition: {'Yes' if details['good_condition'] else 'No'}")
                            if details.get('comments'):
                                st.write("**Comments:**")
                                st.write(details['comments'])



    with tab_all:
        render_requests(all_reqs, "all")
    with tab_pending:
        render_requests(pending_reqs, "pending")
    with tab_completed:
        render_requests(completed_reqs, "completed")
    with tab_cancelled:
        render_requests(cancelled_reqs, "cancelled")
        
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
    # ✅ Route to the thank-you page
    if params.get("page") == "submitted":
        reference_submitted_page()
        return
    if params.get("page") == "cancelled":
        reference_cancelled_page()
        return

    token = params.get("ref")
    if token:
        reference_portal(token)
        return

    st.title("🏠 RentRight")

    if st.session_state.get("user"):
        role = st.session_state.user["role"]
        if role == "tenant":
            tenant_dashboard()
        elif role == "landlord":
            landlord_dashboard()
        elif role == "admin":
            admin_dashboard()
        else:
            st.error(f"Unknown role: {role}")
        return

    auth_gate()


if __name__ == "__main__":
    main()



