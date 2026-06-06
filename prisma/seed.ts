// Optional dev seed: one user with an active premium subscription.
// Run with: npm run prisma:seed
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  const email = 'dev@example.com';
  const passwordHash = await bcrypt.hash('password123', 10);

  const user = await prisma.user.upsert({
    where: { email },
    update: {},
    create: {
      email,
      passwordHash,
      firstName: 'Dev',
      lastName: 'User',
      username: 'dev',
      createdAt: new Date(),
      updatedAt: new Date(),
    },
  });

  const oneYear = new Date();
  oneYear.setFullYear(oneYear.getFullYear() + 1);

  await prisma.subscription.create({
    data: {
      userId: user.id,
      planId: 'premium',
      status: 'active',
      currentPeriodStart: new Date(),
      currentPeriodEnd: oneYear,
      cancelAtPeriodEnd: false,
      createdAt: new Date(),
      updatedAt: new Date(),
    },
  });

  console.log(`Seeded user ${user.email} (${user.id}) with active premium subscription.`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
