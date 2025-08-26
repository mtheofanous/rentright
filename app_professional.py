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

from utils_vault import encrypt_bytes, decrypt_bytes, sha256_bytes

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
        # Admin
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
        "No previous landlords added yet.": "Δεν έχουν προστεθεί ακόμη προηγούμενοι ιδιοκτήτες.",
        "No active reference request.": "Δεν υπάρχει ενεργό αίτημα σύστασης.",
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

# === End language utilities ===


# === Top-right language switcher (flags only) ===
def render_topbar_language():
    c1, c2, c3 = st.columns([8, 2, 2])
    with c2:
        choice = st.selectbox(
            "🌐 Language",
            ["ENG", "GR"],
            key="lang_flag",
            index=0 if st.session_state.get("lang","English")=="English" else 1,
            label_visibility="collapsed",
        )
        st.session_state["lang"] = "English" if choice == "ENG" else "Ελληνικά"
    # with c3:
    #     # simple manual refresh that keeps session_state (so you stay logged in)
    #     if st.button(tr("Refresh"), key="__refresh_topbar__", use_container_width=True):
    #         st.rerun()
            
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
    cur.execute(
        "INSERT OR IGNORE INTO future_landlord_contacts(tenant_id, email, created_at) VALUES (?,?,?)",
        (tenant_id, email, datetime.utcnow().isoformat()),
    )
    conn.commit()


def list_future_landlord_contacts(tenant_id: int):
    cur = get_conn().cursor()
    cur.execute(
        "SELECT id, email, created_at, invited, invited_at FROM future_landlord_contacts WHERE tenant_id = ? ORDER BY id DESC",
        (tenant_id,),
    )
    return cur.fetchall()

def remove_future_landlord_contact(contact_id: int, tenant_id: int):
    cur = get_conn().cursor()
    cur.execute(
        "DELETE FROM future_landlord_contacts WHERE id = ? AND tenant_id = ?",
        (contact_id, tenant_id),
    )
    get_conn().commit()

# def invite_future_landlord(tenant_id: int, email: str, tenant_name: str, tenant_email: str):
#     base = st.session_state.get("app_base_url") or (st.secrets.get("APP_BASE_URL") if hasattr(st, "secrets") else "")
#     join_link = base if base else ""
#     subject = f"{tenant_name} would like to connect with you on RentRight"
#     body = (
#         "Hello,\n\n"
#         f"{tenant_name} ({tenant_email}) has added you as a future landlord on RentRight.\n"
#         + (f"You can sign in or create an account here: {join_link}\n\n" if join_link else "")
#         + "Thank you."
#     )
#     ok, msg = send_email_smtp(email, subject, body)
#     if ok:
#         conn = get_conn()
#         cur = conn.cursor()
#         cur.execute(
#             "UPDATE future_landlord_contacts SET invited = 1, invited_at = ? WHERE tenant_id = ? AND LOWER(email) = LOWER(?)",
#             (datetime.utcnow().isoformat(), tenant_id, email),
#         )
#         conn.commit()
#     return ok, msg

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

 # Tenant deletes request 
# Starts here
import os

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

# def email_reference_cancellation_smtp(
#     tenant_name: str,
#     tenant_email: str,
#     landlord_email: str,
#     landlord_name: str | None,
#     landlord_address: str | None,
#     token: str,
#     cancelled_at: str | None,
# ):
#     subject = "Reference request cancelled — data deleted"
#     body = f"""Hello {landlord_name or 'there'},

# The tenant {tenant_name} has cancelled their rental reference request.

# What this means:
# • The reference link for token {token} is now disabled.
# • The uploaded contract file has been permanently deleted.
# • Any responses you submitted in the reference form have been permanently deleted.

# Address on file: {landlord_address or '—'}
# Cancelled at: {cancelled_at or '—'}

# If you have questions, you can reply to {tenant_email}.
# """
#     # Uses your existing SMTP helper
#     return send_email_smtp(landlord_email, subject, body)

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
    with st.form("login_form"):
        email = st.text_input(tr('Email'))
        password = st.text_input(tr('Password'), type="password")
        submitted = st.form_submit_button(tr('Sign In'))

    if submitted:
        user = get_user_by_email(email)
        if not user or user["password_hash"] != hash_password(password):
            st.error(tr('Incorrect email or password. Please try again.'))
            st.stop()  # stop this run so the form stays visible with the error

        # Save session and immediately rerun so main() routes to the dashboard
        st.session_state.user = {k: user[k] for k in ["id","email","name","role"]}
        # Optional: flash once after rerun (uncomment + handle in dashboard if you want)
        # st.session_state["flash_welcome"] = f"{tr('Welcome, ')}{user['name']}!"
        st.rerun()

# def login_form():
#     st.subheader(tr('Sign In'))
#     with st.form("login_form"):
#         email = st.text_input(tr('Email'))
#         password = st.text_input(tr('Password'), type="password")
#         submitted = st.form_submit_button(tr('Sign In'))
        
#     if submitted:
#         user = get_user_by_email(email)
#         if not user or user["password_hash"] != hash_password(password):
#             st.error(tr('Incorrect email or password. Please try again.'))
#             return
#         st.session_state.user = {k: user[k] for k in ["id","email","name","role"]}
#         st.success(f"Welcome, {user['name']}!")


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



def build_reference_link(token: str) -> str:
    base = st.session_state.get("app_base_url") or (st.secrets.get("APP_BASE_URL") if hasattr(st, "secrets") else "")
    if base:
        base = base.strip().rstrip("/")
        return f"{base}/?ref={token}"
    # fallback that still works when clicked inside the app
    return f"?ref={token}"


# def email_reference_request(tenant_name: str, tenant_email: str, landlord_email: str, link: str):
#     subject = f"Reference Request for Tenant {tenant_name}"
#     body = (
#         f"Hello,\n\n"
#         f"{tenant_name} ({tenant_email}) listed you as a previous landlord and is requesting a short reference.\n"
#         f"Please confirm and complete the form here: {link}\n\n"
#         f"Thank you!"
#     )
#     return send_email_smtp(landlord_email, subject, body)

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
        f"📍 {tr('Address')}: {address}\n\n"
        # f"{tr('Sent to landlord')}: {data['landlord_email']}"
    )

    # st.info(f"Reference for Tenant ID #{data['tenant_id']} — sent to {data['landlord_email']}")
    with st.form("reference_form"):
        confirm = st.checkbox(
            tr(
                "I confirm that I was the landlord for this tenant. "
                "By checking this box, I consent to the use of the uploaded tenancy contract "
                "solely for verifying my relationship with the tenant and for completing this reference. "
                "The contract will remain encrypted and locked until I provide this confirmation. "
                "It will not be shared or used for any other purpose, in accordance with GDPR."
            )
        )

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
    c1.metric("Pending (effective)", len(pending_reqs))
    c2.metric("Completed (effective)", len(completed_reqs))
    c3.metric(tr('Cancelled'), len(cancelled_reqs))

    tab_pending, tab_completed, tab_cancelled = st.tabs([tr('Pending'), tr('Completed'), tr('Cancelled')])
    
    #AFM
    
    # def render_admin_reqs(reqs, prefix: str):
    #     if not reqs:
    #         st.info(tr('No requests available.'))
    #         return

    #     for (token, tenant_id, landlord_email, created_at, status, score) in reqs:
    #         tenant = get_user_by_id(tenant_id)
    #         tenant_label = tenant["name"] if tenant else f"Tenant #{tenant_id}"
    #         final_status = effective_reference_status(status, token)

    #         # Fetch request details and previous landlord info
    #         details = get_reference_request_by_token(token)
    #         pl_name = pl_email = pl_addr = "—"
    #         if details and details.get("prev_landlord_id"):
    #             cur = conn.cursor()
    #             cur.execute(
    #                 "SELECT name, afm, email, address FROM previous_landlords WHERE id=?",
    #                 (details["prev_landlord_id"],),
    #             )
    #             row = cur.fetchone()
    #             if row:
    #                 pl_name, pl_afm, pl_email, pl_addr = row

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

            # with st.container(border=True):
            #     cols = st.columns([3, 3, 3, 2])
            #     cols[0].markdown(f"**Tenant:** {tenant_label} ({tenant['email'] if tenant else '—'})")
            #     cols[1].markdown(f"**To landlord:** {landlord_email}")
            #     cols[2].markdown(f"**Created:** {created_at}")
            #     cols[3].markdown(f"**Status:** {final_status}")

            #     # ⬇️ Show previous landlord Name + AFM
             
            #     st.caption(f"Previous landlord: **{pl_name}** ({pl_email}) · Address: {pl_addr}")
            
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
                cols[2].markdown(f"{tr('**Created:**')} {created_at}")
                cols[3].markdown(f"{tr('**Status:**')} {display_status}")

                # ⬇️ Previous landlord line (translated)
                st.caption(f"{tr('Previous landlord:')} **{pl_name}** ({pl_email}) · {tr('Address:')} {pl_addr}")



                link = build_reference_link(token)
                st.text_input(tr('Reference Link'), value=link, key=f"{prefix}_link_{token}", disabled=True)

                # --- Contract section ---
                contract = get_contract_by_token(token)
                if contract:
                    consent_row = conn.cursor().execute("SELECT consent_status FROM reference_contracts WHERE token=?", (token,)).fetchone()
                    consent_badge = f"Consent: {consent_row[0] if consent_row else 'locked'}"
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



                # --- Admin actions ---
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
    col_h1, col_h2, col_h3 = st.columns([4,1,2])
    with col_h1: st.header(tr('Tenant Dashboard'))
    with col_h2:
        if st.button("🔄", key="tenant_refresh"):
            st.rerun()
    with col_h3: logout_button()
 

    # Header with a visible Sign Out button on the main page
    # col_h1, col_h2 = st.columns([4, 1])
    # with col_h1:
    #     st.header(tr('Tenant Dashboard'))
    # with col_h2:
    #     st.write("")
    #     st.write("")
    #     logout_button()

    # === Future landlord email ===
    st.subheader(tr('Future Landlords (Contacts)'))

    
    with st.form("future_landlords_add_form"):
        new_fl_email = st.text_input(tr('Enter a landlord’s email address'))
        add_fl = st.form_submit_button(tr('Add Contact'))
    if add_fl:
        if not new_fl_email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", new_fl_email):
            st.error(tr('Please enter a valid email address.'))
        else:
            try:
                # 1) Save contact
                add_future_landlord_contact(st.session_state.user["id"], new_fl_email)
                # 2) Auto-send invite
                ok, msg = invite_future_landlord(
                    st.session_state.user["id"],
                    new_fl_email,
                    st.session_state.user["name"],
                    st.session_state.user["email"],
                )
                if ok:
                    st.success(tr('Contact added and invitation sent successfully.'))
                    st.rerun()  # refresh list to show 'Invited' status
                else:
                    st.warning(f"Contact added, but the email could not be sent: {msg}")
            except Exception as e:
                st.warning(f"{tr('Unable to add contact:')} {e}")


    # List + actions (send connection / remove)
    fl_rows = list_future_landlord_contacts(st.session_state.user["id"]) or []
    if fl_rows:
        for (cid, fl_email, created_at, invited, invited_at) in fl_rows:
            with st.container(border=True):
                cols = st.columns([4,2,3,2])
                cols[0].markdown(f"**{fl_email}**")
               
                if invited:
                    cols[2].success(tr('Invited'))
             
                else:
                    if cols[2].button(tr('Send Invitation'), key=f"invite_fl_{cid}"):
                        ok, msg = invite_future_landlord(
                            st.session_state.user["id"],
                            fl_email,
                            st.session_state.user["name"],
                            st.session_state.user["email"],
                        )
                        if ok:
                            st.success(tr('Invitation sent successfully.'))
                            st.rerun()
                        else:
                            st.error(f"Unable to send invitation: {msg}")
                    if cols[3].button(tr('Remove'), key=f"remove_fl_{cid}"):
                        remove_future_landlord_contact(cid, st.session_state.user["id"])
                        st.info(tr('Contact removed.'))
                        st.rerun()
    else:
        st.caption(tr('No future landlord contacts yet.'))

    st.divider()
    
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
            with st.expander(f"{name} • {email} • {address} "):

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

                    # 👉 Always render history in the no-active path
                    # if reqs:
                    #     st.markdown("---")
                    #     for (tok_i, status_i, created_at_i, score_i) in reqs:
                    #         final_i = effective_reference_status(status_i, tok_i)
                    #         contract_i = get_contract_by_token(tok_i)
                    #         final_i_lower = str(final_i).lower()

                    #         if final_i_lower in ("completed", "cancelled"):
                    #             if final_i_lower == "completed":
                    #                 if score_i is not None:
                    #                     st.write(f"{tr('Score')}: **{score_i}**/10")
                    #                 if contract_i:
                    #                     st.markdown(f"**{tr('Contract Status:')}** {contract_status_badge(contract_i['status'])}")
                    #                     try:
                    #                         data_plain_i = load_contract_plaintext(tok_i)
                    #                         if data_plain_i is None:
                    #                             st.warning(tr('Contract is locked awaiting landlord consent'))
                    #                         else:
                    #                             st.download_button(
                    #                                 tr('Download Contract'),
                    #                                 data=data_plain_i,
                    #                                 file_name=contract_i['filename'],
                    #                                 mime=contract_i.get('content_type') or contract_i.get('mime_type'),
                    #                                 key=f"dl_hist_{tok_i}",
                    #                             )
                    #                     except Exception as e:
                    #                         st.warning(f"{tr('Unable to read the saved file')}: {e}")
                    #             else:
                    #                 details_i = get_reference_request_by_token(tok_i)
                    #                 # Optionally show cancelled timestamp:
                    #                 # st.caption(f"Cancelled at: {details_i.get('filled_at') or '—'}")
                    #         else:
                    #             if contract_i:
                    #                 st.markdown(f"**{tr('Contract Status:')}** {contract_status_badge(contract_i['status'])}")

                    # Done with the "no active" branch
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
    col_h1, col_h2, col_h3 = st.columns([4,1,2])
    with col_h1: st.header(tr('Tenant Dashboard'))
    with col_h2:
        if st.button("🔄", key="landlord_refresh"):
            st.rerun()
    with col_h3: logout_button()
    
    # col_h1, col_h2 = st.columns([4, 1])
    # with col_h1:
    #     st.header(tr('Landlord Dashboard'))
    # with col_h2:
    #     st.write("")
    #     st.write("")
    #     logout_button()

    landlord_email = st.session_state.user["email"]
    st.caption(f"Logged in as {landlord_email}")

    # === Prospective tenants who listed this landlord ===
    st.subheader(tr('Prospective Tenants (Listed You as Future Landlord)'))
    prospects = list_prospective_tenants(landlord_email)
    if not prospects:
        st.info(tr('No tenants have listed you as a future landlord yet.'))
    else:
        for (tid, tname, temail, updated_at) in prospects:
            with st.container(border=True):
                st.markdown(f"**{tname}** · {temail}")
                # st.caption(f"Profile last updated: {updated_at}")
                # Average score across COMPLETED references (latest per previous landlord)
                refs = list_latest_references_for_tenant(tid) or []
                scores = []
                for r in refs:
                    status = r[6]  # 'status' from list_latest_references_for_tenant
                    score  = r[7]  # 'score'
                    if status == "completed" and score is not None:
                        scores.append(score)
                if len(scores) == 1:
                    st.metric("Score", f"{scores[0]:.1f}/10")
                elif len(scores) >= 2:
                    avg = sum(scores) / len(scores)
                    st.metric("Average score", f"{avg:.1f}/10")
                    st.caption(f"Based on {len(scores)} completed references.")

                # Show latest reference status per previous landlord for this tenant
                refs = list_latest_references_for_tenant(tid)
                # keep rows where status is None or not "cancelled"
                refs = [r for r in refs if (r[6] is None) or (str(r[6]).lower() != "cancelled")]

                if refs:
                    for (
                        prev_id, prev_name, prev_email, prev_afm, prev_addr,
                        token, status, score, paid_on_time, utilities_unpaid,
                        good_condition, comments, created_at, filled_at
                    ) in refs:

                        # Map raw status -> display key, then translate
                        display_status_key = {
                            None: "not requested",
                            "pending": "Pending",
                            "completed": "Completed",
                            "cancelled": "Cancelled",
                        }.get((status or "").lower() if status else None, status or "not requested")
                        display_status = tr(display_status_key)

                        # Expander title (fix quote nesting + translate labels)
                        with st.expander(
                            f"{tr('Reference from')} ({prev_email}) — {tr('**Status:**')} {display_status}"
                        ):
                            if status == "completed":
                                st.markdown(f"{tr('**Score:**')} {score}/10")
                                st.markdown(f"{tr('**Paid on time:**')} {tr('Yes') if paid_on_time else tr('No')}")
                                st.markdown(f"{tr('**Utilities unpaid:**')} {tr('Yes') if utilities_unpaid else tr('No')}")
                                st.markdown(f"{tr('**Apartment in good condition:**')} {tr('Yes') if good_condition else tr('No')}")
                                if comments:
                                    st.markdown(tr('**Comments:**'))
                                    st.write(comments)

                # # Show latest reference status per previous landlord for this tenant
                # refs = list_latest_references_for_tenant(tid)
                # refs = [r for r in refs if (r[6] is None) or (r[6] != "cancelled")]
                # if refs:
                #     for (prev_id, prev_name, prev_email, prev_addr, token, status, score, paid_on_time, utilities_unpaid, good_condition, comments, created_at, filled_at) in refs:
                #         with st.expander(f"{tr("Reference from")} ({prev_email}) — {tr("Status:")} {status if status else 'not requested'}"):
                            
                            
                #             if status == "completed":
                #                 st.markdown(f"{tr('**Score:**')} {score}/10")
                #                 st.markdown(f"{tr('**Paid on time:**')} {tr('Yes') if paid_on_time else tr('No')}")
                #                 st.markdown(f"{tr('**Utilities unpaid:**')} {tr('Yes') if utilities_unpaid else tr('No')}")
                #                 st.markdown(f"{tr('**Apartment in good condition:**')} {tr('Yes') if good_condition else tr('No')}")

                                if comments:
                                    st.markdown(tr('**Comments:**'))
                                    st.write(comments)
                                # st.write(f"tr(**Score:**) {score}/10")
                                # st.write(f"tr(**Paid on time:**) {tr('Yes') if paid_on_time else tr('No')}")
                                # st.write(f"tr(**Utilities unpaid:**) {tr('Yes') if utilities_unpaid else tr('No')}")
                                # st.write(f"tr(**Apartment in good condition:**) {tr('Yes') if good_condition else tr('No')}")
                                # if comments:
                                #     st.write("tr(**Comments:**)")
                                #     st.write(comments)
                else:
                    st.caption(tr("No previous landlords listed yet."))

    st.divider()

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
                cols[2].markdown(f"{tr('**Created:**')} {created_at}")
                cols[3].markdown(f"{tr('**Score:**')} {score if score is not None else '—'}")

                # cols[0].markdown(f"tr(**Tenant:**) {tenant_label}<br/>tr(**Email:**) {tenant_email}", unsafe_allow_html=True)
                # cols[1].markdown(f"tr(**Status:**) {status}")
                # cols[2].markdown(f"tr(**Created:**) {created_at}")
                # cols[3].markdown(f"tr(**Score:**) {score if score is not None else '—'}")
                st.caption(f"📍 **{tr('Address')}:** {address}")

                if status == "pending":
                    # If landlord already submitted, show a read-only summary instead of the form
                    if details and details.get("confirm_landlord"):
                        with st.expander(tr('Respond Now'), expanded=True):
                            st.info(tr("Thanks — your response is saved. The request will complete once the tenant’s contract is verified by an admin."))
                            st.write(f"**{tr('Overall tenant score')}:** {details.get('score')}/10")
                            st.write(f"**{tr('Did the tenant pay on time?')}:** {'Yes' if details.get('paid_on_time') else 'No'}")
                            st.write(f"**{tr('Did the tenant leave utilities unpaid?')}:** {'Yes' if details.get('utilities_unpaid') else 'No'}")
                            st.write(f"**{tr('Did the tenant leave the apartment in good condition?')}:** {'Yes' if details.get('good_condition') else 'No'}")
                            if details.get('comments'):
                                st.write("**" + tr('Optional comments') + ":**")
                                st.write(details['comments'])
                    else:
                        with st.expander(tr('Respond Now')):
                            with st.form(f"{prefix}_landlord_response_{token}"):
                                # ✅ GDPR-compliant consent text (translatable via tr)
                                confirm = st.checkbox(
                                    tr(
                                        "I confirm that I was the landlord for this tenant. "
                                        "By checking this box, I consent to the use of the uploaded tenancy contract "
                                        "solely for verifying my relationship with the tenant and for completing this reference. "
                                        "The contract will remain encrypted and locked until I provide this confirmation. "
                                        "It will not be shared or used for any other purpose, in accordance with GDPR."
                                    ),
                                    key=f"{prefix}_confirm_{token}"
                                )

                                s = st.slider(
                                    tr('Overall tenant score'), 1, 10, 8,
                                    key=f"{prefix}_score_{token}"
                                )
                                paid_on_time = st.radio(
                                    tr('Did the tenant pay on time?'), ["Yes","No"],
                                    horizontal=True, key=f"{prefix}_paid_{token}"
                                )
                                utilities_unpaid = st.radio(
                                    tr('Did the tenant leave utilities unpaid?'), ["No","Yes"],
                                    horizontal=True, key=f"{prefix}_utilities_{token}"
                                )
                                good_condition = st.radio(
                                    tr('Did the tenant leave the apartment in good condition?'), ["Yes","No"],
                                    horizontal=True, key=f"{prefix}_condition_{token}"
                                )
                                comments = st.text_area(
                                    tr('Optional comments'),
                                    key=f"{prefix}_comments_{token}"
                                )

                                col_a, col_b = st.columns([1,1])
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
                                        paid_on_time=(paid_on_time == "Yes"),
                                        utilities_unpaid=(utilities_unpaid == "Yes"),
                                        good_condition=(good_condition == "Yes"),
                                        comments=comments,
                                    )
                                    st.success(tr('Reference submitted successfully.'))
                                    st.rerun()

                            if cancel_btn:
                                cancel_reference_request(token)
                                st.warning(tr('Request cancelled.'))
                                st.rerun()


    # def render_requests(reqs, prefix: str):
    #     if not reqs:
    #         st.info(tr('No requests found.'))
    #         return

    #     for (token, tenant_id, created_at, status, score) in reqs:
    #         tenant = get_user_by_id(tenant_id)
    #         with st.container(border=True):
    #             cols = st.columns([3,2,3,2])
    #             tenant_label = tenant["name"] if tenant else f"Tenant #{tenant_id}"
    #             cols[0].markdown(f"**Tenant:** {tenant_label}")
    #             cols[1].markdown(f"**Status:** {status}")
    #             cols[2].markdown(f"**Created:** {created_at}")
    #             cols[3].markdown(f"**Score:** {score if score is not None else '—'}")
                
    #             if status == "pending":
    #                 details = get_reference_request_by_token(token)

    #                 # If landlord already submitted, show a read-only summary instead of the form
    #                 if details and details.get("confirm_landlord"):
    #                     with st.expander(tr('Respond Now'), expanded=True):
    #                         st.info(tr("Thanks — your response is saved. The request will complete once the tenant’s contract is verified by an admin."))
    #                         st.write(f"**{tr('Overall tenant score')}:** {details.get('score')}/10")
    #                         st.write(f"**{tr('Did the tenant pay on time?')}:** {'Yes' if details.get('paid_on_time') else 'No'}")
    #                         st.write(f"**{tr('Did the tenant leave utilities unpaid?')}:** {'Yes' if details.get('utilities_unpaid') else 'No'}")
    #                         st.write(f"**{tr('Did the tenant leave the apartment in good condition?')}:** {'Yes' if details.get('good_condition') else 'No'}")
    #                         if details.get('comments'):
    #                             st.write("**" + tr('Optional comments') + ":**")
    #                             st.write(details['comments'])
    #                 else:
    #                     with st.expander(tr('Respond Now')):
    #                         with st.form(f"{prefix}_landlord_response_{token}"):
    #                             confirm = st.checkbox(
    #                                 tr('I confirm I was the landlord for this tenant.'),
    #                                 key=f"{prefix}_confirm_{token}"
    #                             )
    #                             s = st.slider(
    #                                 tr('Overall tenant score'), 1, 10, 8,
    #                                 key=f"{prefix}_score_{token}"
    #                             )
    #                             paid_on_time = st.radio(
    #                                 tr('Did the tenant pay on time?'), ["Yes","No"],
    #                                 horizontal=True, key=f"{prefix}_paid_{token}"
    #                             )
    #                             utilities_unpaid = st.radio(
    #                                 tr('Did the tenant leave utilities unpaid?'), ["No","Yes"],
    #                                 horizontal=True, key=f"{prefix}_utilities_{token}"
    #                             )
    #                             good_condition = st.radio(
    #                                 tr('Did the tenant leave the apartment in good condition?'), ["Yes","No"],
    #                                 horizontal=True, key=f"{prefix}_condition_{token}"
    #                             )
    #                             comments = st.text_area(
    #                                 tr('Optional comments'),
    #                                 key=f"{prefix}_comments_{token}"
    #                             )

    #                             col_a, col_b = st.columns([1,1])
    #                             submit = col_a.form_submit_button(tr('Submit Reference'))
    #                             cancel_btn = col_b.form_submit_button(tr('Not My Tenant / Cancel'))

    #                         if submit:
    #                             if not confirm:
    #                                 st.error(tr('Please confirm you were the landlord.'))
    #                             else:
    #                                 mark_reference_completed(
    #                                     token,
    #                                     confirm_landlord=True,
    #                                     score=int(s),
    #                                     paid_on_time=(paid_on_time == "Yes"),
    #                                     utilities_unpaid=(utilities_unpaid == "Yes"),
    #                                     good_condition=(good_condition == "Yes"),
    #                                     comments=comments,
    #                                 )
    #                                 st.success(tr('Reference submitted successfully.'))
    #                                 st.rerun()

    #                         if cancel_btn:
    #                             cancel_reference_request(token)
    #                             st.warning(tr('Request cancelled.'))
    #                             st.rerun()


                # if status == "pending":
                #     # ❌ no key here
                #     with st.expander(tr('Respond Now')):
                #         # forms use a positional key/name, not key=...
                #         with st.form(f"{prefix}_landlord_response_{token}"):
                #             confirm = st.checkbox(
                #                 tr('I confirm I was the landlord for this tenant.'),
                #                 key=f"{prefix}_confirm_{token}"
                #             )
                #             s = st.slider(
                #                 tr('Overall tenant score'), 1, 10, 8,
                #                 key=f"{prefix}_score_{token}"
                #             )
                #             paid_on_time = st.radio(
                #                 tr('Did the tenant pay on time?'), ["Yes","No"],
                #                 horizontal=True, key=f"{prefix}_paid_{token}"
                #             )
                #             utilities_unpaid = st.radio(
                #                 tr('Did the tenant leave utilities unpaid?'), ["No","Yes"],
                #                 horizontal=True, key=f"{prefix}_utilities_{token}"
                #             )
                #             good_condition = st.radio(
                #                 tr('Did the tenant leave the apartment in good condition?'), ["Yes","No"],
                #                 horizontal=True, key=f"{prefix}_condition_{token}"
                #             )
                #             comments = st.text_area(
                #                 tr('Optional comments'),
                #                 key=f"{prefix}_comments_{token}"
                #             )

                #             col_a, col_b = st.columns([1,1])
                #             # ❌ form_submit_button has no key=
                #             submit = col_a.form_submit_button(tr('Submit Reference'))
                #             cancel_btn = col_b.form_submit_button(tr('Not My Tenant / Cancel'))

                #         if submit:
                #             if not confirm:
                #                 st.error(tr('Please confirm you were the landlord.'))
                #             else:
                #                 mark_reference_completed(
                #                     token,
                #                     confirm_landlord=True,
                #                     score=int(s),
                #                     paid_on_time=(paid_on_time == "Yes"),
                #                     utilities_unpaid=(utilities_unpaid == "Yes"),
                #                     good_condition=(good_condition == "Yes"),
                #                     comments=comments,
                #                 )
                #                 st.success(tr('Reference submitted successfully.'))
                #                 st.rerun()

                #         if cancel_btn:
                #             cancel_reference_request(token)
                #             st.warning(tr('Request cancelled.'))
                #             st.rerun()

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



