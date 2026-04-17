/**
 * Supabase Edge Function: validate-passcode
 *
 * Securely validates an event invite passcode server-side.
 * The passcode hash never reaches the client.
 *
 * POST /validate-passcode
 * Body: { token: string, passcode: string }
 * Returns: { success: true, event_id: string } or 403
 */
import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import * as bcrypt from "https://deno.land/x/bcrypt@v0.4.1/mod.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const authHeader = req.headers.get("Authorization");
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: "Missing authorization" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser(authHeader.replace("Bearer ", ""));

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: "Invalid token" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { token, passcode } = await req.json();

    if (!token || !passcode) {
      return new Response(
        JSON.stringify({ error: "token and passcode are required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { data: invite, error: inviteError } = await supabase
      .from("event_invites")
      .select("id, event_id, passcode_hash, is_active")
      .eq("token", token)
      .single();

    if (inviteError || !invite || !invite.is_active) {
      return new Response(
        JSON.stringify({ error: "Invalid or expired invite" }),
        { status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (!invite.passcode_hash) {
      return new Response(
        JSON.stringify({ error: "This invite does not require a passcode" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const isValid = await bcrypt.compare(passcode, invite.passcode_hash);
    if (!isValid) {
      return new Response(
        JSON.stringify({ error: "Invalid passcode" }),
        { status: 403, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Passcode correct -- insert user as approved member
    const { error: memberError } = await supabase.from("event_members").upsert(
      {
        event_id: invite.event_id,
        profile_id: user.id,
        role: "guest",
        status: "approved",
        joined_via_invite_id: invite.id,
      },
      { onConflict: "event_id,profile_id" }
    );

    if (memberError) {
      console.error("Member insert error:", memberError);
      return new Response(
        JSON.stringify({ error: "Failed to join event" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, event_id: invite.event_id }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error("Unexpected error:", err);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
