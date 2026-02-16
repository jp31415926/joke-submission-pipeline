# Integration Test Fixtures

This directory contains test data for comprehensive integration testing.

## Test Email Files

### email_clean_joke.txt
- **Purpose**: Test a clean joke that should pass all stages
- **Expected outcome**: Reaches 08_ready_for_review
- **Title**: Present (The Tech Support Call)
- **Categories**: Technology, Observational
- **Special notes**: Should pass cleanliness check with high confidence

### email_multiple_jokes.txt
- **Purpose**: Test email containing multiple jokes
- **Expected outcome**: Creates 3 separate joke files
- **Titles**: All present
- **Categories**: Various (Puns, Science, Technology)
- **Special notes**: Tests joke-extractor's ability to split emails

### email_no_title.txt
- **Purpose**: Test joke without title (title generation needed)
- **Expected outcome**: Reaches 08_ready_for_review with generated title
- **Title**: Blank (should be generated in categorized stage)
- **Categories**: Technology, Puns
- **Special notes**: Tests title generation LLM call

### email_poorly_formatted.txt
- **Purpose**: Test joke with poor formatting
- **Expected outcome**: Should be formatted by stage 04_clean_checked
- **Title**: Present but needs formatting
- **Categories**: Animals, Dad Jokes
- **Special notes**: Tests formatting LLM improvements

### email_animal_joke.txt
- **Purpose**: Test clean animal joke
- **Expected outcome**: Reaches 08_ready_for_review
- **Title**: Present (The Octopus)
- **Categories**: Animals, Puns
- **Special notes**: Clear categorization

### email_dad_joke.txt
- **Purpose**: Test classic dad joke
- **Expected outcome**: Reaches 08_ready_for_review
- **Title**: Present (The Graveyard)
- **Categories**: Dad Jokes, Dark Humor
- **Special notes**: Should be categorized correctly

## Test Scenarios

### Scenario 1: Clean Jokes (Pass All Stages)
- email_clean_joke.txt
- email_animal_joke.txt
- email_dad_joke.txt

Expected: All reach 08_ready_for_review

### Scenario 2: Multiple Jokes from One Email
- email_multiple_jokes.txt

Expected: Creates 3 joke files, all progress through pipeline

### Scenario 3: Title Generation
- email_no_title.txt

Expected: Title generated in categorized stage

### Scenario 4: Formatting Improvements
- email_poorly_formatted.txt

Expected: Content improved in clean_checked stage

## Creating Additional Test Data

To create new test email files:

1. Follow email format (From, To, Subject, Date, Message-ID, body)
2. Include joke content in body
3. Optionally include "Title:" prefix for jokes with titles
4. Save with descriptive filename in this directory

## Duplicate Testing

For duplicate detection testing, use existing jokes from the TF-IDF corpus
or create known duplicates with slight variations.
