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
};

export const createTaskByHypothesisId = async (
  hypothesisId: number,
  description: string
) => {
  const task = await prisma.task.create({
    data: {
      description,
      status: TaskStatus.PENDING,
      hypotheses: {
        create: {
          hypothesisId,
        },
      },
    },
  });
  return task;
};
