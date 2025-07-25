'use client';
import React from 'react';
import { useState, useEffect } from 'react';
import { getCellarWines, addToCellar, removeFromCellar, searchWines } from '@/lib/actions/wineActions';
import { type Wine } from '@/lib/api_types';
import { Button } from "@/components/ui/button";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import SommelierChat from './SommelierChat';


type TabType = 'catalog' | 'cellar' | 'chat';

type NotificationType = 'success' | 'error';

interface WineCatalogProps {
    isLoggedIn: boolean;
}

interface Notification {
    message: string;
    type: NotificationType;
}

interface SearchInputProps {
    value: string;
    onChange: (value: string) => void;
    onSearch: () => void;
    loading: boolean;
    placeholder: string;
    isTextArea?: boolean;
}

interface WineCardProps {
    wine: Wine;
    inCellar: boolean;
    onCellarToggle: (wine: Wine) => void;
    isLoggedIn: boolean;
}

function SearchInput({
    value,
    onChange,
    onSearch,
    loading,
    placeholder,
    isTextArea = false
}: SearchInputProps) {
    const InputComponent = isTextArea ? Textarea : Input;

    return (
        <div className="flex gap-2 mb-4">
            <InputComponent
                placeholder={placeholder}
                value={value}
                onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(e.target.value)}
                onKeyPress={(e: React.KeyboardEvent) => e.key === 'Enter' && onSearch()}
            />
            <Button onClick={onSearch} disabled={loading}>
                {loading ? (
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                    '🔍 Search'
                )}
            </Button>
        </div>
    );
}

function WineCard({ wine, inCellar, onCellarToggle, isLoggedIn }: WineCardProps) {
    return (
        <Card>
            <CardContent className="p-4">
                <div className="mb-2">
                    <CardTitle className="text-lg">{wine.title}</CardTitle>
                    <div className="text-sm text-muted-foreground flex items-center gap-2">
                        <span className="font-semibold">{wine.winery}</span>
                        <span>•</span>
                        <span>{wine.variety}</span>
                    </div>
                </div>

                <div className="grid grid-cols-3 gap-y-2 text-sm mb-4">
                    <div><span className="text-muted-foreground">Country:</span> {wine.country}</div>
                    <div><span className="text-muted-foreground">Province:</span> {wine.province}</div>
                    <div><span className="text-muted-foreground">Region:</span> {wine.region_1}</div>
                    <div><span className="text-muted-foreground">Price:</span> ${wine.price}</div>
                    <div><span className="text-muted-foreground">Points:</span> {wine.points}</div>
                </div>

                <p className="text-sm text-muted-foreground mb-4 line-clamp-3">{wine.description}</p>

                {isLoggedIn && (
                    <Button
                        onClick={() => onCellarToggle(wine)}
                        variant={inCellar ? "outline" : "default"}
                        className="w-full"
                    >
                        {inCellar ? 'Remove from Cellar' : 'Add to Cellar'}
                    </Button>
                )}
            </CardContent>
        </Card>
    );
}

// Main Page Component
export default function WineCatalog({ isLoggedIn }: WineCatalogProps) {
    const [activeTab, setActiveTab] = useState<TabType>('catalog');
    const [searchTerm, setSearchTerm] = useState('');
    const [wines, setWines] = useState<Wine[]>([]);
    const [loading, setLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);
    const [cellarWines, setCellarWines] = useState(new Set<number>());
    const [notification, setNotification] = useState<Notification | null>(null);

    const pageSize = 12;

    const showNotification = (message: string, type: NotificationType = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 10000);
    };

    const fetchData = async (page: number = 1) => {
        setLoading(true);
        try {
            let wineData: Wine[], totalPages: number, total: number;

            let cellarWines: Wine[] = [];
            if (isLoggedIn) {
                cellarWines = await getCellarWines();
            }

            if (activeTab === 'catalog') {
                const data = await searchWines({
                    query: searchTerm,
                    page,
                    page_size: pageSize
                });
                wineData = data.items;
                totalPages = data.total_pages;
                total = data.total;
            } else {
                // cellar tab
                wineData = cellarWines;
                totalPages = 1;
                total = cellarWines.length;
            }

            setWines(wineData);
            setCurrentPage(page);
            setTotalPages(totalPages);
            setTotal(total);
            setCellarWines(new Set(cellarWines.map(wine => wine.id)));
        } catch (err) {
            showNotification(`Failed to load data: ${err}`, 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleCellarToggle = async (wine: Wine) => {
        try {
            if (!isLoggedIn) return;

            if (cellarWines.has(wine.id)) {
                await removeFromCellar(wine.id);
                setCellarWines(prev => {
                    const next = new Set(prev);
                    next.delete(wine.id);
                    return next;
                });
                if (activeTab === 'cellar') {
                    setWines(prev => prev.filter(w => w.id !== wine.id));
                    setTotal(prev => prev - 1);
                }
                showNotification(`${wine.title} has been removed from your cellar.`);
            } else {
                await addToCellar(wine.id);
                setCellarWines(prev => new Set([...prev, wine.id]));
                showNotification(`${wine.title} has been added to your cellar.`);
            }
        } catch (err) {
            showNotification(`Failed to update cellar: ${err}`, 'error');
        }
    };

    useEffect(() => {
        if (activeTab !== 'chat') {
            setSearchTerm('');
            setWines([]);
            setTotalPages(0);
            fetchData(1);
        }
    }, [activeTab, isLoggedIn]);

    const tabs = [
        { id: 'catalog' as TabType, name: 'Wine Catalog' },
        { id: 'cellar' as TabType, name: 'My Cellar', hidden: !isLoggedIn },
        { id: 'chat' as TabType, name: 'Sommelier Chat' }
    ];

    return (
        <div className="w-full max-w-4xl mx-auto p-4">
            <div className="border-b">
                <nav className="flex space-x-8" aria-label="Tabs">
                    {tabs.map((tab) => !tab.hidden && (
                        <Button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            variant="ghost"
                            className={activeTab === tab.id ? 'border-b-2 border-primary' : ''}
                        >
                            {tab.name}
                        </Button>
                    ))}
                </nav>
            </div>

            {notification && (
                <div className={`mb-4 p-4 rounded-lg ${notification.type === 'error' ? 'bg-destructive/10' : 'bg-primary/10'}`}>
                    {notification.message}
                </div>
            )}

            <div className="mt-4">
                {/* Chat tab content */}
                {activeTab === 'chat' && (
                    <SommelierChat isLoggedIn={isLoggedIn} />
                )}

                {/* Other tab content */}
                {activeTab !== 'chat' && (
                    <>
                        {activeTab === 'catalog' && (
                            <SearchInput
                                value={searchTerm}
                                onChange={setSearchTerm}
                                onSearch={() => fetchData(1)}
                                loading={loading}
                                placeholder="Search wines..."
                                isTextArea={false}
                            />
                        )}

                        {wines.length > 0 && totalPages > 1 && (
                            <div className="text-sm text-muted-foreground mb-4">
                                Showing {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, total)} of {total} results
                            </div>
                        )}

                        <div className="grid gap-4">
                            {wines.map((wine) => (
                                <WineCard
                                    key={wine.id}
                                    wine={wine}
                                    inCellar={cellarWines.has(wine.id)}
                                    onCellarToggle={handleCellarToggle}
                                    isLoggedIn={isLoggedIn}
                                />
                            ))}
                        </div>

                        {wines.length > 0 && totalPages > 1 && (
                            <div className="flex items-center justify-center gap-2 mt-4">
                                {[
                                    { label: '«', page: 1 },
                                    { label: '‹', page: currentPage - 1 },
                                    ...Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                        let page: number;
                                        if (totalPages <= 5) page = i + 1;
                                        else if (currentPage <= 3) page = i + 1;
                                        else if (currentPage >= totalPages - 2) page = totalPages - 4 + i;
                                        else page = currentPage - 2 + i;
                                        return { label: page.toString(), page };
                                    }),
                                    { label: '›', page: currentPage + 1 },
                                    { label: '»', page: totalPages }
                                ].map(({ label, page }) => (
                                    <Button
                                        key={label}
                                        onClick={() => page >= 1 && page <= totalPages && page !== currentPage && fetchData(page)}
                                        disabled={loading || page === currentPage || page < 1 || page > totalPages}
                                        variant={currentPage === page ? "default" : "outline"}
                                        size="sm"
                                    >
                                        {label}
                                    </Button>
                                ))}
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}