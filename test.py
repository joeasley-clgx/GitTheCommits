from CommitDetailVisibility import CommitDetailVisibility
from CommitInfo import CommitInfo
from github import Auth, BadCredentialsException, GithubException
from github.GitCommit import GitCommit
from github.Requester import Requester
from GitTheCommits import GitTheCommits
from dataclasses import dataclass
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from random import randint
from unittest.mock import Mock, patch, call, MagicMock, mock_open

import unittest
import uuid
import json


class TestGroupRelevantCommitInfo(unittest.TestCase):
    def test_returns_expected_data(self):
        # Arrange
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)

        # Act
        result = target.group_relevant_commit_info(git_commit, "1234", pr_url="www.google.pullrequest.com")

        # Assert
        self.assertEqual("This is a test", result.message)
        self.assertEqual("Uni <uni@test.py>", result.author)
        self.assertEqual(datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc), result.date)
        self.assertEqual("0987654321098765432109876543210987654321", result.sha)
        self.assertEqual("www.google2.com", result.commit_url)
        self.assertEqual("www.google.pullrequest.com", result.pr_url)
        self.assertEqual("1234", result.item_number)


    def test_returns_shortens_commit_hash(self):
        # Arrange
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.use_short_commit_hash = True

        # Act
        result = target.group_relevant_commit_info(git_commit, "1234", pr_url="www.google.pullrequest.com")

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual("This is a test", result.message)
        self.assertEqual("0987654321098765432109876543210987654321"[:target.short_commit_hash_length], result.sha)


    def test_returns_multiple_pr_urls(self):
        # Arrange
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.use_short_commit_hash = True

        # Act
        result = target.group_relevant_commit_info(git_commit, "1234", pr_urls=("www.google.pullrequest.com/1", "www.google.pullrequest.com/2"))

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual("This is a test", result.message)
        self.assertEqual("www.google.pullrequest.com/1, www.google.pullrequest.com/2", result.pr_url)


class TestSaveCommitInfo(unittest.TestCase):
    def test_saves_expected_data(self):
        # Arrange
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)

        # Act
        target.save_commit_info(git_commit, "1234", pr_url="www.google.pullrequest.com")

        # Assert
        self.assertEqual(1, len(target.commit_list))
        saved_commit = target.commit_list[0]
        self.assertEqual("This is a test", saved_commit.message)
        self.assertEqual("Uni <uni@test.py>", saved_commit.author)
        self.assertEqual(datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc), saved_commit.date)
        self.assertEqual("0987654321098765432109876543210987654321", saved_commit.sha)
        self.assertEqual("www.google2.com", saved_commit.commit_url)
        self.assertEqual("www.google.pullrequest.com", saved_commit.pr_url)
        self.assertEqual("1234", saved_commit.item_number)


    def test_with_shortened_sha(self):
        # Arrange
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.use_short_commit_hash = True
        target.short_commit_hash_length = 8 # Manually set here to future-proof this test

        # Act
        target.save_commit_info(git_commit, "1234", pr_url="www.google.pullrequest.com")

        # Assert
        self.assertEqual(1, len(target.commit_list))
        self.assertEqual("09876543", target.commit_list[0].sha)


    def test_does_not_save_commit_if_sha_already_saved(self):
        # Arrange
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)

        saved_commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "1234",
            False
        )

        target.commit_list = [saved_commit]

        # Act
        target.save_commit_info(git_commit, "1234", pr_url="www.google.pullrequest.com")

        # Assert
        self.assertEqual(1, len(target.commit_list))


    def test_with_merge_commit_and_ignore_merge_commits_off(self):
        # Arrange
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                2, 
                True
            )
        )

        target = GitTheCommits(False)
        target.ignore_merge_commits = False

        # Act
        target.save_commit_info(git_commit, "1234", pr_url="www.google.pullrequest.com")

        # Assert
        self.assertEqual(1, len(target.commit_list))
        self.assertEqual("0987654321098765432109876543210987654321", target.commit_list[0].sha)


    def test_with_merge_commit_and_ignore_merge_commits_on(self):
        # Arrange
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                2, 
                True
            )
        )

        target = GitTheCommits(False)
        target.ignore_merge_commits = True

        # Act
        target.save_commit_info(git_commit, "1234", pr_url="www.google.pullrequest.com")

        # Assert
        self.assertEqual(0, len(target.commit_list))


class TestStripNonDigitCharactersFromListOfStrings(unittest.TestCase):
    def test_only_digits(self):
        # Arrange
        target = GitTheCommits(False)
        
        # Act
        output = target.strip_non_digit_characters_from_list_of_strings(["123", "456", "7890"])
        
        # Assert
        self.assertEqual(["123", "456", "7890"], output)


    def test_only_non_digits(self):
        # Arrange
        target = GitTheCommits(False)
        
        # Act
        output = target.strip_non_digit_characters_from_list_of_strings(["abc", "def", "ghij"])
        
        # Assert
        self.assertEqual(["", "", ""], output)


    def test_mixed_valid_and_invalid_strings(self):
        # Arrange
        target = GitTheCommits(False)
        
        # Act
        output = target.strip_non_digit_characters_from_list_of_strings(["a1b2", "-c3d4", "5"])
        
        # Assert
        self.assertEqual(["12", "34", "5"], output)


class TestManuallyEnterItemNumbers(unittest.TestCase):
    @patch('builtins.print')
    @patch('builtins.input', side_effect=['y', '123,456,789'])
    def test_answers_yes(self, mock_input, mock_print):
        # Arrange
        target = GitTheCommits(False)
        
        # Act
        output = target.manually_enter_item_numbers()
        
        # Assert
        self.assertEqual(['123', '456', '789'], output)


    @patch('builtins.print')
    @patch('builtins.input', side_effect=['y', 'ITEM-123,ITEM-456,ITEM-789'])
    def test_answers_yes_with_characters(self, mock_input, mock_print):
        # Arrange
        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = False
        
        # Act
        output = target.manually_enter_item_numbers()
        
        # Assert
        self.assertEqual(['ITEM-123', 'ITEM-456', 'ITEM-789'], output)
    

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['y', 'ITEM-123,ITEM-456,ITEM-789'])
    def test_answers_yes_and_strips_characters(self, mock_input, mock_print):
        # Arrange
        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        
        # Act
        output = target.manually_enter_item_numbers()
        
        # Assert
        self.assertEqual(['123', '456', '789'], output)


    @patch('builtins.print')
    @patch('builtins.input', side_effect=['n', ''])
    def test_answers_no(self, mock_input, mock_print):
        # Arrange
        target = GitTheCommits(False)
        
        # Act
        with self.assertRaises(SystemExit):
            target.manually_enter_item_numbers()


class TestGenerateCherryPickCommand(unittest.TestCase):
    def test_returns_expected_data_with_one_commit(self):
        target = GitTheCommits(False)
        target.cherry_pick_command = "git test"
        
        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        result = target.generate_cherry_pick_command([commit])

        self.assertEqual(result, "\ngit test 0987654321098765432109876543210987654321")

        
    def test_returns_expected_data_with_multiple_commits(self):
        target = GitTheCommits(False)
        target.cherry_pick_command = "git test"
        
        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        result = target.generate_cherry_pick_command([commit_1, commit_2])

        self.assertEqual(result, "\ngit test 0987654321098765432109876543210987654321 1234567890123456789012345678901234567890")


    def test_sorts_commits(self):
        target = GitTheCommits(False)
        target.cherry_pick_command = "git test"
        
        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 11, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        result = target.generate_cherry_pick_command([commit_1, commit_2])

        self.assertEqual(result, "\ngit test 1234567890123456789012345678901234567890 0987654321098765432109876543210987654321")


class TestStringifyCommits(unittest.TestCase):
    def test_shows_all_details_for_single_commit(self):
        # Arrange
        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.cherry_pick_command = "git cherry-pick"
        target.commit_detail_visibilty = CommitDetailVisibility(
            message=True,
            item_number=True,
            author=True,
            date=True,
            commit_url=True,
            pull_request_url=True,
            sha=True,
            is_merge_commit=True,
            show_cherry_pick_command=True
        )

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\n- This is a test" + 
                         "\nItem Number: 1234" + 
                         "\nAuthor: Uni <uni@test.py>" + 
                         "\nDate: 2024-01-12 08:30:02+00:00" + 
                         "\nCommit URL: www.google1.com" + 
                         "\nPull Request URL: www.google1.pullrequest.com" + 
                         "\nSHA: 0987654321098765432109876543210987654321" + 
                         "\nIs Merge Commit: False" + 
                         "\nCherry-Pick Command: git cherry-pick 0987654321098765432109876543210987654321\n", 
                         result)

        
    def test_shows_all_details_for_multiple_commits(self):
        # Arrange
        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.cherry_pick_command = "git cherry-pick"
        target.commit_detail_visibilty = CommitDetailVisibility(
            message=True,
            item_number=True,
            author=True,
            date=True,
            commit_url=True,
            pull_request_url=True,
            sha=True,
            is_merge_commit=True,
            show_cherry_pick_command=True
        )

        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        # Act
        result = target.stringify_commits([commit_1, commit_2])

        # Assert
        self.assertEqual("\n- This is a test" + 
                         "\nItem Number: 1234" + 
                         "\nAuthor: Uni <uni@test.py>" + 
                         "\nDate: 2024-01-12 08:30:02+00:00" + 
                         "\nCommit URL: www.google1.com" + 
                         "\nPull Request URL: www.google1.pullrequest.com" + 
                         "\nSHA: 0987654321098765432109876543210987654321" + 
                         "\nIs Merge Commit: False" + 
                         "\nCherry-Pick Command: git cherry-pick 0987654321098765432109876543210987654321" + 
                         "\n" +
                         "\n- This is also a test" + 
                         "\nItem Number: 4321" + 
                         "\nAuthor: Uni Two <unitwo@test.py>" + 
                         "\nDate: 2024-01-13 08:30:02+00:00" + 
                         "\nCommit URL: www.google2.com" + 
                         "\nPull Request URL: www.google2.pullrequest.com" + 
                         "\nSHA: 1234567890123456789012345678901234567890" + 
                         "\nIs Merge Commit: True" + 
                         "\nCherry-Pick Command: git cherry-pick 1234567890123456789012345678901234567890\n", 
                         result)
        

    def test_shows_only_message_for_single_commit(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(message=True)

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\n- This is a test\n", result)

        
    def test_shows_only_message_for_multiple_commits(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(message=True)

        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        # Act
        result = target.stringify_commits([commit_1, commit_2])

        # Assert
        self.assertEqual("\n- This is a test" + 
                         "\n" +
                         "\n- This is also a test\n", 
                         result)
        
        
    def test_message_does_not_show_when_off(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(message=False)
        
        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        output = target.stringify_commits([commit])
        
        # Assert
        self.assertNotIn("\n- This is a test", output)


    def test_shows_only_item_number_for_single_commit(self):
        # Arrange
        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.commit_detail_visibilty = CommitDetailVisibility(item_number=True)

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\nItem Number: 1234\n", result)

        
    def test_shows_only_item_number_for_multiple_commits(self):
        # Arrange
        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.commit_detail_visibilty = CommitDetailVisibility(item_number=True)

        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        # Act
        result = target.stringify_commits([commit_1, commit_2])

        # Assert
        self.assertEqual("\nItem Number: 1234" + 
                         "\n" +
                         "\nItem Number: 4321\n", 
                         result)
        

    def test_item_number_off(self):
        # Arrange
        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.commit_detail_visibilty = CommitDetailVisibility(item_number=False)
        
        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        output = target.stringify_commits([commit])
        
        # Assert
        self.assertNotIn("\nItem Number: 1234", output)


    def test_item_number_with_characters(self):
        # Arrange
        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = False
        target.commit_detail_visibilty = CommitDetailVisibility(item_number=True)

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "ITEM-1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\nItem: ITEM-1234\n", result)


    def test_shows_only_author_for_single_commit(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(author=True)

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\nAuthor: Uni <uni@test.py>\n", result)

        
    def test_shows_only_author_for_multiple_commits(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(author=True)

        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        # Act
        result = target.stringify_commits([commit_1, commit_2])

        # Assert
        self.assertEqual("\nAuthor: Uni <uni@test.py>" + 
                         "\n" +
                         "\nAuthor: Uni Two <unitwo@test.py>\n", 
                         result)
        

    def test_author_off(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(author=False)
        
        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        output = target.stringify_commits([commit])
        
        # Assert
        self.assertNotIn("\nAuthor: Uni <uni@test.py>", output)


    def test_shows_only_date_for_single_commit(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(date=True)

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\nDate: 2024-01-12 08:30:02+00:00\n", result)

        
    def test_shows_only_date_for_multiple_commits(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(date=True)

        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        # Act
        result = target.stringify_commits([commit_1, commit_2])

        # Assert
        self.assertEqual("\nDate: 2024-01-12 08:30:02+00:00" + 
                         "\n" +
                         "\nDate: 2024-01-13 08:30:02+00:00\n", 
                         result)


    def test_date_off(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(date=False)
        
        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        output = target.stringify_commits([commit])
        
        # Assert
        self.assertNotIn(f"\nDate: {datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc)}", output)


    def test_shows_only_commit_url_for_single_commit(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(commit_url=True)

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\nCommit URL: www.google1.com\n", result)

        
    def test_shows_only_commit_url_for_multiple_commits(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(commit_url=True)

        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        # Act
        result = target.stringify_commits([commit_1, commit_2])

        # Assert
        self.assertEqual("\nCommit URL: www.google1.com" + 
                         "\n" +
                         "\nCommit URL: www.google2.com\n", 
                         result)


    def test_commit_url_off(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(commit_url=False)
        
        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        output = target.stringify_commits([commit])
        
        # Assert
        self.assertNotIn("\nCommit URL: www.google1.com", output)


    def test_shows_only_pull_request_url_for_single_commit(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(pull_request_url=True)

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\nPull Request URL: www.google1.pullrequest.com\n", result)

        
    def test_shows_only_pull_request_url_for_multiple_commits(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(pull_request_url=True)

        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        # Act
        result = target.stringify_commits([commit_1, commit_2])

        # Assert
        self.assertEqual("\nPull Request URL: www.google1.pullrequest.com" + 
                         "\n" +
                         "\nPull Request URL: www.google2.pullrequest.com\n", 
                         result)


    def test_pull_request_url_off(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(pull_request_url=False)
        
        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        output = target.stringify_commits([commit])
        
        # Assert
        self.assertNotIn("\nPull Request URL: www.google1.pullrequest.com", output)


    def test_shows_only_sha_for_single_commit(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(sha=True)

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\nSHA: 0987654321098765432109876543210987654321\n", result)

        
    def test_shows_only_sha_for_multiple_commits(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(sha=True)

        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        # Act
        result = target.stringify_commits([commit_1, commit_2])

        # Assert
        self.assertEqual("\nSHA: 0987654321098765432109876543210987654321" + 
                         "\n" +
                         "\nSHA: 1234567890123456789012345678901234567890\n", 
                         result)


    def test_sha_off(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(sha=False)
        
        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        output = target.stringify_commits([commit])
        
        # Assert
        self.assertNotIn("\nSHA: 0987654321098765432109876543210987654321", output)


    def test_shows_only_is_merge_commit_for_single_commit(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(is_merge_commit=True)

        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        result = target.stringify_commits([commit])

        # Assert
        self.assertEqual("\nIs Merge Commit: False\n", result)

        
    def test_shows_only_is_merge_commit_for_multiple_commits(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(is_merge_commit=True)

        commit_1 = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        commit_2 = CommitInfo(
            "This is also a test",
            "Uni Two <unitwo@test.py>",
            datetime(2024, 1, 13, 8, 30, 2).replace(tzinfo=timezone.utc),
            "1234567890123456789012345678901234567890",
            "www.google2.com",
            "www.google2.pullrequest.com",
            "4321",
            True
        )

        # Act
        result = target.stringify_commits([commit_1, commit_2])

        # Assert
        self.assertEqual("\nIs Merge Commit: False" + 
                         "\n" +
                         "\nIs Merge Commit: True\n", 
                         result)


    def test_is_merge_commit_off(self):
        # Arrange
        target = GitTheCommits(False)
        target.commit_detail_visibilty = CommitDetailVisibility(is_merge_commit=False)
        
        commit = CommitInfo(
            "This is a test",
            "Uni <uni@test.py>",
            datetime(2024, 1, 12, 8, 30, 2).replace(tzinfo=timezone.utc),
            "0987654321098765432109876543210987654321",
            "www.google1.com",
            "www.google1.pullrequest.com",
            "1234",
            False
        )

        # Act
        output = target.stringify_commits([commit])
        
        # Assert
        self.assertNotIn("\nIs Merge Commit: False", output)


class TestSetSettingsViaDictionary(unittest.TestCase):
    def test_sets_all_settings_correctly(self):
        # Arrange
        settings_dictionary = {
            "GitHubToken": "DefinitelyValidToken",
            "TargetRepository": "joeasley-clgx/GitTheCommits",
            "TargetBranch": "test-branch",
            "StripCharactersFromItemNumbers": True,
            "ItemNumbers": [1234],
            "CommitDetailsToShow": {
                "Message": True,
                "ItemNumber": True,
                "Author": True,
                "Date": True,
                "CommitUrl": True,
                "PullRequestUrl": True,
                "Sha": True,
                "IsMergeCommit": True,
                "CherryPickCommand": True
            },
            "GroupCommitsByItem": True,
            "GroupCommitCherryPick": True,
            "ShowCommitsInDateDescendingOrder": True,
            "UseCommitHistory": True,
            "UsePullRequests": True,
            "OutputToTerminal": True,
            "OutputToTxtFile": True,
            "OutputToExcelFile": True,
            "ShowCherryPickCommand": True,
            "IgnoreMergeCommits": True,
            "UseShortCommitHash": True,
            "GitCherryPickArguments": "-test",
            "SearchLimitMonths": 1
        }

        target = GitTheCommits(False)

        # Act
        target.set_settings_via_dictionary(settings_dictionary)

        # Assert
        self.assertEqual(target.settings_are_set, True)
        # all settings default to None
        self.assertEqual(target.github_token, "DefinitelyValidToken")
        self.assertEqual(target.repository_name, "joeasley-clgx/GitTheCommits")
        self.assertEqual(target.target_branch_name, "test-branch")
        self.assertEqual(target.item_numbers, ["1234"])

        self.assertIsNotNone(target.commit_detail_visibilty)
        self.assertEqual(target.commit_detail_visibilty.message, True)
        self.assertEqual(target.commit_detail_visibilty.item_number, True)
        self.assertEqual(target.commit_detail_visibilty.author, True)
        self.assertEqual(target.commit_detail_visibilty.date, True)
        self.assertEqual(target.commit_detail_visibilty.commit_url, True)
        self.assertEqual(target.commit_detail_visibilty.pull_request_url, True)
        self.assertEqual(target.commit_detail_visibilty.sha, True)
        self.assertEqual(target.commit_detail_visibilty.is_merge_commit, True)
        self.assertEqual(target.commit_detail_visibilty.show_cherry_pick_command, True)

        self.assertEqual(target.group_commits_by_item, True)
        self.assertEqual(target.order_commits_by_date_descend, True)
        self.assertEqual(target.use_commit_history, True)
        self.assertEqual(target.use_pull_requests, True)
        self.assertEqual(target.output_to_terminal, True)
        self.assertEqual(target.output_to_txt, True)
        self.assertEqual(target.output_to_excel, True)
        self.assertEqual(target.show_cherry_pick_command, True)
        self.assertEqual(target.ignore_merge_commits, True)
        self.assertEqual(target.use_short_commit_hash, True)
        self.assertEqual(target.cherry_pick_command, "git cherry-pick -test")
        self.assertEqual(target.search_date_limit.strftime("%Y%m%d%H%M%S"), (datetime.today() - relativedelta(months=1)).replace(tzinfo=timezone.utc).strftime("%Y%m%d%H%M%S"))

    
    def test_strips_non_digit_characters_from_item_number(self):
        # Arrange
        settings_dictionary = {
            "GitHubToken": "DefinitelyValidToken",
            "TargetRepository": "joeasley-clgx/GitTheCommits",
            "TargetBranch": "test-branch",
            "StripCharactersFromItemNumbers": True,
            "ItemNumbers": ["Test-1234"],
            "CommitDetailsToShow": {
                "Message": True,
                "ItemNumber": True,
                "Author": True,
                "Date": True,
                "CommitUrl": True,
                "PullRequestUrl": True,
                "Sha": True,
                "IsMergeCommit": True,
                "CherryPickCommand": True
            },
            "GroupCommitsByItem": True,
            "GroupCommitCherryPick": True,
            "ShowCommitsInDateDescendingOrder": True,
            "UseCommitHistory": True,
            "UsePullRequests": True,
            "OutputToTerminal": True,
            "OutputToTxtFile": True,
            "OutputToExcelFile": True,
            "ShowCherryPickCommand": True,
            "IgnoreMergeCommits": True,
            "UseShortCommitHash": True,
            "GitCherryPickArguments": "-test",
            "SearchLimitMonths": 1
        }

        target = GitTheCommits(False)

        # Act
        target.set_settings_via_dictionary(settings_dictionary)

        # Assert
        self.assertEqual(target.item_numbers, ["1234"])
    
    
    def test_keeps_characters_in_item_number(self):
        # Arrange
        settings_dictionary = {
            "GitHubToken": "DefinitelyValidToken",
            "TargetRepository": "joeasley-clgx/GitTheCommits",
            "TargetBranch": "test-branch",
            "StripCharactersFromItemNumbers": False,
            "ItemNumbers": ["Test-1234"],
            "CommitDetailsToShow": {
                "Message": True,
                "ItemNumber": True,
                "Author": True,
                "Date": True,
                "CommitUrl": True,
                "PullRequestUrl": True,
                "Sha": True,
                "IsMergeCommit": True,
                "CherryPickCommand": True
            },
            "GroupCommitsByItem": True,
            "GroupCommitCherryPick": True,
            "ShowCommitsInDateDescendingOrder": True,
            "UseCommitHistory": True,
            "UsePullRequests": True,
            "OutputToTerminal": True,
            "OutputToTxtFile": True,
            "OutputToExcelFile": True,
            "ShowCherryPickCommand": True,
            "IgnoreMergeCommits": True,
            "UseShortCommitHash": True,
            "GitCherryPickArguments": "-test",
            "SearchLimitMonths": 1
        }

        target = GitTheCommits(False)

        # Act
        target.set_settings_via_dictionary(settings_dictionary)

        # Assert
        self.assertEqual(target.item_numbers, ["Test-1234"])

    
    def test_converts_item_numbers_from_int_to_string(self):
        # Arrange
        settings_dictionary = {
            "GitHubToken": "DefinitelyValidToken",
            "TargetRepository": "joeasley-clgx/GitTheCommits",
            "TargetBranch": "test-branch",
            "StripCharactersFromItemNumbers": True,
            "ItemNumbers": [1234],
            "CommitDetailsToShow": {
                "Message": True,
                "ItemNumber": True,
                "Author": True,
                "Date": True,
                "CommitUrl": True,
                "PullRequestUrl": True,
                "Sha": True,
                "IsMergeCommit": True,
                "CherryPickCommand": True
            },
            "GroupCommitsByItem": True,
            "GroupCommitCherryPick": True,
            "ShowCommitsInDateDescendingOrder": True,
            "UseCommitHistory": True,
            "UsePullRequests": True,
            "OutputToTerminal": True,
            "OutputToTxtFile": True,
            "OutputToExcelFile": True,
            "ShowCherryPickCommand": True,
            "IgnoreMergeCommits": True,
            "UseShortCommitHash": True,
            "GitCherryPickArguments": "-test",
            "SearchLimitMonths": 1
        }

        target = GitTheCommits(False)

        # Act
        target.set_settings_via_dictionary(settings_dictionary)

        # Assert
        self.assertEqual(target.item_numbers, ["1234"])

    
    def test_stores_multiple_item_numbers(self):
        # Arrange
        settings_dictionary = {
            "GitHubToken": "DefinitelyValidToken",
            "TargetRepository": "joeasley-clgx/GitTheCommits",
            "TargetBranch": "test-branch",
            "StripCharactersFromItemNumbers": True,
            "ItemNumbers": [1, "2"],
            "CommitDetailsToShow": {
                "Message": True,
                "ItemNumber": True,
                "Author": True,
                "Date": True,
                "CommitUrl": True,
                "PullRequestUrl": True,
                "Sha": True,
                "IsMergeCommit": True,
                "CherryPickCommand": True
            },
            "GroupCommitsByItem": True,
            "GroupCommitCherryPick": True,
            "ShowCommitsInDateDescendingOrder": True,
            "UseCommitHistory": True,
            "UsePullRequests": True,
            "OutputToTerminal": True,
            "OutputToTxtFile": True,
            "OutputToExcelFile": True,
            "ShowCherryPickCommand": True,
            "IgnoreMergeCommits": True,
            "UseShortCommitHash": True,
            "GitCherryPickArguments": "-test",
            "SearchLimitMonths": 1
        }

        target = GitTheCommits(False)

        # Act
        target.set_settings_via_dictionary(settings_dictionary)

        # Assert
        self.assertEqual(target.item_numbers, ["1", "2"])


    def test_handles_no_cherrypick_arguments(self):
        # Arrange
        settings_dictionary = {
            "GitHubToken": "DefinitelyValidToken",
            "TargetRepository": "joeasley-clgx/GitTheCommits",
            "TargetBranch": "test-branch",
            "StripCharactersFromItemNumbers": True,
            "ItemNumbers": [1, "2"],
            "CommitDetailsToShow": {
                "Message": True,
                "ItemNumber": True,
                "Author": True,
                "Date": True,
                "CommitUrl": True,
                "PullRequestUrl": True,
                "Sha": True,
                "IsMergeCommit": True,
                "CherryPickCommand": True
            },
            "GroupCommitsByItem": True,
            "GroupCommitCherryPick": True,
            "ShowCommitsInDateDescendingOrder": True,
            "UseCommitHistory": True,
            "UsePullRequests": True,
            "OutputToTerminal": True,
            "OutputToTxtFile": True,
            "OutputToExcelFile": True,
            "ShowCherryPickCommand": True,
            "IgnoreMergeCommits": True,
            "UseShortCommitHash": True,
            "GitCherryPickArguments": None,
            "SearchLimitMonths": 1
        }

        target = GitTheCommits(False)

        # Act
        target.set_settings_via_dictionary(settings_dictionary)

        # Assert
        self.assertEqual(target.cherry_pick_command, "git cherry-pick")


    def test_include_merge_commits(self):
        # Arrange
        settings_dictionary = {
            "GitHubToken": "DefinitelyValidToken",
            "TargetRepository": "joeasley-clgx/GitTheCommits",
            "TargetBranch": "test-branch",
            "StripCharactersFromItemNumbers": True,
            "ItemNumbers": [1, "2"],
            "CommitDetailsToShow": {
                "Message": True,
                "ItemNumber": True,
                "Author": True,
                "Date": True,
                "CommitUrl": True,
                "PullRequestUrl": True,
                "Sha": True,
                "IsMergeCommit": True,
                "CherryPickCommand": True
            },
            "GroupCommitsByItem": True,
            "GroupCommitCherryPick": True,
            "ShowCommitsInDateDescendingOrder": True,
            "UseCommitHistory": True,
            "UsePullRequests": True,
            "OutputToTerminal": True,
            "OutputToTxtFile": True,
            "OutputToExcelFile": True,
            "ShowCherryPickCommand": True,
            "IgnoreMergeCommits": False,
            "UseShortCommitHash": True,
            "GitCherryPickArguments": "-test",
            "SearchLimitMonths": 1
        }

        target = GitTheCommits(False)

        # Act
        target.set_settings_via_dictionary(settings_dictionary)

        # Assert
        self.assertEqual(target.cherry_pick_command, "git cherry-pick -test -m 1")


class TestSetSettings(unittest.TestCase):
    def test_throws_exception_for_non_json_file(self):
        # Arrange
        target = GitTheCommits(False)

        # Act
        with self.assertRaises(Exception) as context:
            target.set_settings("settings.txt")
        
        # Assert
        self.assertTrue("The file containing your settings must be a '.json' file" in str(context.exception))


    @patch('builtins.open', new_callable=mock_open, read_data='{"key": "value"}')
    @patch('json.load')
    @patch('GitTheCommits.GitTheCommits.set_settings_via_dictionary')
    def test_valid_file(self, mock_set_settings_via_dictionary, mock_json_load, mock_open):
        # Arrange
        target = GitTheCommits(False)
        mock_json_load.return_value = {"key": "value"}
        
        # Act
        target.set_settings("settings.json")
        
        # Assert
        mock_set_settings_via_dictionary.assert_called_once_with({"key": "value"})

    
    @patch('builtins.open', new_callable=mock_open, read_data='{"key": "value",}')
    @patch('json.load')
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_invalid_json(self, mock_print, mock_input, mock_json_load, mock_open):
        # Arrange
        target = GitTheCommits(False)
        mock_json_load.side_effect = json.JSONDecodeError('Invalid JSON', doc='', pos=0)

        # Act
        with self.assertRaises(SystemExit):
            target.set_settings("settings.json")

        # Assert
        mock_print.assert_called_once_with("Your settings.json file has a syntax error on line 1. Please fix it and try again.")


class TestGenerateExcelFile(unittest.TestCase):
    @patch('xlsxwriter.Workbook')
    @patch('builtins.print')
    @patch('os.path.isfile', return_value=False)
    @patch('os.remove')
    @patch('builtins.input')
    def test_no_file(self, mock_input, mock_remove, mock_isfile, mock_print, mock_workbook):
        # Arrange
        mock_workbook.return_value.__enter__.return_value = MagicMock()

        target = GitTheCommits(False)
        commits = [
            CommitInfo("message", "author", "2022-01-01", "sha1", "commit_url", "pr_url", "item_number", "is_merge"),
            CommitInfo("message", "author", "2022-01-02", "sha2", "commit_url", "pr_url", "item_number", "is_merge")
        ]
        
        # Act
        target.generate_excel_file(commits)

        # Assert
        mock_isfile.assert_called_once_with("output.xlsx")
        mock_remove.assert_not_called()
        mock_input.assert_not_called()


    @patch('xlsxwriter.Workbook')
    @patch('builtins.exit', side_effect=SystemExit)
    @patch('builtins.print')
    @patch('os.path.isfile', return_value=True)
    @patch('os.remove', side_effect=[IOError, None])
    @patch('builtins.input', return_value='')
    def test_file_exists_close(self, mock_input, mock_remove, mock_isfile, mock_print, mock_exit, mock_workbook):
        # Arrange
        mock_workbook.return_value.__enter__.return_value = MagicMock()

        target = GitTheCommits(False)
        commits = [
            CommitInfo("message", "author", "2022-01-01", "sha1", "commit_url", "pr_url", "item_number", "is_merge"),
            CommitInfo("message", "author", "2022-01-02", "sha2", "commit_url", "pr_url", "item_number", "is_merge")
        ]
        
        # Act
        target.generate_excel_file(commits)

        # Assert
        mock_isfile.assert_called_once_with("output.xlsx")
        mock_remove.assert_has_calls([call("output.xlsx"), call("output.xlsx")])
        mock_input.assert_called_once_with()


    @patch('xlsxwriter.Workbook')
    @patch('builtins.print')
    @patch('os.path.isfile', return_value=True)
    @patch('os.remove', side_effect=[IOError, None])
    @patch('builtins.input', side_effect=['', ''])
    def test_file_exists_dont_close(self, mock_input, mock_remove, mock_isfile, mock_print, mock_workbook):
        # Arrange
        mock_workbook.return_value.__enter__.return_value = MagicMock()

        target = GitTheCommits(False)
        commits = [
            CommitInfo("message", "author", "2022-01-01", "sha1", "commit_url", "pr_url", "item_number", "is_merge"),
            CommitInfo("message", "author", "2022-01-02", "sha2", "commit_url", "pr_url", "item_number", "is_merge")
        ]
        
        # Act
        target.generate_excel_file(commits)

        # Assert
        mock_isfile.assert_called_once_with("output.xlsx")
        mock_remove.assert_has_calls([call("output.xlsx"), call("output.xlsx")])
        mock_input.assert_has_calls([call()])


    @patch('builtins.print')
    @patch('os.path.isfile', return_value=False)
    @patch('os.remove')
    @patch('xlsxwriter.Workbook')
    def test_all_visible(self, mock_workbook, mock_remove, mock_isfile, mock_print):
        # Arrange
        mock_worksheet = Mock()
        mock_workbook.return_value.__enter__.return_value.add_worksheet.return_value = mock_worksheet

        target = GitTheCommits(True)
        target.commit_detail_visibilty.message = True
        target.commit_detail_visibilty.item_number = True
        target.commit_detail_visibilty.author = True
        target.commit_detail_visibilty.date = True
        target.commit_detail_visibilty.commit_url = True
        target.commit_detail_visibilty.pull_request_url = True
        target.commit_detail_visibilty.sha = True
        target.commit_detail_visibilty.is_merge_commit = True
        target.strip_characters_from_item_numbers = True
        
        commits = [
            CommitInfo("message1", "author1", "2022-01-01", "sha1", "commit_url1", "pr_url1", "123", "is_merge1"),
            CommitInfo("message2", "author2", "2022-01-02", "sha2", "commit_url2", "pr_url2", "234", "is_merge2")
        ]
        
        # Act
        target.generate_excel_file(commits)

        # Assert
        mock_workbook.assert_called_once_with("output.xlsx")
        mock_worksheet = mock_workbook.return_value.__enter__.return_value.add_worksheet.return_value

        # Check that the correct headers were written to the worksheet
        calls = [
            call('A1', "Commit Message", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('B1', "Item Number", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('C1', "Author", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('D1', "Date", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('E1', "Commit Url", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('F1', "Pull Request Url", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('G1', "Sha", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('H1', "Is Merge Commit", mock_workbook.return_value.__enter__.return_value.add_format.return_value)
        ]
        mock_worksheet.write_string.assert_has_calls(calls, any_order=True)

        # Check that the correct data was written to the worksheet
        calls = [
            call(1, 0, "message1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 1, "123", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 2, "author1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 3, "2022-01-01", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 4, "commit_url1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 5, "pr_url1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 6, "sha1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 7, "is_merge1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 0, "message2", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 1, "234", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 2, "author2", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 3, "2022-01-02", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 4, "commit_url2", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 5, "pr_url2", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 6, "sha2", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 7, "is_merge2", mock_workbook.return_value.__enter__.return_value.add_format.return_value)
        ]
        mock_worksheet.write_string.assert_has_calls(calls, any_order=True)


    @patch('builtins.print')
    @patch('os.path.isfile', return_value=False)
    @patch('os.remove')
    @patch('xlsxwriter.Workbook')
    def test_some_not_visible(self, mock_workbook, mock_remove, mock_isfile, mock_print):
        # Arrange
        mock_worksheet = Mock()
        mock_workbook.return_value.__enter__.return_value.add_worksheet.return_value = mock_worksheet

        target = GitTheCommits(True)
        target.commit_detail_visibilty.message = True
        target.commit_detail_visibilty.item_number = False
        target.commit_detail_visibilty.author = True
        target.commit_detail_visibilty.date = False
        target.commit_detail_visibilty.commit_url = True
        target.commit_detail_visibilty.pull_request_url = False
        target.commit_detail_visibilty.sha = True
        target.commit_detail_visibilty.is_merge_commit = False
        target.strip_characters_from_item_numbers = True
        
        commits = [
            CommitInfo("message1", "author1", "2022-01-01", "sha1", "commit_url1", "pr_url1", "123", "is_merge1"),
            CommitInfo("message2", "author2", "2022-01-02", "sha2", "commit_url2", "pr_url2", "234", "is_merge2")
        ]
        
        # Act
        target.generate_excel_file(commits)

        # Assert
        mock_workbook.assert_called_once_with("output.xlsx")
        mock_worksheet = mock_workbook.return_value.__enter__.return_value.add_worksheet.return_value

        # Check that the correct headers were written to the worksheet
        calls = [
            call('A1', "Commit Message", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('B1', "Author", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('C1', "Commit Url", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call('D1', "Sha", mock_workbook.return_value.__enter__.return_value.add_format.return_value)
        ]
        mock_worksheet.write_string.assert_has_calls(calls, any_order=True)

        # Check that the correct data was written to the worksheet
        calls = [
            call(1, 0, "message1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 1, "author1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 2, "commit_url1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(1, 3, "sha1", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 0, "message2", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 1, "author2", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 2, "commit_url2", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 3, "sha2", mock_workbook.return_value.__enter__.return_value.add_format.return_value)
        ]
        mock_worksheet.write_string.assert_has_calls(calls, any_order=True)

    
    @patch('xlsxwriter.Workbook')
    def test_show_cherry_pick_command(self, mock_workbook):
        # Arrange
        mock_worksheet = Mock()
        mock_workbook.return_value.__enter__.return_value.add_worksheet.return_value = mock_worksheet

        target = GitTheCommits(False)
        target.commit_detail_visibilty.message = True
        target.commit_detail_visibilty.item_number = True
        target.commit_detail_visibilty.author = True
        target.commit_detail_visibilty.date = True
        target.commit_detail_visibilty.commit_url = True
        target.commit_detail_visibilty.pull_request_url = True
        target.commit_detail_visibilty.sha = True
        target.commit_detail_visibilty.is_merge_commit = True
        target.show_cherry_pick_command = True
        target.strip_characters_from_item_numbers = True
        
        commits = [
            CommitInfo("message1", "author1", "2022-01-01", "sha1", "commit_url1", "pr_url1", "123", "is_merge1"),
            CommitInfo("message2", "author2", "2022-01-02", "sha2", "commit_url2", "pr_url2", "234", "is_merge2")
        ]
        
        # Act
        target.generate_excel_file(commits)

        # Assert
        mock_workbook.assert_called_once_with("output.xlsx")
        mock_worksheet = mock_workbook.return_value.__enter__.return_value.add_worksheet.return_value

        # Check that the cherry pick command was written to the worksheet
        mock_worksheet.merge_range.assert_called_once_with('A5:I5', target.generate_cherry_pick_command(commits), mock_workbook.return_value.__enter__.return_value.add_format.return_value)


    @patch('builtins.print')
    @patch('os.path.isfile', return_value=False)
    @patch('os.remove')
    @patch('xlsxwriter.Workbook')
    def test_item_header_when_strip_characters_from_item_numbers(self, mock_workbook, mock_remove, mock_isfile, mock_print):
        # Arrange
        mock_worksheet = Mock()
        mock_workbook.return_value.__enter__.return_value.add_worksheet.return_value = mock_worksheet

        target = GitTheCommits(True)
        target.commit_detail_visibilty.item_number = True
        target.strip_characters_from_item_numbers = False
        
        commits = [
            CommitInfo("message1", "author1", "2022-01-01", "sha1", "commit_url1", "pr_url1", "123", "is_merge1"),
            CommitInfo("message2", "author2", "2022-01-02", "sha2", "commit_url2", "pr_url2", "234", "is_merge2")
        ]
        
        # Act
        target.generate_excel_file(commits)

        # Assert
        mock_workbook.assert_called_once_with("output.xlsx")
        mock_worksheet = mock_workbook.return_value.__enter__.return_value.add_worksheet.return_value

        # Check that the correct headers were written to the worksheet
        calls = [
            call('A1', "Item", mock_workbook.return_value.__enter__.return_value.add_format.return_value)
        ]
        mock_worksheet.write_string.assert_has_calls(calls, any_order=True)

        # Check that the correct data was written to the worksheet
        calls = [
            call(1, 0, "123", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
            call(2, 0, "234", mock_workbook.return_value.__enter__.return_value.add_format.return_value),
        ]
        mock_worksheet.write_string.assert_has_calls(calls, any_order=True)


class TestFetchCommits(unittest.TestCase):
    def test_use_pull_requests_returns_commit_from_pr_with_item_number(self):
        # Arrange
        git_commit = Mock()
        git_commit.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_pull_requests = True

        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        self.assertEqual(1, len(target.commit_list))
        result_commit = target.commit_list[0]
        self.assertEqual("1234", result_commit.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit.sha)

    
    def test_use_commit_history_returns_commit_from_history_with_item_number(self):
        # Arrange
        git_commit = Mock()
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "commit for item-1234", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit]

        mock_commit = Mock()
        mock_commit.sha = "ITEM-1234"
        mock_commit.commit = git_commit
        mock_commit.html_url = "www.google.com/commit"
        mock_commit.get_pulls.return_value = [mock_pull_request]

        mock_repo = Mock()
        mock_repo.get_commits.return_value = [mock_commit]

        mock_branch = Mock()
        mock_branch.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_commit_history = True

        target.github_repository = mock_repo
        target.github_target_branch = mock_branch

        # Act
        target.fetch_commits()

        # Assert
        self.assertEqual(1, len(target.commit_list))
        result_commit = target.commit_list[0]
        self.assertEqual("1234", result_commit.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit.sha)


    @patch('builtins.print')
    def test_use_pull_requests_outputs_to_terminal(self, mock_print):
        # Arrange
        git_commit = Mock()
        git_commit.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_pull_requests = True
        target.output_to_terminal = True

        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        self.assertEqual(1, len(target.commit_list))
        expected_calls = [
            call("Fetching commits", end="", flush=True),
            call('.', end='', flush=True)
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)


    @patch('builtins.print')
    def test_use_commit_history_outputs_to_terminal(self, mock_print):
        # Arrange
        git_commit = Mock()
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "commit for item-1234", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit]

        mock_commit = Mock()
        mock_commit.sha = "ITEM-1234"
        mock_commit.commit = git_commit
        mock_commit.html_url = "www.google.com/commit"
        mock_commit.get_pulls.return_value = [mock_pull_request]

        mock_repo = Mock()
        mock_repo.get_commits.return_value = [mock_commit]

        mock_branch = Mock()
        mock_branch.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_commit_history = True
        target.output_to_terminal = True

        target.github_repository = mock_repo
        target.github_target_branch = mock_branch

        # Act
        target.fetch_commits()

        # Assert
        self.assertEqual(1, len(target.commit_list))
        expected_calls = [
            call("Fetching commits", end="", flush=True),
            call('.', end='', flush=True)
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)


    def test_use_pull_requests_returns_multiple_commits_from_pr_with_item_number(self):
        # Arrange
        git_commit_1 = Mock()
        git_commit_1.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )
        git_commit_2 = Mock()
        git_commit_2.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a also test", 
                "Uni 2", 
                "uni2@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google3.com", 
                1, 
                True
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit_1, git_commit_2]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_pull_requests = True

        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        self.assertEqual(2, len(target.commit_list))
        result_commit_1 = target.commit_list[0]
        self.assertEqual("1234", result_commit_1.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit_1.sha)
        result_commit_2 = target.commit_list[1]
        self.assertEqual("1234", result_commit_2.item_number)
        self.assertEqual("1234567890123456789012345678901234567890", result_commit_2.sha)


    def test_use_commit_history_returns_multiple_commits_with_item_number(self):
        # Arrange
        git_commit_1 = generate_git_commit_object(
            GitCommitDetails(
                "commit for item-1234", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        git_commit_2 = generate_git_commit_object(
            GitCommitDetails(
                "another commit for item-1234", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654322", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit_1, git_commit_2]

        mock_commit_1 = Mock()
        mock_commit_1.sha = "ITEM-1234"
        mock_commit_1.commit = git_commit_1
        mock_commit_1.html_url = "www.google.com/commit"
        mock_commit_1.get_pulls.return_value = [mock_pull_request]

        mock_commit_2 = Mock()
        mock_commit_2.sha = "ITEM-1234"
        mock_commit_2.commit = git_commit_2
        mock_commit_2.html_url = "www.google.com/commit"
        mock_commit_2.get_pulls.return_value = [mock_pull_request]

        mock_repo = Mock()
        mock_repo.get_commits.return_value = [mock_commit_1, mock_commit_2]

        mock_branch = Mock()
        mock_branch.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_commit_history = True

        target.github_repository = mock_repo
        target.github_target_branch = mock_branch

        # Act
        target.fetch_commits()

        # Assert
        self.assertEqual(2, len(target.commit_list))
        result_commit_1 = target.commit_list[0]
        self.assertEqual("1234", result_commit_1.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit_1.sha)
        result_commit_2 = target.commit_list[1]
        self.assertEqual("1234", result_commit_2.item_number)
        self.assertEqual("0987654321098765432109876543210987654322", result_commit_2.sha)


    def test_use_pull_requests_returns_only_pr_with_item_number(self):
        # Arrange
        git_commit_1 = Mock()
        git_commit_1.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )
        git_commit_2 = Mock()
        git_commit_2.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a also test", 
                "Uni 2", 
                "uni2@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google3.com", 
                1, 
                True
            )
        )

        mock_pull_request_1 = Mock()
        mock_pull_request_1.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request_1.head.ref = "ITEM-1234"
        mock_pull_request_1.merged = True
        mock_pull_request_1.number = 1
        mock_pull_request_1.html_url = "www.google.com/pr"
        mock_pull_request_1.get_commits.return_value = [git_commit_1]

        mock_pull_request_2 = Mock()
        mock_pull_request_2.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request_2.head.ref = "ITEM-5678"
        mock_pull_request_2.merged = True
        mock_pull_request_2.number = 2
        mock_pull_request_2.html_url = "www.google.com/pr"
        mock_pull_request_2.get_commits.return_value = [git_commit_2]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request_1, mock_pull_request_2]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_pull_requests = True

        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        self.assertEqual(1, len(target.commit_list))
        result_commit_1 = target.commit_list[0]
        self.assertEqual("1234", result_commit_1.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit_1.sha)


    def test_use_commit_history_returns_only_pr_with_item_number(self):
        # Arrange
        git_commit_1 = generate_git_commit_object(
            GitCommitDetails(
                "commit for item-1234", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        git_commit_2 = generate_git_commit_object(
            GitCommitDetails(
                "commit for item-9876", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654322", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit_1, git_commit_2]

        mock_commit_1 = Mock()
        mock_commit_1.sha = "ITEM-1234"
        mock_commit_1.commit = git_commit_1
        mock_commit_1.html_url = "www.google.com/commit"
        mock_commit_1.get_pulls.return_value = [mock_pull_request]

        mock_commit_2 = Mock()
        mock_commit_2.sha = "ITEM-1234"
        mock_commit_2.commit = git_commit_2
        mock_commit_2.html_url = "www.google.com/commit"
        mock_commit_2.get_pulls.return_value = [mock_pull_request]

        mock_repo = Mock()
        mock_repo.get_commits.return_value = [mock_commit_1, mock_commit_2]

        mock_branch = Mock()
        mock_branch.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_commit_history = True

        target.github_repository = mock_repo
        target.github_target_branch = mock_branch

        # Act
        target.fetch_commits()

        # Assert
        self.assertEqual(1, len(target.commit_list))
        result_commit = target.commit_list[0]
        self.assertEqual("1234", result_commit.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit.sha)


    def test_use_pull_requests_skips_unmerged_prs(self):
        # Arrange
        git_commit = Mock()
        git_commit.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = False
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_pull_requests = True

        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        self.assertEqual(0, len(target.commit_list))


    def test_use_pull_requests_returns_prs_within_search_date_limit(self):
        # Arrange
        git_commit_1 = Mock()
        git_commit_1.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )
        git_commit_2 = Mock()
        git_commit_2.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a also test", 
                "Uni 2", 
                "uni2@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google3.com", 
                1, 
                True
            )
        )

        mock_pull_request_1 = Mock()
        mock_pull_request_1.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request_1.head.ref = "ITEM-1234"
        mock_pull_request_1.merged = True
        mock_pull_request_1.number = 1
        mock_pull_request_1.html_url = "www.google.com/pr"
        mock_pull_request_1.get_commits.return_value = [git_commit_1]

        mock_pull_request_2 = Mock()
        mock_pull_request_2.created_at = (datetime.today() - relativedelta(months=2)).replace(tzinfo=timezone.utc)
        mock_pull_request_2.head.ref = "ITEM-5678"
        mock_pull_request_2.merged = True
        mock_pull_request_2.number = 2
        mock_pull_request_2.html_url = "www.google.com/pr"
        mock_pull_request_2.get_commits.return_value = [git_commit_2]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request_1, mock_pull_request_2]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_pull_requests = True
        target.search_date_limit = (datetime.today() - relativedelta(months=1)).replace(tzinfo=timezone.utc)
        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        self.assertEqual(1, len(target.commit_list))
        result_commit_1 = target.commit_list[0]
        self.assertEqual("1234", result_commit_1.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit_1.sha)

    
    def test_use_commit_history_returns_commits_within_search_date_limit(self):
        # Arrange
        git_commit = Mock()
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "commit for item-1234", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit]

        mock_commit = Mock()
        mock_commit.sha = "ITEM-1234"
        mock_commit.commit = git_commit
        mock_commit.html_url = "www.google.com/commit"
        mock_commit.get_pulls.return_value = [mock_pull_request]

        mock_repo = Mock()
        mock_repo.get_commits.return_value = [mock_commit]

        mock_branch = Mock()
        mock_branch.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_commit_history = True
        target.search_date_limit = (datetime.today() - relativedelta(months=1)).replace(tzinfo=timezone.utc)

        target.github_repository = mock_repo
        target.github_target_branch = mock_branch

        # Act
        target.fetch_commits()

        # Assert
        target.github_repository.get_commits.assert_called_once_with(sha=mock_branch.commit.sha, since=target.search_date_limit)


    def test_use_pull_requests_returns_prs_which_have_item_numbers_inside_each_other(self):
        # Arrange
        git_commit_1 = Mock()
        git_commit_1.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )
        git_commit_2 = Mock()
        git_commit_2.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a also test", 
                "Uni 2", 
                "uni2@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google3.com", 
                1, 
                True
            )
        )
        git_commit_3 = Mock()
        git_commit_3.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a also test", 
                "Uni 2", 
                "uni2@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "2345678901234567890123456789012345678901", 
                "www.google3.com", 
                1, 
                True
            )
        )

        mock_pull_request_1 = Mock()
        mock_pull_request_1.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request_1.head.ref = "ITEM-123"
        mock_pull_request_1.merged = True
        mock_pull_request_1.number = 1
        mock_pull_request_1.html_url = "www.google.com/pr"
        mock_pull_request_1.get_commits.return_value = [git_commit_1]

        mock_pull_request_2 = Mock()
        mock_pull_request_2.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request_2.head.ref = "ITEM-12345"
        mock_pull_request_2.merged = True
        mock_pull_request_2.number = 2
        mock_pull_request_2.html_url = "www.google.com/pr"
        mock_pull_request_2.get_commits.return_value = [git_commit_2]

        mock_pull_request_3 = Mock()
        mock_pull_request_3.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request_3.head.ref = "ITEM-345"
        mock_pull_request_3.merged = True
        mock_pull_request_3.number = 3
        mock_pull_request_3.html_url = "www.google.com/pr"
        mock_pull_request_3.get_commits.return_value = [git_commit_3]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request_1, mock_pull_request_2, mock_pull_request_3]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["123", "345", "12345"]
        target.use_pull_requests = True
        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        self.assertEqual(3, len(target.commit_list))

        filtered_commits = list(filter(lambda c: c.item_number == "123", target.commit_list))
        self.assertEqual(1, len(filtered_commits)) # 123
        commit_123 = filtered_commits[0]
        self.assertIsNotNone(commit_123)
        self.assertEqual("123", commit_123.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", commit_123.sha)

        filtered_commits = list(filter(lambda c: c.item_number == "345", target.commit_list))
        self.assertEqual(1, len(filtered_commits)) # 345
        commit_345 = filtered_commits[0]
        self.assertIsNotNone(commit_345)
        self.assertEqual("345", commit_345.item_number)
        self.assertEqual("2345678901234567890123456789012345678901", commit_345.sha)
        
        filtered_commits = list(filter(lambda c: c.item_number == "12345", target.commit_list))
        self.assertEqual(1, len(filtered_commits)) # 12345
        commit_12345 = filtered_commits[0]
        self.assertIsNotNone(commit_12345)
        self.assertEqual("12345", commit_12345.item_number)
        self.assertEqual("1234567890123456789012345678901234567890", commit_12345.sha)


    def test_use_pull_requests_can_distinguish_separated_numbers(self):
        # Arrange
        git_commit_1 = Mock()
        git_commit_1.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )
        git_commit_2 = Mock()
        git_commit_2.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a also test", 
                "Uni 2", 
                "uni2@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google3.com", 
                1, 
                True
            )
        )

        mock_pull_request_1 = Mock()
        mock_pull_request_1.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request_1.head.ref = "ITEM-1234-5"
        mock_pull_request_1.merged = True
        mock_pull_request_1.number = 1
        mock_pull_request_1.html_url = "www.google.com/pr"
        mock_pull_request_1.get_commits.return_value = [git_commit_1]

        mock_pull_request_2 = Mock()
        mock_pull_request_2.created_at = (datetime.today() - relativedelta(months=2)).replace(tzinfo=timezone.utc)
        mock_pull_request_2.head.ref = "123-4567"
        mock_pull_request_2.merged = True
        mock_pull_request_2.number = 2
        mock_pull_request_2.html_url = "www.google.com/pr"
        mock_pull_request_2.get_commits.return_value = [git_commit_2]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request_1, mock_pull_request_2]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["12345", "1234567", "123"]
        target.use_pull_requests = True
        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        self.assertEqual(1, len(target.commit_list))
        result_commit_1 = target.commit_list[0]
        self.assertEqual("123", result_commit_1.item_number)
        self.assertEqual("1234567890123456789012345678901234567890", result_commit_1.sha)


    def test_use_commit_history_can_distinguish_separated_numbers(self):
        # Arrange
        git_commit_1 = generate_git_commit_object(
            GitCommitDetails(
                "commit for ITEM-1234-5", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        git_commit_2 = generate_git_commit_object(
            GitCommitDetails(
                "another commit for 123-4567", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654322", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        mock_pull_request_1 = Mock()
        mock_pull_request_1.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request_1.head.ref = "ITEM-1234-5"
        mock_pull_request_1.merged = True
        mock_pull_request_1.number = 1
        mock_pull_request_1.html_url = "www.google.com/pr"
        mock_pull_request_1.get_commits.return_value = [git_commit_1]

        mock_pull_request_2 = Mock()
        mock_pull_request_2.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request_2.head.ref = "123-4567"
        mock_pull_request_2.merged = True
        mock_pull_request_2.number = 1
        mock_pull_request_2.html_url = "www.google.com/pr"
        mock_pull_request_2.get_commits.return_value = [git_commit_2]

        mock_commit_1 = Mock()
        mock_commit_1.sha = "ITEM-1234-5"
        mock_commit_1.commit = git_commit_1
        mock_commit_1.html_url = "www.google.com/commit"
        mock_commit_1.get_pulls.return_value = [mock_pull_request_1]

        mock_commit_2 = Mock()
        mock_commit_2.sha = "123-4567"
        mock_commit_2.commit = git_commit_2
        mock_commit_2.html_url = "www.google.com/commit"
        mock_commit_2.get_pulls.return_value = [mock_pull_request_2]

        mock_repo = Mock()
        mock_repo.get_commits.return_value = [mock_commit_1, mock_commit_2]

        mock_branch = Mock()
        mock_branch.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = ["1234"]
        target.use_commit_history = True
        target.github_repository = mock_repo
        target.github_target_branch = mock_branch

        # Act
        target.fetch_commits()

        # Assert
        self.assertEqual(1, len(target.commit_list))
        result_commit = target.commit_list[0]
        self.assertEqual("1234", result_commit.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit.sha)


    @patch('GitTheCommits.GitTheCommits.manually_enter_item_numbers')
    def test_handles_no_initial_item_numbers(self, mock_enter_item_numbers):
        # Arrange
        git_commit = Mock()
        git_commit.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit]

        mock_enter_item_numbers.return_value = ["1234"]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = True
        target.item_numbers = []
        target.use_pull_requests = True

        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        mock_enter_item_numbers.assert_called_once()
        self.assertEqual(1, len(target.commit_list))


    def test_use_pull_requests_returns_commit_from_pr_for_item_with_characters(self):
        # Arrange
        git_commit = Mock()
        git_commit.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit]

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pull_request]

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = False
        target.item_numbers = ["ITEM-1234"]
        target.use_pull_requests = True

        target.github_repository = mock_repo

        # Act
        target.fetch_commits()

        # Arrange
        self.assertEqual(1, len(target.commit_list))
        result_commit = target.commit_list[0]
        self.assertEqual("ITEM-1234", result_commit.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit.sha)

    
    def test_use_commit_history_returns_commit_from_history_for_item_with_characters(self):
        # Arrange
        git_commit = Mock()
        git_commit = generate_git_commit_object(
            GitCommitDetails(
                "commit for ITEM-1234", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "0987654321098765432109876543210987654321", 
                "www.google2.com", 
                1, 
                True,
                "1234567890123456789012345678901234567890"
            )
        )

        mock_pull_request = Mock()
        mock_pull_request.created_at = datetime.today().replace(tzinfo=timezone.utc)
        mock_pull_request.head.ref = "ITEM-1234"
        mock_pull_request.merged = True
        mock_pull_request.number = 1
        mock_pull_request.html_url = "www.google.com/pr"
        mock_pull_request.get_commits.return_value = [git_commit]

        mock_commit = Mock()
        mock_commit.sha = "1234"
        mock_commit.commit = git_commit
        mock_commit.html_url = "www.google.com/commit"
        mock_commit.get_pulls.return_value = [mock_pull_request]

        mock_repo = Mock()
        mock_repo.get_commits.return_value = [mock_commit]

        mock_branch = Mock()
        mock_branch.commit = generate_git_commit_object(
            GitCommitDetails(
                "This is a test", 
                "Uni", 
                "uni@test.py", 
                "2024-01-12T08:30:02.000Z", 
                "1234567890123456789012345678901234567890", 
                "www.google2.com", 
                1, 
                True
            )
        )

        target = GitTheCommits(False)
        target.strip_characters_from_item_numbers = False
        target.item_numbers = ["ITEM-1234"]
        target.use_commit_history = True

        target.github_repository = mock_repo
        target.github_target_branch = mock_branch

        # Act
        target.fetch_commits()

        # Assert
        self.assertEqual(1, len(target.commit_list))
        result_commit = target.commit_list[0]
        self.assertEqual("ITEM-1234", result_commit.item_number)
        self.assertEqual("0987654321098765432109876543210987654321", result_commit.sha)


class TestOutputCommits(unittest.TestCase):
    @patch('builtins.print')
    @patch('builtins.input')
    @patch('builtins.exit', side_effect=SystemExit)
    def test_prints_terminal_output_no_commits_found_when_no_commit_list_empty(self, mock_exit, mock_input, mock_print):
        # Arrange
        target = GitTheCommits(False)

        target.commit_list = []
        target.output_to_terminal = True
        target.output_to_excel = False
        target.output_to_txt = False

        # Act
        with self.assertRaises(SystemExit):
            target.output_commits()

        # Assert
        mock_print.assert_called_once_with("\nNo commits found")
        mock_input.assert_called_once()
        mock_exit.assert_called_once()


    @patch('builtins.print')
    @patch('builtins.input')
    @patch('builtins.exit', side_effect=SystemExit)
    @patch('builtins.open', new_callable=mock_open)
    def test_prints_txt_output_no_commits_found_when_no_commit_list_empty(self, mock_open, mock_exit, mock_input, mock_print):
        # Arrange
        target = GitTheCommits(False)

        target.commit_list = []  # no commits
        target.output_to_terminal = False
        target.output_to_excel = False
        target.output_to_txt = True

        # Act
        with self.assertRaises(SystemExit):
            target.output_commits()

        # Assert
        mock_open.assert_called_once_with("output.txt", 'w')
        mock_open().write.assert_called_once_with("No commits found")
        mock_print.assert_not_called()
        mock_input.assert_called_once()
        mock_exit.assert_called_once()

    
    @patch('builtins.print')
    @patch('builtins.input')
    @patch('builtins.exit', side_effect=SystemExit)
    def test_prints_excel_output_no_commits_found_when_no_commit_list_empty(self, mock_exit, mock_input, mock_print):
        # Arrange
        target = GitTheCommits(False)

        target.commit_list = []
        target.output_to_terminal = False
        target.output_to_excel = True
        target.output_to_txt = False

        # Act
        with self.assertRaises(SystemExit):
            target.output_commits()

        # Assert
        mock_print.assert_called_once_with("\nNo commits found")
        mock_input.assert_called_once()
        mock_exit.assert_called_once()

    
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_group_by_item_finds_commits_for_multiple_items(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", 
            "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo("commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", 
            "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )
        
        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 2 related commits'),
            call('\nCommit for 1 (1):\n- commit for item1\n\n---'),
            call('\nCommit for 2 (1):\n- commit for item2\n\n---'),
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)
    
    
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_group_by_item_finds_multiple_commits_for_multiple_items(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 3 related commits'),
            call('\nCommits for 1 (2):\n- commit1 for item1\n\n- commit2 for item1\n\n---'),
            call('\nCommit for 2 (1):\n- commit for item2\n\n---')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)
    
    
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_group_by_item_finds_no_commit_for_one_item(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", 
            "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        
        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 1 related commit'),
            call('\nCommit for 1 (1):\n- commit for item1\n\n---'),
            call('\nNo commits found for 2\n\n---'),
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)
    

    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_group_by_item_sorts_commits_date_asc(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 2 related commits'),
            call('\nCommits for 1 (2):\n- commit1 for item1\n\n- commit2 for item1\n\n---')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)
    
    
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_group_by_item_sorts_commits_date_desc(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = True
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 2 related commits'),
            call('\nCommits for 1 (2):\n- commit2 for item1\n\n- commit1 for item1\n\n---')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)


    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_group_by_item_finds_commits_for_multiple_items_and_prints_cherrypick_command(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = True
        target.cherry_pick_command = "git cherry-pick"
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 2 related commits'),
            call('\nCommit for 1 (1):\n- commit for item1\n\n---'),
            call('\nCommit for 2 (1):\n- commit for item2\n\n---'),
            call('\ngit cherry-pick 1234567890 0987654321')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)


    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_group_by_item_prints_cherry_pick_per_item(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.order_commits_by_date_descend = False
        target.group_commits_by_item = True
        target.group_commit_cherry_pick = True
        target.cherry_pick_command = "git cherry-pick"
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 3 related commits'),
            call('\nCommits for 1 (2):\n- commit1 for item1\n\n- commit2 for item1\n\ngit cherry-pick 1234567890 0987654321\n---'),
            call('\nCommit for 2 (1):\n- commit for item2\n\ngit cherry-pick 2345678901\n---')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)
    
    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_group_by_item_finds_commits_for_multiple_items(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", 
            "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo("commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", 
            "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )
        
        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 2 related commits\n\nCommit for 1 (1):\n- commit for item1\n\n---\n\nCommit for 2 (1):\n- commit for item2\n\n---')
    
    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_group_by_item_finds_multiple_commits_for_multiple_items(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 3 related commits\n\nCommits for 1 (2):\n- commit1 for item1\n\n- commit2 for item1\n\n---\n\nCommit for 2 (1):\n- commit for item2\n\n---')
    
    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_group_by_item_finds_no_commit_for_one_item(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", 
            "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        
        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 1 related commit\n\nCommit for 1 (1):\n- commit for item1\n\n---\n\nNo commits found for 2\n\n---')
    
    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_group_by_item_sorts_commits_date_asc(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 2 related commits\n\nCommits for 1 (2):\n- commit1 for item1\n\n- commit2 for item1\n\n---')
    
    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_group_by_item_sorts_commits_date_desc(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = True
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 2 related commits\n\nCommits for 1 (2):\n- commit2 for item1\n\n- commit1 for item1\n\n---')


    @patch('builtins.open', new_callable=mock_open)
    def test_txt_group_by_item_finds_commits_for_multiple_items_and_prints_cherrypick_command(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = True
        target.cherry_pick_command = "git cherry-pick"
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 2 related commits\n\nCommit for 1 (1):\n- commit for item1\n\n---\n\nCommit for 2 (1):\n- commit for item2\n\n---\n\ngit cherry-pick 1234567890 0987654321')

    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_group_by_item_prints_cherry_pick_per_item(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = True
        target.group_commit_cherry_pick = True
        target.cherry_pick_command = "git cherry-pick"
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 3 related commits\n\nCommits for 1 (2):\n- commit1 for item1\n\n- commit2 for item1\n\ngit cherry-pick 1234567890 0987654321\n---\n\nCommit for 2 (1):\n- commit for item2\n\ngit cherry-pick 2345678901\n---')
    
    
    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_group_by_item_sorts_commits_date_desc(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", 
            "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )
        
        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = True
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit1, commit2])

    
    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_group_by_item_finds_commits_for_multiple_items(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", 
            "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo("commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", 
            "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )
        
        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit1, commit2])
    
    
    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_group_by_item_finds_multiple_commits_for_multiple_items(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit1, commit2, commit3])
    
    
    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_group_by_item_sorts_commits_date_asc(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit1, commit2])
    
    
    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_group_by_item_multiple_commits_in_item_sorts_commits_date_desc(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = True
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit2, commit1])


    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_group_by_item_finds_commits_for_multiple_items_and_prints_cherrypick_command(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = True
        target.cherry_pick_command = "git cherry-pick"
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit1, commit2])


    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_finds_commits_for_multiple_items(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call("\nFound 2 related commits"),
            call("Here are all commits for your items in acsending order:\n\n- commit for item1\n\n- commit for item2\n")
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)
    
    
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_finds_multiple_commits_for_multiple_items(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 3 related commits'),
            call('Here are all commits for your items in acsending order:\n\n- commit1 for item1\n\n- commit2 for item1\n\n- commit for item2\n')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)
    
    
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_sorts_commits_date_asc(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 2 related commits'),
            call('Here are all commits for your items in acsending order:\n\n- commit1 for item1\n\n- commit2 for item1\n')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)
    
    
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_sorts_commits_date_desc(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = True
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 2 related commits'),
            call('Here are all commits for your items in descending order:\n\n- commit2 for item1\n\n- commit1 for item1\n')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)


    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_finds_commits_for_multiple_items_and_prints_cherrypick_command(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = True
        target.cherry_pick_command = "git cherry-pick"
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 2 related commits'),
            call('Here are all commits for your items in acsending order:\n\n- commit for item1\n\n- commit for item2\n\ngit cherry-pick 1234567890 0987654321')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)

    
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_terminal_group_commit_cherry_pick_not_ran_without_group_commits_by_item(self, mock_print, mock_input):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_terminal = True
        target.group_commits_by_item = False
        target.group_commit_cherry_pick = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        expected_calls = [
            call('\nFound 3 related commits'),
            call('Here are all commits for your items in acsending order:\n\n- commit1 for item1\n\n- commit2 for item1\n\n- commit for item2\n')
        ]
        mock_print.assert_has_calls(expected_calls, any_order=False)
    
    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_finds_commits_for_multiple_items(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", 
            "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo("commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", 
            "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )
        
        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 2 related commits\nHere are all commits for your items in acsending order:\n\n- commit for item1\n\n- commit for item2\n')
    
    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_finds_multiple_commits_for_multiple_items(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 3 related commits\nHere are all commits for your items in acsending order:\n\n- commit1 for item1\n\n- commit2 for item1\n\n- commit for item2\n')
    
    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_sorts_commits_date_asc(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 2 related commits\nHere are all commits for your items in acsending order:\n\n- commit1 for item1\n\n- commit2 for item1\n')
    
    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_sorts_commits_date_desc(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = True
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 2 related commits\nHere are all commits for your items in descending order:\n\n- commit2 for item1\n\n- commit1 for item1\n')


    @patch('builtins.open', new_callable=mock_open)
    def test_txt_finds_commits_for_multiple_items_and_prints_cherrypick_command(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = True
        target.cherry_pick_command = "git cherry-pick"
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 2 related commits\nHere are all commits for your items in acsending order:\n\n- commit for item1\n\n- commit for item2\n\ngit cherry-pick 1234567890 0987654321')

    
    @patch('builtins.open', new_callable=mock_open)
    def test_txt_group_commit_cherry_pick_not_ran_without_group_commits_by_item(self, mock_open):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_txt = True
        target.group_commits_by_item = False
        target.group_commit_cherry_pick = True
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        mock_open().write.assert_called_once_with('Found 3 related commits\nHere are all commits for your items in acsending order:\n\n- commit1 for item1\n\n- commit2 for item1\n\n- commit for item2\n')
    
    
    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_finds_commits_for_multiple_items(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", 
            "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo("commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", 
            "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )
        
        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit1, commit2])
    
    
    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_finds_multiple_commits_for_multiple_items(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )
        commit3 = CommitInfo(
            "commit for item2", 
            "author3", 
            datetime.strptime("2022-01-03", "%Y-%m-%d"), 
            "2345678901", 
            "www.google.com/commit3", 
            "www.google.com/pr3", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2, commit3]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0, 1], "2": [2]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit1, commit2, commit3])
    
    
    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_sorts_commits_date_asc(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit1, commit2])
    
    
    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_sorts_commits_date_desc(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit1 for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit2 for item1", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "1", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = True
        target.show_cherry_pick_command = False
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1"]
        target.item_commit_dictionary = {"1": [0, 1]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit2, commit1])


    @patch('GitTheCommits.GitTheCommits.generate_excel_file')
    def test_excel_finds_commits_for_multiple_items_and_prints_cherrypick_command(self, mock_generate_excel_file):
        # Arrange
        commit1 = CommitInfo(
            "commit for item1", 
            "author1", 
            datetime.strptime("2022-01-01", "%Y-%m-%d"), 
            "1234567890", 
            "www.google.com/commit1", 
            "www.google.com/pr1", 
            "1", 
            False
        )
        commit2 = CommitInfo(
            "commit for item2", 
            "author2", 
            datetime.strptime("2022-01-02", "%Y-%m-%d"), 
            "0987654321", 
            "www.google.com/commit2", 
            "www.google.com/pr2", 
            "2", 
            False
        )

        target = GitTheCommits(False)
        target.output_to_excel = True
        target.group_commits_by_item = False
        target.order_commits_by_date_descend = False
        target.show_cherry_pick_command = True
        target.cherry_pick_command = "git cherry-pick"
        target.commit_detail_visibilty.message = True

        target.commit_list = [commit1, commit2]
        target.item_numbers = ["1", "2"]
        target.item_commit_dictionary = {"1": [0], "2": [1]}

        # Act
        target.output_commits()

        # Assert
        mock_generate_excel_file.assert_called_once_with([commit1, commit2])


class TestGetGithubObjects(unittest.TestCase):
    @patch('GitTheCommits.Auth.Token')
    @patch('GitTheCommits.Github')
    def test_success(self, mock_github, mock_token):
        # Arrange
        mock_repo = MagicMock()
        mock_branch = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo
        mock_repo.get_branch.return_value = mock_branch

        target = GitTheCommits(False)
        target.github_token = 'mock_token'
        target.repository_name = 'mock_repo'
        target.target_branch_name = 'mock_branch'

        # Act
        target.get_github_objects()

        # Assert
        mock_github.assert_called_once_with(auth=mock_token())
        mock_github.return_value.get_repo.assert_called_once_with('mock_repo')
        mock_repo.get_branch.assert_called_once_with('mock_branch')
        self.assertEqual(target.github_repository, mock_repo)
        self.assertEqual(target.github_target_branch, mock_branch)


    @patch('GitTheCommits.Github')
    @patch('builtins.print')
    @patch('builtins.input')
    def test_bad_credentials(self, mock_input, mock_print, mock_github):
        # Arrange
        mock_github.return_value.get_repo.side_effect = BadCredentialsException(
            status="Bad credentials",
            data={"message": "Bad credentials"}
        )

        target = GitTheCommits(False)
        target.github_token = 'mock_token'
        target.repository_name = 'mock_repo'

        # Act
        try:
            target.get_github_objects()
        except SystemExit:
            pass

        # Assert
        mock_print.assert_called_once_with(
            "Github responded with a Bad Credentials error. Please ensure that your GitHubToken is valid and has the required permissions, then try again."
        )
        mock_input.assert_called_once()


    @patch('GitTheCommits.Github')
    @patch('builtins.print')
    @patch('builtins.input')
    def test_get_repo_repo_not_found(self, mock_input, mock_print, mock_github):
        # Arrange
        mock_github.return_value.get_repo.side_effect = GithubException(
            status=404,
            data={"message": "Not Found"}
        )

        target = GitTheCommits(False)
        target.github_token = 'mock_token'
        target.repository_name = 'mock_repo'

        # Act
        try:
            target.get_github_objects()
        except SystemExit:
            pass

        # Assert
        mock_print.assert_called_once_with(
            "Could not find the target repository 'mock_repo'. Please ensure that your TargetRepository is correct and your GitHubToken has the required permissions to view the repository, then try again."
        )
        mock_input.assert_called_once()


    @patch('GitTheCommits.Github')
    def test_get_repo_unhandled_exception(self, mock_github):
        # Arrange
        mock_github.return_value.get_repo.side_effect = GithubException(
            status=500,
            data={"message": "Internal Server Error"}
        )

        target = GitTheCommits(False)
        target.github_token = 'mock_token'
        target.repository_name = 'mock_repo'

        # Act & Assert
        with self.assertRaises(GithubException) as context:
            target.get_github_objects()

        self.assertTrue('Internal Server Error' in str(context.exception))


    @patch('GitTheCommits.Github')
    @patch('builtins.print')
    @patch('builtins.input')
    def test_get_branch_branch_not_found(self, mock_input, mock_print, mock_github):
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_branch.side_effect = GithubException(
            status=404,
            data={"message": "Branch not found"}
        )
        mock_github.return_value.get_repo.return_value = mock_repo

        target = GitTheCommits(False)
        target.github_token = 'mock_token'
        target.repository_name = 'mock_repo'
        target.target_branch_name = 'mock_branch'

        # Act
        try:
            target.get_github_objects()
        except SystemExit:
            pass

        # Assert
        mock_print.assert_called_once_with(
            "Could not find the target branch 'mock_branch'. Please ensure that your TargetBranch exists, then try again."
        )
        mock_input.assert_called_once()


    @patch('GitTheCommits.Github')
    @patch('builtins.print')
    @patch('builtins.input')
    def test_get_branch_unhandled_exception(self, mock_input, mock_print, mock_github):
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_branch.side_effect = GithubException(
            status=500,
            data={"message": "Internal Server Error"}
        )
        mock_github.return_value.get_repo.return_value = mock_repo

        target = GitTheCommits(False)
        target.github_token = 'mock_token'
        target.repository_name = 'mock_repo'
        target.target_branch_name = 'mock_branch'

        # Act & Assert
        with self.assertRaises(GithubException) as context:
            target.get_github_objects()

        self.assertTrue('Internal Server Error' in str(context.exception))


# Helper Section
@dataclass
class GitCommitDetails(object):
    """A DTO used to generate fake GitCommits"""
    
    message: str
    name: str
    email: str
    date: str
    sha: str
    html_url: str
    num_parents: int
    completed: bool
    first_parent_sha: str = ""


def get_random_sha():
    return str(randint(1000000000000000000000000000000000000000, 9999999999999999999999999999999999999999))


def generate_git_commit_object(details: GitCommitDetails):
    requester = Requester(Auth.Token("FakeToken"), "https://www.github.com", 123, "user_agent", 10, True, 3, 256)
    headers = {
        "IsTest": True
    }

    parent_commits = []
    for iteration in range(details.num_parents):
        parent_sha = details.first_parent_sha if len(details.first_parent_sha) > 0 and iteration == details.num_parents else get_random_sha()

        parent_commit = generate_git_commit_object(
            GitCommitDetails(
                f"parent_{uuid.uuid4()}", 
                "Parent", 
                "parentcommit@test.py", 
                datetime.today().replace(tzinfo=timezone.utc).isoformat(), 
                parent_sha,
                "www.google.com/parent",
                0,
                True
            )
        )
        
        parent_commits.append(parent_commit.__dict__)

    attributes = {
        "message": details.message,
        "author": {
            "name": details.name,
            "email": details.email,
            "date": details.date,
        },
        "sha": details.sha,
        "html_url": details.html_url,
        "parents": parent_commits
    }

    return GitCommit(requester, headers, attributes, details.completed)
