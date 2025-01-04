// description: 東京都のすべての行政区の中で、最も多くの病院がある行政区を見つける
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/getWardWithMostHospitals.ts

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
const getAllWardsInTokyo = async (): Promise<string[]> => {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"](area.tokyo);
);
out body;
`;
  const response = await fetchOverpassData(overpassQuery);
  const wards = response.elements.map((element: any) => element.tags.name);
  return wards;
};

/**
 * Fetches the number of hospitals in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of hospitals in the ward.
 */
async function getHospitalCountInTokyo(wardName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
area["name"="${wardName}"]->.ward;
(
  nwr["amenity"="hospital"](area.ward)(area.tokyo);
);
out count;
`;

  const response = await fetchOverpassData(overpassQuery);
  return response.elements[0].tags.total;
}

const getWardWithMostHospitals = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxHospitals = 0;
  let wardWithMostHospitals = "";
  for (const ward of wards) {
    const hospitalCount = await getHospitalCountInTokyo(ward);
    console.log(`getWardWithMostHospitals ${ward}: ${hospitalCount} hospitals`);
    if (hospitalCount > maxHospitals) {
      maxHospitals = hospitalCount;
      wardWithMostHospitals = ward;
    }
  }
  return wardWithMostHospitals;
};

export default getWardWithMostHospitals;
