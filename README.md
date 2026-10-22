# isolinear
Isolinear is a plugin for Janeway that integrates the preprint workflow into the journal workflow.

## How this plugin works
Isolinear inserts HTML into Janeway hooks including:

- Unassigned
  - Adds a new action button allowing the Editor to approve the article for preprint publication. This creates a preprint record of the article in a headless repository.  
- Review
  - Adds the option for Editors to create a new preprint version using an revised version of the authors manuscript.
 
Preprint records are created automatically using the article metadata. Isolinear will take a manuscript file in DOCX, OTF or RTF format and convert it, with Pandoc, to PDF and insert a cover sheet with the title.

Will require pandoc, pypdf and xetex

sudo apt-get install texlive-xetex
## Janeway 1.8

This branch runs on Janeway 1.8.2. Janeway 1.8.2 doesn't have the hooks and settings isolinear needs, so the Janeway checkout needs a patch that backports them from 1.9. The patch isn't kept in this repository. Apply it, then load the new setting:

```
cd /path/to/janeway
git apply /path/to/isolinear-1.8.2.patch
python src/manage.py load_default_settings
```

Every template and Python change in the patch has a comment saying it can be removed when upgrading to Janeway 1.9. The new `uses_isolinear_plugin` setting in `journal_defaults.json` can't carry a comment, but it's identical to the one in 1.9.
