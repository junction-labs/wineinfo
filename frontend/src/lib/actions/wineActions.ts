'use server';

import { Wine, PaginatedList, SearchRequest } from '@/lib/types';
import { catalogService, searchService, recsService, persistService } from '@/lib/services';
import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/config";
import { genBaggage } from '@/lib/httpClient';
import { headers } from 'next/headers';

export async function getCellarWines(): Promise<Wine[]> {
    const session = await getServerSession(authOptions);
    const baggage = genBaggage(await headers(), session);
    if (!session?.user?.id) {
        throw new Error("User not authenticated");
    }
    const userId: string = session.user.id;
    const result = await persistService.doSql<[number]>(
        baggage, 
        "SELECT wine_id FROM cellar WHERE user_id = ?",
        [userId]
    );

    const wineIds = result.map((row: any[]) => row[0]);
    return wineIds.length > 0 ? await catalogService.getWine(baggage, wineIds) : [];
}

export async function addToCellar(wineId: number) {
    const session = await getServerSession(authOptions);
    const baggage = genBaggage(await headers(), session);
    if (!session?.user?.id) {
        throw new Error("User not authenticated");
    }
    const userId: string = session.user.id;

    await persistService.doSql(
        baggage,
        "INSERT INTO cellar (wine_id, user_id) VALUES (?, ?)",
        [wineId, userId]
    );
}

export async function removeFromCellar(wineId: number) {
    const session = await getServerSession(authOptions);
    const baggage = genBaggage(await headers(), session);
    if (!session?.user?.id) {
        throw new Error("User not authenticated");
    }
    const userId: string = session.user.id;
    await persistService.doSql(
        baggage,
        "DELETE FROM cellar WHERE wine_id = ? AND user_id = ?",
        [wineId, userId]
    );
}

export async function searchWines(params: SearchRequest): Promise<PaginatedList<Wine>> {
    const session = await getServerSession(authOptions);
    const baggage = genBaggage(await headers(), session);

    const { query, page, page_size } = params;
    if (!query.trim()) {
        return await catalogService.getAllWinesPaginated(baggage, page, page_size);
    }

    const results = await searchService.search(baggage, params);
    const wines = results.items.length > 0
        ? await catalogService.getWine(baggage, results.items)
        : [];

    return {
        items: wines,
        total: results.total,
        page: results.page,
        page_size: results.page_size,
        total_pages: results.total_pages
    };
}

export async function recommendWines(query: string): Promise<Wine[]> {
    const session = await getServerSession(authOptions);
    const baggage = genBaggage(await headers(), session);

    const wineIds = await recsService.getRecommendations(baggage, { query, limit: 10 });
    return wineIds.length > 0 ? await catalogService.getWine(baggage, wineIds) : [];
}
