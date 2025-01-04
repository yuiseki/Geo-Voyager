// description: 東京都千代田区の学校の数が東京都港区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/ChiyodaHigherThanMinato.ts

/**
 * Fetches the count of schools in a given ward using Overpass API.
 * @param wardName - The name of the ward.
 * @returns Promise<number> - The count of schools in the ward.
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
      `Failed to fetch data for ${wardName}: ${response.statusText}`
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
 * Compares the number of schools in Chiyoda Ward and Minato Ward.
 * @returns Promise<boolean> - True if Chiyoda has more schools than Minato, otherwise false.
 */
async function isNumberOfSchoolsInChiyodaHigherThanMinato(): Promise<boolean> {
  try {
    const chiyodaCount = await getSchoolCount("千代田区");
    const minatoCount = await getSchoolCount("港区");

    console.log(`Number of schools in Chiyoda Ward: ${chiyodaCount}`);
    console.log(`Number of schools in Minato Ward: ${minatoCount}`);

    return chiyodaCount > minatoCount;
  } catch (error) {
    console.error("Error comparing school counts:", error);
    throw error;
  }
}

export default isNumberOfSchoolsInChiyodaHigherThanMinato;