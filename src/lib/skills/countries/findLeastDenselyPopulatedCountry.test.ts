import { findLeastDenselyPopulatedCountry } from "./findLeastDenselyPopulatedCountry";
import { getWorldBankPopulationDensityByCountryCode } from "../../common/getWorldBankPopulationDensityByCountryCode";
import { getWorldBankCountryNameByAlpha2Codes } from "../../common/getWorldBankCountryNameByAlpha2Codes";
import { getWorldBankAllCountriesAlpha2Codes } from "../../common/getWorldBankAllCountriesAlpha2Codes";
import { getWorldBankPopulationByCountryCode } from "../../common/getWorldBankPopulationByCountryCode";
import { getWorldBankAreaByCountryCode } from "../../common/getWorldBankAreaByCountryCode";

describe("findLeastDenselyPopulatedCountry", () => {
  it("should find the least densely populated country in the world", async () => {
    // キャッシュを使用するため、モックは不要
    const result = await findLeastDenselyPopulatedCountry();

    // 結果が文字列であることを確認
    expect(typeof result).toBe("string");

    // 国名が空ではないことを確認
    expect(result.length).toBeGreaterThan(0);

    // この国のISO コードを見つける
    const alpha2Codes = await getWorldBankAllCountriesAlpha2Codes();
    let countryCode = "";
    for (const code of alpha2Codes) {
      if (typeof code !== "string") continue;

      try {
        const countryName = await getWorldBankCountryNameByAlpha2Codes(code);
        if (countryName === result) {
          countryCode = code;
          break;
        }
      } catch (error) {
        continue;
      }
    }

    // 人口密度データを取得
    const populationDensity = await getWorldBankPopulationDensityByCountryCode(
      countryCode
    );

    // 人口データを取得
    const population = await getWorldBankPopulationByCountryCode(countryCode);

    // 面積データを計算
    const area = await getWorldBankAreaByCountryCode(countryCode);

    // 人口密度が低いことを検証
    expect(populationDensity).toBeLessThan(10); // 1平方km当たり10人以下が期待される

    // 結論のみを簡潔に出力 (詳細データを含む)
    console.log(
      `世界で最も人口密度が低い国は${result}で、人口密度は${populationDensity.toFixed(
        2
      )}人/km²です（人口: ${population.toLocaleString()}人、面積: ${area.toFixed(
        2
      )}km²）`
    );
  }, 60000); // タイムアウトを60秒に設定
});
