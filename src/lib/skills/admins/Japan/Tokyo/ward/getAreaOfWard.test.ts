import { getAreaOfWard } from "./getAreaOfWard";

describe("getAreaOfWard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should fetch real area data from Overpass API", async () => {
    // テスト対象の区
    const wardName = "新宿区";
    
    // 実際のAPIを使用して面積を取得
    const area = await getAreaOfWard(wardName);

    // 面積は数値であることを確認
    expect(typeof area).toBe("number");
    
    // 新宿区の面積は約18.22 km²であるため、
    // その付近の値が取得できることを確認（誤差を許容）
    expect(area).toBeGreaterThan(17);
    expect(area).toBeLessThan(20);
  }, 30000);

  it("should return different areas for different wards", async () => {
    // 2つの異なる区で比較
    const shinjukuArea = await getAreaOfWard("新宿区");
    const shibuyaArea = await getAreaOfWard("渋谷区");

    // 異なる区なので面積も異なるはず
    expect(shinjukuArea).not.toEqual(shibuyaArea);
    
    // 渋谷区の面積は約15.11 km²であるため、
    // その付近の値が取得できることを確認
    expect(shibuyaArea).toBeGreaterThan(14);
    expect(shibuyaArea).toBeLessThan(16);
  }, 30000);
});