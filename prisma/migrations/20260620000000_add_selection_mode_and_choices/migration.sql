-- Collaborative selection: add a selection mode + per-party venue choices.
--
-- selection_mode defaults to 'owner' so existing rows keep today's owner-only
-- finalize flow. user_a_choice / user_b_choice store the venue each party has
-- currently picked in 'mutual' mode (JSONB, nullable, no backfill). The
-- finalized signal remains selected_place_details + status='completed'.

-- CreateEnum
CREATE TYPE "selection_mode" AS ENUM ('owner', 'mutual');

-- AlterTable
ALTER TABLE "meeting_requests"
  ADD COLUMN "selection_mode" "selection_mode" NOT NULL DEFAULT 'owner',
  ADD COLUMN "user_a_choice" JSONB,
  ADD COLUMN "user_b_choice" JSONB;
