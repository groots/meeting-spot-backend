import json
import uuid
from datetime import datetime, timezone

import pytest

from app.models import Contact, Subscription, User
from app.utils.stripe_helpers import is_premium_feature


@pytest.mark.usefixtures("client", "db_session")
class TestContactsApi:
    """Test class for contacts API endpoints."""

    def test_list_contacts_unauthorized(self, client):
        """Test that unauthorized users cannot list contacts."""
        response = client.get("/api/v1/contacts/")
        assert response.status_code == 401

    def test_create_contact_unauthorized(self, client):
        """Test that unauthorized users cannot create contacts."""
        response = client.post(
            "/api/v1/contacts/",
            json={"name": "Test Contact", "email": "test@example.com"},
        )
        assert response.status_code == 401

    def test_list_contacts(self, client, db_session, test_user, auth_headers):
        """Test listing user contacts."""
        # Create some contacts for the test user
        contacts = []
        for i in range(3):
            contact = Contact(
                user_id=test_user.id,
                name=f"Contact {i}",
                email=f"contact{i}@example.com",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            contacts.append(contact)
            db_session.add(contact)
        db_session.commit()

        # Get contacts
        response = client.get("/api/v1/contacts/", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["name"] == "Contact 0"
        assert data[1]["email"] == "contact1@example.com"

    def test_create_contact(self, client, db_session, test_user, auth_headers):
        """Test creating a new contact."""
        # Mock premium status for test user
        test_user.subscription_plan = "premium"
        test_user.subscription_status = "active"
        db_session.commit()

        # Create contact data
        contact_data = {
            "name": "New Contact",
            "email": "new@example.com",
            "phone": "123-456-7890",
            "company": "Test Company",
            "notes": "Test notes",
        }

        # Create contact
        response = client.post("/api/v1/contacts/", json=contact_data, headers=auth_headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["name"] == contact_data["name"]
        assert data["email"] == contact_data["email"]
        assert data["phone"] == contact_data["phone"]
        assert data["company"] == contact_data["company"]
        assert data["notes"] == contact_data["notes"]

        # Verify contact was added to the database
        contact = Contact.query.filter_by(name="New Contact").first()
        assert contact is not None
        assert str(contact.user_id) == str(test_user.id)

    def test_get_contact(self, client, db_session, test_user, auth_headers):
        """Test getting a specific contact."""
        # Create a contact
        contact = Contact(
            user_id=test_user.id,
            name="Test Contact",
            email="test@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(contact)
        db_session.commit()

        # Get the contact
        response = client.get(f"/api/v1/contacts/{contact.id}", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["name"] == "Test Contact"
        assert data["email"] == "test@example.com"

    def test_update_contact(self, client, db_session, test_user, auth_headers):
        """Test updating a contact."""
        # Create a contact
        contact = Contact(
            user_id=test_user.id,
            name="Test Contact",
            email="test@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(contact)
        db_session.commit()

        # Update data
        update_data = {"name": "Updated Contact", "email": "updated@example.com"}

        # Update the contact
        response = client.put(f"/api/v1/contacts/{contact.id}", json=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["name"] == update_data["name"]
        assert data["email"] == update_data["email"]

        # Verify changes in the database
        contact = db_session.get(Contact, contact.id)
        assert contact.name == update_data["name"]
        assert contact.email == update_data["email"]

    def test_delete_contact(self, client, db_session, test_user, auth_headers):
        """Test deleting a contact."""
        # Create a contact
        contact = Contact(
            user_id=test_user.id,
            name="Test Contact",
            email="test@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(contact)
        db_session.commit()
        contact_id = contact.id

        # Delete the contact
        response = client.delete(f"/api/v1/contacts/{contact_id}", headers=auth_headers)

        assert response.status_code == 200

        # Verify contact was deleted
        contact = db_session.get(Contact, contact_id)
        assert contact is None

    def test_premium_required_for_contacts(self, client, db_session, test_user, auth_headers, monkeypatch):
        """Test that premium is required for contacts feature."""

        # Mock the is_premium_feature function to return True for contacts
        def mock_is_premium_feature(feature_name):
            return feature_name == "contacts"

        monkeypatch.setattr("app.api.contacts.is_premium_feature", mock_is_premium_feature)

        # Ensure test user is not premium
        test_user.subscription_plan = "free"
        test_user.subscription_status = None
        db_session.commit()

        # Try to create a contact
        contact_data = {"name": "New Contact", "email": "new@example.com"}

        response = client.post("/api/v1/contacts/", json=contact_data, headers=auth_headers)

        # Should return 402 Payment Required
        assert response.status_code == 402
        data = json.loads(response.data)
        assert "premium subscription" in data.get("message", "").lower()

    def test_create_contact_from_meeting(self, client, db_session, test_user, auth_headers, test_meeting_request):
        """Test creating a contact from a meeting request."""
        # Mock premium status for test user
        test_user.subscription_plan = "premium"
        test_user.subscription_status = "active"
        db_session.commit()

        # Create contact data
        contact_data = {
            "name": "Meeting Contact",
            "phone": "123-456-7890",
            "company": "Meeting Company",
            "notes": "From meeting",
        }

        # Create contact from meeting
        response = client.post(
            f"/api/v1/contacts/from-meeting/{test_meeting_request.request_id}", json=contact_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["name"] == contact_data["name"]
        assert data["phone"] == contact_data["phone"]
        assert data["company"] == contact_data["company"]
        assert data["notes"] == contact_data["notes"]

        # Verify contact was added to the database and associated with meeting
        contact = Contact.query.filter_by(name="Meeting Contact").first()
        assert contact is not None
        assert str(contact.user_id) == str(test_user.id)
        # Verify contact is associated with meeting request
        assert test_meeting_request.request_id in [m.request_id for m in contact.meeting_requests]
