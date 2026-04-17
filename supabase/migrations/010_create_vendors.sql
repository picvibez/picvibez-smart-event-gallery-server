-- ============================================================
-- Module: Vendor Marketplace
-- ============================================================

CREATE TABLE IF NOT EXISTS public.vendors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    category        TEXT NOT NULL
                    CHECK (category IN ('photography', 'decor', 'dj', 'catering')),
    description     TEXT,
    rating          NUMERIC(2,1) CHECK (rating >= 0 AND rating <= 5),
    price_range     TEXT,
    contact_url     TEXT,
    image_url       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vendors_category ON public.vendors(category);

ALTER TABLE public.vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vendors FORCE ROW LEVEL SECURITY;
