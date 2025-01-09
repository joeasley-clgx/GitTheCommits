import GitTheCommits
import asyncio


SETTINGS_FILE = "settings.json"


async def main():
    git_the_commits = GitTheCommits.GitTheCommits()

    # Apply any settings from the supplied file
    settings_error_message = git_the_commits.set_settings(SETTINGS_FILE)
    if settings_error_message:
        print(settings_error_message)

        if git_the_commits.output_to_terminal:
            # Do not immediately close the program
            input("Press Enter to exit...")
        return

    # Connects, authenticates, and initializes all GitHub related objects
    github_error_message = git_the_commits.get_github_objects()
    if github_error_message:
        print(github_error_message)

        if git_the_commits.output_to_terminal:
            # Do not immediately close the program
            input("Press Enter to exit...")
        return

    # Calls out to GitHub to gather and store all commits found based on the settings applied
    await git_the_commits.fetch_commits()

    # Outputs all the stored commits, if any
    git_the_commits.output_commits()


if __name__ == "__main__":
    asyncio.run(main())