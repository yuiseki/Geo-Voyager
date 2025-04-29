import osmtogeojson from "osmtogeojson";
import { fetchOverpassData } from "../../../../common/fetchOverpassData";
import * as turf from "@turf/turf";

/**
 * Fetches the area of a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The area of the ward in square kilometers.
 */
export const getAreaOfWard = async (wardName: string): Promise<number> => {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"]["place"="city"]["name"="${wardName}"](area.tokyo);
);
out geom;
`;
  const response = await fetchOverpassData(overpassQuery);
  const geoJson = osmtogeojson(response);
  const area = turf.area(geoJson);
  const areaInKm2 = area / 1000000;
  return areaInKm2;
};
