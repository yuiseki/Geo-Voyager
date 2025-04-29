import {
  Feature,
  FeatureCollection,
  MultiPolygon,
  Polygon,
  GeoJsonProperties,
} from "geojson";
import fs from "fs";

/**
 * Fetches the land mask data of a specified admin area and region.
 * @param prefName - The name of the admin area to query.
 * @param regionName - The name of the region to query.
 * @returns The land mask GeoJSON data of the specified admin area and region.
 */
export const fetchNaturalEarthLandMaskGeoJson = async (
  prefName: string,
  regionName: string
): Promise<FeatureCollection<Polygon | MultiPolygon, GeoJsonProperties>> => {
  // 全世界の道州・都道府県レベルのGeoJSONデータを取得
  const geoJsonUrl =
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson";
  const cachePath = `./tmp/cache/ne_10m_admin_1_states_provinces.geojson`;
  let data;
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    data = JSON.parse(cache);
  } catch (e) {
    console.debug("Cache not found. Fetching data from GitHub...");
    const res = await fetch(geoJsonUrl);
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    data = await res.json();
    // cache the data
    await fs.mkdirSync("./tmp/cache", { recursive: true });
    await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
  }

  // 日本の都道府県かつregionに部分一致するfeatureだけを抽出
  const landMask = {
    type: "FeatureCollection",
    features: data.features
      .filter(
        (feature: Feature) =>
          feature.properties?.admin === prefName &&
          (regionName.includes(feature.properties["name"]) ||
            regionName.includes(feature.properties["name_en"]) ||
            regionName.includes(feature.properties["name_ja"]))
      )
      .filter(
        (feature: Feature) =>
          feature.geometry.type === "Polygon" ||
          feature.geometry.type === "MultiPolygon"
      ),
  } as FeatureCollection<Polygon | MultiPolygon, GeoJsonProperties>;
  return landMask;
};
