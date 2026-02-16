### TODO.md - The TO-DO list
When one of these is implemented, tested and confirmed by the user, check the box to indicate it is complete.

LDD stands for Left for Developer/Designer to Decide. In other words, I don't care about this particular detail, so use your best engineering judgment to pick the best way and keep going.

1. [x] From this point forward, when Claude makes changes, it should run `git commit` with a descriptive commit message. Update CLAUDE.md accordingly.
2. [x] Sometimes `joke-pipeline.py --status` returns an error because it can't access a file (probably because it was moved). Make the script handle this properly.
3. [ ] Make stage scripts check for the presence of the file `[project directory]/ALL_STOP` before starting work on the next file in it's stage queue. If that file exists, it should exit gracefully. When`joke-pipeline.py` is first started (before the main loop), it should check for that file and delete it if it exists. The name and path to `ALL_STOP` should set in `config.py`.
4. [ ] When a script is operating on a file, the file remains in the stage directory. Prefer it was moved to the `[stage]/tmp/` directory so it won't get picked up by another script. (Preparation for multiple concurrent stage handles.)
5. [ ] When a script is operating on a file, make it write the joke ID to a status file (name LDD) in the stage directory. When it is done with that file it deletes the file, or just makes it empty (LDD). Change `joke-pipeline.py --status` to display main and prior pipelines in one column so there's more room to the right and display the ID from the status file next to the pipeline stage name and counts.
6. [ ] When a script moves a joke to one of the reject stage directories, append the joke ID and the reason given (on one line) to a `reject_[stage]/failure.log` file.
7. [ ] 