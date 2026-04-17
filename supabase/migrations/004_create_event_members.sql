-- ============================================================
-- Module 1: Event Members (RBAC + Verification)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.event_members (
    event_id            UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    profile_id          UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role                TEXT NOT NULL DEFAULT 'guest'
                        CHECK (role IN ('admin', 'member', 'guest')),
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected', 'banned')),
    joined_via_invite_id UUID REFERENCES public.event_invites(id) ON DELETE SET NULL,
    auto_upload_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (event_id, profile_id)
);

CREATE INDEX idx_event_members_profile ON public.event_members(profile_id);
CREATE INDEX idx_event_members_status ON public.event_members(event_id, status);

ALTER TABLE public.event_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_members FORCE ROW LEVEL SECURITY;
