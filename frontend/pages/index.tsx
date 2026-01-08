import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { getBills, getBillsVoteStats, Bill, VoteStats, BillStatus, BILL_STATUS_LABELS, ACTIVE_STATUSES, getPresidentForDate, PRESIDENTS, President, fetchEnactedByPresident, PRESIDENT_CONGRESS_MAP, getPopularBillsByPresident, PopularBillByPresident } from '../lib/api';

export default function Home() {
  const router = useRouter();
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
  const [collapsedPresidents, setCollapsedPresidents] = useState<Set<string>>(new Set());
  const [popularByPresident, setPopularByPresident] = useState<Record<string, PopularBillByPresident[]>>({});

  // Load persisted state from localStorage on mount
  useEffect(() => {
    try {
      const storedFetchedPresidents = localStorage.getItem('justabill_fetchedPresidents');
      
      if (storedFetchedPresidents) {
        const parsed = JSON.parse(storedFetchedPresidents);
        setFetchedPresidents(new Set(parsed));
      }

      // Initialize all presidents as collapsed
      const allPresidentNames = Object.keys(PRESIDENT_CONGRESS_MAP);
      setCollapsedPresidents(new Set(allPresidentNames));
    } catch (e) {
      console.error('Error loading persisted state:', e);
    }
  }, []);

  // Read tab from URL on mount
  useEffect(() => {
    if (router.isReady) {
      const tab = router.query.tab as string;
      if (tab === 'enacted') {
        setActiveTab('enacted');
      }
      // Scroll to president if specified
      const president = router.query.president as string;
      if (president) {
        setTimeout(() => {
          const el = document.getElementById(`president-${president.replace(/\s+/g, '-')}`);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 500);
      }
    }
  }, [router.isReady, router.query.tab, router.query.president]);

  // Update URL when tab changes
  const handleTabChange = (tab: 'voting' | 'enacted') => {
    setActiveTab(tab);
    router.replace(
      { pathname: '/', query: tab === 'enacted' ? { tab: 'enacted' } : {} },
      undefined,
      { shallow: true }
    );
  };

  // Persist fetchedPresidents to localStorage
  useEffect(() => {
    if (fetchedPresidents.size > 0) {
      localStorage.setItem('justabill_fetchedPresidents', JSON.stringify(Array.from(fetchedPresidents)));
    }
  }, [fetchedPresidents]);

  useEffect(() => {
    loadBills();
  }, [page, statusFilter]);

  useEffect(() => {
    loadLawImpactBills();
    loadPopularBills();
    loadEnactedBills();
  }, []);

  // Auto-fetch all presidents when enacted tab is loaded (only once)
  useEffect(() => {
    if (activeTab === 'enacted' && !loadingEnacted) {
      const presidentNames = Object.keys(PRESIDENT_CONGRESS_MAP);
      
      // Only auto-fetch presidents that haven't been fetched yet
      const unfetchedPresidents = presidentNames.filter(name => !fetchedPresidents.has(name));
      
      if (unfetchedPresidents.length > 0) {
        console.log(`Auto-fetching ${unfetchedPresidents.length} presidents:`, unfetchedPresidents);
        
        // Fetch presidents sequentially with a delay to avoid overwhelming the API
        let delay = 0;
        unfetchedPresidents.forEach((presidentName, index) => {
          setTimeout(() => {
            console.log(`Auto-fetching president ${index + 1}/${unfetchedPresidents.length}: ${presidentName}`);
            handleFetchPresidentBills(presidentName);
          }, delay);
          delay += 2000; // 2 second delay between each president fetch
        });
      }
    }
  }, [activeTab, loadingEnacted, fetchedPresidents]);

  const loadBills = async () => {
    try {
      setLoading(true);
      // Exclude enacted bills from the voting tab (they belong in Signed into Law tab)
      // If user explicitly filters by a status, don't exclude enacted
      const excludeEnacted = statusFilter ? undefined : 'enacted';
      const data = await getBills(page, 20, undefined, undefined, statusFilter || undefined, excludeEnacted as any);
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
      // Exclude enacted bills - they belong in Signed into Law tab
      const data = await getBills(1, 7, undefined, true, undefined, 'enacted');
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
      // Fetch top 3 popular bills (exclude enacted since those aren't for voting)
      const data = await getBills(1, 3, true, undefined, undefined, 'enacted');
      setPopularBills(data.items);
      const stats = await getBillsVoteStats(data.items.map((b: Bill) => b.id));
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
      // Fetch ALL enacted bills (high page size to capture multiple presidents)
      const data = await getBills(1, 100, undefined, undefined, 'enacted');
      setEnactedBills(data.items);
      const stats = await getBillsVoteStats(data.items.map((b: Bill) => b.id));
      setStatsByBill((prev) => ({ ...prev, ...stats }));
      
      // Fetch popular bills by president
      try {
        const popular = await getPopularBillsByPresident(2);
        setPopularByPresident(popular);
      } catch (err) {
        console.error('Error loading popular bills by president:', err);
      }
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
    
    if (fetchingPresident) return;
    if (fetchedPresidents.has(apiName)) return;
    
    setFetchingPresident(apiName);
    setFetchError(null);
    
    try {
      const result = await fetchEnactedByPresident(apiName);
      console.log('Fetch result:', result);
      
      // Mark as fetched
      setFetchedPresidents(prev => {
        const newSet = new Set(Array.from(prev));
        newSet.add(apiName);
        return newSet;
      });
      
      // Reload enacted bills multiple times as n8n ingests them
      // First reload after 3s, then 10s, then 30s to catch stragglers
      setTimeout(() => loadEnactedBills(), 3000);
      setTimeout(() => loadEnactedBills(), 10000);
      setTimeout(() => loadEnactedBills(), 30000);
      
    } catch (error: any) {
      console.error('Error fetching president bills:', error);
      setFetchError(error?.response?.data?.detail || error.message || 'Failed to fetch bills');
    } finally {
      setFetchingPresident(null);
    }
  };
  
  // Toggle collapse state for a president
  const togglePresidentCollapse = (presName: string) => {
    setCollapsedPresidents(prev => {
      const newSet = new Set(Array.from(prev));
      if (newSet.has(presName)) {
        newSet.delete(presName);
      } else {
        newSet.add(presName);
      }
      return newSet;
    });
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
                onClick={() => handleTabChange('voting')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'voting'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                🗳️ Bills for Voting
              </button>
              <button
                onClick={() => handleTabChange('enacted')}
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

        {/* Popular Bills - Top 3 Featured */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">🔥 Popular now</h2>
            <p className="text-sm text-gray-500">
              Bills with significant public attention
            </p>
          </div>
          {loadingPopular ? (
            <div className="bg-white rounded-xl shadow-lg px-6 py-8 text-center text-gray-500">
              Loading popular bills...
            </div>
          ) : popularBills.length === 0 ? (
            <div className="bg-white rounded-xl shadow-lg px-6 py-8 text-center text-gray-500">
              No popular bills at the moment. Check back soon!
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {popularBills.map((bill, index) => (
                <Link
                  key={bill.id}
                  href={`/bills/${bill.id}`}
                  className={`block rounded-xl shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-1 ${
                    index === 0 
                      ? 'bg-gradient-to-br from-orange-50 to-red-50 border-2 border-orange-200' 
                      : 'bg-white border border-gray-200'
                  }`}
                >
                  <div className="p-5">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-2xl ${index === 0 ? '' : 'opacity-70'}`}>
                        🔥
                      </span>
                      {bill.popularity_score && bill.popularity_score > 0 && (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-orange-100 text-orange-800">
                          🔥 {bill.popularity_score} mentions
                        </span>
                      )}
                    </div>
                    <h3 className={`font-bold text-gray-900 ${index === 0 ? 'text-lg' : 'text-base'}`}>
                      {bill.bill_type.toUpperCase()}. {bill.bill_number}
                    </h3>
                    <p className={`mt-1 font-medium ${index === 0 ? 'text-base text-gray-800' : 'text-sm text-gray-700'}`}>
                      {extractShortTitle(bill.title) || 'Untitled'}
                    </p>
                    <p className="mt-2 text-xs text-gray-500 line-clamp-2">
                      {bill.title || 'No description available'}
                    </p>
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-xs text-gray-500 capitalize">
                        {bill.status?.replace(/_/g, ' ') || 'Status unknown'}
                      </span>
                      <span className="text-xs font-medium text-blue-600 flex items-center gap-1">
                        Vote now →
                      </span>
                    </div>
                    <div className="mt-2">
                      {renderVotePreview(bill.id)}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
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
                Bills grouped by president. Data is automatically loaded on first visit.
              </p>
              
              {/* Auto-fetch progress indicator */}
              {(() => {
                const totalPresidents = Object.keys(PRESIDENT_CONGRESS_MAP).length;
                const fetchedCount = fetchedPresidents.size;
                const progress = (fetchedCount / totalPresidents) * 100;
                
                if (fetchedCount < totalPresidents && fetchedCount > 0) {
                  return (
                    <div className="mt-3 bg-blue-50 px-3 py-2 rounded">
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-blue-700 font-medium">Loading presidents...</span>
                        <span className="text-blue-600">{fetchedCount}/{totalPresidents}</span>
                      </div>
                      <div className="w-full bg-blue-200 rounded-full h-1.5">
                        <div 
                          className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${progress}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                }
                return null;
              })()}
              
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
                  // Direct match by name - PRESIDENTS array now has proper 'Donald Trump' and 'Donald Trump 2nd' entries
                  const party = PRESIDENTS.find(p => p.name === name)?.party || 'R';
                  return { name, ...range, party };
                });
                
                return allPresidents.map(({ name: presName, start, end, years, party }) => {
                  // Get bills for this president - use exact name match since we now have separate 'Donald Trump' and 'Donald Trump 2nd'
                  const bills = billsByPresident.get(presName) || [];
                  const isFetching = fetchingPresident === presName;
                  const hasFetched = fetchedPresidents.has(presName);
                  const displayName = presName.replace(' 2nd', '');
                  const isSecondTerm = presName.includes('2nd');
                  const isCurrentTerm = presName === 'Donald Trump 2nd'; // 119th Congress, just started
                  const presidentId = `president-${presName.replace(/\s+/g, '-')}`;
                  const isCollapsed = collapsedPresidents.has(presName);
                  const hasBills = bills.length > 0;
                  
                  return (
                    <div key={presName} id={presidentId} className="bg-white rounded-lg shadow overflow-hidden">
                      {/* President Header - Clickable */}
                      <button
                        onClick={() => {
                          if (hasBills) {
                            togglePresidentCollapse(presName);
                          } else if (!hasFetched) {
                            handleFetchPresidentBills(presName);
                          }
                        }}
                        disabled={isFetching || (!hasBills && hasFetched)}
                        className={`w-full px-6 py-3 border-b text-left transition-colors ${
                          party === 'R' 
                            ? 'bg-red-50 border-red-200 hover:bg-red-100' 
                            : 'bg-blue-50 border-blue-200 hover:bg-blue-100'
                        } ${isFetching ? 'opacity-75' : ''} ${!hasBills && hasFetched ? 'cursor-default' : 'cursor-pointer'}`}
                      >
                        <div className="flex items-center gap-3">
                          {/* Collapse/Expand chevron for presidents with bills */}
                          {hasBills ? (
                            <span className={`text-gray-500 transition-transform duration-200 ${isCollapsed ? '' : 'rotate-90'}`}>
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                              </svg>
                            </span>
                          ) : (
                            <span className="text-2xl">🏛️</span>
                          )}
                          <div className="flex-1">
                            <h3 className="font-semibold text-gray-900">
                              President {displayName}
                              {isSecondTerm && <span className="text-xs text-gray-500 ml-1">(2nd term)</span>}
                            </h3>
                            <p className="text-xs text-gray-500">
                              {party === 'R' ? 'Republican' : 'Democrat'} • {years} • Congress {start}-{end}
                            </p>
                          </div>
                          
                          {isFetching ? (
                            <div className="flex items-center gap-2">
                              <div className="animate-spin h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full"></div>
                              <span className="text-xs text-gray-500">Fetching...</span>
                            </div>
                          ) : hasBills ? (
                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                              party === 'R' 
                                ? 'bg-red-100 text-red-800' 
                                : 'bg-blue-100 text-blue-800'
                            }`}>
                              {bills.length} bill{bills.length !== 1 ? 's' : ''}
                              <span className="ml-1 text-[10px] opacity-60">
                                {isCollapsed ? '(click to expand)' : '(click to collapse)'}
                              </span>
                            </span>
                          ) : hasFetched ? (
                            <span className="text-xs text-gray-400">✓ Checked</span>
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
                      
                      {/* No bills message with refresh for fetched presidents */}
                      {hasFetched && bills.length === 0 && (
                        <div className="px-6 py-4 text-center bg-gray-50">
                          {isCurrentTerm ? (
                            <>
                              <p className="text-sm text-gray-600">📋 No enacted laws yet</p>
                              <p className="text-xs text-gray-400 mt-1">
                                This term just began — bills are still working through Congress
                              </p>
                            </>
                          ) : (
                            <>
                              <p className="text-sm text-gray-600">📋 No enacted laws found in database</p>
                              <p className="text-xs text-gray-400 mt-1">
                                Bills may still be processing or none matched the criteria
                              </p>
                            </>
                          )}
                        </div>
                      )}
                      
                      {/* Bills under this president */}
                      {hasBills && !isCollapsed && (
                        <div className="divide-y divide-gray-200">
                          {bills.map((bill) => {
                            // Check if this bill is in the top 2 popular for this president
                            const popularBills = popularByPresident[presName] || [];
                            const isPopular = popularBills.some(pb => pb.bill_id === bill.id);
                            return (
                            <Link
                              key={bill.id}
                              href={`/bills/${bill.id}?from=enacted&president=${encodeURIComponent(presName)}`}
                              className="block px-6 py-4 hover:bg-green-50 transition-colors"
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="text-green-600">✓</span>
                                    {isPopular && <span className="text-lg" title="Popular bill">🔥</span>}
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
                          );})}
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
