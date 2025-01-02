import { Question } from "@prisma/client";
import { prisma } from "../db";
import {
  getAllRejectedHypothesesByQuestionId,
  HypothesisStatus,
} from "../db/hypothesis";
import { ChatOllama } from "@langchain/ollama";

/**
 * 新しい仮説を生成してデータベースに保存
 * @param question 関連するQuestion
 * @returns 生成された新しいHypothesis
 */
export const formulateNewHypothesis = async (question: Question) => {
  console.log("🧠 Formulating a new hypothesis...");

  // 新しい仮説を生成するロジック（仮説の立案プロンプト）
  const hypothesisDescription = await formulateNewHypothesisFromQuestion(
    question
  );

  if (!hypothesisDescription) {
    console.error("⚠️  Failed to formulate a new hypothesis.");
    return null;
  }

  // 新しい仮説をデータベースに保存
  const newHypothesis = await prisma.hypothesis.create({
    data: {
      description: hypothesisDescription,
      status: HypothesisStatus.PENDING,
      questionId: question.id,
    },
  });

  console.log(`💡 New Hypothesis: ${newHypothesis.description}`);
  return newHypothesis;
};

/**
 * 質問の説明を元に新しい仮説を生成
 * @param question Question
 * @returns 生成された新しい仮説
 */
const formulateNewHypothesisFromQuestion = async (
  question: Question
): Promise<string> => {
  const rejectedHypotheses = await getAllRejectedHypothesesByQuestionId(
    question.id
  );

  // 仮説生成プロンプト
  const prompt = `Given the question: "${
    question.description
  }", formulate a new testable hypothesis in Japanese.

Already Rejected hypotheses:
${rejectedHypotheses.map((h) => `- ${h.description}`).join("\n")}

Reply only with the hypothesis description.`;

  // console.log("🤖 Hypothesis generation prompt:");
  // console.log(prompt);

  // AIのレスポンスとして新しい仮説を生成
  const model = new ChatOllama({
    model: "qwen2.5:7b",
    temperature: 0,
  });
  const hypothesisDescription = await model.invoke(prompt);

  return hypothesisDescription.content as string;
};
