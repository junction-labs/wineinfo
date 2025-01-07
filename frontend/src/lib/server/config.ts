import type { Session } from 'next-auth'


interface ServiceSettings {
    catalogService: string;
    searchService: string;
    recsService: string;
    persistService: string;
    useJunction: boolean;
}

export const settings: ServiceSettings = {
    catalogService: process.env.CATALOG_SERVICE || "http://localhost:8001",
    searchService: process.env.SEARCH_SERVICE || "http://localhost:8002",
    recsService: process.env.RECS_SERVICE || "http://localhost:8003",
    persistService: process.env.PERSIST_SERVICE || "http://localhost:8004",
    useJunction: process.env.USE_JUNCTION === "true"
};


export function genBaggage(headers: Headers, session: Session | null): string[] {
    const requestId = headers.get('x-request-id') || crypto.randomUUID()
    return [
        'request-id=' + requestId,
        'user-id=' + (session?.user?.id || ''),
        'username=' + (session?.user?.name || ''),
        'requestId=' + requestId
    ]
}
