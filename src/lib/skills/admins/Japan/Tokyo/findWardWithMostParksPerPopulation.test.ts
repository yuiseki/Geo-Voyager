import { findWardWithMostParksPerPopulation } from "./findWardWithMostParksPerPopulation";
import { getParkCountByWard } from "./ward/getParkCountByWard";
import { getPopulationOfWard } from "./ward/getPopulationOfWard";

describe("findWardWithMostParksPerPopulation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should find the ward with most parks per population in Tokyo", async () => {
    // 実際に人口あたりの公園数が最も多い区を取得
    const wardWithMostParksPerPopulation =
      await findWardWithMostParksPerPopulation();

    // 結果が文字列であることを確認
    expect(typeof wardWithMostParksPerPopulation).toBe("string");

    // 結果が空でないことを確認
    expect(wardWithMostParksPerPopulation.length).toBeGreaterThan(0);

    // 人口あたりの公園数を計算して検証
    const parkCount = await getParkCountByWard(wardWithMostParksPerPopulation);
    const population = await getPopulationOfWard(
      wardWithMostParksPerPopulation
    );
    const parksPerPopulation = parkCount / population;

    // 公園数と人口が正常値であることを確認
    expect(parkCount).toBeGreaterThan(0);
    expect(population).toBeGreaterThan(0);

    console.log(
      `最も人口あたりの公園数が多い区は${wardWithMostParksPerPopulation}で、` +
        `人口あたりの公園数は${(parksPerPopulation * 10000).toFixed(
          2
        )}公園/1万人です` +
        `（公園数: ${parkCount}、人口: ${population.toLocaleString()}人）`
    );
  }, 90000); // タイムアウトを90秒に設定（多くの区をチェックするため）

  it("should validate that the result actually has the most parks per population", async () => {
    // 公園が多いと予想される区のリスト（テスト用）
    const potentialWards = ["世田谷区", "大田区", "文京区"];

    // 実際に最も人口あたりの公園数が多い区を取得
    const wardWithMostParksPerPopulation =
      await findWardWithMostParksPerPopulation();

    // 選ばれた区の人口あたりの公園数を計算
    const parkCount = await getParkCountByWard(wardWithMostParksPerPopulation);
    const population = await getPopulationOfWard(
      wardWithMostParksPerPopulation
    );
    const highestParksPerPopulation = parkCount / population;

    // サンプル区と比較して、実際に最も人口あたりの公園数が多い区が選ばれていることを確認
    for (const ward of potentialWards) {
      if (ward === wardWithMostParksPerPopulation) continue; // 同じ区はスキップ

      const wardParkCount = await getParkCountByWard(ward);
      const wardPopulation = await getPopulationOfWard(ward);

      // 公園数が0の場合や人口が0の場合は比較しない
      if (wardParkCount === 0 || wardPopulation === 0) {
        console.log(
          `${ward}の公園数が${wardParkCount}、人口が${wardPopulation}のため、比較をスキップします`
        );
        continue;
      }

      const wardParksPerPopulation = wardParkCount / wardPopulation;

      // 人口あたりの公園数が正の有限値であることを確認
      if (!isFinite(wardParksPerPopulation)) {
        console.log(
          `${ward}の人口あたりの公園数が有限値でないため、比較をスキップします`
        );
        continue;
      }

      // 最も人口あたりの公園数が多い区の方が、比較対象より数値が大きいことを確認
      expect(highestParksPerPopulation).toBeGreaterThanOrEqual(
        wardParksPerPopulation
      );
    }
  }, 120000); // 複数の区を比較するため、十分な時間を設定
});
