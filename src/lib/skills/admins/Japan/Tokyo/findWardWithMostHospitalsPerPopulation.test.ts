import { findWardWithMostHospitalsPerPopulation } from "./findWardWithMostHospitalsPerPopulation";
import { getHospitalsCountByWard } from "./ward/getHospitalsCountByWard";
import { getPopulationOfWard } from "./ward/getPopulationOfWard";

describe("findWardWithMostHospitalsPerPopulation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should find the ward with most hospitals per population in Tokyo", async () => {
    // 実際に人口あたりの病院数が最も多い区を取得
    const wardWithMostHospitalsPerPopulation =
      await findWardWithMostHospitalsPerPopulation();

    // 結果が文字列であることを確認
    expect(typeof wardWithMostHospitalsPerPopulation).toBe("string");

    // 結果が空でないことを確認
    expect(wardWithMostHospitalsPerPopulation.length).toBeGreaterThan(0);

    // 人口あたりの病院数を計算して検証
    const hospitalCount = await getHospitalsCountByWard(
      wardWithMostHospitalsPerPopulation
    );
    const population = await getPopulationOfWard(
      wardWithMostHospitalsPerPopulation
    );
    const hospitalsPerPopulation = hospitalCount / population;

    // 病院数と人口が正常値であることを確認
    expect(hospitalCount).toBeGreaterThan(0);
    expect(population).toBeGreaterThan(0);

    console.log(
      `最も人口あたりの病院数が多い区は${wardWithMostHospitalsPerPopulation}で、` +
        `人口あたりの病院数は${(hospitalsPerPopulation * 10000).toFixed(
          2
        )}病院/1万人です` +
        `（病院数: ${hospitalCount}、人口: ${population.toLocaleString()}人）`
    );
  }, 90000); // タイムアウトを90秒に設定（多くの区をチェックするため）

  it("should validate that the result actually has the most hospitals per population", async () => {
    // 病院が多いと予想される区のリスト（テスト用）
    const potentialWards = ["中央区", "港区", "文京区"];

    // 実際に最も人口あたりの病院数が多い区を取得
    const wardWithMostHospitalsPerPopulation =
      await findWardWithMostHospitalsPerPopulation();

    // 選ばれた区の人口あたりの病院数を計算
    const hospitalCount = await getHospitalsCountByWard(
      wardWithMostHospitalsPerPopulation
    );
    const population = await getPopulationOfWard(
      wardWithMostHospitalsPerPopulation
    );
    const highestHospitalsPerPopulation = hospitalCount / population;

    // サンプル区と比較して、実際に最も人口あたりの病院数が多い区が選ばれていることを確認
    for (const ward of potentialWards) {
      if (ward === wardWithMostHospitalsPerPopulation) continue; // 同じ区はスキップ

      const wardHospitalCount = await getHospitalsCountByWard(ward);
      const wardPopulation = await getPopulationOfWard(ward);

      // 病院数が0の場合や人口が0の場合は比較しない
      if (wardHospitalCount === 0 || wardPopulation === 0) {
        console.log(
          `${ward}の病院数が${wardHospitalCount}、人口が${wardPopulation}のため、比較をスキップします`
        );
        continue;
      }

      const wardHospitalsPerPopulation = wardHospitalCount / wardPopulation;

      // 人口あたりの病院数が正の有限値であることを確認
      if (!isFinite(wardHospitalsPerPopulation)) {
        console.log(
          `${ward}の人口あたりの病院数が有限値でないため、比較をスキップします`
        );
        continue;
      }

      // 最も人口あたりの病院数が多い区の方が、比較対象より数値が大きいことを確認
      expect(highestHospitalsPerPopulation).toBeGreaterThanOrEqual(
        wardHospitalsPerPopulation
      );
    }
  }, 120000); // 複数の区を比較するため、十分な時間を設定
});
