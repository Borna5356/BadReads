from enum import Enum
import json

import psycopg2
from sshtunnel import SSHTunnelForwarder

class SortOptions(Enum):
    BOOK_NAME = 1
    PUBLISHER = 2
    GENRE = 3
    RELEASED_YEAR = 4

CONFIG_FILENAME = "config.json"

class DataInteraction:
    __slots__ = ["__sshTunnel", "__connection", "__cursor", "current_user"]

    def __init__(self):
        # Get login credentials
        with open(CONFIG_FILENAME, 'r') as file:
            credentials = json.load(file)

        # Data for connection
        ssh_host = "starbug.cs.rit.edu"
        ssh_port = 22
        sql_host = "127.0.0.1"
        sql_port = 5432
        db = "p32001_13"
        username = credentials["username"]
        password = credentials["password"]
        
        # Establish connection via ssh tunneling
        self.__sshTunnel = SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_username = username,
            ssh_password = password,
            remote_bind_address = (sql_host, sql_port),
            local_bind_address = (sql_host, sql_port)
        )

        self.__sshTunnel.start()

        self.__connection = psycopg2.connect(
            host = self.__sshTunnel.local_bind_host,
            port = self.__sshTunnel.local_bind_port,
            database = db,
            user = username,
            password = password
        )
        self.__connection.autocommit = True
        
        self.__cursor = self.__connection.cursor()
        self.current_user = ""

    def login(self, username: str, password: str) -> bool:
        """
        Attempt to login using a given username and password
        -- This should record login date and time when it was accessed

        :param username: Username of account to access
        :param password: Password to try
        :return: If login was successful
        """

        query = f"""
                    SELECT * FROM users WHERE username = '{username}' AND password = '{password}';
                """

        self.__cursor.execute(query)

        if (self.__cursor.rowcount == 0):
            return False

        # If successfully logged the log in then current user should be set
        self.current_user = username
        return True

    def logout(self) -> bool:
        """
        If logged into account then logout

        :return: If logout successful
        """
        if self.current_user == "":
            return False

        self.current_user = ""
        return True

    def create_account(self, username: str, name: str, email: str, password: str) -> bool:
        """
        Create a new account
        -- Username must be unique
        -- Store date and time that account was created

        :param username: Username to create
        :param name: Name of the user
        :param email: Email address of user
        :param password: Password to set
        :return: If successful
        """

        query = f"""
                    INSERT INTO users (username, name, email, password) VALUES('{username}', '{name}', '{email}', '{password}');
                """

        self.__cursor.execute(query)

        if (self.__cursor.rowcount):
            return False

        # If successfully created the account then set username
        self.current_user = username
        return True

    def get_book_by_isbn(self, isbn: str) -> tuple[str, list[str], str, int, str, int] | None:
        """
        Get the book from an ISBN

        :param isbn: ISBN of the book to search for
        :return: Book details (tuple(title, authors, publishers, length, audience, rating)) or None if not found
        """
        query = f"""
                SELECT 
                    book.title as title,
                    STRING_AGG(DISTINCT authors_contrib.name, ', ') AS authors,
                    STRING_AGG(DISTINCT publishes_contrib.name, ', ') AS publishers,
                    book.length,
                    CASE 
                        WHEN book.audience = 0 THEN 'Kids'
                        WHEN book.audience = 1 THEN 'Teens'
                        WHEN book.audience = 2 THEN 'Adults'
                        ELSE 'Unknown'
                    END AS audience,
                    rates.rates AS rating
                FROM 
                    book
                JOIN
                    authors ON book.isbn = authors.isbn
                JOIN 
                    contributor AS authors_contrib ON authors.contributorID = authors_contrib.contributorID
                JOIN 
                    publishes ON book.isbn = publishes.isbn
                JOIN 
                    contributor AS publishes_contrib ON publishes.contributorID = publishes_contrib.contributorID
                JOIN 
                    rates ON book.isbn = rates.isbn
                WHERE 
                    rates.username = '{self.current_user}' AND
                    book.isbn = {isbn}
                GROUP BY
                    rates.rates, book.title, book.length, book.audience;
                """

        self.__cursor.execute(query)

        return self.__cursor.fetchone()

    def search_for_users(self, email: str) -> list[tuple]:
        """
        Find all user accounts by an email address

        :param email: Email address to search for
        :return: List of all user accounts
        """
        query = f"""
                    SELECT username FROM users WHERE email = '{email}';
                """

        self.__cursor.execute(query)
        rows = self.__cursor.fetchall()
        
        return rows

    def follow_user(self, followee: str) -> bool:
        """
        Current logged in user will follow followee
        -- Followee must exist

        :param followee: Username of person to follow
        :return: If successful
        """
        query = f"""
                    INSERT INTO follows (followerusername, followeeusername)
                    VALUES ('{self.current_user}', '{followee}');
                """

        self.__cursor.execute(query)

        return self.__cursor.rowcount != 0

    def unfollow_user(self, followee: str) -> bool:
        """
        Current logged in user will unfollow the followee
        -- Must be following the user

        :param followee: Person to unfollow by username
        :return: If successful
        """
        query = f"""
            DELETE from follows WHERE followerusername = '{self.current_user}'
            AND followeeusername = '{followee}';
        """

        self.__cursor.execute(query)

        return self.__cursor.rowcount != 0

    def list_followers(self) -> list[str]:
        """
        List all users that follow current user

        :return: List of usernames that follow current user
        """
        query = f"""
                    SELECT followerusername FROM follows WHERE followeeusername = '{self.current_user}';
                """

        self.__cursor.execute(query)
        rows = self.__cursor.fetchall()
        
        return rows

    def list_following(self) -> list[str]:
        """
        List all users that current user follows

        :return: Usernames of following
        """
        query = f"""
                    SELECT followeeusername FROM follows WHERE followerusername = '{self.current_user}';
                """

        self.__cursor.execute(query)
        rows = self.__cursor.fetchall()
        
        return rows

    def create_collection(self, collection_name: str, book_isbns: list[str]) -> bool:
        """
        Create a collection with this name and list of ISBNs (can be empty)
        -- Name must be unique, ISBNs must exist

        :param collection_name: Name of collection to create
        :param book_isbns: List of ISBNs for books to add to the collection
        :return: If successful
        """

        success = True

        # TODO: Is collection_id autoincremented?
        query = f"""
                    INSERT INTO collections (name)
                    VALUES ('{collection_name}');
                """
        
        self.__cursor.execute(query)

        query = f"""
                    SELECT collectionid from collections where name = '{collection_name}';
                """
        
        if self.__cursor.rowcount == 0:
            return False
        
        self.__cursor.execute(query)
        row = self.__cursor.fetchone()

        if row == None:
            return False
        
        collectionid = row[0]

        if (self.__cursor.rowcount != 0):
            for isbn in book_isbns:
                query = f"""
                    INSERT INTO belongs_to (collectionid, isbn)
                    VALUES ({collectionid}, '{isbn}');
                """
        
                self.__cursor.execute(query)

                if (self.__cursor.rowcount == 0):
                    success = False
        else:
            success = False
        
        return success

    def add_books_to_collection(self, collection_name: str, book_isbns: list[str]) -> bool:
        """
        Add a list of books to a collection
        -- Collection must exist and ISBNs must exist

        :param collection_name: Name of collection to add to
        :param book_isbns: List of books to add by ISBN
        :return: If all were added
        """
        success = True
        
        query = f"""
                    SELECT collectionid from collections where name = '{collection_name}';
                """
        self.__cursor.execute(query)
        row = self.__cursor.fetchone()

        if row == None:
            return False
        
        collectionid = row[0]

        for isbn in book_isbns:
            query = f"""
                INSERT INTO belongs_to (collectionid, isbn)
                VALUES ({collectionid}, '{isbn}');
            """
    
            self.__cursor.execute(query)

            if (self.__cursor.rowcount == 0):
                success = False

        return success

    def remove_books_from_collection(self, collection_name: str, book_isbns: list[str]) -> bool:
        """
        Remove a list of books from a collection
        -- Collection must exist and ISBNs must be in collection

        :param collection_name: Name of collection to remove from
        :param book_isbns: List of books to remove by ISBN
        :return: If all were removed
        """
        success = True
        
        query = f"""
                    SELECT collectionid from collections where name = '{collection_name}';
                """
        self.__cursor.execute(query)
        row = self.__cursor.fetchone()

        if row == None:
            return False
        
        collectionid = row[0]

        for isbn in book_isbns:
            query = f"""
                REMOVE FROM belongs_to
                WHERE collectionid = {collectionid}
                AND isbn = {isbn};
            """
    
            self.__cursor.execute(query)

            if (self.__cursor.rowcount == 0):
                success = False

        return success

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a given collection by name
        -- Collection must exist

        :param collection_name: Name of collection
        :return: If successful
        """

        query = f"""
                    DELETE FROM collections where name = '{collection_name}';
                """
        self.__cursor.execute(query)
        
        return self.__cursor.rowcount != 0

    def rename_collection(self, current_name: str, new_name: str) -> bool:
        """
        Rename a collection
        -- Collection must exist, new name must be unique and not equivalent to previous name

        :param current_name: Current name of collection.
        :param new_name: New name of collection
        :return: If successful
        """
        query = f"""
                    UPDATE collections SET name = {new_name}
                    WHERE name = {current_name};
                """
        self.__cursor.execute(query)
        
        return self.__cursor.rowcount != 0
    

    def list_collections(self) -> list[tuple[str, int, int]]:
        """
        Get a list of all collections
        -- Should be listed by name in ascending order

        :return: List of all collections as tuple(name, number of books, total page count)
        """
        query = f"""
                    SELECT collections.name, COUNT(book.isbn) as num_books,
                    SUM(book.length) from book JOIN belongs_to WHERE
                    GROUP BY book.isbn;
                """

        self.__cursor.execute(query)
        rows = self.__cursor.fetchall()
        
        return rows

    def get_collection_contents(self, collection_name: str) -> list[tuple[str, list[str], str, int, str, int]]:
        """
        Get a list of all books in a collection

        :param collection_name: Name of the collection to search
        :return: List of books as tuple(name, authors, publisher, length, audience, rating)
        """
        pass

    def search_for_book(self, search_method: str, val: str, sort_by: SortOptions, ascending: bool = True) -> list[tuple[str, list[str], str, int, str, int]]:
        """
        Search for a book by an attribute

        :param search_method: Either name, release_date, author, publisher, or genre
        :param val: Value to fill in the search method
        :param sort_by: Option to sort the resulting list by specified in the enum
        :param ascending: If we sort in ascending order or False for descending order
        :return: List of matching books in ascending alphabetical order tuple(name, authors, publisher, length,
                                                                                audience, rating)
        """
        pass

    def rate_book(self, book_isbn: str, rating: int) -> bool:
        """
        Rate a book
        -- Book must exist
        -- If book is already rated by this user then the rating is overwritten

        :param book_isbn: ISBN of the book to rate
        :param rating: Rating of that book [1, 5]
        :return: If successful
        """
        pass

    def read_book_by_isbn(self, book_isbn: str, start_page: int, end_page: int) -> bool:
        """
        Read a book by it's ISBN
        -- ISBN must exist

        :param book_isbn: ISBN of the book to read
        :param start_page: Start page for the reading session
        :param end_page: End page for the reading session
        :return: If book read successfully
        """
        pass

    def read_random_book_by_collection(self, collection_name: str, start_page: int, end_page: int) -> str:
        """
        Read a random book from a collection
        -- Collection name must exist

        :param collection_name: Name of collection to select form
        :param start_page: Start page for reading session
        :param end_page: End page for reading session
        :return: Name of the book that was read, empty string if failed
        """
        pass

    def shutdown(self):
        self.__cursor.close()
        self.__connection.close()
        self.__sshTunnel.close()