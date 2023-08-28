# GitTheCommits
A tool to help gather all the commits to merge based on a Jira item number.

## Setup
1. Install all the packages listed in [requirements.txt](https://github.com/joeasley-clgx/GitTheCommits/blob/main/requirements.txt).
2. Create a [Personal Access Token](https://github.com/settings/tokens) for this project to use. Ensure that this token has "repo" access, especially if using this tool with a private repository.
3. Fill in the top three fields in [settings.json](https://github.com/joeasley-clgx/GitTheCommits/blob/main/settings.json) (`GitHubToken`, `TargetRepository`, `TargetBranch`)

# Usage
First, you'll need to gather all the Jira item numbers you wish to merge.
Put those item numbers under the ItemNumbers array in [settings.json](https://github.com/joeasley-clgx/GitTheCommits/blob/main/settings.json), each separated by a comma.

Next you need to configure how the program will both fetch and output the commits.

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

Keep in mind, because we check the commit message, this method will often times pull in merge commits as well as the original commits if pull requests are not squashed.

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
4. OutputToTerminal -
If `true`, prints the output to the terminal.
5. OutputToTxtFile -
If `true`, writes the output to a text file (text is the same as what's printed to the terminal.
6. OutputToExcelFile -
If `true`, writes the output to an excel file.
