import { prisma } from ".";

// FetchSkillを作成する関数
export const createFetchSkill = async (
  name: string,
  description: string,
  code: string
) => {
  return await prisma.fetchSkill.create({
    data: { name, description, code },
  });
};
