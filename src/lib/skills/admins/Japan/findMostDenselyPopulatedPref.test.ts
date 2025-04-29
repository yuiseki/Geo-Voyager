import findMostDenselyPopulatedPref from "./findMostDenselyPopulatedPref";
import { getEStatLatestPopulationOfPrefs } from "../../../common/getEStatLatestPopulationOfPrefs";
import { getPopulationDensityByPrefOnlyLandMask } from "../../../common/getPopulationDensityByPrefOnlyLandMask";

describe("findMostDenselyPopulatedPref", () => {
  it("should defined process.env.E_STAT_APP_ID", async () => {
    
    expect(process.env.E_STAT_APP_ID).toBeDefined();
  })
  it("should find the most densely populated prefecture in Japan", async () => {
    // 実際の関数を実行（環境変数 E_STAT_APP_ID を使用）
    const result = await findMostDenselyPopulatedPref();

    // 結果が文字列であることを確認
    expect(typeof result).toBe("string");

    // 都道府県名が空ではないことを確認
    expect(result.length).toBeGreaterThan(0);

    // 実際の人口データを取得
    const prefs = await getEStatLatestPopulationOfPrefs();
    
    // 結果の都道府県の人口密度を取得
    const resultPopulation = prefs[result];
    const resultDensity = await getPopulationDensityByPrefOnlyLandMask(
      result,
      resultPopulation
    );

    // 結果の都道府県が実際に高い人口密度を持っていることを確認
    expect(resultDensity).toBeGreaterThan(1000); // 1平方km当たり1000人以上が期待される

    // 結果を出力
    console.log(
      `日本で最も人口密度が高い都道府県は${result}で、人口密度は${resultDensity.toFixed(
        2
      )}人/km²です（人口: ${resultPopulation.toLocaleString()}人）`
    );
  }, 300000); // タイムアウトを5分に設定（API呼び出しとキャッシュ機構の時間を考慮）

  it("should return a prefecture from Japan", async () => {
    const result = await findMostDenselyPopulatedPref();
    
    // 日本の有効な都道府県名リスト
    const validPrefectures = [
      "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
      "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
      "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
      "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
      "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
      "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
      "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
    ];
    
    // 結果が有効な都道府県名リストに含まれていることを確認
    expect(validPrefectures).toContain(result);
  });
});