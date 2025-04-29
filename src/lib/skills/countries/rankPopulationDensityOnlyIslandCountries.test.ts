import {
  rankPopulationDensityOnlyIslandCountries,
  getPopulationDensityRankingOfIslandCountriesText,
} from "./rankPopulationDensityOnlyIslandCountries";

describe("rankPopulationDensityOnlyIslandCountries", () => {
  // タイムアウトを長めに設定（APIからのデータ取得に時間がかかるため）
  jest.setTimeout(120000);

  it("should return a ranked list of island countries by population density", async () => {
    // デフォルトのリミット（10）でテスト実行
    const result = await rankPopulationDensityOnlyIslandCountries();

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

    // 結果を表示
    console.log(`島国の人口密度ランキング（上位${result.length}カ国）:`);
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

  it("should only include countries defined as island countries", async () => {
    const result = await rankPopulationDensityOnlyIslandCountries();

    // 定義済みの島国コードリストを取得（privateな定数にアクセスするため実装を確認）
    // この実装は不完全ですが、テストとしては機能します
    const islandCountryCodes = [
      "JP",
      "PH",
      "ID",
      "GB",
      "IE",
      "IS",
      "CU",
      "DO",
      "HT",
      "JM",
      "TT",
      "BS",
      "BB",
      "AG",
      "DM",
      "GD",
      "KN",
      "LC",
      "VC",
      "SG",
      "MV",
      "LK",
      "CY",
      "MT",
      "KM",
      "MU",
      "SC",
      "MG",
      "FJ",
      "SB",
      "VU",
      "WS",
      "TO",
      "KI",
      "FM",
      "MH",
      "PW",
      "NR",
      "TV",
      "NZ",
      "AU",
      "TW",
      "TL",
      "BH",
      "GL",
      "MO",
      "HK",
      "TZ",
      "CK",
      "PG",
    ];

    // すべての結果が島国リストに含まれていることを確認
    result.forEach((country) => {
      expect(islandCountryCodes).toContain(country.code);
    });
  });

  it("should generate a properly formatted text output", async () => {
    // テキスト出力機能をテスト
    const textResult = await getPopulationDensityRankingOfIslandCountriesText(
      3
    );

    // 出力が文字列であることを検証
    expect(typeof textResult).toBe("string");

    // 出力にタイトルが含まれていることを検証
    expect(textResult).toContain("島国の人口密度ランキング（上位3カ国）");

    // 3つの国のデータが含まれていることを検証（3行以上の改行があるはず）
    const lineCount = (textResult.match(/\n/g) || []).length;
    expect(lineCount).toBeGreaterThanOrEqual(3);

    console.log(textResult);
  });
});
