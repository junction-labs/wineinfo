import { Wine, PaginatedList, SearchRequest, RecsRequest } from '@/lib/api_types';
import { HttpClient } from '@/lib/server/httpClient';
import { settings } from '@/lib/server/config';


export class CatalogService {
    private client: HttpClient;

    constructor() {
        this.client = new HttpClient(settings.catalogService);
    }

    async getWine(
        baggage: string[],
        ids: number[]
    ): Promise<Wine[]> {
        return this.client.get(baggage, '/wines/', { ids });
    }

    async getAllWinesPaginated(
        baggage: string[],
        page: number,
        page_size: number
    ): Promise<PaginatedList<Wine>> {
        return this.client.get(baggage, '/wines/batch/', { page, page_size });
    }
}

export class SearchService {
    private client: HttpClient;

    constructor() {
        this.client = new HttpClient(settings.searchService);
    }

    async search(
        baggage: string[],
        request: SearchRequest
    ): Promise<PaginatedList<number>> {
        return this.client.get(baggage, '/search/', request);
    }
}

export class RecsService {
    private client: HttpClient;

    constructor() {
        this.client = new HttpClient(settings.recsService);
    }

    async getRecommendations(
        baggage: string[],
        request: RecsRequest
    ): Promise<number[]> {
        return this.client.get(baggage, '/recommendations/', request);
    }
}

export class PersistService {
    private client: HttpClient;

    constructor() {
        this.client = new HttpClient(settings.persistService);
    }

    async doSql<T>(
        baggage: string[],
        query: string,
        params: (string | number)[],
    ): Promise<T[]> {
        return this.client.post(baggage, '/do_sql/', { query, params });
    }
}

export const catalogService = new CatalogService();
export const searchService = new SearchService();
export const recsService = new RecsService();
export const persistService = new PersistService();
export const useJunction = settings.useJunction === true;
