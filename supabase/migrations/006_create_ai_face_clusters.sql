-- ============================================================
-- Module 2: AI Face Clusters + Media Faces mapping
-- ============================================================

CREATE TABLE IF NOT EXISTS public.ai_face_clusters (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id                UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    representative_image_url TEXT NOT NULL DEFAULT '',
    person_id               UUID,  -- FK added after people table exists
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_face_clusters_event ON public.ai_face_clusters(event_id);

ALTER TABLE public.ai_face_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_face_clusters FORCE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS public.media_faces (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id    UUID NOT NULL REFERENCES public.media(id) ON DELETE CASCADE,
    cluster_id  UUID NOT NULL REFERENCES public.ai_face_clusters(id) ON DELETE CASCADE,
    bounding_box JSONB NOT NULL DEFAULT '{}',
    confidence  REAL
);

CREATE INDEX idx_media_faces_media ON public.media_faces(media_id);
CREATE INDEX idx_media_faces_cluster ON public.media_faces(cluster_id);

ALTER TABLE public.media_faces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.media_faces FORCE ROW LEVEL SECURITY;
