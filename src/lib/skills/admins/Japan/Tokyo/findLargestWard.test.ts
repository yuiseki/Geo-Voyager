import { findLargestWard } from "./findLargestWard";
import { getAreaOfWard } from "./ward/getAreaOfWard";

describe("findLargestWard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should find the ward with the largest area in Tokyo", async () => {
    // 実際に最大の区を取得
    const largestWard = await findLargestWard();

    // 結果が文字列であることを確認
    expect(typeof largestWard).toBe("string");

    // 結果が空でないことを確認
    expect(largestWard.length).toBeGreaterThan(0);

    // 面積を取得して検証
    const area = await getAreaOfWard(largestWard);

    // 実際に最大の区が特定できていることを検証
    // 大田区（約60km²）や世田谷区（約58km²）など大きな区と一致するはず
    expect(area).toBeGreaterThan(50); // 50km²以上の区が最大のはず

    console.info(`最も面積が広い区は${largestWard}で、面積は${area}km²です`);
  }, 60000); // タイムアウトを60秒に設定（多くの区をチェックするため）

  it("should return a ward that actually exists in Tokyo", async () => {
    const largestWard = await findLargestWard();

    // 東京の主要な区のリスト
    const majorWards = [
      "千代田区",
      "中央区",
      "港区",
      "新宿区",
      "文京区",
      "台東区",
      "墨田区",
      "江東区",
      "品川区",
      "目黒区",
      "大田区",
      "世田谷区",
      "渋谷区",
      "中野区",
      "杉並区",
      "豊島区",
      "北区",
      "荒川区",
      "板橋区",
      "練馬区",
      "足立区",
      "葛飾区",
      "江戸川区",
    ];

    // 結果が実際の区の中に含まれていることを確認
    expect(majorWards).toContain(largestWard);
  }, 60000);
});
