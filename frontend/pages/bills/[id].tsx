import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  getBill,
  submitVote,
  submitBulkVotes,
  getMySummary,
  getBillVoteStats,
  getBillSectionVoteStats,
  getMyVotesForBill,
  getMe,
  updateMeAffiliation,
  BillSection,
  BillWithSections,
  UserBillSummary,
  VoteStats,
  VoteSubmitResponse,
} from '../../lib/api';
import { getAccessToken } from '../../lib/auth';

export default function BillPage() {
  const router = useRouter();
  const { id, from, president } = router.query;
  
  const [bill, setBill] = useState<BillWithSections | null>(null);
  const [loading, setLoading] = useState(true);
  const [votes, setVotes] = useState<Record<string, 'up' | 'down' | 'skip'>>({});
  const [showSummary, setShowSummary] = useState(false);
  const [userSummary, setUserSummary] = useState<UserBillSummary | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<'grouped' | 'all'>('grouped');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [billStats, setBillStats] = useState<VoteStats | null>(null);
  const [sectionStats, setSectionStats] = useState<Record<string, VoteStats>>({});
  const [voteMessage, setVoteMessage] = useState<string | null>(null);
  const [me, setMe] = useState<any>(null);
  const [showAffiliationPrompt, setShowAffiliationPrompt] = useState(false);
  const [affiliationInput, setAffiliationInput] = useState('');

  // Build back URL based on where user came from
  const getBackUrl = () => {
    if (from === 'enacted' && president) {
      return `/?tab=enacted&president=${encodeURIComponent(president as string)}`;
    }
    if (from === 'enacted') {
      return '/?tab=enacted';
    }
    return '/';
  };

  const getBackLabel = () => {
    if (from === 'enacted') {
      return '← Back to Signed into Law';
    }
    return '← Back to bills';
  };

  useEffect(() => {
    if (id) {
      loadBill();
    }
  }, [id]);

  useEffect(() => {
    if (!id) return;
    loadStats();
    loadMe();
    loadMyVotes();
  }, [id]);

  const loadBill = async () => {
    try {
      setLoading(true);
      const data = await getBill(id as string);
      setBill(data);
    } catch (error) {
      console.error('Error loading bill:', error);
    } finally {
      setLoading(false);
    }
  };

  const requireLogin = () => {
    router.push(`/login?returnTo=${encodeURIComponent(router.asPath)}`);
  };

  const loadMe = async () => {
    const token = getAccessToken();
    if (!token) {
      setMe(null);
      return;
    }
    try {
      const m = await getMe();
      setMe(m);
    } catch {
      setMe(null);
    }
  };

  const loadMyVotes = async () => {
    const token = getAccessToken();
    if (!token) {
      setVotes({});
      return;
    }

    try {
      const resp = await getMyVotesForBill(id as string);
      const next: Record<string, 'up' | 'down' | 'skip'> = {};
      (resp.votes || []).forEach((v) => {
        next[v.section_id] = v.vote;
      });
      setVotes(next);
    } catch (error: any) {
      if (error?.response?.status === 401) {
        setVotes({});
        return;
      }
      console.warn('Could not load my votes for bill', error);
    }
  };

  const loadStats = async () => {
    try {
      const [b, s] = await Promise.all([
        getBillVoteStats(id as string),
        getBillSectionVoteStats(id as string),
      ]);
      setBillStats(b);
      const map: Record<string, VoteStats> = {};
      s.items.forEach((it) => {
        map[it.section_id] = { counts: it.counts, percents: it.percents };
      });
      setSectionStats(map);
    } catch (error) {
      console.warn('Could not load vote stats', error);
    }
  };

  const handleVote = async (sectionId: string, vote: 'up' | 'down' | 'skip') => {
    try {
      const token = getAccessToken();
      if (!token) {
        requireLogin();
        return;
      }

      const resp: VoteSubmitResponse = await submitVote(id as string, sectionId, vote);
      setVotes((prev: Record<string, 'up' | 'down' | 'skip'>) => ({ ...prev, [sectionId]: vote }));
      setVoteMessage(resp.updated ? 'Vote updated.' : 'Vote saved.');
      await loadStats();
      await loadMe();
      if (!me?.affiliation_raw) {
        setShowAffiliationPrompt(true);
      }
    } catch (error: any) {
      console.error('Error submitting vote:', error);
      if (error?.response?.status === 401) {
        requireLogin();
        return;
      }
      alert('Error submitting vote. Please try again.');
    }
  };

  const handleGroupVote = async (sectionIds: string[], vote: 'up' | 'down' | 'skip') => {
    try {
      const token = getAccessToken();
      if (!token) {
        requireLogin();
        return;
      }

      await submitBulkVotes(id as string, sectionIds, vote);
      setVotes((prev: Record<string, 'up' | 'down' | 'skip'>) => {
        const next = { ...prev };
        for (const sectionId of sectionIds) {
          next[sectionId] = vote;
        }
        return next;
      });
      setVoteMessage('Votes saved.');
      await loadStats();
      await loadMe();
      if (!me?.affiliation_raw) {
        setShowAffiliationPrompt(true);
      }
    } catch (error: any) {
      console.error('Error submitting bulk vote:', error);
      if (error?.response?.status === 401) {
        requireLogin();
        return;
      }
      alert('Error submitting vote. Please try again.');
    }
  };

  const handleViewSummary = async () => {
    try {
      const token = getAccessToken();
      if (!token) {
        requireLogin();
        return;
      }

      const summary = await getMySummary(id as string);
      setUserSummary(summary);
      setShowSummary(true);
    } catch (error: any) {
      console.error('Error loading summary:', error);
      if (error?.response?.status === 401) {
        requireLogin();
        return;
      }
      alert('Error loading summary. Please make sure you have voted on at least one section.');
    }
  };

  const handleSaveAffiliation = async () => {
    try {
      await updateMeAffiliation(affiliationInput.trim() ? affiliationInput.trim() : null);
      setShowAffiliationPrompt(false);
      await loadMe();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Could not save affiliation');
    }
  };

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev: Set<string>) => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  const toggleGroup = (groupKey: string) => {
    setExpandedGroups((prev: Set<string>) => {
      const newSet = new Set(prev);
      if (newSet.has(groupKey)) {
        newSet.delete(groupKey);
      } else {
        newSet.add(groupKey);
      }
      return newSet;
    });
  };

  const getVerdictColor = (verdict: string) => {
    if (verdict.includes('Support')) return 'text-green-700 bg-green-100';
    if (verdict.includes('Oppose')) return 'text-red-700 bg-red-100';
    if (verdict.includes('Mixed')) return 'text-yellow-700 bg-yellow-100';
    return 'text-gray-700 bg-gray-100';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
          <p className="mt-4 text-gray-600">Loading bill...</p>
        </div>
      </div>
    );
  }

  if (!bill) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Bill not found</p>
          <Link href={getBackUrl()} className="mt-4 text-blue-600 hover:underline">
            {getBackLabel()}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Link href={getBackUrl()} className="text-sm text-blue-600 hover:underline mb-2 inline-block">
            {getBackLabel()}
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">
            {bill.bill_type.toUpperCase()}. {bill.bill_number}
          </h1>
          <p className="mt-2 text-gray-600">{bill.title}</p>
          <div className="mt-4 flex items-center space-x-4">
            <span className="text-sm text-gray-500">{bill.congress}th Congress</span>
            {bill.status && (
              <span className="px-3 py-1 text-sm bg-gray-100 rounded">
                {bill.status.replace('_', ' ')}
              </span>
            )}
            {bill.source_urls?.congress_gov && (
              <a
                href={bill.source_urls.congress_gov}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline"
              >
                Official page →
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {bill.sections.length === 0 && (
          <div className="mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <p className="text-sm text-gray-700 font-medium">
                No bill text is available yet.
              </p>
              <p className="mt-1 text-sm text-gray-600">
                Congress.gov has not published a text version for this bill yet, so there are no sections to display or vote on.
              </p>
              {bill.source_urls?.congress_gov && (
                <a
                  href={bill.source_urls.congress_gov}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-block text-sm text-blue-600 hover:underline"
                >
                  View on Congress.gov →
                </a>
              )}
            </div>
          </div>
        )}

        {/* Overall vote stats + account shortcuts */}
        <div className="mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm text-gray-500">Overall bill votes</p>
                {billStats ? (
                  <p className="mt-1 text-sm text-gray-700">
                    Agree: {billStats.counts.up} ({billStats.percents.agree_pct.toFixed(0)}%) • Disagree: {billStats.counts.down} ({billStats.percents.disagree_pct.toFixed(0)}%) • Total: {billStats.counts.total}
                  </p>
                ) : (
                  <p className="mt-1 text-sm text-gray-600">No votes yet.</p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <Link href="/my-votes" className="text-sm text-blue-600 hover:underline">
                  My votes
                </Link>
              </div>
            </div>

            {voteMessage && <div className="mt-3 text-sm text-green-700">{voteMessage}</div>}

            {showAffiliationPrompt && getAccessToken() && !me?.affiliation_raw && (
              <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded">
                <p className="text-sm text-gray-700">
                  Optional: share political affiliation to enable members-only group breakdowns.
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <input
                    value={affiliationInput}
                    onChange={(e) => setAffiliationInput(e.target.value)}
                    placeholder="e.g., Republican, Democrat, Independent"
                    className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
                  />
                  <button
                    onClick={handleSaveAffiliation}
                    className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setShowAffiliationPrompt(false)}
                    className="px-4 py-2 border border-gray-300 rounded text-sm"
                  >
                    Skip
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* View Summary Button */}
        <div className="mb-6 flex justify-end">
          <button
            onClick={handleViewSummary}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            View My Summary
          </button>
        </div>

        {/* User Summary Modal */}
        {showSummary && userSummary && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-2xl font-bold">Your Bill Summary</h2>
                  <button
                    onClick={() => setShowSummary(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Verdict */}
                <div className={`mb-6 p-4 rounded-lg ${getVerdictColor(userSummary.verdict_label)}`}>
                  <p className="text-lg font-semibold">{userSummary.verdict_label}</p>
                  <div className="mt-2 text-sm">
                    <p>Upvotes: {userSummary.upvote_count}</p>
                    <p>Downvotes: {userSummary.downvote_count}</p>
                    <p>Skipped: {userSummary.skip_count}</p>
                    {userSummary.upvote_ratio !== null && (
                      <p>Support Ratio: {(userSummary.upvote_ratio * 100).toFixed(0)}%</p>
                    )}
                  </div>
                </div>

                {/* Liked Sections */}
                {userSummary.liked_sections.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-3 text-green-700">
                      ✓ Sections You Liked
                    </h3>
                    <div className="space-y-3">
                      {userSummary.liked_sections.map((section: any) => (
                        <div key={section.section_id} className="p-3 bg-green-50 rounded border border-green-200">
                          <p className="font-medium">{section.section_key}: {section.heading}</p>
                          {section.summary && section.summary.length > 0 && (
                            <ul className="mt-2 text-sm list-disc list-inside space-y-1">
                              {section.summary.slice(0, 3).map((bullet: string, i: number) => (
                                <li key={i}>{bullet}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Disliked Sections */}
                {userSummary.disliked_sections.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-3 text-red-700">
                      ✗ Sections You Disliked
                    </h3>
                    <div className="space-y-3">
                      {userSummary.disliked_sections.map((section: any) => (
                        <div key={section.section_id} className="p-3 bg-red-50 rounded border border-red-200">
                          <p className="font-medium">{section.section_key}: {section.heading}</p>
                          {section.summary && section.summary.length > 0 && (
                            <ul className="mt-2 text-sm list-disc list-inside space-y-1">
                              {section.summary.slice(0, 3).map((bullet: string, i: number) => (
                                <li key={i}>{bullet}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Disclaimer */}
                <div className="mt-6 p-3 bg-gray-100 rounded text-xs text-gray-600">
                  This is informational only and does not constitute legal, financial, or political advice.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6">
          <div className="inline-flex rounded-lg bg-gray-100 p-1">
            <button
              onClick={() => setActiveTab('grouped')}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                activeTab === 'grouped' ? 'bg-white shadow-sm' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Grouped
            </button>
            <button
              onClick={() => setActiveTab('all')}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                activeTab === 'all' ? 'bg-white shadow-sm' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              All Sections
            </button>
          </div>
        </div>

        {/* Grouped View */}
        {activeTab === 'grouped' && (
          <div className="space-y-6">
            {bill.sections.length === 0 && (
              <div className="bg-white rounded-lg shadow p-6 text-sm text-gray-600">
                No sections to show for this bill yet.
              </div>
            )}
            {(() => {
              const groups: Array<{ key: string; division?: string | null; title?: string | null; title_heading?: string | null; sectionIds: string[]; sections: BillSection[] }> = [];
              const byKey = new Map<string, number>();

              for (const section of bill.sections) {
                const division = section.division ?? null;
                const title = section.title ?? null;
                const title_heading = section.title_heading ?? null;
                const key = `${division || ''}||${title || ''}||${title_heading || ''}`;

                const idx = byKey.get(key);
                if (idx === undefined) {
                  byKey.set(key, groups.length);
                  groups.push({
                    key,
                    division,
                    title,
                    title_heading,
                    sectionIds: [section.id],
                    sections: [section],
                  });
                } else {
                  groups[idx].sectionIds.push(section.id);
                  groups[idx].sections.push(section);
                }
              }

              const formatGroupTitle = (g: { division?: string | null; title?: string | null; title_heading?: string | null }) => {
                const parts: string[] = [];
                if (g.division) {
                  parts.push(g.division.toUpperCase().startsWith('DIVISION') ? g.division : `Division ${g.division}`);
                }
                if (g.title) {
                  parts.push(g.title.toUpperCase().startsWith('TITLE') ? g.title : `Title ${g.title}`);
                }
                if (parts.length === 0) return 'Other Sections';
                return parts.join(' / ');
              };

              // Generate a brief description for each group based on its contents
              const getGroupDescription = (g: { division?: string | null; title?: string | null; title_heading?: string | null; sections: BillSection[] }) => {
                // If there's a title_heading, it already describes the group
                if (g.title_heading) return null;
                
                // Generate description based on what we have
                if (g.sections.length === 1) {
                  const section = g.sections[0];
                  if (section.heading) {
                    return `Contains provisions related to ${section.heading.toLowerCase().replace(/^(the|a|an)\s+/i, '')}.`;
                  }
                }
                
                // Look at the section headings to summarize
                const headings = g.sections
                  .map(s => s.heading)
                  .filter(h => h && h.length > 0)
                  .slice(0, 3);
                
                if (headings.length > 0) {
                  if (headings.length === 1) {
                    return `Covers ${headings[0]?.toLowerCase().replace(/^(the|a|an)\s+/i, '')}.`;
                  }
                  return `Includes provisions on ${headings.slice(0, 2).map(h => h?.toLowerCase().replace(/^(the|a|an)\s+/i, '')).join(', ')}${g.sections.length > 2 ? `, and ${g.sections.length - 2} more` : ''}.`;
                }
                
                // Fallback
                return `Contains ${g.sections.length} legislative provision${g.sections.length > 1 ? 's' : ''} for review.`;
              };

              return groups.map((group) => (
                <div key={group.key} className="bg-white rounded-lg shadow-md overflow-hidden">
                  <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {formatGroupTitle(group)}
                        </h3>
                        {group.title_heading && (
                          <p className="mt-1 text-sm text-gray-600">{group.title_heading}</p>
                        )}
                        {!group.title_heading && getGroupDescription(group) && (
                          <p className="mt-1 text-sm text-gray-500 italic">{getGroupDescription(group)}</p>
                        )}
                        <p className="mt-1 text-xs text-gray-400">{group.sections.length} section{group.sections.length !== 1 ? 's' : ''}</p>
                      </div>
                      <button
                        onClick={() => toggleGroup(group.key)}
                        className="text-sm text-blue-600 hover:underline"
                      >
                        {expandedGroups.has(group.key) ? 'Hide details' : 'Show details'}
                      </button>
                    </div>
                  </div>

                  <div className="px-6 py-4">
                    {expandedGroups.has(group.key) ? (
                      <div className="space-y-4">
                        {group.sections.map((section) => (
                          <div key={section.id} className="border border-gray-200 rounded-lg p-4">
                            <p className="font-medium text-gray-900">
                              {section.section_key}: {section.heading}
                            </p>
                            {section.summary_json ? (
                              section.summary_json.plain_summary_bullets[0]?.startsWith('Error generating') ? (
                                <div className="mt-2 flex items-center gap-2 text-sm text-amber-600">
                                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                  </svg>
                                  <span>Summary generating... refresh in a moment</span>
                                </div>
                              ) : (
                                <ul className="mt-2 list-disc list-inside space-y-1 text-sm text-gray-600">
                                  {section.summary_json.plain_summary_bullets.slice(0, 5).map((bullet, i) => (
                                    <li key={i}>{bullet}</li>
                                  ))}
                                </ul>
                              )
                            ) : (
                              <div className="mt-2 flex items-center gap-2 text-sm text-gray-500">
                                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                <span>Generating summary...</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-600">
                        Vote once for this group (applies to all sections inside).
                      </p>
                    )}

                    {bill.source_urls && (
                      <div className="mt-4">
                        <a
                          href={bill.source_urls.congress_gov || '#'}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:underline"
                        >
                          Read official text →
                        </a>
                      </div>
                    )}
                  </div>

                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-center space-x-4">
                    <button
                      onClick={() => handleGroupVote(group.sectionIds, 'up')}
                      className="px-6 py-2 rounded-lg font-medium transition-colors bg-white text-green-600 border-2 border-green-600 hover:bg-green-50"
                    >
                      Upvote group
                    </button>
                    <button
                      onClick={() => handleGroupVote(group.sectionIds, 'down')}
                      className="px-6 py-2 rounded-lg font-medium transition-colors bg-white text-red-600 border-2 border-red-600 hover:bg-red-50"
                    >
                      Downvote group
                    </button>
                    <button
                      onClick={() => handleGroupVote(group.sectionIds, 'skip')}
                      className="px-6 py-2 rounded-lg font-medium transition-colors bg-white text-gray-600 border-2 border-gray-600 hover:bg-gray-50"
                    >
                      Skip group
                    </button>
                  </div>
                </div>
              ));
            })()}
          </div>
        )}

        {/* All Sections View (long-form) */}
        {activeTab === 'all' && (
          <div className="space-y-6">
            {bill.sections.length === 0 && (
              <div className="bg-white rounded-lg shadow p-6 text-sm text-gray-600">
                No sections to show for this bill yet.
              </div>
            )}
            {bill.sections.map((section) => (
              <div key={section.id} className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {section.section_key}: {section.heading}
                  </h3>
                </div>

                <div className="px-6 py-4">
                  {sectionStats[section.id] && (
                    <div className="mb-3 text-xs text-gray-600">
                      Agree: {sectionStats[section.id].counts.up} • Disagree: {sectionStats[section.id].counts.down} • Total: {sectionStats[section.id].counts.total}
                    </div>
                  )}
                  {section.summary_json ? (
                    section.summary_json.plain_summary_bullets[0]?.startsWith('Error generating') ? (
                      <div className="bg-amber-50 border border-amber-200 rounded p-4">
                        <div className="flex items-center gap-2">
                          <svg className="animate-spin h-5 w-5 text-amber-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <p className="text-sm text-amber-800 font-medium">
                            Summary is being generated...
                          </p>
                        </div>
                        <p className="text-sm text-amber-700 mt-1">
                          Please refresh the page in a few moments. You can still vote on this section!
                        </p>
                      </div>
                    ) : (
                      <>
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">Summary</h4>
                        <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                          {section.summary_json.plain_summary_bullets.map((bullet, i) => (
                            <li key={i}>{bullet}</li>
                          ))}
                        </ul>

                        {section.evidence_quotes && section.evidence_quotes.length > 0 && (
                          <div className="mt-4">
                            <button
                              onClick={() => toggleSection(section.id)}
                              className="text-sm text-blue-600 hover:underline"
                            >
                              {expandedSections.has(section.id) ? '▼' : '►'} Evidence
                            </button>
                            {expandedSections.has(section.id) && (
                              <div className="mt-2 pl-4 border-l-2 border-blue-200">
                                {section.evidence_quotes.map((quote, i) => (
                                  <p key={i} className="text-sm text-gray-600 italic mb-2">
                                    "{quote}"
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )
                  ) : (
                    <div className="bg-blue-50 border border-blue-200 rounded p-4">
                      <div className="flex items-center gap-2">
                        <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <p className="text-sm text-blue-900 font-medium">
                          Generating AI Summary...
                        </p>
                      </div>
                      <p className="text-sm text-blue-700 mt-1">
                        Please refresh the page in a few moments. You can still vote on this section!
                      </p>
                    </div>
                  )}

                  {bill.source_urls && (
                    <div className="mt-4">
                      <a
                        href={bill.source_urls.congress_gov || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:underline"
                      >
                        Read official text →
                      </a>
                    </div>
                  )}
                </div>

                <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-center space-x-4">
                  <button
                    onClick={() => handleVote(section.id, 'up')}
                    className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                      votes[section.id] === 'up'
                        ? 'bg-green-600 text-white'
                        : 'bg-white text-green-600 border-2 border-green-600 hover:bg-green-50'
                    }`}
                  >
                    👍 Upvote
                  </button>
                  <button
                    onClick={() => handleVote(section.id, 'down')}
                    className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                      votes[section.id] === 'down'
                        ? 'bg-red-600 text-white'
                        : 'bg-white text-red-600 border-2 border-red-600 hover:bg-red-50'
                    }`}
                  >
                    👎 Downvote
                  </button>
                  <button
                    onClick={() => handleVote(section.id, 'skip')}
                    className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                      votes[section.id] === 'skip'
                        ? 'bg-gray-600 text-white'
                        : 'bg-white text-gray-600 border-2 border-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    ⊘ Skip
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Bottom CTA */}
        {bill.sections.length > 0 && (
          <div className="mt-8 text-center">
            <button
              onClick={handleViewSummary}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-lg font-semibold"
            >
              View My Summary
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
