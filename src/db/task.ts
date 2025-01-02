import { prisma } from ".";

export const getAllTasksByHypothesisId = async (hypothesisId: number) => {
  return await prisma.task.findMany({
    where: {
      hypotheses: {
        some: {
          hypothesisId,
        },
      },
    },
  });
};
