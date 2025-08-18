import streamlit as st
import sqlite3
import re
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from uuid import uuid4
import os

# ⚠️ set_page_config must be the first Streamlit command
st.set_page_config(page_title="RentRight", page_icon="🏠", layout="wide")

DB_PATH = "rental_app.db"

# ---------- Utilities ----------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_resource
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT CHECK(role IN ("tenant","landlord")) NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tenant_profiles (
            tenant_id INTEGER UNIQUE NOT NULL,
            future_landlord_email TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
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
        """
    )
    cur.execute(
        """
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
        """
    )
    # Contracts table for uploaded tenancy agreements
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            prev_landlord_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            mime_type TEXT,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (prev_landlord_id) REFERENCES previous_landlords(id) ON DELETE CASCADE
        )
        """
    )
    # Add is_admin column to users if missing
    cur.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in cur.fetchall()]
    if "is_admin" not in cols:
        try:
            cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        except Exception:
            pass
    conn.commit()
    return conn

conn = init_db()

# File uploads directory
UPLOAD_DIR = os.path.join("uploads", "contracts")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    cur.execute(
        "SELECT id, email, name, password_hash, role, COALESCE(is_admin,0) FROM users WHERE email = ?",
        (email.lower().strip(),),
    )
    row = cur.fetchone()
    if row:
        keys = ["id","email","name","password_hash","role","is_admin"]
        return dict(zip(keys, row))
    return None


def get_user_by_id(uid: int):
    cur = conn.cursor()
    cur.execute("SELECT id, email, name, role, COALESCE(is_admin,0) FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if row:
        keys = ["id","email","name","role","is_admin"]
        return dict(zip(keys, row))
    return None

# ---------- Validation ----------

def is_valid_email(s: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s or "") is not None


def is_valid_afm(s: str) -> bool:
    return bool(re.fullmatch(r"\d{9}", (s or "").strip()))

# ---------- Email ----------

def send_email_smtp(to_email: str, subject: str, body: str):
    smtp_host = st.session_state.get("smtp_host")
    smtp_port = st.session_state.get("smtp_port", 587)
    smtp_user = st.session_state.get("smtp_user")
    smtp_pass = st.session_state.get("smtp_pass")
    smtp_from = st.session_state.get("smtp_from") or smtp_user
    use_tls = st.session_state.get("smtp_tls", True)

    if not all([smtp_host, smtp_port, smtp_user, smtp_pass, smtp_from]):
        return False, "SMTP settings incomplete"
    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = to_email
        with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [to_email], msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, str(e)

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
        st.session_state.user = {k: user[k] for k in ["id","email","name","role","is_admin"]}
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


def auth_gate():
    if "user" not in st.session_state:
        st.session_state.user = None
    tab1, tab2 = st.tabs(["Log in","Sign up"])
    with tab1:
        login_form()
    with tab2:
        signup_form()


def logout_button():
    if st.button("Log out"):
        st.session_state.user = None
        st.session_state.view_mode = "Dashboard"
        st.rerun()

# Small inline logout helper to place a logout button in page headers
def logout_inline(key: str):
    if st.button("Log out", key=key):
        st.session_state.user = None
        st.session_state.view_mode = "Dashboard"
        st.rerun()

# ---------- Tenant data helpers ----------

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

# ---------- References & Contracts helpers ----------

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


def mark_reference_completed(token: str, confirm_landlord: bool, score: int, paid_on_time: bool, utilities_unpaid: bool, good_condition: bool, comments: str | None):
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE reference_requests
        SET status='completed', filled_at=?, confirm_landlord=?, score=?, paid_on_time=?, utilities_unpaid=?, good_condition=?, comments=?
        WHERE token=?
        """,
        (
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
    """Return tenants who listed landlord_email as their future landlord."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.id, u.name, u.email, tp.updated_at
        FROM tenant_profiles tp
        JOIN users u ON u.id = tp.tenant_id
        WHERE LOWER(tp.future_landlord_email) = LOWER(?)
        ORDER BY tp.updated_at DESC
        """,
        (landlord_email,),
    )
    return cur.fetchall()


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

# ----- Contract storage helpers -----

def save_contract_file(tenant_id: int, prev_landlord_id: int, uploaded_file) -> int:
    """Persist an uploaded contract to disk and record metadata in DB."""
    _, ext = os.path.splitext(uploaded_file.name)
    ext = ext.lower()
    if ext not in [".pdf", ".png", ".jpg", ".jpeg"]:
        if uploaded_file.type == "application/pdf":
            ext = ".pdf"
        elif uploaded_file.type in ("image/png", "image/x-png"):
            ext = ".png"
        elif uploaded_file.type in ("image/jpeg", "image/jpg"):
            ext = ".jpg"
        else:
            ext = ""
    storage_name = f"{uuid4().hex}{ext}"
    storage_path = os.path.join(UPLOAD_DIR, storage_name)
    with open(storage_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO contracts(tenant_id, prev_landlord_id, file_name, file_path, mime_type, uploaded_at) VALUES (?,?,?,?,?,?)",
        (
            tenant_id,
            prev_landlord_id,
            uploaded_file.name,
            storage_path,
            uploaded_file.type,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_contracts_by_prev_landlord(prev_landlord_id: int):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, file_name, file_path, mime_type, uploaded_at FROM contracts WHERE prev_landlord_id = ? ORDER BY id DESC",
        (prev_landlord_id,),
    )
    return cur.fetchall()


def list_contracts_by_tenant(tenant_id: int):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, file_name, file_path, mime_type, uploaded_at FROM contracts WHERE tenant_id = ? ORDER BY id DESC",
        (tenant_id,),
    )
    return cur.fetchall()


def admin_list_contracts(search: str | None = None):
    cur = conn.cursor()
    if search and search.strip():
        like = f"%{search.strip()}%"
        cur.execute(
            """
            SELECT c.id, c.file_name, c.file_path, c.mime_type, c.uploaded_at,
                   u.id, u.name, u.email,
                   pl.name, pl.email, pl.afm, pl.address
            FROM contracts c
            JOIN users u ON u.id = c.tenant_id
            JOIN previous_landlords pl ON pl.id = c.prev_landlord_id
            WHERE u.email LIKE ? OR u.name LIKE ? OR pl.email LIKE ? OR pl.name LIKE ? OR pl.afm LIKE ?
            ORDER BY c.id DESC
            """,
            (like, like, like, like, like),
        )
    else:
        cur.execute(
            """
            SELECT c.id, c.file_name, c.file_path, c.mime_type, c.uploaded_at,
                   u.id, u.name, u.email,
                   pl.name, pl.email, pl.afm, pl.address
            FROM contracts c
            JOIN users u ON u.id = c.tenant_id
            JOIN previous_landlords pl ON pl.id = c.prev_landlord_id
            ORDER BY c.id DESC
            """
        )
    return cur.fetchall()

# ---------- Reference Portal (public) ----------

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

# ---------- Tenant Dashboard ----------

def tenant_dashboard():
    # Header with inline logout on the right
    left, right = st.columns([6,1])
    with left:
        st.header("Tenant Portal")
    with right:
        logout_inline("logout_tenant_top")

    # Future landlord email
    st.subheader("Future Landlord Contact")
    profile = load_tenant_profile(st.session_state.user["id"])
    current_email = profile["future_landlord_email"] if profile else ""

    with st.form("future_landlord_form"):
        future_email = st.text_input("Future landlord email", value=current_email)
        save = st.form_submit_button("Save")
    if save:
        if future_email and not is_valid_email(future_email):
            st.error("Please provide a valid email address for the future landlord.")
        else:
            upsert_tenant_profile(st.session_state.user["id"], future_email or None)
            st.success("Saved future landlord email.")

    st.divider()

    # Previous landlords + reference requests
    st.subheader("Previous Landlords & References")
    with st.form("previous_landlord_form"):
        col1, col2 = st.columns([1,1])
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
    if rows:
        for (pid, email, afm, name, address, created_at) in rows:
            with st.expander(f"{name} • {email}"):
                st.write(f"**AFM:** {afm}")
                st.write(f"**Address:** {address}")
                st.caption(f"Added on {created_at}")

                # --- Contract upload & listing ---
                st.markdown("**Contract upload** (PDF or image)")
                up_files = st.file_uploader(
                    "Upload previous rental contract",
                    type=["pdf","png","jpg","jpeg"],
                    accept_multiple_files=True,
                    key=f"upl_{pid}"
                )
                if up_files:
                    for uf in up_files:
                        try:
                            save_contract_file(st.session_state.user["id"], pid, uf)
                            st.success(f"Uploaded: {uf.name}")
                        except Exception as ex:
                            st.error(f"Failed to save {uf.name}: {ex}")

                contracts = list_contracts_by_prev_landlord(pid) or []
                if contracts:
                    for (cid, fname, fpath, mime, uploaded_at) in contracts:
                        cols_dl = st.columns([3,2])
                        cols_dl[0].write(f"📄 {fname}")
                        with open(fpath, "rb") as fb:
                            cols_dl[1].download_button(
                                "Download",
                                data=fb.read(),
                                file_name=fname,
                                mime=mime or "application/octet-stream",
                                key=f"dl_contract_tenant_{pid}_{cid}",
                            )
                else:
                    st.caption("No contracts uploaded yet.")

                c1, c2 = st.columns([1,2])
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
                            colA, colB, colC = st.columns([2,2,2])
                            colA.write(f"Status: **{status}**")
                            if score is not None:
                                colB.write(f"Score: **{score}**/10")
                            link = build_reference_link(tok)
                            colC.write(link)
                    else:
                        st.caption("No reference requests yet.")
    else:
        st.info("No previous landlords added yet.")

    st.divider()
    st.subheader("All Reference Requests")
    allreqs = list_reference_requests_for_tenant(st.session_state.user["id"]) or []
    if allreqs:
        for (rid, tok, lmail, created_at, status, score) in allreqs:
            cols = st.columns([3,2,3,2])
            cols[0].write(f"To: **{lmail}**")
            cols[1].write(f"Status: **{status}**")
            cols[2].write(f"Link: {build_reference_link(tok)}")
            cols[3].write(f"Score: {score if score is not None else '-'}")
    else:
        st.caption("No reference requests created yet.")

# ---------- Landlord Dashboard (enhanced) ----------

def landlord_dashboard():
    # Header with inline logout on the right
    left, right = st.columns([6,1])
    with left:
        st.header("Landlord Portal")
    with right:
        logout_inline("logout_landlord_top")
    landlord_email = st.session_state.user["email"]
    st.caption(f"Signed in as {landlord_email}")

    # === Prospective tenants who listed this landlord ===
    st.subheader("Prospective Tenants (listed you as future landlord)")

    prospects = list_prospective_tenants(landlord_email)

    # Group by tenant (single card per tenant) and compute average score
    grouped = []
    for (tid, tname, temail, updated_at) in prospects:
        refs_raw = list_latest_references_for_tenant(tid)
        ref_items = []
        pending_count = 0
        completed_count = 0
        score_list = []
        idx = 0
        for (
            prev_id, prev_name, prev_email, prev_afm, prev_addr,
            token, status, score, paid_on_time, utilities_unpaid, good_condition, comments, created_at, filled_at
        ) in refs_raw:
            if status not in ("pending", "completed"):
                continue
            idx += 1
            ref_items.append({
                "index": idx,
                "token": token,
                "status": status,
                "score": score,
                "paid_on_time": paid_on_time,
                "utilities_unpaid": utilities_unpaid,
                "good_condition": good_condition,
                "comments": comments,
                "created_at": created_at,
                "filled_at": filled_at,
            })
            if status == "pending":
                pending_count += 1
            elif status == "completed":
                completed_count += 1
                if score is not None:
                    score_list.append(score)
        avg_score = round(sum(score_list) / len(score_list), 2) if score_list else None
        grouped.append({
            "tenant_id": tid,
            "tenant_name": tname,
            "tenant_email": temail,
            "updated_at": updated_at,
            "pending": pending_count,
            "completed": completed_count,
            "avg_score": avg_score,
            "refs": ref_items,
        })

    total_pending = sum(t["pending"] for t in grouped)
    total_completed = sum(t["completed"] for t in grouped)

    c1, c2 = st.columns(2)
    c1.metric("Pending", total_pending)
    c2.metric("Completed", total_completed)

    tab_all, tab_pending, tab_completed = st.tabs(["All", "Pending", "Completed"])

    def render_tenants(items, scope):
        if not items:
            st.info("No matching tenants.")
            return
        for t in items:
            with st.container(border=True):
                st.markdown(f"**Tenant:** {t['tenant_name']} · {t['tenant_email']}")
                cols = st.columns([2,2,2])
                cols[0].write(f"**Pending refs:** {t['pending']}")
                cols[1].write(f"**Completed refs:** {t['completed']}")
                cols[2].write(f"**Avg score:** {t['avg_score'] if t['avg_score'] is not None else '—'}")
                if t["refs"]:
                    with st.expander("View references"):
                        for r in t["refs"]:
                            st.markdown(
                                f"- **Status:** {r['status']} — **Created:** {r['created_at']}" +
                                (f" — **Filled:** {r['filled_at']}" if r['filled_at'] else "")
                            )
                            if r["status"] == "completed":
                                st.write(f"  Score: {r['score']}/10")
                                st.write(f"  Paid on time: {'Yes' if r['paid_on_time'] else 'No'}")
                                st.write(f"  Utilities unpaid: {'Yes' if r['utilities_unpaid'] else 'No'}")
                                st.write(f"  Apartment in good condition: {'Yes' if r['good_condition'] else 'No'}")
                                if r.get('comments'):
                                    st.write("  Comments:")
                                    st.write(r['comments'])

    with tab_all:
        render_tenants(grouped, 'all')
    with tab_pending:
        render_tenants([t for t in grouped if t['pending'] > 0], 'pending')
    with tab_completed:
        render_tenants([t for t in grouped if t['completed'] > 0], 'completed')

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

    tab_all, tab_pending, tab_completed = st.tabs(["All", "Pending", "Completed"])

    def render_requests(reqs, scope):
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

                if status == "pending":
                    with st.expander("Respond now"):
                        with st.form(f"landlord_response_{scope}_{token}"):
                            confirm = st.checkbox("I confirm I was the landlord for this tenant.")
                            s = st.slider("Overall tenant score", 1, 10, 8)
                            paid_on_time = st.radio("Did the tenant pay on time?", ["Yes","No"], horizontal=True)
                            utilities_unpaid = st.radio("Did the tenant leave utilities unpaid?", ["No","Yes"], horizontal=True)
                            good_condition = st.radio("Did the tenant leave the apartment in good condition?", ["Yes","No"], horizontal=True)
                            comments = st.text_area("Optional comments")
                            col_a, col_b = st.columns([1,1])
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
        render_requests(all_reqs, 'all')
    with tab_pending:
        render_requests(pending_reqs, 'pending')
    with tab_completed:
        render_requests(completed_reqs, 'completed')

# ---------- Admin Console ----------

def admin_dashboard():
    # Header with inline logout on the right
    left, right = st.columns([6,1])
    with left:
        st.header("Admin Console")
    with right:
        logout_inline("logout_admin_top")

    st.caption("Review uploaded contracts and previous landlord details. (Admins only)")

    # Search
    search = st.text_input("Search (tenant name/email, previous landlord name/email/AFM)")

    rows = admin_list_contracts(search)

    # Stats
    total = len(rows)
    today = sum(1 for r in rows if (r[3] and str(r[3])) or True)  # placeholder no tz
    c1, c2 = st.columns(2)
    c1.metric("Total contracts", total)
    c2.metric("Search results", total)

    if not rows:
        st.info("No contracts found.")
        return

    for (cid, file_name, file_path, mime_type, uploaded_at,
         tenant_id, tenant_name, tenant_email,
         pl_name, pl_email, pl_afm, pl_address) in rows:
        with st.container(border=True):
            st.markdown(f"**Tenant:** {tenant_name} · {tenant_email}")
            st.markdown(f"**Previous landlord:** {pl_name} · {pl_email}")
            st.markdown(f"**AFM:** {pl_afm}  ")
            st.markdown(f"**Address:** {pl_address}")
            cols = st.columns([3,2,3])
            cols[0].write(f"📄 **File:** {file_name}")
            cols[1].write(f"Uploaded: {uploaded_at}")
            try:
                with open(file_path, "rb") as fb:
                    cols[2].download_button(
                        "Download contract",
                        data=fb.read(),
                        file_name=file_name,
                        mime=mime_type or "application/octet-stream",
                        key=f"dl_admin_{cid}",
                    )
            except Exception as ex:
                cols[2].error(f"Missing file: {ex}")

# ---------- App ----------

def main():
    params = st.query_params
    token = params.get("ref")
    if token:
        reference_portal(token)
        return

    st.title("🏠 RentRight")
    st.caption("Landing page with login/signup, tenant records, and email-based reference requests.")

    with st.sidebar:
        st.subheader("Email settings (SMTP)")
        st.session_state.smtp_host = st.text_input("SMTP host", value=st.session_state.get("smtp_host", ""))
        st.session_state.smtp_port = st.number_input("SMTP port", value=int(st.session_state.get("smtp_port", 587)))
        st.session_state.smtp_user = st.text_input("SMTP username", value=st.session_state.get("smtp_user", ""))
        st.session_state.smtp_pass = st.text_input("SMTP password", type="password", value=st.session_state.get("smtp_pass", ""))
        st.session_state.smtp_from = st.text_input("From email (optional)", value=st.session_state.get("smtp_from", ""))
        st.session_state.smtp_tls = st.checkbox("Use TLS", value=st.session_state.get("smtp_tls", True))
        st.markdown("---")
        st.subheader("App base URL")
        st.session_state.app_base_url = st.text_input("Base URL for links", help="e.g., https://yourdomain.com")

        st.markdown("---")
        st.subheader("View mode")
        if st.session_state.get("user", {}).get("is_admin", 0):
            st.session_state.view_mode = st.radio(
                "Choose view",
                ["Dashboard", "Admin"],
                index=0 if st.session_state.get("view_mode", "Dashboard") == "Dashboard" else 1,
                key="view_mode_radio",
            )
        st.markdown("---")
        st.subheader("MVP helper")
        st.caption("If you don't have email set up, copy the generated link and open it to fill the form yourself.")

        if st.session_state.get("user"):
            logout_button()

    if st.session_state.get("user"):
        # Admin view override
        if st.session_state.get("user", {}).get("is_admin", 0) and st.session_state.get("view_mode") == "Admin":
            admin_dashboard()
            return

        role = st.session_state.user["role"]
        if role == "tenant":
            tenant_dashboard()
        else:
            landlord_dashboard()
        return

    auth_gate()

if __name__ == "__main__":
    main()
