import { Wine, PaginatedList, SearchRequest, RecsRequest } from '@/lib/api_types';
import { HttpClient, HttpClientOptions } from '@/lib/server/httpClient';
import { settings } from '@/lib/server/config';


export class CatalogService {
    constructor(private client: HttpClient) {
    }

    async getWine(
        ids: number[],
        options: HttpClientOptions
    ): Promise<Wine[]> {
        return this.client.get('/wines/', { ids }, options);
    }

    async getAllWinesPaginated(
        page: number,
        page_size: number,
        options: HttpClientOptions
    ): Promise<PaginatedList<Wine>> {
        return this.client.get('/wines/batch/', { page, page_size }, options);
    }
}

export class SearchService {
    constructor(private client: HttpClient) {
    }

    async search(
        request: SearchRequest,
        options: HttpClientOptions
    ): Promise<PaginatedList<number>> {
        return this.client.get('/search/', request, options);
    }
}

export class RecsService {
    constructor(private client: HttpClient) {
    }

    async getRecommendations(
        request: RecsRequest,
        options: HttpClientOptions
    ): Promise<number[]> {
        return this.client.get('/recommendations/', request, options);
    }
}

export class PersistService {
    constructor(private client: HttpClient) {
    }

    async doSql<T>(
        query: string,
        params: (string | number)[],
        options: HttpClientOptions
    ): Promise<T[]> {
        return this.client.post('/do_sql/', { query, params }, options);
    }
}

export const catalogService = new CatalogService(new HttpClient(settings.catalogService, settings.useJunction));
export const searchService = new SearchService(new HttpClient(settings.searchService, settings.useJunction));
export const recsService = new RecsService(new HttpClient(settings.recsService, settings.useJunction));
export const persistService = new PersistService(new HttpClient(settings.persistService, settings.useJunction));
