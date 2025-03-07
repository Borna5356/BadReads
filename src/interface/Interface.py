from getpass import getpass
from tabulate import tabulate

from src.data_interaction.DataInteraction import DataInteraction


class Interface:
    def __init__(self):
        self.database = DataInteraction()

    def __pre_checks(self) -> bool:
        """
        Run any preliminary checks before calling to database

        :return: If query can be allowed to continue
        """
        if self.database.current_user is None:
            print("Must be logged in to a user account.")
            return False

        return True

    def __matching_prompt(self, prompt: str, options: list[str]) -> str:
        """
        Prompt the user and make sure they respond with one of the options

        :param prompt: Prompt to issue the user
        :param options: Available options to pick from
        :return: Selected option
        """
        print("{}: {}".format(prompt, ", ".join(options)))

        selected = "None"
        while selected not in options:
            selected = str(input("Enter option to select: ")).lower()

        return selected

    def login(self) -> bool:
        """
        Attempt to login using a given username and password

        :return: If login was successful
        """
        username = str(input("Username: "))
        password = str(getpass("Password: "))

        if self.database.login(username, password):
            # This means login success so allow login
            print(f"Successfully logged in to {username}.")
            return True

        else:
            print("Incorrect password or user does not exist.")
            return False


    def logout(self) -> bool:
        """
        Log out of the account
        :return: If logout was successful (will fail if no one is logged in)
        """
        if not self.__pre_checks():
            return False

        self.database.logout()
        print("Successfully logged out.")
        return True

    def create_account(self) -> bool:
        """
        Create an account for badreads

        :return: If account creation successful
        """
        username = str(input("Enter a username (must be unique): "))
        name = str(input("Enter your name: "))
        email = str(input("Enter your email: "))
        password = str(getpass("Enter a password: "))
        confirm_pass = str(getpass("Reenter password: "))

        if password != confirm_pass:
            print("Passwords do not match.")
            return False

        # Now attempt to create the account
        if self.database.create_account(username, name, email, password):
            print("Account created successfully! Logged in.")
            self.database.current_user = username
            return True
        else:
            return False

    def create_collection(self) -> bool:
        """
        Create a collection of books

        :return: If creation successful
        """
        if not self.__pre_checks():
            return False

        collection_name = str(input("Enter collection name (must be unique): "))

        isbn_text = str(input("Enter comma separated ISBNs (can be empty): "))
        isbns = [x.strip() for x in isbn_text.split(",")]

        if len(isbns) == 1 and isbns[0] == "":
            isbns = []

        if self.database.create_collection(collection_name, isbns):
            print("Collection created successfully!")
            return True
        else:
            print("Failed to create collection. Collection name should be unique and ISBNs must exist.")
            return False

    def show_collections(self) -> bool:
        """
        List all collections of books

        :return: If display was successful
        """
        if not self.__pre_checks():
            return False

        collections = self.database.list_collections()

        if len(collections) == 0:
            print("You have no existing collections.")

        else:
            headers = ["Collection name", "Number of books", "Total page count"]
            table = tabulate(collections, headers=headers, tablefmt="grid")
            print(table)

        return True

    def search_for_books(self) -> bool:
        """
        Search for books by name, release_date, author, publisher, or genre

        :return: If searching successful
        """
        if not self.__pre_checks():
            return False

        search_options = ["name", "release_date", "author", "publisher", "genre"]

        search_method = self.__matching_prompt("Available search methods", search_options)

        search_val = str(input("Search value: "))

        results = self.database.search_for_book(search_method, search_val)

        # Join up the authors list
        results = [(name, ", ".join(authors), publisher, length, audience, rating) \
                   for (name, authors, publisher, length, audience, rating) in results]

        headers = ["Book name", "Authors", "Publisher", "Length", "Audience", "Rating"]

        table = tabulate(results, headers=headers, tablefmt="grid")

        print(table)

        return True

    def modify_collection(self) -> bool:
        """
        Change name or delete a collection

        :return: If operation successful
        """
        if not self.__pre_checks():
            return False

        collection_name = str(input("Enter collection name: "))

        modify_options = ["rename", "delete"]

        selected = self.__matching_prompt("Available modification options", modify_options)

        if selected == "rename":
            new_name = str(input("Enter new name: "))

            if self.database.rename_collection(collection_name, new_name):
                print("Renamed successfully.")
                return True
            else:
                print("Failed to rename.")
                return False


        elif selected == "delete":
            if self.database.delete_collection(collection_name):
                print("Deleted successfully.")
                return True
            else:
                print("Failed to delete.")
                return False

        return False