class DataInteraction:
    def __init__(self):
        pass

    def create_account(self, username: str, password: str) -> bool:
        """
        Create a new account
        -- Username must be unique

        :param username: Username to create
        :param password: Password to set
        :return: If successful
        """
        pass

    def follow_user(self, followee: str) -> bool:
        """
        Current logged in user will follow followee
        -- Followee must exist

        :param followee: Username of person to follow
        :return: If successful
        """
        pass

    def unfollow_user(self, followee: str) -> bool:
        """
        Current logged in user will unfollow the followee
        -- Must be following the user

        :param followee: Person to unfollow by username
        :return: If successful
        """
        pass

    def list_followers(self) -> list[str]:
        """
        List all users that follow current user

        :return: List of usernames that follow current user
        """
        pass

    def list_following(self) -> list[str]:
        """
        List all users that current user follows

        :return: Usernames of following
        """
        pass

    def create_collection(self, collection_name: str, book_isbns: list[str] | None = None) -> bool:
        """
        Create a collection with this name and list of ISBNs (can be empty or None)
        -- Name must be unique, ISBNs must exist

        :param collection_name: Name of collection to create
        :param book_isbns: List of ISBNs for books to add to the collection
        :return: If successful
        """
        pass

    def add_books_to_collection(self, collection_name: str, book_isbns: list[str]) -> bool:
        """
        Add a list of books to a collection
        -- Collection must exist and ISBNs must exist

        :param collection_name: Name of collection to add to
        :param book_isbns: List of books to add by ISBN
        :return: If all were added
        """
        pass

    def remove_books_from_collection(self, collection_name: str, book_isbns: list[str]) -> bool:
        """
        Remove a list of books from a collection
        -- Collection must exist and ISBNs must be in collection

        :param collection_name: Name of collection to remove from
        :param book_isbns: List of books to remove by ISBN
        :return: If all were removed
        """
        pass