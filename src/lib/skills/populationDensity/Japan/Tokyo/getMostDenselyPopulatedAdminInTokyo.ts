// description: 東京都のすべての行政区の中で、最も多くの学校がある行政区を見つける
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/getAdminWithMostSchoolsInTokyo.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

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
out body;
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
async function getPopulationDensityOfAdminInsideTokyo(
  adminName: string
): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["name"="${adminName}"]["admin_level"="7"](area.tokyo);
);
out geom;
`;
  const response = await fetchOverpassData(overpassQuery);
  const geojson = osmtogeojson(response);
  const area = turf.area(geojson.features[0]);
  const population = parseInt(response.elements[0].tags.population);
  return (population / area) * 1000000; // m2 to km2
}

const getMostDenselyPopulatedAdminInTokyo = async (): Promise<string> => {
  const adminAreas = await getAllAdminNamesInTokyo();
  let maxPopulationDensity = 0;
  let mostDenselyPopulatedAdmin = "";
  for (const admin of adminAreas.split("\n")) {
    const populationDensity = await getPopulationDensityOfAdminInsideTokyo(
      admin
    );
    console.log(
      `getMostDenselyPopulatedAdminInTokyo ${admin}: ${populationDensity} people/km²`
    );
    if (populationDensity > maxPopulationDensity) {
      maxPopulationDensity = populationDensity;
      mostDenselyPopulatedAdmin = admin;
    }
  }
  return mostDenselyPopulatedAdmin;
};

export default getMostDenselyPopulatedAdminInTokyo;
