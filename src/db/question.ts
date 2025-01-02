// src/db/question.ts
import { prisma } from "./index";
import { distance } from "fastest-levenshtein";

// 疑問を作成する関数
export const createQuestion = async (description: string) => {
  return await prisma.question.create({
    data: { description, status: "OPEN" },
  });
};

// 疑問をステータスごとに取得する関数
export const getQuestionsByStatus = async (status: string) => {
  return await prisma.question.findMany({
    where: { status },
  });
};

// 最新の疑問を取得する関数
export const getLatestQuestionByStatus = async (status: string) => {
  return await prisma.question.findFirst({
    where: { status },
    orderBy: { createdAt: "desc" },
  });
};

// 疑問のステータスを更新する関数
export const updateQuestionStatus = async (id: number, status: string) => {
  return await prisma.question.update({
    where: { id },
    data: { status },
  });
};
