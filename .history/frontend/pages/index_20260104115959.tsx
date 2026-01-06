import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getBills, Bill } from '../lib/api';

export default function Home() {
  const [bills, setBills] = useState<Bill[]>([]);
  const [lawImpactBills, setLawImpactBills] = useState<Bill[]>([]);
  const [popularBills, setPopularBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingLawImpact, setLoadingLawImpact] = useState(true);
  const [loadingPopular, setLoadingPopular] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    loadBills();
  }, [page]);

  useEffect(() => {
    loadLawImpactBills();
    loadPopularBills();
  }, []);

  const loadBills = async () => {
    try {
      setLoading(true);
      const data = await getBills(page, 20);
      setBills(data.items);
      setTotalPages(data.pages);
    } catch (error) {
      console.error('Error loading bills:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadLawImpactBills = async () => {
    try {
      setLoadingLawImpact(true);
      // First page of likely law-impact bills (e.g., HR/S in latest Congress)
      const data = await getBills(1, 10, undefined, true);
      setLawImpactBills(data.items);
    } catch (error) {
      console.error('Error loading law-impact bills:', error);
    } finally {
      setLoadingLawImpact(false);
    }
  };

  const loadPopularBills = async () => {
    try {
      setLoadingPopular(true);
      // First page of popular bills
      const data = await getBills(1, 10, true);
      setPopularBills(data.items);
    } catch (error) {
      console.error('Error loading popular bills:', error);
    } finally {
      setLoadingPopular(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">Just A Bill</h1>
          <p className="mt-2 text-sm text-gray-600">
            Explore and vote on sections of U.S. federal bills (ingested into this app)
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Disclaimer */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
          <p className="text-sm text-blue-800">
            <strong>Disclaimer:</strong> This app is informational. It summarizes bill text and 
            reflects your votes; it does not provide legal, financial, or political advice.
          </p>
        </div>

        {/* Popular Bills */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900">🔥 Popular now</h2>
            <p className="text-xs text-gray-500">
              Bills with significant public attention based on web mentions.
            </p>
          </div>
          <div className="bg-white rounded-lg shadow">
            {loadingPopular ? (
              <div className="px-6 py-6 text-center text-sm text-gray-500">
                Loading popular bills...
              </div>
            ) : popularBills.length === 0 ? (
              <div className="px-6 py-6 text-center text-sm text-gray-500">
                No popular bills at the moment. Check back soon!
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {popularBills.map((bill) => (
                  <Link
                    key={bill.id}
                    href={`/bills/${bill.id}`}
                    className="block px-6 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-medium text-gray-900 truncate">
                            {bill.bill_type.toUpperCase()}. {bill.bill_number}
                          </h3>
                          {bill.popularity_score && bill.popularity_score > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">
                              {bill.popularity_score} mentions
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-gray-600 line-clamp-1">
                          {bill.title || 'No title available'}
                        </p>
                        <div className="mt-1 flex items-center space-x-3 text-[11px] text-gray-500">
                          <span>{bill.congress}th Congress</span>
                          {bill.latest_action_date && (
                            <span>Updated: {formatDate(bill.latest_action_date)}</span>
                          )}
                        </div>
                      </div>
                      <div className="ml-3 flex-shrink-0">
                        <svg
                          className="h-4 w-4 text-gray-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Likely law-impact bills */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900">Likely law-impact bills</h2>
            <p className="text-xs text-gray-500">
              Primarily House and Senate bills (HR/S) from the latest Congress.
            </p>
          </div>
          <div className="bg-white rounded-lg shadow">
            {loadingLawImpact ? (
              <div className="px-6 py-6 text-center text-sm text-gray-500">
                Loading law-impact bills...
              </div>
            ) : lawImpactBills.length === 0 ? (
              <div className="px-6 py-6 text-center text-sm text-gray-500">
                No law-impact bills found in the current feed.
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {lawImpactBills.map((bill) => (
                  <Link
                    key={bill.id}
                    href={`/bills/${bill.id}`}
                    className="block px-6 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-900 truncate">
                          {bill.bill_type.toUpperCase()}. {bill.bill_number}
                        </h3>
                        <p className="mt-1 text-xs text-gray-600 line-clamp-1">
                          {bill.title || 'No title available'}
                        </p>
                        <div className="mt-1 flex items-center space-x-3 text-[11px] text-gray-500">
                          <span>{bill.congress}th Congress</span>
                          {bill.latest_action_date && (
                            <span>Updated: {formatDate(bill.latest_action_date)}</span>
                          )}
                        </div>
                      </div>
                      <div className="ml-3 flex-shrink-0">
                        <svg
                          className="h-4 w-4 text-gray-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Bills List */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Bills</h2>
          </div>

          {loading ? (
            <div className="px-6 py-12 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
              <p className="mt-2 text-gray-600">Loading bills...</p>
            </div>
          ) : bills.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">
              No bills found. Try ingesting some bills first.
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {bills.map((bill) => (
                <Link
                  key={bill.id}
                  href={`/bills/${bill.id}`}
                  className="block px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-medium text-gray-900 truncate">
                        {bill.bill_type.toUpperCase()}. {bill.bill_number}
                      </h3>
                      <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                        {bill.title || 'No title available'}
                      </p>
                      <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                        <span>{bill.congress}th Congress</span>
                        {bill.status && (
                          <span className="px-2 py-1 bg-gray-100 rounded">
                            {bill.status.replace('_', ' ')}
                          </span>
                        )}
                        {bill.latest_action_date && (
                          <span>Updated: {formatDate(bill.latest_action_date)}</span>
                        )}
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <svg
                        className="h-5 w-5 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {/* Pagination */}
          {!loading && bills.length > 0 && (
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-gray-700">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
