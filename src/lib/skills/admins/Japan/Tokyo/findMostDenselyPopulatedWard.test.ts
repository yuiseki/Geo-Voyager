import { findMostDenselyPopulatedWard } from "./findMostDenselyPopulatedWard";
import { getPopulationOfWard } from "./ward/getPopulationOfWard";
import { getAreaOfWard } from "./ward/getAreaOfWard";

describe("findMostDenselyPopulatedWard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should find the most densely populated ward in Tokyo", async () => {
    // 実際に人口密度が最も高い区を取得
    const mostDenseWard = await findMostDenselyPopulatedWard();

    // 結果が文字列であることを確認
    expect(typeof mostDenseWard).toBe("string");

    // 結果が空でないことを確認
    expect(mostDenseWard.length).toBeGreaterThan(0);

    // 人口密度を計算して検証
    const population = await getPopulationOfWard(mostDenseWard);
    const area = await getAreaOfWard(mostDenseWard);
    const density = population / area;

    // 人口密度が高いことを検証
    // 東京都の人口密度の高い区は1万人/km²以上のはず
    expect(density).toBeGreaterThan(10000);

    console.log(
      `最も人口密度が高い区は${mostDenseWard}で、人口密度は${density.toFixed(
        2
      )}人/km²です（人口: ${population}人、面積: ${area.toFixed(2)}km²）`
    );
  }, 90000); // タイムアウトを90秒に設定（多くの区をチェックするため）

  it("should validate that the result is actually the most dense ward", async () => {
    // 人口密度が高いと予想される区のリスト（テスト用）
    const denseWards = ["豊島区", "中野区", "荒川区", "台東区"];

    // 実際に最も人口密度が高い区を取得
    const mostDenseWard = await findMostDenselyPopulatedWard();

    // 選ばれた区の人口密度を計算
    const population = await getPopulationOfWard(mostDenseWard);
    const area = await getAreaOfWard(mostDenseWard);
    const highestDensity = population / area;

    // サンプル区と比較して、実際に最も高い区が選ばれていることを確認
    for (const ward of denseWards) {
      if (ward === mostDenseWard) continue; // 同じ区はスキップ

      const wardPopulation = await getPopulationOfWard(ward);
      const wardArea = await getAreaOfWard(ward);
      const wardDensity = wardPopulation / wardArea;

      console.log(
        `${ward}の人口密度: ${wardDensity.toFixed(
          2
        )}人/km²（人口: ${wardPopulation}人、面積: ${wardArea.toFixed(2)}km²）`
      );

      // 最も人口密度が高い区の方が、比較対象より人口密度が高いことを確認
      expect(highestDensity).toBeGreaterThanOrEqual(wardDensity);
    }
  }, 120000); // 複数の区を比較するため、十分な時間を設定
});
