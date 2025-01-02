import { prisma } from ".";

// Skillを作成する関数
export const createSkill = async (description: string, code: string) => {
  return await prisma.skill.create({
    data: { description, code },
  });
};
