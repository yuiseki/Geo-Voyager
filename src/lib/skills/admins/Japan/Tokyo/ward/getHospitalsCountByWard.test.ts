import { getHospitalsCountByWard } from "./getHospitalsCountByWard";

describe("getHospitalsCountByWard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should fetch real hospital count data from Overpass API", async () => {
    // テスト対象の区
    const wardName = "新宿区";

    // 実際のAPIを使用して病院数を取得
    const hospitalCount = await getHospitalsCountByWard(wardName);

    // 病院数は数値であることを確認
    expect(typeof hospitalCount).toBe("number");

    // 新宿区には複数の病院があるはず
    expect(hospitalCount).toBeGreaterThan(0);
  }, 30000);

  it("should return different hospital counts for different wards", async () => {
    // 2つの異なる区で比較
    const shinjukuHospitalCount = await getHospitalsCountByWard("新宿区");
    const shibuyaHospitalCount = await getHospitalsCountByWard("渋谷区");

    // 病院数は数値であることを確認
    expect(typeof shinjukuHospitalCount).toBe("number");
    expect(typeof shibuyaHospitalCount).toBe("number");

    // 両方とも病院があるはず
    expect(shinjukuHospitalCount).toBeGreaterThan(0);
    expect(shibuyaHospitalCount).toBeGreaterThan(0);

    // 異なる区なので病院数も異なる可能性が高い
    // (完全に同じ数である可能性は低いため)
    expect(shinjukuHospitalCount).not.toEqual(shibuyaHospitalCount);
  }, 30000);
});
