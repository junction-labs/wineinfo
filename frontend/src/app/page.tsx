'use client';

import { useSession, signIn, signOut } from 'next-auth/react';
import Link from 'next/link';
import WineCatalog from '@/components/WineCatalog';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function Home() {
  const { data: session, status } = useSession({
    required: false
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card className="mb-8 shadow-xl border-0 bg-white/80 backdrop-blur-sm">
          <CardContent className="flex justify-between items-center p-6">
            <div className="flex items-center space-x-4">
              <Link
                href="/"
                className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent hover:from-purple-700 hover:to-blue-700 transition-all duration-200"
              >
                🍷 Wine Catalog
              </Link>
            </div>

            <div className="flex items-center space-x-4">
              {status === 'loading' ? (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-purple-600 border-t-transparent" />
                  <span className="text-gray-600">Loading...</span>
                </div>
              ) : session ? (
                <>
                    <span className="text-gray-700 font-medium">Welcome, {session.user?.name}</span>
                  <Button
                    variant="outline"
                    onClick={() => signOut()}
                      className="border-gray-300 hover:bg-gray-50 transition-all duration-200"
                  >
                    Sign Out
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => signIn()}
                      className="border-gray-300 hover:bg-gray-50 transition-all duration-200"
                >
                  Sign In
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
        <WineCatalog isLoggedIn={session?.user !== undefined} />
      </div>
    </div>
  );
}
