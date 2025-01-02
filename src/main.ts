// src/main.ts
import { getFirstOpenQuestion } from "./db/question";
import { getFirstPendingHypothesisByQuestionId } from "./db/hypothesis";
import { findAndExecuteTasksByHypothesis } from "./utils/findAndExecuteTasksByHypothesis";
import { formulateNewHypothesis } from "./utils/formulateNewHypothesis";

(async () => {
  console.log("🗺️  Geo-Voyager Starting...");

  // OPENなQuestionを1件取得
  const question = await getFirstOpenQuestion();
  if (!question) {
    console.log("⚠️  No OPEN questions found.");
    return;
  } else {
    console.log(`❓️ Question: ${question.description}`);
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
})();
