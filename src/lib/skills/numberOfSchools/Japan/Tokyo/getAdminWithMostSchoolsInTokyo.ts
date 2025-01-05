// description: 東京都のすべての行政区の中で、最も多くの学校がある行政区を見つける
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/getAdminWithMostSchoolsInTokyo.ts

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query string.
 * @returns Promise resolving to JSON data from the Overpass API.
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
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  const data = await res.json();
  if (!data.elements || data.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${query}`
    );
  }
  return data;
};

/**
 * @returns A list of name of all admin areas in Tokyo.
 */
const getAllAdminNamesInTokyo = async (): Promise<string> => {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"](area.tokyo);
);
out tags;
`;
  const response = await fetchOverpassData(overpassQuery);
  const adminNames = response.elements.map((element: any) => element.tags.name);
  return adminNames.join("\n");
};

/**
 * Fetches the number of schools in a specified admin area using Overpass API.
 * @param adminName - The name of the admin area to query.
 * @returns The total count of schools in the admin area.
 */
async function getSchoolCountByAdminInsideTokyo(
  adminName: string
): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
area["name"="${adminName}"]->.ward;
(
  nwr["amenity"="school"](area.ward)(area.tokyo);
);
out count;
`;

  const response = await fetchOverpassData(overpassQuery);
  return response.elements[0].tags.total;
}

const getAdminWithMostSchoolsInTokyo = async (): Promise<string> => {
  const adminAreas = await getAllAdminNamesInTokyo();
  let maxSchools = 0;
  let wardWithMostSchools = "";
  for (const adminArea of adminAreas.split("\n")) {
    const schoolCount = await getSchoolCountByAdminInsideTokyo(adminArea);
    console.log(`getWardWithMostSchools ${adminArea}: ${schoolCount} schools`);
    if (schoolCount > maxSchools) {
      maxSchools = schoolCount;
      wardWithMostSchools = adminArea;
    }
  }
  return wardWithMostSchools;
};

export default getAdminWithMostSchoolsInTokyo;
