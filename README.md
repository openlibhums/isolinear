# isolinear
Isolinear is a plugin for Janeway that integrates the preprint workflow into the journal workflow.

## How this plugin works
Isolinear inserts HTML into Janeway hooks including:

- Unassigned
  - Adds a new action button allowing the Editor to approve the article for preprint publication. This creates a preprint record of the article in a headless repository.  
- Review
  - Adds the option for Editors to create a new preprint version using an revised version of the authors manuscript.
 
Preprint records are created automatically using the article metadata. Isolinear will take a manuscript file in DOCX, OTF or RTF format and convert it, with Pandoc, to PDF and insert a cover sheet with the title.
