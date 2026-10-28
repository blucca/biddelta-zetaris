WITH notice_releases AS (
SELECT
  item.ocid AS ocid,
  item.notice_id AS notice_id,
  item.prior_notice_id AS prior_notice_id,
  item.prior_notice_ref_pointer AS prior_notice_ref_pointer,
  item.title AS title,
  item.release_tags AS release_tags,
  item.published_at AS published_at,
  item.retrieved_at AS retrieved_at,
  item.as_of AS as_of,
  item.provenance_class AS provenance_class,
  item.replay_partition AS replay_partition,
  item.source_url AS source_url,
  item.api_url AS api_url,
  item.source_path AS source_path,
  item.source_sha256 AS source_sha256,
  item.release_pointer AS release_pointer
FROM biddelta_public.notice_releases_raw
LATERAL VIEW explode(rows) AS item
),
notice_changes AS (
SELECT
  item.ocid AS ocid,
  item.notice_id AS notice_id,
  item.prior_notice_id AS prior_notice_id,
  item.change_id AS change_id,
  item.as_of AS as_of,
  item.published_at AS published_at,
  item.provenance_class AS provenance_class,
  item.section AS section,
  item.label AS label,
  item.value_kind AS value_kind,
  item.old_value AS old_value,
  item.new_value AS new_value,
  item.source_url AS source_url,
  item.source_path AS source_path,
  item.source_sha256 AS source_sha256,
  item.change_pointer AS change_pointer,
  item.old_value_pointer AS old_value_pointer,
  item.new_value_pointer AS new_value_pointer
FROM biddelta_public.notice_changes_raw
LATERAL VIEW explode(rows) AS item
),
task_dependencies AS (
SELECT
  item.ocid AS ocid,
  item.dependency_id AS dependency_id,
  item.task_id AS task_id,
  item.target_type AS target_type,
  item.target_id AS target_id,
  item.relation AS relation,
  item.active_from_notice_id AS active_from_notice_id,
  item.as_of AS as_of,
  item.provenance_class AS provenance_class
FROM biddelta_tasks.task_dependencies_raw
LATERAL VIEW explode(rows) AS item
),
tasks_current AS (
SELECT
  item.ocid AS ocid,
  item.as_of AS as_of,
  item.snapshot_id AS snapshot_id,
  item.snapshot_version AS snapshot_version,
  item.provenance_class AS provenance_class,
  item.task_id AS task_id,
  item.row_kind AS row_kind,
  item.task_exists AS task_exists,
  item.task_version AS task_version,
  item.title AS title,
  item.status AS status,
  item.due_at AS due_at,
  item.notes AS notes,
  item.prior_approval_notice_id AS prior_approval_notice_id,
  item.task_sha256 AS task_sha256
FROM biddelta_tasks.tasks_current_raw
LATERAL VIEW explode(rows) AS item
),
visible_changes AS (
  SELECT c.*
  FROM notice_changes c
  JOIN notice_releases r
    ON r.ocid = c.ocid AND r.notice_id = c.notice_id
  WHERE r.ocid = 'ocds-h6vhtk-0470d3'
    AND r.published_at <= '2024-11-08T15:56:37Z'
), active_links AS (
  SELECT d.*
  FROM task_dependencies d
  JOIN notice_releases r
    ON r.ocid = d.ocid AND r.notice_id = d.active_from_notice_id
  WHERE r.published_at <= '2024-11-08T15:56:37Z'
), direct_impacts AS (
  SELECT l.ocid, l.task_id, c.notice_id, c.change_id
  FROM active_links l
  JOIN visible_changes c
    ON c.ocid = l.ocid AND c.section = l.target_id
  WHERE l.target_type = 'notice_section' AND l.relation = 'monitors_section'
), impacts AS (
  SELECT ocid, task_id, notice_id, change_id FROM direct_impacts
  UNION
  SELECT l.ocid, l.task_id, d.notice_id, d.change_id
  FROM active_links l
  JOIN direct_impacts d ON d.ocid = l.ocid AND d.task_id = l.target_id
  WHERE l.target_type = 'task' AND l.relation = 'requires_review'
)
SELECT i.task_id, i.change_id, c.section, c.old_value, c.new_value,
       c.source_sha256, c.old_value_pointer, c.new_value_pointer,
       t.snapshot_id, t.snapshot_version, t.task_exists, t.task_version,
       t.title, t.status, t.due_at, t.notes, t.prior_approval_notice_id, t.task_sha256,
       l.relation AS document_relation,
       d.document_id, d.availability, d.document_version, d.content_sha256
FROM impacts i
JOIN visible_changes c
  ON c.ocid = i.ocid AND c.notice_id = i.notice_id AND c.change_id = i.change_id
JOIN tasks_current t ON t.ocid = i.ocid AND t.task_id = i.task_id
LEFT JOIN active_links l
  ON l.ocid = i.ocid AND l.task_id = i.task_id AND l.target_type = 'document'
LEFT JOIN biddelta_document_pg.document_register d ON d.ocid = l.ocid AND d.document_id = l.target_id
ORDER BY i.task_id, i.change_id, d.document_id;
