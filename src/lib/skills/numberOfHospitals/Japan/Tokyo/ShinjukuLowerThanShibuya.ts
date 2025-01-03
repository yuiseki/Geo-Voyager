// description: 東京都新宿区の病院の数が東京都渋谷区よりも少ないことを確認する。
// file_path: src/lib/skills/numberOfHospitals/Japan/Tokyo/ShinjukuLowerThanShibuya.ts

import fetch from 'node-fetch';

/**
 * Fetches the number of hospitals in a specified area using Overpass API.
 * @param areaName - The name of the area to query.
 * @returns The count of hospitals in the specified area.
 */
async function getHospitalCount(areaName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area[name="${areaName}"]->.searchArea;
    (
      node[amenity=hospital](area.searchArea);
      way[amenity=hospital](area.searchArea);
      relation[amenity=hospital](area.searchArea);
    );
    out count;
  `;

  const response = await fetch('https://overpass-api.de/api/interpreter', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
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
 * Compares the number of hospitals in Shinjuku and Shibuya wards of Tokyo.
 * @returns A boolean indicating whether Shinjuku has fewer hospitals than Shibuya.
 */
async function isShinjukuLowerThanShibuya(): Promise<boolean> {
  const shinjukuCount = await getHospitalCount('新宿区');
  const shibuyaCount = await getHospitalCount('渋谷区');

  console.log(`Number of hospitals in Shinjuku: ${shinjukuCount}`);
  console.log(`Number of hospitals in Shibuya: ${shibuyaCount}`);

  return shinjukuCount < shibuyaCount;
}

export default isShinjukuLowerThanShibuya;