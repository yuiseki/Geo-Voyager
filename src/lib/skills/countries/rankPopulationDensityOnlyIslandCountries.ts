// filepath: /home/yuiseki/src/github.com/yuiseki/Geo-Voyager/src/lib/skills/countries/rankPopulationDensityOnlyIslandCountries.ts
// description: 島国のみの人口密度ランキングを生成するスキル

import { getWorldBankAllCountriesAlpha2Codes } from "../../common/getWorldBankAllCountriesAlpha2Codes";
import { getWorldBankCountryNameByAlpha2Codes } from "../../common/getWorldBankCountryNameByAlpha2Codes";
import { getWorldBankPopulationDensityByCountryCode } from "../../common/getWorldBankPopulationDensityByCountryCode";
import { getWorldBankPopulationByCountryCode } from "../../common/getWorldBankPopulationByCountryCode";
import { getWorldBankAreaByCountryCode } from "../../common/getWorldBankAreaByCountryCode";
import { CountryDensityInfo } from "./rankPopulationDensityOfAllCountries";

/**
 * 島国の定義に当てはまる国のISO 3166-1アルファ2コードのリスト
 * 主に海に囲まれた島として存在する国家を含む
 */
const ISLAND_COUNTRY_CODES = [
  "JP", // 日本
  "PH", // フィリピン
  "ID", // インドネシア
  "GB", // イギリス
  "IE", // アイルランド
  "IS", // アイスランド
  "CU", // キューバ
  "DO", // ドミニカ共和国
  "HT", // ハイチ
  "JM", // ジャマイカ
  "TT", // トリニダード・トバゴ
  "BS", // バハマ
  "BB", // バルバドス
  "AG", // アンティグア・バーブーダ
  "DM", // ドミニカ国
  "GD", // グレナダ
  "KN", // セントクリストファー・ネイビス
  "LC", // セントルシア
  "VC", // セントビンセント・グレナディーン
  "SG", // シンガポール
  "MV", // モルディブ
  "LK", // スリランカ
  "CY", // キプロス
  "MT", // マルタ
  "KM", // コモロ
  "MU", // モーリシャス
  "SC", // セーシェル
  "MG", // マダガスカル
  "FJ", // フィジー
  "SB", // ソロモン諸島
  "VU", // バヌアツ
  "WS", // サモア
  "TO", // トンガ
  "KI", // キリバス
  "FM", // ミクロネシア連邦
  "MH", // マーシャル諸島
  "PW", // パラオ
  "NR", // ナウル
  "TV", // ツバル
  "NZ", // ニュージーランド
  "AU", // オーストラリア
  "TW", // 台湾
  "TL", // 東ティモール
  "BH", // バーレーン
  "GL", // グリーンランド
  "MO", // マカオ
  "HK", // 香港
  "TZ", // タンザニア（ザンジバル島を含む）
  "CK", // クック諸島
  "PG", // パプアニューギニア
];

/**
 * 島国のみの人口密度ランキングを生成する関数
 * @param limit 結果の上位数（デフォルト10）
 * @returns 人口密度の高い順に並べられた島国の情報配列
 */
export const rankPopulationDensityOnlyIslandCountries = async (
  limit: number = 10
): Promise<CountryDensityInfo[]> => {
  const alpha2Codes = await getWorldBankAllCountriesAlpha2Codes();
  const islandCountriesData: CountryDensityInfo[] = [];

  for (const code of alpha2Codes) {
    if (typeof code !== "string") continue;
    if (code === "XK") continue; // コソボはWorld Bank APIにデータがない

    // 島国リストに含まれていない場合はスキップ
    if (!ISLAND_COUNTRY_CODES.includes(code)) continue;

    try {
      const density = await getWorldBankPopulationDensityByCountryCode(code);

      // 人口密度が0以下、または非常に小さい値の場合はスキップ（無人地域や特殊領域の可能性）
      if (density <= 0 || density < 0.01) continue;

      const name = await getWorldBankCountryNameByAlpha2Codes(code);
      const population = await getWorldBankPopulationByCountryCode(code);
      const area = await getWorldBankAreaByCountryCode(code);

      islandCountriesData.push({
        name,
        code,
        population,
        area,
        density,
      });
    } catch (error) {
      console.error(`Error processing island country ${code}: ${error}`);
      continue;
    }
  }

  // 人口密度の高い順にソート
  const rankedIslandCountries = islandCountriesData.sort(
    (a, b) => b.density - a.density
  );

  // 上位X件を返す
  return rankedIslandCountries.slice(0, limit);
};

/**
 * 島国のみの人口密度ランキングを文字列形式で取得する関数
 * @param limit 結果の上位数（デフォルト10）
 * @returns フォーマットされたランキング文字列
 */
export const getPopulationDensityRankingOfIslandCountriesText = async (
  limit: number = 10
): Promise<string> => {
  const rankedIslandCountries = await rankPopulationDensityOnlyIslandCountries(
    limit
  );

  let result = `島国の人口密度ランキング（上位${limit}カ国）:\n\n`;

  rankedIslandCountries.forEach((country, index) => {
    result +=
      `${index + 1}. ${country.name}: ${country.density.toFixed(2)}人/km² ` +
      `（人口: ${country.population.toLocaleString()}人、面積: ${country.area.toFixed(
        2
      )}km²）\n`;
  });

  return result;
};
