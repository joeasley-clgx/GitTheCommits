from github import Github, Auth, GitCommit, GithubException, BadCredentialsException, Branch, Repository
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from CommitDetailVisibility import CommitDetailVisibility
from CommitInfo import CommitInfo

import json
import os
import re
import xlsxwriter


class GitTheCommits:
    """
    Gathers and outputs all associated commits based on Jira item numbers
    """
    short_commit_hash_length = 10

    settings_are_set: bool
    github_token: str
    repository_name: str
    target_branch_name: str
    item_numbers: list[str]
    commit_detail_visibilty: CommitDetailVisibility
    group_commits_by_item: bool
    order_commits_by_date_descend: bool
    use_commit_history: bool
    use_pull_requests: bool
    output_to_terminal: bool
    output_to_txt: bool
    output_to_excel: bool
    show_cherry_pick_command: bool
    ignore_merge_commits: bool
    use_short_commit_hash: bool
    cherry_pick_command: str
    search_date_limit: datetime

    commit_list: list[CommitInfo]
    item_commit_dictionary: dict[int, list[int]] # item_number : commit_index

    github_repository: Repository.Repository
    github_target_branch: Branch.Branch

    def __init__(self, print_version = True) -> None:
        if print_version: 
            print("GitTheCommits v2.0.0\n")

        # Settings
        self.settings_are_set = False
        self.github_token = None
        self.repository_name = None
        self.target_branch_name = None
        self.item_numbers = None
        self.commit_detail_visibilty = CommitDetailVisibility()
        self.group_commits_by_item = None
        self.order_commits_by_date_descend = None
        self.use_commit_history = None
        self.use_pull_requests = None
        self.output_to_terminal = None
        self.output_to_txt = None
        self.output_to_excel = None
        self.show_cherry_pick_command = None
        self.ignore_merge_commits = None
        self.use_short_commit_hash = None
        self.cherry_pick_command = None
        self.search_date_limit = None
        
        self.commit_list = []
        self.item_commit_dictionary = dict()

        self.github_repository = None
        self.github_target_branch = None


    def group_relevant_commit_info(self, git_commit: GitCommit.GitCommit, item_number, pr_urls: tuple = None, pr_url: str = None) -> CommitInfo:
        """ 
        Condenses all the info from a commit into just the information we need and in a format we can use 
        """
        
        return CommitInfo(
            message = git_commit.message, 
            author = f"{git_commit.author.name} <{git_commit.author.email}>",
            date = git_commit.author.date,
            sha = git_commit.sha[:self.short_commit_hash_length] if self.use_short_commit_hash else git_commit.sha,
            commit_url = git_commit.html_url,
            pr_url = pr_url if pr_url != None else (", ".join(pr_urls) if pr_urls != None else "None"),
            item_number = str(item_number),
            is_merge = len(git_commit.parents) > 1
        )


    def save_commit_info(self, commit: GitCommit.GitCommit, item_number: str, pr_urls: tuple = None, pr_url: str = None) -> None:
        """
        Adds commit to the commit_list and groups the index of that commit to the provided item_number in the item_commit_dictionary
        """

        commit_sha = commit.sha[:self.short_commit_hash_length] if self.use_short_commit_hash else commit.sha

        if not commit_sha in [commit.sha for commit in self.commit_list]:
            commit_info = self.group_relevant_commit_info(commit, item_number, pr_urls, pr_url)

            if not self.ignore_merge_commits or not commit_info.is_merge:
                self.commit_list.append(commit_info)
                
                if item_number in self.item_commit_dictionary:
                    self.item_commit_dictionary[item_number].append(len(self.commit_list) - 1)
                else:
                    self.item_commit_dictionary[item_number] = [len(self.commit_list) - 1]
        else:
            filtered_commit = list(filter(lambda c: c.sha == commit_sha, self.commit_list))
            
            if len(filtered_commit) == 1:
                saved_commit = filtered_commit[0]

                if saved_commit.pr_url.split(', '):
                    # update pr url with new urls (pull request flow)
                    return


    def stringify_commits(self, commit_list: list[CommitInfo]) -> str:
        """
        Format the commit into a human-readable string
        """
        
        output = ""
        for commit in commit_list:
            if self.commit_detail_visibilty.message: output += f"\n- {commit.message}"
            if self.commit_detail_visibilty.item_number: output += f"\nItem Number: {commit.item_number}"
            if self.commit_detail_visibilty.author: output += f"\nAuthor: {commit.author}"
            if self.commit_detail_visibilty.date: output += f"\nDate: {commit.date}"
            if self.commit_detail_visibilty.commit_url: output += f"\nCommit URL: {commit.commit_url}"
            if self.commit_detail_visibilty.pull_request_url: output += f"\nPull Request URL: {commit.pr_url}"
            if self.commit_detail_visibilty.sha: output += f"\nSHA: {commit.sha}"
            if self.commit_detail_visibilty.is_merge_commit: output += f"\nIs Merge Commit: {commit.is_merge}"
            if self.commit_detail_visibilty.show_cherry_pick_command: output += f"\nCherry-Pick Command: {self.cherry_pick_command} {commit.sha}"
            output += "\n"
            
        return output
    

    def strip_non_digit_characters_from_list_of_strings(self, input: list) -> list[str]:
        return [re.sub("\D", '', str(number)) for number in input]


    def manually_enter_item_numbers(self) -> list[str]:
        """
        Prompt the user to manually enter item numbers
        """

        print("No Jira items have been supplied. You can enter a list of item numbers under the \"ItemNumbers\" property in settings.json")
        enter_numbers_manually_input = input("Would you like to enter those item numbers now? (Y/N) ").lower()
        if len(enter_numbers_manually_input) > 0 and enter_numbers_manually_input[0] == 'y':
            item_numbers_input = input("Please enter your item numbers separated by commas. Press ENTER when done:\n")
            item_numbers = self.strip_non_digit_characters_from_list_of_strings(item_numbers_input.split(','))
            print("Item numbers I'll search for:")
            print(", ".join([f"{item_number}" for item_number in item_numbers]) + "\n")
        else:
            print("Be sure to enter the Jira item numbers you need commits for in settings.json.")
            input()
            exit()
        
        return item_numbers


    def generate_cherry_pick_command(self, commits: list[CommitInfo]) -> str:
        """
        Sorts commits in acsending date order and returns a git cherry-pick command with those commits
        """
        
        sorted_commits = sorted(commits, key=lambda x: x.date)
        return f"\n{self.cherry_pick_command} {' '.join([commit.sha for commit in sorted_commits])}"
    

    def set_settings_via_dictionary(self, new_settings: dict) -> None:
        """
        Populates all settings via a dictionary
        """
        
        # GitHub Access Token: https://github.com/settings/tokens
        # Required Access: repo - Full control of private repositories (There's unfortuntately no read-only for private repositories)
        self.github_token = new_settings["GitHubToken"]
        self.repository_name = new_settings["TargetRepository"]
        self.target_branch_name = new_settings["TargetBranch"]

        # Convert ItemNumbers into a string containing only numbers (1234 or "ITEM-1234" becomes "1234")
        self.item_numbers = self.strip_non_digit_characters_from_list_of_strings(new_settings["ItemNumbers"])

        # A dictionary of what details should be included in the output
        commitDetailsToShow = new_settings["CommitDetailsToShow"]
        self.commit_detail_visibilty = CommitDetailVisibility(
            message=commitDetailsToShow["Message"],
            item_number=commitDetailsToShow["ItemNumber"],
            author=commitDetailsToShow["Author"],
            date=commitDetailsToShow["Date"],
            commit_url=commitDetailsToShow["CommitUrl"],
            pull_request_url=commitDetailsToShow["PullRequestUrl"],
            sha=commitDetailsToShow["Sha"],
            is_merge_commit=commitDetailsToShow["IsMergeCommit"],
            show_cherry_pick_command=commitDetailsToShow["CherryPickCommand"]
        )

        # If true, groups each commit by the Jira item number
        self.group_commits_by_item = new_settings["GroupCommitsByItem"]

        # If true, sorts the commits by descending order (latest commit first)
        self.order_commits_by_date_descend = new_settings["ShowCommitsInDateDescendingOrder"]

        # Collect commits using the Develop commit history (only works if every commit has item number in it)
        self.use_commit_history = new_settings["UseCommitHistory"]

        # Collect commits using the pull requests to the Develop branch ***this is the recommended method***
        self.use_pull_requests = new_settings["UsePullRequests"]

        # Choose how you'd like to see the results:
        self.output_to_terminal = new_settings["OutputToTerminal"]
        self.output_to_txt = new_settings["OutputToTxtFile"]
        self.output_to_excel = new_settings["OutputToExcelFile"]

        # Show the git cherry-pick command to the end of the output
        self.show_cherry_pick_command = new_settings["ShowCherryPickCommand"]

        # If a commit has more than one parent, it will be excluded (Use case, ignore "merge develop to feature branch" commits)
        self.ignore_merge_commits = new_settings["IgnoreMergeCommits"]

        # Specifies whether to use full or short commit hashes in the output (short meaning first 7 characters)
        self.use_short_commit_hash = new_settings["UseShortCommitHash"]

        # Denotes all arguments for the git cherry-pick command
        cherry_pick_command_segments = ["git cherry-pick", new_settings["GitCherryPickArguments"], '-m 1' if not self.ignore_merge_commits else '']
        if new_settings["GitCherryPickArguments"] == None or len(str(new_settings["GitCherryPickArguments"]).strip()) == 0:
            cherry_pick_command_segments.pop(1)

        self.cherry_pick_command = ' '.join(cherry_pick_command_segments).strip()
        
        # Limit how far back we search for commits
        self.search_date_limit = (datetime.today() - relativedelta(months=int(new_settings["SearchLimitMonths"]))).replace(tzinfo=timezone.utc) if new_settings["SearchLimitMonths"] else None

        self.settings_are_set = True

    
    def set_settings(self, filename: str) -> None:
        """
        Populates all settings via a JSON file
        """

        if not filename[-5:] == ".json":
            raise Exception("The file containing your settings must be a '.json' file")

        with open(filename, 'r') as file:
            try:
                settings = json.load(file)
                self.set_settings_via_dictionary(settings)
            except json.decoder.JSONDecodeError as exception:
                print(f"Your {filename} file has a syntax error on line {exception.lineno}. " + 
                    "Please fix it and try again.")
                
                # Do not immediately close program
                input()
                exit()


    def generate_excel_file(self, commit_list: list[CommitInfo]) -> None:
        """
        Generates an Excel file with all the data stored in the class
        """

        # xlsxwriter package cannot overwrite files
        if os.path.isfile("output.xlsx"):
            while True:
                try:
                    os.remove("output.xlsx")
                except IOError:
                    print("Please close output.xlsx so it can be updated, then press enter.")
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
                8: 'H',
                9: 'I'
            }

            # Header Rows
            header_column_number = 1
            if self.commit_detail_visibilty.message: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 100)
                worksheet.write_string(f'{letter}1', "Commit Message", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.item_number: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 15)
                worksheet.write_string(f'{letter}1', "Item Number", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.author: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 45)
                worksheet.write_string(f'{letter}1', "Author", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.date: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 20)
                worksheet.write_string(f'{letter}1', "Date", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.commit_url: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 101)
                worksheet.write_string(f'{letter}1', "Commit Url", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.pull_request_url: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 61)
                worksheet.write_string(f'{letter}1', "Pull Request Url", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.sha: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 10 if self.use_short_commit_hash else 42)
                worksheet.write_string(f'{letter}1', "Sha", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.is_merge_commit: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 42)
                worksheet.write_string(f'{letter}1', "Is Merge Commit", header_format)
                header_column_number += 1

            # THE DATA
            row = 1
            for commit in commit_list:
                data_column_number = 0
                if self.commit_detail_visibilty.message: 
                    worksheet.write_string(row, data_column_number, commit.message, data_format)
                    data_column_number += 1
                if self.commit_detail_visibilty.item_number:
                    worksheet.write_string(row, data_column_number, commit.item_number, centered_data_format) 
                    data_column_number += 1
                if self.commit_detail_visibilty.author:
                    worksheet.write_string(row, data_column_number, commit.author, data_format) 
                    data_column_number += 1
                if self.commit_detail_visibilty.date:
                    worksheet.write_string(row, data_column_number, str(commit.date), centered_data_format) 
                    data_column_number += 1
                if self.commit_detail_visibilty.commit_url:
                    worksheet.write_string(row, data_column_number, commit.commit_url, data_format) 
                    data_column_number += 1
                if self.commit_detail_visibilty.pull_request_url:
                    worksheet.write_string(row, data_column_number, commit.pr_url, data_format) 
                    data_column_number += 1
                if self.commit_detail_visibilty.sha:
                    worksheet.write_string(row, data_column_number, commit.sha, centered_data_format) 
                    data_column_number += 1
                if self.commit_detail_visibilty.is_merge_commit:
                    worksheet.write_string(row, data_column_number, str(commit.is_merge), centered_data_format) 
                    data_column_number += 1
                
                row += 1
            
            if self.show_cherry_pick_command:
                worksheet.merge_range(f"A{row + 2}:{letter_dictionary[header_column_number]}{row + 2}", 
                                    self.generate_cherry_pick_command(commit_list), data_format)
                

    def fetch_commits(self) -> None:
        """
        Uses the class' GitHub properties to fetch all commits according to all relevant settings
        """
        
        if len(self.item_numbers) == 0:
            self.item_numbers = self.manually_enter_item_numbers()
        
        if self.output_to_terminal:
            print("Fetching commits", end='', flush=True)
        if self.use_commit_history:
            github_commits = None
            if self.search_date_limit != None:
                github_commits = self.github_repository.get_commits(sha=self.github_target_branch.commit.sha, since=self.search_date_limit) 
            else:
                github_commits =  self.github_repository.get_commits(sha=self.github_target_branch.commit.sha)

            for commit_object in github_commits:
                commit = commit_object.commit

                commit_message_numbers = re.sub("\D+", '-', commit.message).strip('-').split('-')
                matched_item_numbers = [item_number for item_number in self.item_numbers if(item_number in commit_message_numbers)]
                if len(matched_item_numbers) > 0:
                    item_number = matched_item_numbers[0]

                    if self.output_to_terminal:
                        print('.', end='', flush=True)

                    pr_urls = (pull.html_url for pull in commit_object.get_pulls())
                    self.save_commit_info(commit, item_number, pr_urls=pr_urls)

        if self.use_pull_requests:
            for pull in self.github_repository.get_pulls(state="closed", base=self.target_branch_name):
                if self.search_date_limit != None and pull.created_at < self.search_date_limit:
                    break

                if pull.merged:
                    pull_head_branch_numbers = re.sub("\D+", '-', pull.head.ref).strip('-').split('-')

                    matched_item_numbers = [item_number for item_number in self.item_numbers if(item_number in pull_head_branch_numbers)]
                    if len(matched_item_numbers) > 0:
                        item_number = matched_item_numbers[0]
                        
                        if self.output_to_terminal:
                            print('.', end='', flush=True)

                        for commit_object in pull.get_commits():
                            self.save_commit_info(commit_object.commit, item_number, pr_url=pull.html_url)
                
    
    def output_commits(self) -> None:
        """
        Takes all commits stored in the class and outputs them according to all relevant settings
        """
        
        if len(self.commit_list) == 0:
            output = "No commits found"

            if self.output_to_terminal or self.output_to_excel:
                print("\n" + output)
            if self.output_to_txt:
                with open("output.txt", 'w') as file:
                    file.write(output)
            
            input()
            exit()

        total_output = ""
        output = f"Found {len(self.commit_list)} related commit{'' if len(self.commit_list) == 1 else 's'}"

        if self.output_to_terminal:
            print("\n" + output)
        if self.output_to_txt:
            total_output += output

        if self.group_commits_by_item:
            excel_data_list = []

            for item_number in self.item_numbers:
                if not item_number in self.item_commit_dictionary:
                    output = f"\nNo commits found for {item_number}\n\n---"

                    if self.output_to_terminal:
                        print(output)
                    if self.output_to_txt:
                        total_output += "\n" + output
                    continue

                item_commit_list = [self.commit_list[index] for index in self.item_commit_dictionary[item_number]]
                sorted_commit_list = sorted(item_commit_list, key=lambda x: x.date, reverse=self.order_commits_by_date_descend)

                if self.output_to_excel:
                    excel_data_list.extend(sorted_commit_list)

                if self.output_to_terminal or self.output_to_txt:
                    output = f"\nCommit{'' if len(item_commit_list) == 1 else 's'} for {item_number} ({len(item_commit_list)}):"
                    output += self.stringify_commits(sorted_commit_list)
                    output += "\n---"

                    if self.output_to_terminal:
                        print(output)
                    if self.output_to_txt:
                        total_output += "\n" + output

            
            if self.show_cherry_pick_command and (self.output_to_terminal or self.output_to_txt):
                # git cherry-pick command should stay in date-specific order, despite GroupCommitsByItem setting
                output = self.generate_cherry_pick_command(self.commit_list)

                if self.output_to_terminal:
                    print(output)
                if self.output_to_txt:
                    total_output += "\n" + output

            if self.output_to_excel:
                self.generate_excel_file(excel_data_list)

        else:
            sorted_commit_list = sorted(self.commit_list, key=lambda x: x.date, reverse=self.order_commits_by_date_descend)

            if self.output_to_excel:
                self.generate_excel_file(sorted_commit_list)

            if self.output_to_terminal or self.output_to_txt:
                output = f"Here are all commits for your items in {'descending' if self.order_commits_by_date_descend else 'acsending'} order:\n"
                output += self.stringify_commits(sorted_commit_list)
                
                if self.show_cherry_pick_command:
                    output += self.generate_cherry_pick_command(self.commit_list)

                if self.output_to_terminal:
                    print(output)
                if self.output_to_txt:
                    total_output += "\n" + output

        if self.output_to_txt:
            with open("output.txt", 'w') as file:
                file.write(total_output)
        
        if self.output_to_terminal:
            # Do not immediately close program
            input()
                

    def get_github_objects(self) -> None:
        """
        Connects to GitHub and pulls down the repository and target branch
        """

        auth = Auth.Token(self.github_token)
        github = Github(auth=auth)

        try:
            self.github_repository = github.get_repo(self.repository_name)
        except BadCredentialsException:
            print("Github responded with a Bad Credentials error. " +
                "Please ensure that your GitHubToken is valid and has the required permissions, then try again.")
            
            # Do not immediately close program
            input()
            exit()
        except GithubException as exception:
            if exception.data["message"] == "Not Found":
                print(f"Could not find the target repository '{self.repository_name}'. " +
                    "Please ensure that your TargetRepository is correct " + 
                    "and your GitHubToken has the required permissions to view the repository, then try again.")
            else:
                # Put any unhandled exception to the terminal
                raise exception

            # Do not immediately close program
            input()
            exit()

        try:
            self.github_target_branch = self.github_repository.get_branch(self.target_branch_name)
        except GithubException as exception:
            if exception.data["message"] == "Branch not found":
                print(f"Could not find the target branch '{self.target_branch_name}'. " +
                    "Please ensure that your TargetBranch exists, then try again.")
            else:
                # Put any unhandled exception to the terminal
                raise exception

            # Do not immediately close program
            input()
            exit()
