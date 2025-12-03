--
-- PostgreSQL database dump
--

\restrict RJkMX5dNtmQysigykKnpLh8sxNF8yQlCuH9IhcSrghkkfMT327dfI0ewQr2Uv5M

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg12+1)
-- Dumped by pg_dump version 15.15 (Debian 15.15-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP FUNCTION IF EXISTS public.update_user_api_keys_updated_at();
--
-- Name: update_user_api_keys_updated_at(); Type: FUNCTION; Schema: public; Owner: agentic_pm
--

CREATE FUNCTION public.update_user_api_keys_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_user_api_keys_updated_at() OWNER TO agentic_pm;

--
-- PostgreSQL database dump complete
--

\unrestrict RJkMX5dNtmQysigykKnpLh8sxNF8yQlCuH9IhcSrghkkfMT327dfI0ewQr2Uv5M

