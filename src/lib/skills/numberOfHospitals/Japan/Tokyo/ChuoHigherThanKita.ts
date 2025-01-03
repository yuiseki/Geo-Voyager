// description: 東京都中央区の病院の数が東京都北区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfHospitals/Japan/Tokyo/ChuoHigherThanKita.ts

/**
 * @returns boolean
 */
const isNumberOfHospitalsInChuoHigherThanKita = async () => {
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

  // 東京都中央区の病院の数を取得
  const queryChuoHospitals = `[out:json];
area["name"="東京都"]->.outer;
area["name"="中央区"]->.inner;
nwr["amenity"="hospital"](area.inner)(area.outer);
out count;`;
  const resultChuoHospitals = await fetchOverpassData(queryChuoHospitals);
  if (resultChuoHospitals.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryChuoHospitals}`
    );
  }
  const numberOfChuoHospitals = resultChuoHospitals.elements[0].tags.total;

  // 東京都北区の病院の数を取得
  const queryKitaHospitals = `[out:json];
area["name"="東京都"]->.outer;
area["name"="北区"]->.inner;
nwr["amenity"="hospital"](area.inner)(area.outer);
out count;`;
  const resultKitaHospitals = await fetchOverpassData(queryKitaHospitals);
  if (resultKitaHospitals.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryKitaHospitals}`
    );
  }
  const numberOfKitaHospitals = resultKitaHospitals.elements[0].tags.total;

  // 病院の数を比較
  return numberOfChuoHospitals > numberOfKitaHospitals;
};

export default isNumberOfHospitalsInChuoHigherThanKita;
