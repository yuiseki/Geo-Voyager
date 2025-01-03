// description: 東京都大田区の学校の数が東京都千代田区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/OtaHigherThanChiyoda.ts

/**
 * Fetches the number of schools in a specified area using Overpass API.
 * @param areaName - The name of the area to query.
 * @returns The count of schools in the specified area.
 */
async function getSchoolCount(areaName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area[name="${areaName}"]->.searchArea;
    (
      node[amenity=school](area.searchArea);
      way[amenity=school](area.searchArea);
      relation[amenity=school](area.searchArea);
    );
    out count;
  `;

  const response = await fetch("https://overpass-api.de/api/interpreter", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `data=${encodeURIComponent(overpassQuery)}`,
  });

  if (!response.ok) {
    throw new Error(
      `Failed to fetch data from Overpass API: ${response.statusText}`
    );
  }

  const data = await response.json();

  if (data.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${overpassQuery}`
    );
  }

  return data.elements[0].tags.total;
}

/**
 * Compares the number of schools in Ota and Chiyoda districts.
 * @returns True if Ota has more schools than Chiyoda, otherwise false.
 */
async function isNumberOfSchoolsInOtaHigherThanChiyoda(): Promise<boolean> {
  const otaSchoolCount = await getSchoolCount("大田区");
  const chiyodaSchoolCount = await getSchoolCount("千代田区");

  return otaSchoolCount > chiyodaSchoolCount;
}

export default isNumberOfSchoolsInOtaHigherThanChiyoda;