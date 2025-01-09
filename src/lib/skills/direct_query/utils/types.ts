export interface Rankings {
  [key: string]: number;
}

export interface LibraryTypes {
  public_library: number;
  university_library: number;
  school_library: number;
  special_library: number;
}

export interface ParkTypes {
  public_park: number;
  nature_reserve: number;
  playground: number;
  garden: number;
}

export interface SchoolTypes {
  elementary: number;
  junior_high: number;
  high_school: number;
  university: number;
}

export type LibraryTypeKey = keyof LibraryTypes;
export type ParkTypeKey = keyof ParkTypes;
export type SchoolTypeKey = keyof SchoolTypes;

export interface TypeRankings {
  [key: string]: Rankings;
}

export interface QueryResult<T> {
  data: T;
  metadata: {
    timestamp: number;
    source: string;
    cacheHit: boolean;
  };
}

export interface ErrorResult {
  error: string;
  details?: unknown;
  timestamp: number;
}

export type QueryResponse<T> = QueryResult<T> | ErrorResult;

// Helper type for Prisma JSON serialization
export type SerializableJson = { [key: string]: any };
