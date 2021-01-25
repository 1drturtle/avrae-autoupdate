# Script to Automate the updating of Avrae Collections

Automatically handles updating workshop aliases and snippets. Has support for updating GVARs.

Installation Instructions
-------------------------
WIP

Script Intentions
-----------------
1. Take in env vars
  * `AVRAE_TOKEN` - Token used to communicate with Avrae API
  * `MODIFIED_FILES` - List of modified files (Created using `jitterbit/get-changed-files@master`, see `example-workflow.yml`)
  * `COLLECTIONS_ID_FILE` - Relative path of the JSON file that contains the file with collection ID's. (See `example-collections.json`)
  * `GVARS_ID_FILE` - Path to JSON of GVAR ID's to update if found in an active folder (See `example-gvars.json`)