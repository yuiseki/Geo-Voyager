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
