import { getAllQuestionsByStatus, QuestionStatus } from "../db/question";
import { getAllExecutedTasksByQuestionId, TaskStatus } from "../db/task";

export const listUpAllSolvedQuestions = async () => {
  const questions = await getAllQuestionsByStatus(QuestionStatus.SOLVED);
  console.log(`📚 Total ${questions.length} solved questions:`);
  for (const question of questions) {
    console.log(`- ✨️ ${question.description}`);
    const executedTasks = await getAllExecutedTasksByQuestionId(question.id);
    if (executedTasks.length > 0) {
      for (const task of executedTasks) {
        if (task.status === TaskStatus.COMPLETED) {
          console.log(`  - ✅ Task: ${task.description}[${task.status}]`);
          console.log(`    - 📝️ Result: ${task.result}`);
        } else {
          console.log(`  - ❌ Task: ${task.description} [${task.status}]`);
        }
      }
    }
  }
};
