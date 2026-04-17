-- ============================================================
-- Module 4: Social (Likes + Comments)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.media_likes (
    media_id    UUID NOT NULL REFERENCES public.media(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (media_id, user_id)
);

ALTER TABLE public.media_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.media_likes FORCE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS public.media_comments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id    UUID NOT NULL REFERENCES public.media(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    comment_text TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_comments_media ON public.media_comments(media_id, created_at);

ALTER TABLE public.media_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.media_comments FORCE ROW LEVEL SECURITY;
