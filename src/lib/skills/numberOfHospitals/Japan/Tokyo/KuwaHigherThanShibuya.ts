// description: 東京都港区の病院の数が東京都渋谷区よりも少ないことを確認する。
// file_path: src/lib/skills/numberOfHospitals/Japan/Tokyo/KuwaHigherThanShibuya.ts

import fetch from 'node-fetch';

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
 * Compares the number of hospitals in Minato-ku and Shibuya-ku.
 * @returns True if Minato-ku has fewer hospitals than Shibuya-ku, otherwise false.
 */
const isNumberOfHospitalsInMinatoLowerThanShibuya = async (): Promise<boolean> => {
  // Query for the number of hospitals in Minato-ku
  const queryMinatoHospitals = `[out:json];
area["name"="東京都"]->.outer;
area["name"="港区"]->.inner;
nwr["amenity"="hospital"](area.inner)(area.outer);
out count;`;
  const resultMinatoHospitals = await fetchOverpassData(queryMinatoHospitals);
  if (resultMinatoHospitals.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryMinatoHospitals}`
    );
  }
  const numberOfMinatoHospitals = resultMinatoHospitals.elements[0].tags.total;

  // Query for the number of hospitals in Shibuya-ku
  const queryShibuyaHospitals = `[out:json];
area["name"="東京都"]->.outer;
area["name"="渋谷区"]->.inner;
nwr["amenity"="hospital"](area.inner)(area.outer);
out count;`;
  const resultShibuyaHospitals = await fetchOverpassData(queryShibuyaHospitals);
  if (resultShibuyaHospitals.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryShibuyaHospitals}`
    );
  }
  const numberOfShibuyaHospitals = resultShibuyaHospitals.elements[0].tags.total;

  // Compare the number of hospitals
  return numberOfMinatoHospitals < numberOfShibuyaHospitals;
};

export default isNumberOfHospitalsInMinatoLowerThanShibuya;