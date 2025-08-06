'use client';

import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, Wine } from '@/lib/api_types';
import { chatWithSommelier, getCellarWineIds, addToCellar, removeFromCellar } from '@/lib/actions/wineActions';
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
    const [messageCount, setMessageCount] = useState(1); // Track message count for scroll behavior
    const [cellarWineIds, setCellarWineIds] = useState<Set<number>>(new Set());
    const [cellarLoadingStates, setCellarLoadingStates] = useState<Set<number>>(new Set());

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // Only scroll when new messages are added, not on initial mount
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

        // Add user message
        setMessages(prev => [...prev, userMessage]);
        setMessageCount(prev => prev + 1);
        setInputMessage('');
        setIsLoading(true);

        // Add loading message
        const loadingMessage: DisplayMessage = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: 'Thinking...',
            timestamp: new Date(),
            isLoading: true
        };
        setMessages(prev => [...prev, loadingMessage]);
        setMessageCount(prev => prev + 1);

        try {
            const conversationHistory: ChatMessage[] = messages.map(msg => ({
                role: msg.role,
                content: msg.content
            }));

            const response = await chatWithSommelier({
                message: inputMessage,
                conversation_history: conversationHistory
            });

            const recommendedWines = response.recommended_wines;

            setMessages(prev => prev.slice(0, -1).concat([{
                id: (Date.now() + 2).toString(),
                role: 'assistant',
                content: response.response,
                timestamp: new Date(),
                recommendedWines: recommendedWines
            }]));
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