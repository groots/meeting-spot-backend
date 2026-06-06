// Contact persistence (Prisma) + serializer matching the Python Contact.to_dict.
import { Contact, Prisma } from '@prisma/client';
import { prisma } from '../config/prisma.js';

export interface ContactInput {
  name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  notes?: string | null;
}

export function listByUser(userId: string): Promise<Contact[]> {
  return prisma.contact.findMany({ where: { userId }, orderBy: { createdAt: 'desc' } });
}

export function findByIdForUser(id: string, userId: string): Promise<Contact | null> {
  return prisma.contact.findFirst({ where: { id, userId } });
}

export function createContact(userId: string, input: ContactInput): Promise<Contact> {
  const now = new Date();
  return prisma.contact.create({
    data: {
      userId,
      name: input.name,
      email: input.email ?? null,
      phone: input.phone ?? null,
      company: input.company ?? null,
      notes: input.notes ?? null,
      createdAt: now,
      updatedAt: now,
    },
  });
}

export function updateContact(
  id: string,
  data: Prisma.ContactUpdateInput
): Promise<Contact> {
  return prisma.contact.update({ where: { id }, data });
}

export function deleteContact(id: string): Promise<Contact> {
  return prisma.contact.delete({ where: { id } });
}

/** Count meeting requests associated with a contact (via the M:N relation). */
export async function countMeetings(contactId: string): Promise<number> {
  const contact = await prisma.contact.findUnique({
    where: { id: contactId },
    include: { _count: { select: { meetingRequests: true } } },
  });
  return contact?._count.meetingRequests ?? 0;
}

export interface ContactWithMeetings {
  meetingRequests: {
    requestId: string;
    status: string;
    createdAt: Date;
    updatedAt: Date;
    selectedPlace: { name: string; address: string; googlePlaceId: string | null } | null;
  }[];
}

/** Fetch a contact's associated meetings (premium view). */
export function findMeetingsForContact(contactId: string) {
  return prisma.meetingRequest.findMany({
    where: { contacts: { some: { id: contactId } } },
    include: { selectedPlace: true },
    orderBy: { createdAt: 'desc' },
  });
}

export function toDict(contact: Contact): Record<string, unknown> {
  return {
    id: contact.id,
    user_id: contact.userId,
    name: contact.name,
    email: contact.email,
    phone: contact.phone,
    company: contact.company,
    notes: contact.notes,
    created_at: contact.createdAt.toISOString(),
    updated_at: contact.updatedAt.toISOString(),
  };
}
