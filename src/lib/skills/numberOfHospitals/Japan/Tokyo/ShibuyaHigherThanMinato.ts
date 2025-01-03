// description: 東京都渋谷区の病院の数が東京都港区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfHospitals/Japan/Tokyo/ShibuyaHigherThanMinato.ts

import fetch from 'node-fetch';

/**
 * Fetches the number of hospitals in a specified area using Overpass API.
 * @param areaName - The name of the area to query.
 * @returns The count of hospitals in the specified area.
 */
async function getHospitalCount(areaName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area[name="東京都"]->.tokyo;
    area[name="${areaName}"]->.searchArea;
    (
        nwr["amenity"="hospital"](area.searchArea)(area.tokyo);
    );
    out count;
  `;

  const response = await fetch("https://overpass-api.de/api/interpreter", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `data=${encodeURIComponent(overpassQuery)}`,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch data from Overpass API: ${response.statusText}`);
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
 * Compares the number of hospitals in Shibuya and Minato wards of Tokyo.
 * @returns A boolean indicating whether Shibuya has more hospitals than Minato.
 */
async function isShibuyaHigherThanMinato(): Promise<boolean> {
  const shibuyaCount = await getHospitalCount("渋谷区");
  const minatoCount = await getHospitalCount("港区");

  console.log(`Number of hospitals in Shibuya: ${shibuyaCount}`);
  console.log(`Number of hospitals in Minato: ${minatoCount}`);

  return shibuyaCount > minatoCount;
}

export default isShibuyaHigherThanMinato;