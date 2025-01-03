import { calculateQuestionScore } from "./calculateQuestionScore";
import { getAllQuestionsByStatus } from "../db/question";

jest.mock("../db/question", () => ({
  getQuestionsByStatus: jest.fn(),
}));

describe("calculateQuestionScore", () => {
  it("should return 1 when there are no existing questions", async () => {
    (getAllQuestionsByStatus as jest.Mock).mockResolvedValue([]);

    const score = await calculateQuestionScore(
      "What is the population of Tokyo?"
    );
    expect(score).toBe(1);
  });

  it("should return a lower score for a question similar to an existing one", async () => {
    (getAllQuestionsByStatus as jest.Mock).mockImplementation((status) => {
      if (status === "OPEN" || status === "SOLVED") {
        return Promise.resolve([
          { description: "What is the population of Tokyo?" },
        ]);
      }
      return Promise.resolve([]);
    });

    const score = await calculateQuestionScore("What is Tokyo's population?");
    expect(score).toBeLessThan(1);
  });

  it("should return a lower score for a question similar to an unresolvable one", async () => {
    (getAllQuestionsByStatus as jest.Mock).mockImplementation((status) => {
      if (status === "UNRESOLVABLE") {
        return Promise.resolve([
          { description: "What is the exact number of stars in the universe?" },
        ]);
      }
      return Promise.resolve([]);
    });

    const score = await calculateQuestionScore(
      "How many stars are in the universe?"
    );
    expect(score).toBeLessThan(1);
  });

  it("should calculate the combined score correctly", async () => {
    (getAllQuestionsByStatus as jest.Mock).mockImplementation((status) => {
      if (status === "OPEN" || status === "SOLVED") {
        return Promise.resolve([
          { description: "What is the population of Tokyo?" },
        ]);
      }
      if (status === "UNRESOLVABLE") {
        return Promise.resolve([
          { description: "What is the exact number of stars in the universe?" },
        ]);
      }
      return Promise.resolve([]);
    });

    const score = await calculateQuestionScore(
      "How many people live in Tokyo?"
    );
    expect(score).toBeGreaterThan(0);
    expect(score).toBeLessThan(1);
  });
});
