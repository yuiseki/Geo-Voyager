import { getAllQuestionsByStatus, QuestionStatus } from "../db/question";
import { distance } from "fastest-levenshtein";

// 疑問スコアを計算する関数
export const calculateQuestionScore = async (
  newQuestion: string
): Promise<number> => {
  // 編集距離から類似性を計算するユーティリティ関数
  const calculateSimilarity = (a: string, b: string): number => {
    const maxLength = Math.max(a.length, b.length);
    const levenshteinDistance = distance(a, b);
    return 1 - levenshteinDistance / maxLength; // 類似性スコア（0〜1の範囲）
  };

  // 陳腐さスコア
  const openQuestions = await getAllQuestionsByStatus(QuestionStatus.OPEN);
  const solvedQuestions = await getAllQuestionsByStatus(QuestionStatus.SOLVED);
  const openAndSolvedQuestions = [...openQuestions, ...solvedQuestions];

  const redundancyScores = openAndSolvedQuestions.map((q) =>
    calculateSimilarity(newQuestion, q.description)
  );
  const redundancyScore =
    redundancyScores.length > 0 ? Math.max(...redundancyScores) : 0;

  // 荒唐無稽さスコア
  const unresolvableQuestions = await getAllQuestionsByStatus(
    QuestionStatus.UNRESOLVABLE
  );
  const unresolvableScores = unresolvableQuestions.map((q) =>
    calculateSimilarity(newQuestion, q.description)
  );
  const unresolvableScore =
    unresolvableScores.length > 0 ? Math.max(...unresolvableScores) : 0;

  // 総合スコア
  // (1 - redundancyScore) * (1 - unresolvableScore)
  const score = (1 - redundancyScore) * (1 - unresolvableScore);
  return score;
};
