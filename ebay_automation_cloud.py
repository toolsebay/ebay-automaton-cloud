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

# --- eBay Credentials ---
EBAY_CLIENT_ID = st.secrets.get("EBAY_CLIENT_ID", os.getenv("EBAY_CLIENT_ID", "NawazIqb-eBayAuto-PRD-d254d2f41-10c98af7"))
EBAY_CLIENT_SECRET = st.secrets.get("EBAY_CLIENT_SECRET", os.getenv("EBAY_CLIENT_SECRET", ""))
EBAY_RUNAME = st.secrets.get("EBAY_RUNAME", os.getenv("EBAY_RUNAME", ""))

SMTP_EMAIL = st.secrets.get("SMTP_EMAIL", os.getenv("SMTP_EMAIL", ""))
SMTP_PASSWORD = st.secrets.get("SMTP_PASSWORD", os.getenv("SMTP_PASSWORD", ""))

WHATSAPP_NUMBER = st.secrets.get("WHATSAPP_NUMBER", os.getenv("WHATSAPP_NUMBER", ""))
WHATSAPP_DEFAULT_MSG = "Hello, I need help with the eBay Automation Dashboard."
WHATSAPP_LINK = (
    f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib.parse.quote(WHATSAPP_DEFAULT_MSG)}"
    if WHATSAPP_NUMBER
    else ""
)

# Standard eBay OAuth Endpoints
EBAY_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_API_BASE = "https://api.ebay.com"

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
    "free shipping", "l@@k", "wow", "must see", "best price",
    "authentic", "genuine", "top rated", "brand new sealed",
    "rare", "hot", "fast ship"
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
    symbol = {"USD": "\(", "GBP": "£", "EUR": "€", "AUD": "A\)"}.get(currency, currency + " ")
    return f"{symbol}{amount:,.2f}"


def page_header(title: str, subtitle: str = "", eyebrow: str = "eBay Automation") -> None:
    st.markdown(
        f"""






{eyebrow}


{title}


{subtitle}



    """,
    unsafe_allow_html=True,
)


def metric_card(label: str, value: str, help_text: str = "") -> None:
st.markdown(
f"""



{label}


{value}


{help_text}



    """,
    unsafe_allow_html=True,
)


def panel_start(title: str, subtitle: str = "") -> None:
st.markdown(
f"""



{title}


{subtitle}




    """,
    unsafe_allow_html=True,
)



def panel_end() -> None:
st.markdown("
", unsafe_allow_html=True)
def dataframe_download(df: pd.DataFrame, filename: str, label: str = "Export CSV") -> None:
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(
label=label,
data=csv_bytes,
file_name=filename,
mime="text/csv",
)
============================================================
USER / AUTH
============================================================
def load_users() -> Dict[str, Any]:
users = load_json(FILES["users"], {})
return users if isinstance(users, dict) else {}
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
st.markdown('
