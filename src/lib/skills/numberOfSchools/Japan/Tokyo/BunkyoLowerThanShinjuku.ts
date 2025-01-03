// description: 東京都文京区の学校の数が新宿区よりも少ないことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/BunkyoLowerThanShinjuku.ts

/**
 * Fetches data from the Overpass API based on a given query.
 * @param query - The Overpass QL query to execute.
 * @returns The JSON response from the Overpass API.
 */
const fetchOverpassData = async (query: string): Promise<any> => {
  const endpoint = "https://overpass-api.de/api/interpreter";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: `data=${encodeURIComponent(query)}`,
  });
  return await res.json();
};

/**
 * Compares the number of schools in Bunkyo Ward with Shinjuku Ward.
 * @returns A boolean indicating whether Bunkyo has fewer schools than Shinjuku.
 */
const isNumberOfSchoolsInBunkyoLowerThanShinjuku = async (): Promise<boolean> => {
  // Query to get the number of schools in Bunkyo Ward
  const queryBunkyoSchools = `
    [out:json];
    area["name"="東京都"]->.outer;
    area["name"="文京区"]->.inner;
    nwr["amenity"="school"](area.inner)(area.outer);
    out count;
  `;
  const resultBunkyoSchools = await fetchOverpassData(queryBunkyoSchools);
  if (resultBunkyoSchools.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryBunkyoSchools}`
    );
  }
  const numberOfBunkyoSchools = resultBunkyoSchools.elements[0].tags.total;

  // Query to get the number of schools in Shinjuku Ward
  const queryShinjukuSchools = `
    [out:json];
    area["name"="東京都"]->.outer;
    area["name"="新宿区"]->.inner;
    nwr["amenity"="school"](area.inner)(area.outer);
    out count;
  `;
  const resultShinjukuSchools = await fetchOverpassData(queryShinjukuSchools);
  if (resultShinjukuSchools.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryShinjukuSchools}`
    );
  }
  const numberOfShinjukuSchools = resultShinjukuSchools.elements[0].tags.total;

  // Compare the number of schools
  return numberOfBunkyoSchools < numberOfShinjukuSchools;
};

// Export the function to be used as a skill
export default isNumberOfSchoolsInBunkyoLowerThanShinjuku;