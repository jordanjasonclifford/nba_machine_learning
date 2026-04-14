SELECT viewname
FROM pg_views
WHERE schemaname = 'public'
AND viewname LIKE 'mart_%'
ORDER BY viewname;