// description: 東京都文京区の学校の数が東京都港区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/BunkyoHigherThanMinato.ts

/**
 * Fetches the number of schools in a specified area using Overpass API.
 * @param areaName - The name of the area to query.
 * @returns The count of schools in the specified area.
 */
async function getSchoolCount(areaName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
area["name"="${areaName}"]->.ward;
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

  if (result.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${overpassQuery}`
    );
  }

  return result.elements[0].tags.total;
}

/**
 * Compares the number of schools in Bunkyo and Minato wards.
 * @returns A boolean indicating whether Bunkyo has more schools than Minato.
 */
async function isBunkyoHigherThanMinato(): Promise<boolean> {
  const bunkyoSchoolCount = await getSchoolCount("文京区");
  const minatoSchoolCount = await getSchoolCount("港区");

  console.log(`Number of schools in 文京区: ${bunkyoSchoolCount}`);
  console.log(`Number of schools in 港区: ${minatoSchoolCount}`);

  return bunkyoSchoolCount > minatoSchoolCount;
}

// Export the function to be used as a skill
export default isBunkyoHigherThanMinato;
