// description: 東京都千代田区の病院の数が東京都渋谷区よりも少ないことを確認する。
// file_path: src/lib/skills/numberOfHospitals/Japan/Tokyo/ShibuyaLessThanChiyoda.ts

/**
 * Fetches the number of hospitals in a specified area using Overpass API.
 * @param areaName - The name of the area to query.
 * @returns The count of hospitals in the specified area.
 */
async function getNumberOfHospitals(areaName: string): Promise<number> {
  const overpassQuery = `
    [out:json];
    area["name"="${areaName}"]->.searchArea;
    (
      node["amenity"="hospital"](area.searchArea);
      way["amenity"="hospital"](area.searchArea);
      relation["amenity"="hospital"](area.searchArea);
    );
    out count;
  `;

  const response = await fetch("https://overpass-api.de/api/interpreter", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `data=${encodeURIComponent(overpassQuery)}`,
  });

  if (!response.ok) {
    throw new Error(
      `Failed to fetch data from Overpass API: ${response.statusText}`
    );
  }

  const result = await response.json();

  if (result.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${overpassQuery}`
    );
  }

  return result.elements[0].tags.total;
}

/**
 * Compares the number of hospitals in Chiyoda and Shibuya districts.
 * @returns True if Chiyoda has fewer hospitals than Shibuya, otherwise false.
 */
async function isNumberOfHospitalsInChiyodaLessThanShibuya(): Promise<boolean> {
  const numberOfHospitalsInChiyoda = await getNumberOfHospitals("千代田区");
  const numberOfHospitalsInShibuya = await getNumberOfHospitals("渋谷区");

  console.log(`Number of hospitals in Chiyoda: ${numberOfHospitalsInChiyoda}`);
  console.log(`Number of hospitals in Shibuya: ${numberOfHospitalsInShibuya}`);

  return numberOfHospitalsInChiyoda < numberOfHospitalsInShibuya;
}

export default isNumberOfHospitalsInChiyodaLessThanShibuya;
