-- Phase 1 availability: store Google Calendar OAuth refresh tokens (encrypted)
-- so we can compute free/busy open slots. Busy event details are never stored.
CREATE TABLE "calendar_connections" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "provider" VARCHAR(32) NOT NULL,
    "account_email" VARCHAR(255) NOT NULL,
    "refresh_token_encrypted" TEXT NOT NULL,
    "scopes" VARCHAR(512) NOT NULL,
    "timezone" VARCHAR(64),
    "revoked_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "calendar_connections_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "calendar_connections_user_id_provider_key" ON "calendar_connections"("user_id", "provider");

CREATE INDEX "calendar_connections_user_id_idx" ON "calendar_connections"("user_id");

ALTER TABLE "calendar_connections" ADD CONSTRAINT "calendar_connections_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
