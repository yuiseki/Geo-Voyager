// description: 東京都のすべての行政区の中で、最も多くの病院がある行政区を見つける
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/getWardWithMostHospitalsInTokyo.ts

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
 * @returns A list of all wards in Tokyo.
 */
const getAllAdminNamesInTokyo = async (): Promise<string> => {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"](area.tokyo);
);
out body;
`;
  const response = await fetchOverpassData(overpassQuery);
  const adminNames = response.elements.map((element: any) => element.tags.name);
  return adminNames.join("\n");
};

/**
 * Fetches the number of hospitals in a specified admin area using Overpass API.
 * @param adminName - The name of the admin area to query.
 * @returns The total count of hospitals in the admin area.
 */
async function getHospitalCountByAdminInsideTokyo(adminName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
area["name"="${adminName}"]->.ward;
(
  nwr["amenity"="hospital"](area.ward)(area.tokyo);
);
out count;
`;

  const response = await fetchOverpassData(overpassQuery);
  return response.elements[0].tags.total;
}

const getWardWithMostHospitalsInTokyo = async (): Promise<string> => {
  const adminAreas = await getAllAdminNamesInTokyo();
  let maxHospitals = 0;
  let wardWithMostHospitals = "";
  for (const adminArea of adminAreas.split("\n")) {
    const hospitalCount = await getHospitalCountByAdminInsideTokyo(adminArea);
    console.log(`getWardWithMostHospitals ${adminArea}: ${hospitalCount} hospitals`);
    if (hospitalCount > maxHospitals) {
      maxHospitals = hospitalCount;
      wardWithMostHospitals = adminArea;
    }
  }
  return wardWithMostHospitals;
};

export default getWardWithMostHospitalsInTokyo;
