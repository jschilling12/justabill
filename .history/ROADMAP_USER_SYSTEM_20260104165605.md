# User System & Enhanced Voting Roadmap

## Current State
- Voting exists but requires hardcoded user_id
- No authentication system
- No vote aggregation display
- No user history/dashboard

## Target State
- User registration & login
- Optional political affiliation after voting
- Aggregate vote counts per section
- User vote history & dashboard
- Real-time vote updates as more people vote

---

## Phase 1: User Authentication (Essential)

### Backend Changes
1. **Add User Model** (`backend/app/models.py`)
   - id (UUID)
   - email (unique, indexed)
   - password_hash
   - username (optional)
   - political_affiliation (enum: democrat, republican, independent, other, prefer_not_to_say, null)
   - created_at, updated_at

2. **Add Auth Endpoints** (`backend/app/routers/auth.py`)
   - `POST /auth/register` - Create account
   - `POST /auth/login` - Returns JWT token
   - `GET /auth/me` - Get current user info
   - `PATCH /auth/me` - Update profile (including political affiliation)

3. **Add JWT Middleware**
   - Install `python-jose`, `passlib[bcrypt]`
   - Create token generation/validation utilities
   - Protect voting endpoints to require auth

### Frontend Changes
1. **Add Auth Context** (`frontend/contexts/AuthContext.tsx`)
   - Store user state, token in localStorage
   - Provide login/logout/register functions

2. **Create Auth Pages**
   - `/register` - Registration form
   - `/login` - Login form
   - `/profile` - User profile & settings

3. **Add Auth UI Components**
   - Nav bar user menu (login/logout)
   - Protected route wrapper

---

## Phase 2: Vote Aggregation & Display

### Backend Changes
1. **Update Vote Model** (already has user_id)
   - Ensure proper foreign key to User

2. **Add Aggregate Endpoints** (`backend/app/routers/votes.py`)
   - `GET /bills/{bill_id}/sections/{section_id}/vote-stats`
     - Returns: `{up_votes: 10, down_votes: 3, skip_votes: 2, total: 15}`
   - `GET /bills/{bill_id}/vote-stats` - Aggregate for whole bill

3. **Political Affiliation Breakdown** (optional)
   - `GET /bills/{bill_id}/sections/{section_id}/vote-stats?by_affiliation=true`
   - Returns breakdown: `{democrat: {up: 5, down: 1}, republican: {up: 2, down: 3}, ...}`

### Frontend Changes
1. **Show Aggregate Counts on Sections**
   - Display "👍 23 | 👎 7" next to each section
   - Color code based on ratio (green if mostly up, red if mostly down)

2. **Add Political Affiliation Prompt**
   - After first vote (if affiliation is null), show modal:
     - "Help us understand perspectives! What's your political affiliation? (Optional)"
     - Buttons: Democrat, Republican, Independent, Other, Prefer not to say, Skip
   - Calls `PATCH /auth/me` with affiliation

---

## Phase 3: User Vote History & Dashboard

### Backend Changes
1. **Add Vote History Endpoints**
   - `GET /users/me/votes` - All votes by current user
     - Pagination, filtering by date
   - `GET /users/me/votes/summary` - Stats: total votes, bills voted on, support ratio

### Frontend Changes
1. **Create Dashboard Page** (`/dashboard`)
   - "Your Voting History"
   - List of bills you've voted on with support score
   - Click to see individual section votes
   - Show updated aggregate counts (so you can see how opinion shifted)

2. **Add "Continue Voting" Feature**
   - Dashboard shows bills you partially voted on
   - Quick link to resume voting

---

## Phase 4: Enhanced Features (Future)

1. **Voting Analytics**
   - Trend charts: "Opinion over time"
   - Heatmap: "Most controversial sections"
   - Political breakdown visualization

2. **Social Features**
   - Share your vote summary
   - See how your votes compare to overall averages
   - "People like you also supported..."

3. **Notifications**
   - Email when a bill you voted on advances
   - Weekly digest of new bills

---

## Migration Path

### Step 1: Auth System (Non-Breaking)
- Deploy user system alongside existing anonymous voting
- Add optional login to nav

### Step 2: Require Auth for Voting
- Show "Sign in to vote" prompt for anonymous users
- Migrate any test votes to a "test user" account

### Step 3: Add Aggregation
- Backfill vote stats
- Update UI to show counts

### Step 4: Add Dashboard
- Create dashboard for logged-in users

---

## Database Migrations

### Migration 1: Add users table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    political_affiliation VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
```

### Migration 2: Add vote aggregation table (for performance)
```sql
CREATE TABLE section_vote_stats (
    section_id UUID PRIMARY KEY REFERENCES bill_sections(id) ON DELETE CASCADE,
    up_votes INTEGER DEFAULT 0,
    down_votes INTEGER DEFAULT 0,
    skip_votes INTEGER DEFAULT 0,
    total_votes INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger to update stats on vote insert/update/delete
```

---

## Timeline Estimate
- Phase 1 (Auth): 2-3 hours
- Phase 2 (Aggregation): 1-2 hours
- Phase 3 (Dashboard): 1-2 hours
- Total: 4-7 hours for full implementation

---

## Security Considerations
- Use bcrypt for password hashing
- JWT tokens with reasonable expiration (7 days)
- Rate limit auth endpoints
- Validate email format
- HTTPS required in production
- CSRF protection for API calls
