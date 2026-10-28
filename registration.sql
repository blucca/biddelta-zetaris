CREATE LIGHTNING DATABASE biddelta_public DESCRIBE BY "Historical official procurement notices";


CREATE LIGHTNING DATABASE biddelta_tasks DESCRIBE BY "Synthetic supplier task REST feed";


CREATE LIGHTNING REST TABLE notice_releases_raw FROM biddelta_public REQUEST(endpoint "http://172.18.0.1:18085/notice_releases.json", method "get", response_type "json", http_encoding "URLENCODED") HEADER () BODY ();


CREATE LIGHTNING REST TABLE notice_changes_raw FROM biddelta_public REQUEST(endpoint "http://172.18.0.1:18085/notice_changes.json", method "get", response_type "json", http_encoding "URLENCODED") HEADER () BODY ();


CREATE LIGHTNING REST TABLE task_dependencies_raw FROM biddelta_tasks REQUEST(endpoint "http://172.18.0.1:18085/task_dependencies.json", method "get", response_type "json", http_encoding "URLENCODED") HEADER () BODY ();


CREATE LIGHTNING REST TABLE tasks_current_raw FROM biddelta_tasks REQUEST(endpoint "http://172.18.0.1:18085/tasks_current.json", method "get", response_type "json", http_encoding "URLENCODED") HEADER () BODY ();
