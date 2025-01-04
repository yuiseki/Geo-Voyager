// description: 世界のすべての国の英語名を取得する
// file_path: src/lib/skills/list/getAllCountriesEnglishNames.ts

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
const getAllCountriesEnglishNames = async (): Promise<string[]> => {
  const overpassQuery = `
[out:json];
relation["admin_level"="2"];
out body;
`;
  const response = await fetchOverpassData(overpassQuery);
  const wards = response.elements.map((element: any) => {
    if ("name:en" in element.tags) {
      return element.tags["name:en"];
    }
  });
  return wards;
};

export default getAllCountriesEnglishNames;
