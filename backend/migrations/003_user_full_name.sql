-- 003_user_full_name.sql
-- Add display names for user-friendly assignment in admin UI.

BEGIN;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS full_name TEXT;

UPDATE users
   SET full_name = INITCAP(REPLACE(SPLIT_PART(email, '@', 1), '.', ' '))
 WHERE full_name IS NULL OR BTRIM(full_name) = '';

COMMIT;
