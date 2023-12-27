# Avrae Auto-Update v2.0

> Warning! This is a new update with breaking changes. Please review the installation instructions and your workflow file to ensure all is correct.

This project allows users to automatically update the code and documentation for snippets and aliases in Avrae collections. It also allows for the automatic updating of GVARS. See below for the required setup and instructions. Feel free to make an issue if you run into any problems!

## Required project structure

Generally, each collection should be given it's own folder. Inside the collection folder, each alias should have it's own folder. In each alias folder, the alias should be present as well as the documentation for the alias. Snippets should be placed under the collection directory. Here is a full graphical demonstration.

```text
Github Repository
├── collections
│   └── cool-collection
│       ├── my-alias
│       │   ├── my-alias.alias
│       │   ├── my-alias.md
│       │   └── my-subalias
│       │       ├── my-subalias.alias
│       │       └── my-subalias.md
│       ├── my-snippet.md
│       └── my-snippet.snippet
├── collections.json
├── .github
│   └── workflows
│       └── update_avrae.yml
├── gvars
│   └── my-gvar.gvar
└── gvars.json
```

[Here](https://github.com/1drturtle/test-avrae-autoupdate) you can find a repository that has this action set up correctly.

## Installation Instructions

> Warning: Take caution when performing step 2. Your Avrae token should be kept secret, so please do *not* share the token or do anything with it except place it as a github secret. This action does *not* leak any tokens to logs.

1. Install the action file into your repository. See the above graphic for where the YAML file should go, under the `.github` directory. An example workflow is provided in the example folder, [here](https://github.com/1drturtle/avrae-autoupdate/tree/master/examples/ex-workflow.yml).
    1. Ensure that the correct branch is present under line 5. Typical values include `main` and `master`.
2. Create and populate your `collections.json` and your `gvars.json`
    1. `collections.json` should contain a JSON dictionary. See example [here](https://github.com/1drturtle/avrae-autoupdate/blob/master/examples/ex-collections.json)
    2. `gvars.json` should contain a JSON dictonary. See example [here](https://github.com/1drturtle/avrae-autoupdate/blob/master/examples/ex-gvars.json)
3. Add your Avrae Token to your repository.
    1. Go to `https://avrae.io/dashboard` and ensure you are signed into your account.
    2. Open your browser's developer console, usually via `F12`
    3. Navigate to your "Storage" -> "Local Storage". Steps may vary from browser to browser.
    4. Copy the value of the `avrae-token` variable.
    5. Following [these steps](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions#creating-secrets-for-a-repository), create a Github Secret in your repository with the exact name of `AVRAE_TOKEN`.
4. To ensure the action is working correctly, create a "test change" to an alias in your repository, commit the change, and push to Github.
    1. After a couple minutes, navigate to the "Actions" tab next to the Pull Requests tab
    2. Click the most recent action run.
    3. Click "publish"
    4. Review the output under the "Run 1drturtle/avrae-autoupdate" tab.
