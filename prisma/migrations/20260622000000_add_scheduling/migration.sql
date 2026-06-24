-- Scheduling: add the finalized meeting time + per-party time choices + duration.
--
-- Mirrors the selection_mode/choice trio for *when* the meeting happens. The
-- existing selection_mode governs both place and time:
--   OWNER  → meeting_time set immediately when the owner proposes.
--   MUTUAL → user_a_time_choice / user_b_time_choice store each party's proposal;
--            meeting_time is set once they agree (matching ISO-minute key).
-- All columns are nullable and additive (no backfill, no new status value). The
-- finalized-time signal is simply `meeting_time IS NOT NULL`; time selection
-- happens while status='completed' (the place is already locked).
-- meeting_duration_min is optional (code defaults to 60 for the ICS end time).

-- AlterTable
ALTER TABLE "meeting_requests"
  ADD COLUMN "meeting_time" TIMESTAMPTZ(6),
  ADD COLUMN "user_a_time_choice" TIMESTAMPTZ(6),
  ADD COLUMN "user_b_time_choice" TIMESTAMPTZ(6),
  ADD COLUMN "meeting_duration_min" INTEGER;
