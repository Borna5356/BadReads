from getpass import getpass
from tabulate import tabulate

from src.data_interaction.DataInteraction import DataInteraction
from src.data_interaction.DataInteraction import SortOptions


class Interface:
    def __init__(self):
        self.database = DataInteraction()

        # Tuples of command keyword, description, function pointer
        self.command_list = (
            ("help", "Show available commands", self.help),
            ("login", "Login to an existing account", self.login),
            ("logout", "Logout of current account", self.logout),
            ("create account", "Create a new account", self.create_account),
            ("search books", "Search for books in the database", self.search_for_books),
            ("create collection", "Create a collection of books", self.create_collection),
            ("show collections", "Show all created collections", self.show_collections),
            ("show collection contents", "Show all books under a collection", self.get_collection_contents),
            ("modify collection", "Modify the name or delete a collection", self.modify_collection),
            ("modify collection contents", "Modify the contents of a collection", self.modify_collection_contents),
            ("rate book", "Give a book a star rating", self.rate_book),
            ("read book", "Read a book by ISBN", self.read_by_isbn),
            ("read random book", "Read a random book from collection", self.read_random_book),
            ("search users", "Search for users by email", self.search_for_users),
            ("follow user", "Follow a user", self.follow_user),
            ("unfollow user", "Unfollow a user", self.unfollow_user),
            ("list followers", "List all followers", self.list_followers),
            ("list following", "List all following", self.list_following)
        )

        # Generate command mappings
        self.command_mapping = dict()

        for cmd in self.command_list:
            self.command_mapping[cmd[0]] = cmd[2]

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

    def __display_books(self, books) -> None:
        """
        Print a list of books as a table

        :param books: List of books as tuple(name, authors, publisher, length, audience, rating)
        """
        # Join up the authors list
        books = [(name, ", ".join(authors), publisher, length, audience, rating) \
                   for (name, authors, publisher, length, audience, rating) in books]

        headers = ["Book name", "Authors", "Publisher", "Length", "Audience", "Rating"]

        table = tabulate(books, headers=headers, tablefmt="grid")

        print(table)

    def help(self) -> bool:
        """
        Display all available commands

        :return: If successful
        """
        print("Available commands:")

        help_messages = [(i[0], i[1]) for i in self.command_list]

        table = tabulate(help_messages, headers=["Command", "Description"], tablefmt="simple")
        print(table)

        return True

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

        # TODO Add the options to change what we're sorting by

        results = self.database.search_for_book(search_method, search_val, SortOptions.BOOK_NAME, True)

        self.__display_books(results)

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

        print("Unknown error occurred.")
        return False

    def modify_collection_contents(self) -> bool:
        """
        Change the contents of a collection, add or remove books

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        collection_name = str(input("Enter collection name: "))

        modify_options = ["add", "remove"]

        selected = self.__matching_prompt("Available modification options", modify_options)

        if selected == "add":
            new_books_str = str(input("Enter the ISBNs of the books to add comma separated: "))
            new_books = [x.strip() for x in new_books_str.split(",")]

            if self.database.add_books_to_collection(collection_name, new_books):
                print("Successfully added all books!")
                return True
            else:
                print("Failed to add books to collection.")
                return False

        elif selected == "remove":
            remove_books_str = str(input("Enter the ISBNs of the books to remove comma separated: "))
            remove_books = [x.strip() for x in remove_books_str.split(",")]

            if self.database.remove_books_from_collection(collection_name, remove_books):
                print("Successfully removed all books!")
                return True
            else:
                print("Failed to remove books from collection.")
                return False

        print("Unknown error occurred.")
        return False

    def get_collection_contents(self) -> bool:
        """
        Get books in a collection by collection name

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        collection_name = str(input("Enter collection name: "))

        books = self.database.get_collection_contents(collection_name)

        self.__display_books(books)

        return True

    def rate_book(self) -> bool:
        """
        Rate a book by ISBN, overwrites current rating

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        book_isbn = str(input("Enter the ISBN of the book to rate: "))

        if self.database.get_book_by_isbn(book_isbn) is None:
            print("Book does not exist. Try again.")
            return False

        star_rating = 0

        while 1 <= star_rating <= 5:
            star_rating = int(input("Enter new rating to set [1, 5]: "))

        if self.database.rate_book(book_isbn, star_rating):
            print("Successfully set rating.")
            return True
        else:
            print("Failed to set rating.")
            return False

    def read_by_isbn(self) -> bool:
        """
        Read a book by its ISBN and page start and end

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        book_isbn = str(input("Enter the ISBN of the book to read: "))

        if self.database.get_book_by_isbn(book_isbn) is None:
            print("Book does not exist. Try again.")
            return False

        start_page = int(input("Enter start page: "))
        end_page = int(input("Enter end page: "))

        if self.database.read_book_by_isbn(book_isbn, start_page, end_page):
            print("Successfully read book.")
            return True
        else:
            print("Failed to read book.")
            return False

    def read_random_book(self) -> bool:
        """
        Read a random book from a collection

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        collection_name = str(input("Enter collection name: "))

        start_page = int(input("Enter start page: "))
        end_page = int(input("Enter end page: "))

        # TODO Add book name that was read
        if self.database.read_random_book_by_collection(collection_name, start_page, end_page):
            print("Successfully read book.")
            return True
        else:
            print("Failed to read book.")
            return False

    def search_for_users(self) -> bool:
        """
        Search for users by a given email

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        email = str(input("Enter an email to search for users: "))

        usernames = self.database.search_for_users(email)

        print("User accounts found:")

        for user in usernames:
            print(user)

        return True

    def follow_user(self) -> bool:
        """
        Follow a given user

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        username = str(input("Enter a username to follow: "))

        if self.database.follow_user(username):
            print("Followed successfully.")
            return True
        else:
            print("Failed to follow user.")
            return False

    def unfollow_user(self) -> bool:
        """
        Unfollow a given user

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        username = str(input("Enter a username to unfollow: "))

        if self.database.unfollow_user(username):
            print("Unfollowed successfully.")
            return True
        else:
            print("Failed to unfollow user.")
            return False

    def list_followers(self) -> bool:
        """
        List all account followers

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        followers = self.database.list_followers()

        print("Followers:")

        for follower in followers:
            print(follower)

        return True

    def list_following(self) -> bool:
        """
        List all accounts that you follow

        :return: If successful
        """
        if not self.__pre_checks():
            return False

        following = self.database.list_following()

        print("Following:")

        for f in following:
            print(f)

        return True
    
    def shutdown(self):
        self.database.shutdown()
