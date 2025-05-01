# Add tests for resend-invitation endpoint


def test_resend_invitation_success(client, auth, test_users, sample_meeting_request_pending):
    """Test successful resend of invitation email."""
    # Get authenticated user token
    token = auth.login(test_users[0]["email"], test_users[0]["password"])

    # Make resend request
    response = client.post(
        f"/api/v1/meeting-requests/{sample_meeting_request_pending.request_id}/resend-invitation",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Check response
    assert response.status_code == 200
    assert response.json["message"] == "Invitation resent successfully"


def test_resend_invitation_unauthorized(client, auth, test_users, sample_meeting_request_pending):
    """Test resend invitation with wrong user (unauthorized)."""
    # Login with different user
    token = auth.login(test_users[1]["email"], test_users[1]["password"])

    # Make resend request with wrong user
    response = client.post(
        f"/api/v1/meeting-requests/{sample_meeting_request_pending.request_id}/resend-invitation",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Check response
    assert response.status_code == 403
    assert "Unauthorized" in response.json["error"]


def test_resend_invitation_cooldown(client, auth, test_users, sample_meeting_request_pending, monkeypatch):
    """Test resend invitation with cooldown active."""
    from datetime import datetime, timedelta, timezone

    # Get authenticated user token
    token = auth.login(test_users[0]["email"], test_users[0]["password"])

    # First request should succeed
    response = client.post(
        f"/api/v1/meeting-requests/{sample_meeting_request_pending.request_id}/resend-invitation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    # Second request should be rate limited
    response = client.post(
        f"/api/v1/meeting-requests/{sample_meeting_request_pending.request_id}/resend-invitation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 429
    assert "cooldown_remaining_minutes" in response.json


def test_resend_invitation_wrong_status(client, auth, test_users, sample_meeting_request_calculating):
    """Test resend invitation when status is not pending_b_address."""
    # Get authenticated user token
    token = auth.login(test_users[0]["email"], test_users[0]["password"])

    # Make resend request
    response = client.post(
        f"/api/v1/meeting-requests/{sample_meeting_request_calculating.request_id}/resend-invitation",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Check response
    assert response.status_code == 400
    assert "Cannot resend invitation for requests that are not pending" in response.json["error"]
