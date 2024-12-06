export interface Wine {
    id: number;
    title: string;
    country: string;
    description: string;
    designation: string;
    points: string;
    price: string;
    province: string;
    region_1: string;
    region_2: string;
    taster_name: string;
    taster_twitter_handle: string;
    variety: string;
    winery: string;
}

export interface SearchResponse {
    items: Wine[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface WineSearchParams {
    query: string;
    page: number;
    pageSize: number;
}

export interface User {
    username: string;
    isAdmin: boolean;
}

class WineService {
    private baseUrl: string;
    private currentUser: User | undefined;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    setUser(user: User | undefined) {
        this.currentUser = user;
    }
    
    getUser(): User | undefined {
        return this.currentUser;
    }

    private async request<T>(
        method: 'GET' | 'POST' | 'PUT' | 'DELETE',
        path: string,
        {
            query = {},
            body = undefined,
            additionalHeaders = {}
        }: {
            query?: Record<string, any>,
            body?: any,
            additionalHeaders?: Record<string, string>
        } = {}
    ): Promise<T> {
        try {
            const query_params = new URLSearchParams(query);
            const headers: Record<string, string> = { ...additionalHeaders };

            if (this.currentUser) {
                headers['x-username'] = this.currentUser.username;
            }

            const url = `${this.baseUrl}/${path}?${query_params.toString()}`;

            const requestInit: RequestInit = {
                method,
                headers
            };

            if (body !== undefined) {
                requestInit.body = JSON.stringify(body);
                requestInit.headers = {
                    ...headers,
                    'Content-Type': 'application/json'
                };
            }

            const response = await fetch(url, requestInit);

            if (!response.ok) {
                throw new Error(`Request failed: ${response.status} ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Error ${method} ${path}:`, error);
            throw error;
        }
    }

    async get<T>(path: string, query: Record<string, any> = {}): Promise<T> {
        return this.request<T>('GET', path, { query });
    }

    async post<T>(path: string, body: any = {}, query: Record<string, any> = {}): Promise<T> {
        return this.request<T>('POST', path, { body, query });
    }

    async put<T>(path: string, body: any = {}, query: Record<string, any> = {}): Promise<T> {
        return this.request<T>('PUT', path, { body, query });
    }

    async delete<T>(path: string, query: Record<string, any> = {}): Promise<T> {
        return this.request<T>('DELETE', path, { query });
    }

    async getCellarWines(): Promise<Array<Wine>> {
        if (!this.currentUser) {
            return [];
        }
        return await this.get("cellar/list");
    }

    async addToCellar(wineId: number) {
        const q = {
            wine_id: wineId,
        };
        return await this.get("cellar/add", q);
    }

    async removeFromCellar(wineId: number) {
        const q = {
            wine_id: wineId,
        };
        return await this.get("cellar/remove", q);
    }

    async getFeatureFlags(): Promise<Record<string, string>> {
        return await this.get("admin/get_feature_flags");
    }

    async setFeatureFlag(key: string, value: string) {
        const q = {
            key: key,
            value: value,
        };
        return await this.post("admin/set_feature_flag", q);
    }

    async recommendWines(query: string): Promise<Array<Wine>> {
        const q = {
            query: query,
        }
        return await this.get("wines/recommendations", q);
    }

    async searchWines(params: WineSearchParams): Promise<SearchResponse> {
        const q = {
            query: params.query,
            page: params.page,
            page_size: params.pageSize,
        };
        return await this.get("wines/search", q);
    }
}

let backendUrl = "http://localhost:8000";
if (import.meta.env.VITE_BACKEND) {
    backendUrl = import.meta.env.VITE_BACKEND;
}

export const wineService = new WineService(backendUrl);
