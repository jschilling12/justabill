import axios from 'axios';
import { getAccessToken, setAccessToken, clearAccessToken } from './auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Get session ID from localStorage or create new one
function getSessionId(): string {
  if (typeof window === 'undefined') return '';
  
  let sessionId = localStorage.getItem('session_id');
  if (!sessionId) {
    sessionId = crypto.randomUUID();
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

// API functions
export async function getBills(
  page: number = 1,
  pageSize: number = 20,
  popular?: boolean,
  lawImpactOnly?: boolean
) {
  const params: Record<string, any> = { page, page_size: pageSize };
  if (popular) params.popular = true;
  if (lawImpactOnly) params.law_impact_only = true;

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

export default api;
