-- ============================================================
-- Module 4: Admin Secrets (Gifts / Notes)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.event_guests_metadata (
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    person_id       UUID NOT NULL REFERENCES public.people(id) ON DELETE CASCADE,
    gift_received   TEXT,
    thank_you_sent  BOOLEAN NOT NULL DEFAULT FALSE,
    admin_notes     TEXT,
    PRIMARY KEY (event_id, person_id)
);

ALTER TABLE public.event_guests_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_guests_metadata FORCE ROW LEVEL SECURITY;


-- ============================================================
-- Billing: Transactions
-- ============================================================

CREATE TABLE IF NOT EXISTS public.transactions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id            UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    stripe_payment_id   TEXT NOT NULL,
    type                TEXT NOT NULL CHECK (type IN ('base_plan', 'storage_addon')),
    amount_cents        INTEGER NOT NULL,
    purchased_bytes     BIGINT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_transactions_event ON public.transactions(event_id);

ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions FORCE ROW LEVEL SECURITY;
