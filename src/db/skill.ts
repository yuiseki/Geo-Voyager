import { prisma } from ".";

// Skillを作成する関数
export const createSkill = async (description: string, code: string) => {
  return await prisma.skill.create({
    data: { description, code },
  });
};

export const getFirstSkillByDescription = async (description: string) => {
  return await prisma.skill.findFirst({
    where: { description },
  });
};

export const saveSkillToDatabase = async (
  description: string,
  code: string
) => {
  const skill = await prisma.skill.create({
    data: {
      description,
      code,
    },
  });
  return skill;
};
