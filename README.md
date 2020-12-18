# Script to Automate the updating of Avrae Collections

Script Intentions
-----------------
1. Take in env vars
  * `AVRAE_TOKEN` - Token used to communicate with Avrae API
  * `MODIFIED_FILES` - List of modified files (Created using `jitterbit/get-changed-files@master`, see `example-workflow.yml`)
  * `COLLECTIONS_ID_FILE` - Relative path of the JSON file that contains the file with collection ID's. (See `example-collections.json`)
2. Check every directory that is specified in the Collections ID file. If the collection directory contains a file that is modified (List comp, `[file for file in modified_files if file.startswith(collection_dir)]`), Make a request against the collection with `/full` to get all the aliases.
3. Take the collection request and compare the alias/snippet names against the files in the collection directory that have been modified. Store the modified files as a list
4. Take the stored aliases+file paths, update the aliases and set them to active