// description: モナコの人口密度がバーレーンよりも高いことを確認する。
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @returns boolean
 */
const isPopulationDensityOfMonacoHigherThanBahrain = async () => {
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

  // バーレーンの面積と人口を取得
  const queryBahrain = `[out:json];
relation["name:en"="Bahrain"]["admin_level"=2];
out geom;`;
  const resultBahrain = await fetchOverpassData(queryBahrain);
  const geoJsonBahrain = osmtogeojson(resultBahrain);
  const areaBahrain = turf.area(geoJsonBahrain);
  const populationBahrain = geoJsonBahrain.features[0].properties?.population;
  // バーレーンの人口密度を計算
  const populationDensityBahrain = populationBahrain / areaBahrain;

  return populationDensityMonaco > populationDensityBahrain;
};

export default isPopulationDensityOfMonacoHigherThanBahrain;
