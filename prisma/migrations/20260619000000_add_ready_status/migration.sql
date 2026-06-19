-- Add a `ready` status to the meeting_request_status enum. `ready` means the
-- venue suggestions have been generated and are awaiting the owner to agree on a
-- place; `completed` now strictly means a place was selected/agreed.
ALTER TYPE "meeting_request_status" ADD VALUE IF NOT EXISTS 'ready' BEFORE 'completed';
