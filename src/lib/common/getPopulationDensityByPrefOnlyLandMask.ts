import {
  Feature,
  FeatureCollection,
  MultiPolygon,
  Polygon,
  Position,
  GeoJsonProperties,
} from "geojson";
import { fetchNaturalEarthLandMaskGeoJson } from "./fetchNaturalEarthLandMaskGeoJson";
import { fetchOverpassData } from "./fetchOverpassData";
import osmtogeojson from "osmtogeojson";
import * as turf from "@turf/turf";

/**
 * Fetches the number of population density in a specified pref area using Overpass API.
 * @param prefName - The name of the pref area to query.
 * @param population - The population of the pref area.
 * @returns The population density of the pref area.
 */
export const getPopulationDensityByPrefOnlyLandMask = async (
  prefName: string,
  population: number
): Promise<number> => {
  const landMaskGeoJson = await fetchNaturalEarthLandMaskGeoJson(
    "Japan",
    prefName
  );
  const overpassQuery = `
[out:json];
area["name"="日本"]->.tokyo;
(
  relation["name"="${prefName}"]["admin_level"="4"](area.tokyo);
);
out geom;
`;
  const response = await fetchOverpassData(overpassQuery);
  const geojson = osmtogeojson(response);
  const newGeoJson = {
    type: "FeatureCollection",
    features: geojson.features.filter(
      (feature: Feature) =>
        feature.geometry.type === "Polygon" ||
        feature.geometry.type === "MultiPolygon"
    ),
  } as FeatureCollection<Polygon | MultiPolygon, GeoJsonProperties>;
  // newGeoJson.features[0] を turf で扱える形に変換
  const poly1 =
    newGeoJson.features[0].geometry.type === "Polygon"
      ? turf.polygon(
          newGeoJson.features[0].geometry.coordinates as number[][][]
        )
      : turf.multiPolygon(
          newGeoJson.features[0].geometry.coordinates as Position[][][]
        );
  // landMask.features[0] を turf で扱える形に変換
  const poly2 =
    landMaskGeoJson.features[0].geometry.type === "Polygon"
      ? turf.polygon(
          landMaskGeoJson.features[0].geometry.coordinates as number[][][]
        )
      : turf.multiPolygon(
          landMaskGeoJson.features[0].geometry.coordinates as Position[][][]
        );
  const clipped = turf.intersect(
    // @ts-expect-error poly1とpoly2はPolygon | MultiPolygonである
    turf.featureCollection([poly1, poly2])
  );
  if (!clipped) {
    throw new Error("Failed to clip the land mask.");
  }
  // area in square meters
  const area = turf.area(clipped);
  // area in square kilometers
  const areaInKm2 = area / 1000000;
  if (isNaN(population)) {
    population = 0;
  }
  return population / areaInKm2;
};
