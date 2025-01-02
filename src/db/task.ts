import { prisma } from ".";

export enum TaskStatus {
  PENDING = "PENDING",
  IN_PROGRESS = "IN_PROGRESS",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
  ERROR = "ERROR",
}

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

export const updateTaskStatusAndResult = async (
  id: number,
  status: TaskStatus,
  result: string
) => {
  return await prisma.task.update({
    where: { id },
    data: { status, result },
  });
}