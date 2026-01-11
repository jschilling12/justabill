import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { getAccessToken, clearAccessToken } from '../lib/auth';
import { getMe, updateMeAffiliation, updateSurveyOptIn } from '../lib/api';

const AGE_RANGES = ['18-24', '25-34', '35-44', '45-54', '55-64', '65+'];

export default function ProfilePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [affiliationRaw, setAffiliationRaw] = useState<string>('');
  const [savedBucket, setSavedBucket] = useState<string | null>(null);

  // Survey panel state
  const [surveyOptIn, setSurveyOptIn] = useState(false);
  const [zipCode, setZipCode] = useState('');
  const [ageRange, setAgeRange] = useState('');
  const [surveyLoading, setSurveyLoading] = useState(false);

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
        setSurveyOptIn(me.survey_opt_in || false);
        setZipCode(me.zip_code || '');
        setAgeRange(me.age_range || '');
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const save = async () => {
    setError(null);
    setSuccessMsg(null);
    try {
      const me = await updateMeAffiliation(affiliationRaw.trim() ? affiliationRaw.trim() : null);
      setAffiliationRaw(me.affiliation_raw || '');
      setSavedBucket(me.affiliation_bucket || null);
      setSuccessMsg('Profile saved!');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save');
    }
  };

  const handleSurveyOptIn = async (optIn: boolean) => {
    setError(null);
    setSuccessMsg(null);
    setSurveyLoading(true);
    try {
      const response = await updateSurveyOptIn({
        opt_in: optIn,
        zip_code: zipCode || undefined,
        age_range: ageRange || undefined,
      });
      setSurveyOptIn(response.survey_opt_in);
      setSuccessMsg(response.message);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update survey preferences');
    } finally {
      setSurveyLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold text-gray-900">Profile</h1>

          {loading && <p className="mt-4 text-gray-600">Loading…</p>}
          {error && <p className="mt-4 text-red-700">{error}</p>}
          {successMsg && <p className="mt-4 text-green-700">{successMsg}</p>}

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

              {/* Survey Panel Opt-In Section */}
              <div className="mt-8 pt-6 border-t border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <span>📊</span> Survey Panel
                </h2>
                <p className="mt-2 text-sm text-gray-600">
                  Join our anonymous survey panel to help us understand how people feel about legislation. 
                  Your individual votes are never shared — we only publish aggregated, anonymized insights 
                  (e.g., "65% of users in Texas supported Section 2").
                </p>

                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800 font-medium">What we collect (if you opt in):</p>
                  <ul className="mt-2 text-sm text-blue-700 list-disc list-inside space-y-1">
                    <li>Your anonymized votes (aggregated with other users)</li>
                    <li>ZIP code (to understand regional sentiment)</li>
                    <li>Age range (for demographic insights)</li>
                    <li>Political affiliation (already collected above)</li>
                  </ul>
                  <p className="mt-3 text-sm text-blue-800 font-medium">What we NEVER do:</p>
                  <ul className="mt-2 text-sm text-blue-700 list-disc list-inside space-y-1">
                    <li>Share your individual votes or identity</li>
                    <li>Publish data for groups with fewer than 25 people</li>
                    <li>Sell your personal information</li>
                  </ul>
                </div>

                {/* Optional demographic fields */}
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-500">ZIP Code (optional)</label>
                    <input
                      value={zipCode}
                      onChange={(e) => setZipCode(e.target.value.replace(/\D/g, '').slice(0, 5))}
                      placeholder="e.g., 90210"
                      maxLength={5}
                      className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-500">Age Range (optional)</label>
                    <select
                      value={ageRange}
                      onChange={(e) => setAgeRange(e.target.value)}
                      className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm"
                    >
                      <option value="">Select...</option>
                      {AGE_RANGES.map((range) => (
                        <option key={range} value={range}>{range}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Opt-in toggle */}
                <div className="mt-4 flex items-center gap-4">
                  {surveyOptIn ? (
                    <>
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                        ✓ Opted In
                      </span>
                      <button
                        onClick={() => handleSurveyOptIn(false)}
                        disabled={surveyLoading}
                        className="px-4 py-2 border border-red-300 text-red-700 rounded text-sm hover:bg-red-50 disabled:opacity-50"
                      >
                        {surveyLoading ? 'Updating...' : 'Leave Survey Panel'}
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => handleSurveyOptIn(true)}
                      disabled={surveyLoading}
                      className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
                    >
                      {surveyLoading ? 'Updating...' : 'Join Survey Panel'}
                    </button>
                  )}
                </div>

                {surveyOptIn && (
                  <button
                    onClick={() => handleSurveyOptIn(true)}
                    disabled={surveyLoading}
                    className="mt-2 text-sm text-blue-600 hover:underline"
                  >
                    Update ZIP/Age preferences
                  </button>
                )}
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
