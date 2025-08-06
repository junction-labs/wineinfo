'use server';

import { Wine, PaginatedList, SearchRequest, SommelierChatRequest, SommelierChatResponse } from '@/lib/api_types';
import { searchService, embeddingsService, sommelierService, persistService } from '@/lib/server/services';
import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/auth";
import { headers } from 'next/headers';
import { sessionOptions } from '@/lib/server/httpClient';


export async function getCellarWineIds(): Promise<number[]> {
    const session = await getServerSession(authOptions);
    const options = sessionOptions(await headers(), session);
    if (!session?.user || !(session.user as any).id) {
        return [];
    }
    const result = await persistService.doSql<[number]>(
        "SELECT wine_id FROM cellar WHERE user_id = ?",
        [(session.user as any).id],
        options
    );

    return result.map((row: any[]) => row[0]);
}

export async function getWinesByIds(wineIds: number[]): Promise<Wine[]> {
    const session = await getServerSession(authOptions);
    const options = sessionOptions(await headers(), session);

    return wineIds.length > 0 ? await persistService.getWine(wineIds, options) : [];
}

export async function addToCellar(wineId: number) {
    const session = await getServerSession(authOptions);
    const options = sessionOptions(await headers(), session);
    if (!session?.user || !(session.user as any).id) {
        throw new Error("User not authenticated");
    }
    await persistService.doSql(
        "INSERT INTO cellar (wine_id, user_id) VALUES (?, ?)",
        [wineId, (session.user as any).id],
        options
    );
}

export async function removeFromCellar(wineId: number) {
    const session = await getServerSession(authOptions);
    const options = sessionOptions(await headers(), session);
    if (!session?.user || !(session.user as any).id) {
        throw new Error("User not authenticated");
    }
    await persistService.doSql(
        "DELETE FROM cellar WHERE wine_id = ? AND user_id = ?",
        [wineId, (session.user as any).id],
        options
    );
}

export async function searchWines(params: SearchRequest): Promise<PaginatedList<Wine>> {
    const session = await getServerSession(authOptions);
    const options = sessionOptions(await headers(), session);

    const { query, page, page_size } = params;
    if (!query.trim()) {
        return await persistService.getAllWinesPaginated(page, page_size, options);
    }

    const results = await searchService.catalog_search(params, options);
    const wines = results.items.length > 0
        ? await persistService.getWine(results.items, options)
        : [];

    return {
        items: wines,
        total: results.total,
        page: results.page,
        page_size: results.page_size,
        total_pages: results.total_pages
    };
}

export async function searchWinesSemantic(params: { query: string; page: number; page_size: number }): Promise<PaginatedList<Wine>> {
    const session = await getServerSession(authOptions);
    const options = sessionOptions(await headers(), session);

    const { query, page, page_size } = params;
    if (!query.trim()) {
        return await persistService.getAllWinesPaginated(page, page_size, options);
    }

    const wineIds = await embeddingsService.catalog_search({
        query,
        limit: page_size * 2 // Get more results to handle pagination
    }, options);

    // Handle pagination manually
    const start = (page - 1) * page_size;
    const end = start + page_size;
    const paginatedIds = wineIds.slice(start, end);
    const wines = paginatedIds.length > 0
        ? await persistService.getWine(paginatedIds, options)
        : [];

    return {
        items: wines,
        total: wineIds.length,
        page,
        page_size,
        total_pages: Math.ceil(wineIds.length / page_size)
    };
}

export async function chatWithSommelier(request: SommelierChatRequest): Promise<SommelierChatResponse> {
    const session = await getServerSession(authOptions);
    const options = sessionOptions(await headers(), session);

    return await sommelierService.chat(request, options);
}
