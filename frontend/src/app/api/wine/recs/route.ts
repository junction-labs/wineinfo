import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { recsService, catalogService } from '@/lib/server/services';
import { sessionOptions } from '@/lib/server/httpClient';

export async function GET(request: NextRequest) {
    try {
        const session = await getServerSession(authOptions);
        const { searchParams } = new URL(request.url);
        const query = searchParams.get('query');

        if (!query) {
            return NextResponse.json(
                { error: "Query parameter is required" },
                { status: 400 }
            );
        }

        const options = sessionOptions(request.headers, session);
        const wineIds = await recsService.getRecommendations(
            { query, limit: 10 },
            options
        );

        const wines = wineIds.length > 0 ?
            await catalogService.getWine(wineIds, options) :
            [];

        return NextResponse.json(wines);
    } catch (error: any) {
        const status = error.status || 500;
        const message = error.message || "Failed to get recommendations";
        return NextResponse.json(
            { error: message },
            { status }
        );
    }
}
