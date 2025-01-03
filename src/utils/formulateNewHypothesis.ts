import { Question } from "@prisma/client";
import { prisma } from "../db";
import {
  getAllRejectedHypothesesByQuestionId,
  getAllHypothesesByStatus,
  HypothesisStatus,
  getAllOtherHypothesesByQuestionId,
} from "../db/hypothesis";
import { ChatOllama } from "@langchain/ollama";
import { getAllExecutedTasksByHypothesisId } from "../db/task";

/**
 * 新しい仮説を生成してデータベースに保存
 * @param question 関連するQuestion
 * @returns 生成された新しいHypothesis
 */
export const formulateNewHypothesis = async (question: Question) => {
  console.log("🧠 Formulating a new hypothesis...");
  const model = new ChatOllama({
    model: "qwen2.5:7b",
    temperature: 0,
  });

  // 新しい仮説を生成するロジック（仮説の立案プロンプト）
  const exampleHypotheses = await getAllOtherHypothesesByQuestionId(
    question.id
  );
  /**
Examples of testable hypotheses for other questions:
${exampleHypotheses.map((h) => `- ${h.description}`).join("\n")}

   * 
   */
  const rejectedHypotheses = await getAllRejectedHypothesesByQuestionId(
    question.id
  );
  // RejectedHypothesesに結びつくタスクを取得
  const rejectedHypothesesWithTasks = await Promise.all(
    rejectedHypotheses.map(async (hypothesis) => {
      const tasks = await getAllExecutedTasksByHypothesisId(hypothesis.id);
      return {
        description: hypothesis.description,
        tasks: tasks.map(
          (task) => `  - Task: ${task.description} [${task.status}]`
        ),
      };
    })
  );
  // 仮説生成プロンプト
  const prompt = `Given the question: "${
    question.description
  }", formulate a new testable hypothesis in Japanese.

Already rejected hypotheses for this question and their associated tasks:
${rejectedHypothesesWithTasks
  .map(
    (hypothesisWithTasks) =>
      `- Hypothesis: ${
        hypothesisWithTasks.description
      }\n${hypothesisWithTasks.tasks.join("\n")}`
  )
  .join("\n")}

Reply only with the hypothesis description.`;

  // console.log("🤖 Hypothesis generation prompt:");
  // console.log(prompt);

  // AIのレスポンスとして新しい仮説を生成
  const res = await model.invoke(prompt);

  const hypothesisDescription = res.content as string;

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
