-- Create the places table
CREATE TABLE places (
    id UUID NOT NULL,
    name VARCHAR NOT NULL,
    address VARCHAR NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    google_place_id VARCHAR,
    suggested_by_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    UNIQUE (google_place_id),
    FOREIGN KEY(suggested_by_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Create the meeting_request_suggested_places table
CREATE TABLE meeting_request_suggested_places (
    meeting_request_id UUID NOT NULL,
    place_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (meeting_request_id, place_id),
    FOREIGN KEY(meeting_request_id) REFERENCES meeting_requests (request_id) ON DELETE CASCADE,
    FOREIGN KEY(place_id) REFERENCES places (id) ON DELETE CASCADE
);

-- Add selected_place_id column to meeting_requests
ALTER TABLE meeting_requests ADD COLUMN selected_place_id UUID;
ALTER TABLE meeting_requests ADD CONSTRAINT meeting_requests_selected_place_id_fkey
    FOREIGN KEY (selected_place_id) REFERENCES places (id) ON DELETE CASCADE;

-- Update alembic_version
UPDATE alembic_version SET version_num = '9b430c7496d6';
