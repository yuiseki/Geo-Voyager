// description: 東京都港区の学校の数が東京都新宿区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/MinatoHigherThanShinjuku.ts

/**
 * @returns boolean
 */
const isNumberOfSchoolsInChiyodaHigherThanShinjuku = async () => {
  /**
   *
   * @param query Overpass QL
   * @returns Overpass API JSON
   */
  const fetchOverpassData = async (query: string): Promise<any> => {
    const endpoint = "https://overpass-api.de/api/interpreter";
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: `data=${encodeURIComponent(query)}`,
    });
    return await res.json();
  };

  // 東京都港区の学校の数を取得
  const queryMinatoSchools = `[out:json];
area["name"="東京都"]->.outer;
area["name"="港区"]->.inner;
nwr["amenity"="school"](area.inner)(area.outer);
out count;`;
  const resultMinatoSchools = await fetchOverpassData(queryMinatoSchools);
  if (resultMinatoSchools.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryMinatoSchools}`
    );
  }
  const numberOfMinatoSchools = resultMinatoSchools.elements[0].tags.total;

  // 東京都新宿区の学校の面積を取得
  const queryShinjukuSchools = `[out:json];
area["name"="東京都"]->.outer;
area["name"="新宿区"]->.inner;
nwr["amenity"="school"](area.inner)(area.outer);
out count;`;
  const resultShinjukuSchools = await fetchOverpassData(queryShinjukuSchools);
  if (resultShinjukuSchools.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryShinjukuSchools}`
    );
  }
  const numberOfShinjukuSchools = resultShinjukuSchools.elements[0].tags.total;

  // 学校の数を比較
  return numberOfMinatoSchools > numberOfShinjukuSchools;
};

export default isNumberOfSchoolsInChiyodaHigherThanShinjuku;
