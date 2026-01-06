import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { getMyBillsVotes, MyBillVoteItem, logout } from '../lib/api';
import { getAccessToken } from '../lib/auth';

export default function MyVotesPage() {
  const router = useRouter();
  const [items, setItems] = useState<MyBillVoteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.push(`/login?returnTo=${encodeURIComponent('/my-votes')}`);
      return;
    }

    (async () => {
      try {
        setLoading(true);
        const resp = await getMyBillsVotes();
        setItems(resp.items);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load vote history');
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <Link href="/" className="text-sm text-blue-600 hover:underline">← Back</Link>
              <h1 className="mt-2 text-2xl font-bold text-gray-900">My votes</h1>
            </div>
            <button
              onClick={() => {
                logout();
                router.push('/');
              }}
              className="text-sm text-gray-600 hover:underline"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        {loading && <p className="text-gray-600">Loading…</p>}
        {error && <p className="text-red-700">{error}</p>}

        {!loading && !error && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            {items.length === 0 ? (
              <div className="p-6 text-gray-600">No votes yet.</div>
            ) : (
              <ul className="divide-y divide-gray-200">
                {items.map((b) => (
                  <li key={b.bill_id} className="p-4">
                    <Link href={`/bills/${b.bill_id}`} className="text-blue-600 hover:underline">
                      {b.bill_type.toUpperCase()}. {b.bill_number}
                    </Link>
                    <p className="text-sm text-gray-700 mt-1">{b.title}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      Voted sections: {b.voted_sections} • Latest action: {formatDate(b.latest_action_date)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
