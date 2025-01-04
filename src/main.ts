// src/main.ts
import { getFirstOpenQuestion } from "./db/question";
import {
  getAllOtherHypothesesByQuestionId,
  getAllRejectedHypothesesByQuestionId,
  getFirstPendingHypothesisByQuestionId,
} from "./db/hypothesis";
import { findAndExecuteTasksByHypothesis } from "./utils/findAndExecuteTasksByHypothesis";
import { formulateNewHypothesis } from "./utils/formulateNewHypothesis";
import { listUpAllSolvedQuestions } from "./utils/listUpAllSolvedQuestions";
import { getAllExecutedTasksByHypothesisId, TaskStatus } from "./db/task";
import getWardWithMostSchools from "./lib/skills/numberOfSchools/Japan/Tokyo/getWardWithMostSchools";

(async () => {
  console.log("🗺️  Initializing Geo-Voyager...");

  const result = await getWardWithMostSchools();

  console.log(`🏫 Ward with the most schools in Tokyo: ${result}`);

  return;

  await listUpAllSolvedQuestions();

  // OPENなQuestionを1件取得
  const question = await getFirstOpenQuestion();
  if (!question) {
    console.log("⚠️  No OPEN questions found.");
    return;
  } else {
    console.log(`❓️ Question: ${question.description}`);
  }

  const rejectedHypotheses = await getAllRejectedHypothesesByQuestionId(
    question.id
  );
  if (rejectedHypotheses.length > 0) {
    const rejectedHypothesesWithTasks = await Promise.all(
      rejectedHypotheses.map(async (hypothesis) => {
        const tasks = await getAllExecutedTasksByHypothesisId(hypothesis.id);
        return {
          description: hypothesis.description,
          tasks: tasks.map((task) => {
            if (task.status === TaskStatus.COMPLETED) {
              return `    - ✅ Task: ${task.description} [${task.status}]`;
            } else if (task.status === TaskStatus.FAILED) {
              return `    - ❌ Task: ${task.description} [${task.status}]`;
            }
          }),
        };
      })
    );
    console.log("🚫 Rejected hypotheses:");
    for (const rejectedHypothesis of rejectedHypothesesWithTasks) {
      console.log(`  - 🚫 ${rejectedHypothesis.description} [REJECTED]`);
      for (const task of rejectedHypothesis.tasks) {
        console.log(task);
      }
    }
  }

  // OPENなQuestionに関連し、PENDINGなHypothesisを1件取得
  let hypothesis = await getFirstPendingHypothesisByQuestionId(question.id);
  if (hypothesis) {
    console.log(`💡 Hypothesis: ${hypothesis.description}`);
  } else {
    console.log("⚠️  No PENDING hypotheses found for this question.");
    hypothesis = await formulateNewHypothesis(question);
    if (!hypothesis) {
      console.log("⚠️  Failed to formulate a new hypothesis.");
      return;
    }
  }

  // Hypothesisに関連するTaskを探して実行
  await findAndExecuteTasksByHypothesis(hypothesis);

  console.log("🗺️  Geo-Voyager has finished his journey.");
})();
