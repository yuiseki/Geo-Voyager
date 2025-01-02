import { prisma } from "./index";

export enum QuestionStatus {
  OPEN = "OPEN",
  SOLVED = "SOLVED",
  UNRESOLVABLE = "UNRESOLVABLE",
}

// 疑問を作成する関数
export const createQuestion = async (description: string) => {
  return await prisma.question.create({
    data: { description, status: "OPEN" },
  });
};

// 疑問をステータスごとに取得する関数
export const getQuestionsByStatus = async (status: QuestionStatus) => {
  return await prisma.question.findMany({
    where: { status },
  });
};

// 最新の疑問を取得する関数
export const getFirstQuestionByStatus = async (status: QuestionStatus) => {
  return await prisma.question.findFirst({
    where: { status },
    orderBy: { createdAt: "desc" },
  });
};

export const getFirstOpenQuestion = async () => {
  return await getFirstQuestionByStatus(QuestionStatus.OPEN);
};

// 疑問のステータスを更新する関数
export const updateQuestionStatus = async (id: number, status: string) => {
  return await prisma.question.update({
    where: { id },
    data: { status },
  });
};
