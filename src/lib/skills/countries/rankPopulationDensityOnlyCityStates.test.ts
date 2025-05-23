import {
  rankPopulationDensityOnlyCityStates,
  getPopulationDensityRankingOfCityStatesText,
} from "./rankPopulationDensityOnlyCityStates";

describe("rankPopulationDensityOnlyCityStates", () => {
  // タイムアウトを長めに設定（APIからのデータ取得に時間がかかるため）
  jest.setTimeout(120000);

  it("should return a ranked list of city-states by population density", async () => {
    // デフォルトのリミット（10）でテスト実行
    const result = await rankPopulationDensityOnlyCityStates();

    // 結果が配列であることを検証
    expect(Array.isArray(result)).toBe(true);

    // 最大10カ国が返されることを検証
    expect(result.length).toBeLessThanOrEqual(10);

    // 各国のデータが正しい形式であることを検証
    result.forEach((country) => {
      expect(country).toHaveProperty("name");
      expect(country).toHaveProperty("code");
      expect(country).toHaveProperty("population");
      expect(country).toHaveProperty("area");
      expect(country).toHaveProperty("density");

      // 数値データの検証
      expect(typeof country.population).toBe("number");
      expect(typeof country.area).toBe("number");
      expect(typeof country.density).toBe("number");

      // 人口密度が正の値であることを検証
      expect(country.density).toBeGreaterThan(0);
    });

    // ランキングが正しくソートされているかを検証
    for (let i = 0; i < result.length - 1; i++) {
      expect(result[i].density).toBeGreaterThanOrEqual(result[i + 1].density);
    }

  });

  it("should only include countries defined as city-states", async () => {
    const result = await rankPopulationDensityOnlyCityStates();

    // 定義済みの都市国家コードリスト
    const cityStateCodes = [
      "SG",
      "MC",
      "VA",
      "MO",
      "HK",
      "GI",
      "SM",
      "MT",
      "BH",
      "AD",
      "LI",
      "LU",
      "QA",
      "KW",
      "BN",
    ];

    // すべての結果が都市国家リストに含まれていることを確認
    result.forEach((country) => {
      expect(cityStateCodes).toContain(country.code);
    });
  });

  it("should have generally higher population densities than typical countries", async () => {
    const result = await rankPopulationDensityOnlyCityStates();

    // 都市国家の上位半分は非常に高い人口密度を持つはず
    const topHalf = result.slice(0, Math.ceil(result.length / 2));
    topHalf.forEach((country) => {
      // 上位半分は1000人/km²以上の人口密度があることを期待
      expect(country.density).toBeGreaterThan(1000);
    });

    // 下位の都市国家でも一般的な国よりは人口密度が高いはず
    result.forEach((country) => {
      // すべての都市国家は100人/km²以上の人口密度があることを期待
      expect(country.density).toBeGreaterThan(100);
    });
  });

  it("should generate a properly formatted text output", async () => {
    // テキスト出力機能をテスト
    const textResult = await getPopulationDensityRankingOfCityStatesText(3);

    // 出力が文字列であることを検証
    expect(typeof textResult).toBe("string");

    // 出力にタイトルが含まれていることを検証
    expect(textResult).toContain("都市国家の人口密度ランキング（上位3カ国）");

    // 3つの国のデータが含まれていることを検証（3行以上の改行があるはず）
    const lineCount = (textResult.match(/\n/g) || []).length;
    expect(lineCount).toBeGreaterThanOrEqual(3);

    console.log(textResult);
  });
});
