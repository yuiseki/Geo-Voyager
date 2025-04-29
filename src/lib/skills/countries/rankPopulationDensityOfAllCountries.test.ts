import {
  rankPopulationDensityOfAllCountries,
  getPopulationDensityRankingOfAllCountriesText,
} from "./rankPopulationDensityOfAllCountries";

describe("rankPopulationDensityOfAllCountries", () => {
  // タイムアウトを長めに設定（APIからのデータ取得に時間がかかるため）
  jest.setTimeout(120000);

  it("should return a ranked list of countries by population density", async () => {
    // デフォルトのリミット（10）でテスト実行
    const result = await rankPopulationDensityOfAllCountries();

    // 結果が配列であることを検証
    expect(Array.isArray(result)).toBe(true);

    // 10カ国が返されることを検証
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

    // 結果を表示
    console.log(`世界の人口密度ランキング（上位${result.length}カ国）:`);
    result.forEach((country, index) => {
      console.log(
        `${index + 1}. ${country.name}: ${country.density.toFixed(
          2
        )}人/km²（人口: ${country.population.toLocaleString()}人、面積: ${country.area.toFixed(
          2
        )}km²）`
      );
    });
  });

  it("should respect the limit parameter", async () => {
    // リミットを5に設定
    const result = await rankPopulationDensityOfAllCountries(5);

    // 5カ国が返されることを検証
    expect(result.length).toBeLessThanOrEqual(5);
  });

  it("should generate a properly formatted text output", async () => {
    // テキスト出力機能をテスト
    const textResult = await getPopulationDensityRankingOfAllCountriesText(3);

    // 出力が文字列であることを検証
    expect(typeof textResult).toBe("string");

    // 出力にタイトルが含まれていることを検証
    expect(textResult).toContain("世界の人口密度ランキング（上位3カ国）");

    // 3つの国のデータが含まれていることを検証（3行以上の改行があるはず）
    const lineCount = (textResult.match(/\n/g) || []).length;
    expect(lineCount).toBeGreaterThanOrEqual(3);

    console.log(textResult);
  });
});
