// filepath: /home/yuiseki/src/github.com/yuiseki/Geo-Voyager/src/lib/skills/countries/comparePopulationDensityMonacoMacao.ts
// description: モナコとマカオの人口密度を比較分析するスキル

import { getWorldBankPopulationDensityByCountryCode } from "../../common/getWorldBankPopulationDensityByCountryCode";
import { getWorldBankPopulationByCountryCode } from "../../common/getWorldBankPopulationByCountryCode";
import { getWorldBankAreaByCountryCode } from "../../common/getWorldBankAreaByCountryCode";

/**
 * モナコとマカオの詳細な地理情報
 */
interface CountryDensityInfo {
  name: string;
  code: string;
  population: number;
  area: number;
  density: number;
}

/**
 * 比較結果を格納する型
 */
export interface DensityComparisonResult {
  monaco: CountryDensityInfo;
  macao: CountryDensityInfo;
  denser: string; // どちらが人口密度が高いかの結果
  densityRatio: number; // 人口密度の比率
}

/**
 * モナコとマカオの人口密度を比較分析する関数
 * @returns モナコとマカオの人口密度比較結果
 */
export const comparePopulationDensityMonacoMacao =
  async (): Promise<DensityComparisonResult> => {
    // モナコの地理情報を取得
    const monacoCode = "MC";
    const monacoDensity = await getWorldBankPopulationDensityByCountryCode(
      monacoCode
    );
    const monacoPopulation = await getWorldBankPopulationByCountryCode(
      monacoCode
    );
    const monacoArea = await getWorldBankAreaByCountryCode(monacoCode);

    // マカオの地理情報を取得
    const macaoCode = "MO";
    const macaoDensity = await getWorldBankPopulationDensityByCountryCode(
      macaoCode
    );
    const macaoPopulation = await getWorldBankPopulationByCountryCode(
      macaoCode
    );
    const macaoArea = await getWorldBankAreaByCountryCode(macaoCode);

    // 結果をオブジェクトにまとめる
    const monaco: CountryDensityInfo = {
      name: "Monaco",
      code: monacoCode,
      population: monacoPopulation,
      area: monacoArea,
      density: monacoDensity,
    };

    const macao: CountryDensityInfo = {
      name: "Macao SAR, China",
      code: macaoCode,
      population: macaoPopulation,
      area: macaoArea,
      density: macaoDensity,
    };

    // 人口密度が高い方と比率を計算
    const denser = monacoDensity > macaoDensity ? "Monaco" : "Macao SAR, China";
    const densityRatio =
      monacoDensity > macaoDensity
        ? monacoDensity / macaoDensity
        : macaoDensity / monacoDensity;

    return {
      monaco,
      macao,
      denser,
      densityRatio,
    };
  };

/**
 * モナコとマカオの人口密度を比較した結果を文字列で返す
 * @returns 比較結果の文字列表現
 */
export const getMonacoMacaoPopulationDensityComparisonText =
  async (): Promise<string> => {
    const result = await comparePopulationDensityMonacoMacao();

    return `モナコとマカオの人口密度比較:
  - モナコ: ${result.monaco.density.toFixed(
    2
  )}人/km²（人口: ${result.monaco.population.toLocaleString()}人、面積: ${result.monaco.area.toFixed(
      2
    )}km²）
  - マカオ: ${result.macao.density.toFixed(
    2
  )}人/km²（人口: ${result.macao.population.toLocaleString()}人、面積: ${result.macao.area.toFixed(
      2
    )}km²）
  
  結果: ${result.denser}の方が人口密度が${result.densityRatio.toFixed(
      2
    )}倍高いです。`;
  };
