// description: 東京都新宿区の学校の数が東京都文京区よりも少ないことを確認する。
// file_path: src/lib/skills/numberOfSchools/ShinjukuLowerThanBunkyo.ts

/**
 * Fetches the number of schools in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of schools in the ward.
 */
async function getSchoolCount(wardName: string): Promise<number> {
  const overpassQuery = `
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
 * Compares the number of schools in Shinjuku Ward and Bunkyo Ward.
 * @returns True if Shinjuku Ward has fewer schools than Bunkyo Ward, otherwise false.
 */
async function isShinjukuLowerThanBunkyo(): Promise<boolean> {
  const shinjukuSchoolCount = await getSchoolCount("新宿区");
  const bunkyoSchoolCount = await getSchoolCount("文京区");

  console.log(`Number of schools in Shinjuku Ward: ${shinjukuSchoolCount}`);
  console.log(`Number of schools in Bunkyo Ward: ${bunkyoSchoolCount}`);

  return shinjukuSchoolCount < bunkyoSchoolCount;
}

export default isShinjukuLowerThanBunkyo;