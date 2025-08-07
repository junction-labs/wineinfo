import { Wine, PaginatedList, SearchRequest, EmbeddingsSearchRequest, SommelierChatRequest, SommelierChatResponse } from '@/lib/api_types';
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

    async catalog_search(
        request: SearchRequest,
        options: HttpClientOptions
    ): Promise<PaginatedList<number>> {
        return this.client.post('/catalog_search/', request, options);
    }
}

export class EmbeddingsService {
    constructor(private client: HttpClient) {
    }

    async catalog_search(
        request: EmbeddingsSearchRequest,
        options: HttpClientOptions
    ): Promise<number[]> {
        return this.client.get('/catalog_search/', request, options);
    }
}

export class SommelierService {
    constructor(private client: HttpClient) {
    }

    async chatStream(
        request: SommelierChatRequest,
        options: HttpClientOptions
    ): Promise<Response> {
        return this.client.postStream('/chat/', request, options);
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

export const searchService = new SearchService(new HttpClient(settings.searchService, settings.useJunction));
export const embeddingsService = new EmbeddingsService(new HttpClient(settings.embeddingsService, settings.useJunction));
export const sommelierService = new SommelierService(new HttpClient(settings.sommelierService, settings.useJunction));
export const persistService = new PersistService(new HttpClient(settings.persistService, settings.useJunction));
