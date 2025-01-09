import { BaseDirectQuery } from './utils/BaseDirectQuery';
import { QueryResponse } from './utils/types';
import { fetchWithCache } from './utils/fetchWithCache';

interface ParkData {
  ward: string;
  totalParks: number;
  parksPerPopulation: number;
  population: number;
  parkTypes: {
    public_park: number;
    nature_reserve: number;
    playground: number;
    garden: number;
  };
  totalArea: number; // in square meters
}

interface ParkQueryResult {
  mostParks: ParkData;
  mostParksPerCapita: ParkData;
  allWards: ParkData[];
  rankings: {
    byTotal: { [key: string]: number };
    byPerCapita: { [key: string]: number };
    byType: {
      public_park: { [key: string]: number };
      nature_reserve: { [key: string]: number };
      playground: { [key: string]: number };
      garden: { [key: string]: number };
    };
    byArea: { [key: string]: number };
  };
}

export class TokyoWardParkStatisticsQuery extends BaseDirectQuery<ParkQueryResult> {
  private readonly CACHE_TTL = 43200; // 12 hours in seconds

  constructor() {
    // Set rate limit to 2 calls per second as per Overpass API guidelines
    super(2);
  }

  private async fetchWardPopulations(): Promise<Map<string, number>> {
    const populationData = await fetchWithCache(
      'https://api.data.metro.tokyo.lg.jp/v1/WardPopulation',
      {
        directory: 'tokyo',
        ttlSeconds: this.CACHE_TTL
      }
    );

    const populations = new Map<string, number>();
    for (const ward of populationData) {
      populations.set(ward.ward_name, ward.population);
    }
    return populations;
  }

  private async fetchParksInWard(wardName: string): Promise<{
    types: ParkData['parkTypes'];
    totalArea: number;
  }> {
    const query = `
      [out:json][timeout:25];
      area["name:en"="${wardName}"]["admin_level"="8"]->.ward;
      (
        // Public parks
        way["leisure"="park"](area.ward);
        relation["leisure"="park"](area.ward);
        // Nature reserves
        way["leisure"="nature_reserve"](area.ward);
        relation["leisure"="nature_reserve"](area.ward);
        // Playgrounds
        way["leisure"="playground"](area.ward);
        relation["leisure"="playground"](area.ward);
        // Gardens
        way["leisure"="garden"](area.ward);
        relation["leisure"="garden"](area.ward);
      );
      out geom;
    `;

    const data = await fetchWithCache(
      `https://overpass-api.de/api/interpreter?data=${encodeURIComponent(query)}`,
      {
        directory: 'osm',
        ttlSeconds: this.CACHE_TTL
      }
    );

    let totalArea = 0;
    const types = {
      public_park: 0,
      nature_reserve: 0,
      playground: 0,
      garden: 0
    };

    for (const element of data.elements) {
      // Count by type
      if (element.tags?.leisure === 'park') types.public_park++;
      else if (element.tags?.leisure === 'nature_reserve') types.nature_reserve++;
      else if (element.tags?.leisure === 'playground') types.playground++;
      else if (element.tags?.leisure === 'garden') types.garden++;

      // Calculate area if geometry is available
      if (element.geometry) {
        const area = this.calculatePolygonArea(element.geometry);
        totalArea += area;
      }
    }

    return { types, totalArea };
  }

  private calculatePolygonArea(points: { lat: number; lon: number }[]): number {
    if (points.length < 3) return 0;

    const R = 6371000; // Earth's radius in meters
    let total = 0;

    for (let i = 0; i < points.length; i++) {
      const j = (i + 1) % points.length;
      const p1 = points[i];
      const p2 = points[j];

      // Convert to radians
      const lat1 = p1.lat * Math.PI / 180;
      const lon1 = p1.lon * Math.PI / 180;
      const lat2 = p2.lat * Math.PI / 180;
      const lon2 = p2.lon * Math.PI / 180;

      // Calculate area using spherical geometry
      total += (lon2 - lon1) * (2 + Math.sin(lat1) + Math.sin(lat2));
    }

    return Math.abs(total * R * R / 2);
  }

  async execute(): Promise<QueryResponse<ParkQueryResult>> {
    try {
      const tokyoWards = [
        'Adachi', 'Arakawa', 'Bunkyo', 'Chiyoda', 'Chuo',
        'Edogawa', 'Itabashi', 'Katsushika', 'Kita', 'Koto',
        'Meguro', 'Minato', 'Nakano', 'Nerima', 'Ota',
        'Setagaya', 'Shibuya', 'Shinagawa', 'Shinjuku', 'Suginami',
        'Sumida', 'Taito', 'Toshima'
      ];

      const wardData: ParkData[] = [];
      const populations = await this.fetchWardPopulations();

      // Fetch park data for all wards
      for (const ward of tokyoWards) {
        await this.rateLimiter.waitForNext();
        const { types: parkTypes, totalArea } = await this.fetchParksInWard(ward);
        const population = populations.get(ward) || 0;
        const totalParks = Object.values(parkTypes).reduce((a, b) => a + b, 0);
        
        wardData.push({
          ward,
          totalParks,
          parkTypes,
          totalArea,
          population,
          parksPerPopulation: population > 0 ? (totalParks / population) * 100000 : 0
        });
      }

      // Sort by various metrics
      const byTotal = [...wardData].sort((a, b) => b.totalParks - a.totalParks);
      const byPerCapita = [...wardData].sort((a, b) => b.parksPerPopulation - a.parksPerPopulation);
      const byArea = [...wardData].sort((a, b) => b.totalArea - a.totalArea);

      // Calculate rankings
      const rankings = {
        byTotal: {},
        byPerCapita: {},
        byType: {
          public_park: {},
          nature_reserve: {},
          playground: {},
          garden: {}
        },
        byArea: {}
      };

      byTotal.forEach((ward, index) => {
        rankings.byTotal[ward.ward] = index + 1;
      });

      byPerCapita.forEach((ward, index) => {
        rankings.byPerCapita[ward.ward] = index + 1;
      });

      byArea.forEach((ward, index) => {
        rankings.byArea[ward.ward] = index + 1;
      });

      // Rankings by park type
      ['public_park', 'nature_reserve', 'playground', 'garden'].forEach(type => {
        const sorted = [...wardData].sort((a, b) => 
          b.parkTypes[type] - a.parkTypes[type]
        );
        sorted.forEach((ward, index) => {
          rankings.byType[type][ward.ward] = index + 1;
        });
      });

      const result: ParkQueryResult = {
        mostParks: byTotal[0],
        mostParksPerCapita: byPerCapita[0],
        allWards: wardData,
        rankings
      };

      return {
        data: result,
        metadata: {
          timestamp: Date.now(),
          source: 'OpenStreetMap Overpass API',
          cacheHit: false
        }
      };
    } catch (error) {
      return this.handleError(error);
    }
  }
}

// Export singleton instance
export const tokyoWardParkStatisticsQuery = new TokyoWardParkStatisticsQuery();
