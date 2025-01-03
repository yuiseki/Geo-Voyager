// description: 東京都文京区の学校の数が東京都江東区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/BunkyoHigherThanKoto.ts

import fetch from 'node-fetch';

/**
 * Fetches the number of schools in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of schools in the ward.
 */
async function getSchoolCount(wardName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area["name"="東京都"]->.tokyo;
    area["name"="${wardName}"]->.ward;
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
  return result.elements[0].tags.total;
}

/**
 * Compares the number of schools in Bunkyo Ward and Koto Ward.
 * @returns True if Bunkyo Ward has more schools than Koto Ward, otherwise false.
 */
async function isBunkyoHigherThanKoto(): Promise<boolean> {
  const bunkyoSchoolCount = await getSchoolCount("文京区");
  const kotoSchoolCount = await getSchoolCount("江東区");

  console.log(`Number of schools in Bunkyo Ward: ${bunkyoSchoolCount}`);
  console.log(`Number of schools in Koto Ward: ${kotoSchoolCount}`);

  return bunkyoSchoolCount > kotoSchoolCount;
}

export default isBunkyoHigherThanKoto;