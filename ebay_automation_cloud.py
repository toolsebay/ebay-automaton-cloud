"""
eBay Automation Cloud Portal
Cleaned + redesigned Streamlit application
Concept 1: Premium SaaS / eBay-only

Security:
- No eBay or Gmail secrets are hard-coded.
- Configure credentials with Streamlit secrets or environment variables.
- Rotate any credentials that were previously exposed in source code.

Run:
    streamlit run ebay_automation_cloud.py

Recommended secrets/environment variables:
    EBAY_CLIENT_ID
    EBAY_CLIENT_SECRET
    EBAY_RUNAME
    SMTP_EMAIL
    SMTP_PASSWORD
    WHATSAPP_NUMBER
    APP_DATA_DIR   (optional)
"""

import base64
import datetime as dt
import hashlib
import io
import json
import os
import random
import re
import smtplib
import time
import urllib.parse
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="eBay Automation Cloud",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "eBay Automation Cloud"
APP_VERSION = "2.1"

DATA_DIR = Path(os.getenv("APP_DATA_DIR", "."))
DATA_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "stores": DATA_DIR / "connected_stores.json",
    "users": DATA_DIR / "users_db.json",
    "templates": DATA_DIR / "custom_templates.json",
    "logs": DATA_DIR / "message_logs.json",
}

EBAY_CLIENT_ID = st.secrets.get("EBAY_CLIENT_ID", os.getenv("EBAY_CLIENT_ID", "NawazIqb-eBayAuto-PRD-d254d2f41-10c98af7"))
EBAY_CLIENT_SECRET = st.secrets.get(
    "EBAY_CLIENT_SECRET", os.getenv("EBAY_CLIENT_SECRET", "")
)
EBAY_RUNAME = st.secrets.get("EBAY_RUNAME", os.getenv("EBAY_RUNAME", ""))

SMTP_EMAIL = st.secrets.get("SMTP_EMAIL", os.getenv("SMTP_EMAIL", ""))
SMTP_PASSWORD = st.secrets.get("SMTP_PASSWORD", os.getenv("SMTP_PASSWORD", ""))

WHATSAPP_NUMBER = st.secrets.get(
    "WHATSAPP_NUMBER", os.getenv("WHATSAPP_NUMBER", "")
)
WHATSAPP_DEFAULT_MSG = "Hello, I need help with the eBay Automation Dashboard."
WHATSAPP_LINK = (
    f"https://wa.me/{WHATSAPP_NUMBER}?text="
    f"{urllib.parse.quote(WHATSAPP_DEFAULT_MSG)}"
    if WHATSAPP_NUMBER
    else ""
)

EBAY_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
EBAY_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
EBAY_PROD_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

EBAY_API_BASE = "https://api.ebay.com"
EBAY_SANDBOX_API_BASE = "https://api.sandbox.ebay.com"

DEFAULT_TEMPLATES = {
    "Brand New Order Welcome": (
        "Hello {buyer}, thank you for your order #{order_id}. "
        "We appreciate your business and will process your order shortly."
    ),
    "Shipped Notification": (
        "Hello {buyer}, your eBay order #{order_id} has shipped. "
        "Carrier: {carrier}. Tracking: {tracking_number}. Thank you!"
    ),
    "Delivered Feedback": (
        "Hello {buyer}, your order #{order_id} shows as delivered. "
        "We hope you enjoy your purchase. Thank you for shopping with us!"
    ),
    "Order Cancellation Notice": (
        "Hello {buyer}, your eBay order #{order_id} has been cancelled. "
        "Please contact us if you need any assistance."
    ),
}

SPAM_TERMS = [
    "free shipping",
    "l@@k",
    "wow",
    "must see",
    "best price",
    "authentic",
    "genuine",
    "top rated",
    "brand new sealed",
    "rare",
    "hot",
    "fast ship",
]

ALL_MODULES = [
    "Dashboard",
    "Orders & Auto-Messaging",
    "Product Hunting & Research",
    "Listings & Policy",
    "Sales & Revenue",
    "Promoted Listings / Ads",
    "Tasks & Reminders",
    "Price Checker",
    "Inventory",
    "Watchlist / Saved Products",
    "Connect eBay Store",
    "Message Templates",
]


# ============================================================
# PREMIUM SAAS UI
# ============================================================

def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --navy: #0b1220;
            --navy-2: #111a2d;
            --blue: #4f7cff;
            --blue-2: #6d8dff;
            --text: #172033;
            --muted: #73809a;
            --border: #e7ebf3;
            --panel: #ffffff;
            --bg: #f5f7fb;
            --success: #20a66a;
            --warning: #e7a62c;
            --danger: #e45a68;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1220 0%, #111a2d 100%);
            border-right: 1px solid rgba(255,255,255,.06);
        }

        [data-testid="stSidebar"] * {
            color: #e9eefb;
        }

        [data-testid="stSidebar"] .stButton button {
            border: 0 !important;
            background: transparent !important;
            text-align: left !important;
            color: #cbd4e7 !important;
            border-radius: 10px !important;
        }

        [data-testid="stSidebar"] .stButton button:hover {
            background: rgba(79,124,255,.14) !important;
            color: white !important;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 11px;
            padding: 6px 4px 24px 4px;
        }

        .brand-icon {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #4f7cff, #765cff);
            box-shadow: 0 8px 24px rgba(79,124,255,.30);
            font-size: 20px;
        }

        .brand-title {
            font-size: 16px;
            font-weight: 800;
            color: white;
            line-height: 1.1;
        }

        .brand-subtitle {
            color: #8290aa;
            font-size: 11px;
            margin-top: 3px;
        }

        .topbar {
            display:flex;
            align-items:center;
            justify-content:space-between;
            margin-bottom: 18px;
        }

        .eyebrow {
            color: var(--blue);
            font-size: 12px;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        .page-title {
            font-size: 30px;
            line-height: 1.1;
            font-weight: 850;
            color: #111a2d;
            margin-top: 4px;
        }

        .page-subtitle {
            color: var(--muted);
            font-size: 13px;
            margin-top: 6px;
        }

        .metric-card {
            background: white;
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 8px 24px rgba(17,26,45,.04);
            min-height: 122px;
        }

        .metric-label {
            color: var(--muted);
            font-size: 12px;
            font-weight: 700;
        }

        .metric-value {
            color: #111a2d;
            font-size: 27px;
            font-weight: 850;
            margin-top: 7px;
        }

        .metric-help {
            color: #8b96aa;
            font-size: 11px;
            margin-top: 4px;
        }

        .panel {
            background: white;
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 24px rgba(17,26,45,.04);
            margin-bottom: 18px;
        }

        .panel-title {
            font-size: 16px;
            font-weight: 800;
            color: #172033;
            margin-bottom: 4px;
        }

        .panel-subtitle {
            font-size: 12px;
            color: var(--muted);
            margin-bottom: 14px;
        }

        .status-pill {
            display: inline-flex;
            padding: 5px 9px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 800;
            background: #edf8f3;
            color: #198653;
        }

        .status-pill.off {
            background: #fff0f1;
            color: #c44755;
        }

        .quick-action {
            border: 1px solid var(--border);
            background: #fafbfe;
            border-radius: 13px;
            padding: 15px;
        }

        .small-note {
            color: #7d899e;
            font-size: 11px;
        }

        .login-shell {
            max-width: 470px;
            margin: 7vh auto 0 auto;
        }

        .login-card {
            background: white;
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 18px 50px rgba(17,26,45,.09);
        }

        .footer {
            text-align:center;
            color:#8b96aa;
            font-size:11px;
            margin: 30px 0 8px;
        }

        .stButton button, .stDownloadButton button {
            border-radius: 10px;
            font-weight: 700;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border);
        }

        /* Accessible, high-contrast controls */
        .stApp, .stApp p, .stApp label, .stApp span { color: var(--text); }
        .stApp [data-testid="stMarkdownContainer"] p,
        .stApp [data-testid="stMarkdownContainer"] li { color: var(--text); }
        .stApp input, .stApp textarea {
            color: #172033 !important;
            background-color: #ffffff !important;
            caret-color: #172033 !important;
        }
        .stApp input::placeholder, .stApp textarea::placeholder {
            color: #667085 !important; opacity: 1 !important;
        }
        .stApp [data-baseweb="select"] > div {
            background-color: #ffffff !important; color: #172033 !important;
            border-color: #cfd6e4 !important;
        }
        .stApp [data-baseweb="select"] * { color: #172033 !important; }
        .stApp [role="radiogroup"] label,
        .stApp [role="checkbox"] label,
        .stApp [data-testid="stWidgetLabel"] { color: #172033 !important; }
        .stApp button { color: #172033 !important; }
        .stApp button[kind="primary"] { color: #ffffff !important; }
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span { color: #e9eefb !important; }
        .login-card .stTabs [data-baseweb="tab-list"] button { color: #344054 !important; }
        .login-card .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] { color: #2457d6 !important; }

        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()


# ============================================================
# GENERIC HELPERS
# ============================================================

def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path: Path, data: Any) -> bool:
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        tmp.replace(path)
        return True
    except OSError:
        return False


def hash_pass(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def normalize_username(value: str) -> str:
    return (value or "").strip().lower()


def valid_password(password: str) -> bool:
    return len(password or "") >= 8


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def money(value: Any, currency: str = "USD") -> str:
    amount = safe_float(value)
    symbol = {"USD": "$", "GBP": "£", "EUR": "€", "AUD": "A$"}.get(currency, currency + " ")
    return f"{symbol}{amount:,.2f}"


def page_header(title: str, subtitle: str = "", eyebrow: str = "eBay Automation") -> None:
    st.markdown(
        f"""
        <div class="topbar">
            <div>
                <div class="eyebrow">{eyebrow}</div>
                <div class="page-title">{title}</div>
                <div class="page-subtitle">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def panel_start(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{title}</div>
            <div class="panel-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def panel_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def dataframe_download(df: pd.DataFrame, filename: str, label: str = "Export CSV") -> None:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
    )


def get_setting(name: str, default: Any = "") -> Any:
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


# ============================================================
# USER / AUTH
# ============================================================

def load_users() -> Dict[str, Any]:
    users = load_json(FILES["users"], {})
    if not isinstance(users, dict):
        users = {}
    return users


def save_users(users: Dict[str, Any]) -> None:
    save_json(FILES["users"], users)


def ensure_admin() -> None:
    users = load_users()
    if "admin" not in users:
        users["admin"] = {
            "password": hash_pass("change-me"),
            "role": "admin",
            "email": "",
            "enabled": True,
            "modules": ALL_MODULES.copy(),
            "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
        save_users(users)


def send_otp_email(recipient: str, otp: str) -> Tuple[bool, str]:
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False, "SMTP credentials are not configured."

    try:
        msg = EmailMessage()
        msg["Subject"] = "eBay Automation Cloud Verification Code"
        msg["From"] = SMTP_EMAIL
        msg["To"] = recipient
        msg.set_content(f"Your verification code is: {otp}\n\nThis code expires shortly.")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        return True, "OTP sent successfully."
    except Exception as exc:
        return False, f"Unable to send OTP: {exc}"


def login_screen() -> None:
    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="login-card">
            <div class="brand">
                <div class="brand-icon">🛒</div>
                <div>
                    <div class="brand-title" style="color:#111a2d">eBay Automation Cloud</div>
                    <div class="brand-subtitle" style="color:#667085">Premium seller operations dashboard</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    tab_login, tab_signup, tab_forgot = st.tabs(["Sign in", "Create account", "Reset password"])

    with tab_login:
        username_raw = st.text_input("Username / Email", key="login_user", placeholder="Enter your username or email")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")
        if st.button("Sign in", type="primary", use_container_width=True, key="login_button"):
            username = normalize_username(username_raw)
            user = load_users().get(username)
            if user and user.get("enabled", True) and user.get("password") == hash_pass(password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = user.get("role", "client")
                st.session_state.page = "Dashboard"
                st.rerun()
            else:
                st.error("Invalid username/email or password.")
        st.caption("First run admin: admin / change-me — change it immediately.")

    with tab_signup:
        new_user_raw = st.text_input("Email / Username", key="signup_user", placeholder="you@example.com")
        new_pass = st.text_input("Password", type="password", key="signup_pass", placeholder="Minimum 8 characters")
        confirm = st.text_input("Confirm password", type="password", key="signup_confirm", placeholder="Repeat your password")
        if st.button("Create account", type="primary", use_container_width=True, key="signup_button"):
            new_user = normalize_username(new_user_raw)
            users = load_users()
            if not new_user or not new_pass:
                st.warning("Enter a username/email and password.")
            elif len(new_user) < 3:
                st.warning("Username/email must be at least 3 characters.")
            elif new_user == "admin":
                st.error("The username 'admin' is reserved.")
            elif new_user in users:
                st.error("Account already exists. Please sign in instead.")
            elif not valid_password(new_pass):
                st.error("Password must be at least 8 characters.")
            elif new_pass != confirm:
                st.error("Passwords do not match.")
            else:
                users[new_user] = {
                    "password": hash_pass(new_pass),
                    "role": "client",
                    "email": new_user if "@" in new_user else "",
                    "enabled": True,
                    "modules": ALL_MODULES.copy(),
                    "created_at": dt.datetime.now().isoformat(timespec="seconds"),
                }
                if save_users(users):
                    st.session_state.logged_in = True
                    st.session_state.username = new_user
                    st.session_state.role = "client"
                    st.session_state.page = "Dashboard"
                    st.success("Account created successfully. Opening your dashboard...")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("Account could not be saved. Check the app's data storage permissions.")

    with tab_forgot:
        email_raw = st.text_input("Account email", key="forgot_email", placeholder="Enter your registered email")
        email = normalize_username(email_raw)
        if st.button("Send reset code", use_container_width=True, key="send_reset_code"):
            users = load_users()
            if email in users and users[email].get("email"):
                otp = str(random.randint(100000, 999999))
                st.session_state.reset_otp = otp
                st.session_state.reset_user = email
                st.session_state.reset_otp_time = time.time()
                ok, msg = send_otp_email(email, otp)
                st.success(msg) if ok else st.error(msg)
            elif email in users:
                st.error("This account uses a username. Sign in and use Change Password.")
            else:
                st.error("Account not found.")
        otp = st.text_input("Verification code", key="reset_otp_input")
        new_password = st.text_input("New password", type="password", key="reset_new_pass")
        if st.button("Reset password", use_container_width=True, key="reset_password_button"):
            if not valid_password(new_password):
                st.error("New password must be at least 8 characters.")
            elif (st.session_state.get("reset_user") == email and
                  st.session_state.get("reset_otp") == otp and
                  time.time() - st.session_state.get("reset_otp_time", 0) < 900):
                users = load_users()
                if email in users and save_users({**users, email: {**users[email], "password": hash_pass(new_password)}}):
                    users[email]["password"] = hash_pass(new_password)
                    st.success("Password reset successfully. You can sign in now.")
                else:
                    st.error("Password could not be saved.")
            else:
                st.error("Invalid or expired verification code.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="footer">eBay-only automation • Secure credential configuration • v2.1</div>', unsafe_allow_html=True)


# ============================================================
# EBAY AUTH / API
# ============================================================

def clean_auth_code(code: str) -> str:
    code = (code or "").strip()
    if not code:
        return ""
    if "code=" in code:
        parsed = urllib.parse.urlparse(code)
        query = urllib.parse.parse_qs(parsed.query)
        return query.get("code", [code])[0]
    return urllib.parse.unquote(code)


def ebay_configured() -> bool:
    return all([EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_RUNAME])


def ebay_basic_auth() -> str:
    raw = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def exchange_code_for_tokens(code: str, production: bool = True) -> Dict[str, Any]:
    if not ebay_configured():
        raise RuntimeError("eBay credentials are not configured.")

    token_url = EBAY_PROD_TOKEN_URL if production else EBAY_TOKEN_URL
    redirect_uri = EBAY_RUNAME

    headers = {
        "Authorization": f"Basic {ebay_basic_auth()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": clean_auth_code(code),
        "redirect_uri": redirect_uri,
    }

    response = requests.post(token_url, headers=headers, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def get_fresh_token(
    store: Dict[str, Any],
    production: bool = True,
    force_refresh: bool = False,
) -> Optional[str]:
    """Return a valid user access token, refreshing it automatically when needed."""
    refresh_token = store.get("refresh_token")
    if not refresh_token:
        return None

    # Reuse the cached access token until shortly before it expires.
    access_token = store.get("access_token")
    expires_at = float(store.get("access_token_expires_at", 0) or 0)
    if access_token and not force_refresh and time.time() < expires_at - 60:
        return access_token

    token_url = EBAY_PROD_TOKEN_URL if production else EBAY_TOKEN_URL
    headers = {
        "Authorization": f"Basic {ebay_basic_auth()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    # Do not send a scope here. eBay refreshes using the scopes originally
    # granted with the refresh token and may reject an incompatible scope list.
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        payload = response.json()
        new_access_token = payload.get("access_token")
        if not new_access_token:
            return None

        store["access_token"] = new_access_token
        store["access_token_expires_at"] = time.time() + int(payload.get("expires_in", 7200))
        # eBay can rotate the refresh token. Preserve the old one if a new one
        # is not returned, otherwise save the rotated token.
        if payload.get("refresh_token"):
            store["refresh_token"] = payload["refresh_token"]

        stores = load_stores()
        for username, user_stores in stores.items():
            if isinstance(user_stores, dict):
                for alias, saved_store in user_stores.items():
                    if saved_store is store or (
                        saved_store.get("refresh_token") == refresh_token
                        and saved_store.get("marketplace_id") == store.get("marketplace_id")
                    ):
                        user_stores[alias] = store
                        save_stores(stores)
                        return new_access_token
        return new_access_token
    except requests.RequestException:
        return None


def get_app_access_token(production: bool = True) -> Optional[str]:
    if not ebay_configured():
        return None

    token_url = EBAY_PROD_TOKEN_URL if production else EBAY_TOKEN_URL
    headers = {
        "Authorization": f"Basic {ebay_basic_auth()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.RequestException:
        return None


def ebay_headers(token: str, marketplace_id: str = "EBAY_US") -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": marketplace_id,
    }


# ============================================================
# STORE MANAGEMENT
# ============================================================

def load_stores() -> Dict[str, Any]:
    stores = load_json(FILES["stores"], {})
    return stores if isinstance(stores, dict) else {}


def save_stores(stores: Dict[str, Any]) -> None:
    save_json(FILES["stores"], stores)


def get_user_stores(username: str) -> Dict[str, Any]:
    stores = load_stores()
    user_stores = stores.get(username, {})
    return user_stores if isinstance(user_stores, dict) else {}


def selected_store(username: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    stores = get_user_stores(username)
    if not stores:
        return None, None

    names = list(stores.keys())
    name = st.selectbox("eBay Store", names, key="selected_store_name")
    return name, stores.get(name)


# ============================================================
# ORDERS
# ============================================================

def fetch_all_ebay_orders_cached(
    store: Dict[str, Any],
    marketplace_id: str = "EBAY_US",
    days_back: int = 90,
) -> List[Dict[str, Any]]:
    token = get_fresh_token(store)
    if not token:
        return []

    endpoint = f"{EBAY_API_BASE}/sell/fulfillment/v1/order"
    start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_back)
    params = {
        "filter": (
            f"creationdate:[{start.strftime('%Y-%m-%dT%H:%M:%S.000Z')}.."
            f"{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')}]"
        ),
        "limit": 200,
    }

    orders: List[Dict[str, Any]] = []
    offset = 0

    while True:
        params["offset"] = offset
        try:
            response = requests.get(
                endpoint,
                headers=ebay_headers(token, marketplace_id),
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException:
            break

        batch = payload.get("orders", []) or []
        orders.extend(batch)

        total = safe_int(payload.get("total"))
        if not batch or len(orders) >= total or len(batch) < 200:
            break
        offset += len(batch)

        if offset > 5000:
            break

    return orders


def get_clean_order_status(order: Dict[str, Any]) -> str:
    if order.get("cancelStatus", {}).get("cancelState") == "CANCELLED":
        return "Cancelled"

    fulfillment = order.get("orderFulfillmentStatus", "")
    payment = order.get("orderPaymentStatus", "")

    if fulfillment == "FULFILLED":
        return "Shipped"
    if fulfillment == "DELIVERED":
        return "Delivered"
    if payment == "PAID":
        return "Paid"
    if payment:
        return str(payment).title()

    return "Unknown"


def order_to_row(order: Dict[str, Any]) -> Dict[str, Any]:
    pricing = order.get("pricingSummary", {}) or {}
    buyer = order.get("buyer", {}) or {}
    fulfillment = order.get("fulfillmentStartInstructions", []) or []

    carrier = ""
    tracking = ""

    if fulfillment:
        shipment = fulfillment[0].get("shippingStep", {}) or {}
        carrier = shipment.get("shippingCarrierCode", "")
        tracking = shipment.get("trackingNumber", "")

    return {
        "order_id": order.get("orderId", ""),
        "created": order.get("creationDate", ""),
        "buyer": buyer.get("username", "") or buyer.get("buyerRegistrationAddress", {}).get("fullName", ""),
        "status": get_clean_order_status(order),
        "subtotal": safe_float(pricing.get("price", {}).get("value")),
        "currency": pricing.get("price", {}).get("currency", "USD"),
        "quantity": sum(
            safe_int(item.get("lineItemQuantity", 0))
            for item in order.get("lineItems", [])
        ),
        "carrier": carrier,
        "tracking_number": tracking,
        "raw": order,
    }


# ============================================================
# EBAY MESSAGING
# ============================================================

def send_ebay_message(
    store: Dict[str, Any],
    buyer_username: str,
    subject: str,
    body: str,
) -> Tuple[bool, str]:
    token = get_fresh_token(store)
    if not token:
        return False, "Unable to refresh eBay token."

    endpoint = f"{EBAY_API_BASE}/ws/api.dll"
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<AddMemberMessageAAQToPartnerRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>
  <ItemID>0</ItemID>
  <MemberMessage>
    <Body>{escape_xml(body)}</Body>
    <Subject>{escape_xml(subject)}</Subject>
    <RecipientID>{escape_xml(buyer_username)}</RecipientID>
    <QuestionType>General</QuestionType>
  </MemberMessage>
</AddMemberMessageAAQToPartnerRequest>
"""

    headers = {
        "X-EBAY-API-CALL-NAME": "AddMemberMessageAAQToPartner",
        "X-EBAY-API-SITEID": "0",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "1231",
        "Content-Type": "text/xml",
    }

    try:
        response = requests.post(endpoint, headers=headers, data=xml.encode("utf-8"), timeout=30)
        if response.status_code >= 400:
            return False, f"eBay returned HTTP {response.status_code}"
        if "<Ack>Failure</Ack>" in response.text:
            return False, "eBay rejected the message."
        return True, "Message sent."
    except requests.RequestException as exc:
        return False, f"Message request failed: {exc}"


def escape_xml(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def render_template(template: str, order_row: Dict[str, Any]) -> str:
    values = {
        "buyer": order_row.get("buyer", ""),
        "order_id": order_row.get("order_id", ""),
        "carrier": order_row.get("carrier", ""),
        "tracking_number": order_row.get("tracking_number", ""),
    }
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template


def log_message(username: str, order_id: str, buyer: str, template: str, success: bool, detail: str) -> None:
    logs = load_json(FILES["logs"], [])
    if not isinstance(logs, list):
        logs = []

    logs.append(
        {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "user": username,
            "order_id": order_id,
            "buyer": buyer,
            "template": template,
            "success": success,
            "detail": detail,
        }
    )
    save_json(FILES["logs"], logs)


# ============================================================
# PRODUCT HUNTING
# ============================================================

def search_ebay_market(
    keyword: str,
    marketplace_id: str = "EBAY_US",
    condition: str = "Any",
    sort: str = "Best Match",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    token = get_app_access_token()
    if not token:
        return []

    endpoint = f"{EBAY_API_BASE}/buy/browse/v1/item_summary/search"

    sort_map = {
        "Best Match": "BEST_MATCH",
        "Price: Low to High": "PRICE",
        "Price: High to Low": "-PRICE",
        "Newest": "NEWLY_LISTED",
    }

    params = {
        "q": keyword,
        "limit": min(max(limit, 1), 200),
        "sort": sort_map.get(sort, "BEST_MATCH"),
    }

    if condition != "Any":
        condition_map = {
            "New": "NEW",
            "Used": "USED",
            "Refurbished": "CERTIFIED_REFURBISHED",
        }
        if condition in condition_map:
            params["filter"] = f"conditionIds:{{{condition_map[condition]}}}"

    try:
        response = requests.get(
            endpoint,
            headers=ebay_headers(token, marketplace_id),
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("itemSummaries", []) or []
    except requests.RequestException:
        return []


def audit_competitor_listing(item: Dict[str, Any]) -> Dict[str, Any]:
    title = str(item.get("title", ""))
    seller = item.get("seller", {}) or {}
    price = safe_float((item.get("price", {}) or {}).get("value"))
    image_url = str((item.get("image", {}) or {}).get("imageUrl", ""))

    lower = title.lower()
    spam_found = [term for term in SPAM_TERMS if term in lower]
    caps_ratio = (
        sum(ch.isupper() for ch in title if ch.isalpha())
        / max(1, sum(ch.isalpha() for ch in title))
    )

    warnings = []

    if spam_found:
        warnings.append("Promotional/spam-like wording")
    if len(title) > 80:
        warnings.append("Title longer than 80 characters")
    if caps_ratio > 0.70:
        warnings.append("Excessive uppercase")
    if safe_float(seller.get("feedbackPercentage"), 100) < 95:
        warnings.append("Low seller feedback")
    if 0 < price < 0.99:
        warnings.append("Unusually low price")
    if image_url and not image_url.lower().startswith("https://"):
        warnings.append("Non-HTTPS image")

    return {
        "policy_status": "Warning" if warnings else "OK",
        "warnings": "; ".join(warnings),
        "title_length": len(title),
        "seller_feedback": seller.get("feedbackPercentage", ""),
        "price": price,
        "image_https": image_url.lower().startswith("https://") if image_url else False,
    }


# ============================================================
# COMPLIANCE
# ============================================================

def fetch_ebay_compliance_violations(
    store: Dict[str, Any],
    marketplace_id: str = "EBAY_US",
) -> List[Dict[str, Any]]:
    token = get_fresh_token(store)
    if not token:
        return []

    endpoint = f"{EBAY_API_BASE}/sell/compliance/v1/listing_violation_summary"
    try:
        response = requests.get(
            endpoint,
            headers=ebay_headers(token, marketplace_id),
            timeout=30,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        return payload.get("listingViolations", []) or payload.get("violations", []) or []
    except requests.RequestException:
        return []


# ============================================================
# WATCHLIST / TASKS / LOCAL DATA
# ============================================================

def get_local_user_store(key: str, default: Any) -> Any:
    return st.session_state.get(key, default)


def save_watchlist(item: Dict[str, Any]) -> None:
    watchlist = st.session_state.setdefault("watchlist", [])
    item_id = item.get("itemId")
    if item_id and not any(x.get("itemId") == item_id for x in watchlist):
        watchlist.append(item)


# ============================================================
# SIDEBAR
# ============================================================

def render_sidebar(username: str, role: str) -> str:
    users = load_users()
    user = users.get(username, {})
    enabled_modules = user.get("modules", ALL_MODULES)

    st.sidebar.markdown(
        """
        <div class="brand">
            <div class="brand-icon">🛒</div>
            <div>
                <div class="brand-title">eBay Automation</div>
                <div class="brand-subtitle">Premium Seller Cloud</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.caption(f"Signed in as {username}")
    st.sidebar.divider()

    available = [m for m in ALL_MODULES if m in enabled_modules]
    if role == "admin":
        available = ALL_MODULES

    default_page = "Dashboard" if "Dashboard" in available else available[0]
    current = st.session_state.get("page", default_page)

    page = st.sidebar.radio(
        "WORKSPACE",
        available,
        index=available.index(current) if current in available else 0,
        key="navigation",
    )
    st.session_state.page = page

    st.sidebar.divider()

    if role == "admin":
        if st.sidebar.button("👥 Registered Clients", use_container_width=True):
            st.session_state.page = "Registered Clients"
            st.rerun()

    if st.sidebar.button("🔐 Change Password", use_container_width=True):
        st.session_state.show_change_password = True

    if WHATSAPP_LINK:
        st.sidebar.markdown(
            f'<a href="{WHATSAPP_LINK}" target="_blank" '
            'style="text-decoration:none;"><div class="quick-action">💬 '
            'WhatsApp Support</div></a>',
            unsafe_allow_html=True,
        )

    if st.sidebar.button("Log out", use_container_width=True):
        for key in ["logged_in", "username", "role", "page"]:
            st.session_state.pop(key, None)
        st.rerun()

    st.sidebar.markdown(
        f'<div class="footer">{APP_NAME} • v{APP_VERSION}</div>',
        unsafe_allow_html=True,
    )

    return page


def render_change_password(username: str) -> None:
    if not st.session_state.get("show_change_password"):
        return

    st.sidebar.markdown("### Change password")
    old = st.sidebar.text_input("Current password", type="password", key="old_password")
    new = st.sidebar.text_input("New password", type="password", key="new_password")
    confirm = st.sidebar.text_input("Confirm new password", type="password", key="confirm_password")

    if st.sidebar.button("Update password", use_container_width=True):
        users = load_users()
        user = users.get(username)

        if not user or user.get("password") != hash_pass(old):
            st.sidebar.error("Current password is incorrect.")
        elif not valid_password(new):
            st.sidebar.error("New password must be at least 8 characters.")
        elif new != confirm:
            st.sidebar.error("New passwords do not match.")
        else:
            users[username]["password"] = hash_pass(new)
            save_users(users)
            st.sidebar.success("Password updated.")
            st.session_state.show_change_password = False


# ============================================================
# PAGES
# ============================================================

def page_dashboard(username: str) -> None:
    page_header(
        "Dashboard",
        "A single command center for your eBay store operations.",
        "Overview",
    )

    stores = get_user_stores(username)
    logs = load_json(FILES["logs"], [])
    user_logs = [x for x in logs if x.get("user") == username] if isinstance(logs, list) else []

    cols = st.columns(4)
    with cols[0]:
        metric_card("Connected stores", str(len(stores)), "eBay stores connected")
    with cols[1]:
        metric_card("Messages sent", str(sum(1 for x in user_logs if x.get("success"))), "Successful automated messages")
    with cols[2]:
        metric_card("Watchlist", str(len(st.session_state.get("watchlist", []))), "Saved hunting opportunities")
    with cols[3]:
        metric_card("Message success", f"{(sum(1 for x in user_logs if x.get('success')) / max(1, len(user_logs)) * 100):.0f}%", "Based on local logs")

    st.markdown("")

    left, right = st.columns([1.45, 1])

    with left:
        panel_start("Quick actions", "Jump directly into the workflows you use most.")
        qa1, qa2 = st.columns(2)

        with qa1:
            if st.button("🔎 Product Hunting", use_container_width=True):
                st.session_state.page = "Product Hunting & Research"
                st.rerun()
            if st.button("💬 Auto Messages", use_container_width=True):
                st.session_state.page = "Orders & Auto-Messaging"
                st.rerun()

        with qa2:
            if st.button("📊 Sales Report", use_container_width=True):
                st.session_state.page = "Sales & Revenue"
                st.rerun()
            if st.button("🔗 Connect eBay Store", use_container_width=True):
                st.session_state.page = "Connect eBay Store"
                st.rerun()
        panel_end()

        panel_start("Recent message activity", "Latest automation events.")
        if user_logs:
            log_df = pd.DataFrame(user_logs[-8:][::-1])
            st.dataframe(
                log_df[["timestamp", "order_id", "buyer", "template", "success", "detail"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No message activity yet.")
        panel_end()

    with right:
        panel_start("Store health", "Connection status across your eBay accounts.")
        if stores:
            for name, store in stores.items():
                st.markdown(
                    f"**{name}** &nbsp; "
                    f'<span class="status-pill">Connected</span>',
                    unsafe_allow_html=True,
                )
                st.caption(store.get("marketplace_id", "EBAY_US"))
        else:
            st.warning("No eBay store connected.")
            if st.button("Connect your first store", type="primary", use_container_width=True):
                st.session_state.page = "Connect eBay Store"
                st.rerun()
        panel_end()

        panel_start("Workspace", "eBay-only modules enabled in this portal.")
        for module in [
            "Product Hunting & Research",
            "Orders & Auto-Messaging",
            "Sales & Revenue",
            "Listings & Policy",
        ]:
            st.markdown(f"✓ {module}")
        panel_end()


def page_orders(username: str) -> None:
    page_header(
        "Orders & Auto-Messaging",
        "Sync orders, filter by status, and send templated eBay buyer messages.",
        "Operations",
    )

    store_name, store = selected_store(username)
    if not store:
        st.info("Connect an eBay store first.")
        return

    marketplace = store.get("marketplace_id", "EBAY_US")

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        days_back = st.number_input("Days to sync", 1, 365, 90)
    with c2:
        status_filter = st.selectbox(
            "Status",
            ["All", "Paid", "Shipped", "Delivered", "Cancelled", "Unknown"],
        )
    with c3:
        if st.button("↻ Sync orders", type="primary", use_container_width=True):
            with st.spinner("Fetching eBay orders..."):
                orders = fetch_all_ebay_orders_cached(store, marketplace, int(days_back))
            st.session_state.orders_cache = orders
            st.success(f"Synced {len(orders)} orders.")

    orders = st.session_state.get("orders_cache", [])
    rows = [order_to_row(x) for x in orders]

    if status_filter != "All":
        rows = [x for x in rows if x["status"] == status_filter]

    if not rows:
        st.info("No orders loaded. Click “Sync orders”.")
        return

    df = pd.DataFrame(rows)

    m = st.columns(4)
    with m[0]:
        metric_card("Matched orders", str(len(df)))
    with m[1]:
        metric_card("Revenue", money(df["subtotal"].sum()))
    with m[2]:
        metric_card("Units", str(int(df["quantity"].sum())))
    with m[3]:
        metric_card("AOV", money(df["subtotal"].mean() if len(df) else 0))

    panel_start("Auto message center", "Select a template and send it to matching buyers.")
    templates = load_json(FILES["templates"], DEFAULT_TEMPLATES.copy())
    if not isinstance(templates, dict):
        templates = DEFAULT_TEMPLATES.copy()

    template_name = st.selectbox("Message template", list(templates.keys()))
    message_preview = render_template(
        templates[template_name],
        df.iloc[0].to_dict(),
    )
    st.text_area("Preview", message_preview, height=110)

    send_col1, send_col2 = st.columns([1, 1])
    with send_col1:
        send_bulk = st.button("Send to all matched orders", type="primary", use_container_width=True)
    with send_col2:
        dataframe_download(df.drop(columns=["raw"], errors="ignore"), "ebay_orders.csv", "Export orders")

    if send_bulk:
        progress = st.progress(0)
        sent = 0
        for idx, row in df.iterrows():
            body = render_template(templates[template_name], row.to_dict())
            ok, detail = send_ebay_message(
                store,
                str(row.get("buyer", "")),
                template_name,
                body,
            )
            log_message(
                username,
                str(row.get("order_id", "")),
                str(row.get("buyer", "")),
                template_name,
                ok,
                detail,
            )
            sent += int(ok)
            progress.progress((idx + 1) / len(df))
        st.success(f"Automation finished. {sent}/{len(df)} messages sent.")

    panel_end()

    panel_start("Orders", "Live order records returned by the eBay API.")
    display_cols = [
        "order_id",
        "created",
        "buyer",
        "status",
        "subtotal",
        "currency",
        "quantity",
        "carrier",
        "tracking_number",
    ]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
    panel_end()


def page_product_hunting(username: str) -> None:
    page_header(
        "Product Hunting & Research",
        "Find eBay opportunities, inspect competitor listings, and save products to your watchlist.",
        "Research",
    )

    top1, top2, top3 = st.columns([2.2, 1, 1])
    with top1:
        keyword = st.text_input("Search keyword", placeholder="e.g. wireless car charger")
    with top2:
        marketplace = st.selectbox(
            "Marketplace",
            ["EBAY_US", "EBAY_GB", "EBAY_DE", "EBAY_AU"],
        )
    with top3:
        condition = st.selectbox("Condition", ["Any", "New", "Used", "Refurbished"])

    sort = st.selectbox(
        "Sort",
        ["Best Match", "Price: Low to High", "Price: High to Low", "Newest"],
    )

    if st.button("🔎 Hunt products", type="primary", use_container_width=True):
        if not keyword.strip():
            st.warning("Enter a product keyword.")
        else:
            with st.spinner("Searching eBay marketplace..."):
                results = search_ebay_market(
                    keyword.strip(),
                    marketplace,
                    condition,
                    sort,
                    limit=50,
                )
            st.session_state.hunt_results = results

    results = st.session_state.get("hunt_results", [])
    if not results:
        st.info("Search results will appear here.")
        return

    records = []
    for item in results:
        audit = audit_competitor_listing(item)
        price = item.get("price", {}) or {}
        seller = item.get("seller", {}) or {}

        records.append(
            {
                "itemId": item.get("itemId", ""),
                "title": item.get("title", ""),
                "price": safe_float(price.get("value")),
                "currency": price.get("currency", "USD"),
                "seller": seller.get("username", ""),
                "feedback": seller.get("feedbackPercentage", ""),
                "condition": item.get("condition", ""),
                "policy": audit["policy_status"],
                "warnings": audit["warnings"],
                "url": item.get("itemWebUrl", ""),
            }
        )

    df = pd.DataFrame(records)

    c = st.columns(4)
    with c[0]:
        metric_card("Results", str(len(df)))
    with c[1]:
        metric_card("Avg. price", money(df["price"].mean() if len(df) else 0))
    with c[2]:
        metric_card("Policy warnings", str(int((df["policy"] == "Warning").sum())))
    with c[3]:
        metric_card("Saved", str(len(st.session_state.get("watchlist", []))))

    panel_start("Research results", "Competitor policy audit is heuristic, not an official eBay policy decision.")

    for _, row in df.iterrows():
        a, b, c = st.columns([4.5, 1.1, 1.1])
        with a:
            st.markdown(f"**{row['title']}**")
            st.caption(
                f"Seller: {row['seller']} • Feedback: {row['feedback']} • "
                f"Condition: {row['condition']}"
            )
            if row["warnings"]:
                st.warning(row["warnings"])
            else:
                st.success("No local audit warnings.")
        with b:
            st.markdown(f"**{money(row['price'], row['currency'])}**")
            st.caption(row["policy"])
        with c:
            if st.button("Save", key=f"save_{row['itemId']}"):
                save_watchlist(row.to_dict())
                st.success("Saved")

    dataframe_download(df, "ebay_product_hunting.csv")
    panel_end()


def page_listings_policy(username: str) -> None:
    page_header(
        "Listings & Policy",
        "Review eBay compliance signals and listing quality before issues become costly.",
        "Risk & Compliance",
    )

    store_name, store = selected_store(username)
    if not store:
        st.info("Connect an eBay store first.")
        return

    marketplace = store.get("marketplace_id", "EBAY_US")

    if st.button("🛡 Scan eBay compliance", type="primary"):
        with st.spinner("Checking eBay compliance..."):
            violations = fetch_ebay_compliance_violations(store, marketplace)
        st.session_state.violations = violations

    violations = st.session_state.get("violations", [])
    if not violations:
        st.success("No compliance violations were returned by the current API endpoint.")
        return

    df = pd.DataFrame(violations)

    critical = 0
    warning = 0
    for _, row in df.iterrows():
        text = json.dumps(row.to_dict()).lower()
        if any(word in text for word in ["critical", "blocked", "suspend"]):
            critical += 1
        else:
            warning += 1

    c = st.columns(3)
    with c[0]:
        metric_card("Total issues", str(len(df)))
    with c[1]:
        metric_card("Critical", str(critical))
    with c[2]:
        metric_card("Warnings", str(warning))

    panel_start("Compliance results")
    st.dataframe(df, use_container_width=True, hide_index=True)
    dataframe_download(df, "ebay_compliance_violations.csv")
    panel_end()


def page_sales(username: str) -> None:
    page_header(
        "Sales & Revenue",
        "Analyze order revenue, AOV, units, and basic order outcomes.",
        "Finance",
    )

    store_name, store = selected_store(username)
    if not store:
        st.info("Connect an eBay store first.")
        return

    marketplace = store.get("marketplace_id", "EBAY_US")

    col1, col2, col3 = st.columns(3)
    with col1:
        sales_start_date = st.date_input(
            "Start date",
            value=dt.date.today() - dt.timedelta(days=30),
            key="sales_start_date",
        )
    with col2:
        sales_end_date = st.date_input(
            "End date",
            value=dt.date.today(),
            key="sales_end_date",
        )
    with col3:
        all_time = st.checkbox("Use all synced orders", value=False)

    if st.button("📊 Build sales report", type="primary"):
        with st.spinner("Fetching sales data..."):
            days_back = 3650 if all_time else max(
                1, (sales_end_date - sales_start_date).days + 1
            )
            orders = fetch_all_ebay_orders_cached(store, marketplace, days_back)
        st.session_state.sales_orders = orders

    orders = st.session_state.get("sales_orders", [])
    rows = [order_to_row(x) for x in orders]
    if not rows:
        st.info("No sales data loaded.")
        return

    df = pd.DataFrame(rows)
    df["created_dt"] = pd.to_datetime(df["created"], errors="coerce", utc=True)

    if not all_time:
        start_ts = pd.Timestamp(sales_start_date, tz="UTC")
        end_ts = pd.Timestamp(sales_end_date + dt.timedelta(days=1), tz="UTC")
        df = df[(df["created_dt"] >= start_ts) & (df["created_dt"] < end_ts)]

    successful = df[~df["status"].isin(["Cancelled", "Unknown"])]
    revenue = successful["subtotal"].sum()
    units = successful["quantity"].sum()
    aov = successful["subtotal"].mean() if len(successful) else 0

    c = st.columns(4)
    with c[0]:
        metric_card("Revenue", money(revenue))
    with c[1]:
        metric_card("Orders", str(len(successful)))
    with c[2]:
        metric_card("Units", str(int(units)))
    with c[3]:
        metric_card("AOV", money(aov))

    panel_start("Sales breakdown")
    status_counts = df["status"].value_counts().rename_axis("status").reset_index(name="orders")
    st.dataframe(status_counts, use_container_width=True, hide_index=True)
    panel_end()

    panel_start("Order-level sales data")
    display = df.drop(columns=["raw"], errors="ignore")
    st.dataframe(display, use_container_width=True, hide_index=True)
    dataframe_download(display, "ebay_sales_report.csv")
    panel_end()


def page_promoted_ads(username: str) -> None:
    page_header(
        "Promoted Listings / Ads",
        "Keep your advertising workspace ready for campaign and performance tracking.",
        "Marketing",
    )

    panel_start(
        "eBay Ads workspace",
        "Campaign management endpoints vary by account and eBay API permissions.",
    )
    st.info(
        "This cleaned build provides the module shell and KPI workspace. "
        "Connect the eBay Marketing API campaign endpoints before enabling live campaign writes."
    )

    c = st.columns(4)
    with c[0]:
        metric_card("Ad spend", "$0.00", "Connect campaign reporting")
    with c[1]:
        metric_card("Ad revenue", "$0.00", "Connect campaign reporting")
    with c[2]:
        metric_card("ROAS", "—", "Requires campaign data")
    with c[3]:
        metric_card("Active campaigns", "0", "Requires campaign data")
    panel_end()


def page_tasks(username: str) -> None:
    page_header(
        "Tasks & Reminders",
        "Keep daily eBay operations organized inside the same workspace.",
        "Productivity",
    )

    if "tasks" not in st.session_state:
        st.session_state.tasks = []

    with st.form("new_task_form", clear_on_submit=True):
        task = st.text_input("Task")
        due = st.date_input("Due date", dt.date.today())
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        submitted = st.form_submit_button("Add task", type="primary")

    if submitted and task.strip():
        st.session_state.tasks.append(
            {
                "task": task.strip(),
                "due": str(due),
                "priority": priority,
                "done": False,
            }
        )

    if not st.session_state.tasks:
        st.info("No tasks yet.")
        return

    df = pd.DataFrame(st.session_state.tasks)
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "done": st.column_config.CheckboxColumn("Done"),
        },
    )
    st.session_state.tasks = edited.to_dict("records")


def page_price_checker(username: str) -> None:
    page_header(
        "Price Checker",
        "Quickly compare target cost, eBay price, fees, and estimated margin.",
        "Pricing",
    )

    c = st.columns(2)
    with c[0]:
        cost = st.number_input("Product cost", min_value=0.0, value=10.0, step=0.50)
        shipping = st.number_input("Shipping cost", min_value=0.0, value=3.0, step=0.50)
        ebay_fee = st.number_input("Estimated eBay fee %", min_value=0.0, max_value=100.0, value=13.5)
    with c[1]:
        sale_price = st.number_input("Target sale price", min_value=0.0, value=29.99, step=0.50)
        other_cost = st.number_input("Other cost", min_value=0.0, value=0.0, step=0.50)

    fee_amount = sale_price * ebay_fee / 100
    profit = sale_price - cost - shipping - other_cost - fee_amount
    margin = profit / sale_price * 100 if sale_price else 0

    c = st.columns(3)
    with c[0]:
        metric_card("Estimated fee", money(fee_amount))
    with c[1]:
        metric_card("Estimated profit", money(profit))
    with c[2]:
        metric_card("Net margin", f"{margin:.1f}%")

    if profit > 0:
        st.success("This price is profitable under your assumptions.")
    else:
        st.error("This price is not profitable under your assumptions.")


def page_inventory(username: str) -> None:
    page_header(
        "Inventory",
        "Simple inventory workspace for SKU, quantity, reorder level, and notes.",
        "Operations",
    )

    if "inventory" not in st.session_state:
        st.session_state.inventory = pd.DataFrame(
            columns=["SKU", "Product", "Quantity", "Reorder Level", "Notes"]
        )

    df = st.data_editor(
        st.session_state.inventory,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
    )
    st.session_state.inventory = df

    low_stock = df[
        (pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
         <= pd.to_numeric(df["Reorder Level"], errors="coerce").fillna(0))
    ] if len(df) else df

    if len(low_stock):
        st.warning(f"{len(low_stock)} SKU(s) are at or below reorder level.")
    else:
        st.success("No low-stock SKUs detected.")


def page_watchlist(username: str) -> None:
    page_header(
        "Watchlist / Saved Products",
        "Products saved during hunting sessions.",
        "Research",
    )

    watchlist = st.session_state.get("watchlist", [])
    if not watchlist:
        st.info("Your saved product opportunities will appear here.")
        return

    df = pd.DataFrame(watchlist)
    st.dataframe(df, use_container_width=True, hide_index=True)
    dataframe_download(df, "ebay_watchlist.csv")

    if st.button("Clear watchlist"):
        st.session_state.watchlist = []
        st.rerun()


def page_connect_store(username: str) -> None:
    page_header(
        "Connect eBay Store",
        "Authorize your eBay seller account and securely save its refresh token.",
        "Integrations",
    )

    if not ebay_configured():
        st.error(
            "eBay credentials are not configured. Add EBAY_CLIENT_ID, "
            "EBAY_CLIENT_SECRET and EBAY_RUNAME to Streamlit secrets or environment variables."
        )
        st.code(
            """[ebay]
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"
RUNAME = "your-runame"
""",
            language="toml",
        )
        return

    scopes = [
        "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
        "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.finances",
        "https://api.ebay.com/oauth/api_scope/commerce.message",
    ]

    auth_url = (
        EBAY_AUTH_URL
        + "?"
        + urllib.parse.urlencode(
            {
                "client_id": EBAY_CLIENT_ID,
                "redirect_uri": EBAY_RUNAME,
                "response_type": "code",
                "scope": " ".join(scopes),
            }
        )
    )

    st.markdown(
        f'<a href="{auth_url}" target="_blank">'
        '<div class="quick-action">🔗 Open eBay Authorization</div></a>',
        unsafe_allow_html=True,
    )

    st.write("")
    code = st.text_input(
        "Paste the authorization code or returned URL",
        type="password",
    )
    alias = st.text_input("Store alias", placeholder="My US Store")
    marketplace_id = st.selectbox(
        "Marketplace",
        ["EBAY_US", "EBAY_GB", "EBAY_DE", "EBAY_AU"],
    )

    # Automatic OAuth callback: when eBay redirects back to the configured
    # RuName/URL, Streamlit exposes the returned ?code=... query parameter.
    # This removes the need to copy/paste the authorization code manually.
    query_code = st.query_params.get("code", "")
    query_error = st.query_params.get("error", "")
    if query_error:
        st.error(f"eBay authorization failed: {query_error}")
    if query_code and not st.session_state.get("ebay_oauth_processed"):
        try:
            with st.spinner("Completing eBay authorization..."):
                token_data = exchange_code_for_tokens(query_code, production=True)
            stores = load_stores()
            user_stores = stores.setdefault(username, {})
            auto_alias = alias.strip() or f"eBay {marketplace_id}"
            user_stores[auto_alias] = {
                "access_token": token_data.get("access_token", ""),
                "access_token_expires_at": time.time() + int(token_data.get("expires_in", 7200)),
                "refresh_token": token_data.get("refresh_token", ""),
                "token_type": token_data.get("token_type", "Bearer"),
                "marketplace_id": marketplace_id,
                "connected_at": dt.datetime.now().isoformat(timespec="seconds"),
            }
            save_stores(stores)
            st.session_state.ebay_oauth_processed = True
            st.query_params.clear()
            st.success(f"{auto_alias} connected successfully. OAuth token is now managed automatically.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not complete eBay authorization: {exc}")

    if st.button("Save connected store", type="primary", use_container_width=True):
        if not code or not alias:
            st.warning("Enter authorization code and store alias, or use the automatic eBay callback above.")
            return

        try:
            with st.spinner("Exchanging authorization code..."):
                token_data = exchange_code_for_tokens(code, production=True)

            stores = load_stores()
            user_stores = stores.setdefault(username, {})

            user_stores[alias] = {
                "access_token": token_data.get("access_token", ""),
                "access_token_expires_at": time.time() + int(token_data.get("expires_in", 7200)),
                "refresh_token": token_data.get("refresh_token", ""),
                "token_type": token_data.get("token_type", "Bearer"),
                "marketplace_id": marketplace_id,
                "connected_at": dt.datetime.now().isoformat(timespec="seconds"),
            }

            save_stores(stores)
            st.success(f"{alias} connected successfully.")
        except Exception as exc:
            st.error(f"Could not connect store: {exc}")

    st.divider()

    stores = get_user_stores(username)
    if stores:
        st.subheader("Connected stores")
        for name, store in list(stores.items()):
            c1, c2, c3 = st.columns([2.5, 1, 1])
            with c1:
                st.write(name)
                st.caption(store.get("marketplace_id", "EBAY_US"))
            with c2:
                st.markdown('<span class="status-pill">Connected</span>', unsafe_allow_html=True)
            with c3:
                if st.button("Disconnect", key=f"disconnect_{name}"):
                    all_stores = load_stores()
                    all_stores.get(username, {}).pop(name, None)
                    save_stores(all_stores)
                    st.success("Store disconnected.")
                    st.rerun()


def page_templates(username: str) -> None:
    page_header(
        "Message Templates",
        "Create reusable buyer messages with dynamic order variables.",
        "Automation",
    )

    templates = load_json(FILES["templates"], DEFAULT_TEMPLATES.copy())
    if not isinstance(templates, dict):
        templates = DEFAULT_TEMPLATES.copy()

    names = list(templates.keys())
    selected = st.selectbox("Template", names)

    name = st.text_input("Template name", value=selected)
    body = st.text_area(
        "Message",
        value=templates[selected],
        height=180,
        help="Variables: {buyer}, {order_id}, {carrier}, {tracking_number}",
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save template", type="primary", use_container_width=True):
            templates[name] = body
            if name != selected:
                templates.pop(selected, None)
            save_json(FILES["templates"], templates)
            st.success("Template saved.")
    with c2:
        if st.button("Restore default templates", use_container_width=True):
            save_json(FILES["templates"], DEFAULT_TEMPLATES.copy())
            st.success("Defaults restored.")
            st.rerun()

    st.caption("Supported variables: {buyer} • {order_id} • {carrier} • {tracking_number}")


def page_registered_clients() -> None:
    page_header(
        "Registered Clients",
        "Admin workspace for account status and module access.",
        "Administration",
    )

    users = load_users()
    rows = []

    for username, user in users.items():
        rows.append(
            {
                "username": username,
                "email": user.get("email", ""),
                "role": user.get("role", "client"),
                "enabled": user.get("enabled", True),
                "modules": len(user.get("modules", [])),
                "stores": len(get_user_stores(username)),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    target = st.selectbox("Select account", list(users.keys()))
    if target:
        user = users[target]
        enabled = st.checkbox("Account enabled", value=user.get("enabled", True))

        modules = st.multiselect(
            "Allowed modules",
            ALL_MODULES,
            default=user.get("modules", ALL_MODULES),
        )

        if st.button("Save account access", type="primary"):
            users[target]["enabled"] = enabled
            users[target]["modules"] = modules
            save_users(users)
            st.success("Account updated.")


# ============================================================
# ROUTER
# ============================================================

def main() -> None:
    ensure_admin()

    if not st.session_state.get("logged_in"):
        login_screen()
        return

    username = st.session_state.get("username", "")
    role = st.session_state.get("role", "client")

    page = render_sidebar(username, role)
    render_change_password(username)

    if page == "Dashboard":
        page_dashboard(username)
    elif page == "Orders & Auto-Messaging":
        page_orders(username)
    elif page == "Product Hunting & Research":
        page_product_hunting(username)
    elif page == "Listings & Policy":
        page_listings_policy(username)
    elif page == "Sales & Revenue":
        page_sales(username)
    elif page == "Promoted Listings / Ads":
        page_promoted_ads(username)
    elif page == "Tasks & Reminders":
        page_tasks(username)
    elif page == "Price Checker":
        page_price_checker(username)
    elif page == "Inventory":
        page_inventory(username)
    elif page == "Watchlist / Saved Products":
        page_watchlist(username)
    elif page == "Connect eBay Store":
        page_connect_store(username)
    elif page == "Message Templates":
        page_templates(username)
    elif page == "Registered Clients":
        if role == "admin":
            page_registered_clients()
        else:
            st.error("Admin access required.")

    st.markdown(
        '<div class="footer">eBay-only • Product Hunting • Auto Messages • '
        'Orders • Sales • Policy • Inventory • Ads</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
