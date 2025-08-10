'use client';

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, Wine } from '@/lib/api_types';
import { addToCellar, removeFromCellar, getCellarWineIds } from '@/lib/actions/wineActions';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

interface SommelierChatProps {
    isLoggedIn: boolean;
}

interface DisplayMessage extends ChatMessage {
    id: string;
    timestamp: Date;
    isLoading?: boolean;
    recommendedWines?: Wine[];
    traceMessages?: string[];
    userSummaries?: string[];
}

export default function SommelierChat({ isLoggedIn }: SommelierChatProps) {
    const [messages, setMessages] = useState<DisplayMessage[]>([
        {
            id: '1',
            role: 'assistant',
            content: 'Hello! I\'m your personal sommelier assistant. I can help you discover wines from our catalog based on your preferences, suggest food pairings, and provide recommendations tailored to your cellar. What would you like to know about wine today?',
            timestamp: new Date()
        }
    ]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [messageCount, setMessageCount] = useState(1);
    const [cellarWineIds, setCellarWineIds] = useState<Set<number>>(new Set());
    const [cellarLoadingStates, setCellarLoadingStates] = useState<Set<number>>(new Set());
    const [showDetailedTraces, setShowDetailedTraces] = useState(false);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        if (isLoggedIn) {
            const fetchCellar = async () => {
                try {
                    const cellarIds = await getCellarWineIds();
                    setCellarWineIds(new Set(cellarIds));
                } catch (error) {
                    console.error('Error fetching cellar:', error);
                }
            };
            fetchCellar();
        }
    }, [isLoggedIn]);

    useEffect(() => {
        if (messageCount > 1) {
            scrollToBottom();
        }
    }, [messageCount]);

    const handleSendMessage = async () => {
        if (!inputMessage.trim() || isLoading) return;

        const userMessage: DisplayMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: inputMessage,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setMessageCount(prev => prev + 1);
        setInputMessage('');
        setIsLoading(true);

        const loadingMessage: DisplayMessage = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: 'Thinking...',
            timestamp: new Date(),
            isLoading: true,
            traceMessages: [],
            userSummaries: []
        };
        setMessages(prev => [...prev, loadingMessage]);
        setMessageCount(prev => prev + 1);

        try {
            const conversationHistory: ChatMessage[] = messages.map(msg => ({
                role: msg.role,
                content: msg.content
            }));

            const response = await fetch('/api/wine/chat-stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: inputMessage,
                    conversation_history: conversationHistory
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to get response');
            }

            const reader = response.body?.getReader();
            if (!reader) {
                throw new Error('No response body');
            }

            const decoder = new TextDecoder();
            let finalResponse = '';
            let recommendedWines: Wine[] = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            switch (data.type) {
                                case 'status':
                                    setMessages(prev => prev.map(msg =>
                                        msg.isLoading
                                            ? { ...msg, content: data.message }
                                            : msg
                                    ));
                                    break;

                                case 'trace':
                                    setMessages(prev => prev.map(msg =>
                                        msg.isLoading
                                            ? {
                                                ...msg,
                                                traceMessages: [...(msg.traceMessages || []), data.message]
                                            }
                                            : msg
                                    ));
                                    break;

                                case 'user':
                                    setMessages(prev => prev.map(msg =>
                                        msg.isLoading
                                            ? {
                                                ...msg,
                                                userSummaries: [...(msg.userSummaries || []), data.message]
                                            }
                                            : msg
                                    ));
                                    break;

                                case 'complete':
                                    finalResponse = data.response;
                                    recommendedWines = data.recommended_wines;
                                    break;

                                case 'error':
                                    throw new Error(data.message);
                            }
                        } catch (error) {
                            console.error('Error parsing SSE data:', error);
                        }
                    }
                }
            }

            setMessages(prev => {
                const loadingMessage = prev[prev.length - 1];
                return prev.slice(0, -1).concat([{
                    id: (Date.now() + 2).toString(),
                    role: 'assistant',
                    content: finalResponse,
                    timestamp: new Date(),
                    recommendedWines: recommendedWines,
                    traceMessages: loadingMessage.traceMessages
                }]);
            });
            setMessageCount(prev => prev + 1);

        } catch (error) {
            console.error('Error sending message:', error);
            setMessages(prev => prev.slice(0, -1).concat([{
                id: (Date.now() + 3).toString(),
                role: 'assistant',
                content: 'I apologize, but I encountered an error while processing your request. Please try again.',
                timestamp: new Date()
            }]));
            setMessageCount(prev => prev + 1);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCellarAction = async (wineId: number, action: 'add' | 'remove') => {
        if (!isLoggedIn) return;

        setCellarLoadingStates(prev => new Set(prev).add(wineId));

        try {
            if (action === 'add') {
                await addToCellar(wineId);
                setCellarWineIds(prev => new Set(prev).add(wineId));
            } else {
                await removeFromCellar(wineId);
                setCellarWineIds(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(wineId);
                    return newSet;
                });
            }
        } catch (error) {
            console.error(`Error ${action}ing wine from cellar:`, error);
        } finally {
            setCellarLoadingStates(prev => {
                const newSet = new Set(prev);
                newSet.delete(wineId);
                return newSet;
            });
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    return (
        <div className="flex flex-col max-w-4xl mx-auto">
            <Card className="mb-4 shadow-lg border-0 bg-white/80 backdrop-blur-sm">
                <CardContent className="p-4">
                    <ScrollArea className="h-[calc(100vh-350px)] pr-4">
                        <div className="space-y-4">
                            {messages.map((message) => (
                                <div
                                    key={message.id}
                                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`max-w-[80%] rounded-lg p-4 ${message.role === 'user'
                                            ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg'
                                            : 'bg-gray-50 border border-gray-200'
                                            } ${message.isLoading ? 'animate-pulse' : ''}`}
                                    >
                                        <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>

                                        {message.userSummaries && message.userSummaries.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-gray-200">
                                                <div className="text-sm font-semibold mb-2 text-green-600 flex items-center gap-2">
                                                    <span>🤖</span>
                                                    <span>What I'm doing:</span>
                                                </div>
                                                <div className="space-y-2">
                                                    {message.userSummaries.map((summary, index) => (
                                                        <div key={index} className="text-sm text-gray-700 bg-green-50 p-3 rounded-lg border border-green-200">
                                                            {summary}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {message.traceMessages && message.traceMessages.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-gray-200">
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="text-xs font-semibold text-gray-500 flex items-center gap-1">
                                                        <span>🔧</span>
                                                        <span>Debug Information:</span>
                                                    </div>
                                                    <button
                                                        onClick={() => setShowDetailedTraces(!showDetailedTraces)}
                                                        className="text-xs text-purple-600 hover:text-purple-700 font-medium transition-colors"
                                                    >
                                                        {showDetailedTraces ? 'Hide Details' : 'Show Details'}
                                                    </button>
                                                </div>
                                                {showDetailedTraces && (
                                                    <div className="text-xs font-mono bg-gray-100 p-3 rounded-lg max-h-32 overflow-y-auto border border-gray-200">
                                                        {message.traceMessages.map((trace, index) => (
                                                            <div key={index} className="text-xs text-gray-600">
                                                                {trace}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {message.recommendedWines && message.recommendedWines.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-gray-200">
                                                <div className="text-sm font-semibold mb-3 text-gray-900 flex items-center gap-2">
                                                    <span>🍷</span>
                                                    <span>Recommended Wines:</span>
                                                </div>
                                                <div className="space-y-3">
                                                    {message.recommendedWines.map((wine) => {
                                                        const isInCellar = cellarWineIds.has(wine.id);
                                                        const isLoading = cellarLoadingStates.has(wine.id);

                                                        return (
                                                            <Card key={wine.id} className="p-3 border border-gray-200 hover:shadow-md transition-shadow">
                                                                <div className="flex justify-between items-start">
                                                                    <div className="text-sm flex-1 min-w-0">
                                                                        <div className="font-semibold text-gray-900 mb-1 leading-tight">
                                                                            {wine.title}
                                                                        </div>
                                                                        <div className="text-muted-foreground mb-1">
                                                                            <span className="font-medium">{wine.winery}</span>
                                                                            <span className="text-gray-400 mx-1">•</span>
                                                                            <span className="font-medium">{wine.variety}</span>
                                                                        </div>
                                                                        <div className="text-xs text-muted-foreground">
                                                                            <span>{wine.country}, {wine.province}</span>
                                                                            <span className="text-gray-400 mx-1">•</span>
                                                                            <span className="font-semibold">${wine.price}</span>
                                                                            <span className="text-gray-400 mx-1">•</span>
                                                                            <span>{wine.points} pts</span>
                                                                        </div>
                                                                    </div>
                                                                    {isLoggedIn && (
                                                                        <Button
                                                                            variant={isInCellar ? "outline" : "default"}
                                                                            size="sm"
                                                                            onClick={() => handleCellarAction(wine.id, isInCellar ? 'remove' : 'add')}
                                                                            disabled={isLoading}
                                                                            className={`ml-3 flex-shrink-0 h-8 transition-all duration-200 ${isInCellar
                                                                                ? 'border-red-200 text-red-700 hover:bg-red-50 hover:border-red-300'
                                                                                : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
                                                                                }`}
                                                                        >
                                                                            {isLoading ? (
                                                                                <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                                                                            ) : (
                                                                                    isInCellar ? "🗑️ Remove" : "🍷 Add"
                                                                            )}
                                                                        </Button>
                                                                    )}
                                                                </div>
                                                            </Card>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        )}

                                        <div className="text-xs text-muted-foreground mt-3 opacity-70">
                                            {message.timestamp.toLocaleTimeString()}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </div>
                    </ScrollArea>
                </CardContent>
            </Card>

            <div className="flex-shrink-0 bg-background border-t border-gray-200 p-4 -mx-4 shadow-lg">
                <div className="flex gap-3 max-w-4xl mx-auto">
                    <Input
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={isLoggedIn
                            ? "Ask about wine recommendations, food pairings, or what's in your cellar..."
                            : "Ask about wine recommendations, food pairings, or general wine questions..."
                        }
                        disabled={isLoading}
                        className="flex-1 h-10 text-base"
                    />
                    <Button
                        onClick={handleSendMessage}
                        disabled={isLoading || !inputMessage.trim()}
                        className="h-10 px-6 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 transition-all duration-200 shadow-lg hover:shadow-xl"
                    >
                        {isLoading ? (
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        ) : (
                            'Send'
                        )}
                    </Button>
                </div>
            </div>
        </div>
    );
}