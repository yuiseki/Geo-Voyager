import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";
import { fetchOverpassData } from "../api/overpass";

/**
 * シンガポールの面積と人口を得て、人口密度を計算する
 */
export const getSingaporePopulationDensity = async () => {
  const query = `[out:json];
relation["name"="Singapore"]["admin_level"=2];
out geom;`;
  const result = await fetchOverpassData(query);
  const geoJson = osmtogeojson(result);
  const area = turf.area(geoJson);
  const population = geoJson.features[0].properties?.population;
  const populationDensity = population / area;
  return populationDensity;
};
