// src/main.ts
import { prisma } from "./db";
import { compareMonacoAndSingaporePopulationDensity } from "./lib/compareMonacoAndSingaporePopulationDensity";

(async () => {
  console.log("Geo-Voyager Starting...");

  // OPENなQuestionを1件取得
  const question = await prisma.question.findFirst({
    where: { status: "OPEN" },
  });
  if (!question) {
    console.log("No OPEN questions found.");
    return;
  } else {
    console.log(`Question: ${question.description}`);
  }

  // OPENなQuestionに関連し、PENDINGなHypothesisを1件取得
  const hypothesis = await prisma.hypothesis.findFirst({
    where: {
      status: "PENDING",
      questionId: question.id,
    },
  });
  if (!hypothesis) {
    console.log("No PENDING hypotheses found for this question.");
    return;
  } else {
    console.log(`Hypothesis: ${hypothesis.description}`);
  }

  // Hypothesisに結びついているすべてのTaskを取得してログに出力
  const tasks = await prisma.task.findMany({
    where: {
      hypotheses: {
        some: {
          hypothesisId: hypothesis.id,
        },
      },
    },
  });
  if (tasks.length === 0) {
    console.log("No tasks associated with this hypothesis.");
    return;
  }

  console.log("Associated Tasks:");
  for (const task of tasks) {
    console.log(`- ${task.description} [${task.status}]`);
    if (task.status === "PENDING") {
      console.log(`  Starting task: ${task.description}`);
      // ここにタスクの処理を追加
    }
  }

  const result = await compareMonacoAndSingaporePopulationDensity();
  console.log(`Result: ${result}`);
})();
