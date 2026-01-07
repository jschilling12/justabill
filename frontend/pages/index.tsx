import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getBills, getBillsVoteStats, Bill, VoteStats, BillStatus, BILL_STATUS_LABELS, ACTIVE_STATUSES, getPresidentForDate, PRESIDENTS, President, fetchEnactedByPresident, PRESIDENT_CONGRESS_MAP } from '../lib/api';

export default function Home() {
  const [bills, setBills] = useState<Bill[]>([]);
  const [lawImpactBills, setLawImpactBills] = useState<Bill[]>([]);
  const [popularBills, setPopularBills] = useState<Bill[]>([]);
  const [enactedBills, setEnactedBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingLawImpact, setLoadingLawImpact] = useState(true);
  const [loadingPopular, setLoadingPopular] = useState(true);
  const [loadingEnacted, setLoadingEnacted] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statsByBill, setStatsByBill] = useState<Record<string, VoteStats>>({});
  const [statusFilter, setStatusFilter] = useState<BillStatus | ''>('');
  const [activeTab, setActiveTab] = useState<'voting' | 'enacted'>('voting');
  
  // On-demand president fetching
  const [fetchingPresident, setFetchingPresident] = useState<string | null>(null);
  const [fetchedPresidents, setFetchedPresidents] = useState<Set<string>>(new Set());
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    loadBills();
  }, [page, statusFilter]);

  useEffect(() => {
    loadLawImpactBills();
    loadPopularBills();
    loadEnactedBills();
  }, []);

  const loadBills = async () => {
    try {
      setLoading(true);
      const data = await getBills(page, 20, undefined, undefined, statusFilter || undefined);
      setBills(data.items);
      setTotalPages(data.pages);
      const stats = await getBillsVoteStats(data.items.map((b: Bill) => b.id));
      setStatsByBill((prev) => ({ ...prev, ...stats }));
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
      const data = await getBills(1, 7, undefined, true);
      setLawImpactBills(data.items);
      const stats = await getBillsVoteStats(data.items.map((b: Bill) => b.id));
      setStatsByBill((prev) => ({ ...prev, ...stats }));
    } catch (error) {
      console.error('Error loading law-impact bills:', error);
    } finally {
      setLoadingLawImpact(false);
    }
  };

  const loadPopularBills = async () => {
    try {
      setLoadingPopular(true);
      // Fetch top 5 popular bills (exclude enacted since those aren't for voting)
      const data = await getBills(1, 5, true);
      // Filter out enacted bills from popular
      const activeBills = data.items.filter((b: Bill) => b.status !== 'enacted');
      setPopularBills(activeBills);
      const stats = await getBillsVoteStats(activeBills.map((b: Bill) => b.id));
      setStatsByBill((prev) => ({ ...prev, ...stats }));
    } catch (error) {
      console.error('Error loading popular bills:', error);
    } finally {
      setLoadingPopular(false);
    }
  };

  const loadEnactedBills = async () => {
    try {
      setLoadingEnacted(true);
      // Fetch bills that have been signed into law
      const data = await getBills(1, 10, undefined, undefined, 'enacted');
      setEnactedBills(data.items);
      const stats = await getBillsVoteStats(data.items.map((b: Bill) => b.id));
      setStatsByBill((prev) => ({ ...prev, ...stats }));
    } catch (error) {
      console.error('Error loading enacted bills:', error);
    } finally {
      setLoadingEnacted(false);
    }
  };

  // Handle clicking on a president to fetch their enacted bills
  const handleFetchPresidentBills = async (presidentName: string) => {
    // Map display name to API name
    let apiName = presidentName;
    
    // Special handling for Trump's two terms
    if (presidentName === 'Donald Trump') {
      // Check if we're looking at 2025+ (2nd term) or 2017-2021 (1st term)
      // We'll need to determine this from context. For now, use the exact match logic
      const hasTrump2nd = Object.keys(PRESIDENT_CONGRESS_MAP).includes('Donald Trump 2nd');
      // If the president header shows 2025-2029, it's 2nd term
      // This will be handled by the onClick context
    }
    
    if (fetchingPresident || fetchedPresidents.has(apiName)) return;
    
    setFetchingPresident(apiName);
    setFetchError(null);
    
    try {
      const result = await fetchEnactedByPresident(apiName);
      console.log('Fetch result:', result);
      
      // Mark as fetched
      setFetchedPresidents(prev => new Set([...prev, apiName]));
      
      // Wait a moment then reload enacted bills
      setTimeout(() => {
        loadEnactedBills();
      }, 3000); // Give n8n time to ingest some bills
      
    } catch (error: any) {
      console.error('Error fetching president bills:', error);
      setFetchError(error?.response?.data?.detail || error.message || 'Failed to fetch bills');
    } finally {
      setFetchingPresident(null);
    }
  };

  const renderVotePreview = (billId: string) => {
    const s = statsByBill[billId];
    if (!s || !s.counts || !s.counts.total) {
      return (
        <div className="mt-2 inline-flex items-center gap-2 rounded-md bg-gray-100 px-2.5 py-1 text-xs text-gray-700">
          <span className="font-semibold">Community vote</span>
          <span className="text-gray-500">No votes yet</span>
        </div>
      );
    }

    const agree = s.percents.agree_pct.toFixed(0);
    const disagree = s.percents.disagree_pct.toFixed(0);

    return (
      <div className="mt-2 inline-flex flex-wrap items-center gap-2 rounded-md bg-gray-100 px-2.5 py-1">
        <span className="text-xs font-semibold text-gray-800">Community vote</span>
        <span className="inline-flex items-center gap-1 text-xs text-gray-700">
          <span aria-hidden>👍</span>
          <span className="font-semibold">{agree}%</span>
        </span>
        <span className="text-xs text-gray-400">•</span>
        <span className="inline-flex items-center gap-1 text-xs text-gray-700">
          <span aria-hidden>👎</span>
          <span className="font-semibold">{disagree}%</span>
        </span>
        <span className="text-xs text-gray-400">•</span>
        <span className="text-xs text-gray-600">{s.counts.total} voters</span>
      </div>
    );
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const extractShortTitle = (fullTitle: string): string => {
    if (!fullTitle) return '';
    
    // If title starts with "A bill to", "A resolution to", etc., extract the action
    if (fullTitle.toLowerCase().startsWith('a bill to') || fullTitle.toLowerCase().startsWith('a resolution to')) {
      const match = fullTitle.match(/(?:to\s+)(.+?)(?:\.|,|\s+and\s+for\s+other\s+purposes)/i);
      if (match && match[1]) {
        let short = match[1].trim();
        // Limit length and capitalize first letter
        if (short.length > 60) short = short.substring(0, 60) + '...';
        return short.charAt(0).toUpperCase() + short.slice(1);
      }
    }
    
    // Otherwise, the title IS the short title (e.g., "Reliable Power Act")
    // Just return it as-is, truncated if too long
    let short = fullTitle.trim();
    if (short.length > 60) short = short.substring(0, 60) + '...';
    return short;
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

        {/* Main Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('voting')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'voting'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                🗳️ Bills for Voting
              </button>
              <button
                onClick={() => setActiveTab('enacted')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'enacted'
                    ? 'border-green-500 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                ✅ Signed into Law
              </button>
            </nav>
          </div>
        </div>

        {activeTab === 'voting' ? (
          <>

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
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="text-sm font-medium text-gray-900">
                            {bill.bill_type.toUpperCase()}. {bill.bill_number}
                            {extractShortTitle(bill.title) && (
                              <span className="font-normal text-gray-700"> - {extractShortTitle(bill.title)}</span>
                            )}
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
                          <span className="capitalize">{bill.status?.replace(/_/g, ' ') || 'Status unknown'}</span>
                          {bill.latest_action_date && (
                            <span>Updated: {formatDate(bill.latest_action_date)}</span>
                          )}
                        </div>
                        {renderVotePreview(bill.id)}
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
                        <h3 className="text-sm font-medium text-gray-900">
                          {bill.bill_type.toUpperCase()}. {bill.bill_number}
                          {extractShortTitle(bill.title) && (
                            <span className="font-normal text-gray-700"> - {extractShortTitle(bill.title)}</span>
                          )}
                        </h3>
                        <p className="mt-1 text-xs text-gray-600 line-clamp-1">
                          {bill.title || 'No title available'}
                        </p>
                        <div className="mt-1 flex items-center space-x-3 text-[11px] text-gray-500">
                          <span className="capitalize">{bill.status?.replace(/_/g, ' ') || 'Status unknown'}</span>
                          {bill.latest_action_date && (
                            <span>Updated: {formatDate(bill.latest_action_date)}</span>
                          )}
                        </div>
                        {renderVotePreview(bill.id)}
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
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">All Bills</h2>
            <div className="flex items-center gap-2">
              <label htmlFor="status-filter" className="text-sm text-gray-600">Filter by status:</label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value as BillStatus | '');
                  setPage(1);
                }}
                className="text-sm border border-gray-300 rounded-md px-3 py-1.5 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">All Statuses</option>
                {ACTIVE_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {BILL_STATUS_LABELS[status]}
                  </option>
                ))}
              </select>
            </div>
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
                      <h3 className="text-lg font-medium text-gray-900">
                        {bill.bill_type.toUpperCase()}. {bill.bill_number}
                        {extractShortTitle(bill.title) && (
                          <span className="font-normal text-gray-700"> - {extractShortTitle(bill.title)}</span>
                        )}
                      </h3>
                      <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                        {bill.title || 'No title available'}
                      </p>
                      <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                        <span className="capitalize">{bill.status?.replace(/_/g, ' ') || 'Status unknown'}</span>
                        {bill.latest_action_date && (
                          <span>Updated: {formatDate(bill.latest_action_date)}</span>
                        )}
                      </div>
                      {renderVotePreview(bill.id)}
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
        </>
        ) : (
          /* Enacted Bills Tab - Grouped by President */
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow px-6 py-4">
              <h2 className="text-xl font-semibold text-gray-900">✅ Signed into Law</h2>
              <p className="text-sm text-gray-500 mt-1">
                Click on a president to load enacted bills from their term. Bills are fetched on-demand.
              </p>
              {fetchError && (
                <div className="mt-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
                  {fetchError}
                </div>
              )}
            </div>
            
            {loadingEnacted ? (
              <div className="bg-white rounded-lg shadow px-6 py-12 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-green-600 mx-auto"></div>
                <p className="mt-2 text-gray-600">Loading enacted bills...</p>
              </div>
            ) : (
              /* Show all presidents - grouped with bills if available */
              (() => {
                // Group existing bills by president
                const billsByPresident = new Map<string, Bill[]>();
                for (const bill of enactedBills) {
                  const pres = getPresidentForDate(bill.latest_action_date);
                  const key = pres ? pres.name : 'Other';
                  if (!billsByPresident.has(key)) {
                    billsByPresident.set(key, []);
                  }
                  billsByPresident.get(key)!.push(bill);
                }
                
                // Create list of all presidents to show
                const allPresidents = Object.entries(PRESIDENT_CONGRESS_MAP).map(([name, range]) => {
                  const party = PRESIDENTS.find(p => p.name === name || 
                    (name === 'Donald Trump 2nd' && p.name === 'Donald Trump' && p.startDate === '2025-01-20') ||
                    (name === 'Donald Trump' && p.name === 'Donald Trump' && p.startDate === '2017-01-20')
                  )?.party || 'R';
                  return { name, ...range, party };
                });
                
                return allPresidents.map(({ name: presName, start, end, years, party }) => {
                  const bills = billsByPresident.get(presName.replace(' 2nd', '')) || [];
                  const isFetching = fetchingPresident === presName;
                  const hasFetched = fetchedPresidents.has(presName);
                  const displayName = presName.replace(' 2nd', '');
                  const isSecondTerm = presName.includes('2nd');
                  
                  return (
                    <div key={presName} className="bg-white rounded-lg shadow overflow-hidden">
                      {/* President Header - Clickable */}
                      <button
                        onClick={() => handleFetchPresidentBills(presName)}
                        disabled={isFetching}
                        className={`w-full px-6 py-3 border-b text-left transition-colors ${
                          party === 'R' 
                            ? 'bg-red-50 border-red-200 hover:bg-red-100' 
                            : 'bg-blue-50 border-blue-200 hover:bg-blue-100'
                        } ${isFetching ? 'opacity-75' : ''}`}
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">🏛️</span>
                          <div className="flex-1">
                            <h3 className="font-semibold text-gray-900">
                              President {displayName}
                              {isSecondTerm && <span className="text-xs text-gray-500 ml-1">(2nd term)</span>}
                            </h3>
                            <p className="text-xs text-gray-500">
                              {party === 'R' ? 'Republican' : 'Democrat'} • {years} • Congress {end}-{start}
                            </p>
                          </div>
                          
                          {isFetching ? (
                            <div className="flex items-center gap-2">
                              <div className="animate-spin h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full"></div>
                              <span className="text-xs text-gray-500">Fetching...</span>
                            </div>
                          ) : bills.length > 0 ? (
                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                              party === 'R' 
                                ? 'bg-red-100 text-red-800' 
                                : 'bg-blue-100 text-blue-800'
                            }`}>
                              {bills.length} bill{bills.length !== 1 ? 's' : ''}
                            </span>
                          ) : hasFetched ? (
                            <span className="text-xs text-gray-400">No bills found</span>
                          ) : (
                            <span className="text-xs text-gray-400 flex items-center gap-1">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                              </svg>
                              Click to load
                            </span>
                          )}
                        </div>
                      </button>
                      
                      {/* Bills under this president */}
                      {bills.length > 0 && (
                        <div className="divide-y divide-gray-200">
                          {bills.map((bill) => (
                            <Link
                              key={bill.id}
                              href={`/bills/${bill.id}`}
                              className="block px-6 py-4 hover:bg-green-50 transition-colors"
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="text-green-600">✓</span>
                                    <h4 className="text-sm font-medium text-gray-900">
                                      {bill.bill_type.toUpperCase()}. {bill.bill_number}
                                      {extractShortTitle(bill.title) && (
                                        <span className="font-normal text-gray-700"> - {extractShortTitle(bill.title)}</span>
                                      )}
                                    </h4>
                                  </div>
                                  <p className="mt-1 text-xs text-gray-600 line-clamp-1">
                                    {bill.title || 'No title available'}
                                  </p>
                                  <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
                                    {bill.latest_action_date && (
                                      <span>Enacted: {formatDate(bill.latest_action_date)}</span>
                                    )}
                                  </div>
                                  {renderVotePreview(bill.id)}
                                </div>
                                <div className="ml-3 flex-shrink-0">
                                  <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                  </svg>
                                </div>
                              </div>
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                });
              })()
            )}
          </div>
        )}
      </main>
    </div>
  );
}
