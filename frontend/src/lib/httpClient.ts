import { settings } from '@/lib/config';

export interface Fetcher {
    fetch(url: string, config: RequestInit): Promise<Response>;
}


export class HttpClient {
    private junction: any;

    constructor(private baseUrl: string) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        if (false) {
            this.junction = require("@junction-labs/client");
        }        
    }

    private async myfetch(input: string | URL | globalThis.Request, init?: RequestInit): Promise<Response> {
        if (this.junction) {
            return this.junction.fetch(input, init);
        } else {
            return fetch(input, init);
        }
    }    

    private async request<T>(
        method: 'GET' | 'POST',
        url: string,
        data?: any,
        username?: string
    ): Promise<T> {
        try {
            const headers: HeadersInit = {
                'Content-Type': 'application/json'
            };

            if (username) {
                headers['x-username'] = username;
            }

            const config: RequestInit = { method, headers };

            if (method === 'GET' && data) {
                const params = new URLSearchParams();
                Object.entries(data).forEach(([key, value]) => {
                    if (Array.isArray(value)) {
                        value.forEach(v => params.append(key, v.toString()));
                    } else if (value !== undefined && value !== null) {
                        params.append(key, value.toString());
                    }
                });
                url = `${url}?${params.toString()}`;
            } else if (data) {
                config.body = JSON.stringify(data);
            }

            const response = await this.myfetch(`${this.baseUrl}${url}`, config);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        } catch (error) {
            throw new Error(`Request failed: ${error}`);
        }
    }

    async get<T>(url: string, data?: any, username?: string): Promise<T> {
        return this.request<T>('GET', url, data, username);
    }

    async post<T>(url: string, data: any, username?: string): Promise<T> {
        return this.request<T>('POST', url, data, username);
    }
}
