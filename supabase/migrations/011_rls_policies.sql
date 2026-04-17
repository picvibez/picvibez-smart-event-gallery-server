-- ============================================================
-- Row Level Security Policies
-- ============================================================

-- Helper: check if a user is an approved member of an event
CREATE OR REPLACE FUNCTION public.is_approved_member(ev_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.event_members
        WHERE event_id = ev_id
          AND profile_id = auth.uid()
          AND status = 'approved'
    );
$$;

-- Helper: check if a user is admin of an event
CREATE OR REPLACE FUNCTION public.is_event_admin(ev_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.event_members
        WHERE event_id = ev_id
          AND profile_id = auth.uid()
          AND status = 'approved'
          AND role = 'admin'
    );
$$;


-- ═══════════ profiles ═══════════

CREATE POLICY "Anyone can read profiles"
    ON public.profiles FOR SELECT
    USING (true);

CREATE POLICY "Users update own profile"
    ON public.profiles FOR UPDATE
    USING (id = auth.uid());


-- ═══════════ events ═══════════

CREATE POLICY "Approved members read events"
    ON public.events FOR SELECT
    USING (public.is_approved_member(id));

CREATE POLICY "Admins update events"
    ON public.events FOR UPDATE
    USING (public.is_event_admin(id));

CREATE POLICY "Authenticated users create events"
    ON public.events FOR INSERT
    WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Admins delete events"
    ON public.events FOR DELETE
    USING (public.is_event_admin(id));


-- ═══════════ event_invites ═══════════

CREATE POLICY "Anyone reads active invites"
    ON public.event_invites FOR SELECT
    USING (is_active = true);

CREATE POLICY "Admins manage invites"
    ON public.event_invites FOR ALL
    USING (public.is_event_admin(event_id));


-- ═══════════ event_members ═══════════

CREATE POLICY "Users read own membership"
    ON public.event_members FOR SELECT
    USING (profile_id = auth.uid());

CREATE POLICY "Approved members see fellow members"
    ON public.event_members FOR SELECT
    USING (public.is_approved_member(event_id));

CREATE POLICY "Anyone can request to join"
    ON public.event_members FOR INSERT
    WITH CHECK (profile_id = auth.uid());

CREATE POLICY "Admins manage members"
    ON public.event_members FOR UPDATE
    USING (public.is_event_admin(event_id));

CREATE POLICY "Users leave or admins kick"
    ON public.event_members FOR DELETE
    USING (profile_id = auth.uid() OR public.is_event_admin(event_id));


-- ═══════════ media ═══════════

CREATE POLICY "Approved members view approved media"
    ON public.media FOR SELECT
    USING (
        public.is_approved_member(event_id)
        AND (is_approved = true OR uploader_id = auth.uid() OR public.is_event_admin(event_id))
    );

CREATE POLICY "Approved non-guest members upload media"
    ON public.media FOR INSERT
    WITH CHECK (
        public.is_approved_member(event_id)
        AND uploader_id = auth.uid()
    );

CREATE POLICY "Uploader or admin deletes media"
    ON public.media FOR DELETE
    USING (uploader_id = auth.uid() OR public.is_event_admin(event_id));

CREATE POLICY "Admin moderates media"
    ON public.media FOR UPDATE
    USING (public.is_event_admin(event_id));


-- ═══════════ ai_face_clusters ═══════════

CREATE POLICY "Members view face clusters"
    ON public.ai_face_clusters FOR SELECT
    USING (public.is_approved_member(event_id));

CREATE POLICY "Service role manages clusters"
    ON public.ai_face_clusters FOR ALL
    USING (true);


-- ═══════════ media_faces ═══════════

CREATE POLICY "Members view media faces"
    ON public.media_faces FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.media m
            WHERE m.id = media_id
              AND public.is_approved_member(m.event_id)
        )
    );

CREATE POLICY "Service role manages media faces"
    ON public.media_faces FOR ALL
    USING (true);


-- ═══════════ people ═══════════

CREATE POLICY "Admins manage their own people"
    ON public.people FOR ALL
    USING (managed_by_admin_id = auth.uid());


-- ═══════════ relationships ═══════════

CREATE POLICY "Admins manage relationships of their people"
    ON public.relationships FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.people
            WHERE id = person_id
              AND managed_by_admin_id = auth.uid()
        )
    );


-- ═══════════ event_guests_metadata ═══════════

CREATE POLICY "Admins control guest metadata"
    ON public.event_guests_metadata FOR ALL
    USING (public.is_event_admin(event_id));


-- ═══════════ media_likes ═══════════

CREATE POLICY "Members manage own likes"
    ON public.media_likes FOR ALL
    USING (
        user_id = auth.uid()
        AND EXISTS (
            SELECT 1 FROM public.media m
            WHERE m.id = media_id
              AND public.is_approved_member(m.event_id)
        )
    );

CREATE POLICY "Members view likes"
    ON public.media_likes FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.media m
            WHERE m.id = media_id
              AND public.is_approved_member(m.event_id)
        )
    );


-- ═══════════ media_comments ═══════════

CREATE POLICY "Members add comments"
    ON public.media_comments FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND EXISTS (
            SELECT 1 FROM public.media m
            WHERE m.id = media_id
              AND public.is_approved_member(m.event_id)
        )
    );

CREATE POLICY "Members view comments"
    ON public.media_comments FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.media m
            WHERE m.id = media_id
              AND public.is_approved_member(m.event_id)
        )
    );

CREATE POLICY "Owner or admin deletes comments"
    ON public.media_comments FOR DELETE
    USING (
        user_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM public.media m
            WHERE m.id = media_id
              AND public.is_event_admin(m.event_id)
        )
    );


-- ═══════════ transactions ═══════════

CREATE POLICY "Users view own transactions"
    ON public.transactions FOR SELECT
    USING (user_id = auth.uid());


-- ═══════════ vendors ═══════════

CREATE POLICY "Public read vendors"
    ON public.vendors FOR SELECT
    USING (true);
