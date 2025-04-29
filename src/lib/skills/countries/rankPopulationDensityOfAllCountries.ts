// filepath: /home/yuiseki/src/github.com/yuiseki/Geo-Voyager/src/lib/skills/countries/rankPopulationDensityOfAllCountries.ts
// description: 世界のすべての国の人口密度ランキングを生成するスキル

import { getWorldBankAllCountriesAlpha2Codes } from "../../common/getWorldBankAllCountriesAlpha2Codes";
import { getWorldBankCountryNameByAlpha2Codes } from "../../common/getWorldBankCountryNameByAlpha2Codes";
import { getWorldBankPopulationDensityByCountryCode } from "../../common/getWorldBankPopulationDensityByCountryCode";
import { getWorldBankPopulationByCountryCode } from "../../common/getWorldBankPopulationByCountryCode";
import { getWorldBankAreaByCountryCode } from "../../common/getWorldBankAreaByCountryCode";

/**
 * 国の人口密度情報を表すインターフェース
 */
export interface CountryDensityInfo {
  name: string;
  code: string;
  population: number;
  area: number;
  density: number;
}

/**
 * 世界のすべての国の人口密度ランキングを生成する関数
 * @param limit 結果の上位数（デフォルト10）
 * @returns 人口密度の高い順に並べられた国の情報配列
 */
export const rankPopulationDensityOfAllCountries = async (
  limit: number = 10
): Promise<CountryDensityInfo[]> => {
  const alpha2Codes = await getWorldBankAllCountriesAlpha2Codes();
  const countriesData: CountryDensityInfo[] = [];

  for (const code of alpha2Codes) {
    if (typeof code !== "string") continue;
    if (code === "XK") continue; // コソボはWorld Bank APIにデータがない

    try {
      const density = await getWorldBankPopulationDensityByCountryCode(code);

      // 人口密度が0以下、または非常に小さい値の場合はスキップ（無人地域や特殊領域の可能性）
      if (density <= 0 || density < 0.01) continue;

      const name = await getWorldBankCountryNameByAlpha2Codes(code);
      const population = await getWorldBankPopulationByCountryCode(code);
      const area = await getWorldBankAreaByCountryCode(code);

      countriesData.push({
        name,
        code,
        population,
        area,
        density,
      });
    } catch (error) {
      console.error(`Error processing country ${code}: ${error}`);
      continue;
    }
  }

  // 人口密度の高い順にソート
  const rankedCountries = countriesData.sort((a, b) => b.density - a.density);

  // 上位X件を返す
  return rankedCountries.slice(0, limit);
};

/**
 * 世界のすべての国の人口密度ランキングを文字列形式で取得する関数
 * @param limit 結果の上位数（デフォルト10）
 * @returns フォーマットされたランキング文字列
 */
export const getPopulationDensityRankingOfAllCountriesText = async (
  limit: number = 10
): Promise<string> => {
  const rankedCountries = await rankPopulationDensityOfAllCountries(limit);

  let result = `世界の人口密度ランキング（上位${limit}カ国）:\n\n`;

  rankedCountries.forEach((country, index) => {
    result +=
      `${index + 1}. ${country.name}: ${country.density.toFixed(2)}人/km² ` +
      `（人口: ${country.population.toLocaleString()}人、面積: ${country.area.toFixed(
        2
      )}km²）\n`;
  });

  return result;
};
