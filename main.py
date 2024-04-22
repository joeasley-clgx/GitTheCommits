import GitTheCommits


SETTINGS_FILE = "settings.json"


git_the_commits = GitTheCommits.GitTheCommits()

# Apply any settings from the supplied file
git_the_commits.set_settings(SETTINGS_FILE)

# Connects, authenticates, and initializes all GitHub related objects
git_the_commits.get_github_objects()

# Calls out to GitHub to gather and store all commits found based on the settings applied
git_the_commits.fetch_commits()

# Outputs all the stored commits, if any
git_the_commits.output_commits()
