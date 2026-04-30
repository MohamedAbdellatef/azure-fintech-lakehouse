| Entity | Old Watermark       | New Watermark       | Rows Copied | ADLS Path                         | Watermark Updated? | Status      |
| ------ | ------------------- | ------------------- | ----------: | --------------------------------- | ------------------ | ----------- |
| users  | 2026-04-29 10:00:00 | 2026-04-29 12:30:00 |          3 | raw/landing/users/incremental/... | Yes                | Success     |
| users  | 2026-04-29 12:30:00 | NULL                |           0 | N/A                               | No                 | No new rows |
