import json
import uuid
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import String, TypeDecorator


class UUIDType(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect) -> None:
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect) -> None:
        if value is None:
            return None
        return uuid.UUID(value)

    def process_literal_param(self, value, dialect) -> None:
        if value is None:
            return None
        return str(value)


class JSONType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect) -> None:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect) -> None:
        if value is None:
            return None
        return json.loads(value)

    def process_literal_param(self, value, dialect) -> None:
        if value is None:
            return None
        return json.dumps(value)
