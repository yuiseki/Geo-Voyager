// src/main.ts
import { getAllQuestionsByStatus, QuestionStatus } from "./db/question";
import { listUpAllSolvedQuestions } from "./utils/listUpAllSolvedQuestions";
import { getAllExecutedTasksByQuestionId, TaskStatus } from "./db/task";
import { findAndExecuteTasksByQuestion } from "./utils/findAndExecuteTasksByQuestion";

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

    await findAndExecuteTasksByQuestion(question);

    const executedTasks = await getAllExecutedTasksByQuestionId(question.id);
    if (executedTasks.length > 0) {
      console.log("📚 Executed tasks:");
      for (const task of executedTasks) {
        if (task.status === TaskStatus.COMPLETED) {
          console.log(
            `  - ✅ Task: ${task.description} - ${task.result} [${task.status}]`
          );
        } else {
          console.log(`  - ❌ Task: ${task.description} [${task.status}]`);
        }
      }
    }
  }

  console.log("\n🗺️  Geo-Voyager has finished his journey.");
})();
