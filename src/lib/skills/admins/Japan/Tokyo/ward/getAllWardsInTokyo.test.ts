import { getAllWardsInTokyo } from "./getAllWardsInTokyo";

describe("getAllWardsInTokyo", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should fetch real data from Overpass API", async () => {
    // Call the function with real API
    const wards = await getAllWardsInTokyo();

    // Just verify we got some data (not empty)
    expect(wards.length).toBeGreaterThan(0);
    // 東京には67の自治体があるはず
    expect(wards.length).toBe(67);
    // 特定の区が含まれているか確認
    expect(wards).toContain("新宿区");
    expect(wards).toContain("渋谷区");
    expect(wards).toContain("豊島区");
  }, 30000);
});
