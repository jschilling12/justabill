import React from 'react';
import type { AppProps } from 'next/app';
import Link from 'next/link';
import '../styles/globals.css';
import { getAccessToken, clearAccessToken } from '../lib/auth';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(!!getAccessToken());
  }, [router.asPath]);

  return (
    <>
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="text-sm font-semibold text-gray-900">
            Just a Bill
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/my-votes" className="text-sm text-blue-600 hover:underline">
              My votes
            </Link>
            <Link href="/profile" className="text-sm text-blue-600 hover:underline">
              Profile
            </Link>
            {!loggedIn ? (
              <>
                <Link href="/login" className="text-sm text-blue-600 hover:underline">
                  Log in
                </Link>
                <Link href="/register" className="text-sm text-blue-600 hover:underline">
                  Register
                </Link>
              </>
            ) : (
              <button
                onClick={() => {
                  clearAccessToken();
                  setLoggedIn(false);
                  router.push('/');
                }}
                className="text-sm text-gray-600 hover:underline"
              >
                Log out
              </button>
            )}
          </div>
        </div>
      </div>
      <Component {...pageProps} />
    </>
  );
}
