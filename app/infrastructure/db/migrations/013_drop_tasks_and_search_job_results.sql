-- Rollback for created tables: tasks, search_job_results

-- Drop indexes first
DROP INDEX IF EXISTS idx_tasks_period;
DROP INDEX IF EXISTS idx_tasks_source_id;
DROP INDEX IF EXISTS idx_search_job_results_job_rank;
DROP INDEX IF EXISTS idx_search_job_results_job_id;

-- Drop tables
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS search_job_results;
