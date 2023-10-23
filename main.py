from github import Github, Auth, GitCommit, GithubException, BadCredentialsException

import json
import os
import re
import xlsxwriter


def group_relevant_commit_info(git_commit: GitCommit.GitCommit, item_number, pr_urls: tuple = None, pr_url: str = None) -> object:
    # Condenses all the info from a commit into just the information we need and in a format we can use 

    global use_short_commit_hash

    return {
        "message": git_commit.message, 
        "author": f"{git_commit.author.name} <{git_commit.author.email}>",
        "date": git_commit.author.date,
        "sha": git_commit.sha[:7] if use_short_commit_hash else git_commit.sha,
        "commit url": git_commit.html_url,
        "pr url": pr_url if pr_url != None else (", ".join(pr_urls) if pr_urls != None else "None"),
        "item number": f"CLCTUTD-{str(item_number)}",
        "is merge": len(git_commit.parents) > 1
    }


def save_commit_info(commit: GitCommit.GitCommit, item_number: str, pr_urls: tuple = None, pr_url: str = None) -> None:
    # Adds commit to the commit_list and groups the index of that commit to the provided item_number in the item_commit_dictionary

    global commit_list
    global item_commit_dictionary
    global ignore_merge_commits

    commit_sha = commit.sha[:7] if use_short_commit_hash else commit.sha

    if not commit_sha in [commit['sha'] for commit in commit_list]:
        commit_info = group_relevant_commit_info(commit, item_number, pr_urls, pr_url)

        if not ignore_merge_commits or not commit_info['is merge']:
            commit_list.append(commit_info)
            
            if item_number in item_commit_dictionary:
                item_commit_dictionary[item_number].append(len(commit_list) - 1)
            else:
                item_commit_dictionary[item_number] = [len(commit_list) - 1]


def stringify_commits(commit_list: list) -> str:
    # Format the commit to a human-readable string

    global commit_detail_visibilty

    output = ""
    for commit in commit_list:
        if commit_detail_visibilty["Message"]: output += f"\n- {commit['message']}"
        if commit_detail_visibilty["ItemNumber"]: output += f"\nItem Number: {commit['item number']}"
        if commit_detail_visibilty["Author"]: output += f"\nAuthor: {commit['author']}"
        if commit_detail_visibilty["Date"]: output += f"\nDate: {commit['date']}"
        if commit_detail_visibilty["CommitUrl"]: output += f"\nCommit URL: {commit['commit url']}"
        if commit_detail_visibilty["PullRequestUrl"]: output += f"\nPull Request URL: {commit['pr url']}"
        if commit_detail_visibilty["Sha"]: output += f"\nSHA: {commit['sha']}"
        if commit_detail_visibilty["IsMergeCommit"]: output += f"\nIs Merge Commit: {commit['is merge']}"
        output += "\n"
        
    return output


def manually_enter_item_numbers() -> list:
    # Prompt the user to manually enter item numbers

    print("No Jira items have been supplied. You can enter a list of item numbers under the \"ItemNumbers\" property in settings.json")
    enter_numbers_manually_input = input("Would you like to enter those item numbers now? (Y/N) ").lower()
    if len(enter_numbers_manually_input) > 0 and enter_numbers_manually_input[0] == 'y':
        item_numbers_input = input("Please enter your item numbers separated by commas. Press ENTER when done:\n")
        item_numbers = [re.sub("[^0-9]", "", str(number)) for number in item_numbers_input.split(',')]
        print("Item numbers I'll search for:")
        print(", ".join([f"CLCTUTD-{item_number}" for item_number in item_numbers]) + "\n")
    else:
        print("Be sure to enter the Jira item numbers you need commits for in settings.json.")
        exit()
    
    return item_numbers


def generate_cherry_pick_command(commits: list) -> str:
    # Sorts commits in acsending date order and returns a git cherry-pick command with those commits

    global cherry_pick_command

    sorted_commits = sorted(commits, key=lambda x: x['date'])
    return f"\n{cherry_pick_command}{' '.join([commit['sha'] for commit in sorted_commits])}"


def generate_excel_file(commit_list: list) -> None:
    # Make xlsx file

    global cherry_pick_command
    global use_short_commit_hash

    # xlsxwriter package cannot overwrite files
    if os.path.isfile("output.xlsx"):
        while True:
            try:
                os.remove("output.xlsx")
            except IOError:
                print("Please close ouput.xlsx so it can be updated, then press enter.")
                input()
            else:
                break

    with xlsxwriter.Workbook(f"output.xlsx") as workbook:
        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({"bg_color": "#b8cce4", "align": "center", "border": 1, "border_color": "black"})
        data_format = workbook.add_format({"bg_color": "white", "align": "left", "border": 1, "border_color": "#d9d9d9"})
        centered_data_format = workbook.add_format({"bg_color": "white", "align": "center", "border": 1, "border_color": "#d0d0d0"})

        letter_dictionary = {
            1: 'A',
            2: 'B',
            3: 'C',
            4: 'D',
            5: 'E',
            6: 'F',
            7: 'G',
            8: 'H'
        }

        # Header Rows
        header_column_number = 1
        if commit_detail_visibilty["Message"]: 
            letter = letter_dictionary[header_column_number]
            worksheet.set_column(f"{letter}:{letter}", 100)
            worksheet.write_string(f'{letter}1', "Commit Message", header_format)
            header_column_number += 1
        if commit_detail_visibilty["ItemNumber"]: 
            letter = letter_dictionary[header_column_number]
            worksheet.set_column(f"{letter}:{letter}", 15)
            worksheet.write_string(f'{letter}1', "Item Number", header_format)
            header_column_number += 1
        if commit_detail_visibilty["Author"]: 
            letter = letter_dictionary[header_column_number]
            worksheet.set_column(f"{letter}:{letter}", 45)
            worksheet.write_string(f'{letter}1', "Author", header_format)
            header_column_number += 1
        if commit_detail_visibilty["Date"]: 
            letter = letter_dictionary[header_column_number]
            worksheet.set_column(f"{letter}:{letter}", 20)
            worksheet.write_string(f'{letter}1', "Date", header_format)
            header_column_number += 1
        if commit_detail_visibilty["CommitUrl"]: 
            letter = letter_dictionary[header_column_number]
            worksheet.set_column(f"{letter}:{letter}", 101)
            worksheet.write_string(f'{letter}1', "Commit Url", header_format)
            header_column_number += 1
        if commit_detail_visibilty["PullRequestUrl"]: 
            letter = letter_dictionary[header_column_number]
            worksheet.set_column(f"{letter}:{letter}", 61)
            worksheet.write_string(f'{letter}1', "Pull Request Url", header_format)
            header_column_number += 1
        if commit_detail_visibilty["Sha"]: 
            letter = letter_dictionary[header_column_number]
            worksheet.set_column(f"{letter}:{letter}", 10 if use_short_commit_hash else 42)
            worksheet.write_string(f'{letter}1', "Sha", header_format)
            header_column_number += 1
        if commit_detail_visibilty["IsMergeCommit"]: 
            letter = letter_dictionary[header_column_number]
            worksheet.set_column(f"{letter}:{letter}", 42)
            worksheet.write_string(f'{letter}1', "Is Merge Commit", header_format)
            header_column_number += 1

        # THE DATA
        row = 1
        for commit in commit_list:
            data_column_number = 0
            if commit_detail_visibilty["Message"]: 
                worksheet.write_string(row, data_column_number, commit['message'], data_format)
                data_column_number += 1
            if commit_detail_visibilty["ItemNumber"]:
                worksheet.write_string(row, data_column_number, commit['item number'], centered_data_format) 
                data_column_number += 1
            if commit_detail_visibilty["Author"]:
                worksheet.write_string(row, data_column_number, commit['author'], data_format) 
                data_column_number += 1
            if commit_detail_visibilty["Date"]:
                worksheet.write_string(row, data_column_number, str(commit['date']), centered_data_format) 
                data_column_number += 1
            if commit_detail_visibilty["CommitUrl"]:
                worksheet.write_string(row, data_column_number, commit['commit url'], data_format) 
                data_column_number += 1
            if commit_detail_visibilty["PullRequestUrl"]:
                worksheet.write_string(row, data_column_number, commit['pr url'], data_format) 
                data_column_number += 1
            if commit_detail_visibilty["Sha"]:
                worksheet.write_string(row, data_column_number, commit['sha'], centered_data_format) 
                data_column_number += 1
            if commit_detail_visibilty["IsMergeCommit"]:
                worksheet.write_string(row, data_column_number, str(commit['is merge']), centered_data_format) 
                data_column_number += 1
            
            row += 1
        
        if show_cherry_pick_command:
            worksheet.merge_range(f"A{row + 2}:{letter_dictionary[header_column_number]}{row + 2}", 
                                  generate_cherry_pick_command(commit_list), data_format)


if __name__ == "__main__":
    with open("settings.json", 'r') as file:
        try:
            settings = json.load(file)
        except json.decoder.JSONDecodeError as exception:
            print(f"Your settings.json file has a syntax error on line {exception.lineno}. " + 
                   "Please fix it and try again.")
            
            # Do not immediately close program
            input()
            exit()

        # GitHub Access Token: https://github.com/settings/tokens
        # Required Access: repo - Full control of private repositories (There's unfortuntately no read-only for private repositories)
        github_Token = settings["GitHubToken"]
        repository_name = settings["TargetRepository"]
        target_branch_name = settings["TargetBranch"]
        # Convert ItemNumbers into a string containing only numbers (1234 or CLCTUTD-1234 becomes "1234")
        item_numbers = [re.sub("[^0-9]", '', str(number)) for number in settings["ItemNumbers"]]
        # A dictionary of what details should be included in the output
        commit_detail_visibilty = settings["CommitDetailsToShow"]
        # If true, groups each commit by the Jira item number
        group_commits_by_item = settings["GroupCommitsByItem"]
        # If true, sorts the commits by descending order (latest commit first)
        order_commits_by_date_descend = settings["ShowCommitsInDateDescendingOrder"]
        # Collect commits using the Develop commit history (only works if every commit has item number in it)
        use_commit_history = settings["UseCommitHistory"]
        # Collect commits using the pull requests to the Develop branch ***this is the recommended method***
        use_pull_requests = settings["UsePullRequests"]
        # Choose how you'd like to see the results:
        output_to_terminal = settings["OutputToTerminal"]
        output_to_txt = settings["OutputToTxtFile"]
        output_to_excel = settings["OutputToExcelFile"]
        # Show the git cherry-pick command to the end of the output
        show_cherry_pick_command = settings["ShowCherryPickCommand"]
        # If a commit has more than one parent, it will be excluded (Use case, ignore "merge develop to feature branch" commits)
        ignore_merge_commits = settings["IgnoreMergeCommits"]
        # Specifies whether to use full or short commit hashes in the output (short meaning first 7 characters)
        use_short_commit_hash = settings["UseShortCommitHash"]
        # Denotes all arguments for the git cherry-pick command
        git_cherry_pick_arguments = settings["GitCherryPickArguments"]

    if len(item_numbers) == 0:
        item_numbers = manually_enter_item_numbers()

    auth = Auth.Token(github_Token)
    github = Github(auth=auth)

    try:
        repo = github.get_repo(repository_name)
    except BadCredentialsException:
        print("Github responded with a Bad Credentials error. " +
              "Please ensure that your GitHubToken is valid and has the required permissions, then try again.")
    except GithubException as exception:
        if exception.data["message"] == "Not Found":
            print(f"Could not find the target repository '{repository_name}'. " +
                   "Please ensure that your TargetRepository is correct " + 
                   "and your GitHubToken has the required permissions to view the repository, then try again.")
        else:
            # Put any unhandled exception to the terminal
            raise exception

        # Do not immediately close program
        input()
        exit()

    try:
        target_branch = repo.get_branch(target_branch_name)
    except GithubException as exception:
        if exception.data["message"] == "Branch not found":
            print(f"Could not find the target branch '{target_branch_name}'. " +
                   "Please ensure that your TargetBranch exists, then try again.")
        else:
            # Put any unhandled exception to the terminal
            raise exception

        # Do not immediately close program
        input()
        exit()

    commit_list = []
    item_commit_dictionary = {} # item_number : [commit_index]

    if output_to_terminal:
        print("Fetching commits", end='', flush=True)
    if use_commit_history:
        for commit_object in repo.get_commits(sha=target_branch.commit.sha):
            commit = commit_object.commit
            matches = [item_number for item_number in item_numbers if(item_number in commit.message)]
            if len(matches) > 0:
                if output_to_terminal:
                    print('.', end='', flush=True)

                item_number = matches[0]
                pr_urls = (pull.html_url for pull in commit_object.get_pulls())
                save_commit_info(commit, item_number, pr_urls=pr_urls)

    if use_pull_requests:
        for pull in repo.get_pulls(state="closed", base=target_branch_name):
            matches = [item_number for item_number in item_numbers if(item_number in pull.head.ref)]
            if len(matches) > 0:
                if output_to_terminal:
                    print('.', end='', flush=True)

                item_number = matches[0]
                for commit_object in pull.get_commits():
                    if pull.merged:
                        pr_urls = pull.html_url
                        save_commit_info(commit_object.commit, item_number, pr_url=pull.html_url)

    if len(commit_list) == 0:
        output = "No commits found"

        if output_to_terminal or output_to_excel:
            print("\n" + output)
        if output_to_txt:
            with open("output.txt", 'w') as file:
                file.write(output)
        
        exit()

    # Output commits
    total_output = ""
    output = f"Found {len(commit_list)} related commit{'' if len(commit_list) == 1 else 's'}"
    
    cherry_pick_command_segments = ["git cherry-pick", git_cherry_pick_arguments, '-m 1 ' if not ignore_merge_commits else '']
    if git_cherry_pick_arguments == None or len(str(git_cherry_pick_arguments).strip()) == 0:
        cherry_pick_command_segments.pop(1)

    cherry_pick_command = ' '.join(cherry_pick_command_segments)

    if output_to_terminal:
        print("\n" + output)
    if output_to_txt:
        total_output += output

    if group_commits_by_item:
        excel_data_list = []

        for item_number in item_numbers:
            if not item_number in item_commit_dictionary:
                output = f"\nNo commits found for CLCTUTD-{item_number}\n\n---"

                if output_to_terminal:
                    print(output)
                if output_to_txt:
                    total_output += "\n" + output
                continue

            item_commit_list = [commit_list[index] for index in item_commit_dictionary[item_number]]
            sorted_commit_list = sorted(item_commit_list, key=lambda x: x['date'], reverse=order_commits_by_date_descend)

            if output_to_excel:
                excel_data_list.extend(sorted_commit_list)

            if output_to_terminal or output_to_txt:
                output = f"\nCommit{'' if len(item_commit_list) == 1 else 's'} for CLCTUTD-{item_number} ({len(item_commit_list)}):"
                output += stringify_commits(sorted_commit_list)
                output += "\n---"

                if output_to_terminal:
                    print(output)
                if output_to_txt:
                    total_output += "\n" + output

        
        if show_cherry_pick_command and (output_to_terminal or output_to_txt):
            # git cherry-pick command should stay in date-specific order, despite GroupCommitsByItem setting
            output = generate_cherry_pick_command(commit_list)

            if output_to_terminal:
                print(output)
            if output_to_txt:
                total_output += "\n" + output

        if output_to_excel:
            generate_excel_file(excel_data_list)

    else:
        sorted_commit_list = sorted(commit_list, key=lambda x: x['date'], reverse=order_commits_by_date_descend)

        if output_to_excel:
            generate_excel_file(sorted_commit_list)

        if output_to_terminal or output_to_txt:
            output = f"Here are all commits for your items in {'descending' if order_commits_by_date_descend else 'acsending'} order:\n"
            output += stringify_commits(sorted_commit_list)
            
            if show_cherry_pick_command:
                output += generate_cherry_pick_command(commit_list)

            if output_to_terminal:
                print(output)
            if output_to_txt:
                total_output += "\n" + output

    if output_to_txt:
        with open("output.txt", 'w') as file:
            file.write(total_output)
    
    if output_to_terminal:
        # Do not immediately close program
        input()
        