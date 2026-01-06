import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { getBill, submitVote, getUserSummary, BillWithSections, UserBillSummary } from '../../lib/api';

export default function BillPage() {
  const router = useRouter();
  const { id } = router.query;
  
  const [bill, setBill] = useState<BillWithSections | null>(null);
  const [loading, setLoading] = useState(true);
  const [votes, setVotes] = useState<Record<string, 'up' | 'down' | 'skip'>>({});
  const [showSummary, setShowSummary] = useState(false);
  const [userSummary, setUserSummary] = useState<UserBillSummary | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (id) {
      loadBill();
    }
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

  const handleVote = async (sectionId: string, vote: 'up' | 'down' | 'skip') => {
    try {
      await submitVote(id as string, sectionId, vote);
      setVotes(prev => ({ ...prev, [sectionId]: vote }));
    } catch (error) {
      console.error('Error submitting vote:', error);
      alert('Error submitting vote. Please try again.');
    }
  };

  const handleViewSummary = async () => {
    try {
      const sessionId = localStorage.getItem('session_id') || '';
      const summary = await getUserSummary(id as string, sessionId);
      setUserSummary(summary);
      setShowSummary(true);
    } catch (error) {
      console.error('Error loading summary:', error);
      alert('Error loading summary. Please make sure you have voted on at least one section.');
    }
  };

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
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
          <Link href="/" className="mt-4 text-blue-600 hover:underline">
            Back to bills list
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
          <Link href="/" className="text-sm text-blue-600 hover:underline mb-2 inline-block">
            ← Back to bills
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
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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

        {/* Section Cards */}
        <div className="space-y-6">
          {bill.sections.map((section) => (
            <div key={section.id} className="bg-white rounded-lg shadow-md overflow-hidden">
              {/* Section Header */}
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">
                  {section.section_key}: {section.heading}
                </h3>
              </div>

              {/* Summary */}
              <div className="px-6 py-4">
                {section.summary_json ? (
                  <>
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Summary</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                      {section.summary_json.plain_summary_bullets.map((bullet, i) => (
                        <li key={i}>{bullet}</li>
                      ))}
                    </ul>

                    {/* Evidence */}
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
                ) : (
                  <div className="bg-blue-50 border border-blue-200 rounded p-4">
                    <p className="text-sm text-blue-900 font-medium mb-1">
                      💡 AI Summary Not Available
                    </p>
                    <p className="text-sm text-blue-700">
                      To enable AI-generated summaries, add an OpenAI or Anthropic API key to your backend configuration. 
                      You can still vote on this section!
                    </p>
                  </div>
                )}

                {/* Official Source Link */}
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

              {/* Vote Buttons */}
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
