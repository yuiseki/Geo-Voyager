import { findWardWithMostLibrariesPerPopulation } from "./findWardWithMostLibrariesPerPopulation";
import { getLibrariesCountByWard } from "./ward/getLibrariesCountByWard";
import { getPopulationOfWard } from "./ward/getPopulationOfWard";

describe("findWardWithMostLibrariesPerPopulation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should find the ward with most libraries per population in Tokyo", async () => {
    // 実際に人口あたりの図書館数が最も多い区を取得
    const wardWithMostLibrariesPerPopulation =
      await findWardWithMostLibrariesPerPopulation();

    // 結果が文字列であることを確認
    expect(typeof wardWithMostLibrariesPerPopulation).toBe("string");

    // 結果が空でないことを確認
    expect(wardWithMostLibrariesPerPopulation.length).toBeGreaterThan(0);

    // 人口あたりの図書館数を計算して検証
    const libraryCount = await getLibrariesCountByWard(
      wardWithMostLibrariesPerPopulation
    );
    const population = await getPopulationOfWard(
      wardWithMostLibrariesPerPopulation
    );
    const librariesPerPopulation = libraryCount / population;

    // 図書館数と人口が正常値であることを確認
    expect(libraryCount).toBeGreaterThan(0);
    expect(population).toBeGreaterThan(0);

    console.log(
      `最も人口あたりの図書館数が多い区は${wardWithMostLibrariesPerPopulation}で、` +
        `人口あたりの図書館数は${(librariesPerPopulation * 10000).toFixed(
          2
        )}図書館/1万人です` +
        `（図書館数: ${libraryCount}、人口: ${population.toLocaleString()}人）`
    );
  }, 90000); // タイムアウトを90秒に設定（多くの区をチェックするため）

  it("should validate that the result actually has the most libraries per population", async () => {
    // 図書館が多いと予想される区のリスト（テスト用）
    const potentialWards = ["中央区", "文京区", "台東区"];

    // 実際に最も人口あたりの図書館数が多い区を取得
    const wardWithMostLibrariesPerPopulation =
      await findWardWithMostLibrariesPerPopulation();

    // 選ばれた区の人口あたりの図書館数を計算
    const libraryCount = await getLibrariesCountByWard(
      wardWithMostLibrariesPerPopulation
    );
    const population = await getPopulationOfWard(
      wardWithMostLibrariesPerPopulation
    );
    const highestLibrariesPerPopulation = libraryCount / population;

    // サンプル区と比較して、実際に最も人口あたりの図書館数が多い区が選ばれていることを確認
    for (const ward of potentialWards) {
      if (ward === wardWithMostLibrariesPerPopulation) continue; // 同じ区はスキップ

      const wardLibraryCount = await getLibrariesCountByWard(ward);
      const wardPopulation = await getPopulationOfWard(ward);

      // 図書館数が0の場合や人口が0の場合は比較しない
      if (wardLibraryCount === 0 || wardPopulation === 0) {
        console.log(
          `${ward}の図書館数が${wardLibraryCount}、人口が${wardPopulation}のため、比較をスキップします`
        );
        continue;
      }

      const wardLibrariesPerPopulation = wardLibraryCount / wardPopulation;

      // 人口あたりの図書館数が正の有限値であることを確認
      if (!isFinite(wardLibrariesPerPopulation)) {
        console.log(
          `${ward}の人口あたりの図書館数が有限値でないため、比較をスキップします`
        );
        continue;
      }

      // 最も人口あたりの図書館数が多い区の方が、比較対象より数値が大きいことを確認
      expect(highestLibrariesPerPopulation).toBeGreaterThanOrEqual(
        wardLibrariesPerPopulation
      );
    }
  }, 120000); // 複数の区を比較するため、十分な時間を設定
});
