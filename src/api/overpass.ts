// src/api/overpass.ts
import { log } from "../utils/logger";

export const fetchOverpassData = async (query: string): Promise<any> => {
    const baseUrl = "https://overpass-api.de/api/interpreter";

    try {
        log("Sending request to Overpass API...");
        const response = await fetch(baseUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: `data=${encodeURIComponent(query)}`,
        });

        if (!response.ok) {
            throw new Error(`Overpass API returned an error: ${response.status}`);
        }

        log("Successfully received data from Overpass API.");
        return await response.json();
    } catch (error) {
        if (error instanceof Error) {
            log(`Error fetching data from Overpass API: ${error.message}`);
        } else {
            log(`Error fetching data from Overpass API: ${String(error)}`);
        }
        throw error;
    }
};
