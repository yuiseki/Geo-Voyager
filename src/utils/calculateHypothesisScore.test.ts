import { calculateHypothesisScore } from "./calculateHypothesisScore";
import { getHypothesesByStatus, HypothesisStatus } from "../db/hypothesis";

// Jestのモックを作成
jest.mock("../db/hypothesis", () => ({
  getHypothesesByStatus: jest.fn(),
  HypothesisStatus: {
    VERIFIED: "VERIFIED",
    REJECTED: "REJECTED",
    UNVERIFIABLE_FETCH: "UNVERIFIABLE_FETCH",
    UNVERIFIABLE_ANALYZE: "UNVERIFIABLE_ANALYZE",
  },
}));

describe("calculateHypothesisScore", () => {
  it("should return 1 when there are no existing hypotheses", async () => {
    // モックで空の配列を返すように設定
    (getHypothesesByStatus as jest.Mock).mockResolvedValue([]);

    const score = await calculateHypothesisScore("new hypothesis");
    expect(score).toBe(1); // スコアは1になるはず
  });

  it("should return a lower score for a hypothesis similar to a verified one", async () => {
    // モックでVERIFIEDステータスの仮説を返すように設定
    (getHypothesesByStatus as jest.Mock).mockImplementation((status) => {
      if (status === HypothesisStatus.VERIFIED) {
        return Promise.resolve([{ description: "verified hypothesis" }]);
      }
      return Promise.resolve([]);
    });

    const score = await calculateHypothesisScore("verified hypothesis");
    expect(score).toBeLessThan(1); // 類似性があるためスコアは1未満
  });

  it("should return a lower score for a hypothesis similar to an unverifiable one", async () => {
    // モックでUNVERIFIABLE_FETCHステータスの仮説を返すように設定
    (getHypothesesByStatus as jest.Mock).mockImplementation((status) => {
      if (status === HypothesisStatus.UNVERIFIABLE_FETCH) {
        return Promise.resolve([{ description: "unverifiable hypothesis" }]);
      }
      return Promise.resolve([]);
    });

    const score = await calculateHypothesisScore("unverifiable hypothesis");
    expect(score).toBeLessThan(1); // 類似性があるためスコアは1未満
  });

  it("should calculate the combined score correctly", async () => {
    // モックでVERIFIEDとUNVERIFIABLE_FETCHの仮説を返すように設定
    (getHypothesesByStatus as jest.Mock).mockImplementation((status) => {
      if (status === HypothesisStatus.VERIFIED) {
        return Promise.resolve([{ description: "verified hypothesis" }]);
      }
      if (status === HypothesisStatus.UNVERIFIABLE_FETCH) {
        return Promise.resolve([{ description: "unverifiable hypothesis" }]);
      }
      return Promise.resolve([]);
    });

    const score = await calculateHypothesisScore("verified hypothesis 2");
    expect(score).toBeGreaterThan(0); // スコアは0以上
    expect(score).toBeLessThan(1); // スコアは1未満
  });
});
