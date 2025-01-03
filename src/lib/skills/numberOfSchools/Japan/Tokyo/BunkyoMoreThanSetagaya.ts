// description: 東京都文京区の学校の数が東京都世田谷区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/BunkyoMoreThanSetagaya.ts

import fetch from 'node-fetch';

/**
 * Fetches the count of schools in a given ward using Overpass API.
 * @param wardName - The name of the ward.
 * @returns Promise<number> - The count of schools in the ward.
 */
async function getSchoolCount(wardName: string): Promise<number> {
  const query = `
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
    body: `data=${encodeURIComponent(query)}`,
  });

  if (!response.ok) {
    throw new Error(
      `Failed to fetch data for ${wardName}: ${response.statusText}`
    );
  }

  const data = await response.json();
  return data.elements[0].tags.total;
}

/**
 * Compares the number of schools in Bunkyo Ward and Setagaya Ward.
 * @returns Promise<boolean> - True if Bunkyo has more schools than Setagaya, otherwise false.
 */
async function isNumberOfSchoolsInBunkyoMoreThanSetagaya(): Promise<boolean> {
  try {
    const bunkyoCount = await getSchoolCount("文京区");
    const setagayaCount = await getSchoolCount("世田谷区");

    console.log(`Number of schools in Bunkyo Ward: ${bunkyoCount}`);
    console.log(`Number of schools in Setagaya Ward: ${setagayaCount}`);

    return bunkyoCount > setagayaCount;
  } catch (error) {
    console.error("Error comparing school counts:", error);
    throw error;
  }
}

export default isNumberOfSchoolsInBunkyoMoreThanSetagaya;