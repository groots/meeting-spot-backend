from enum import Enum
from typing import Any, Dict, List, Optional, Union


class MeetingRequestStatus(Enum):
    """Enum for meeting request statuses."""

    PENDING_B_ADDRESS = "pending_b_address"
    CALCULATING = "calculating"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


class ContactType(Enum):
    """Enum for contact types."""

    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
