import { comparePopulationDensityMonacoMacao } from "./comparePopulationDensityMonacoMacao";
import { getWorldBankPopulationDensityByCountryCode } from "../../common/getWorldBankPopulationDensityByCountryCode";
import { getWorldBankPopulationByCountryCode } from "../../common/getWorldBankPopulationByCountryCode";
import { getWorldBankAreaByCountryCode } from "../../common/getWorldBankAreaByCountryCode";

describe("comparePopulationDensityMonacoMacao", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should compare population densities of Monaco and Macao", async () => {
    // モナコとマカオの人口密度比較結果を取得
    const result = await comparePopulationDensityMonacoMacao();

    // 結果の基本的な検証
    expect(result).toBeDefined();
    expect(result.monaco).toBeDefined();
    expect(result.macao).toBeDefined();
    expect(result.denser).toBeDefined();
    expect(result.densityRatio).toBeDefined();

    // 人口密度の検証
    expect(result.monaco.density).toBeGreaterThan(0);
    expect(result.macao.density).toBeGreaterThan(0);

    // 人口の検証
    expect(result.monaco.population).toBeGreaterThan(0);
    expect(result.macao.population).toBeGreaterThan(0);

    // 面積の検証
    expect(result.monaco.area).toBeGreaterThan(0);
    expect(result.macao.area).toBeGreaterThan(0);

    // 人口密度の比率が正しく計算されているか検証
    const calculatedRatio =
      Math.max(result.monaco.density, result.macao.density) /
      Math.min(result.monaco.density, result.macao.density);
    expect(result.densityRatio).toBeCloseTo(calculatedRatio, 5);

    // より人口密度が高い国が正しく特定されているか検証
    const expectedDenser =
      result.monaco.density > result.macao.density
        ? "Monaco"
        : "Macao SAR, China";
    expect(result.denser).toBe(expectedDenser);

    // 結果を出力
    console.log(`モナコとマカオの人口密度比較:
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
    )}倍高いです。`);
  }, 30000); // タイムアウトを30秒に設定

  it("should validate the data consistency for Monaco", async () => {
    const result = await comparePopulationDensityMonacoMacao();

    // モナコのコードを直接指定して取得したデータと比較
    const monacoCode = "MC";
    const expectedDensity = await getWorldBankPopulationDensityByCountryCode(
      monacoCode
    );
    const expectedPopulation = await getWorldBankPopulationByCountryCode(
      monacoCode
    );
    const expectedArea = await getWorldBankAreaByCountryCode(monacoCode);

    // 結果が一致することを検証
    expect(result.monaco.density).toBeCloseTo(expectedDensity, 5);
    expect(result.monaco.population).toBe(expectedPopulation);
    expect(result.monaco.area).toBeCloseTo(expectedArea, 5);

    // 人口密度が計算による値とも一致することを検証（人口÷面積）
    const calculatedDensity = expectedPopulation / expectedArea;
    expect(result.monaco.density).toBeCloseTo(calculatedDensity, 5);
  }, 30000); // タイムアウトを30秒に設定

  it("should validate the data consistency for Macao", async () => {
    const result = await comparePopulationDensityMonacoMacao();

    // マカオのコードを直接指定して取得したデータと比較
    const macaoCode = "MO";
    const expectedDensity = await getWorldBankPopulationDensityByCountryCode(
      macaoCode
    );
    const expectedPopulation = await getWorldBankPopulationByCountryCode(
      macaoCode
    );
    const expectedArea = await getWorldBankAreaByCountryCode(macaoCode);

    // 結果が一致することを検証
    expect(result.macao.density).toBeCloseTo(expectedDensity, 5);
    expect(result.macao.population).toBe(expectedPopulation);
    expect(result.macao.area).toBeCloseTo(expectedArea, 5);

    // 人口密度が計算による値とも一致することを検証（人口÷面積）
    const calculatedDensity = expectedPopulation / expectedArea;
    expect(result.macao.density).toBeCloseTo(calculatedDensity, 5);
  }, 30000); // タイムアウトを30秒に設定
});
