import { prisma } from ".";

export enum TaskStatus {
  PENDING = "PENDING",
  IN_PROGRESS = "IN_PROGRESS",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
  ERROR = "ERROR",
}

export const deleteTaskById = async (taskId: number) => {
  return await prisma.task.delete({
    where: { id: taskId },
  });
};

export const getAllTasksByQuestionId = async (questionId: number) => {
  return await prisma.task.findMany({
    where: {
      questionId,
    },
  });
};

export const getAllExecutedTasks = async () => {
  return await prisma.task.findMany({
    where: {
      status: {
        in: [TaskStatus.COMPLETED, TaskStatus.FAILED],
      },
    },
  });
};

export const getAllExecutedTasksByQuestionId = async (questionId: number) => {
  return await prisma.task.findMany({
    where: {
      questionId,
      status: {
        in: [TaskStatus.COMPLETED, TaskStatus.FAILED],
      },
    },
  });
};

export const updateTaskStatusAndResult = async (
  taskId: number,
  status: TaskStatus,
  result: string
) => {
  return await prisma.task.update({
    where: { id: taskId },
    data: { status, result },
  });
};

export const createTaskByQuestionId = async (
  questionId: number,
  description: string
) => {
  const task = await prisma.task.create({
    data: {
      description,
      status: TaskStatus.PENDING,
      questionId,
    },
  });
  return task;
};
