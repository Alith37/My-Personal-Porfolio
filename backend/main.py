
import os
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from pydantic import field_validator

    def validator_compat(*fields):
        return field_validator(*fields)
except ImportError:
    from pydantic import validator

    def validator_compat(*fields):
        return validator(*fields, allow_reuse=True)

from pymongo import MongoClient
from pymongo.errors import (
    ConfigurationError,
    PyMongoError,
    ServerSelectionTimeoutError,
)


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

# Load environment variables from backend/.env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)


def sanitize_mongo_uri(raw_uri: str) -> str:
    """
    Safely normalize MongoDB URI.

    Handles passwords containing special characters by
    URL-encoding the password portion.
    """
    if not raw_uri:
        return raw_uri

    # Strip surrounding whitespace and optional quotes (single or double)
    raw_uri = raw_uri.strip().strip('"\'')

    # Support both SRV and standard connection strings
    prefixes = ["mongodb+srv://", "mongodb://"]
    for prefix in prefixes:
        if raw_uri.startswith(prefix):
            rest = raw_uri[len(prefix):]
            at_idx = rest.rfind("@")
            if at_idx != -1:
                user_pass = rest[:at_idx]
                host_and_options = rest[at_idx + 1:]
                if ":" in user_pass:
                    username, password = user_pass.split(":", 1)
                    # Remove accidental angle brackets if present
                    password = password.strip("<>")
                    # Decode first in case it is already encoded,
                    # then encode it correctly.
                    password = urllib.parse.unquote_plus(password)
                    password = urllib.parse.quote_plus(password)
                    return f"{prefix}{username}:{password}@{host_and_options}"
    return raw_uri


def mask_credentials(text: str) -> str:
    """
    Hide username/password credentials from MongoDB error messages.
    """
    return re.sub(
        r"://([^:]+):([^@]+)@",
        r"://\1:***@",
        str(text),
    )


MONGODB_URI = sanitize_mongo_uri(
    os.getenv("MONGODB_URI", "").strip()
)

DATABASE_NAME = os.getenv(
    "DATABASE_NAME",
    "PortfolioDB",
).strip()

COLLECTION_NAME = os.getenv(
    "COLLECTION_NAME",
    "contacts",
).strip()


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Portfolio Contact API",
    description=(
        "Backend API for portfolio contact form submissions."
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "https://my-personal-porfolio-peach.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=(
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================
# VALIDATION
# ============================================================

EMAIL_REGEX = (
    r"^[a-zA-Z0-9_.+-]+@"
    r"[a-zA-Z0-9-]+\."
    r"[a-zA-Z0-9-.]+$"
)


class ContactRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Sender's full name",
    )

    email: str = Field(
        ...,
        min_length=3,
        max_length=254,
        description="Sender's email address",
    )

    phone: Optional[str] = Field(
        None,
        max_length=40,
        description="Optional phone number",
    )

    service: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Service requested",
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Project message",
    )

    @validator_compat("name", "service", "message")
    def validate_non_empty(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "Field cannot be empty or contain only whitespace."
            )

        return cleaned

    @validator_compat("email")
    def validate_email_address(cls, value: str) -> str:
        cleaned = value.strip()

        if not re.match(EMAIL_REGEX, cleaned):
            raise ValueError("Invalid email format.")

        return cleaned.lower()

    @validator_compat("phone")
    def sanitize_phone(
        cls,
        value: Optional[str],
    ) -> Optional[str]:

        if value is None:
            return None

        cleaned = value.strip()

        return cleaned if cleaned else None


class ContactResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# MONGODB CLIENT
# ============================================================

_client: Optional[MongoClient] = None
_cached_uri: Optional[str] = None


def get_mongo_client():
    """
    Return a working MongoDB client.

    Creates a new client when necessary and verifies the
    connection with a ping.
    """

    global _client, _cached_uri

    # Reload .env in case configuration changed
    load_dotenv(
        dotenv_path=env_path,
        override=True,
    )

    raw_uri = os.getenv(
        "MONGODB_URI",
        "",
    ).strip()

    uri = sanitize_mongo_uri(raw_uri)

    if (
        not uri
        or "<username>" in uri
        or "<password>" in uri
    ):
        return (
            None,
            "MongoDB connection string is not configured. "
            "Please set MONGODB_URI in backend/.env.",
        )

    try:

        # Create a client if one doesn't exist,
        # or if the connection string changed.
        if _client is None or _cached_uri != uri:

            if _client is not None:
                try:
                    _client.close()
                except Exception:
                    pass

            _client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
            )

            _cached_uri = uri

        # Verify connection
        _client.admin.command("ping")

        return _client, None

    except (
        ConfigurationError,
        ServerSelectionTimeoutError,
        PyMongoError,
    ) as e:

        _client = None
        _cached_uri = None

        return (
            None,
            "Could not connect to MongoDB Atlas: "
            f"{mask_credentials(str(e))}",
        )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    """
    Check API and MongoDB connectivity.
    """

    client, error = get_mongo_client()

    db_status = (
        "connected"
        if client is not None
        else f"unconnected ({error})"
    )

    return {
        "status": "online",
        "app": "Portfolio Contact API",
        "database": db_status,
        "database_name": DATABASE_NAME,
        "collection_name": COLLECTION_NAME,
    }


# ============================================================
# CONTACT FORM ENDPOINT
# ============================================================

@app.post(
    "/api/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
    tags=["Contact"],
    summary="Submit contact form",
)
def submit_contact(payload: ContactRequest):
    """
    Validate contact form data and save it to MongoDB Atlas.
    """

    client, db_error = get_mongo_client()

    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "message": (
                    "Database service is currently unavailable. "
                    "Please verify backend/.env configuration."
                ),
                "error": mask_credentials(db_error),
            },
        )

    try:

        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]

        document = {
            "name": payload.name,
            "email": payload.email,
            "phone": payload.phone,
            "service": payload.service,
            "message": payload.message,
            "created_at": (
                datetime.now(timezone.utc).isoformat()
            ),
        }

        result = collection.insert_one(document)

        if not result.inserted_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "message": (
                        "Failed to store contact submission."
                    ),
                },
            )

        return ContactResponse(
            success=True,
            message="Your message has been received.",
        )

    except PyMongoError as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": (
                    "A database error occurred while "
                    "saving your message."
                ),
                "error": mask_credentials(str(e)),
            },
        )
