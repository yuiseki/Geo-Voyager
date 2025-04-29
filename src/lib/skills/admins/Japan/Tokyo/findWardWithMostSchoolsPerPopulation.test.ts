import { findWardWithMostSchoolsPerPopulation } from "./findWardWithMostSchoolsPerPopulation";
import { getSchoolsCountByWard } from "./ward/getSchoolsCountByWard";
import { getPopulationOfWard } from "./ward/getPopulationOfWard";

describe("findWardWithMostSchoolsPerPopulation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should find the ward with most schools per population in Tokyo", async () => {
    // 実際に人口あたりの学校数が最も多い区を取得
    const wardWithMostSchoolsPerPopulation =
      await findWardWithMostSchoolsPerPopulation();

    // 結果が文字列であることを確認
    expect(typeof wardWithMostSchoolsPerPopulation).toBe("string");

    // 結果が空でないことを確認
    expect(wardWithMostSchoolsPerPopulation.length).toBeGreaterThan(0);

    // 人口あたりの学校数を計算して検証
    const schoolCount = await getSchoolsCountByWard(
      wardWithMostSchoolsPerPopulation
    );
    const population = await getPopulationOfWard(
      wardWithMostSchoolsPerPopulation
    );
    const schoolsPerPopulation = Number(schoolCount) / population;

    // 学校数と人口が正常値であることを確認
    expect(Number(schoolCount)).toBeGreaterThan(0);
    expect(population).toBeGreaterThan(0);

    console.log(
      `最も人口あたりの学校数が多い区は${wardWithMostSchoolsPerPopulation}で、` +
        `人口あたりの学校数は${(schoolsPerPopulation * 10000).toFixed(
          2
        )}校/1万人です` +
        `（学校数: ${schoolCount}、人口: ${population.toLocaleString()}人）`
    );
  }, 90000); // タイムアウトを90秒に設定（多くの区をチェックするため）

  it("should validate that the result actually has the most schools per population", async () => {
    // 学校が多いと予想される区のリスト（テスト用）
    const potentialWards = ["文京区", "中央区", "港区"];

    // 実際に最も人口あたりの学校数が多い区を取得
    const wardWithMostSchoolsPerPopulation =
      await findWardWithMostSchoolsPerPopulation();

    // 選ばれた区の人口あたりの学校数を計算
    const schoolCount = await getSchoolsCountByWard(
      wardWithMostSchoolsPerPopulation
    );
    const population = await getPopulationOfWard(
      wardWithMostSchoolsPerPopulation
    );
    const highestSchoolsPerPopulation = Number(schoolCount) / population;

    // サンプル区と比較して、実際に最も人口あたりの学校数が多い区が選ばれていることを確認
    for (const ward of potentialWards) {
      if (ward === wardWithMostSchoolsPerPopulation) continue; // 同じ区はスキップ

      const wardSchoolCount = await getSchoolsCountByWard(ward);
      const wardPopulation = await getPopulationOfWard(ward);

      // 学校数が0の場合や人口が0の場合は比較しない
      if (Number(wardSchoolCount) === 0 || wardPopulation === 0) {
        console.log(
          `${ward}の学校数が${wardSchoolCount}、人口が${wardPopulation}のため、比較をスキップします`
        );
        continue;
      }

      const wardSchoolsPerPopulation = Number(wardSchoolCount) / wardPopulation;

      // 人口あたりの学校数が正の有限値であることを確認
      if (!isFinite(wardSchoolsPerPopulation)) {
        console.log(
          `${ward}の人口あたりの学校数が有限値でないため、比較をスキップします`
        );
        continue;
      }

      // 最も人口あたりの学校数が多い区の方が、比較対象より数値が大きいことを確認
      expect(highestSchoolsPerPopulation).toBeGreaterThanOrEqual(
        wardSchoolsPerPopulation
      );
    }
  }, 120000); // 複数の区を比較するため、十分な時間を設定
});
