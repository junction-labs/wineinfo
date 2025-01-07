import { settings } from '@/lib/config';
import { Session } from 'next-auth';

export interface Fetcher {
    fetch(url: string, config: RequestInit): Promise<Response>;
}

export function genBaggage(headers: Headers, session: Session | null ): string[] {
    const requestId = headers.get('x-request-id') || crypto.randomUUID()
    return [
        'request-id=' + requestId,
        'user-id=' + (session?.user?.id || ''),
        'username=' + (session?.user?.name || ''),
        'requestId=' + requestId
    ]    
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
        baggage: string[],
        method: 'GET' | 'POST',
        url: string,
        data?: any): Promise<T> {
        try {
            const headers = new Headers()
            headers.append('Content-Type', 'application/json');
            baggage.forEach(item => {
                headers.append('baggage', item)
            })
            const request: RequestInit = { method, headers };

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
                request.body = JSON.stringify(data);
            }

            const response = await this.myfetch(`${this.baseUrl}${url}`, request);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        } catch (error) {
            throw new Error(`Request failed: ${error}`);
        }
    }

    async get<T>(baggage: string[], url: string, data?: any): Promise<T> {
        return this.request<T>(baggage, 'GET', url, data);
    }

    async post<T>(baggage: string[], url: string, data: any): Promise<T> {
        return this.request<T>(baggage, 'POST', url, data);
    }
}
