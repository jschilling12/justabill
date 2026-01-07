import axios from 'axios';
import { getAccessToken, setAccessToken, clearAccessToken } from './auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Generate UUID with fallback for browsers that don't support crypto.randomUUID
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Get session ID from localStorage or create new one
function getSessionId(): string {
  if (typeof window === 'undefined') return '';
  
  let sessionId = localStorage.getItem('session_id');
  if (!sessionId) {
    sessionId = generateUUID();
    localStorage.setItem('session_id', sessionId);
  }
  return sessionId;
}

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add session ID to all requests
api.interceptors.request.use((config) => {
  const sessionId = getSessionId();
  if (sessionId) {
    config.headers['X-Session-ID'] = sessionId;
  }

  const token = getAccessToken();
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

export interface AuthTokenResponse {
  access_token: string;
  token_type: 'bearer';
}

export interface UserMe {
  id: string;
  email?: string | null;
  affiliation_raw?: string | null;
  affiliation_bucket?: string | null;
}

export interface Bill {
  id: string;
  congress: number;
  bill_type: string;
  bill_number: number;
  title: string;
  introduced_date?: string;
  latest_action_date?: string;
  status?: string;
  is_popular?: boolean;
  popularity_score?: number;
  popularity_updated_at?: string | null;
  is_law_impact_candidate?: boolean;
}

export interface BillSection {
  id: string;
  bill_id: string;
  section_key: string;
  heading: string;
  division?: string | null;
  title?: string | null;
  title_heading?: string | null;
  order_index: number;
  section_text: string;
  summary_json?: {
    plain_summary_bullets: string[];
    key_terms?: string[];
    who_it_affects?: string[];
    uncertainties?: string[];
  };
  evidence_quotes?: string[];
}

export interface BillWithSections extends Bill {
  sections: BillSection[];
  source_urls?: {
    congress_gov?: string;
    govinfo?: string;
  };
}

export interface UserBillSummary {
  id: string;
  upvote_count: number;
  downvote_count: number;
  skip_count: number;
  upvote_ratio: number | null;
  verdict_label: string;
  liked_sections: any[];
  disliked_sections: any[];
}

export interface VoteCounts {
  up: number;
  down: number;
  skip: number;
  total: number;
}

export interface VotePercents {
  agree_pct: number;
  disagree_pct: number;
}

export interface VoteStats {
  counts: VoteCounts;
  percents: VotePercents;
}

export interface SectionVoteStatsItem {
  section_id: string;
  counts: VoteCounts;
  percents: VotePercents;
}

export interface BillSectionVoteStatsResponse {
  bill_id: string;
  items: SectionVoteStatsItem[];
}

export interface VoteSubmitResponse {
  vote: {
    id: string;
    user_id: string;
    bill_id: string;
    section_id: string;
    vote: 'up' | 'down' | 'skip';
    created_at: string;
    updated_at?: string | null;
  };
  updated: boolean;
}

export interface MyVotesForBillResponse {
  bill_id: string;
  user_id: string;
  votes: Array<{ section_id: string; vote: 'up' | 'down' | 'skip' }>;
}

export interface MyBillVoteItem {
  bill_id: string;
  congress: number;
  bill_type: string;
  bill_number: number;
  title: string;
  latest_action_date?: string | null;
  voted_sections: number;
}

export interface MyBillsVotesResponse {
  items: MyBillVoteItem[];
}

// Bill status enum
export type BillStatus = 
  | 'introduced'
  | 'in_committee'
  | 'passed_house'
  | 'passed_senate'
  | 'in_conference'
  | 'passed_both'
  | 'vetoed'
  | 'enacted';

export const BILL_STATUS_LABELS: Record<BillStatus, string> = {
  introduced: 'Introduced',
  in_committee: 'In Committee',
  passed_house: 'Passed House',
  passed_senate: 'Passed Senate',
  in_conference: 'In Conference',
  passed_both: 'Passed Both Chambers',
  vetoed: 'Vetoed',
  enacted: 'Signed into Law',
};

// Statuses that are "in progress" (for voting)
export const ACTIVE_STATUSES: BillStatus[] = [
  'introduced',
  'in_committee',
  'passed_house',
  'passed_senate',
  'in_conference',
  'passed_both',
];

// President terms for grouping enacted bills
export interface President {
  name: string;
  party: 'R' | 'D';
  startDate: string;
  endDate: string;
}

export const PRESIDENTS: President[] = [
  // Current
  { name: 'Donald Trump', party: 'R', startDate: '2025-01-20', endDate: '2029-01-20' },
  { name: 'Joe Biden', party: 'D', startDate: '2021-01-20', endDate: '2025-01-20' },
  // 2000s-2020s
  { name: 'Donald Trump', party: 'R', startDate: '2017-01-20', endDate: '2021-01-20' },
  { name: 'Barack Obama', party: 'D', startDate: '2009-01-20', endDate: '2017-01-20' },
  { name: 'George W. Bush', party: 'R', startDate: '2001-01-20', endDate: '2009-01-20' },
  // 1990s
  { name: 'Bill Clinton', party: 'D', startDate: '1993-01-20', endDate: '2001-01-20' },
  { name: 'George H.W. Bush', party: 'R', startDate: '1989-01-20', endDate: '1993-01-20' },
  // 1980s
  { name: 'Ronald Reagan', party: 'R', startDate: '1981-01-20', endDate: '1989-01-20' },
  // 1970s
  { name: 'Jimmy Carter', party: 'D', startDate: '1977-01-20', endDate: '1981-01-20' },
  { name: 'Gerald Ford', party: 'R', startDate: '1974-08-09', endDate: '1977-01-20' },
  { name: 'Richard Nixon', party: 'R', startDate: '1969-01-20', endDate: '1974-08-09' },
  // 1960s (in case any old bills)
  { name: 'Lyndon B. Johnson', party: 'D', startDate: '1963-11-22', endDate: '1969-01-20' },
  { name: 'John F. Kennedy', party: 'D', startDate: '1961-01-20', endDate: '1963-11-22' },
];

export function getPresidentForDate(dateString: string | null | undefined): President | null {
  if (!dateString) return null;
  const date = new Date(dateString);
  for (const pres of PRESIDENTS) {
    const start = new Date(pres.startDate);
    const end = new Date(pres.endDate);
    if (date >= start && date < end) {
      return pres;
    }
  }
  return null;
}

export function groupBillsByPresident(bills: Bill[]): Map<string, Bill[]> {
  const grouped = new Map<string, Bill[]>();
  
  for (const bill of bills) {
    const pres = getPresidentForDate(bill.latest_action_date);
    const key = pres ? pres.name : 'Unknown';
    
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key)!.push(bill);
  }
  
  return grouped;
}

// API functions
export async function getBills(
  page: number = 1,
  pageSize: number = 20,
  popular?: boolean,
  lawImpactOnly?: boolean,
  status?: BillStatus
) {
  const params: Record<string, any> = { page, page_size: pageSize };
  if (popular) params.popular = true;
  if (lawImpactOnly) params.law_impact_only = true;
  if (status) params.status = status;

  const response = await api.get('/bills', { params });
  return response.data;
}

export async function getBill(billId: string): Promise<BillWithSections> {
  const response = await api.get(`/bills/${billId}`);
  return response.data;
}

export async function submitVote(billId: string, sectionId: string, vote: 'up' | 'down' | 'skip') {
  const response = await api.post(`/votes/vote?bill_id=${billId}`, {
    section_id: sectionId,
    vote: vote
  });
  return response.data;
}

export async function submitBulkVotes(
  billId: string,
  sectionIds: string[],
  vote: 'up' | 'down' | 'skip'
) {
  const response = await api.post(`/votes/bulk-vote?bill_id=${billId}`, sectionIds.map((sectionId) => ({
    section_id: sectionId,
    vote,
  })));
  return response.data;
}

export async function getUserSummary(billId: string, userId: string): Promise<UserBillSummary> {
  const response = await api.get(`/bills/${billId}/user-summary`, {
    params: { user_id: userId }
  });
  return response.data;
}

export async function getMySummary(billId: string): Promise<UserBillSummary> {
  const response = await api.get(`/bills/${billId}/my-summary`);
  return response.data;
}

export async function getBillVoteStats(billId: string): Promise<VoteStats> {
  const response = await api.get(`/votes/bill/${billId}/stats`);
  return response.data;
}

export async function getBillsVoteStats(billIds: string[]): Promise<Record<string, VoteStats>> {
  if (!billIds.length) return {};
  const response = await api.get(`/votes/bills/stats`, {
    params: { bill_ids: billIds.join(',') },
  });
  const out: Record<string, VoteStats> = {};
  (response.data.items || []).forEach((it: any) => {
    out[it.bill_id] = { counts: it.counts, percents: it.percents };
  });
  return out;
}

export async function getBillSectionVoteStats(billId: string): Promise<BillSectionVoteStatsResponse> {
  const response = await api.get(`/votes/bill/${billId}/section-stats`);
  return response.data;
}

export async function getMyBillsVotes(): Promise<MyBillsVotesResponse> {
  const response = await api.get(`/votes/my-bills`);
  return response.data;
}

export async function getMyVotesForBill(billId: string): Promise<MyVotesForBillResponse> {
  const response = await api.get(`/votes/my-votes/${billId}`);
  return response.data;
}

export async function register(email: string, password: string): Promise<AuthTokenResponse> {
  const response = await api.post(`/auth/register`, { email, password });
  const tokenResp = response.data as AuthTokenResponse;
  if (tokenResp?.access_token) setAccessToken(tokenResp.access_token);
  return tokenResp;
}

export async function login(email: string, password: string): Promise<AuthTokenResponse> {
  const response = await api.post(`/auth/login`, { email, password });
  const tokenResp = response.data as AuthTokenResponse;
  if (tokenResp?.access_token) setAccessToken(tokenResp.access_token);
  return tokenResp;
}

export async function logout() {
  clearAccessToken();
}

export async function getMe(): Promise<UserMe> {
  const response = await api.get(`/auth/me`);
  return response.data;
}

export async function updateMeAffiliation(affiliation_raw: string | null): Promise<UserMe> {
  const response = await api.patch(`/auth/me`, { affiliation_raw });
  return response.data;
}

// Fetch enacted bills for a specific president (triggers n8n workflow)
export interface FetchEnactedResponse {
  status: string;
  president: string;
  congress_range: {
    start: number;
    end: number;
    years: string;
  };
  message?: string;
}

export async function fetchEnactedByPresident(presidentName: string): Promise<FetchEnactedResponse> {
  const response = await api.post(`/ingest/fetch-enacted-by-president?president_name=${encodeURIComponent(presidentName)}`);
  return response.data;
}

// Get popular enacted bills by president (top N per president)
export interface PopularBillByPresident {
  bill_id: string;
  bill_type: string;
  bill_number: number;
  title: string;
  vote_count: number;
  latest_action_date: string | null;
}

export async function getPopularBillsByPresident(topN: number = 2): Promise<Record<string, PopularBillByPresident[]>> {
  const response = await api.get(`/bills/popular-by-president?top_n=${topN}`);
  return response.data;
}

// President to Congress mapping (client-side reference)
export const PRESIDENT_CONGRESS_MAP: Record<string, { start: number; end: number; years: string }> = {
  "Donald Trump 2nd": { start: 119, end: 119, years: "2025-2029" },
  "Joe Biden": { start: 117, end: 118, years: "2021-2025" },
  "Donald Trump": { start: 115, end: 116, years: "2017-2021" },
  "Barack Obama": { start: 111, end: 114, years: "2009-2017" },
  "George W. Bush": { start: 107, end: 110, years: "2001-2009" },
  "Bill Clinton": { start: 103, end: 106, years: "1993-2001" },
  "George H.W. Bush": { start: 101, end: 102, years: "1989-1993" },
  "Ronald Reagan": { start: 97, end: 100, years: "1981-1989" },
  "Jimmy Carter": { start: 95, end: 96, years: "1977-1981" },
  "Gerald Ford": { start: 94, end: 94, years: "1974-1977" },
  "Richard Nixon": { start: 91, end: 93, years: "1969-1974" },
  "Lyndon B. Johnson": { start: 89, end: 90, years: "1963-1969" },
  "John F. Kennedy": { start: 87, end: 88, years: "1961-1963" },
};

export default api;
