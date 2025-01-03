// description: 東京都文京区の病院の数が東京都渋谷区よりも少ないことを確認する。
// file_path: src/lib/skills/numberOfHospitals/Japan/Tokyo/BunkyoLessThanShibuya.ts

/**
 * This skill checks if the number of hospitals in Bunkyo Ward is less than in Shibuya Ward.
 * It uses Overpass API to fetch the data and compares the counts.
 */

import fetch from 'node-fetch';

/**
 * Fetches the count of hospitals in a given ward using Overpass API.
 * @param wardName - The name of the ward.
 * @returns Promise<number> - The count of hospitals in the ward.
 */
async function getHospitalCount(wardName: string): Promise<number> {
  const query = `
    [out:json];
    area["name"="東京都"]->.tokyo;
    area["name"="${wardName}"]->.ward;
    (
      nwr["amenity"="hospital"](area.ward)(area.tokyo);
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
 * Compares the number of hospitals in Bunkyo Ward and Shibuya Ward.
 * @returns Promise<boolean> - True if Bunkyo has fewer hospitals than Shibuya, otherwise false.
 */
async function isNumberOfHospitalsInBunkyoLessThanShibuya(): Promise<boolean> {
  try {
    const bunkyoCount = await getHospitalCount("文京区");
    const shibuyaCount = await getHospitalCount("渋谷区");

    console.log(`Number of hospitals in Bunkyo Ward: ${bunkyoCount}`);
    console.log(`Number of hospitals in Shibuya Ward: ${shibuyaCount}`);

    return bunkyoCount < shibuyaCount;
  } catch (error) {
    console.error("Error comparing hospital counts:", error);
    throw error;
  }
}

export default isNumberOfHospitalsInBunkyoLessThanShibuya;