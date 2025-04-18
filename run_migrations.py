# Run migrations in order
migrations_to_run = [
    "create_users_table",
    "create_meeting_requests_table",
    "create_places_table",
    "add_selected_place_column",
    "create_password_resets_table",
    "create_subscriptions_table",
    "create_contacts_table",
    "create_meeting_contacts_table",
    "add_facebook_oauth",  # Add the new migration
]
