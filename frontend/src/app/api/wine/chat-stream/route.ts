import { NextRequest, NextResponse } from 'next/server';
import { headers } from 'next/headers';
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { sessionOptions } from '@/lib/server/httpClient';
import { sommelierService } from '@/lib/server/services';

export async function POST(request: NextRequest) {
    const session = await getServerSession(authOptions);
    const options = sessionOptions(await headers(), session);
    const { message, conversation_history } = await request.json();

    try {
        const pythonResponse = await sommelierService.chatStream(
            { message, conversation_history },
            options
        );
        return new Response(pythonResponse.body, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        });
    } catch (error) {
        return NextResponse.json({ error: 'Python service error' }, { status: 500 });
    }
}
