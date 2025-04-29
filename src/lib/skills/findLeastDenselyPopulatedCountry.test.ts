import { findLeastDenselyPopulatedCountry } from "./findLeastDenselyPopulatedCountry";

describe("findLeastDenselyPopulatedCountry", () => {
  it("should find the least densely populated country in the world", async () => {
    // キャッシュを使用するため、モックは不要
    const result = await findLeastDenselyPopulatedCountry();

    // 結果が文字列であることを確認
    expect(typeof result).toBe("string");

    // 国名が空ではないことを確認
    expect(result.length).toBeGreaterThan(0);

    // 結論のみを簡潔に出力
    console.log(`世界で最も人口密度が低い国は${result}です`);
  });
});
