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

## Setup

1. Ensure you have a Python 3 version installed on your machine. (Tool developed with version [3.10.5](https://www.python.org/downloads/release/python-3105/))
2. PIP install all the packages listed in [requirements.txt](https://github.com/joeasley-clgx/GitTheCommits/blob/main/requirements.txt). (`pip install -r ./requirements.txt`)
3. Create a [Personal Access Token](https://github.com/settings/tokens) for this project to use. Ensure that this token has "repo" access, especially if using this tool with a private repository.
4. Fill in the top three fields in [settings.json](https://github.com/joeasley-clgx/GitTheCommits/blob/main/settings.json) (`GitHubToken`, `TargetRepository`, `TargetBranch`)
   - `GitHubToken` is the Personal Access Token you created in step 3.
   - `TargetRepository` is the path to the repository. (Example: "organization/project", "joeasley-clgx/GitTheCommits")
   - `TargetBranch` is the branch to grab commits from. Most often this will be the development branch.

# Usage

First, you'll need to gather all the Jira item numbers you wish to merge.
Put those item numbers under the ItemNumbers array in [settings.json](https://github.com/joeasley-clgx/GitTheCommits/blob/main/settings.json), each separated by a comma.

Don't sweat if you forget to input your item numbers into the settings.
If empty, the program will ask you if you'd like to enter those numbers in on the fly.

Next, you need to configure how the program will both fetch and output the commits.

## Fetching Commits

There are two main methods of associating commits to Jira items.

### Using Merged Pull Requests **(Recommended)**:

Use this method if your repository puts the Jira item number in the branch's name.
How this works is we grab all of the closed pull requests to the `TargetBranch`.
Then we look at the pull request's head branch name to see if it contains one of the supplied `ItemNumbers`.

This ensures two main things:

1. We only look at changes checked into the `TargetBranch`.
2. We catch "quick commits", where someone forgot to put the item number in the commit message (Ex: "Fixed build issue", "Applied changes from pull request")

To turn on, set `UsePullRequests` to `true`

### Using Commit Messages:

Use this method if your repository puts the Jira item number in the commit message.
This one's simple, if the item number is within the commit message, we grab it.

Keep in mind, because we check the commit message, this method will oftentimes pull in merge commits as well as the original commits if pull requests are not squashed.

To turn on, set `UseCommitHistory` to `true`.

## Outputing Commits

There are many options for displaying the related commits:

1. CommitDetailsToShow -
   A list of different commit details you'd like to see in the output.
   Toggle these to `true` or `false` as you see fit.
2. GroupCommitsByItem -
   If `true`, keeps commits that are part of the same Jira item together in the output.
3. ShowCommitsInDateDescendingOrder -
   If `true`, sorts the commits by descending order (latest commit first).
   This setting works in tandem with GroupCommitsByItem, so if you want all commits in order, be sure that GroupCommitsByItem is `false`.
4. OutputToTerminal -
   If `true`, prints the output to the terminal.
5. OutputToTxtFile -
   If `true`, writes the output to a text file. (text is the same as what's printed to the terminal)
6. OutputToExcelFile -
   If `true`, writes the output to an excel file.
7. ShowCherryPickCommand -
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

Once you've finalized your settings, run `main.py`, kick back, relax, grab some popcorn, then realize you don't have time to make popcorn because the results are in!
