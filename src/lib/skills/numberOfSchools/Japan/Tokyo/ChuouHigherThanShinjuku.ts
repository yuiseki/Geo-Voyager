// description: 東京都中央区の学校の数が東京都新宿区の学校の数よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/ChuouHigherThanShinjuku.ts

import fetch from 'node-fetch';

/**
 * Fetches the number of schools in a specified area using Overpass API.
 * @param areaName - The name of the area to query.
 * @returns The count of schools in the specified area.
 */
async function getNumberOfSchools(areaName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area["name"="${areaName}"]->.searchArea;
    (
      node["amenity"="school"](area.searchArea);
      way["amenity"="school"](area.searchArea);
      relation["amenity"="school"](area.searchArea);
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
 * Compares the number of schools in Tokyo Chuou and Shinjuku.
 * @returns True if Chuou has more schools than Shinjuku, otherwise false.
 */
async function isNumberOfSchoolsInChuouHigherThanShinjuku(): Promise<boolean> {
  const numberOfChuouSchools = await getNumberOfSchools('中央区');
  const numberOfShinjukuSchools = await getNumberOfSchools('新宿区');

  return numberOfChuouSchools > numberOfShinjukuSchools;
}

export default isNumberOfSchoolsInChuouHigherThanShinjuku;