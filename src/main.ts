// src/main.ts
import { getAllQuestionsByStatus, QuestionStatus } from "./db/question";
import {
  getAllRejectedHypothesesByQuestionId,
  getFirstPendingHypothesisByQuestionId,
} from "./db/hypothesis";
import { findAndExecuteTasksByHypothesis } from "./utils/findAndExecuteTasksByHypothesis";
import { formulateNewHypothesis } from "./utils/formulateNewHypothesis";
import { listUpAllSolvedQuestions } from "./utils/listUpAllSolvedQuestions";
import { getAllExecutedTasksByHypothesisId, TaskStatus } from "./db/task";

(async () => {
  console.log("🗺️  Initializing Geo-Voyager...");

  await listUpAllSolvedQuestions();

  // すべてのOPENなQuestionを取得
  const openQuestions = await getAllQuestionsByStatus(QuestionStatus.OPEN);
  if (openQuestions.length === 0) {
    console.log("⚠️  No OPEN questions found.");
    console.log("🗺️  Geo-Voyager has finished his journey.");
    return;
  }

  for (const question of openQuestions) {
    console.log(`\n❓️ Question: ${question.description}`);

    // 棄却された仮説を表示
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

    // PENDINGな仮説を処理
    let hypothesis = await getFirstPendingHypothesisByQuestionId(question.id);
    while (true) {
      if (!hypothesis) {
        console.log("⚠️  No PENDING hypotheses found for this question.");
        hypothesis = await formulateNewHypothesis(question);
        if (!hypothesis) {
          console.log("⚠️  Failed to formulate a new hypothesis.");
          break; // 次の質問へ
        }
      }

      console.log(`💡 Hypothesis: ${hypothesis.description}`);
      
      // 仮説に関連するTaskを探して実行
      await findAndExecuteTasksByHypothesis(hypothesis);

      // 次のPENDING仮説を確認
      const nextHypothesis = await getFirstPendingHypothesisByQuestionId(question.id);
      if (!nextHypothesis || nextHypothesis.id === hypothesis.id) {
        // 新しいPENDING仮説がない場合は次の質問へ
        break;
      }
      hypothesis = nextHypothesis;
    }
  }

  console.log("\n🗺️  Geo-Voyager has finished his journey.");
})();
