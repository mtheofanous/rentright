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

# ⚠️ set_page_config must be the first Streamlit command
st.set_page_config(page_title="RentRight", page_icon="🏠", layout="centered")

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
        return False, "Faltan datos SMTP: host/port/user/pass/from o destinatario."

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


DB_PATH = "rental_app.db"

UPLOAD_DIR = Path("uploads") / "contracts"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------- Utilities ----------
@st.cache_resource
def get_conn():
    # one shared connection per process/session
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    # improve concurrent behavior
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")  # wait up to 5s if locked
    return conn


@st.cache_resource
def init_db():
    conn = get_conn()
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
            afm TEXT NOT NULL,
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

def invite_future_landlord(tenant_id: int, email: str, tenant_name: str, tenant_email: str):
    base = st.session_state.get("app_base_url") or (st.secrets.get("APP_BASE_URL") if hasattr(st, "secrets") else "")
    join_link = base if base else ""
    subject = f"{tenant_name} quiere conectar contigo en RentRight"
    body = (
        "Hola,\n\n"
        f"{tenant_name} ({tenant_email}) te ha añadido como futuro casero/a en RentRight.\n"
        + (f"Puedes iniciar sesión o crear cuenta aquí: {join_link}\n\n" if join_link else "")
        + "Gracias."
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
    st.subheader("Log in")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
        
    if submitted:
        user = get_user_by_email(email)
        if not user or user["password_hash"] != hash_password(password):
            st.error("Invalid email or password.")
            return
        st.session_state.user = {k: user[k] for k in ["id","email","name","role"]}
        st.success(f"Welcome {user['name']}!")


def signup_form():
    st.subheader("Create account")
    with st.form("signup_form"):
        name = st.text_input("Full name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["tenant","landlord"], format_func=lambda x: x.capitalize())
        password = st.text_input("Password", type="password")
        password2 = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Sign up")
    if submitted:
        if not name.strip():
            st.error("Name is required")
            return
        if not is_valid_email(email):
            st.error("Enter a valid email")
            return
        if password != password2:
            st.error("Passwords do not match")
            return
        if get_user_by_email(email):
            st.error("Email already exists")
            return
        create_user(email, name, password, role)
        st.success("Account created, you can log in.")
        # 🔁 redirect back to landing/login
        st.session_state.signup_done = True
        st.rerun()


# def auth_gate():
#     if "user" not in st.session_state:
#         st.session_state.user = None
#     tab1, tab2 = st.tabs(["Log in","Sign up"])
#     with tab1:
#         login_form()

#     with tab2:
#         signup_form()
        
def auth_gate():
    if "user" not in st.session_state:
        st.session_state.user = None

    # If user just signed up, show a one-time success + only the Login form
    if st.session_state.get("signup_done"):
        st.success("Account created — please log in.")
        login_form()
        # reset so it doesn't persist across reruns
        st.session_state.signup_done = False
        return

    # Default: both tabs
    tab1, tab2 = st.tabs(["Log in","Sign up"])
    with tab1:
        login_form()
    with tab2:
        signup_form()



def logout_button():
    if st.button("Log out"):
        st.session_state.user = None
        st.rerun()

# ---------- Tenant data helpers ----------
import os
from pathlib import Path

UPLOAD_DIR = Path("uploads") / "contracts"
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

    # Size (max 15 MB)
    try:
        size = len(uploaded_file.getbuffer())
    except Exception:
        # fallback
        data = uploaded_file.read()
        size = len(data)
        uploaded_file = type("Tmp", (), {"read": lambda self=data: self, "type": "application/octet-stream"})()
    if size > 15 * 1024 * 1024:
        return False, "File too large (max 15 MB)."

    # Save file under uploads/contracts/<token>/<filename>
    folder = UPLOAD_DIR / token
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    with open(path, "wb") as f:
        f.write(uploaded_file.read())

    now = datetime.utcnow().isoformat()
    cur = conn.cursor()
    existing = get_contract_by_token(token)
    if existing:
        cur.execute(
            """
            UPDATE reference_contracts
               SET filename=?, content_type=?, path=?, size_bytes=?,
                   uploaded_at=?, status='pending', status_updated_at=?, status_by=NULL
             WHERE token=?
            """,
            (name, getattr(uploaded_file, "type", None) or "application/octet-stream",
             str(path), size, now, now, token),
        )
    else:
        cur.execute(
            """
            INSERT INTO reference_contracts(token, tenant_id, filename, content_type, path, size_bytes,
                                            status, status_updated_at, status_by, uploaded_at)
            VALUES (?,?,?,?,?,?, 'pending', ?, NULL, ?)
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

    cur = conn.cursor()
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
        return "✅ Verified"
    if s == "rejected":
        return "❌ Rejected"
    return "🕒 Pending"



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


def add_previous_landlord(tenant_id: int, email: str, afm: str, name: str, address: str):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO previous_landlords(tenant_id, email, afm, name, address, created_at) VALUES (?,?,?,?,?,?)",
        (tenant_id, email.strip(), afm.strip(), name.strip(), address.strip(), datetime.utcnow().isoformat()),
    )
    conn.commit()


def list_previous_landlords(tenant_id: int):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, afm, name, address, created_at FROM previous_landlords WHERE tenant_id = ? ORDER BY id DESC",
        (tenant_id,),
    )
    return cur.fetchall()


def delete_previous_landlord(entry_id: int, tenant_id: int):
    cur = conn.cursor()
    cur.execute("DELETE FROM previous_landlords WHERE id = ? AND tenant_id = ?", (entry_id, tenant_id))
    conn.commit()

# ---------- References helpers ----------

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
    cur.execute("UPDATE reference_requests SET status='cancelled' WHERE token=? AND status='pending'", (token,))
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


# def list_prospective_tenants(landlord_email: str):
#     """Return tenants who listed landlord_email as their future landlord."""
#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT u.id, u.name, u.email, tp.updated_at
#         FROM tenant_profiles tp
#         JOIN users u ON u.id = tp.tenant_id
#         WHERE LOWER(tp.future_landlord_email) = LOWER(?)
#         ORDER BY tp.updated_at DESC
#         """,
#         (landlord_email,),
#     )
#     return cur.fetchall()


def list_latest_references_for_tenant(tenant_id: int):
    """Return each previous landlord with the latest (most recent) reference request, if any, and its answers."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pl.id AS prev_id,
               pl.name AS prev_name,
               pl.email AS prev_email,
               pl.afm AS prev_afm,
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


# def build_reference_link(token: str) -> str:
#     base = st.session_state.get("app_base_url")
#     if base and base.strip():
#         base = base.strip().rstrip('/')
#         return f"{base}/?ref={token}"
#     return f"http://localhost:8501/?ref={token}"

def build_reference_link(token: str) -> str:
    base = st.session_state.get("app_base_url") or (st.secrets.get("APP_BASE_URL") if hasattr(st, "secrets") else "")
    if base:
        base = base.strip().rstrip("/")
        return f"{base}/?ref={token}"
    # fallback that still works when clicked inside the app
    return f"?ref={token}"


def email_reference_request(tenant_name: str, tenant_email: str, landlord_email: str, link: str):
    subject = f"Reference request for tenant {tenant_name}"
    body = (
        f"Hello,\n\n"
        f"{tenant_name} ({tenant_email}) listed you as a previous landlord and is requesting a short reference.\n"
        f"Please confirm and fill the form here: {link}\n\n"
        f"Thank you!"
    )
    return send_email_smtp(landlord_email, subject, body)

# ---------- Landlord Reference Portal (public) ----------

def reference_portal(token: str):
    st.title("🏠 RentRight — Landlord Reference")
    data = get_reference_request_by_token(token)
    if not data:
        st.error("Invalid or expired reference token.")
        return

    if data["status"] == "completed":
        st.success("This reference has already been submitted. Thank you!")
        st.stop()

    st.info(f"Reference for tenant ID #{data['tenant_id']} — sent to {data['landlord_email']}")
    with st.form("reference_form"):
        confirm = st.checkbox("I confirm I was the landlord for this tenant.")
        score = st.slider("Overall tenant score", min_value=1, max_value=10, value=8)
        paid_on_time = st.radio("Did the tenant pay on time?", ["Yes","No"], horizontal=True)
        utilities_unpaid = st.radio("Did the tenant leave utilities unpaid?", ["No","Yes"], horizontal=True)
        good_condition = st.radio("Did the tenant leave the apartment in good condition?", ["Yes","No"], horizontal=True)
        comments = st.text_area("Optional comments")
        submit = st.form_submit_button("Submit reference")

    if submit:
        if not confirm:
            st.error("You must confirm you were the landlord.")
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
        st.success("Reference submitted. Thank you!")


def admin_dashboard():
    st.header("Admin Dashboard")
    st.caption(f"Signed in as {st.session_state.user['email']}")

    # ---------------- Settings moved from sidebar ----------------
    with st.expander("Email & App Settings"):
        st.subheader("Email settings (SMTP)")
        st.session_state.smtp_host = st.text_input("SMTP host", value=st.session_state.get("smtp_host", ""))
        st.session_state.smtp_port = st.number_input("SMTP port", value=int(st.session_state.get("smtp_port", 587)))
        st.session_state.smtp_user = st.text_input("SMTP username", value=st.session_state.get("smtp_user", ""))
        st.session_state.smtp_pass = st.text_input("SMTP password", type="password", value=st.session_state.get("smtp_pass", ""))
        st.session_state.smtp_from = st.text_input("From email (optional)", value=st.session_state.get("smtp_from", ""))
        st.session_state.smtp_tls = st.checkbox("Use TLS", value=st.session_state.get("smtp_tls", True))

        st.markdown("---")
        st.subheader("App base URL")
        st.session_state.app_base_url = st.text_input(
            "Base URL for links",
            value=st.session_state.get("app_base_url", ""),
            help="e.g., https://yourdomain.com"
        )
                # --- SMTP quick test ---
        st.markdown("---")
        st.caption("Enviar correo de prueba")
        test_to = st.text_input(
            "Enviar test a",
            value=st.session_state.get("smtp_user", ""),
            key="admin_test_to",
        )
        if st.button("Send test email", key="admin_send_test_email"):
            try:
                ok, msg = send_email_smtp(
                    to_email=test_to,
                    subject="RentRight SMTP Test",
                    body="Si recibiste este correo, tu SMTP está OK. ✅",
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
                    _msg = MIMEText("Si recibiste este correo, tu SMTP está OK. ✅", "plain")
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
                st.success("Correo de prueba enviado.")
            else:
                st.error(f"Fallo al enviar: {msg}")

    st.markdown("---")

    # ---------------- Pending references management ----------------
    st.subheader("Pending References (global)")

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
    c3.metric("Cancelled", len(cancelled_reqs))

    tab_pending, tab_completed, tab_cancelled = st.tabs(["Pending", "Completed", "Cancelled"])

    # def render_admin_reqs(reqs, prefix: str):
    #     if not reqs:
    #         st.info("No items.")
    #         return
    #     for (token, tenant_id, landlord_email, created_at, status, score) in reqs:
    #         tenant = get_user_by_id(tenant_id)
    #         tenant_label = tenant["name"] if tenant else f"Tenant #{tenant_id}"
    #         final_status = effective_reference_status(status, token)

    #         with st.container(border=True):
    #             cols = st.columns([3, 3, 3, 2])
    #             cols[0].markdown(f"**Tenant:** {tenant_label} ({tenant['email'] if tenant else '—'})")
    #             cols[1].markdown(f"**To landlord:** {landlord_email}")
    #             cols[2].markdown(f"**Created:** {created_at}")
    #             cols[3].markdown(f"**Status:** {final_status}")
    def render_admin_reqs(reqs, prefix: str):
        if not reqs:
            st.info("No items.")
            return

        for (token, tenant_id, landlord_email, created_at, status, score) in reqs:
            tenant = get_user_by_id(tenant_id)
            tenant_label = tenant["name"] if tenant else f"Tenant #{tenant_id}"
            final_status = effective_reference_status(status, token)

            # Fetch request details and previous landlord info
            details = get_reference_request_by_token(token)
            pl_name = pl_afm = pl_email = pl_addr = "—"
            if details and details.get("prev_landlord_id"):
                cur = conn.cursor()
                cur.execute(
                    "SELECT name, afm, email, address FROM previous_landlords WHERE id=?",
                    (details["prev_landlord_id"],),
                )
                row = cur.fetchone()
                if row:
                    pl_name, pl_afm, pl_email, pl_addr = row

            with st.container(border=True):
                cols = st.columns([3, 3, 3, 2])
                cols[0].markdown(f"**Tenant:** {tenant_label} ({tenant['email'] if tenant else '—'})")
                cols[1].markdown(f"**To landlord:** {landlord_email}")
                cols[2].markdown(f"**Created:** {created_at}")
                cols[3].markdown(f"**Status:** {final_status}")

                # ⬇️ Show previous landlord Name + AFM
             
                st.caption(f"Previous landlord: **{pl_name}** ({pl_email}) · AFM: **{pl_afm}** · Address: {pl_addr}")


                link = build_reference_link(token)
                st.text_input("Reference link", value=link, key=f"{prefix}_link_{token}", disabled=True)

                # --- Contract section ---
                contract = get_contract_by_token(token)
                if contract:
                    st.markdown(f"**Contract:** {contract['filename']} · {contract_status_badge(contract['status'])}")
                    st.caption(
                        f"Uploaded: {contract['uploaded_at']} • "
                        f"Last status update: {contract['status_updated_at'] or '—'}"
                        + (f" • by {contract['status_by']}" if contract['status_by'] else "")
                    )
                    try:
                        with open(contract["path"], "rb") as f:
                            st.download_button(
                                "Download contract",
                                data=f.read(),
                                file_name=contract["filename"],
                                mime=contract["content_type"],
                                key=f"{prefix}_dl_{token}",
                            )
                    except Exception as e:
                        st.warning(f"Could not read saved file: {e}")
                else:
                    st.caption("No contract uploaded yet.")

                # --- Admin actions ---
                ac1, ac2 = st.columns(2)
                if ac1.button("✅ Verify contract", key=f"{prefix}_verify_{token}"):
                    ok, msg = set_contract_status(token, "verified", st.session_state.user["email"])
                    if ok:
                        # Try to promote to completed if the landlord already submitted the reference
                        promote_reference_if_ready(token)
                        st.success("Contract verified.")
                        st.rerun()
                    else:
                        st.error(msg)

                if ac2.button("🛑 Cancel reference", key=f"{prefix}_cancel_{token}"):
                    cancel_reference_request(token)
                    st.warning("Reference cancelled.")
                    st.rerun()


    with tab_pending:
        render_admin_reqs(pending_reqs, "admin_pending")
    with tab_completed:
        render_admin_reqs(completed_reqs, "admin_completed")
    with tab_cancelled:
        render_admin_reqs(cancelled_reqs, "admin_cancelled")

    st.markdown("---")
    logout_button()

    
def tenant_dashboard():
    # Helper: show 'pending' if a contract exists but isn't verified yet
    # def effective_reference_status(raw_status: str | None, token: str) -> str:
    #     # Keep 'cancelled' as-is
    #     if raw_status == "cancelled":
    #         return "cancelled"
    #     contract = get_contract_by_token(token)
    #     # If a contract exists and isn't verified, force pending
    #     if contract and contract.get("status") != "verified":
    #         return "pending"
    #     # Otherwise fall back to the raw status (or pending if None)
    #     return raw_status or "pending"

    # Header with a visible Log out button on the main page
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.header("Tenant Portal")
    with col_h2:
        st.write("")
        st.write("")
        logout_button()

    # === Future landlord email ===
    st.subheader("Future Landlords")

    # Add multiple future landlord emails
    # with st.form("future_landlords_add_form"):
    #     new_fl_email = st.text_input("Add a future landlord email")
    #     add_fl = st.form_submit_button("Add email")
    # if add_fl:
    #     if not new_fl_email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", new_fl_email):
    #         st.error("Please enter a valid email.")
    #     else:
    #         try:
    #             add_future_landlord_contact(st.session_state.user["id"], new_fl_email)
    #             st.success("Added.")
    #         except Exception as e:
    #             st.warning(f"Could not add: {e}")
    with st.form("future_landlords_add_form"):
        new_fl_email = st.text_input("Add a future landlord email")
        add_fl = st.form_submit_button("Add email")
    if add_fl:
        if not new_fl_email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", new_fl_email):
            st.error("Please enter a valid email.")
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
                    st.success("Added and invitation sent.")
                    st.rerun()  # refresh list to show 'Invited' status
                else:
                    st.warning(f"Added, but email not sent: {msg}")
            except Exception as e:
                st.warning(f"Could not add: {e}")


    # List + actions (send connection / remove)
    fl_rows = list_future_landlord_contacts(st.session_state.user["id"]) or []
    if fl_rows:
        for (cid, fl_email, created_at, invited, invited_at) in fl_rows:
            with st.container(border=True):
                cols = st.columns([4,2,2,2])
                cols[0].markdown(f"**{fl_email}**")
                cols[1].caption(f"Added: {created_at}")
                if invited:
                    cols[2].success("Invited")
                    cols[3].caption(f"At: {invited_at}")
                else:
                    if cols[2].button("Send connection", key=f"invite_fl_{cid}"):
                        ok, msg = invite_future_landlord(
                            st.session_state.user["id"],
                            fl_email,
                            st.session_state.user["name"],
                            st.session_state.user["email"],
                        )
                        if ok:
                            st.success("Invitation sent.")
                            st.rerun()
                        else:
                            st.error(f"Could not send: {msg}")
                    if cols[3].button("Remove", key=f"remove_fl_{cid}"):
                        remove_future_landlord_contact(cid, st.session_state.user["id"])
                        st.info("Removed.")
                        st.rerun()
    else:
        st.caption("No future landlords yet.")

    st.divider()

    # st.subheader("Future Landlord Contact")
    # profile = load_tenant_profile(st.session_state.user["id"])
    # current_email = profile["future_landlord_email"] if profile else ""

    # with st.form("future_landlord_form"):
    #     future_email = st.text_input("Future landlord email", value=current_email)
    #     save = st.form_submit_button("Save")
    # if save:
    #     if future_email and not is_valid_email(future_email):
    #         st.error("Please provide a valid email address for the future landlord.")
    #     else:
    #         upsert_tenant_profile(st.session_state.user["id"], future_email or None)
    #         st.success("Saved future landlord email.")

    # st.divider()

    # === Previous landlords + reference requests ===
    st.subheader("Previous Landlords & References")
    with st.form("previous_landlord_form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            pl_email = st.text_input("Email")
            pl_afm = st.text_input("AFM (9 digits)")
        with col2:
            pl_name = st.text_input("Name")
            pl_address = st.text_input("Address")
        add = st.form_submit_button("Add previous landlord")
    if add:
        if not (pl_email and is_valid_email(pl_email)):
            st.error("Enter a valid email.")
        elif not is_valid_afm(pl_afm):
            st.error("AFM must be exactly 9 digits.")
        elif not pl_name.strip():
            st.error("Name is required.")
        elif not pl_address.strip():
            st.error("Address is required.")
        else:
            add_previous_landlord(st.session_state.user["id"], pl_email, pl_afm, pl_name, pl_address)
            st.success("Added previous landlord.")

    rows = list_previous_landlords(st.session_state.user["id"]) or []
    st.subheader("All Reference Requests")
    if rows:
        for (pid, email, afm, name, address, created_at) in rows:
            with st.expander(f"{name} • {email}"):
                st.write(f"**AFM:** {afm}")
                st.write(f"**Address:** {address}")
                st.caption(f"Added on {created_at}")

                c1, c2 = st.columns([1, 2])
                with c1:
                    if st.button("Request reference", key=f"req_{pid}"):
                        rec = create_reference_request(st.session_state.user["id"], pid, email)
                        link = build_reference_link(rec["token"])
                        ok, msg = email_reference_request(
                            st.session_state.user["name"], st.session_state.user["email"], email, link
                        )
                        if ok:
                            st.success("Reference request sent via email.")
                        else:
                            st.warning(f"Email not sent ({msg}). Here's the link to share:")
                            st.code(link)
                with c2:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT token, status, created_at, score FROM reference_requests WHERE prev_landlord_id=? ORDER BY id DESC",
                        (pid,),
                    )
                    reqs = cur.fetchall()
                    if reqs:
                        for (tok, status, created_at2, score) in reqs:
                            # Use the effective status (gated by contract verification)
                            final_status = effective_reference_status(status, tok)

                            colA, colB, colC = st.columns([2, 2, 2])
                            colA.write(f"Status: **{final_status}**")  # <-- final status here
                            if score is not None:
                                colB.write(f"Score: **{score}**/10")
                            link = build_reference_link(tok)
                            colC.write(link)

                            # --- Contract upload / status per request token ---
                            contract = get_contract_by_token(tok)

                            if contract:
                                st.markdown(f"**Contract status:** {contract_status_badge(contract['status'])}")
                                st.caption(
                                    f"Uploaded: {contract['uploaded_at']} • "
                                    f"Last status update: {contract['status_updated_at'] or '—'}"
                                    + (f" • by {contract['status_by']}" if contract['status_by'] else "")
                                )
                                # Download button
                                try:
                                    with open(contract["path"], "rb") as f:
                                        st.download_button(
                                            "Download contract",
                                            data=f.read(),
                                            file_name=contract["filename"],
                                            mime=contract["content_type"],
                                            key=f"dl_{tok}",
                                        )
                                except Exception as e:
                                    st.warning(f"Could not read saved file: {e}")

                                # Replace upload (resets status to Pending)
                                uploaded = st.file_uploader(
                                    "Replace contract (PDF or image)",
                                    type=["pdf", "png", "jpg", "jpeg", "webp"],
                                    key=f"up_{tok}",
                                )
                                if uploaded is not None:
                                    ok, msg = save_contract_upload(tok, st.session_state.user["id"], uploaded)
                                    if ok:
                                        st.success("Contract uploaded (status reset to Pending).")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            else:
                                st.markdown("**Contract status:** 🕒 Pending (no file yet)")
                                uploaded = st.file_uploader(
                                    "Upload previous contract (PDF or image)",
                                    type=["pdf", "png", "jpg", "jpeg", "webp"],
                                    key=f"up_{tok}",
                                )
                                if uploaded is not None:
                                    ok, msg = save_contract_upload(tok, st.session_state.user["id"], uploaded)
                                    if ok:
                                        st.success("Contract uploaded (status set to Pending).")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            # --- End contract block ---
                    else:
                        st.caption("No reference requests yet.")
    else:
        st.info("No previous landlords added yet.")

    st.divider()

    # # === All Reference Requests ===
    
    # allreqs = list_reference_requests_for_tenant(st.session_state.user["id"]) or []
    # if allreqs:
    #     for (rid, tok, lmail, created_at, status, score) in allreqs:
    #         # Use effective status here too
    #         final_status = effective_reference_status(status, tok)

    #         cols = st.columns([3, 2, 3, 2])
    #         cols[0].write(f"To: **{lmail}**")
    #         cols[1].write(f"Status: **{final_status}**")  # <-- final status here
    #         cols[2].write(f"Link: {build_reference_link(tok)}")
    #         cols[3].write(f"Score: {score if score is not None else '-'}")

    #         # Show contract status & upload here as well (use different keys to avoid collisions with the section above)
    #         contract = get_contract_by_token(tok)
    #         if contract:
    #             st.markdown(f"**Contract status:** {contract_status_badge(contract['status'])}")
    #             st.caption(
    #                 f"Uploaded: {contract['uploaded_at']} • "
    #                 f"Last status update: {contract['status_updated_at'] or '—'}"
    #                 + (f" • by {contract['status_by']}" if contract['status_by'] else "")
    #             )
    #             try:
    #                 with open(contract["path"], "rb") as f:
    #                     st.download_button(
    #                         "Download contract",
    #                         data=f.read(),
    #                         file_name=contract["filename"],
    #                         mime=contract["content_type"],
    #                         key=f"all_dl_{tok}",
    #                     )
    #             except Exception as e:
    #                 st.warning(f"Could not read saved file: {e}")

    #             uploaded = st.file_uploader(
    #                 "Replace contract (PDF or image)",
    #                 type=["pdf", "png", "jpg", "jpeg", "webp"],
    #                 key=f"all_up_{tok}",
    #             )
    #             if uploaded is not None:
    #                 ok, msg = save_contract_upload(tok, st.session_state.user["id"], uploaded)
    #                 if ok:
    #                     st.success("Contract uploaded (status reset to Pending).")
    #                     st.rerun()
    #                 else:
    #                     st.error(msg)
    #         else:
    #             uploaded = st.file_uploader(
    #                 "Upload previous contract (PDF or image)",
    #                 type=["pdf", "png", "jpg", "jpeg", "webp"],
    #                 key=f"all_up_{tok}",
    #             )
    #             if uploaded is not None:
    #                 ok, msg = save_contract_upload(tok, st.session_state.user["id"], uploaded)
    #                 if ok:
    #                     st.success("Contract uploaded (status set to Pending).")
    #                     st.rerun()
    #                 else:
    #                     st.error(msg)
    # else:
    #     st.caption("No reference requests created yet.")


# ---------- Landlord Dashboard (enhanced) ----------

def landlord_dashboard():
    
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.header("Landlord Portal")
    with col_h2:
        st.write("")
        st.write("")
        logout_button()

    landlord_email = st.session_state.user["email"]
    st.caption(f"Signed in as {landlord_email}")

    # === Prospective tenants who listed this landlord ===
    st.subheader("Prospective Tenants (listed you as future landlord)")
    prospects = list_prospective_tenants(landlord_email)
    if not prospects:
        st.info("No tenants have listed you as their future landlord yet.")
    else:
        for (tid, tname, temail, updated_at) in prospects:
            with st.container(border=True):
                st.markdown(f"**{tname}** · {temail}")
                st.caption(f"Profile last updated: {updated_at}")
                # Average score across COMPLETED references (latest per previous landlord)
                refs = list_latest_references_for_tenant(tid) or []
                scores = []
                for r in refs:
                    status = r[6]  # 'status' from list_latest_references_for_tenant
                    score  = r[7]  # 'score'
                    if status == "completed" and score is not None:
                        scores.append(score)

                if len(scores) >= 2:  # only show if more than one reference
                    avg = sum(scores) / len(scores)
                    st.metric("Average score", f"{avg:.1f}/10")
                    st.caption(f"Based on {len(scores)} completed references.")

                # Show latest reference status per previous landlord for this tenant
                refs = list_latest_references_for_tenant(tid)
                refs = [r for r in refs if (r[6] is None) or (r[6] != "cancelled")]
                if refs:
                    for (prev_id, prev_name, prev_email, prev_afm, prev_addr, token, status, score, paid_on_time, utilities_unpaid, good_condition, comments, created_at, filled_at) in refs:
                        with st.expander(f"Reference from ({prev_email}) — Status: {status if status else 'not requested'}"):
                            
                            if token:
                                st.write(f"Request created: {created_at}")
                                st.write(f"Last update: {filled_at if filled_at else '—'}")
                            
                            if status == "completed":
                                st.write(f"**Score:** {score}/10")
                                st.write(f"**Paid on time:** {'Yes' if paid_on_time else 'No'}")
                                st.write(f"**Utilities unpaid:** {'Yes' if utilities_unpaid else 'No'}")
                                st.write(f"**Apartment in good condition:** {'Yes' if good_condition else 'No'}")
                                if comments:
                                    st.write("**Comments:**")
                                    st.write(comments)
                else:
                    st.caption("No previous landlords listed yet.")

    st.divider()

    # === Reference requests that were sent to this landlord ===
    st.subheader("Reference Requests Sent To You")

    # Quick stats
    all_reqs = list_reference_requests_for_landlord(landlord_email)
    pending_reqs = [r for r in all_reqs if r[3] == "pending"]
    completed_reqs = [r for r in all_reqs if r[3] == "completed"]
    cancelled_reqs = [r for r in all_reqs if r[3] == "cancelled"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Pending", len(pending_reqs))
    c2.metric("Completed", len(completed_reqs))
    c3.metric("Cancelled", len(cancelled_reqs))

    tab_all, tab_pending, tab_completed, tab_cancelled = st.tabs(["All", "Pending", "Completed", "Cancelled"])

    def render_requests(reqs, prefix: str):
        if not reqs:
            st.info("No requests found.")
            return

        for (token, tenant_id, created_at, status, score) in reqs:
            tenant = get_user_by_id(tenant_id)
            with st.container(border=True):
                cols = st.columns([3,2,3,2])
                tenant_label = tenant["name"] if tenant else f"Tenant #{tenant_id}"
                cols[0].markdown(f"**Tenant:** {tenant_label}")
                cols[1].markdown(f"**Status:** {status}")
                cols[2].markdown(f"**Created:** {created_at}")
                cols[3].markdown(f"**Score:** {score if score is not None else '—'}")

                link = build_reference_link(token)
                st.text_input("Reference link", value=link, key=f"{prefix}_link_{token}", disabled=True)

                if status == "pending":
                    # ❌ no key here
                    with st.expander("Respond now"):
                        # forms use a positional key/name, not key=...
                        with st.form(f"{prefix}_landlord_response_{token}"):
                            confirm = st.checkbox(
                                "I confirm I was the landlord for this tenant.",
                                key=f"{prefix}_confirm_{token}"
                            )
                            s = st.slider(
                                "Overall tenant score", 1, 10, 8,
                                key=f"{prefix}_score_{token}"
                            )
                            paid_on_time = st.radio(
                                "Did the tenant pay on time?", ["Yes","No"],
                                horizontal=True, key=f"{prefix}_paid_{token}"
                            )
                            utilities_unpaid = st.radio(
                                "Did the tenant leave utilities unpaid?", ["No","Yes"],
                                horizontal=True, key=f"{prefix}_utilities_{token}"
                            )
                            good_condition = st.radio(
                                "Did the tenant leave the apartment in good condition?", ["Yes","No"],
                                horizontal=True, key=f"{prefix}_condition_{token}"
                            )
                            comments = st.text_area(
                                "Optional comments",
                                key=f"{prefix}_comments_{token}"
                            )

                            col_a, col_b = st.columns([1,1])
                            # ❌ form_submit_button has no key=
                            submit = col_a.form_submit_button("Submit reference")
                            cancel_btn = col_b.form_submit_button("Not my tenant / Cancel")

                        if submit:
                            if not confirm:
                                st.error("Please confirm you were the landlord.")
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
                                st.success("Reference submitted.")
                                st.rerun()

                        if cancel_btn:
                            cancel_reference_request(token)
                            st.warning("Request cancelled.")
                            st.rerun()

                elif status == "completed":
                    # ❌ no key here
                    with st.expander("View submitted reference"):
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


# ---------- App ----------
def main():
    load_smtp_defaults()
    params = st.query_params
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

