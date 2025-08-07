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
                                    // Update loading message with status
                                    setMessages(prev => prev.map(msg =>
                                        msg.isLoading
                                            ? { ...msg, content: data.message }
                                            : msg
                                    ));
                                    break;

                                case 'trace':
                                    // Add detailed trace message
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
                                    // Add user summary message
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

            // Replace loading message with final response
            setMessages(prev => {
                const loadingMessage = prev[prev.length - 1];
                return prev.slice(0, -1).concat([{
                    id: (Date.now() + 2).toString(),
                    role: 'assistant',
                    content: finalResponse,
                    timestamp: new Date(),
                    recommendedWines: recommendedWines,
                    traceMessages: loadingMessage.traceMessages // Preserve trace messages
                }]);
            });
            setMessageCount(prev => prev + 1);

        } catch (error) {
            console.error('Error sending message:', error);
            // Replace loading message with error
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
            {/* Messages area - uses viewport height minus space for header, tabs, input, etc. */}
            <Card className="mb-4">
                <CardContent className="p-4">
                    <ScrollArea className="h-[calc(100vh-280px)] pr-4">
                        <div className="space-y-4">
                            {messages.map((message) => (
                                <div
                                    key={message.id}
                                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`max-w-[80%] rounded-lg p-3 ${message.role === 'user'
                                            ? 'bg-primary text-primary-foreground'
                                            : 'bg-muted'
                                            } ${message.isLoading ? 'animate-pulse' : ''}`}
                                    >
                                        <div className="whitespace-pre-wrap">{message.content}</div>

                                        {/* User Summaries */}
                                        {message.userSummaries && message.userSummaries.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-border">
                                                <div className="text-sm font-semibold mb-2 text-green-600 dark:text-green-400">
                                                    🤖 What I'm doing:
                                                </div>
                                                <div className="space-y-1">
                                                    {message.userSummaries.map((summary, index) => (
                                                        <div key={index} className="text-sm text-gray-700 dark:text-gray-300 bg-green-50 dark:bg-green-900/20 p-2 rounded">
                                                            {summary}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Detailed Traces (Toggleable) */}
                                        {message.traceMessages && message.traceMessages.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-border">
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                                                        Debug Information:
                                                    </div>
                                                    <button
                                                        onClick={() => setShowDetailedTraces(!showDetailedTraces)}
                                                        className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                                                    >
                                                        {showDetailedTraces ? 'Hide Details' : 'Show Details'}
                                                    </button>
                                                </div>
                                                {showDetailedTraces && (
                                                    <div className="text-xs font-mono bg-gray-100 dark:bg-gray-800 p-2 rounded max-h-32 overflow-y-auto">
                                                        {message.traceMessages.map((trace, index) => (
                                                            <div key={index} className="text-xs text-gray-600 dark:text-gray-400">
                                                                {trace}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {message.recommendedWines && message.recommendedWines.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-border">
                                                <div className="text-sm font-semibold mb-2">Recommended Wines:</div>
                                                <div className="space-y-2">
                                                    {message.recommendedWines.map((wine) => {
                                                        const isInCellar = cellarWineIds.has(wine.id);
                                                        const isLoading = cellarLoadingStates.has(wine.id);

                                                        return (
                                                            <Card key={wine.id} className="p-2">
                                                                <div className="flex justify-between items-start">
                                                                    <div className="text-sm flex-1">
                                                                        <div className="font-medium">{wine.title}</div>
                                                                        <div className="text-muted-foreground">
                                                                            {wine.winery} • {wine.variety} • ${wine.price}
                                                                        </div>
                                                                        <div className="text-xs text-muted-foreground mt-1">
                                                                            {wine.country}, {wine.province} • {wine.points} pts
                                                                        </div>
                                                                    </div>
                                                                    {isLoggedIn && (
                                                                        <Button
                                                                            variant={isInCellar ? "destructive" : "default"}
                                                                            size="sm"
                                                                            onClick={() => handleCellarAction(wine.id, isInCellar ? 'remove' : 'add')}
                                                                            disabled={isLoading}
                                                                            className="ml-2 flex-shrink-0"
                                                                        >
                                                                            {isLoading ? (
                                                                                <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                                                                            ) : (
                                                                                isInCellar ? "Remove" : "Add to Cellar"
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

                                        <div className="text-xs text-muted-foreground mt-2">
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

            {/* Sticky input area at bottom of viewport */}
            <div className="sticky bottom-0 bg-background border-t p-4 -mx-4">
                <div className="flex gap-2 max-w-4xl mx-auto">
                    <Input
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={isLoggedIn
                            ? "Ask about wine recommendations, food pairings, or what's in your cellar..."
                            : "Ask about wine recommendations, food pairings, or general wine questions..."
                        }
                        disabled={isLoading}
                        className="flex-1"
                    />
                    <Button
                        onClick={handleSendMessage}
                        disabled={isLoading || !inputMessage.trim()}
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