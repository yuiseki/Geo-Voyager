// description: 東京都渋谷区の病院の数が東京都新宿区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfHospitals/Japan/Tokyo/ShibuyaHigherThanShinjuku.ts

import fetch from 'node-fetch';

/**
 * Fetches the number of hospitals in a specified area using Overpass API.
 * @param areaName - The name of the area to query.
 * @returns The count of hospitals in the specified area.
 */
async function getNumberOfHospitals(areaName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area["name"="${areaName}"]->.searchArea;
    (
      node["amenity"="hospital"](area.searchArea);
      way["amenity"="hospital"](area.searchArea);
      relation["amenity"="hospital"](area.searchArea);
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
  return result.elements[0].tags.total;
}

/**
 * Compares the number of hospitals in Shibuya and Shinjuku districts.
 * @returns True if Shibuya has more hospitals than Shinjuku, otherwise false.
 */
async function isNumberOfHospitalsInShibuyaHigherThanShinjuku(): Promise<boolean> {
  const numberOfHospitalsInShibuya = await getNumberOfHospitals('渋谷区');
  const numberOfHospitalsInShinjuku = await getNumberOfHospitals('新宿区');

  console.log(`Number of hospitals in Shibuya: ${numberOfHospitalsInShibuya}`);
  console.log(`Number of hospitals in Shinjuku: ${numberOfHospitalsInShinjuku}`);

  return numberOfHospitalsInShibuya > numberOfHospitalsInShinjuku;
}

export default isNumberOfHospitalsInShibuyaHigherThanShinjuku;