#!/usr/bin/env python3
import os
os.environ["ENCRYPTION_KEY"] = "wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA"
from app import create_app
from app.models.meeting_request import MeetingRequest
app = create_app("development")
with app.app_context():
    print("Testing MeetingRequest query...")
    meeting_requests = MeetingRequest.query.all()
    print(f"Found {len(meeting_requests)} meeting requests")
    for mr in meeting_requests:
        print(f"ID: {mr.request_id}, Contact: {mr.user_b_contact}")
    print("All tests passed successfully!")
