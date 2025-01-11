// src/main.ts
import { getAllQuestionsByStatus, QuestionStatus } from "./db/question";
import { listUpAllSolvedQuestions } from "./utils/listUpAllSolvedQuestions";
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
  }

  console.log("\n🗺️  Geo-Voyager has finished his journey.");
})();
