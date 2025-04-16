"""API endpoints for managing contacts."""

import uuid
from datetime import datetime, timezone

from flask import current_app, request
from flask_restx import Namespace, Resource, abort, fields

from app import db
from app.decorators import token_required
from app.models import Contact, MeetingRequest
from app.utils.stripe_helpers import is_premium_feature

api = Namespace("contacts", description="Contact management operations")

# Model definitions for swagger documentation
contact_model = api.model(
    "Contact",
    {
        "id": fields.String(description="Contact identifier"),
        "name": fields.String(required=True, description="Contact name"),
        "email": fields.String(description="Contact email address"),
        "phone": fields.String(description="Contact phone number"),
        "company": fields.String(description="Contact company or organization"),
        "notes": fields.String(description="Additional notes about the contact"),
        "created_at": fields.DateTime(description="Creation timestamp"),
        "updated_at": fields.DateTime(description="Last update timestamp"),
    },
)

contact_create_model = api.model(
    "ContactCreate",
    {
        "name": fields.String(required=True, description="Contact name"),
        "email": fields.String(description="Contact email address"),
        "phone": fields.String(description="Contact phone number"),
        "company": fields.String(description="Contact company or organization"),
        "notes": fields.String(description="Additional notes about the contact"),
    },
)

contact_update_model = api.model(
    "ContactUpdate",
    {
        "name": fields.String(description="Contact name"),
        "email": fields.String(description="Contact email address"),
        "phone": fields.String(description="Contact phone number"),
        "company": fields.String(description="Contact company or organization"),
        "notes": fields.String(description="Additional notes about the contact"),
    },
)

meeting_summary_model = api.model(
    "MeetingSummary",
    {
        "id": fields.String(description="Meeting request identifier"),
        "status": fields.String(description="Meeting request status"),
        "created_at": fields.DateTime(description="Creation timestamp"),
        "updated_at": fields.DateTime(description="Last update timestamp"),
        "selected_place": fields.Raw(description="Selected meeting place details"),
    },
)

contact_with_meetings_model = api.model(
    "ContactWithMeetings",
    {
        "id": fields.String(description="Contact identifier"),
        "name": fields.String(description="Contact name"),
        "email": fields.String(description="Contact email address"),
        "phone": fields.String(description="Contact phone number"),
        "company": fields.String(description="Contact company or organization"),
        "notes": fields.String(description="Additional notes about the contact"),
        "created_at": fields.DateTime(description="Creation timestamp"),
        "updated_at": fields.DateTime(description="Last update timestamp"),
        "meetings": fields.List(fields.Nested(meeting_summary_model), description="Meeting history with this contact"),
    },
)


@api.route("/")
class ContactList(Resource):
    @api.doc("list_contacts")
    @api.marshal_list_with(contact_model)
    @token_required
    def get(self, current_user):
        """List all contacts for the current user."""
        # Check if contacts management is a premium feature
        if is_premium_feature("contacts") and not current_user.is_premium():
            abort(
                402,
                "This feature requires a premium subscription. Please upgrade your plan to use contacts management.",
            )

        return [contact.to_dict() for contact in current_user.contacts]

    @api.doc("create_contact")
    @api.expect(contact_create_model)
    @api.marshal_with(contact_model, code=201)
    @token_required
    def post(self, current_user):
        """Create a new contact."""
        # Check if contacts management is a premium feature
        if is_premium_feature("contacts") and not current_user.is_premium():
            abort(
                402,
                "This feature requires a premium subscription. Please upgrade your plan to use contacts management.",
            )

        data = request.json
        contact = Contact(
            user_id=current_user.id,
            name=data["name"],
            email=data.get("email"),
            phone=data.get("phone"),
            company=data.get("company"),
            notes=data.get("notes"),
        )

        db.session.add(contact)
        db.session.commit()

        return contact.to_dict(), 201


@api.route("/<string:id>")
@api.param("id", "The contact identifier")
class ContactResource(Resource):
    @api.doc("get_contact")
    @api.marshal_with(contact_with_meetings_model)
    @token_required
    def get(self, id, current_user):
        """Get a specific contact with meeting history."""
        try:
            uuid_obj = uuid.UUID(id)
        except ValueError:
            abort(400, "Invalid contact ID format")

        contact = Contact.query.filter_by(id=uuid_obj, user_id=current_user.id).first_or_404(
            description=f"Contact {id} not found"
        )

        result = contact.to_dict()

        # Include meeting history if user has premium subscription
        if current_user.is_premium():
            meetings = []
            for meeting in contact.meeting_requests:
                meeting_dict = {
                    "id": str(meeting.id),
                    "status": meeting.status.name if hasattr(meeting, "status") else "UNKNOWN",
                    "created_at": meeting.created_at.isoformat(),
                    "updated_at": meeting.updated_at.isoformat(),
                }

                # Add selected place details if available
                if meeting.selected_place:
                    meeting_dict["selected_place"] = {
                        "name": meeting.selected_place.name,
                        "address": meeting.selected_place.address,
                        "google_place_id": meeting.selected_place.google_place_id,
                    }

                meetings.append(meeting_dict)

            result["meetings"] = meetings
        else:
            # For non-premium users, only include meeting count
            result["meeting_count"] = len(contact.meeting_requests)
            result["premium_required"] = True

        return result

    @api.doc("update_contact")
    @api.expect(contact_update_model)
    @api.marshal_with(contact_model)
    @token_required
    def put(self, id, current_user):
        """Update a specific contact."""
        # Check if contacts management is a premium feature
        if is_premium_feature("contacts") and not current_user.is_premium():
            abort(
                402,
                "This feature requires a premium subscription. Please upgrade your plan to use contacts management.",
            )

        try:
            uuid_obj = uuid.UUID(id)
        except ValueError:
            abort(400, "Invalid contact ID format")

        contact = Contact.query.filter_by(id=uuid_obj, user_id=current_user.id).first_or_404(
            description=f"Contact {id} not found"
        )

        data = request.json
        if "name" in data:
            contact.name = data["name"]
        if "email" in data:
            contact.email = data["email"]
        if "phone" in data:
            contact.phone = data["phone"]
        if "company" in data:
            contact.company = data["company"]
        if "notes" in data:
            contact.notes = data["notes"]

        contact.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return contact.to_dict()

    @api.doc("delete_contact")
    @token_required
    def delete(self, id, current_user):
        """Delete a specific contact."""
        # Check if contacts management is a premium feature
        if is_premium_feature("contacts") and not current_user.is_premium():
            abort(
                402,
                "This feature requires a premium subscription. Please upgrade your plan to use contacts management.",
            )

        try:
            uuid_obj = uuid.UUID(id)
        except ValueError:
            abort(400, "Invalid contact ID format")

        contact = Contact.query.filter_by(id=uuid_obj, user_id=current_user.id).first_or_404(
            description=f"Contact {id} not found"
        )

        db.session.delete(contact)
        db.session.commit()

        return {"message": f"Contact {id} deleted successfully"}, 200


@api.route("/from-meeting/<string:meeting_id>")
@api.param("meeting_id", "The meeting request identifier")
class CreateContactFromMeeting(Resource):
    @api.doc("create_contact_from_meeting")
    @api.expect(contact_create_model)
    @api.marshal_with(contact_model, code=201)
    @token_required
    def post(self, meeting_id, current_user):
        """Create a contact from a meeting participant."""
        print(f"Processing request for meeting ID: {meeting_id}")
        print(f"Current user ID: {current_user.id}")

        # Check if contacts management is a premium feature
        if is_premium_feature("contacts") and not current_user.is_premium():
            print("User doesn't have premium subscription")
            abort(
                402,
                "This feature requires a premium subscription. Please upgrade your plan to use contacts management.",
            )

        try:
            meeting_uuid = uuid.UUID(meeting_id)
            print(f"Parsed meeting UUID: {meeting_uuid}")
        except ValueError as e:
            print(f"Invalid meeting ID format: {e}")
            abort(400, "Invalid meeting ID format")

        # Find the meeting request
        meeting = MeetingRequest.query.filter_by(request_id=meeting_uuid).first_or_404(
            description=f"Meeting request {meeting_id} not found"
        )
        print(f"Found meeting: {meeting}")
        print(f"Meeting user_a_id: {meeting.user_a_id}")
        print(f"Meeting user_b_email: {meeting.user_b_email}")

        # Check if the user is authorized to access this meeting
        if meeting.user_a_id != current_user.id:
            print(f"Authorization failed: {meeting.user_a_id} != {current_user.id}")
            abort(403, "You are not authorized to access this meeting request")

        data = request.json
        print(f"Contact data: {data}")

        # Create the contact
        contact = Contact(
            user_id=current_user.id,
            name=data.get("name", ""),
            email=meeting.user_b_email,  # Use email from meeting request
            phone=data.get("phone"),
            company=data.get("company"),
            notes=data.get("notes"),
        )

        # Add the contact to the database
        db.session.add(contact)

        # Associate the contact with the meeting request
        meeting.contacts.append(contact)

        db.session.commit()

        return contact.to_dict(), 201


@api.route("/", doc=False)
class ContactsOptions(Resource):
    def options(self):
        """Handle OPTIONS requests for the contacts endpoint."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response


@api.route("/<string:id>", doc=False)
class ContactIdOptions(Resource):
    def options(self, id):
        """Handle OPTIONS requests for individual contact endpoints."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response


@api.route("/from-meeting/<string:meeting_id>", doc=False)
class MeetingContactOptions(Resource):
    def options(self, meeting_id):
        """Handle OPTIONS requests for creating contacts from meeting endpoint."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response
