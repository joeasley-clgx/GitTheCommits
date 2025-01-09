import xlsxwriter.format
import xlsxwriter.worksheet
from CommitDetailVisibility import CommitDetailVisibility
from CommitInfo import CommitInfo
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from github import Github, Auth, GitCommit, GithubException, BadCredentialsException, Branch, Repository, PullRequest, Commit

import asyncio
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
    strip_characters_from_item_numbers: bool
    commit_detail_visibilty: CommitDetailVisibility
    group_commits_by_item: bool
    item_cherry_pick: bool
    order_commits_by_date_descend: bool
    use_commit_history: bool
    use_pull_requests: bool
    output_to_terminal: bool
    output_to_txt: bool
    output_to_excel: bool
    all_commits_cherry_pick_command: bool
    ignore_merge_commits: bool
    use_short_commit_hash: bool
    cherry_pick_command: str
    search_date_limit: datetime
    use_concurrent_commit_fetching: bool
    seconds_between_github_requests: int

    commit_list: list[CommitInfo]
    item_commit_dictionary: dict[int, list[int]] # item_number : commit_index

    github_repository: Repository.Repository
    github_target_branch: Branch.Branch


    def __init__(self, print_version = True) -> None:
        if print_version: 
            print("GitTheCommits v3.0.0\n")

        # Settings
        self.settings_are_set = False
        self.github_token = None
        self.repository_name = None
        self.target_branch_name = None
        self.strip_characters_from_item_numbers = None
        self.item_numbers = None
        self.commit_detail_visibilty = CommitDetailVisibility()
        self.group_commits_by_item = None
        self.item_cherry_pick = None
        self.order_commits_by_date_descend = None
        self.use_commit_history = None
        self.use_pull_requests = None
        self.output_to_terminal = None
        self.output_to_txt = None
        self.output_to_excel = None
        self.all_commits_cherry_pick_command = None
        self.ignore_merge_commits = None
        self.use_short_commit_hash = None
        self.cherry_pick_command = None
        self.search_date_limit = None
        self.use_concurrent_commit_fetching = None
        self.seconds_between_github_requests = None
        
        self.commit_list = []
        self.item_commit_dictionary = dict()

        self.github_repository = None
        self.github_target_branch = None


    def group_relevant_commit_info(self, git_commit: GitCommit.GitCommit, item_number, 
                                   pr_urls: tuple = None, pr_url: str = None) -> CommitInfo:
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


    def save_commit_info(self, commit: GitCommit.GitCommit, item_number: str, 
                         pr_urls: tuple = None, pr_url: str = None) -> None:
        """
        Adds commit to the commit_list and groups the index of that commit to the provided item_number in the item_commit_dictionary
        """

        def get_pull_request_number(url: str) -> int | None:
            if url == None:
                return None
            if '/' not in url:
                return None

            last_url_segment = url.split('/')[-1]

            if not last_url_segment.isnumeric():
                return None
            
            return int(last_url_segment)
        

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

                # store first pull request that commit appears in
                current_pr_number = get_pull_request_number(saved_commit.pr_url)
                new_pr_number = get_pull_request_number(pr_url)
                if current_pr_number is not None and new_pr_number is not None and new_pr_number < current_pr_number:
                    saved_commit.pr_url = pr_url


    def stringify_commits(self, commit_list: list[CommitInfo]) -> str:
        """
        Format the commit into a human-readable string
        """
        
        output = ""
        for commit in commit_list:
            if self.commit_detail_visibilty.message: 
                output += f"\n- {commit.message}"
            if self.commit_detail_visibilty.item_number: 
                output += f"\nItem{' Number' if self.strip_characters_from_item_numbers else ''}: {commit.item_number}"
            if self.commit_detail_visibilty.author: 
                output += f"\nAuthor: {commit.author}"
            if self.commit_detail_visibilty.date: 
                output += f"\nDate: {commit.date}"
            if self.commit_detail_visibilty.commit_url: 
                output += f"\nCommit URL: {commit.commit_url}"
            if self.commit_detail_visibilty.pull_request_url: 
                output += f"\nPull Request URL: {commit.pr_url}"
            if self.commit_detail_visibilty.sha: 
                output += f"\nSHA: {commit.sha}"
            if self.commit_detail_visibilty.is_merge_commit: 
                output += f"\nIs Merge Commit: {commit.is_merge}"
            if self.commit_detail_visibilty.cherry_pick_command: 
                output += f"\nCherry-Pick Command: {self.cherry_pick_command} {commit.sha}"
            output += "\n"
            
        return output


    def strip_non_digit_characters_from_list_of_strings(self, input: list) -> list[str]:
        """
        Strips all non-digit characters from a list of strings and returns that list
        """

        return [re.sub("\D", '', str(number)) for number in input]


    def manually_enter_item_numbers(self) -> list[str]:
        """
        Prompt the user to manually enter item numbers
        """

        print("No Jira items have been supplied. You can enter a list of item numbers under the \"ItemNumbers\" property in settings.json")
        enter_numbers_manually_input = input("Would you like to enter those item numbers now? (Y/N) ").lower()
        if len(enter_numbers_manually_input) > 0 and enter_numbers_manually_input[0] == 'y':
            item_numbers_input = input("Please enter your item numbers separated by commas. Press ENTER when done:\n")
            item_numbers = item_numbers_input.split(',')
            if self.strip_characters_from_item_numbers:
                item_numbers = self.strip_non_digit_characters_from_list_of_strings(item_numbers)
            print("Item numbers I'll search for:")
            print(", ".join([f"{item_number}" for item_number in item_numbers]) + "\n")
        else:
            print("Be sure to enter the Jira item numbers you need commits for in settings.json.")
            input("Press Enter to exit...")
            exit()
        
        return item_numbers


    def generate_cherry_pick_command(self, commits: list[CommitInfo]) -> str:
        """
        Sorts commits in acsending date order and returns a git cherry-pick command with those commits
        """
        
        sorted_commits = sorted(commits, key=lambda x: x.date)
        return f"{self.cherry_pick_command} {' '.join([commit.sha for commit in sorted_commits])}"


    def sort_item_numbers_by_commit_dates(self) -> list[str]:
        """
        Sorts the saved item numbers by the date of the item's commit dates
        """

        datetime_max_utc = datetime.max.replace(tzinfo=timezone.utc)
        datetime_min_utc = datetime.min.replace(tzinfo=timezone.utc)

        sorted_item_numbers = sorted(
            self.item_numbers, 
            key=lambda item_number: min(
                [self.commit_list[index].date for index in self.item_commit_dictionary[item_number]]
            ) if item_number in self.item_commit_dictionary else datetime_max_utc
        )
        
        if self.order_commits_by_date_descend:
            sorted_item_numbers.sort(
                key=lambda item_number: max(
                    [self.commit_list[index].date for index in self.item_commit_dictionary[item_number]]
                ) if item_number in self.item_commit_dictionary else datetime_min_utc, 
                reverse=True
            )
        
        return sorted_item_numbers


    def set_settings_via_dictionary(self, new_settings: dict) -> None:
        """
        Populates all settings via a dictionary
        """
        
        # GitHub Access Token: https://github.com/settings/tokens
        # Required Access: repo - Full control of private repositories 
        # (There's unfortuntately no read-only for private repositories)
        self.github_token = new_settings["GitHubToken"]
        self.repository_name = new_settings["TargetRepository"]
        self.target_branch_name = new_settings["TargetBranch"]

        # If true, removes all non-digit characters from the item numbers
        self.strip_characters_from_item_numbers = new_settings["StripCharactersFromItemNumbers"]

        if self.strip_characters_from_item_numbers:
            # Convert ItemNumbers into a string containing only numbers (1234 or "ITEM-1234" becomes "1234")
            self.item_numbers = self.strip_non_digit_characters_from_list_of_strings(new_settings["ItemNumbers"])
        else:
            # Ensure all item numbers are strings
            self.item_numbers = [str(item_number) for item_number in new_settings["ItemNumbers"]]

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
            cherry_pick_command=commitDetailsToShow["CherryPickCommand"]
        )

        # If true, groups each commit by the Jira item number
        self.group_commits_by_item = new_settings["GroupCommitsByItem"]

        # If true, shows one git cherry-pick command for all commits under an item
        self.item_cherry_pick = new_settings["ItemCherryPick"]

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
        self.all_commits_cherry_pick_command = new_settings["AllCommitsCherryPickCommand"]

        # If a commit has more than one parent, it will be excluded 
        # (Use case, ignore "merge develop to feature branch" commits)
        self.ignore_merge_commits = new_settings["IgnoreMergeCommits"]

        # Specifies whether to use full or short commit hashes in the output (short meaning first 7 characters)
        self.use_short_commit_hash = new_settings["UseShortCommitHash"]

        # Denotes all arguments for the git cherry-pick command
        cherry_pick_command_segments = [
            "git cherry-pick", 
            new_settings["GitCherryPickArguments"], '-m 1' if not self.ignore_merge_commits else ''
        ]
        if new_settings["GitCherryPickArguments"] == None or len(str(new_settings["GitCherryPickArguments"]).strip()) == 0:
            cherry_pick_command_segments.pop(1)

        self.cherry_pick_command = ' '.join(cherry_pick_command_segments).strip()
        
        # Limit how far back we search for commits
        self.search_date_limit = (
            datetime.today() - relativedelta(months=int(new_settings["SearchLimitMonths"]))
        ).replace(tzinfo=timezone.utc) if new_settings["SearchLimitMonths"] else None

        # Enables multiple commits to be fetched concurrently.
        # Speeds up the process but could cause rate-limiting related issues
        self.use_concurrent_commit_fetching = new_settings["UseConcurrentCommitFetching"]

        # The number of seconds to wait between each GitHub request (Default is 1 second)
        self.seconds_between_github_requests = new_settings["SecondsBetweenGithubRequests"]

        self.settings_are_set = True


    def set_settings(self, filename: str) -> str:
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
                return f"Your {filename} file has a syntax error on line {exception.lineno}. Please fix it and try again."


    def write_commit_details_to_worksheet(self, commit_list: list[CommitInfo], worksheet: xlsxwriter.worksheet.Worksheet, 
                                          row: int, data_format: xlsxwriter.format.Format, 
                                          centered_data_format: xlsxwriter.format.Format) -> None:
        """
        Writes the details of each commit to the worksheet and returns the number of rows added
        """

        rows_added = 0
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
                worksheet.write_string(row, data_column_number, commit.date.strftime("%m/%d/%Y, %H:%M:%S"), centered_data_format) 
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
            if self.commit_detail_visibilty.cherry_pick_command:
                worksheet.write_string(row, data_column_number, f"{self.cherry_pick_command} {commit.sha}", data_format) 
                data_column_number += 1
                
            row += 1
            rows_added += 1
        
        return rows_added


    def write_column_spanning_string_to_worksheet(self, worksheet: xlsxwriter.worksheet.Worksheet, row: int, 
                                                  column_letter: str, string: str, format: xlsxwriter.format.Format) -> None:
        """
        Writes a string to a cell that spans x columns
        """

        worksheet.merge_range(f"A{row + 1}:{column_letter}{row + 1}", string, format)


    def generate_excel_file(self) -> None:
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
                    input("Press Enter to continue...")
                else:
                    break

        with xlsxwriter.Workbook(f"output.xlsx") as workbook:
            worksheet = workbook.add_worksheet()

            header_format = workbook.add_format(
                {"bg_color": "#b8cce4", "align": "center", "border": 1, "border_color": "black"}
            )
            subheader_format = workbook.add_format(
                {"bg_color": "#d8d8d8", "align": "left", "border": 1, "border_color": "#d9d9d9"}
            )
            data_format = workbook.add_format(
                {"bg_color": "white", "align": "left", "border": 1, "border_color": "#d9d9d9"}
            )
            data_warning_format = workbook.add_format(
                {"bg_color": "#ffff7f", "align": "left", "border": 1, "border_color": "#ffff7f"}
            )
            centered_data_format = workbook.add_format(
                {"bg_color": "white", "align": "center", "border": 1, "border_color": "#d0d0d0"}
            )

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
                worksheet.write_string(f'{letter}1', f"Item{' Number' if self.strip_characters_from_item_numbers else ''}", header_format)
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
                worksheet.write_string(f'{letter}1', "Pull Request Url(s)", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.sha: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 10 if self.use_short_commit_hash else 42)
                worksheet.write_string(f'{letter}1', "Sha", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.is_merge_commit: 
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 16)
                worksheet.write_string(f'{letter}1', "Is Merge Commit", header_format)
                header_column_number += 1
            if self.commit_detail_visibilty.cherry_pick_command:
                letter = letter_dictionary[header_column_number]
                worksheet.set_column(f"{letter}:{letter}", 80)
                worksheet.write_string(f'{letter}1', "Cherry-Pick Command", header_format)
                header_column_number += 1

            # THE DATA
            last_column_letter = letter_dictionary[max(header_column_number - 1, 1)]
            row = 1
            if self.group_commits_by_item:
                sorted_item_numbers = self.sort_item_numbers_by_commit_dates()
                
                for item_number in sorted_item_numbers:
                    # No commits found
                    if not item_number in self.item_commit_dictionary:
                        no_commits_string = f"No commits found for '{item_number}'"
                        self.write_column_spanning_string_to_worksheet(worksheet, row, last_column_letter, 
                                                                       no_commits_string, data_warning_format)
                        row += 1
                        continue

                    item_commit_list = [self.commit_list[index] for index in self.item_commit_dictionary[item_number]]
                    sorted_commit_list = sorted(item_commit_list, key=lambda x: x.date, reverse=self.order_commits_by_date_descend or 0)

                    # Commit info
                    item_commits_string = f"Commit{'' if len(item_commit_list) == 1 else 's'} for {item_number} ({len(item_commit_list)}):"
                    
                    self.write_column_spanning_string_to_worksheet(worksheet, row, last_column_letter, 
                                                                   item_commits_string, subheader_format)
                    row += 1

                    rows_added = self.write_commit_details_to_worksheet(item_commit_list, worksheet, row, 
                                                                        data_format, centered_data_format)
                    row += rows_added
                    
                    # Cherry Pick Command
                    if self.item_cherry_pick:
                        item_cherry_pick_string = self.generate_cherry_pick_command(item_commit_list)

                        # leave a blank space between the last commit and the cherry-pick command
                        self.write_column_spanning_string_to_worksheet(worksheet, row, last_column_letter, 
                                                                       None, data_format)
                        row += 1
                        self.write_column_spanning_string_to_worksheet(worksheet, row, last_column_letter, 
                                                                       item_cherry_pick_string, data_format)
                        row += 1
                    
            else:
                if len(self.commit_list) == 0:
                    no_commits_string = "No commits found"
                    self.write_column_spanning_string_to_worksheet(worksheet, 1, letter_dictionary[max(header_column_number - 1, 1)], 
                                                                no_commits_string, data_warning_format)
                    return

                sorted_commit_list = sorted(self.commit_list, key=lambda x: x.date, reverse=self.order_commits_by_date_descend or 0)
                rows_added = self.write_commit_details_to_worksheet(sorted_commit_list, worksheet, row, 
                                                                    data_format, centered_data_format)
                row += rows_added

            if self.all_commits_cherry_pick_command:
                # git cherry-pick command should stay in date-specific order, despite GroupCommitsByItem setting
                cherry_pick_command_string = self.generate_cherry_pick_command(self.commit_list)

                # leave a blank space between the last commit and the cherry-pick command
                self.write_column_spanning_string_to_worksheet(worksheet, row, last_column_letter, None, data_format)
                row += 1
                self.write_column_spanning_string_to_worksheet(worksheet, row, last_column_letter, 
                                                               cherry_pick_command_string, subheader_format)
                row += 1


    async def fetch_commits(self) -> None:
        """
        Uses the class' GitHub properties to fetch all commits according to all relevant settings
        """

        async def process_pull_requests_async(pull: PullRequest.PullRequest) -> None:
            def process_pull_requests(pull: PullRequest.PullRequest):
                if self.search_date_limit != None and pull.created_at < self.search_date_limit:
                    return

                if pull.merged:
                    # To explain the '|' characters: When we search for 'ITEM-123' in 'ITEM-12345', we get a match
                    # To prevent that, we add '|' on the end so we end up searching for 'ITEM-123|' in 'ITEM-12345|'
                    pull_head_branch = pull.head.ref + '|'
                    
                    if self.strip_characters_from_item_numbers:
                        pull_head_branch = [branch_name + '|' for branch_name in re.sub("\D+", '-', pull_head_branch).strip('-').split('-')]

                    matched_item_numbers = [item_number for item_number in self.item_numbers if(item_number + '|' in pull_head_branch)]
                    if len(matched_item_numbers) > 0:
                        item_number = matched_item_numbers[0]
                        
                        if self.output_to_terminal:
                            print('.', end='', flush=True)

                        for commit_object in pull.get_commits():
                            self.save_commit_info(commit_object.commit, item_number, pr_url=pull.html_url)

            return await asyncio.to_thread(process_pull_requests, pull)

        
        async def process_commits_async(commit_object: Commit.Commit) -> None:
            def process_commits(commit_object: Commit.Commit):
                commit = commit_object.commit

                commit_message = commit.message
                if self.strip_characters_from_item_numbers:
                    commit_message = re.sub("\D+", '-', commit_message).strip('-').split('-')

                matched_item_numbers = [item_number for item_number in self.item_numbers if(item_number in commit_message)]
                if len(matched_item_numbers) > 0:
                    item_number = matched_item_numbers[0]

                    if self.output_to_terminal:
                        print('.', end='', flush=True)

                    pr_urls = (pull.html_url for pull in commit_object.get_pulls())
                    self.save_commit_info(commit, item_number, pr_urls=pr_urls)
            
            return await asyncio.to_thread(process_commits, commit_object)

        
        if len(self.item_numbers) == 0:
            self.item_numbers = self.manually_enter_item_numbers()
        
        if self.output_to_terminal:
            print("Fetching commits", end='', flush=True)
        if self.use_commit_history:
            github_commits = None
            if self.search_date_limit != None:
                github_commits = self.github_repository.get_commits(sha=self.github_target_branch.commit.sha, 
                                                                    since=self.search_date_limit) 
            else:
                github_commits =  self.github_repository.get_commits(sha=self.github_target_branch.commit.sha)

            if self.use_concurrent_commit_fetching:
                await asyncio.gather(*[process_commits_async(commit_object) for commit_object in github_commits])
            else:
                for commit_object in github_commits:
                    await process_commits_async(commit_object)

        if self.use_pull_requests:
            pull_requests = self.github_repository.get_pulls(state="closed", base=self.target_branch_name)

            if self.use_concurrent_commit_fetching:
                await asyncio.gather(*[process_pull_requests_async(pull) for pull in pull_requests])
            else:
                for pull in pull_requests:
                    await process_pull_requests_async(pull)


    def output_commits(self) -> list[CommitInfo]:
        """
        Takes all commits stored in the class and outputs them according to all relevant settings
        """

        if self.output_to_excel:
            self.generate_excel_file()
        
        if len(self.commit_list) == 0:
            output = "No commits found"

            if self.output_to_terminal:
                print("\n" + output)
            if self.output_to_txt:
                with open("output.txt", 'w') as file:
                    file.write(output)

            if self.output_to_terminal:
                input("Press Enter to exit...")
            return []

        total_commits = []
        total_output = ""
        output = f"Found {len(self.commit_list)} related commit{'' if len(self.commit_list) == 1 else 's'}"

        if self.output_to_terminal:
            print("\n" + output)
        if self.output_to_txt:
            total_output += output

        if self.group_commits_by_item:
            sorted_item_numbers = self.sort_item_numbers_by_commit_dates()

            for item_number in sorted_item_numbers:
                # No commits found
                if not item_number in self.item_commit_dictionary:
                    output = f"\nNo commits found for '{item_number}'\n\n---"

                    if self.output_to_terminal:
                        print(output)
                    if self.output_to_txt:
                        total_output += "\n" + output
                    continue

                item_commit_list = [self.commit_list[index] for index in self.item_commit_dictionary[item_number]]
                sorted_commit_list = sorted(item_commit_list, key=lambda x: x.date, reverse=self.order_commits_by_date_descend)
                total_commits.extend(sorted_commit_list)

                # Commit info
                if self.output_to_terminal or self.output_to_txt:
                    output = f"\nCommit{'' if len(item_commit_list) == 1 else 's'} for {item_number} ({len(item_commit_list)}):"
                    output += self.stringify_commits(sorted_commit_list)

                    # Cherry Pick Command
                    if self.item_cherry_pick:
                        output += "\n" + self.generate_cherry_pick_command(item_commit_list)

                    output += "\n---"

                    if self.output_to_terminal:
                        print(output)
                    if self.output_to_txt:
                        total_output += "\n" + output
            
            if self.all_commits_cherry_pick_command and (self.output_to_terminal or self.output_to_txt):
                # git cherry-pick command should stay in date-specific order, despite GroupCommitsByItem setting
                output = "\n" + self.generate_cherry_pick_command(self.commit_list)

                if self.output_to_terminal:
                    print(output)
                if self.output_to_txt:
                    total_output += "\n" + output
        else:
            sorted_commit_list = sorted(self.commit_list, key=lambda x: x.date, reverse=self.order_commits_by_date_descend)
            total_commits.extend(sorted_commit_list)

            if self.output_to_terminal or self.output_to_txt:
                output = f"Here are all commits for your items in {'descending' if self.order_commits_by_date_descend else 'acsending'} order:\n"
                output += self.stringify_commits(sorted_commit_list)
                
                if self.all_commits_cherry_pick_command:
                    output += "\n" + self.generate_cherry_pick_command(self.commit_list)

                if self.output_to_terminal:
                    print(output)
                if self.output_to_txt:
                    total_output += "\n" + output

        if self.output_to_txt:
            with open("output.txt", 'w') as file:
                file.write(total_output)
        
        if self.output_to_terminal:
            # Do not immediately close program
            input("Press Enter to exit...")

        return total_commits


    def get_github_objects(self) -> str:
        """
        Connects to GitHub and pulls down the repository and target branch
        """

        auth = Auth.Token(self.github_token)
        github = Github(auth=auth, seconds_between_requests=self.seconds_between_github_requests)

        try:
            self.github_repository = github.get_repo(self.repository_name)
        except BadCredentialsException:
            return "Github responded with a Bad Credentials error. \nPlease ensure that your GitHubToken is valid and has the required permissions, \nthen try again."
        
        except GithubException as exception:
            if exception.data["message"] == "Not Found":
                return f"Could not find the target repository '{self.repository_name}'. \nPlease ensure that your TargetRepository is correct \nand your GitHubToken has the required permissions to view the repository, \nthen try again."
            else:
                # Put any unhandled exception to the terminal
                raise exception

        try:
            self.github_target_branch = self.github_repository.get_branch(self.target_branch_name)
        except GithubException as exception:
            if exception.data["message"] == "Branch not found":
                return f"Could not find the target branch '{self.target_branch_name}'. \nPlease ensure that your TargetBranch exists, then try again."
            else:
                # Put any unhandled exception to the terminal
                raise exception
