-- ============================================================
-- Module 3: Family Tree Engine (Graph Model)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.people (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name          TEXT NOT NULL,
    last_name           TEXT,
    date_of_birth       DATE,
    face_cluster_id     UUID REFERENCES public.ai_face_clusters(id) ON DELETE SET NULL,
    managed_by_admin_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE
);

CREATE INDEX idx_people_admin ON public.people(managed_by_admin_id);

ALTER TABLE public.people ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.people FORCE ROW LEVEL SECURITY;

-- Now add deferred FK from profiles.person_id -> people.id
ALTER TABLE public.profiles
    ADD CONSTRAINT fk_profiles_person
    FOREIGN KEY (person_id) REFERENCES public.people(id) ON DELETE SET NULL;

-- And from ai_face_clusters.person_id -> people.id
ALTER TABLE public.ai_face_clusters
    ADD CONSTRAINT fk_clusters_person
    FOREIGN KEY (person_id) REFERENCES public.people(id) ON DELETE SET NULL;


CREATE TABLE IF NOT EXISTS public.relationships (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id           UUID NOT NULL REFERENCES public.people(id) ON DELETE CASCADE,
    related_person_id   UUID NOT NULL REFERENCES public.people(id) ON DELETE CASCADE,
    relationship_type   TEXT NOT NULL
                        CHECK (relationship_type IN ('parent', 'child', 'spouse', 'sibling')),
    CONSTRAINT no_self_relationship CHECK (person_id <> related_person_id)
);

CREATE INDEX idx_relationships_person ON public.relationships(person_id);
CREATE INDEX idx_relationships_related ON public.relationships(related_person_id);

ALTER TABLE public.relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.relationships FORCE ROW LEVEL SECURITY;
