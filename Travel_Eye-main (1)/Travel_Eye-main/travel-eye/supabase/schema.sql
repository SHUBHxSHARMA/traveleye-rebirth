-- Run this in Supabase: SQL Editor → New query → paste → Run

create extension if not exists "uuid-ossp";

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz default now()
);

create table if not exists public.sites (
  id uuid primary key default uuid_generate_v4(),
  slug text unique not null,
  name text not null,
  city text not null,
  country text not null,
  description text not null,
  latitude double precision not null,
  longitude double precision not null,
  cover_image text,
  created_at timestamptz default now()
);

create table if not exists public.checkpoints (
  id uuid primary key default uuid_generate_v4(),
  site_id uuid not null references public.sites(id) on delete cascade,
  slug text not null,
  name text not null,
  category text not null,
  short_description text not null,
  story text not null,
  latitude double precision not null,
  longitude double precision not null,
  radius_meters integer not null default 40,
  reference_image_url text,
  sort_order integer not null default 0,
  unique(site_id, slug)
);

create table if not exists public.discoveries (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  checkpoint_id uuid not null references public.checkpoints(id) on delete cascade,
  method text not null check (method in ('gps', 'photo_match', 'manual')),
  discovered_at timestamptz default now(),
  unique(user_id, checkpoint_id)
);

alter table public.profiles enable row level security;
alter table public.sites enable row level security;
alter table public.checkpoints enable row level security;
alter table public.discoveries enable row level security;

create policy "Profiles are viewable by owner"
  on public.profiles for select using (auth.uid() = id);

create policy "Profiles are updatable by owner"
  on public.profiles for update using (auth.uid() = id);

create policy "Users can insert own profile"
  on public.profiles for insert with check (auth.uid() = id);

create policy "Sites are public"
  on public.sites for select using (true);

create policy "Checkpoints are public"
  on public.checkpoints for select using (true);

create policy "Users view own discoveries"
  on public.discoveries for select using (auth.uid() = user_id);

create policy "Users insert own discoveries"
  on public.discoveries for insert with check (auth.uid() = user_id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1)));
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
