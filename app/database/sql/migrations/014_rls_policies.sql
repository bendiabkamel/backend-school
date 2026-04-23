-- 014_rls_policies.sql
-- Base RLS policies for M0 schema.
-- Note: service role bypasses RLS by design; these policies secure direct authenticated access paths.

CREATE OR REPLACE FUNCTION public.app_is_admin()
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.users u
    WHERE u.id = auth.uid()
      AND u.role = 'admin'
  );
$$;

CREATE OR REPLACE FUNCTION public.app_is_staff()
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.users u
    WHERE u.id = auth.uid()
      AND u.role IN ('admin', 'formateur')
  );
$$;

GRANT EXECUTE ON FUNCTION public.app_is_admin() TO authenticated;
GRANT EXECUTE ON FUNCTION public.app_is_staff() TO authenticated;

DO $$
DECLARE
  tbl TEXT;
  policy_name TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'academic_sessions',
    'semesters',
    'school_classes',
    'sections',
    'courses',
    'student_enrollments',
    'teacher_assignments',
    'academic_settings',
    'school_exams',
    'exam_rules',
    'grading_systems',
    'grade_rules',
    'marks',
    'final_marks',
    'attendance_sessions',
    'attendance_records',
    'assignments',
    'assignment_submissions',
    'routines',
    'events',
    'notices',
    'promotions',
    'promotion_audit_events'
  ]
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);

    policy_name := format('p_%s_staff_all', tbl);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', policy_name, tbl);
    EXECUTE format(
      'CREATE POLICY %I ON %I FOR ALL TO authenticated USING (public.app_is_staff()) WITH CHECK (public.app_is_staff())',
      policy_name,
      tbl
    );
  END LOOP;
END $$;

-- Student ownership read policies.
DROP POLICY IF EXISTS p_student_enrollments_owner_read ON student_enrollments;
CREATE POLICY p_student_enrollments_owner_read
  ON student_enrollments
  FOR SELECT
  TO authenticated
  USING (owner_user_id = auth.uid());

DROP POLICY IF EXISTS p_attendance_records_owner_read ON attendance_records;
CREATE POLICY p_attendance_records_owner_read
  ON attendance_records
  FOR SELECT
  TO authenticated
  USING (owner_user_id = auth.uid());

DROP POLICY IF EXISTS p_marks_owner_read ON marks;
CREATE POLICY p_marks_owner_read
  ON marks
  FOR SELECT
  TO authenticated
  USING (owner_user_id = auth.uid());

DROP POLICY IF EXISTS p_final_marks_owner_read ON final_marks;
CREATE POLICY p_final_marks_owner_read
  ON final_marks
  FOR SELECT
  TO authenticated
  USING (owner_user_id = auth.uid());

DROP POLICY IF EXISTS p_promotions_owner_read ON promotions;
CREATE POLICY p_promotions_owner_read
  ON promotions
  FOR SELECT
  TO authenticated
  USING (owner_user_id = auth.uid());

DROP POLICY IF EXISTS p_assignment_submissions_owner_rw ON assignment_submissions;
CREATE POLICY p_assignment_submissions_owner_rw
  ON assignment_submissions
  FOR ALL
  TO authenticated
  USING (owner_user_id = auth.uid())
  WITH CHECK (owner_user_id = auth.uid());

-- Authenticated read policies for school communication and timetable entities.
DROP POLICY IF EXISTS p_notices_auth_read ON notices;
CREATE POLICY p_notices_auth_read
  ON notices
  FOR SELECT
  TO authenticated
  USING (TRUE);

DROP POLICY IF EXISTS p_events_auth_read ON events;
CREATE POLICY p_events_auth_read
  ON events
  FOR SELECT
  TO authenticated
  USING (TRUE);

DROP POLICY IF EXISTS p_routines_auth_read ON routines;
CREATE POLICY p_routines_auth_read
  ON routines
  FOR SELECT
  TO authenticated
  USING (TRUE);

DROP POLICY IF EXISTS p_assignments_auth_read ON assignments;
CREATE POLICY p_assignments_auth_read
  ON assignments
  FOR SELECT
  TO authenticated
  USING (TRUE);

DROP POLICY IF EXISTS p_school_exams_auth_read ON school_exams;
CREATE POLICY p_school_exams_auth_read
  ON school_exams
  FOR SELECT
  TO authenticated
  USING (TRUE);

DROP POLICY IF EXISTS p_exam_rules_auth_read ON exam_rules;
CREATE POLICY p_exam_rules_auth_read
  ON exam_rules
  FOR SELECT
  TO authenticated
  USING (TRUE);
