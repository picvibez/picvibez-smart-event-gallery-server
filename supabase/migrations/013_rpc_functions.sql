-- ============================================================
-- RPC Functions
-- ============================================================

-- Family tree recursive traversal
CREATE OR REPLACE FUNCTION public.get_family_tree(starting_person_id UUID)
RETURNS TABLE (id UUID, first_name TEXT, last_name TEXT, generation INT)
LANGUAGE plpgsql
STABLE SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE family_tree AS (
        -- Base: starting person
        SELECT p.id, p.first_name, p.last_name, 0 AS generation
        FROM public.people p
        WHERE p.id = starting_person_id

        UNION

        -- Recursive: traverse relationships
        SELECT p.id, p.first_name, p.last_name,
               CASE
                   WHEN r.relationship_type = 'parent' THEN ft.generation - 1
                   WHEN r.relationship_type = 'child'  THEN ft.generation + 1
                   ELSE ft.generation
               END AS generation
        FROM public.people p
        INNER JOIN public.relationships r ON p.id = r.related_person_id
        INNER JOIN family_tree ft ON r.person_id = ft.id
    )
    SELECT DISTINCT ON (family_tree.id)
        family_tree.id,
        family_tree.first_name,
        family_tree.last_name,
        family_tree.generation
    FROM family_tree;
END;
$$;
