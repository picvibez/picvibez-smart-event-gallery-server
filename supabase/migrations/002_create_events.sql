-- ============================================================
-- Module 1: Events
-- ============================================================

CREATE TABLE IF NOT EXISTS public.events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    event_type          TEXT NOT NULL DEFAULT 'Wedding',
    start_time          TIMESTAMPTZ,
    end_time            TIMESTAMPTZ,
    privacy_mode        TEXT NOT NULL DEFAULT 'public'
                        CHECK (privacy_mode IN ('public', 'approval', 'passcode')),
    storage_limit_bytes BIGINT NOT NULL DEFAULT 536870912, -- 500 MB
    current_storage_bytes BIGINT NOT NULL DEFAULT 0,
    is_watermark_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by          UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_created_by ON public.events(created_by);

ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events FORCE ROW LEVEL SECURITY;
