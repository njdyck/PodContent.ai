-- =============================================================
-- PodContent.ai — Supabase DB Schema (MVP)
-- =============================================================
-- Abhängigkeit: Supabase Auth (auth.uid()), Storage Bucket "audio"
-- =============================================================

-- 1. PROFILES (erweitert auth.users)
-- =============================================================
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  full_name text,
  credits_remaining int not null default 3, -- MVP: 3 Free Generations
  plan text not null default 'free' check (plan in ('free', 'starter', 'pro')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Auto-Create Profile on Signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', '')
  );
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 2. EPISODES (ein Upload = eine Episode)
-- =============================================================
create table public.episodes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null default 'Unbenannte Episode',
  audio_storage_path text not null,       -- Pfad im Storage Bucket
  audio_duration_seconds int,             -- Dauer in Sekunden
  status text not null default 'uploaded'
    check (status in ('uploaded', 'transcribing', 'generating', 'completed', 'failed')),
  error_message text,                     -- Bei Fehler: was ging schief
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_episodes_user_id on public.episodes(user_id);
create index idx_episodes_status on public.episodes(status);

-- 3. TRANSCRIPTS
-- =============================================================
create table public.transcripts (
  id uuid primary key default gen_random_uuid(),
  episode_id uuid not null unique references public.episodes(id) on delete cascade,
  full_text text not null,
  language text default 'de',
  word_count int,
  created_at timestamptz not null default now()
);

-- 4. GENERATED CONTENT
-- =============================================================
create table public.contents (
  id uuid primary key default gen_random_uuid(),
  episode_id uuid not null references public.episodes(id) on delete cascade,
  content_type text not null
    check (content_type in ('linkedin_post', 'blog_article', 'newsletter', 'tweet_thread', 'show_notes')),
  title text,                             -- Überschrift / Hook
  body text not null,                     -- Der generierte Content
  metadata jsonb default '{}',            -- Flexible Zusatzdaten (Hashtags, Keywords etc.)
  is_favorite boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_contents_episode_id on public.contents(episode_id);
create index idx_contents_type on public.contents(content_type);

-- 5. UPDATED_AT TRIGGER
-- =============================================================
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

create trigger trg_episodes_updated_at
  before update on public.episodes
  for each row execute function public.set_updated_at();

create trigger trg_contents_updated_at
  before update on public.contents
  for each row execute function public.set_updated_at();

-- =============================================================
-- RLS POLICIES
-- =============================================================

alter table public.profiles enable row level security;
alter table public.episodes enable row level security;
alter table public.transcripts enable row level security;
alter table public.contents enable row level security;

-- PROFILES: User sieht nur sich selbst
create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- EPISODES: User sieht/erstellt nur eigene
create policy "Users can view own episodes"
  on public.episodes for select
  using (auth.uid() = user_id);

create policy "Users can insert own episodes"
  on public.episodes for insert
  with check (auth.uid() = user_id);

create policy "Users can update own episodes"
  on public.episodes for update
  using (auth.uid() = user_id);

create policy "Users can delete own episodes"
  on public.episodes for delete
  using (auth.uid() = user_id);

-- n8n Service Role: braucht Zugriff auf alle Episoden (via service_role key)
-- → service_role bypassed RLS automatisch in Supabase

-- TRANSCRIPTS: User sieht nur Transkripte eigener Episoden
create policy "Users can view own transcripts"
  on public.transcripts for select
  using (
    exists (
      select 1 from public.episodes
      where episodes.id = transcripts.episode_id
      and episodes.user_id = auth.uid()
    )
  );

-- CONTENTS: User sieht/bearbeitet nur Content eigener Episoden
create policy "Users can view own contents"
  on public.contents for select
  using (
    exists (
      select 1 from public.episodes
      where episodes.id = contents.episode_id
      and episodes.user_id = auth.uid()
    )
  );

create policy "Users can update own contents"
  on public.contents for update
  using (
    exists (
      select 1 from public.episodes
      where episodes.id = contents.episode_id
      and episodes.user_id = auth.uid()
    )
  );

-- =============================================================
-- STORAGE BUCKET
-- =============================================================
-- Manuell im Supabase Dashboard erstellen oder via SQL:

insert into storage.buckets (id, name, public)
values ('audio', 'audio', false);

-- Storage Policies: User kann nur in eigenen Ordner uploaden
create policy "Users can upload own audio"
  on storage.objects for insert
  with check (
    bucket_id = 'audio'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Users can read own audio"
  on storage.objects for select
  using (
    bucket_id = 'audio'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Users can delete own audio"
  on storage.objects for delete
  using (
    bucket_id = 'audio'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
