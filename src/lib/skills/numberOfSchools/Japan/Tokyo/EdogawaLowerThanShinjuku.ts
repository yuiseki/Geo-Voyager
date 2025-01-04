// description: 東京都江戸川区の学校の数が東京都新宿区の学校の数より少ないことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/EdogawaLowerThanShinjuku.ts

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
 * Compares the number of schools in Edogawa Ward and Shinjuku Ward.
 * @returns True if Edogawa Ward has fewer schools than Shinjuku Ward, otherwise false.
 */
async function isEdogawaLowerThanShinjuku(): Promise<boolean> {
  const edogawaSchoolCount = await getSchoolCount("江戸川区");
  const shinjukuSchoolCount = await getSchoolCount("新宿区");

  console.log(`Number of schools in Edogawa Ward: ${edogawaSchoolCount}`);
  console.log(`Number of schools in Shinjuku Ward: ${shinjukuSchoolCount}`);

  return edogawaSchoolCount < shinjukuSchoolCount;
}

export default isEdogawaLowerThanShinjuku;