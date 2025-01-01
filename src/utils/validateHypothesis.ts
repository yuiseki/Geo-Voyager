import {
  getHypothesisById,
  HypothesisStatus,
  updateHypothesisStatus,
} from "../db/hypothesis";

export const validateHypothesis = async (hypothesisId: number) => {
  const hypothesis = await getHypothesisById(hypothesisId);
  if (!hypothesis || hypothesis.status !== "PENDING") {
    throw new Error("Invalid hypothesis for validation.");
  }

  // FetchSkillを模擬的に実行
  const fetchSkillCode = "return { data: 'dummy data' };";
  const fetchResult = new Function(fetchSkillCode)();
  console.log("Fetch Result:", fetchResult);

  // AnalyzeSkillを模擬的に実行
  const analyzeSkillCode =
    "return data === 'dummy data' ? 'success' : 'failure';";
  const analyzeResult = new Function("data", analyzeSkillCode)(
    fetchResult.data
  );
  console.log("Analyze Result:", analyzeResult);

  // ステータス更新
  const newStatus =
    analyzeResult === "success"
      ? HypothesisStatus.VERIFIED
      : HypothesisStatus.REJECTED;
  await updateHypothesisStatus(hypothesisId, newStatus);

  return newStatus;
};
