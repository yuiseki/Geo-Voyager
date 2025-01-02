import * as turf from "@turf/turf";

export const calculateArea = (geojson: any) => {
  return turf.area(geojson);
};
