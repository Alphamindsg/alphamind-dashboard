-- MEM-001: optional persisted confidence score for company memories.
--
-- This migration is additive and must not be executed without explicit approval
-- for the exact Supabase environment. The application remains functional before
-- this migration by calculating confidence in the browser.

ALTER TABLE company_memories
  ADD COLUMN IF NOT EXISTS confidence_score smallint;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'company_memories_confidence_score_check'
      AND conrelid = 'company_memories'::regclass
  ) THEN
    ALTER TABLE company_memories
      ADD CONSTRAINT company_memories_confidence_score_check
      CHECK (confidence_score IS NULL OR confidence_score BETWEEN 0 AND 100);
  END IF;
END
$$;

COMMENT ON COLUMN company_memories.confidence_score IS
  'Deterministic 0-100 content completeness/evidence score. Not a guarantee of factual truth.';
