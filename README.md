# GitTheCommits (AKA Sir Lance-A-Git)

This is a tool to help gather and merge all associated commits based on a Jira item number automatically.
Currently, it can take a day or two to find and merge all your items properly, plus time later if anything was missed.
We can cut this time down tenfold using GitHub's APIs and a bit of snake magic to streamline the merge process.

Why does this exist you may ask?
Well, there are 3 big reasons:

**Speed**:
Having to manually comb through item numbers and cherry-pick commits is quite slow.
This "combing" behavior screams automation; GitTheCommits is the pacifier.

**Jira-GitHub Integration Weirdness**:
The development tab in Jira seems a bit arbitrary, pulling in commits from other repositories and even missing some entirely.
Using the GitHub APIs and two different combing strategies based on your Git workflow, GitTheCommits can reliably get your commits.

**Ease of Use**:
This tool can take off the pressure and/or anxiety of trying your best not to miss any commits and ensure that all your commits work after being cherry-picked.
Once set up properly, you just enter your item numbers and run the program.

# Requirements

1. Ensure you have a Python 3 version installed on your machine. 
   (Tool developed with version [3.10.5](https://www.python.org/downloads/release/python-3105/))
2. PIP install all the packages listed in [requirements.txt](https://github.com/joeasley-clgx/GitTheCommits/blob/main/requirements.txt). 
   (`pip install -r ./requirements.txt`)
3. Create a [Personal Access Token](https://github.com/settings/tokens) for this project to use. 
   Ensure that this token has "repo" access, especially if using this tool with a private repository.

# Usage

There are two ways to run this tool, through the command line or through the GUI.

To run via the new GUI, run the `gui.py` file.

To run via the command line, run the `main.py` file in your terminal.

## GUI Instructions

Run the `gui.py` file and navigate to the `Settings` panel.

Fill in at least the top three required fields, `GitHub Token`, `Target Repository`, and `Target Branch`
- `GitHub Token` is the Personal Access Token you created in requirement step 3.
- `Target Repository` is the path to the repository. 
   (Example: "user/repository", "joeasley-clgx/GitTheCommits")
- `Target Branch` is the branch to grab commits from. 
   Most often this will be the development branch.

Next, you need to customize the settings you wish to use.
Each setting is explained in the Settings section below.

Once you're happy with your settings, click the `Save` button at the bottom right, then navigate to the `Output` panel.

This is where you enter your item numbers to search for and where you fetch and view your commits.
As the results pane will say, you can enter your item numbers in the `Item Numbers:` pane to the left.

If any item numbers are already saved in the `settings.json` file, they will be filled in this pane, otherwise it will be blank.
To add another entry for another item number, you can click the `Add Item Number` on the bottom of the pane.
To remove an entry, click the `X` button next to the entry you wish to remove.

There are some keyboard shortcuts to navigate and add item numbers.
- `Enter` will either skip to the next item entry below your current one, or if one does not exist, it will create a new entry below.
- `Up` will skip to the entry above your current entry.
- `Down` will skip to the entry below your current entry.

To save your item numbers, click the `Save Item Numbers` button below.

Finally, when you're ready to fetch your items' commits, click the `Fetch Commits` at the bottom.
This will automatically save your item numbers, just like the button above it.

If all goes well, your commits will be displayed in the right pane according to your settings.
A huge upside to using the GUI is even after your commits have been fetched, you can any display related setting and the output will update as soon as you save those settings.
Note: this does not apply to the already generated output text/excel files.

## Command Line Instructions

Fill in the top three fields in [settings.json](https://github.com/joeasley-clgx/GitTheCommits/blob/main/settings.json) (`GitHubToken`, `TargetRepository`, `TargetBranch`)
- `GitHubToken` is the Personal Access Token you created in requirement step 3.
- `TargetRepository` is the path to the repository. 
   (Example: "user/repository", "joeasley-clgx/GitTheCommits")
- `TargetBranch` is the branch to grab commits from. 
   Most often this will be the development branch.

Now you'll need to gather all the Jira item numbers you wish to merge.
Put those item numbers under the ItemNumbers array in [settings.json](https://github.com/joeasley-clgx/GitTheCommits/blob/main/settings.json), each separated by a comma.

Don't sweat if you forget to input your item numbers into the settings.
If empty, the program will ask you if you'd like to enter those numbers in on the fly.

Next, you need to customize the settings you wish to use.
Each setting is explained in the Settings section below.

Once you've finalized your settings, run `main.py`, kick back, relax, grab some popcorn, then realize you don't have time to make popcorn because the results are in!

# Settings

The setting names below are from the `settings.json` file.
Note that the GUI will have these settings spelled out, but the explaination still applies.

Both the GUI and command line will share this same `settings.json` file.

## Fetching Commits

There are two main methods of associating commits to Jira items.
You should only have one enabled at a time.

### Using Merged Pull Requests **(Slower, but Thorough)**:

Use this method if your repository puts the Jira item number in the branch's name.
How this works is we grab all of the closed pull requests to the `TargetBranch`.
Then we look at the pull request's head branch name to see if it contains one of the supplied `ItemNumbers`.

This ensures two main things:

1. We only look at changes checked into the `TargetBranch`.
2. We catch "quick commits", where someone forgot to put the item number in the commit message (Ex: "Fixed build issue", "Applied changes from pull request")

To turn on, set `UsePullRequests` to `true`

### Using Commit Messages **(Fastest)**:

Use this method if your repository puts the Jira item number in the commit message.
This one's simple, if the item number is within the commit message, we grab it.

Keep in mind, because we check the commit message, this method will oftentimes pull in merge commits as well as the original commits if pull requests are not squashed.

To turn on, set `UseCommitHistory` to `true`.

### Note:
If you have OutputToTerminal enabled and you see "403: Forbidden. Retrying in 60 seconds" show up, don't panic, that's just Github's rate limiting.
This appears to happen more often when using Pull Requests.

If it happens, let the program continue.
Your results will be displayed all the same.

## Outputing Commits

There are many options for displaying the related commits:

1. CommitDetailsToShow -
   A list of different commit details you'd like to see in the output.
   Toggle these to `true` or `false` as you see fit.
2. GroupCommitsByItem -
   If `true`, keeps commits that are part of the same Jira item together in the output.
2. ItemCherryPick -
   If `true`, shows one git cherry-pick command for all commit under an item. (cherry-pick for 'item-123', another for 'item-456')
3. ShowCommitsInDateDescendingOrder -
   If `true`, sorts the commits by descending order (latest commit first).
   This setting works in tandem with GroupCommitsByItem, so if you want all commits in order, be sure that GroupCommitsByItem is `false`.
4. OutputToTerminal -
   If `true`, prints the output to the terminal.
5. OutputToTxtFile -
   If `true`, writes the output to a text file. (text is the same as what's printed to the terminal)
6. OutputToExcelFile -
   If `true`, writes the output to an excel file.
7. AllCommitsCherryPickCommand -
   If `true`, writes a git cherry-pick command for all the found commits to any enabled output.
   The command will automatically cherry-pick each commit into the currently checked-out branch as *staged* changes.
   This way you can build and verify the changes, enter your commit message, and push as you please.
   (If you get a `fatal: bad revision` error, you need to fetch all remotes: `git fetch --all`)
8. IgnoreMergeCommits -
   If `true`, excludes any commit with more than one parent commit.
   Multiple parents are a tell that the commit was merged from elsewhere.
   The main use case for this is to exclude any "Merge develop into feature branch" commits.
9. UseShortCommitHash -
   If `true`, shortens the commit hash (or SHA) to the first 7 characters.
   This is mainly for reducing output length and does not affect the commit URL.
   For repositories with an enormous amount of commits, this probably needs to be `false`.
10. GitCherryPickArguments -
   Denotes what arguments to include with the git cherry-pick.
   Obviously, this only takes effect if `AllCommitsCherryPickCommand` is `true`.
11. SearchLimitMonths -
   Limits how far back we search for commits by X month(s).
   This helps speed up the fetch process if you know what time frame your changes were made.
   Value should be an integer or `null`. Examples: `1`, `2`, `3`.
12. UseConcurrentCommitFetching -
   If `true`, once the commits or pull requests have been found, asynchronusly process and save each commit.
   This is faster as we send out multiple API requests at a time, but also can trip GitHub's rate limiting/traffic control.
13. SecondsBetweenGithubRequests -
   As a rate limiting/traffic control solution, this acts as a delay between requests to GitHub in the event that requests are rejected as 403.
   Said rejection errors will appear in the console, and even when they appear, will automatically retry after 60 seconds.
   Value should be a float or `null`. Examples: `1`, `2.0`, `3.5`.

# Development
If you run through the requirements and usage sections, you'll have all you need to make changes as you wish.
For stability purposes, there are unit tests you can run with `python -m unittest` to validate existing functionality.
For code coverage, I've used the [coverage](https://pypi.org/project/coverage/) package, using `coverage run -m unittest test.py` to run and `coverage html` to fancy up the results.

If you make a change that you'd like to make permanent, create a Pull Request and we'll take a look!

If you find an issue/bug with the tool, please create an issue so it can be fixed.
