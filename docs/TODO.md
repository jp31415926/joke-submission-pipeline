### TODO.md - The TO-DO list
When one of these is implemented, tested and confirmed by the user, check the box to indicate it is complete.

LDD stands for Left for Developer/Designer to Decide. In other words, I don't care about this particular detail, so use your best engineering judgment to pick the best way and keep going.

Completed items have been moved to `docs/COMPLETED-TODOS.md` for reference, if needed.

 17. [ ] The various stage names and pipeline directory names are inconsistent. Use these for the stage names: parse, dedup, clean_check, format, categorize, title. Use directory names that indicate what happens to files in the stage. e.g. 01_incoming -> 01_parse, 02_parsed -> 02_dedup, etc. Fix this throughout the code an docs. Rename all the main and priority stage directories. Make sure all the tests pass.
 18. [ ] The way the --retry mechanism works is too cumbersome. There are way too many options to type. Instead, if "--retry" is given, can we redefine the remaining command line arguments? For example: `joke-pipeline.py --retry <pipeline> <stage> <id1> <id2>`. Update docs and tests.
 19. [ ] I would like the full text of each reason to be included in a stage-based named header in the joke file. It's OK if the lines get very long. This will help with post-analysis. Do this for all stages where the LLM returns a reason. Update docs and tests.
 20. [ ] I want an additional indication that the title was LLM generated instead of provided by the submitter in a "Title-Source:" header in the joke file. Update docs and tests.
 21. [ ] I also want a stage-based named header indicating what LLM was used for that stage. Just use the info from OLLAMA_MODEL. Use "LLM-Model-Used:" for the header. Update docs and tests.
 22. [ ] PLACEHOLDER. Update docs and tests.