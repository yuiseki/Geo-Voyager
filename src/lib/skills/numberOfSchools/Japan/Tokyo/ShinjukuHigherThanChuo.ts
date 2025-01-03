// description: 東京都新宿区の学校の数が東京都中央区の学校の数よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/ShinjukuHigherThanChuo.ts

/**
 * Fetches the number of schools in a specified area using Overpass API.
 * @param areaName - The name of the area to query.
 * @returns The count of schools in the specified area.
 */
async function getSchoolCount(areaName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area["name"="東京都"]->.tokyo;
    area["name"="${areaName}"]->.ward;
    (
      nwr["amenity"="school"](area.ward)(area.tokyo);
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

  const result = await response.json();

  if (result.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${overpassQuery}`
    );
  }

  return result.elements[0].tags.total;
}

/**
 * Compares the number of schools in Shinjuku and Chuo wards.
 * @returns A boolean indicating whether Shinjuku has more schools than Chuo.
 */
async function isShinjukuHigherThanChuo(): Promise<boolean> {
  const shinjukuSchoolCount = await getSchoolCount("新宿区");
  const chuoSchoolCount = await getSchoolCount("中央区");

  console.log(`Number of schools in 新宿区: ${shinjukuSchoolCount}`);
  console.log(`Number of schools in 中央区: ${chuoSchoolCount}`);

  return shinjukuSchoolCount > chuoSchoolCount;
}

// Export the function to be used as a skill
export default isShinjukuHigherThanChuo;
