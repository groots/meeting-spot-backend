-- AlterTable: add single-use marker for User B's invite token. Nullable with no
-- backfill — existing rows keep NULL, which means "not yet used", so already
-- responded-to requests remain readable. The /respond claim flips NULL → now()
-- atomically to prevent double-submit.
ALTER TABLE "meeting_requests" ADD COLUMN "token_b_used_at" TIMESTAMPTZ(6);
