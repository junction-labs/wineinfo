import { Wine, PaginatedList, SearchRequest, RecsRequest } from '@/lib/types';
import { HttpClient } from '@/lib/httpClient';
import { settings } from '@/lib/config';


export class CatalogService {
    private client: HttpClient;

    constructor() {
        this.client = new HttpClient(settings.catalogService);
    }

    async getWine(ids: number[], username?: string): Promise<Wine[]> {
        return this.client.get('/wines/', { ids }, username);
    }

    async getAllWinesPaginated(
        page: number,
        page_size: number,
        username?: string
    ): Promise<PaginatedList<Wine>> {
        return this.client.get('/wines/batch/', { page, page_size }, username);
    }
}

export class SearchService {
    private client: HttpClient;

    constructor() {
        this.client = new HttpClient(settings.searchService);
    }

    async search(
        request: SearchRequest,
        username?: string
    ): Promise<PaginatedList<number>> {
        return this.client.get('/search/', request, username);
    }
}

export class RecsService {
    private client: HttpClient;

    constructor() {
        this.client = new HttpClient(settings.recsService);
    }

    async getRecommendations(
        request: RecsRequest,
        username?: string
    ): Promise<number[]> {
        return this.client.get('/recommendations/', request, username);
    }
}

export class PersistService {
    private client: HttpClient;

    constructor() {
        this.client = new HttpClient(settings.persistService);
    }

    async doSql<T>(
        query: string,
        params: (string | number)[],
        username?: string
    ): Promise<T[]> {
        return this.client.post('/do_sql/', { query, params }, username);
    }
}

// Initialize services
export const catalogService = new CatalogService();
export const searchService = new SearchService();
export const recsService = new RecsService();
export const persistService = new PersistService();
export const useJunction = settings.useJunction === true;
