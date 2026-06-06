-- CreateEnum
CREATE TYPE "meeting_request_status" AS ENUM ('pending_b_address', 'calculating', 'completed', 'expired', 'failed');

-- CreateEnum
CREATE TYPE "contact_type" AS ENUM ('email', 'phone', 'sms');

-- CreateTable
CREATE TABLE "users" (
    "id" UUID NOT NULL,
    "email" VARCHAR(120) NOT NULL,
    "password_hash" VARCHAR(256),
    "google_oauth_id" VARCHAR(255),
    "facebook_oauth_id" VARCHAR(255),
    "username" VARCHAR(50),
    "first_name" VARCHAR(50),
    "last_name" VARCHAR(50),
    "phone" VARCHAR(50),
    "profile_picture_url" VARCHAR(255),
    "stripe_customer_id" VARCHAR(255),
    "created_at" TIMESTAMPTZ(6) NOT NULL,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "meeting_requests" (
    "request_id" UUID NOT NULL,
    "user_a_id" UUID,
    "user_b_contact_type" "contact_type" NOT NULL,
    "user_b_contact_encrypted" VARCHAR(255) NOT NULL,
    "location_type" VARCHAR(50) NOT NULL,
    "location_a" JSONB,
    "location_b" JSONB,
    "address_a_lat" DOUBLE PRECISION NOT NULL,
    "address_a_lon" DOUBLE PRECISION NOT NULL,
    "address_b_lat" DOUBLE PRECISION,
    "address_b_lon" DOUBLE PRECISION,
    "status" "meeting_request_status" NOT NULL DEFAULT 'pending_b_address',
    "token_b" VARCHAR(64) NOT NULL,
    "selected_place_google_id" VARCHAR(255),
    "selected_place_details" JSONB,
    "suggested_options" JSONB,
    "session_identifier_a" VARCHAR(255),
    "selected_place_id" UUID,
    "created_at" TIMESTAMPTZ(6) NOT NULL,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,
    "expires_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "meeting_requests_pkey" PRIMARY KEY ("request_id")
);

-- CreateTable
CREATE TABLE "places" (
    "id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "address" TEXT NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    "google_place_id" TEXT,
    "suggested_by_id" UUID NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "places_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "contacts" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255),
    "phone" VARCHAR(50),
    "company" VARCHAR(255),
    "notes" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "contacts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "subscriptions" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "stripe_subscription_id" VARCHAR(255),
    "stripe_customer_id" VARCHAR(255),
    "plan_id" VARCHAR(50) NOT NULL,
    "status" VARCHAR(50) NOT NULL,
    "current_period_start" TIMESTAMPTZ(6),
    "current_period_end" TIMESTAMPTZ(6),
    "cancel_at_period_end" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMPTZ(6) NOT NULL,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "subscriptions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "password_resets" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "token" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expires_at" TIMESTAMPTZ(6) NOT NULL,
    "used" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "password_resets_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "_SuggestedPlaces" (
    "A" UUID NOT NULL,
    "B" UUID NOT NULL
);

-- CreateTable
CREATE TABLE "_MeetingContacts" (
    "A" UUID NOT NULL,
    "B" UUID NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "users_google_oauth_id_key" ON "users"("google_oauth_id");

-- CreateIndex
CREATE INDEX "users_email_idx" ON "users"("email");

-- CreateIndex
CREATE INDEX "users_google_oauth_id_idx" ON "users"("google_oauth_id");

-- CreateIndex
CREATE UNIQUE INDEX "meeting_requests_token_b_key" ON "meeting_requests"("token_b");

-- CreateIndex
CREATE INDEX "meeting_requests_status_idx" ON "meeting_requests"("status");

-- CreateIndex
CREATE INDEX "meeting_requests_user_a_id_idx" ON "meeting_requests"("user_a_id");

-- CreateIndex
CREATE INDEX "meeting_requests_token_b_idx" ON "meeting_requests"("token_b");

-- CreateIndex
CREATE INDEX "meeting_requests_session_identifier_a_idx" ON "meeting_requests"("session_identifier_a");

-- CreateIndex
CREATE UNIQUE INDEX "places_google_place_id_key" ON "places"("google_place_id");

-- CreateIndex
CREATE INDEX "contacts_user_id_idx" ON "contacts"("user_id");

-- CreateIndex
CREATE INDEX "contacts_email_idx" ON "contacts"("email");

-- CreateIndex
CREATE UNIQUE INDEX "subscriptions_stripe_subscription_id_key" ON "subscriptions"("stripe_subscription_id");

-- CreateIndex
CREATE INDEX "subscriptions_user_id_idx" ON "subscriptions"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "password_resets_token_key" ON "password_resets"("token");

-- CreateIndex
CREATE INDEX "password_resets_user_id_idx" ON "password_resets"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "_SuggestedPlaces_AB_unique" ON "_SuggestedPlaces"("A", "B");

-- CreateIndex
CREATE INDEX "_SuggestedPlaces_B_index" ON "_SuggestedPlaces"("B");

-- CreateIndex
CREATE UNIQUE INDEX "_MeetingContacts_AB_unique" ON "_MeetingContacts"("A", "B");

-- CreateIndex
CREATE INDEX "_MeetingContacts_B_index" ON "_MeetingContacts"("B");

-- AddForeignKey
ALTER TABLE "meeting_requests" ADD CONSTRAINT "meeting_requests_user_a_id_fkey" FOREIGN KEY ("user_a_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "meeting_requests" ADD CONSTRAINT "meeting_requests_selected_place_id_fkey" FOREIGN KEY ("selected_place_id") REFERENCES "places"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "places" ADD CONSTRAINT "places_suggested_by_id_fkey" FOREIGN KEY ("suggested_by_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "contacts" ADD CONSTRAINT "contacts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subscriptions" ADD CONSTRAINT "subscriptions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "password_resets" ADD CONSTRAINT "password_resets_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_SuggestedPlaces" ADD CONSTRAINT "_SuggestedPlaces_A_fkey" FOREIGN KEY ("A") REFERENCES "meeting_requests"("request_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_SuggestedPlaces" ADD CONSTRAINT "_SuggestedPlaces_B_fkey" FOREIGN KEY ("B") REFERENCES "places"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_MeetingContacts" ADD CONSTRAINT "_MeetingContacts_A_fkey" FOREIGN KEY ("A") REFERENCES "contacts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_MeetingContacts" ADD CONSTRAINT "_MeetingContacts_B_fkey" FOREIGN KEY ("B") REFERENCES "meeting_requests"("request_id") ON DELETE CASCADE ON UPDATE CASCADE;
