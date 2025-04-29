import { getLibrariesCountByWard } from "./getLibrariesCountByWard";

describe("getLibrariesCountByWard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should fetch real library count data from Overpass API", async () => {
    // テスト対象の区
    const wardName = "新宿区";

    // 実際のAPIを使用して図書館数を取得
    const libraryCount = await getLibrariesCountByWard(wardName);

    // 図書館数は数値であることを確認
    expect(typeof libraryCount).toBe("number");

    // 新宿区には複数の図書館があるはず
    expect(libraryCount).toBeGreaterThan(0);
  }, 30000);

  it("should return different library counts for different wards", async () => {
    // 2つの異なる区で比較
    const shinjukuLibraryCount = await getLibrariesCountByWard("新宿区");
    const shibuyaLibraryCount = await getLibrariesCountByWard("渋谷区");

    // 図書館数は数値であることを確認
    expect(typeof shinjukuLibraryCount).toBe("number");
    expect(typeof shibuyaLibraryCount).toBe("number");

    // 両方とも図書館があるはず
    expect(shinjukuLibraryCount).toBeGreaterThan(0);
    expect(shibuyaLibraryCount).toBeGreaterThan(0);

    // 異なる区なので図書館数も異なる可能性が高い
    // (完全に同じ数である可能性は低いため)
    expect(shinjukuLibraryCount).not.toEqual(shibuyaLibraryCount);
  }, 30000);
});
