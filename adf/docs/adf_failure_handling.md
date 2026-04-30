| Failure Scenario            | Handling                                                         |
| --------------------------- | ---------------------------------------------------------------- |
| PostgreSQL connection fails | Pipeline fails; no files are trusted                             |
| ADLS write fails            | Run fails; no watermark update                                   |
| Count mismatch              | Mark validation failed; investigate before downstream processing |
| Incremental copy fails      | Do not update watermark                                          |
| No new incremental rows     | Skip copy and keep old watermark                                 |
| Partial/failed run output   | Isolated by run_id and can be ignored or replayed                |
| Wrong source/table config   | Detected through validation counts and path checks               |
