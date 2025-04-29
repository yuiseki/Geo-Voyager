// filepath: /home/yuiseki/src/github.com/yuiseki/Geo-Voyager/src/lib/skills/countries/rankPopulationDensityOnlyCityStates.ts
// description: 都市国家のみの人口密度ランキングを生成するスキル

import { getWorldBankAllCountriesAlpha2Codes } from "../../common/getWorldBankAllCountriesAlpha2Codes";
import { getWorldBankCountryNameByAlpha2Codes } from "../../common/getWorldBankCountryNameByAlpha2Codes";
import { getWorldBankPopulationDensityByCountryCode } from "../../common/getWorldBankPopulationDensityByCountryCode";
import { getWorldBankPopulationByCountryCode } from "../../common/getWorldBankPopulationByCountryCode";
import { getWorldBankAreaByCountryCode } from "../../common/getWorldBankAreaByCountryCode";
import { CountryDensityInfo } from "./rankPopulationDensityOfAllCountries";

/**
 * 都市国家の定義に当てはまる国や特別行政区のISO 3166-1アルファ2コードのリスト
 * 主に小さな面積で高度に都市化された国家または特別行政区を含む
 */
const CITY_STATE_CODES = [
  "SG", // シンガポール
  "MC", // モナコ
  "VA", // バチカン市国
  "MO", // マカオ
  "HK", // 香港
  "GI", // ジブラルタル
  "SM", // サンマリノ
  "MT", // マルタ
  "BH", // バーレーン
  "AD", // アンドラ
  "LI", // リヒテンシュタイン
  "LU", // ルクセンブルク
  "QA", // カタール
  "KW", // クウェート
  "BN", // ブルネイ
];

/**
 * 都市国家のみの人口密度ランキングを生成する関数
 * @param limit 結果の上位数（デフォルト10）
 * @returns 人口密度の高い順に並べられた都市国家の情報配列
 */
export const rankPopulationDensityOnlyCityStates = async (
  limit: number = 10
): Promise<CountryDensityInfo[]> => {
  const alpha2Codes = await getWorldBankAllCountriesAlpha2Codes();
  const cityStatesData: CountryDensityInfo[] = [];

  for (const code of alpha2Codes) {
    if (typeof code !== "string") continue;
    if (code === "XK") continue; // コソボはWorld Bank APIにデータがない

    // 都市国家リストに含まれていない場合はスキップ
    if (!CITY_STATE_CODES.includes(code)) continue;

    try {
      const density = await getWorldBankPopulationDensityByCountryCode(code);

      // 人口密度が0以下、または非常に小さい値の場合はスキップ（無人地域や特殊領域の可能性）
      if (density <= 0 || density < 0.01) continue;

      const name = await getWorldBankCountryNameByAlpha2Codes(code);
      const population = await getWorldBankPopulationByCountryCode(code);
      const area = await getWorldBankAreaByCountryCode(code);

      cityStatesData.push({
        name,
        code,
        population,
        area,
        density,
      });
    } catch (error) {
      console.error(`Error processing city state ${code}: ${error}`);
      continue;
    }
  }

  // 人口密度の高い順にソート
  const rankedCityStates = cityStatesData.sort((a, b) => b.density - a.density);

  // 上位X件を返す
  return rankedCityStates.slice(0, limit);
};

/**
 * 都市国家のみの人口密度ランキングを文字列形式で取得する関数
 * @param limit 結果の上位数（デフォルト10）
 * @returns フォーマットされたランキング文字列
 */
export const getPopulationDensityRankingOfCityStatesText = async (
  limit: number = 10
): Promise<string> => {
  const rankedCityStates = await rankPopulationDensityOnlyCityStates(limit);

  let result = `都市国家の人口密度ランキング（上位${limit}カ国）:\n\n`;

  rankedCityStates.forEach((country, index) => {
    result +=
      `${index + 1}. ${country.name}: ${country.density.toFixed(2)}人/km² ` +
      `（人口: ${country.population.toLocaleString()}人、面積: ${country.area.toFixed(
        2
      )}km²）\n`;
  });

  return result;
};
