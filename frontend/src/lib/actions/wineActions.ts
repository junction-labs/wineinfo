'use server';

import { Wine, PaginatedList, SearchRequest } from '@/lib/types';
import { catalogService, searchService, recsService, persistService } from '@/lib/services';

export async function getCellarWines(username: string): Promise<Wine[]> {
    const result = await persistService.doSql<[number]>(
        "SELECT wine_id FROM cellar WHERE user_id = ?",
        [username],
        username
    );

    const wineIds = result.map((row: any[]) => row[0]);
    return wineIds.length > 0 ? await catalogService.getWine(wineIds, username) : [];
}

export async function addToCellar(username: string, wineId: number) {
    await persistService.doSql(
        "INSERT INTO cellar (wine_id, user_id) VALUES (?, ?)",
        [wineId, username],
        username
    );
}

export async function removeFromCellar(username: string, wineId: number) {
    await persistService.doSql(
        "DELETE FROM cellar WHERE wine_id = ? AND user_id = ?",
        [wineId, username],
        username
    );
}

export async function searchWines(params: SearchRequest): Promise<PaginatedList<Wine>> {
    const { query, page, page_size } = params;

    if (!query.trim()) {
        return await catalogService.getAllWinesPaginated(page, page_size);
    }

    const results = await searchService.search(params);
    const wines = results.items.length > 0
        ? await catalogService.getWine(results.items)
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
    const wineIds = await recsService.getRecommendations({ query, limit: 10 });
    return wineIds.length > 0 ? await catalogService.getWine(wineIds) : [];
}
