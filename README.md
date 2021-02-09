# Script to Automate the updating of Avrae Collections

Automatically handles updating workshop aliases and snippets. Has support for updating GVARs.

[Here's an example of a repository that would use this](https://github.com/1drturtle/test-avrae-autoupdate)

Installation Instructions
-------------------------
1. Get your Avrae Token. You can do this by going to [the Avrae Website](https://avrae.io) and opening up the developer console. Then, go to Storage, Local Storage, and copy the value of the avrae_token.
	* With your Avrae Token, go to your GitHub Repository and click settings. Then, near the bottom-left click Secrets. Click New Secret and call it `AVRAE_TOKEN`, and put your token into the value textbox.
2. Make a new folder in your repository called `.github/workflows`. In this folder make a document called `update_workflow.yml`. Paste the contents of the `example-workflow.yml` file (that exists in this repository) into your `update_workflow.yml`
3. In the base of your repository, make a file called `collections.json`. Inside this file, you will create a JSON dictionary, where each key is a folder path and the value is the ID the collection. You can get the ID of your collection from the URL of the collection.
4. (Optional for GVAR updating) In the base of your repository, make a file called `gvars.json`. Inside this file, you will create a JSON dictionary, where each key is a GVAR id and each value is a description of the GVAR. You can put whatever you want for the description.
5. Commit and push your changes.

> If your primary branch of your repository is main instead of master, replace master with main in your `update_workflow.yml`


