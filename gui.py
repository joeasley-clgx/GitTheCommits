import asyncio
import customtkinter
import json
import math
import threading
import tkinter

from CommitDetailVisibility import CommitDetailVisibility
from CommitInfo import CommitInfo
from datetime import datetime
from GitTheCommits import GitTheCommits


class AppRoot(customtkinter.CTk):
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
    original_settings: dict

    github_token_valid: bool
    repository_name_valid: bool
    target_branch_name_valid: bool

    git_the_commits: GitTheCommits

    DEFAULT_BORDER_COLOR = "#d9d9d9"
    ERROR_BORDER_COLOR = "#d90000"


    def __init__(self, settings_filename: str) -> None:
        super().__init__()
        self.title('GitTheCommits v3.0.0')
        self.geometry('950x664')

        self.settings_filename = settings_filename
        
        # settings
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

        self.github_token_valid = False
        self.repository_name_valid = False
        self.target_branch_name_valid = False

        self.git_the_commits = GitTheCommits(False)

        self.tab_view = TabView(self)
        self.tab_view.pack(fill='both', padx=17)
        self.tab_view.set("Output")

        self.DEFAULT_BORDER_COLOR = customtkinter.CTkEntry(self).cget('border_color')

    
    def update_original_settings(self) -> None:
        self.original_settings = json.load(open(self.settings_filename, 'r'))


    def update_github_token_validity(self, value: bool) -> None:
        self.github_token_valid = value
        self.update_settings_validity()


    def update_repository_name_validity(self, value: bool) -> None:
        self.repository_name_valid = value
        self.update_settings_validity()

    
    def update_target_branch_name_validity(self, value: bool) -> None:
        self.target_branch_name_valid = value
        self.update_settings_validity()


    def update_settings_validity(self) -> None:
        if self.github_token_valid and self.repository_name_valid and self.target_branch_name_valid:
            self.tab_view.output_frame.fetch_commits_button.configure(state="normal")
            self.tab_view.settings_frame.save_button.configure(state="normal")
        else:
            self.tab_view.output_frame.fetch_commits_button.configure(state="disabled")
            self.tab_view.settings_frame.save_button.configure(state="disabled")


class TabView(customtkinter.CTkTabview):
    def __init__(self, app_root: AppRoot, **kwargs) -> None:
        super().__init__(app_root, **kwargs)
        self.app_root = app_root

        # Create the tabs
        self.add("Settings")
        self.settings_frame = SettingsFrame(self.tab("Settings"), self)
        self.settings_frame.pack(fill='both')

        self.add("Output")
        self.output_frame = OutputFrame(self.tab("Output"), self)
        self.output_frame.pack(fill='both')


class OutputFrame(customtkinter.CTkFrame):
    def __init__(self, master: customtkinter.CTkFrame, tab_view: TabView, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.tab_view = tab_view
        self.fetch_commits_thread = None
        self.is_fetching_commits = False

        self.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Item Numbers
        self.item_numbers_frame = ItemNumbersListFrame(self)
        self.item_numbers_frame.grid(row=0, column=0, sticky='nswe', pady=5, padx=5)

        # Add Item Number Button
        self.add_item_number_button = customtkinter.CTkButton(self, text="Add Item Number", 
                                                              command=self.item_numbers_frame.add_item_number_entry)
        self.add_item_number_button.grid(row=1, column=0, sticky='swe', pady=5, padx=5)

        # Save Item Numbers Button
        self.save_item_numbers_button = customtkinter.CTkButton(self, text="Save Item Numbers", 
                                                                command=self.save_item_numbers)
        self.save_item_numbers_button.grid(row=2, column=0, sticky='swe', pady=5, padx=5)

        # Fetch Commits Button
        self.fetch_commits_button = customtkinter.CTkButton(self, text="Fetch Commits", 
                                                            command=self.fetch_commits_button_clicked)
        self.fetch_commits_button.grid(row=3, column=0, sticky='swe', pady=5, padx=5)

        # Commits Display
        self.results_frame = ResultsFrame(self)
        self.results_frame.grid(row=0, column=1, columnspan=7, rowspan=4, sticky='we', pady=5)


    def fetch_commits_button_clicked(self) -> None:
        if not self.is_fetching_commits:
            if len(self.item_numbers_frame.get_item_numbers()) == 0:
                self.results_frame.commits_frame.clear_displayed_commits()
                self.results_frame.commits_frame.add_status_label(
                    "Please add at least one item number to fetch commits for"
                )
                return

            self.save_item_numbers()

            self.fetch_commits_button.configure(text="Exit Program to Cancel", state="disabled")
            self.add_item_number_button.configure(state="disabled")
            self.save_item_numbers_button.configure(state="disabled")
            self.is_fetching_commits = True

            self.results_frame.start_progress_bar()
            self.fetch_commits_thread = threading.Thread(target=self.fetch_commits, daemon=True)
            self.fetch_commits_thread.start() 


    def save_item_numbers(self) -> None:
        self.tab_view.settings_frame.save_settings(self.item_numbers_frame.get_item_numbers())


    def fetch_commits(self) -> None:
        git_the_commits = self.tab_view.app_root.git_the_commits

        self.item_numbers_frame.disable_all_entries()

        item_numbers = self.item_numbers_frame.get_item_numbers()
        if git_the_commits.strip_characters_from_item_numbers:
            item_numbers = git_the_commits.strip_non_digit_characters_from_list_of_strings(item_numbers)
        git_the_commits.item_numbers = item_numbers

        self.results_frame.commits_frame.clear_displayed_commits()
        self.results_frame.commits_frame.add_status_label("Connecting to GitHub")
        github_error = git_the_commits.get_github_objects()

        if github_error:
            self.results_frame.commits_frame.clear_displayed_commits()
            self.results_frame.commits_frame.add_status_label(github_error)
            self.results_frame.stop_progress_bar()
            self.is_fetching_commits = False
            self.fetch_commits_button.configure(text="Fetch Commits", state="normal")
            self.add_item_number_button.configure(state="normal")
            self.save_item_numbers_button.configure(state="normal")
            return

        self.results_frame.commits_frame.clear_displayed_commits()
        self.results_frame.commits_frame.add_status_label("Fetching Commits")
        asyncio.run(git_the_commits.fetch_commits())

        self.results_frame.commits_frame.clear_displayed_commits()
        commits = git_the_commits.output_commits()
        self.is_fetching_commits = False

        if len(commits) == 0:
            self.results_frame.commits_frame.add_status_label("No commits found")
        else:
            self.results_frame.commits_frame.update_commit_entries(commits)


        self.item_numbers_frame.enable_all_entries()
        self.results_frame.stop_progress_bar()
        self.fetch_commits_button.configure(text="Fetch Commits", state="normal")
        self.add_item_number_button.configure(state="normal")
        self.save_item_numbers_button.configure(state="normal")


class ResultsFrame(customtkinter.CTkFrame):
    def __init__(self, output_frame: OutputFrame, **kwargs) -> None:
        super().__init__(output_frame, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.output_frame = output_frame

        self.commits_frame = CommitsFrame(self, width=100, height=550)
        self.commits_frame.grid(row=0, column=0, sticky='nwe', pady=5, padx=5)

        # Progress Bar
        self.progress_bar = customtkinter.CTkProgressBar(self)
        self.stop_progress_bar()
        self.progress_bar.grid(row=1, column=0, sticky='swe', padx=5, pady=5)

    
    def start_progress_bar(self) -> None:
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.set(0)
        self.progress_bar.start()


    def stop_progress_bar(self) -> None:
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1)
        self.progress_bar.stop()


class CommitsFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, results_frame: ResultsFrame, **kwargs) -> None:
        super().__init__(results_frame, **kwargs)
        self.results_frame = results_frame

        self.displayed_elements = []
        self.cached_commits = []
        
        self.update_commit_entries(self.cached_commits)


    def add_results_header(self, text: str) -> None:
        header_label = customtkinter.CTkLabel(self, text=text, font=customtkinter.CTkFont(size=20, weight="bold"))
        self.displayed_elements.append(header_label)
        header_label.pack(anchor='w', fill='x')


    def add_status_label(self, text: str) -> None:
        status_label = customtkinter.CTkLabel(self, text=text, font=customtkinter.CTkFont(size=16))
        self.displayed_elements.append(status_label)
        status_label.pack(anchor='w', fill='x', pady=5)


    def add_commit_entry(self, commit: CommitInfo) -> None:
        new_entry = CommitEntryFrame(self, commit, fg_color=self.cget('bg_color'))
        self.displayed_elements.append(new_entry)
        new_entry.pack(anchor='w', pady=5, fill='x')

    
    def add_cherry_pick_command(self, label_text: str, cherry_pick_text: str) -> None:
        message_lines = math.ceil(len(cherry_pick_text) / 80) + 1 # +1 for the label
        cherry_pick_textbox = customtkinter.CTkTextbox(
            self, height=(18 * message_lines) + 10, border_width=0, fg_color=self.cget('bg_color'), 
            wrap='word', activate_scrollbars=False)
        
        self.displayed_elements.append(cherry_pick_textbox)
        cherry_pick_textbox.insert("0.0", label_text + '\n' + cherry_pick_text)
        cherry_pick_textbox.configure(state="disabled")
        cherry_pick_textbox.pack(anchor='w', pady=5, fill='x')


    def update_commit_entries(self, commits: list[CommitInfo] = None) -> None:
        if self.results_frame.output_frame.is_fetching_commits:
            return

        if commits is not None:
            self.cached_commits = commits
        else:
            commits = self.cached_commits

        if commits is None or len(commits) == 0:
            self.clear_displayed_commits()
            self.add_status_label("Please enter your item numbers on the left and click 'Fetch Commits'")
            return

        git_the_commits = self.results_frame.output_frame.tab_view.app_root.git_the_commits
        order_commits_by_date_descend = git_the_commits.order_commits_by_date_descend
        commits.sort(key=lambda x: x.date, reverse=order_commits_by_date_descend)

        self.clear_displayed_commits()
        if git_the_commits.group_commits_by_item:
            sorted_item_numbers = git_the_commits.sort_item_numbers_by_commit_dates()

            for item_number in sorted_item_numbers:
                item_commits = [commit for commit in commits if commit.item_number == item_number]

                # No commits found
                if len(item_commits) == 0:
                    self.add_status_label(f"No commits found for{' Item Number' if git_the_commits.strip_characters_from_item_numbers else ''} '{item_number}'")
                    continue
                
                # Commit info
                self.add_results_header(f"Item{' Number' if git_the_commits.strip_characters_from_item_numbers else ''}: {item_number}")
                for commit in item_commits:
                    self.add_commit_entry(commit)

                # Cherry Pick Command
                if git_the_commits.item_cherry_pick:
                    cherry_pick_text = f"{git_the_commits.cherry_pick_command} {' '.join([commit.sha for commit in commits if commit.item_number == item_number])}"
                    self.add_cherry_pick_command("Item Cherry Pick:", cherry_pick_text)
        else:
            for commit in commits:
                self.add_commit_entry(commit)

        if git_the_commits.all_commits_cherry_pick_command:
            all_commits_cherry_pick_text = git_the_commits.generate_cherry_pick_command(git_the_commits.commit_list)
            self.add_cherry_pick_command("All Commits Cherry Pick:", all_commits_cherry_pick_text)


    def clear_displayed_commits(self) -> None:
        for entry in self.displayed_elements:
            entry.pack_forget()
        self.displayed_elements = []


class CommitEntryFrame(customtkinter.CTkFrame):
    def __init__(self, commits_frame: CommitsFrame, commit: CommitInfo, **kwargs) -> None:
        super().__init__(commits_frame, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.commits_frame = commits_frame

        git_the_commits = self.commits_frame.results_frame.output_frame.tab_view.app_root.git_the_commits

        if git_the_commits.commit_detail_visibilty.message:
            message_lines = sum((math.ceil(len(line) / 60) for line in commit.message.splitlines()))
            self.commit_message_label = customtkinter.CTkTextbox(
                self, height=(20 * message_lines) + 10, border_width=0, fg_color=self.cget('fg_color'), 
                font=customtkinter.CTkFont(size=12, weight="bold"), wrap='word', activate_scrollbars=False)
            
            self.commit_message_label.insert("0.0", commit.message)
            self.commit_message_label.configure(state="disabled")
            self.commit_message_label.pack(anchor='w', padx=5, fill='x')

        if git_the_commits.commit_detail_visibilty.item_number: 
            self.add_commit_detail_label(f"\nItem{' Number' if git_the_commits.strip_characters_from_item_numbers else ''}", commit.item_number)

        if git_the_commits.commit_detail_visibilty.author: 
            self.add_commit_detail_label("Author", commit.author)

        if git_the_commits.commit_detail_visibilty.date: 
            self.add_commit_detail_label("Date", commit.date)

        if git_the_commits.commit_detail_visibilty.commit_url: 
            self.add_commit_detail_label("Commit URL", commit.commit_url)

        if git_the_commits.commit_detail_visibilty.pull_request_url: 
            self.add_commit_detail_label("Pull Request URL", commit.pr_url)

        if git_the_commits.commit_detail_visibilty.sha: 
            self.add_commit_detail_label("SHA", commit.sha)

        if git_the_commits.commit_detail_visibilty.is_merge_commit: 
            self.add_commit_detail_label("Is Merge Commit", commit.is_merge)

        if git_the_commits.commit_detail_visibilty.cherry_pick_command: 
            self.add_commit_detail_label("Cherry-Pick Command", f"{git_the_commits.cherry_pick_command} {commit.sha}")


    def add_commit_detail_label(self, label_text: str, value: str) -> None:
        # I know the function says "label", but label text can't be selected and copied.
        # An entry can be copied, so we dress up an entry to look like a label ;)
        label = customtkinter.CTkEntry(self, border_width=0, fg_color=self.cget('fg_color'), height=20)
        label.insert(0, f"{label_text}: {value}")
        label.configure(state="readonly")
        label.pack(anchor='w', padx=5, fill='x')


class ItemNumbersListFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, output_frame: OutputFrame, **kwargs) -> None:
        super().__init__(output_frame, **kwargs)
        self.output_frame = output_frame
        self.entries_are_disabled = False

        self.item_number_label = customtkinter.CTkLabel(self, text="Item Numbers:", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.item_number_label.pack(anchor='n', padx=5)

        self.item_number_entries = []

        # Initialize with any item numbers from the settings file
        if self.output_frame.tab_view.app_root.item_numbers:
            for item_number in self.output_frame.tab_view.app_root.item_numbers:
                self.add_item_number_entry(item_number)
        else:
            self.add_item_number_entry()


    def update_item_number_entries(self) -> None:
        disable_remove_buttons = len(self.item_number_entries) == 1
        for entry in self.item_number_entries:
            if disable_remove_buttons:
                entry.disable_remove_button()
            else:
                entry.enable_remove_button()

    
    def add_item_number_entry(self, value: str = None) -> None:
        new_entry = ItemNumberEntryFrame(self, value)
        new_entry.focus_entry()

        self.item_number_entries.append(new_entry)
        new_entry.pack(pady=5, fill='x')

        self.update_item_number_entries()


    def remove_item_number_entry(self, entry: customtkinter.CTkButton) -> None:
        # focus the previous entry if it exists
        if self.item_number_entries.index(entry) > 0:
            self.item_number_entries[self.item_number_entries.index(entry) - 1].focus_entry()

        entry.remove_bindings()
        self.item_number_entries.remove(entry)
        entry.pack_forget()
        entry.grid_forget()

        self.update_item_number_entries()


    def get_item_numbers(self) -> None:
        item_numbers = []
        for entry in self.item_number_entries:
            item_number = entry.item_number_entry.get()
            if item_number:
                item_numbers.append(item_number)
        return item_numbers

    
    def add_or_focus_next_entry(self, entry: customtkinter.CTkEntry) -> None:
        if self.entries_are_disabled:
            return

        if entry == self.item_number_entries[-1]:
            self.add_item_number_entry()
        else:
            index = self.item_number_entries.index(entry)
            self.item_number_entries[index + 1].focus_entry()


    def focus_previous_entry(self, entry: customtkinter.CTkEntry) -> None:
        if self.entries_are_disabled:
            return
        
        if entry == self.item_number_entries[0]:
            return
        index = self.item_number_entries.index(entry)
        self.item_number_entries[index - 1].focus_entry()

    
    def focus_next_entry(self, entry: customtkinter.CTkEntry) -> None:
        if self.entries_are_disabled:
            return
        
        if entry == self.item_number_entries[-1]:
            return
        index = self.item_number_entries.index(entry)
        self.item_number_entries[index + 1].focus_entry()

    
    def disable_all_entries(self) -> None:
        self.entries_are_disabled = True
        for entry in self.item_number_entries:
            entry.disable_entry()
            
    
    def enable_all_entries(self) -> None:
        self.entries_are_disabled = False
        for entry in self.item_number_entries:
            entry.enable_entry()


class ItemNumberEntryFrame(customtkinter.CTkFrame):
    def __init__(self, item_numbers_list_frame: ItemNumbersListFrame, value: str = None, **kwargs) -> None:
        super().__init__(item_numbers_list_frame, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.item_numbers_list_frame = item_numbers_list_frame

        self.item_number_entry = customtkinter.CTkEntry(self)
        if value:
            self.item_number_entry.insert(0, value)

        self.item_number_entry.bind("<Return>", lambda _: self.item_numbers_list_frame.add_or_focus_next_entry(self))
        self.item_number_entry.bind("<Up>", lambda _: self.item_numbers_list_frame.focus_previous_entry(self))
        self.item_number_entry.bind("<Down>", lambda _: self.item_numbers_list_frame.focus_next_entry(self))

        self.item_number_entry.grid(row=0, column=0, sticky='we')

        self.remove_button = customtkinter.CTkButton(self, text="X", width=30, command=lambda: self.item_numbers_list_frame.remove_item_number_entry(self))
        self.remove_button.configure(fg_color=self.remove_button.cget('text_color'), 
                                     hover_color=self.remove_button.cget('border_color'), 
                                     text_color=self.remove_button.cget('bg_color'))

        self.remove_button.grid(row=0, column=1, sticky='e')


    def disable_remove_button(self) -> None:
        self.remove_button.configure(state="disabled")


    def enable_remove_button(self) -> None:
        self.remove_button.configure(state="normal")

    
    def focus_entry(self) -> None:
        self.item_number_entry.focus()

    
    def remove_bindings(self) -> None:
        self.item_number_entry.unbind("<Return>")
        self.item_number_entry.unbind("<Up>")
        self.item_number_entry.unbind("<Down>")


    def disable_entry(self) -> None:
        self.is_disabled = True
        self.item_number_entry.configure(state="disabled")
        self.disable_remove_button()

    
    def enable_entry(self) -> None:
        self.is_disabled = False
        self.item_number_entry.configure(state="normal")
        self.enable_remove_button()


class SettingsFrame(customtkinter.CTkFrame):
    # Private class enums
    DIGIT = 1
    FLOAT = 2

    GITHUB_TOKEN = 1
    TARGET_REPOSITORY = 2
    TARGET_BRANCH = 3

    def __init__(self, master: customtkinter.CTkFrame, tab_view: TabView, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.tab_view = tab_view

        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Text Inputs
        self.github_token_label, self.github_token = self.create_entry_setting_input(
            "GitHub Token:", 0, 0, 3, hide_text=True, placeholder_text="Required. Example: ghp_abcdefghijklmnopqrstuvwxyz1234567890", 
            bind_method=lambda _: self.handle_github_token_entry())
        
        self.target_repository_label, self.target_repository = self.create_entry_setting_input(
            "Target Repository:", 1, 0, 3, placeholder_text="Required. Example: user/repository", 
            bind_method=lambda _: self.handle_target_repository_entry())
        
        self.target_branch_label, self.target_branch = self.create_entry_setting_input(
            "Target Branch:", 2, 0, 3, placeholder_text="Required. Example: develop",
            bind_method=lambda _: self.handle_target_branch_entry())
        
        self.cherry_pick_label, self.cherry_pick = self.create_entry_setting_input(
            "Cherry Pick Arguments:", 3, 0, 3, placeholder_text="Suggested: -n --strategy=recursive")
        
        self.search_limit_months_label, self.search_limit_months = self.create_entry_setting_input(
            "Search Limit Months:", 4, 0, 1, 'w', value_type=self.DIGIT)
        
        self.seconds_between_github_requests_label, self.seconds_between_github_requests = self.create_entry_setting_input(
            "Seconds Between Github Requests:", 5, 0, 1, 'w', value_type=self.FLOAT)

        # Boolean Inputs
        self.ignore_merge_commits_label, self.ignore_merge_commits = self.create_switch_setting_input("Ignore Merge Commits:", 6, 0)
        self.group_commits_by_item_label, self.group_commits_by_item = self.create_switch_setting_input("Group Commits By Item:", 7, 0)
        self.item_cherry_pick_label, self.item_cherry_pick = self.create_switch_setting_input("Group Commit Cherry Pick Arguments:", 8, 0)
        self.output_to_excel_file_label, self.output_to_excel_file = self.create_switch_setting_input("Output To Excel File:", 9, 0)
        self.output_to_txt_file_label, self.output_to_txt_file = self.create_switch_setting_input("Output To Text File:", 10, 0)
        self.all_commits_cherry_pick_command_label, self.all_commits_cherry_pick_command = self.create_switch_setting_input("All Items Cherry Pick Command:", 11, 0)
        self.show_commits_in_date_descending_order_label, self.show_commits_in_date_descending_order = self.create_switch_setting_input("Show Commits In Date Descending Order:", 12, 0)
        self.strip_characters_label, self.strip_characters = self.create_switch_setting_input("Strip Characters From Item Numbers:", 13, 0)
        self.use_short_commit_hash_label, self.use_short_commit_hash = self.create_switch_setting_input("Use Short Commit Hash:", 14, 0)
        self.use_concurrent_commit_fetching_label, self.use_concurrent_commit_fetching = self.create_switch_setting_input("Use Concurrent Commit Fetching:", 15, 0)
        
        # Use commit history or pull requests
        self.radio_var = tkinter.IntVar(value=0)
        self.radio_button_1 = customtkinter.CTkRadioButton(master=self, variable=self.radio_var, value=0, text="Use Commit History")
        self.radio_button_1.grid(row=4, column=2, sticky="we")
        self.radio_button_2 = customtkinter.CTkRadioButton(master=self, variable=self.radio_var, value=1, text="Use Pull Requests")
        self.radio_button_2.grid(row=4, column=3, sticky="we")

        # Commit Details To Show
        self.commit_details_to_show_frame = CommitDetailsToShowSubFrame(self)
        self.commit_details_to_show_frame.grid(row=5, column=2, columnspan=2, rowspan=11, sticky='we', pady=10)

        # Save Button
        self.save_button = customtkinter.CTkButton(self, text="Save", command=self.save_settings_button_clicked)
        self.save_button.grid(row=16, column=3, sticky='e', pady=5, padx=5)

        self.tab_view.app_root.update_original_settings()
        self.load_settings(self.tab_view.app_root.original_settings)


    def load_settings(self, settings_dict: dict[str, any]) -> None:
        if settings_dict["GitHubToken"] is not None and settings_dict["GitHubToken"] != "":
            self.github_token.delete(0, 'end')
            self.github_token.insert(0, settings_dict["GitHubToken"])
            self.tab_view.app_root.github_token_valid = True
        else:
            self.tab_view.app_root.github_token_valid = False

        if settings_dict["TargetRepository"] is not None and settings_dict["TargetRepository"] != "":
            self.target_repository.delete(0, 'end')
            self.target_repository.insert(0, settings_dict["TargetRepository"])
            self.tab_view.app_root.repository_name_valid = True
        else:
            self.tab_view.app_root.repository_name_valid = False

        if settings_dict["TargetBranch"] is not None and settings_dict["TargetBranch"] != "":
            self.target_branch.delete(0, 'end')
            self.target_branch.insert(0, settings_dict["TargetBranch"])
            self.tab_view.app_root.target_branch_name_valid = True
        else:
            self.tab_view.app_root.target_branch_name_valid = False

        if settings_dict["GitCherryPickArguments"] is not None:
            self.cherry_pick.delete(0, 'end')
            self.cherry_pick.insert(0, settings_dict["GitCherryPickArguments"])

        if settings_dict["SearchLimitMonths"] is not None:
            self.search_limit_months.delete(0, 'end')
            self.search_limit_months.insert(0, settings_dict["SearchLimitMonths"])

        if settings_dict["SecondsBetweenGithubRequests"] is not None:
            self.seconds_between_github_requests.delete(0, 'end')
            self.seconds_between_github_requests.insert(0, settings_dict["SecondsBetweenGithubRequests"])

        self.ignore_merge_commits.select() if settings_dict["IgnoreMergeCommits"] else self.ignore_merge_commits.deselect()
        self.group_commits_by_item.select() if settings_dict["GroupCommitsByItem"] else self.group_commits_by_item.deselect()
        self.item_cherry_pick.select() if settings_dict["ItemCherryPick"] else self.item_cherry_pick.deselect()
        self.output_to_excel_file.select() if settings_dict["OutputToExcelFile"] else self.output_to_excel_file.deselect()
        self.output_to_txt_file.select() if settings_dict["OutputToTxtFile"] else self.output_to_txt_file.deselect()
        self.all_commits_cherry_pick_command.select() if settings_dict["AllCommitsCherryPickCommand"] else self.all_commits_cherry_pick_command.deselect()
        self.show_commits_in_date_descending_order.select() if settings_dict["ShowCommitsInDateDescendingOrder"] else self.show_commits_in_date_descending_order.deselect()
        self.strip_characters.select() if settings_dict["StripCharactersFromItemNumbers"] else self.strip_characters.deselect()
        self.use_short_commit_hash.select() if settings_dict["UseShortCommitHash"] else self.use_short_commit_hash.deselect()
        self.use_concurrent_commit_fetching.select() if settings_dict["UseConcurrentCommitFetching"] else self.use_concurrent_commit_fetching.deselect()
        self.radio_var.set(settings_dict["UsePullRequests"])
        self.commit_details_to_show_frame.commit_message_detail.select() if settings_dict["CommitDetailsToShow"]["Message"] else self.commit_details_to_show_frame.commit_message_detail.deselect()
        self.commit_details_to_show_frame.commit_item_number_detail.select() if settings_dict["CommitDetailsToShow"]["ItemNumber"] else self.commit_details_to_show_frame.commit_item_number_detail.deselect()
        self.commit_details_to_show_frame.commit_author_detail.select() if settings_dict["CommitDetailsToShow"]["Author"] else self.commit_details_to_show_frame.commit_author_detail.deselect()
        self.commit_details_to_show_frame.commit_date_detail.select() if settings_dict["CommitDetailsToShow"]["Date"] else self.commit_details_to_show_frame.commit_date_detail.deselect()
        self.commit_details_to_show_frame.commit_url_detail.select() if settings_dict["CommitDetailsToShow"]["CommitUrl"] else self.commit_details_to_show_frame.commit_url_detail.deselect()
        self.commit_details_to_show_frame.commit_pull_request_url_detail.select() if settings_dict["CommitDetailsToShow"]["PullRequestUrl"] else self.commit_details_to_show_frame.commit_pull_request_url_detail.deselect()
        self.commit_details_to_show_frame.commit_sha_detail.select() if settings_dict["CommitDetailsToShow"]["Sha"] else self.commit_details_to_show_frame.commit_sha_detail.deselect()
        self.commit_details_to_show_frame.commit_is_merge_commit_detail.select() if settings_dict["CommitDetailsToShow"]["IsMergeCommit"] else self.commit_details_to_show_frame.commit_is_merge_commit_detail.deselect()
        self.commit_details_to_show_frame.commit_cherry_pick_command_detail.select() if settings_dict["CommitDetailsToShow"]["CherryPickCommand"] else self.commit_details_to_show_frame.commit_cherry_pick_command_detail.deselect()

        self.tab_view.app_root.item_numbers = settings_dict["ItemNumbers"]

        # The UI replaces the OutputToTerminal option, so we leave it alone in the settings.json file but always disable it in the UI
        settings_dict["OutputToTerminal"] = False

        # Temporary
        settings_dict["UseConcurrentCommitFetching"] = True
        settings_dict["SecondsBetweenGithubRequests"] = 1.5

        self.tab_view.app_root.git_the_commits.set_settings_via_dictionary(settings_dict)


    def save_settings_button_clicked(self) -> None:
        self.save_settings()
        self.tab_view.output_frame.results_frame.commits_frame.update_commit_entries()


    def save_settings(self, item_numbers: list[str] = None) -> None:
        self.tab_view.app_root.update_original_settings()

        parsed_search_limit_months = None if not self.search_limit_months.get().isnumeric() else int(self.search_limit_months.get())
        parsed_seconds_between_github_requests = None if not self.seconds_between_github_requests.get().replace('.', '', 1).isnumeric() else float(self.seconds_between_github_requests.get())

        settings_dict = {
            "GitHubToken": None if self.github_token.get() == "" else self.github_token.get(),
            "TargetRepository": None if self.target_repository.get() == "" else self.target_repository.get(),
            "TargetBranch": None if self.target_branch.get() == "" else self.target_branch.get(),
            "StripCharactersFromItemNumbers": True if self.strip_characters.get() else False,
            "ItemNumbers": item_numbers if item_numbers is not None else self.tab_view.app_root.original_settings["ItemNumbers"],
            "CommitDetailsToShow": {
                "Message": True if self.commit_details_to_show_frame.commit_message_detail.get() else False,
                "ItemNumber": True if self.commit_details_to_show_frame.commit_item_number_detail.get() else False,
                "Author": True if self.commit_details_to_show_frame.commit_author_detail.get() else False,
                "Date": True if self.commit_details_to_show_frame.commit_date_detail.get() else False,
                "CommitUrl": True if self.commit_details_to_show_frame.commit_url_detail.get() else False,
                "PullRequestUrl": True if self.commit_details_to_show_frame.commit_pull_request_url_detail.get() else False,
                "Sha": True if self.commit_details_to_show_frame.commit_sha_detail.get() else False,
                "IsMergeCommit": True if self.commit_details_to_show_frame.commit_is_merge_commit_detail.get() else False,
                "CherryPickCommand": True if self.commit_details_to_show_frame.commit_cherry_pick_command_detail.get() else False
            },
            "GroupCommitsByItem": True if self.group_commits_by_item.get() else False,
            "ItemCherryPick": True if self.item_cherry_pick.get() else False,
            "ShowCommitsInDateDescendingOrder": True if self.show_commits_in_date_descending_order.get() else False,
            "UseCommitHistory": False if self.radio_var.get() else True,
            "UsePullRequests": True if self.radio_var.get() else False,
            "OutputToTerminal": self.tab_view.app_root.original_settings["OutputToTerminal"],
            "OutputToTxtFile": True if self.output_to_txt_file.get() else False,
            "OutputToExcelFile": True if self.output_to_excel_file.get() else False,
            "AllCommitsCherryPickCommand": True if self.all_commits_cherry_pick_command.get() else False,
            "IgnoreMergeCommits": True if self.ignore_merge_commits.get() else False,
            "UseShortCommitHash": True if self.use_short_commit_hash.get() else False,
            "GitCherryPickArguments": None if self.cherry_pick.get() == "" else self.cherry_pick.get(),
            "SearchLimitMonths": None if self.search_limit_months.get() == "" else parsed_search_limit_months,
            "UseConcurrentCommitFetching": True if self.use_concurrent_commit_fetching.get() else False,
            "SecondsBetweenGithubRequests": None if self.seconds_between_github_requests.get() == "" else parsed_seconds_between_github_requests
        }

        with open(self.tab_view.app_root.settings_filename, 'w') as settings_file:
            json.dump(settings_dict, settings_file, indent=4)

        settings_dict["OutputToTerminal"] = False

        self.tab_view.app_root.git_the_commits.set_settings_via_dictionary(settings_dict)


    def create_entry_setting_input(self, label_text: str, row: int, column: int, columnspan: int, sticky: str = "we", 
                                   hide_text: bool = False, placeholder_text: str = None, value_type: str = None, 
                                   bind_method = None) -> tuple[customtkinter.CTkLabel, customtkinter.CTkEntry]:
        label = customtkinter.CTkLabel(self, text=label_text)
        label.grid(row=row, column=column, sticky='e', padx=5)

        input = None
        match value_type:
            case self.DIGIT:
                input = customtkinter.CTkEntry(self, width=50, show=('*' if hide_text else None), 
                                               placeholder_text=placeholder_text, validate="key", 
                                               validatecommand=(self.register(self.validate_only_digit), '%P'))
            case self.FLOAT:
                input = customtkinter.CTkEntry(self, width=50, show=('*' if hide_text else None), 
                                               placeholder_text=placeholder_text, validate="key", 
                                               validatecommand=(self.register(self.validate_only_float), '%P'))
            case _:
                input = customtkinter.CTkEntry(self, width=50, show=('*' if hide_text else None), placeholder_text=placeholder_text)
        input.grid(row=row, column=column + 1, sticky=sticky, pady=5, padx=3, columnspan=columnspan)

        if bind_method is not None:
            input.bind("<KeyRelease>", bind_method)

        return label, input
    

    def create_switch_setting_input(self, label_text: str, row: int, column: int) -> tuple[customtkinter.CTkLabel, customtkinter.CTkSwitch]:
        label = customtkinter.CTkLabel(self, text=label_text)
        label.grid(row=row, column=column, sticky='e', padx=5)
        input = customtkinter.CTkSwitch(self, text=None)
        input.grid(row=row, column=column + 1, sticky='w', pady=5, padx=3)

        return label, input
    

    def validate_only_digit(self, text: str) -> None:
        return text.isdigit() or text == ""
    

    def validate_only_float(self, text: str) -> None:
        # Only allow one decimal point
        return text.replace('.', '', 1).isdigit() or text.replace('.', '', 1) == ""
    

    def handle_github_token_entry(self) -> None:
        return self.handle_required_entry(self.github_token, SettingsFrame.GITHUB_TOKEN)
    

    def handle_target_repository_entry(self) -> None:
        return self.handle_required_entry(self.target_repository, SettingsFrame.TARGET_REPOSITORY)
    

    def handle_target_branch_entry(self) -> None:
        return self.handle_required_entry(self.target_branch, SettingsFrame.TARGET_BRANCH)
    

    def handle_required_entry(self, entry: customtkinter.CTkEntry, field_type: int) -> None:
        app_root = self.tab_view.app_root

        # entry is valid if it is not empty after the event. 
        # Entry.get() is the value before the event. 
        # Entry should also be valid if the user types an alphanumeric character
        is_valid = not (entry is None or entry.get() == "")

        if is_valid:
            entry.configure(border_color = app_root.DEFAULT_BORDER_COLOR)
        else:
            entry.configure(border_color = app_root.ERROR_BORDER_COLOR)

        match field_type:
            case self.GITHUB_TOKEN:
                app_root.update_github_token_validity(is_valid)
            case self.TARGET_REPOSITORY:
                app_root.update_repository_name_validity(is_valid)
            case self.TARGET_BRANCH:
                app_root.update_target_branch_name_validity(is_valid)


class CommitDetailsToShowSubFrame(customtkinter.CTkFrame):
    def __init__(self, settings_frame: SettingsFrame, **kwargs) -> None:
        super().__init__(settings_frame, **kwargs)
        self.grid_columnconfigure((0, 1), weight=1)

        self.commit_details_to_show_label = customtkinter.CTkLabel(
            self, text="Commit Details To Show", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.commit_details_to_show_label.grid(row=0, column=0, columnspan=2, sticky='we', pady=5)

        self.commit_message_detail_label, self.commit_message_detail = self.create_switch_setting_input("Message:", 1)
        self.commit_item_number_detail_label, self.commit_item_number_detail = self.create_switch_setting_input("Item Number:", 2)
        self.commit_author_detail_label, self.commit_author_detail = self.create_switch_setting_input("Author:", 3)
        self.commit_date_detail_label, self.commit_date_detail = self.create_switch_setting_input("Date:", 4)
        self.commit_url_detail_label, self.commit_url_detail = self.create_switch_setting_input("Commit URL:", 5)
        self.commit_pull_request_url_detail_label, self.commit_pull_request_url_detail = self.create_switch_setting_input("Pull Request URL:", 6)
        self.commit_sha_detail_label, self.commit_sha_detail = self.create_switch_setting_input("SHA:", 7)
        self.commit_is_merge_commit_detail_label, self.commit_is_merge_commit_detail = self.create_switch_setting_input("Is Merge Commit:", 8)
        self.commit_cherry_pick_command_detail_label, self.commit_cherry_pick_command_detail = self.create_switch_setting_input("Cherry Pick Command:", 9)


    def create_switch_setting_input(self, label_text: str, row: int) -> tuple[customtkinter.CTkLabel, customtkinter.CTkSwitch]:
        label = customtkinter.CTkLabel(self, text=label_text)
        label.grid(row=row, column=0, sticky='e', padx=5)
        input = customtkinter.CTkSwitch(self, text=None)
        input.grid(row=row, column=1, sticky='w', pady=5, padx=3)

        return label, input


if __name__ == '__main__':
    gui = AppRoot("settings.json")
    gui.mainloop()
