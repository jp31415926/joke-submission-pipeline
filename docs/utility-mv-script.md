Write a bash script that moves a file from one stage directory to another. Each directory contains files to be processed in that stage. The directory is named with a stage name. I want to be able to put in a source and destination stage name on the command line and the script will translate that to a directory names based on a list that is hard coded in the script. The map between directory name and stage name is listed below.

`Usage: script.sh <src-stage> <dst-stage> <item-id>`

- `<src-stage>` - source stage name that maps to a - directory below

- `<dst-stage>` - destination name stage that maps to a directory below

- `<item-id>` - name of file to move. if the '.txt' extension is not include, append it. if there is any directory path part of the name, remove and ignore it. Only use the basename.

| stage name           | directory name          |
| -------------------- | ----------------------- |
| parse                | 01_parse                |
| dedup                | 02_dedup                |
| clean_check          | 03_clean_check          |
| format               | 04_format               |
| categorize           | 05_categorize           |
| title                | 06_title                |
| ready_for_review     | 08_ready_for_review     |
| rejected_parse       | 50_rejected_parse       |
| rejected_dedup       | 51_rejected_dedup       |
| rejected_clean_check | 52_rejected_clean_check |
| rejected_format      | 53_rejected_format      |
| rejected_categorize  | 54_rejected_categorize  |
| rejected_title       | 55_rejected_title       |
