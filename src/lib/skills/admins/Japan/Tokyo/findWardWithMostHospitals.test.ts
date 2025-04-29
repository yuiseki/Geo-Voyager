import { findWardWithMostHospitals } from "./findWardWithMostHospitals";
import { fetchOverpassData } from "../../../common/fetchOverpassData";

describe("findWardWithMostHospitals", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 実際のAPIリクエストを使用するテスト
  it("should find the ward with the most hospitals in Tokyo", async () => {
    // 実際に病院が最も多い区を取得
    const wardWithMostHospitals = await findWardWithMostHospitals();

    // 結果が文字列であることを確認
    expect(typeof wardWithMostHospitals).toBe("string");

    // 結果が空でないことを確認
    expect(wardWithMostHospitals.length).toBeGreaterThan(0);

    // 病院の数を確認するためのOverpassクエリ
    const overpassQuery = `
[out:json];
area["name"="東京都"]->.out;
area["name"="${wardWithMostHospitals}"]->.in;
(
  nwr["amenity"="hospital"](area.in)(area.out);
);
out count;
`;

    // 実際に取得した区の病院数を確認
    const response = await fetchOverpassData(overpassQuery);
    const hospitalCount = parseInt(response.elements[0].tags.total);

    // 病院の数が一定数以上あることを確認
    expect(hospitalCount).toBeGreaterThan(10);

    console.log(
      `最も病院が多い区は${wardWithMostHospitals}で、病院数は${hospitalCount}です`
    );
  }, 90000); // タイムアウトを90秒に設定（多くの区をチェックするため）

  it("should validate that the result actually has the most hospitals", async () => {
    // 病院が多いと予想される区のリスト（テスト用）
    const potentialWards = ["新宿区", "港区", "世田谷区", "大田区"];

    // 実際に最も病院が多い区を取得
    const wardWithMostHospitals = await findWardWithMostHospitals();

    // 選ばれた区の病院数を取得
    const mostHospitalsQuery = `
[out:json];
area["name"="東京都"]->.out;
area["name"="${wardWithMostHospitals}"]->.in;
(
  nwr["amenity"="hospital"](area.in)(area.out);
);
out count;
`;

    const mostHospitalsResponse = await fetchOverpassData(mostHospitalsQuery);
    const highestHospitalCount = parseInt(
      mostHospitalsResponse.elements[0].tags.total
    );

    // サンプル区と比較して、実際に最も病院が多い区が選ばれていることを確認
    for (const ward of potentialWards) {
      if (ward === wardWithMostHospitals) continue; // 同じ区はスキップ

      const wardQuery = `
[out:json];
area["name"="東京都"]->.out;
area["name"="${ward}"]->.in;
(
  nwr["amenity"="hospital"](area.in)(area.out);
);
out count;
`;

      const wardResponse = await fetchOverpassData(wardQuery);
      const wardHospitalCount = parseInt(wardResponse.elements[0].tags.total);

      // 最も病院が多い区の方が、比較対象より病院が多いことを確認
      expect(highestHospitalCount).toBeGreaterThanOrEqual(wardHospitalCount);
    }
  }, 120000); // 複数の区を比較するため、十分な時間を設定
});
