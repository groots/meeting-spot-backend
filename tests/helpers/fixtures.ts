// Plain object factories that mirror the shapes Prisma returns (camelCase
// fields). Enum-typed fields use the member-name strings the generated client
// produces at runtime (e.g. ContactType.EMAIL === 'EMAIL').
import type { User, MeetingRequest, Contact, Subscription } from '@prisma/client';

const NOW = new Date('2024-01-01T00:00:00.000Z');

export function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-a-id',
    email: 'a@example.com',
    passwordHash: '$2a$10$hashplaceholderhashplaceholderhashplaceholderha',
    googleOauthId: null,
    facebookOauthId: null,
    username: 'a',
    firstName: null,
    lastName: null,
    phone: null,
    profilePictureUrl: null,
    stripeCustomerId: null,
    emailVerified: false,
    createdAt: NOW,
    updatedAt: NOW,
    ...overrides,
  };
}

export function makeMeetingRequest(
  overrides: Partial<MeetingRequest> = {}
): MeetingRequest {
  return {
    requestId: 'req-1',
    userAId: 'user-a-id',
    userBContactType: 'EMAIL' as MeetingRequest['userBContactType'],
    userBContactEncrypted: 'encrypted-placeholder',
    locationType: 'Food & Drink',
    locationA: { address: '1 A St', latitude: 37.7749, longitude: -122.4194 },
    locationB: null,
    addressALat: 37.7749,
    addressALon: -122.4194,
    addressBLat: null,
    addressBLon: null,
    status: 'PENDING_B_ADDRESS' as MeetingRequest['status'],
    selectionMode: 'OWNER' as MeetingRequest['selectionMode'],
    userAChoice: null,
    userBChoice: null,
    meetingTime: null,
    userATimeChoice: null,
    userBTimeChoice: null,
    meetingDurationMin: null,
    tokenB: 'valid-token-b',
    tokenBUsedAt: null,
    selectedPlaceGoogleId: null,
    selectedPlaceDetails: null,
    suggestedOptions: null,
    sessionIdentifierA: 'session-a-secret',
    selectedPlaceId: null,
    createdAt: NOW,
    updatedAt: NOW,
    expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
    ...overrides,
  } as MeetingRequest;
}

export function makeContact(overrides: Partial<Contact> = {}): Contact {
  return {
    id: 'contact-1',
    userId: 'user-a-id',
    name: 'Bob',
    email: 'bob@example.com',
    phone: null,
    company: null,
    notes: null,
    createdAt: NOW,
    updatedAt: NOW,
    ...overrides,
  };
}

export function makeSubscription(
  overrides: Partial<Subscription> = {}
): Subscription {
  return {
    id: 'sub-1',
    userId: 'user-a-id',
    stripeSubscriptionId: null,
    stripeCustomerId: null,
    planId: 'premium',
    status: 'active',
    currentPeriodStart: new Date(Date.now() - 1000),
    currentPeriodEnd: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
    cancelAtPeriodEnd: false,
    createdAt: NOW,
    updatedAt: NOW,
    ...overrides,
  };
}
