// description: 東京都のすべての行政区を列挙する。
// file_path: src/lib/skills/list/Japan/Tokyo/listUpAllWardsInTokyo.ts

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
  nwr["admin_level"="7"](area.tokyo);
);
out body;
`;
  const response = await fetchOverpassData(overpassQuery);
  const wards = response.elements.map((element: any) => element.tags.name);
  return wards;
};

export default getAllWardsInTokyo;
