import { getAllQuestionsByStatus, QuestionStatus } from "../db/question";

export const listUpAllSolvedQuestions = async () => {
  const questions = await getAllQuestionsByStatus(QuestionStatus.SOLVED);
  console.log(`📚 Total ${questions.length} solved questions:`);
  for (const question of questions) {
    console.log(`- ✨️ ${question.description}`);
  }
};
