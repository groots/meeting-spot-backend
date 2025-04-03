"""Helper functions for the application."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from flask import current_app, jsonify, request
from werkzeug.exceptions import HTTPException

# Configure logger
logger = logging.getLogger(__name__)


def get_current_time() -> datetime:
    """
    Get the current time in UTC.
    """
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime) -> str:
    """
    Format a datetime object to ISO format string.
    """
    return dt.isoformat()


def parse_datetime(dt_str: str) -> datetime:
    """
    Parse an ISO format datetime string to datetime object.
    """
    return datetime.fromisoformat(dt_str)


def get_request_json() -> Dict[str, Any]:
    """
    Get JSON data from request body.
    Raises HTTPException if request body is not valid JSON.
    """
    if not request.is_json:
        raise HTTPException(
            description="Request body must be JSON",
            response=jsonify({"error": "Request body must be JSON"}),
        )

    try:
        return request.get_json()
    except Exception as e:
        logger.error(f"Error parsing JSON request body: {e}")
        raise HTTPException(
            description="Invalid JSON in request body",
            response=jsonify({"error": "Invalid JSON in request body"}),
        )


def get_query_params() -> Dict[str, Any]:
    """
    Get query parameters from request.
    """
    return dict(request.args)


def get_pagination_params() -> tuple[int, int]:
    """
    Get pagination parameters from request.
    Returns tuple of (page, per_page).
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get(
        "per_page",
        current_app.config.get("DEFAULT_ITEMS_PER_PAGE", 10),
        type=int,
    )
    return page, per_page


def get_sort_params() -> tuple[str, str]:
    """
    Get sort parameters from request.
    Returns tuple of (sort_by, sort_order).
    """
    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc").lower()
    return sort_by, sort_order


def get_filter_params() -> Dict[str, Any]:
    """
    Get filter parameters from request.
    """
    filters = {}
    for key, value in request.args.items():
        if key not in ["page", "per_page", "sort_by", "sort_order"]:
            filters[key] = value
    return filters


def paginate_query(query, page: int, per_page: int):
    """
    Paginate a SQLAlchemy query.
    Returns tuple of (items, total).
    """
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination.items, pagination.total


def format_response(
    data: Any,
    message: Optional[str] = None,
    status_code: int = 200,
) -> tuple[Dict[str, Any], int]:
    """
    Format API response.
    """
    response = {"data": data}
    if message:
        response["message"] = message
    return response, status_code


def format_error_response(
    error: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None,
) -> tuple[Dict[str, Any], int]:
    """
    Format error response.
    """
    response = {"error": error}
    if details:
        response["details"] = details
    return response, status_code


def validate_required_fields(
    data: Dict[str, Any], required_fields: List[str]
) -> None:
    """
    Validate required fields in request data.
    Raises HTTPException if any required field is missing.
    """
    missing_fields = [
        field for field in required_fields if field not in data
    ]
    if missing_fields:
        raise HTTPException(
            description=f"Missing required fields: {', '.join(missing_fields)}",
            response=jsonify(
                {
                    "error": "Missing required fields",
                    "details": {"missing_fields": missing_fields},
                }
            ),
        )


def validate_field_types(
    data: Dict[str, Any], field_types: Dict[str, type]
) -> None:
    """
    Validate field types in request data.
    Raises HTTPException if any field has incorrect type.
    """
    for field, expected_type in field_types.items():
        if field in data and not isinstance(data[field], expected_type):
            raise HTTPException(
                description=f"Field '{field}' must be of type {expected_type.__name__}",
                response=jsonify(
                    {
                        "error": "Invalid field type",
                        "details": {
                            "field": field,
                            "expected_type": expected_type.__name__,
                            "actual_type": type(data[field]).__name__,
                        },
                    }
                ),
            )


def validate_field_values(
    data: Dict[str, Any],
    field_validators: Dict[str, callable],
) -> None:
    """
    Validate field values using custom validator functions.
    Raises HTTPException if any field fails validation.
    """
    for field, validator in field_validators.items():
        if field in data and not validator(data[field]):
            raise HTTPException(
                description=f"Invalid value for field '{field}'",
                response=jsonify(
                    {
                        "error": "Invalid field value",
                        "details": {"field": field},
                    }
                ),
            )


def validate_unique_fields(
    model: Any,
    data: Dict[str, Any],
    unique_fields: List[str],
) -> None:
    """
    Validate unique fields in request data.
    Raises HTTPException if any unique field already exists.
    """
    for field in unique_fields:
        if field in data:
            existing = model.query.filter_by(**{field: data[field]}).first()
            if existing:
                raise HTTPException(
                    description=f"Field '{field}' must be unique",
                    response=jsonify(
                        {
                            "error": "Duplicate field value",
                            "details": {"field": field},
                        }
                    ),
                )


def validate_foreign_key(
    model: Any,
    field: str,
    value: Any,
) -> None:
    """
    Validate foreign key relationship.
    Raises HTTPException if referenced record does not exist.
    """
    if not model.query.get(value):
        raise HTTPException(
            description=f"Referenced {field} does not exist",
            response=jsonify(
                {
                    "error": "Invalid foreign key",
                    "details": {"field": field},
                }
            ),
        )


def validate_date_range(
    start_date: datetime,
    end_date: datetime,
) -> None:
    """
    Validate date range.
    Raises HTTPException if end date is before start date.
    """
    if end_date < start_date:
        raise HTTPException(
            description="End date must be after start date",
            response=jsonify(
                {
                    "error": "Invalid date range",
                    "details": {
                        "start_date": format_datetime(start_date),
                        "end_date": format_datetime(end_date),
                    },
                }
            ),
        )


def validate_time_range(
    start_time: datetime,
    end_time: datetime,
) -> None:
    """
    Validate time range.
    Raises HTTPException if end time is before start time.
    """
    if end_time < start_time:
        raise HTTPException(
            description="End time must be after start time",
            response=jsonify(
                {
                    "error": "Invalid time range",
                    "details": {
                        "start_time": format_datetime(start_time),
                        "end_time": format_datetime(end_time),
                    },
                }
            ),
        )


def validate_coordinates(
    latitude: float,
    longitude: float,
) -> None:
    """
    Validate coordinates.
    Raises HTTPException if coordinates are invalid.
    """
    if not (-90 <= latitude <= 90):
        raise HTTPException(
            description="Latitude must be between -90 and 90",
            response=jsonify(
                {
                    "error": "Invalid coordinates",
                    "details": {"field": "latitude"},
                }
            ),
        )

    if not (-180 <= longitude <= 180):
        raise HTTPException(
            description="Longitude must be between -180 and 180",
            response=jsonify(
                {
                    "error": "Invalid coordinates",
                    "details": {"field": "longitude"},
                }
            ),
        )


def validate_radius(radius: float) -> None:
    """
    Validate search radius.
    Raises HTTPException if radius is invalid.
    """
    max_radius = current_app.config.get("MAX_SEARCH_RADIUS", 50)
    if not (0 < radius <= max_radius):
        raise HTTPException(
            description=f"Radius must be between 0 and {max_radius}",
            response=jsonify(
                {
                    "error": "Invalid radius",
                    "details": {
                        "min": 0,
                        "max": max_radius,
                    },
                }
            ),
        )


def validate_file_size(file_size: int, max_size_mb: int = 5) -> None:
    """
    Validate file size.
    Raises HTTPException if file size is too large.
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            description=f"File size must be less than {max_size_mb}MB",
            response=jsonify(
                {
                    "error": "File too large",
                    "details": {
                        "max_size_mb": max_size_mb,
                    },
                }
            ),
        )


def validate_file_extension(
    filename: str,
    allowed_extensions: List[str],
) -> None:
    """
    Validate file extension.
    Raises HTTPException if file extension is not allowed.
    """
    if not filename or "." not in filename:
        raise HTTPException(
            description="File must have an extension",
            response=jsonify(
                {
                    "error": "Invalid file extension",
                    "details": {
                        "allowed_extensions": allowed_extensions,
                    },
                }
            ),
        )

    extension = filename.rsplit(".", 1)[1].lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            description=f"File extension must be one of: {', '.join(allowed_extensions)}",
            response=jsonify(
                {
                    "error": "Invalid file extension",
                    "details": {
                        "allowed_extensions": allowed_extensions,
                    },
                }
            ),
        )


def validate_rating(rating: float) -> None:
    """
    Validate rating value.
    Raises HTTPException if rating is invalid.
    """
    if not (0 <= rating <= 5):
        raise HTTPException(
            description="Rating must be between 0 and 5",
            response=jsonify(
                {
                    "error": "Invalid rating",
                    "details": {
                        "min": 0,
                        "max": 5,
                    },
                }
            ),
        )


def validate_comment_length(comment: str, max_length: int = 1000) -> None:
    """
    Validate comment length.
    Raises HTTPException if comment is too long.
    """
    if len(comment) > max_length:
        raise HTTPException(
            description=f"Comment must be less than {max_length} characters",
            response=jsonify(
                {
                    "error": "Comment too long",
                    "details": {
                        "max_length": max_length,
                    },
                }
            ),
        )


def validate_tags(tags: List[str]) -> None:
    """
    Validate tags.
    Raises HTTPException if tags are invalid.
    """
    if not tags:
        raise HTTPException(
            description="At least one tag is required",
            response=jsonify(
                {
                    "error": "Invalid tags",
                    "details": {
                        "min_tags": 1,
                    },
                }
            ),
        )

    for tag in tags:
        if len(tag) < 2:
            raise HTTPException(
                description="Each tag must be at least 2 characters long",
                response=jsonify(
                    {
                        "error": "Invalid tags",
                        "details": {
                            "min_tag_length": 2,
                        },
                    }
                ),
            )

        if not tag.replace(" ", "").isalnum():
            raise HTTPException(
                description="Tags can only contain letters, numbers, and spaces",
                response=jsonify(
                    {
                        "error": "Invalid tags",
                        "details": {
                            "allowed_characters": "letters, numbers, and spaces",
                        },
                    }
                ),
            )


def validate_price_range(
    min_price: float,
    max_price: float,
) -> None:
    """
    Validate price range.
    Raises HTTPException if price range is invalid.
    """
    if min_price < 0:
        raise HTTPException(
            description="Minimum price cannot be negative",
            response=jsonify(
                {
                    "error": "Invalid price range",
                    "details": {
                        "field": "min_price",
                    },
                }
            ),
        )

    if max_price < min_price:
        raise HTTPException(
            description="Maximum price must be greater than minimum price",
            response=jsonify(
                {
                    "error": "Invalid price range",
                    "details": {
                        "min_price": min_price,
                        "max_price": max_price,
                    },
                }
            ),
        )


def validate_capacity(capacity: int) -> None:
    """
    Validate capacity value.
    Raises HTTPException if capacity is invalid.
    """
    if capacity <= 0:
        raise HTTPException(
            description="Capacity must be greater than 0",
            response=jsonify(
                {
                    "error": "Invalid capacity",
                    "details": {
                        "min_capacity": 1,
                    },
                }
            ),
        )


def validate_duration(duration: int) -> None:
    """
    Validate duration value.
    Raises HTTPException if duration is invalid.
    """
    if duration <= 0:
        raise HTTPException(
            description="Duration must be greater than 0",
            response=jsonify(
                {
                    "error": "Invalid duration",
                    "details": {
                        "min_duration": 1,
                    },
                }
            ),
        )

    max_duration = current_app.config.get("MAX_DURATION", 480)  # 8 hours
    if duration > max_duration:
        raise HTTPException(
            description=f"Duration must be less than {max_duration} minutes",
            response=jsonify(
                {
                    "error": "Invalid duration",
                    "details": {
                        "max_duration": max_duration,
                    },
                }
            ),
        )


def validate_availability(
    start_time: datetime,
    end_time: datetime,
    existing_bookings: List[Dict[str, Any]],
) -> None:
    """
    Validate time slot availability.
    Raises HTTPException if time slot is not available.
    """
    for booking in existing_bookings:
        booking_start = parse_datetime(booking["start_time"])
        booking_end = parse_datetime(booking["end_time"])

        if start_time < booking_end and end_time > booking_start:
            raise HTTPException(
                description="Time slot is not available",
                response=jsonify(
                    {
                        "error": "Time slot not available",
                        "details": {
                            "start_time": format_datetime(start_time),
                            "end_time": format_datetime(end_time),
                            "conflicting_booking": {
                                "start_time": format_datetime(booking_start),
                                "end_time": format_datetime(booking_end),
                            },
                        },
                    }
                ),
            )


def validate_pagination_params(
    page: int,
    per_page: int,
    max_per_page: int = 100,
) -> None:
    """
    Validate pagination parameters.
    Raises HTTPException if parameters are invalid.
    """
    if page < 1:
        raise HTTPException(
            description="Page number must be greater than 0",
            response=jsonify(
                {
                    "error": "Invalid pagination parameters",
                    "details": {
                        "field": "page",
                        "min_value": 1,
                    },
                }
            ),
        )

    if per_page < 1:
        raise HTTPException(
            description="Items per page must be greater than 0",
            response=jsonify(
                {
                    "error": "Invalid pagination parameters",
                    "details": {
                        "field": "per_page",
                        "min_value": 1,
                    },
                }
            ),
        )

    if per_page > max_per_page:
        raise HTTPException(
            description=f"Items per page cannot exceed {max_per_page}",
            response=jsonify(
                {
                    "error": "Invalid pagination parameters",
                    "details": {
                        "field": "per_page",
                        "max_value": max_per_page,
                    },
                }
            ),
        )


def format_pagination_response(
    items: List[Any],
    total: int,
    page: int,
    per_page: int,
) -> Dict[str, Any]:
    """
    Format paginated response.
    """
    return {
        "data": items,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        },
    }


def format_sort_response(
    items: List[Any],
    sort_by: str,
    sort_order: str,
) -> Dict[str, Any]:
    """
    Format sorted response.
    """
    return {
        "data": items,
        "sort": {
            "by": sort_by,
            "order": sort_order,
        },
    }


def format_filter_response(
    items: List[Any],
    filters: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Format filtered response.
    """
    return {
        "data": items,
        "filters": filters,
    }


def format_search_response(
    items: List[Any],
    query: str,
    total: int,
) -> Dict[str, Any]:
    """
    Format search response.
    """
    return {
        "data": items,
        "search": {
            "query": query,
            "total": total,
        },
    }


def format_error_details(
    error: Exception,
) -> Dict[str, Any]:
    """
    Format error details for response.
    """
    details = {
        "type": type(error).__name__,
        "message": str(error),
    }

    if hasattr(error, "details"):
        details["details"] = error.details

    return details


def log_error(error: Exception) -> None:
    """
    Log error details.
    """
    logger.error(
        f"Error: {type(error).__name__} - {str(error)}",
        exc_info=True,
    )


def handle_error(error: Exception) -> tuple[Dict[str, Any], int]:
    """
    Handle error and return appropriate response.
    """
    log_error(error)

    if isinstance(error, HTTPException):
        return format_error_response(
            error.description,
            error.code,
            format_error_details(error),
        )

    return format_error_response(
        "Internal server error",
        500,
        format_error_details(error),
    ) 