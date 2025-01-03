import { getAllHypothesesByStatus, HypothesisStatus } from "../db/hypothesis";
import { distance } from "fastest-levenshtein";

// 仮説スコアを計算する関数
export const calculateHypothesisScore = async (
  newHypothesis: string
): Promise<number> => {
  // 編集距離から類似性を計算するユーティリティ関数
  const calculateSimilarity = (a: string, b: string): number => {
    const maxLength = Math.max(a.length, b.length);
    const levenshteinDistance = distance(a, b);
    return 1 - levenshteinDistance / maxLength; // 類似性スコア（0〜1の範囲）
  };

  // 陳腐さスコア
  const verifiedHypotheses = await getAllHypothesesByStatus(
    HypothesisStatus.VERIFIED
  );
  const rejectedHypotheses = await getAllHypothesesByStatus(
    HypothesisStatus.REJECTED
  );
  const verifiedAndRejectedHypotheses = [
    ...verifiedHypotheses,
    ...rejectedHypotheses,
  ];
  const redundancyScores = verifiedAndRejectedHypotheses.map((h) =>
    calculateSimilarity(newHypothesis, h.description)
  );
  const redundancyScore =
    redundancyScores.length > 0 ? Math.max(...redundancyScores) : 0;

  // 荒唐無稽さスコア
  const unverifiedFetchHypotheses = await getAllHypothesesByStatus(
    HypothesisStatus.UNVERIFIABLE_FETCH
  );
  const unverifiedAnalyzeHypotheses = await getAllHypothesesByStatus(
    HypothesisStatus.UNVERIFIABLE_ANALYZE
  );
  const unverifiedHypotheses = [
    ...unverifiedFetchHypotheses,
    ...unverifiedAnalyzeHypotheses,
  ];
  const unverifiedScores = unverifiedHypotheses.map((h) =>
    calculateSimilarity(newHypothesis, h.description)
  );
  const unverifiedScore =
    unverifiedScores.length > 0 ? Math.max(...unverifiedScores) : 0;

  // 総合スコア
  // (1 - redundancyScore) * (1 - unverifiedScore)
  const score = (1 - redundancyScore) * (1 - unverifiedScore);
  return score;
};
