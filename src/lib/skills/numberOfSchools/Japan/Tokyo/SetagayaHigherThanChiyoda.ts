// description: 東京都世田谷区の学校の数が東京都千代田区よりも多いことを確認する。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/SetagayaHigherThanChiyoda.ts

/**
 * Function to fetch data from Overpass API using a given query.
 * @param query - The Overpass QL query string.
 * @returns Promise resolving to the JSON response from Overpass API.
 */
const fetchOverpassData = async (query: string): Promise<any> => {
  const endpoint = "https://overpass-api.de/api/interpreter";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `data=${encodeURIComponent(query)}`,
  });

  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }

  return res.json();
};

/**
 * Function to compare the number of schools in Setagaya and Chiyoda districts.
 * @returns Promise resolving to a boolean indicating if Setagaya has more schools than Chiyoda.
 */
const isNumberOfSchoolsInSetagayaHigherThanChiyoda =
  async (): Promise<boolean> => {
    // Overpass QL query for Setagaya district
    const querySetagaya = `
    [out:json];
    area["name"="東京都"]["name:en"="Tokyo"]->.a;
    area["name"="世田谷区"]["name:en"="Setagaya"]->.b;
    (
      node(area.b)["amenity"="school"];
      way(area.b)["amenity"="school"];
      relation(area.b)["amenity"="school"];
    );
    out count;
  `;

    // Overpass QL query for Chiyoda district
    const queryChiyoda = `
    [out:json];
    area["name"="東京都"]["name:en"="Tokyo"]->.a;
    area["name"="千代田区"]["name:en"="Chiyoda"]->.b;
    (
      node(area.b)["amenity"="school"];
      way(area.b)["amenity"="school"];
      relation(area.b)["amenity"="school"];
    );
    out count;
  `;

    // Fetch data for Setagaya
    const resultSetagaya = await fetchOverpassData(querySetagaya);
    if (resultSetagaya.elements.length === 0) {
      throw new Error(
        `Overpass API returned no data without errors. Please try to fix this query:\n${querySetagaya}`
      );
    }
    const numberOfSetagayaSchools = resultSetagaya.elements[0].tags.total;

    // Fetch data for Chiyoda
    const resultChiyoda = await fetchOverpassData(queryChiyoda);
    if (resultChiyoda.elements.length === 0) {
      throw new Error(
        `Overpass API returned no data without errors. Please try to fix this query:\n${queryChiyoda}`
      );
    }
    const numberOfChiyodaSchools = resultChiyoda.elements[0].tags.total;

    // Compare the number of schools
    return numberOfSetagayaSchools > numberOfChiyodaSchools;
  };

export default isNumberOfSchoolsInSetagayaHigherThanChiyoda;
