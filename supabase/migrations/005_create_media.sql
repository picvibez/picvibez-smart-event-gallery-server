-- ============================================================
-- Module 2: Media (Photos / Videos)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.media (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    uploader_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    s3_key          TEXT NOT NULL,
    thumbnail_key   TEXT,
    cdn_url         TEXT NOT NULL DEFAULT '',
    file_name       TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    media_type      TEXT NOT NULL CHECK (media_type IN ('image', 'video')),
    is_approved     BOOLEAN NOT NULL DEFAULT TRUE,
    ai_labels       JSONB,
    captured_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_media_event ON public.media(event_id, created_at DESC);
CREATE INDEX idx_media_uploader ON public.media(uploader_id);
CREATE INDEX idx_media_labels ON public.media USING GIN (ai_labels);

ALTER TABLE public.media ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.media FORCE ROW LEVEL SECURITY;

-- Storage quota trigger: increment on insert
CREATE OR REPLACE FUNCTION public.update_storage_on_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    UPDATE public.events
    SET current_storage_bytes = current_storage_bytes + NEW.file_size_bytes
    WHERE id = NEW.event_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_media_insert_storage ON public.media;
CREATE TRIGGER trg_media_insert_storage
    AFTER INSERT ON public.media
    FOR EACH ROW EXECUTE FUNCTION public.update_storage_on_insert();

-- Storage quota trigger: decrement on delete
CREATE OR REPLACE FUNCTION public.update_storage_on_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    UPDATE public.events
    SET current_storage_bytes = GREATEST(0, current_storage_bytes - OLD.file_size_bytes)
    WHERE id = OLD.event_id;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_media_delete_storage ON public.media;
CREATE TRIGGER trg_media_delete_storage
    AFTER DELETE ON public.media
    FOR EACH ROW EXECUTE FUNCTION public.update_storage_on_delete();
