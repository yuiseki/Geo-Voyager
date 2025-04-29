import { fetchOverpassData } from "../../../../common/fetchOverpassData";

/**
 * Fetches the number of parks in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of parks of the ward.
 */
export async function getParkCountByWard(wardName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.out;
area["name"="${wardName}"]->.in;
(
  nwr["leisure"="park"](area.in)(area.out);
);
out count;
`;
  const response = await fetchOverpassData(overpassQuery);
  return response.elements.length;
}
