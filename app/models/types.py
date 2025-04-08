import json
import uuid

from sqlalchemy import CHAR, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID


class UUIDType(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's UUID type when available, otherwise
    uses CHAR(36).
    """

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # Convert to string for all dialects to ensure compatibility
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            # Handle string values that might contain 'urn:' or 'uuid:' prefixes
            if isinstance(value, str):
                value = value.replace("urn:", "").replace("uuid:", "")
            return uuid.UUID(str(value))
        except (ValueError, AttributeError):
            return None


class JSONType(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)

    def process_literal_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)
