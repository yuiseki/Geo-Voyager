import { prisma } from ".";

// AnalyzeSkillを作成する関数
export const createAnalyzeSkill = async (
  name: string,
  description: string,
  code: string
) => {
  return await prisma.analyzeSkill.create({
    data: { name, description, code },
  });
};
