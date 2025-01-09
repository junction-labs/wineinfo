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
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card className="mb-8">
          <CardContent className="flex justify-between items-center p-4">
            <div className="flex items-center space-x-4">
              <Link
                href="/"
                className="text-xl font-semibold hover:text-muted-foreground"
              >
                Wine Catalog
              </Link>
            </div>

            <div className="flex items-center space-x-4">
              {status === 'loading' ? (
                <div>Loading...</div>
              ) : session ? (
                <>
                  <span>Welcome, {session.user?.name}</span>
                  <Button
                    variant="outline"
                    onClick={() => signOut()}
                  >
                    Sign Out
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => signIn()}
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
