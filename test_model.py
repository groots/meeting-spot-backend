from datetime import datetime, timedelta, timezone

from app import create_app
from app.models import ContactType, MeetingRequest, MeetingRequestStatus

app = create_app()
with app.app_context():
    # Set up timestamps for testing
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=1)

    # Test setting user_b_email
    mr1 = MeetingRequest(
        user_b_email="test1@example.com",
        location_a={"address": "123 Main St"},
        address_a_lat=10,
        address_a_lon=10,
        location_type="coffee",
        token_b="xyz",
        status=MeetingRequestStatus.PENDING_B_ADDRESS,
        created_at=now,
        updated_at=now,
        expires_at=expires,
    )
    print(f"MR1 - Contact: {mr1.user_b_contact}, Email: {mr1.user_b_email}, Type: {mr1.user_b_contact_type.value}")

    # Test setting user_b_contact directly
    mr2 = MeetingRequest(
        user_b_contact_type=ContactType.EMAIL,
        user_b_contact="test2@example.com",
        location_a={"address": "123 Main St"},
        address_a_lat=10,
        address_a_lon=10,
        location_type="coffee",
        token_b="xyz",
        status=MeetingRequestStatus.PENDING_B_ADDRESS,
        created_at=now,
        updated_at=now,
        expires_at=expires,
    )
    print(f"MR2 - Contact: {mr2.user_b_contact}, Email: {mr2.user_b_email}, Type: {mr2.user_b_contact_type.value}")

    # Test backward compatibility in to_dict
    dict_result = mr1.to_dict()
    print(f"MR1 to_dict has user_b_email: {'user_b_email' in dict_result}")
    print(f"MR1 user_b_email value: {dict_result.get('user_b_email')}")
