// description: 大阪府大阪市のすべての行政区の名前を取得する
// file_path: src/lib/skills/list/Japan/OsakaPref/OsakaCity/getAllAdminsInOsakaCity.ts

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
 * @returns A list of all admin areas in Osaka City.
 */
const getAllAdminsInOsakaCity = async (): Promise<string> => {
  const overpassQuery = `
[out:json];
area["name"="大阪府"]->.osakaPref;
area["name"="大阪市"]->.osakaCity;
(
  relation["admin_level"="8"](area.osakaCity)(area.osakaPref);
);
out tags;
`;
  const response = await fetchOverpassData(overpassQuery);
  const wards = response.elements.map((element: any) => element.tags.name);
  return wards.join("\n");
};

export default getAllAdminsInOsakaCity;
