
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


class WineService {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }
    
    async get(path: string, query: any = {}): Promise<any> {
        try {
            const qs = new URLSearchParams(query);
            const response = await fetch(`${this.baseUrl}/${path}?` + qs.toString(), {
                method: 'GET',
            });
            if (!response.ok) {
                throw new Error('Failed to fetch');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching ${path}:', error);
            throw error;
        }
    }

    async searchWines(params: WineSearchParams): Promise<SearchResponse> {
        const q = {
            query: params.query,
            page: params.page,
            page_size: params.pageSize,
        };
        return await this.get("wines/search", q);
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

    async getCellarWines(params: WineSearchParams): Promise<SearchResponse> {
        const q = {
            query: params.query,
            page: params.page,
            page_size: params.pageSize,
        }
        return await this.get("cellar", q);
    }

    async getAllCellarWineIds(): Promise<Set<number>> {
        const data = await this.get("cellar/ids");
        return new Set(data.wineIds);
    }

    async recommendWines(query:string): Promise<Array<Wine>> {
        const q = {
            query: query,
        }
        return await this.get("wines/recommendations", q);
    }
}

let backendUrl = "http://localhost:8000";
if (import.meta.env.VITE_BACKEND) {
    backendUrl = import.meta.env.VITE_BACKEND;
}

export const wineService = new WineService(backendUrl);
