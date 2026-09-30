-- =============================================================================
-- schema.sql
-- Run this in the Supabase SQL editor (Project -> SQL Editor -> New query)
-- to create every table this app needs. Safe to re-run: uses IF NOT EXISTS.
-- =============================================================================

create extension if not exists "pgcrypto";  -- for gen_random_uuid(), if you prefer DB-generated ids

-- -----------------------------------------------------------------------------
-- USERS  (mirrors auth.users one-to-one; user_id == auth.users.id)
-- -----------------------------------------------------------------------------
create table if not exists users (
    user_id           text primary key,
    name              text not null,
    username          text not null unique,
    email             text not null unique,
    profile_picture   text,                 -- storage path, not a URL
    bio               text default '',
    interests         jsonb default '[]',
    is_moderator      boolean default false,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);
create index if not exists idx_users_username on users (lower(username));

-- -----------------------------------------------------------------------------
-- SKILLS
-- -----------------------------------------------------------------------------
create table if not exists skills (
    skill_id       text primary key,
    user_id        text not null references users(user_id) on delete cascade,
    skill_name     text not null,
    category       text not null,
    current_level  text not null check (current_level in ('BEGINNER','INTERMEDIATE','ADVANCED')),
    target_level   text not null check (target_level in ('BEGINNER','INTERMEDIATE','ADVANCED')),
    start_date     date not null,
    target_date    date,
    status         text not null default 'ACTIVE' check (status in ('ACTIVE','PAUSED','COMPLETED')),
    description    text default '',
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);
create index if not exists idx_skills_user on skills (user_id);
create index if not exists idx_skills_category on skills (category);

-- -----------------------------------------------------------------------------
-- GOALS
-- -----------------------------------------------------------------------------
create table if not exists goals (
    goal_id        text primary key,
    skill_id       text not null references skills(skill_id) on delete cascade,
    user_id        text not null references users(user_id) on delete cascade,
    title          text not null,
    target_value   numeric not null check (target_value > 0),
    current_value  numeric not null default 0,
    unit           text not null default 'hours',
    deadline       date,
    status         text not null default 'ACTIVE' check (status in ('ACTIVE','COMPLETED','ABANDONED')),
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);
create index if not exists idx_goals_skill on goals (skill_id);
create index if not exists idx_goals_user on goals (user_id);

-- -----------------------------------------------------------------------------
-- MILESTONES
-- -----------------------------------------------------------------------------
create table if not exists milestones (
    milestone_id   text primary key,
    goal_id        text not null references goals(goal_id) on delete cascade,
    title          text not null,
    target_value   numeric not null check (target_value > 0),
    achieved       boolean not null default false,
    achieved_at    timestamptz
);
create index if not exists idx_milestones_goal on milestones (goal_id);

-- -----------------------------------------------------------------------------
-- PRACTICE_SESSIONS
-- -----------------------------------------------------------------------------
create table if not exists practice_sessions (
    session_id        text primary key,
    user_id           text not null references users(user_id) on delete cascade,
    skill_id          text not null references skills(skill_id) on delete cascade,
    duration_minutes  numeric not null check (duration_minutes > 0),
    activity          text default '',
    notes             text default '',
    practiced_at      date not null,
    created_at        timestamptz not null default now()
);
create index if not exists idx_sessions_user on practice_sessions (user_id);
create index if not exists idx_sessions_skill on practice_sessions (skill_id);
create index if not exists idx_sessions_user_date on practice_sessions (user_id, practiced_at);

-- -----------------------------------------------------------------------------
-- POSTS
-- -----------------------------------------------------------------------------
create table if not exists posts (
    post_id       text primary key,
    user_id       text not null references users(user_id) on delete cascade,
    skill_id      text references skills(skill_id) on delete set null,
    content       text default '',
    media_path    text,
    visibility    text not null default 'PUBLIC' check (visibility in ('PUBLIC','FOLLOWERS')),
    like_count    integer not null default 0,
    comment_count integer not null default 0,
    created_at    timestamptz not null default now()
);
create index if not exists idx_posts_user on posts (user_id);
create index if not exists idx_posts_created on posts (created_at desc);
create index if not exists idx_posts_visibility_created on posts (visibility, created_at desc);

-- -----------------------------------------------------------------------------
-- COMMENTS
-- -----------------------------------------------------------------------------
create table if not exists comments (
    comment_id  text primary key,
    post_id     text not null references posts(post_id) on delete cascade,
    user_id     text not null references users(user_id) on delete cascade,
    text        text not null,
    created_at  timestamptz not null default now()
);
create index if not exists idx_comments_post on comments (post_id);

-- -----------------------------------------------------------------------------
-- LIKES  (composite key "<post_id>:<user_id>" enforces "one like per user")
-- -----------------------------------------------------------------------------
create table if not exists likes (
    like_id     text primary key,
    post_id     text not null references posts(post_id) on delete cascade,
    user_id     text not null references users(user_id) on delete cascade,
    created_at  timestamptz not null default now(),
    unique (post_id, user_id)
);
create index if not exists idx_likes_post on likes (post_id);

-- -----------------------------------------------------------------------------
-- FOLLOWS  (optional feature)
-- -----------------------------------------------------------------------------
create table if not exists follows (
    follow_id     text primary key,
    follower_id   text not null references users(user_id) on delete cascade,
    following_id  text not null references users(user_id) on delete cascade,
    created_at    timestamptz not null default now(),
    unique (follower_id, following_id)
);
create index if not exists idx_follows_follower on follows (follower_id);
create index if not exists idx_follows_following on follows (following_id);

-- -----------------------------------------------------------------------------
-- FILES  (metadata only — the bytes live in Supabase Storage)
-- -----------------------------------------------------------------------------
create table if not exists files (
    file_id       text primary key,
    owner_id      text not null references users(user_id) on delete cascade,
    kind          text not null check (kind in ('PROFILE_IMAGE','ACHIEVEMENT_IMAGE','POST_MEDIA')),
    storage_path  text not null,
    content_type  text not null,
    size_bytes    integer not null,
    created_at    timestamptz not null default now()
);
create index if not exists idx_files_owner on files (owner_id);

-- -----------------------------------------------------------------------------
-- REPORTS  (content moderation)
-- -----------------------------------------------------------------------------
create table if not exists reports (
    report_id    text primary key,   -- "<post_id>:<reporter_id>"
    post_id      text not null references posts(post_id) on delete cascade,
    reporter_id  text not null references users(user_id) on delete cascade,
    reason       text not null,
    status       text not null default 'OPEN' check (status in ('OPEN','REVIEWED','DISMISSED')),
    created_at   timestamptz not null default now()
);
create index if not exists idx_reports_status on reports (status);

-- =============================================================================
-- Row Level Security
-- The FastAPI backend uses the SERVICE-ROLE key (bypasses RLS) so that the
-- Python service layer is the single source of truth for authorization.
-- These policies are a defense-in-depth backstop in case a key is ever used
-- with the anon/public role directly.
-- =============================================================================
alter table users enable row level security;
alter table skills enable row level security;
alter table goals enable row level security;
alter table milestones enable row level security;
alter table practice_sessions enable row level security;
alter table posts enable row level security;
alter table comments enable row level security;
alter table likes enable row level security;
alter table follows enable row level security;
alter table files enable row level security;
alter table reports enable row level security;

create policy "public profiles are readable" on users for select using (true);
create policy "users manage own row" on users for all using (auth.uid()::text = user_id);

create policy "users manage own skills" on skills for all using (auth.uid()::text = user_id);
create policy "users manage own goals" on goals for all using (auth.uid()::text = user_id);
create policy "users manage own sessions" on practice_sessions for all using (auth.uid()::text = user_id);

create policy "public posts are readable" on posts for select using (visibility = 'PUBLIC');
create policy "users manage own posts" on posts for all using (auth.uid()::text = user_id);

create policy "comments are readable" on comments for select using (true);
create policy "users manage own comments" on comments for all using (auth.uid()::text = user_id);

create policy "likes are readable" on likes for select using (true);
create policy "users manage own likes" on likes for all using (auth.uid()::text = user_id);

create policy "follows are readable" on follows for select using (true);
create policy "users manage own follows" on follows for all using (auth.uid()::text = follower_id);

-- milestones/files/reports have RLS enabled with no policy defined here, which
-- means "deny all" under the anon/public role - correct, since only the
-- backend's service-role key (which bypasses RLS entirely) should touch them.
