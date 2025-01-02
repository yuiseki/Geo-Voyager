// description: モナコの人口密度がモルディブよりも高いことを確認する。
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfMonacoHigherThanMaldives = async () => {
  const fetchOverpassData = async (query: string): Promise<any> => {
    const endpoint = "https://overpass-api.de/api/interpreter";
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: `data=${encodeURIComponent(query)}`,
    });
    return await res.json();
  };

  // モナコの面積と人口を取得
  const queryMonaco = `[out:json];
relation["name"="Monaco"]["admin_level"=2];
out geom;`;
  const resultMonaco = await fetchOverpassData(queryMonaco);
  const geoJsonMonaco = osmtogeojson(resultMonaco);
  const areaMonaco = turf.area(geoJsonMonaco);
  const populationMonaco = geoJsonMonaco.features[0].properties?.population;
  // モナコの人口密度を計算
  const populationDensityMonaco = populationMonaco / areaMonaco;

  // モルディブの面積と人口を取得
  const queryMaldives = `[out:json];
relation["name:en"="Maldives"]["admin_level"=2];
out geom;`;
  const resultMaldives = await fetchOverpassData(queryMaldives);
  const geoJsonMaldives = osmtogeojson(resultMaldives);

  if (!geoJsonMaldives.features || geoJsonMaldives.features.length === 0) {
    throw new Error(`GeoJSON data not found for Maldives`);
  }

  const areaMaldives = turf.area(geoJsonMaldives);

  const populationMaldives = geoJsonMaldives.features[0].properties?.population;
  if (!populationMaldives) {
    throw new Error(`Population data not found for Maldives`);
  }

  // モルディブの人口密度を計算
  const populationDensityMaldives = populationMaldives / areaMaldives;

  return populationDensityMonaco > populationDensityMaldives;
};

export default isPopulationDensityOfMonacoHigherThanMaldives;
