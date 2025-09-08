from __future__ import annotations

def apply_admin_review_patch(env: dict):
    """
    Injects: schema ensures, audit helpers, and a professional admin UI to the host app.
    Usage in host: from admin_review_patch import apply_admin_review_patch; apply_admin_review_patch(globals())
    """
    # Pull needed symbols from host environment
    st = env["st"]
    get_conn = env["get_conn"]
    DOC_TYPES = env["DOC_TYPES"]
    td_list_by_status = env["td_list_by_status"]
    td_read_bytes = env["td_read_bytes"]
    td_set_status = env["td_set_status"]
    format_dt = env["format_dt"]
    tr = env.get("tr", lambda s: s)

    import sqlite3, time

    # -------- Schema ensure (idempotent) --------
    def ensure_admin_audit_schema():
        c = get_conn()
        # admin_audit table
        c.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT NOT NULL,            -- 'tenant_document' | 'reference_request'
                entity_id INTEGER NOT NULL,
                action TEXT NOT NULL,            -- 'verify' | 'reject' | 'revoke'
                old_status TEXT,
                new_status TEXT,
                reason_code TEXT,
                notes TEXT,
                admin_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON admin_audit(entity, entity_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_audit_admin  ON admin_audit(admin_user_id, created_at DESC)")
        # ensure tenant_documents has the columns we expect (tolerant across seeds)
        def _has_col(tbl, col):
            try:
                return any(r[1] == col for r in c.execute(f"PRAGMA table_info({tbl})"))
            except Exception:
                return False
        if not _has_col("tenant_documents", "status"):
            c.execute("ALTER TABLE tenant_documents ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
        if not _has_col("tenant_documents", "status_updated_at"):
            c.execute("ALTER TABLE tenant_documents ADD COLUMN status_updated_at TEXT")
        if not _has_col("tenant_documents", "status_by"):
            c.execute("ALTER TABLE tenant_documents ADD COLUMN status_by INTEGER")
        # useful indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_td_status_time ON tenant_documents(status, uploaded_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_td_tenant_type ON tenant_documents(tenant_id, doc_type)")
        # extra index for fast “latest per type”
        c.execute("""
        CREATE INDEX IF NOT EXISTS idx_td_tenant_type_uploaded
        ON tenant_documents(tenant_id, doc_type, uploaded_at DESC, id DESC)
        """)
        # views for reporting (best-active and latest-verified)
        c.execute("""
        CREATE VIEW IF NOT EXISTS v_tenant_active_doc AS
        WITH ranked AS (
          SELECT
            td.id AS doc_id, td.tenant_id, td.doc_type, td.status, td.filename,
            td.uploaded_at, td.status_updated_at,
            CASE LOWER(COALESCE(td.status,'pending'))
              WHEN 'verified' THEN 0 WHEN 'pending' THEN 1
              WHEN 'rejected' THEN 2 WHEN 'revoked' THEN 3 ELSE 4 END AS status_rank,
            ROW_NUMBER() OVER (
              PARTITION BY td.tenant_id, td.doc_type
              ORDER BY status_rank ASC, td.uploaded_at DESC, td.id DESC
            ) AS rn
          FROM tenant_documents td
        )
        SELECT doc_id, tenant_id, doc_type, status, filename, uploaded_at, status_updated_at
        FROM ranked WHERE rn = 1
        """)
        c.execute("""
        CREATE VIEW IF NOT EXISTS v_tenant_latest_verified_doc AS
        WITH ranked AS (
          SELECT
            td.id AS doc_id, td.tenant_id, td.doc_type, td.status, td.filename,
            td.uploaded_at, td.status_updated_at,
            ROW_NUMBER() OVER (
              PARTITION BY td.tenant_id, td.doc_type
              ORDER BY td.uploaded_at DESC, td.id DESC
            ) AS rn
          FROM tenant_documents td
          WHERE LOWER(COALESCE(td.status,'pending')) = 'verified'
        )
        SELECT doc_id, tenant_id, doc_type, status, filename, uploaded_at, status_updated_at
        FROM ranked WHERE rn = 1
        """)
        get_conn().commit()

    # -------- Audit helpers --------
    def admin_audit(entity: str, entity_id: int, action: str,
                    old_status: str|None, new_status: str,
                    reason_code: str|None, notes: str|None, admin_user_id: int):
        try:
            c = get_conn()
            ok = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='admin_audit' LIMIT 1").fetchone()
            if not ok:
                return
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""INSERT INTO admin_audit
                (entity, entity_id, action, old_status, new_status, reason_code, notes, admin_user_id, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (entity, entity_id, action, old_status, new_status, reason_code, notes, admin_user_id, now))
            c.commit()
        except Exception:
            pass

    def list_admin_audit(limit: int = 30):
        try:
            return get_conn().execute("""
                SELECT a.*, COALESCE(u.email, 'system') AS actor_email
                FROM admin_audit a
                LEFT JOIN users u ON u.id = a.admin_user_id
                ORDER BY a.id DESC
                LIMIT ?
            """, (limit,)).fetchall()
        except Exception:
            return []

    # -------- Status helpers --------
    ALLOWED_TRANSITIONS = {
        "pending": {"verified", "rejected"},
        "verified": {"revoked"},
        "rejected": set(),
        "revoked": set(),
    }
    def _can_transition(old: str, new: str) -> bool:
        return new in ALLOWED_TRANSITIONS.get((old or "pending").lower(), set())

    REASON_CODES = [
        ("blurry", tr("Blurry / unreadable")),
        ("mismatch_name", tr("Name mismatch")),
        ("outdated", tr("Outdated document")),
        ("partial_pages", tr("Incomplete pages")),
        ("wrong_type", tr("Wrong document type")),
        ("suspected_edit", tr("Suspected modification")),
    ]

    # Set status + audit (wraps your td_set_status)
    def _admin_set_status(doc_id: int, new_status: str, admin_id: int,
                          reason_label: str|None = None, notes: str|None = None):
        c = get_conn()
        row = c.execute("SELECT status FROM tenant_documents WHERE id=?", (doc_id,)).fetchone()
        old = (row[0] if row else "pending")
        if not _can_transition(old, new_status) and new_status in ("verified","rejected","revoked"):
            raise ValueError(f"Illegal transition {old} → {new_status}")
        td_set_status(doc_id, new_status, admin_id)
        code = None
        if reason_label:
            code = next((c for c,lbl in REASON_CODES if lbl == reason_label), "unspecified")
        admin_audit("tenant_document", doc_id, new_status, old, new_status, code, notes, admin_id)

    # -------- UI --------
    def _status_badge(status: str) -> str:
        s = (status or "").lower()
        if s == "verified":  return f'<span class="pill pill--ok">✅ {tr("Verified")}</span>'
        if s == "pending":   return f'<span class="pill pill--info">⏳ {tr("Pending")}</span>'
        if s == "rejected":  return f'<span class="pill pill--err">❌ {tr("Rejected")}</span>'
        if s == "revoked":   return f'<span class="pill pill--err">⛔ {tr("Revoked")}</span>'
        return f'<span class="pill">{status}</span>'

    def _preview_or_download(r):
        data = td_read_bytes(r["id"])
        if not data:
            st.warning(tr("Can't read the saved file"))
            return
        fname = str(r["filename"] or "")
        if fname.lower().endswith((".png",".jpg",".jpeg",".webp")):
            st.image(data, caption=fname)
        else:
            st.download_button(tr("Download"), data=data, file_name=fname or f"{r['doc_type']}.pdf")

    def render_admin_documents_tabs(current_user):
        # CSS
        st.markdown("""
        <style>
        .pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.85rem;
              font-weight:600;border:1px solid;white-space:nowrap}
        .pill--ok{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}
        .pill--info{background:#eff6ff;color:#1e40af;border-color:#bfdbfe}
        .pill--err{background:#fef2f2;color:#7f1d1d;border-color:#fecaca}
        .muted{color:#64748b}
        </style>
        """, unsafe_allow_html=True)

        # Ensure schema (once per run)
        try:
            ensure_admin_audit_schema()
        except Exception:
            pass

        st.subheader(tr("Tenant Documents Review"))
        # Counters
        c = get_conn()
        counts = {
            "pending":  c.execute("SELECT COUNT(*) FROM tenant_documents WHERE status='pending'").fetchone()[0],
            "verified": c.execute("SELECT COUNT(*) FROM tenant_documents WHERE status='verified'").fetchone()[0],
            "rejected": c.execute("SELECT COUNT(*) FROM tenant_documents WHERE status='rejected'").fetchone()[0],
        }
        tabs = st.tabs([
            f"{tr('Pending')} ({counts['pending']})",
            f"{tr('Verified')} ({counts['verified']})",
            f"{tr('Rejected')} ({counts['rejected']})",
        ])

        def _render_rows(rows, allow_revoke=False):
            if not rows:
                st.info(tr("No actions"))
                return
            for r in rows:
                title = f"{DOC_TYPES.get(r['doc_type'], r['doc_type'])} • {r['filename']} — {r['name']} <{r['email']}>"
                meta  = f"{tr('Uploaded')}: {format_dt(r['uploaded_at'])}"
                if r["status_updated_at"]:
                    meta += f" · {tr('Updated')}: {format_dt(r['status_updated_at'])}"
                with st.expander(title + " • " + meta, expanded=False):
                    colA, colB = st.columns([2, 1])
                    with colA:
                        if st.button(tr("Preview"), key=f"prev_{r['id']}"):
                            _preview_or_download(r)
                    with colB:
                        st.markdown(_status_badge(r["status"]), unsafe_allow_html=True)
                    st.divider()
                    with st.form(key=f"decide_{r['id']}"):
                        reason = st.selectbox(tr("Reason"), [tr("Select reason…")] + [lbl for _, lbl in REASON_CODES], index=0)
                        notes = st.text_area(tr("Notes (optional)"), height=80)
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            do_verify = st.form_submit_button("✅ " + tr("Verify"))
                        with c2:
                            do_reject = st.form_submit_button("❌ " + tr("Reject"))
                        with c3:
                            do_revoke = st.form_submit_button("⛔ " + tr("Revoke")) if allow_revoke else False
                        if do_verify:
                            try:
                                _admin_set_status(r["id"], "verified", current_user["id"], None, notes)
                                st.success(tr("Verified"))
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                        if do_reject:
                            if reason == tr("Select reason…"):
                                st.error(tr("Please choose a reason to reject."))
                            else:
                                try:
                                    _admin_set_status(r["id"], "rejected", current_user["id"], reason, notes)
                                    st.info(tr("Rejected."))
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                        if do_revoke and allow_revoke:
                            if reason == tr("Select reason…"):
                                st.error(tr("Please choose a reason to revoke."))
                            else:
                                try:
                                    _admin_set_status(r["id"], "revoked", current_user["id"], reason, notes)
                                    st.warning(tr("Revoked"))
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

        with tabs[0]:
            _render_rows(td_list_by_status("pending"))
        with tabs[1]:
            _render_rows(td_list_by_status("verified"), allow_revoke=True)
        with tabs[2]:
            _render_rows(td_list_by_status("rejected"))

        with st.expander(tr("Recent admin actions"), expanded=False):
            rows = list_admin_audit(30)
            if not rows:
                st.caption(tr("No actions"))
            else:
                for a in rows:
                    ts = a["created_at"]
                    who = a["actor_email"] or "-"
                    what = a["action"]
                    tgt = f"{a['entity']}#{a['entity_id']}"
                    st.write(f"- {ts} • {who} → {what} • {tgt}")

    # Export patched function into host env (override previous def if any)
    env["render_admin_documents_tabs"] = render_admin_documents_tabs
