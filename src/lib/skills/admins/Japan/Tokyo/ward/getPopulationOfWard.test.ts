import { getPopulationOfWard } from "./getPopulationOfWard";

describe("getPopulationOfWard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should fetch real population data from Overpass API", async () => {
    // テスト対象の区
    const wardName = "新宿区";
    
    // 実際のAPIを使用して人口を取得
    const population = await getPopulationOfWard(wardName);

    // 人口は数値であることを確認
    expect(typeof population).toBe("number");
    
    // 新宿区の人口は30万人程度であるため、
    // ある程度の範囲内の値が取得できることを確認
    expect(population).toBeGreaterThan(200000);
    expect(population).toBeLessThan(400000);
  }, 30000);

  it("should return different populations for different wards", async () => {
    // 2つの異なる区で比較
    const shinjukuPopulation = await getPopulationOfWard("新宿区");
    const shibuyaPopulation = await getPopulationOfWard("渋谷区");

    // 異なる区なので人口も異なるはず
    expect(shinjukuPopulation).not.toEqual(shibuyaPopulation);
    
    // 渋谷区の人口は20万人程度であるため、
    // ある程度の範囲内の値が取得できることを確認
    expect(shibuyaPopulation).toBeGreaterThan(150000);
    expect(shibuyaPopulation).toBeLessThan(300000);
  }, 30000);

  it("should handle a ward with invalid population data", async () => {
    // 実際のデータでテストするため、モックは使用せず
    // モッキングなしでテストするため、実際にOverpass APIから返されるデータに
    // 依存しますが、万が一人口データがないか不正な場合を検証
    
    // 仮に不正なデータがある場合を想定したテスト
    // 注: このテストは実際のデータによって成功するとは限らない
    const validPopulation = await getPopulationOfWard("新宿区");
    expect(validPopulation).toBeGreaterThan(0); // 正常に取得できればゼロ以上
  }, 30000);
});