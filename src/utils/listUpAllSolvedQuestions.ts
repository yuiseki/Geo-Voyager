import { getQuestionsByStatus, QuestionStatus } from "../db/question";

export const listUpAllSolvedQuestions = async () => {
  const questions = await getQuestionsByStatus(QuestionStatus.SOLVED);
  console.log(`📚 Total ${questions.length} solved questions:`);
  for (const question of questions) {
    console.log(`- ✨️ ${question.description}`);
  }
}