import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { getAccessToken, clearAccessToken } from '../lib/auth';
import { getMe, updateMeAffiliation } from '../lib/api';

export default function ProfilePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [affiliationRaw, setAffiliationRaw] = useState<string>('');
  const [savedBucket, setSavedBucket] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.push(`/login?returnTo=${encodeURIComponent('/profile')}`);
      return;
    }

    (async () => {
      try {
        setLoading(true);
        const me = await getMe();
        setEmail(me.email || null);
        setAffiliationRaw(me.affiliation_raw || '');
        setSavedBucket(me.affiliation_bucket || null);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const save = async () => {
    setError(null);
    try {
      const me = await updateMeAffiliation(affiliationRaw.trim() ? affiliationRaw.trim() : null);
      setAffiliationRaw(me.affiliation_raw || '');
      setSavedBucket(me.affiliation_bucket || null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold text-gray-900">Profile</h1>

          {loading && <p className="mt-4 text-gray-600">Loading…</p>}
          {error && <p className="mt-4 text-red-700">{error}</p>}

          {!loading && !error && (
            <>
              <div className="mt-4">
                <p className="text-sm text-gray-500">Email</p>
                <p className="text-sm text-gray-900">{email || '—'}</p>
              </div>

              <div className="mt-4">
                <p className="text-sm text-gray-500">Political affiliation (optional)</p>
                <input
                  value={affiliationRaw}
                  onChange={(e) => setAffiliationRaw(e.target.value)}
                  placeholder="e.g., Republican, Democrat, Independent"
                  className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
                <p className="mt-1 text-xs text-gray-500">Saved bucket: {savedBucket || 'none'}</p>
              </div>

              <div className="mt-4 flex gap-2">
                <button onClick={save} className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                  Save
                </button>
                <button
                  onClick={() => {
                    clearAccessToken();
                    router.push('/');
                  }}
                  className="px-4 py-2 border border-gray-300 rounded text-sm"
                >
                  Log out
                </button>
              </div>

              <div className="mt-6 p-3 bg-gray-100 rounded text-xs text-gray-600">
                This app is informational. It summarizes bill text and reflects your votes; it does not provide legal, financial, or political advice.
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
