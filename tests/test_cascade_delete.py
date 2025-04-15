import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import db
from app.models.contact import Contact
from app.models.meeting_request import ContactType, MeetingRequest, MeetingRequestStatus
from app.models.place import Place
from app.models.subscription import Subscription
from app.models.user import User


def test_cascade_delete_user(app):
    """Test that deleting a user cascades to all related records."""
    with app.app_context():
        # Create a user
        user = User(email="test_cascade@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()  # Get the user ID without committing
        user_id = user.id

        # Create a subscription
        subscription = Subscription(
            user_id=user.id,
            plan_id="premium",
            status="active",
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.session.add(subscription)

        # Create a contact
        contact = Contact(
            user_id=user.id,
            name="Test Contact",
            email="contact@example.com",
        )
        db.session.add(contact)

        # Create a place
        place = Place(
            name="Test Place",
            address="123 Test St",
            latitude=10.0,
            longitude=20.0,
            suggested_by_id=user.id,
            google_place_id="test_place_id",
        )
        db.session.add(place)

        # Create a meeting request
        meeting_req = MeetingRequest(
            user_a_id=user.id,
            user_b_contact_type=ContactType.EMAIL,
            user_b_email="userb@example.com",
            location_type="Restaurant",
            address_a_lat=10.0,
            address_a_lon=20.0,
            location_a={"address": "123 Main St", "latitude": 10.0, "longitude": 20.0},
            token_b="testtoken123",
            status=MeetingRequestStatus.PENDING_B_ADDRESS,
        )
        meeting_req.user_b_contact = "userb@example.com"
        db.session.add(meeting_req)

        # Commit to save all records
        db.session.commit()

        # Verify records exist after creation
        subscription_count = Subscription.query.filter_by(user_id=user_id).count()
        contact_count = Contact.query.filter_by(user_id=user_id).count()
        place_count = Place.query.filter_by(suggested_by_id=user_id).count()
        meeting_count = MeetingRequest.query.filter_by(user_a_id=user_id).count()

        assert subscription_count > 0, "Should have subscriptions before deletion"
        assert contact_count > 0, "Should have contacts before deletion"
        assert place_count > 0, "Should have places before deletion"
        assert meeting_count > 0, "Should have meeting requests before deletion"

        print(
            f"Before deletion: Subscriptions={subscription_count}, Contacts={contact_count}, Places={place_count}, Meetings={meeting_count}"
        )

        # Delete the user
        db.session.delete(user)
        db.session.commit()

        # Verify all related records are deleted
        user_exists = User.query.get(user_id) is not None
        subscription_count = Subscription.query.filter_by(user_id=user_id).count()
        contact_count = Contact.query.filter_by(user_id=user_id).count()
        place_count = Place.query.filter_by(suggested_by_id=user_id).count()
        meeting_count = MeetingRequest.query.filter_by(user_a_id=user_id).count()

        print(
            f"After deletion: User exists={user_exists}, Subscriptions={subscription_count}, Contacts={contact_count}, Places={place_count}, Meetings={meeting_count}"
        )

        assert not user_exists, "User should be deleted"
        assert subscription_count == 0, "Subscriptions should be deleted"
        assert contact_count == 0, "Contacts should be deleted"
        assert place_count == 0, "Places should be deleted"
        assert meeting_count == 0, "Meeting requests should be deleted"
