// description: 東京都渋谷区の病院の数が東京都文京区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfHospitals/Japan/Tokyo/ShibuyaHigherThanBunkyo.ts

import fetch from 'node-fetch';

/**
 * Fetches the number of hospitals in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of hospitals in the ward.
 */
async function getNumberOfHospitals(wardName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area["name"="東京都"]->.tokyo;
    area["name"="${wardName}"]->.ward;
    (
      node["amenity"="hospital"](area.ward)(area.tokyo);
      way["amenity"="hospital"](area.ward)(area.tokyo);
      relation["amenity"="hospital"](area.ward)(area.tokyo);
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
 * Compares the number of hospitals in Shibuya Ward and Bunkyo Ward.
 * @returns True if Shibuya Ward has more hospitals than Bunkyo Ward, otherwise false.
 */
async function isNumberOfHospitalsInShibuyaHigherThanBunkyo(): Promise<boolean> {
  const numberOfHospitalsInShibuya = await getNumberOfHospitals('渋谷区');
  const numberOfHospitalsInBunkyo = await getNumberOfHospitals('文京区');

  console.log(`Number of hospitals in Shibuya Ward: ${numberOfHospitalsInShibuya}`);
  console.log(`Number of hospitals in Bunkyo Ward: ${numberOfHospitalsInBunkyo}`);

  return numberOfHospitalsInShibuya > numberOfHospitalsInBunkyo;
}

export default isNumberOfHospitalsInShibuyaHigherThanBunkyo;