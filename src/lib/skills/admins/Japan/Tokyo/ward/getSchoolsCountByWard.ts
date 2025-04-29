import { fetchOverpassData } from "../../../../../common/fetchOverpassData";

/**
 * Fetches the number of schools in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of schools in the ward.
 */
export async function getSchoolsCountByWard(wardName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.out;
area["name"="${wardName}"]->.in;
(
  nwr["amenity"="school"](area.in)(area.out);
);
out count;
`;
  const response = await fetchOverpassData(overpassQuery);
  return parseInt(response.elements[0].tags.total);
}
