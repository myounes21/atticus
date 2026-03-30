-- 002_roles_and_hardening.sql
-- - migrate legacy paralegal users to lawyer
-- - tighten role constraints to admin/lawyer only

BEGIN;

UPDATE users
   SET role = 'lawyer'
 WHERE role = 'paralegal';

ALTER TABLE users
  DROP CONSTRAINT IF EXISTS users_role_check;

ALTER TABLE users
  ADD CONSTRAINT users_role_check
  CHECK (role IN ('admin', 'lawyer'));

COMMIT;
