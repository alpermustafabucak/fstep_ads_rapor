-- Supabase SQL Editor'de bir defa çalıştırın.
create extension if not exists pgcrypto;
create table if not exists public.firms (
 id uuid primary key default gen_random_uuid(),
 name text not null unique,
 website text not null default '',
 currency text not null default 'GBP',
 created_at timestamptz not null default now()
);
create table if not exists public.reports (
 id uuid primary key default gen_random_uuid(),
 firm_id uuid not null references public.firms(id) on delete cascade,
 report_date date not null,
 file_path text not null unique,
 file_name text not null,
 file_hash text not null,
 spend numeric(14,2),
 impressions integer,
 clicks integer,
 conversions integer,
 cpc numeric(14,2),
 ctr numeric(9,2),
 cpa numeric(14,2),
 extracted_text text,
 created_at timestamptz not null default now(),
 unique (firm_id,report_date,file_hash)
);
create index if not exists reports_firm_date_idx on public.reports(firm_id,report_date desc);
alter table public.firms enable row level security;
alter table public.reports enable row level security;
-- RLS açık, anon/authenticated erişimine politika verilmedi.
-- Uygulama yalnızca sunucudaki service_role ile sorgular.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values ('ads-reports','ads-reports',false,15728640,array['application/pdf'])
on conflict (id) do update set public=false;
