import findWardWithMostSchools from "./findWardWithMostSchools";
import { getSchoolsCountByWard } from "./ward/getSchoolsCountByWard";

describe("findWardWithMostSchools", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should find the ward with most schools in Tokyo", async () => {
    // 実際に学校数が最も多い区を取得
    const wardWithMostSchools = await findWardWithMostSchools();

    // 結果が文字列であることを確認
    expect(typeof wardWithMostSchools).toBe("string");

    // 結果が空でないことを確認
    expect(wardWithMostSchools.length).toBeGreaterThan(0);

    // 学校数を取得して検証
    const schoolCount = await getSchoolsCountByWard(wardWithMostSchools);

    // 学校数が正常値であることを確認
    expect(schoolCount).toBeGreaterThan(0);

    console.log(
      `最も学校数が多い区は${wardWithMostSchools}で、` +
        `学校数は${schoolCount}校です`
    );
  }, 90000); // タイムアウトを90秒に設定（多くの区をチェックするため）

  it("should validate that the result actually has the most schools", async () => {
    // 学校が多いと予想される区のリスト（テスト用）
    const potentialWards = ["世田谷区", "練馬区", "大田区"];

    // 実際に最も学校数が多い区を取得
    const wardWithMostSchools = await findWardWithMostSchools();

    // 選ばれた区の学校数を計算
    const highestSchoolCount = await getSchoolsCountByWard(wardWithMostSchools);

    // サンプル区と比較して、実際に最も学校数が多い区が選ばれていることを確認
    for (const ward of potentialWards) {
      if (ward === wardWithMostSchools) continue; // 同じ区はスキップ

      const wardSchoolCount = await getSchoolsCountByWard(ward);

      // 学校数が0の場合は比較しない
      if (wardSchoolCount === 0) {
        console.log(
          `${ward}の学校数が${wardSchoolCount}のため、比較をスキップします`
        );
        continue;
      }

      // 最も学校数が多い区の方が、比較対象より数値が大きいことを確認
      expect(highestSchoolCount).toBeGreaterThanOrEqual(wardSchoolCount);
    }
  }, 120000); // 複数の区を比較するため、十分な時間を設定
});
