-- ============================================================
-- Module 1: Event Invites (Link / QR / NFC)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.event_invites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    invite_type     TEXT NOT NULL DEFAULT 'link'
                    CHECK (invite_type IN ('link', 'qr', 'nfc')),
    token           UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    passcode_hash   TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    usage_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_event_invites_token ON public.event_invites(token);
CREATE INDEX idx_event_invites_event ON public.event_invites(event_id);

ALTER TABLE public.event_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_invites FORCE ROW LEVEL SECURITY;

-- RPC to atomically increment usage_count
CREATE OR REPLACE FUNCTION public.increment_invite_usage(invite_id_param UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    UPDATE public.event_invites
    SET usage_count = usage_count + 1
    WHERE id = invite_id_param;
END;
$$;
