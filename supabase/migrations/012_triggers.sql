-- ============================================================
-- Additional triggers (beyond those in individual table files)
-- ============================================================

-- Invite usage counter trigger
CREATE OR REPLACE FUNCTION public.track_invite_usage()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    IF NEW.joined_via_invite_id IS NOT NULL THEN
        UPDATE public.event_invites
        SET usage_count = usage_count + 1
        WHERE id = NEW.joined_via_invite_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_member_joined_invite ON public.event_members;
CREATE TRIGGER trg_member_joined_invite
    AFTER INSERT ON public.event_members
    FOR EACH ROW EXECUTE FUNCTION public.track_invite_usage();


-- Enable Realtime for key tables
ALTER PUBLICATION supabase_realtime ADD TABLE public.media;
ALTER PUBLICATION supabase_realtime ADD TABLE public.event_members;
ALTER PUBLICATION supabase_realtime ADD TABLE public.media_comments;
ALTER PUBLICATION supabase_realtime ADD TABLE public.media_likes;
