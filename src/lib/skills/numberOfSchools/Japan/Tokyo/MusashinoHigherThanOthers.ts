// description: 東京都文京区の学校の数が他のすべての行政区の学校数よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/MusashinoHigherThanOthers.ts

import fetch from 'node-fetch';

/**
 * Fetches the number of schools in a given Tokyo ward using Overpass API.
 * @param wardName - The name of the Tokyo ward.
 * @returns The total number of schools in the specified ward.
 */
async function getNumberOfSchoolsInWard(wardName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area["name"="東京都"];
    area["name"="${wardName}"]->.ward;
    (
      node(area.ward)["amenity"="school"];
      way(area.ward)["amenity"="school"];
      relation(area.ward)["amenity"="school"];
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
 * Compares the number of schools in Musashino with all other specified wards.
 * @returns True if Musashino has more schools than all other wards, otherwise false.
 */
async function isNumberOfSchoolsInMusashinoHigherThanOthers(): Promise<boolean> {
  const wards = ['大田区', '世田谷区', '台東区', '豊島区', '品川区'];
  const numberOfMusashinoSchools = await getNumberOfSchoolsInWard('文京区');

  for (const ward of wards) {
    const numberOfSchools = await getNumberOfSchoolsInWard(ward);
    if (numberOfMusashinoSchools <= numberOfSchools) {
      return false;
    }
  }

  return true;
}

export default isNumberOfSchoolsInMusashinoHigherThanOthers;