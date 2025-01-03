// description: 東京都新宿区の学校の数が東京都千代田区の学校の数よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/ShinjukuHigherThanChiyoda.ts

import fetch from "node-fetch";

/**
 * Fetches data from the Overpass API based on a given query.
 * @param query - The Overpass QL query string.
 * @returns Parsed JSON response from the Overpass API.
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
  return await res.json();
};

/**
 * Compares the number of schools in Shinjuku and Chiyoda districts.
 * @returns A promise that resolves to true if Shinjuku has more schools than Chiyoda, otherwise false.
 */
const isShinjukuHigherThanChiyoda = async (): Promise<boolean> => {
  // Query for the number of schools in Shinjuku
  const queryShinjukuSchools = `[out:json];
area["name"="東京都"]->.outer;
area["name"="新宿区"]->.inner;
nwr["amenity"="school"](area.inner)(area.outer);
out count;`;
  const resultShinjukuSchools = await fetchOverpassData(queryShinjukuSchools);
  if (resultShinjukuSchools.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryShinjukuSchools}`
    );
  }
  const numberOfShinjukuSchools = resultShinjukuSchools.elements[0].tags.total;

  // Query for the number of schools in Chiyoda
  const queryChiyodaSchools = `[out:json];
area["name"="東京都"]->.outer;
area["name"="千代田区"]->.inner;
nwr["amenity"="school"](area.inner)(area.outer);
out count;`;
  const resultChiyodaSchools = await fetchOverpassData(queryChiyodaSchools);
  if (resultChiyodaSchools.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryChiyodaSchools}`
    );
  }
  const numberOfChiyodaSchools = resultChiyodaSchools.elements[0].tags.total;

  // Compare the number of schools
  return numberOfShinjukuSchools > numberOfChiyodaSchools;
};

export default isShinjukuHigherThanChiyoda;
