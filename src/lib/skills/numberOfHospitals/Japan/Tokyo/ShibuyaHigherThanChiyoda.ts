// description: 東京都渋谷区の病院の数が東京都千代田区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfHospitals/Japan/Tokyo/ShibuyaHigherThanChiyoda.ts

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

  const data = await response.json();
  return data.elements[0].tags.total;
}

/**
 * Compares the number of hospitals in Shibuya and Chiyoda districts.
 * @returns True if Shibuya has more hospitals than Chiyoda, otherwise false.
 */
async function isNumberOfHospitalsInShibuyaHigherThanChiyoda(): Promise<boolean> {
  const shibuyaHospitalCount = await getHospitalCount('渋谷区');
  const chiyodaHospitalCount = await getHospitalCount('千代田区');

  return shibuyaHospitalCount > chiyodaHospitalCount;
}

export default isNumberOfHospitalsInShibuyaHigherThanChiyoda;