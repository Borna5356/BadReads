from enum import Enum
import json
import random

import psycopg2
from sshtunnel import SSHTunnelForwarder

class SortOptions(Enum):
    BOOK_NAME = 1
    PUBLISHER = 2
    GENRE = 3
    RELEASED_YEAR = 4

class SearchMethods(Enum):
    BOOK_NAME = 1
    RELEASE_DATE = 2
    AUTHOR = 3
    PUBLISHER = 4
    GENRE = 5
    

CONFIG_FILENAME = "../config.json"

class DataInteraction:
    __slots__ = ["__sshTunnel", "__connection", "__cursor", "__current_user"]

    def __init__(self):
        try:
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
            self.__current_user = None
        except Exception as e:
            self.shutdown()
            raise Exception(e)

    def login(self, username: str, password: str) -> bool:
        """
        Attempt to login using a given username and password
        -- This should record login date and time when it was accessed

        :param username: Username of account to access
        :param password: Password to try
        :return: If login was successful
        """

        try:
            query = f"""
                        UPDATE users SET lastaccessed = CURRENT_TIMESTAMP
                        WHERE username = '{username}' AND password = '{password}';
                    """

            self.__cursor.execute(query)

            if (self.__cursor.rowcount == 0):
                return False

            # If successfully logged the log in then current user should be set
            self.__current_user = username
            return True
        except:
            return False

    def logout(self) -> bool:
        """
        If logged into account then logout

        :return: If logout successful
        """
        if self.__current_user == None:
            return False

        self.__current_user = None
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

        try:
            query = f"""
                        INSERT INTO users
                            (username, name, email, password, datecreated, lastaccessed)
                        VALUES
                            ('{username}', '{name}', '{email}', '{password}',
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                    """

            self.__cursor.execute(query)

            if (self.__cursor.rowcount == 0):
                return False

            # If successfully created the account then set username
            self.__current_user = username
            return True
        except:
            return False

    def get_book_by_isbn(self, isbn: str) -> tuple[str, list[str], str, int, str, int] | None:
        """
        Get the book from an ISBN

        :param isbn: ISBN of the book to search for
        :return: Book details (tuple(title, authors, publishers, length, audience, rating)) or None if not found
        """

        try:
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
                    LEFT JOIN 
                        rates ON book.isbn = rates.isbn AND rates.username = '{self.__current_user}'
                    WHERE
                        book.isbn = '{isbn}'
                    GROUP BY
                        rates.rates, book.title, book.length, book.audience;
                    """

            self.__cursor.execute(query)

            return self.__cursor.fetchone()
        except:
            return False

    def search_for_users(self, email: str) -> list[tuple]:
        """
        Find all user accounts by an email address

        :param email: Email address to search for
        :return: List of all user accounts
        """

        try:
            query = f"""
                        SELECT username FROM users WHERE email = '{email}';
                    """

            self.__cursor.execute(query)
            rows = self.__cursor.fetchall()
            
            return rows
        except:
            return False

    def follow_user(self, followee: str) -> bool:
        """
        Current logged in user will follow followee
        -- Followee must exist

        :param followee: Username of person to follow
        :return: If successful
        """

        try:
            query = f"""
                        INSERT INTO follows (followerusername, followeeusername)
                        VALUES ('{self.__current_user}', '{followee}');
                    """

            self.__cursor.execute(query)

            return self.__cursor.rowcount != 0
        except:
            return False

    def unfollow_user(self, followee: str) -> bool:
        """
        Current logged in user will unfollow the followee
        -- Must be following the user

        :param followee: Person to unfollow by username
        :return: If successful
        """
        try:
            query = f"""
                DELETE from follows WHERE followerusername = '{self.__current_user}'
                AND followeeusername = '{followee}';
            """

            self.__cursor.execute(query)

            return self.__cursor.rowcount != 0
        except:
            return False

    def list_followers(self, username: str = None) -> list[str]:
        """
        List all users that follow user with given username

        :param username: Username of the user to query, if None use current user
        :return: List of usernames that follow current user
        """
        if (username == None):
            username = self.__current_user
            
        try:
            query = f"""
                        SELECT followerusername FROM follows WHERE followeeusername = '{username}';
                    """

            self.__cursor.execute(query)
            rows = self.__cursor.fetchall()
            
            return rows
        except:
            return False

    def list_following(self, username: str = None) -> list[str]:
        """
        List all users that the given user follows

        :param username: Username of the user to query, if None use current user
        :return: Usernames of following
        """
        if (username == None):
            username = self.__current_user

        try:
            query = f"""
                        SELECT followeeusername FROM follows WHERE followerusername = '{username}';
                    """

            self.__cursor.execute(query)
            rows = self.__cursor.fetchall()
            
            return rows
        except:
            return False

    def create_collection(self, collection_name: str, book_isbns: list[str]) -> bool:
        """
        Create a collection with this name and list of ISBNs (can be empty)
        -- Name must be unique, ISBNs must exist

        :param collection_name: Name of collection to create
        :param book_isbns: List of ISBNs for books to add to the collection
        :return: If successful
        """

        try:
            success = True

            query = f"""
                        INSERT INTO collections (name)
                        VALUES ('{collection_name}')
                        RETURNING collectionid;
                    """
            
            self.__cursor.execute(query)

            if (self.__cursor.rowcount == 0):
                return False

            row = self.__cursor.fetchone()            
            collectionid = row[0]

            query = f"""
                        INSERT INTO creates (username, collectionid)
                        VALUES ('{self.__current_user}', {collectionid});
                    """
            
            self.__cursor.execute(query)

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
        except:
            return False

    def add_books_to_collection(self, collection_name: str, book_isbns: list[str]) -> bool:
        """
        Add a list of books to a collection
        -- Collection must exist and ISBNs must exist

        :param collection_name: Name of collection to add to
        :param book_isbns: List of books to add by ISBN
        :return: If all were added
        """
        try:
            query = f"""SELECT creates.collectionid
                        FROM
                            creates
                        JOIN
                            collections ON creates.collectionid = collections.collectionid
                        WHERE
                            creates.username = '{self.__current_user}'
                            AND collections.name = '{collection_name}';
                    """
            self.__cursor.execute(query)
            
            if self.__cursor.rowcount == 0:
                return False
            
            success = True
            
            row = self.__cursor.fetchone()            
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
        except:
            return False

    def remove_books_from_collection(self, collection_name: str, book_isbns: list[str]) -> bool:
        """
        Remove a list of books from a collection
        -- Collection must exist and ISBNs must be in collection

        :param collection_name: Name of collection to remove from
        :param book_isbns: List of books to remove by ISBN
        :return: If all were removed
        """

        try:
            query = f"""SELECT creates.collectionid
                        FROM
                            creates
                        JOIN
                            collections ON creates.collectionid = collections.collectionid
                        WHERE
                            creates.username = '{self.__current_user}'
                            AND collections.name = '{collection_name}';
                    """
            self.__cursor.execute(query)
            
            if self.__cursor.rowcount == 0:
                return False
            
            success = True
            
            row = self.__cursor.fetchone()            
            collectionid = row[0]

            for isbn in book_isbns:
                query = f"""
                    DELETE FROM belongs_to
                    WHERE collectionid = {collectionid}
                    AND isbn = '{isbn}';
                """
        
                self.__cursor.execute(query)

                if (self.__cursor.rowcount == 0):
                    success = False

            return success
        except:
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a given collection by name
        -- Collection must exist

        :param collection_name: Name of collection
        :return: If successful
        """

        try:
            query = f"""SELECT creates.collectionid
                        FROM
                            creates
                        JOIN
                            collections ON creates.collectionid = collections.collectionid
                        WHERE
                            creates.username = '{self.__current_user}'
                            AND collections.name = '{collection_name}';
                    """
            self.__cursor.execute(query)
            
            if self.__cursor.rowcount == 0:
                return False
            
            row = self.__cursor.fetchone()            
            collectionid = row[0]
        
            query = f"""
                        DELETE FROM belongs_to WHERE collectionid = {collectionid};
                    """

            self.__cursor.execute(query)
            
            query = f"""
                        DELETE FROM creates WHERE username = '{self.__current_user}'
                        AND collectionid = {collectionid};
                    """
            self.__cursor.execute(query)
            
            if self.__cursor.rowcount == 0:
                return False
            
            query = f"""
                        DELETE FROM collections where collectionid = {collectionid};
                    """

            self.__cursor.execute(query)
            
            return self.__cursor.rowcount != 0
        except:
            return False

    def rename_collection(self, current_name: str, new_name: str) -> bool:
        """
        Rename a collection
        -- Collection must exist, new name must be unique and not equivalent to previous name

        :param current_name: Current name of collection.
        :param new_name: New name of collection
        :return: If successful
        """
        try:
            query = f"""SELECT creates.username
                        FROM
                            creates
                        JOIN
                            collections ON creates.collectionid = collections.collectionid
                        WHERE
                            creates.username = '{self.__current_user}';
                    """
            self.__cursor.execute(query)
            
            if self.__cursor.rowcount == 0:
                return False
            
            query = f"""
                        UPDATE collections SET name = '{new_name}'
                        WHERE name = '{current_name}';
                    """
            self.__cursor.execute(query)
            
            return self.__cursor.rowcount != 0
        except:
            return False
    

    def list_collections(self, username: str = None) -> list[tuple[str, int, int]]:
        """
        Get a list of all collections
        -- Should be listed by name in ascending order

        :param username: Username of the user to query, if None use current user
        :return: List of all collections as tuple(name, number of books, total page count)
        """
        if (username == None):
            username = self.__current_user
        
        try:
            query = f"""
                        SELECT collections.name, COUNT(belongs_to.isbn) AS num_books,
                        SUM(book.length) AS total_page_count
                        FROM
                            creates
                        JOIN
                            collections ON creates.collectionid = collections.collectionid
                        LEFT JOIN
                            belongs_to ON collections.collectionid = belongs_to.collectionid
                        LEFT JOIN
                            book ON book.isbn = belongs_to.isbn
                        WHERE
                            creates.username = '{username}'
                        GROUP BY collections.name;
                    """

            self.__cursor.execute(query)
            rows = self.__cursor.fetchall()
            
            return rows
        except:
            return False

    def get_collection_contents(self, collection_name: str, username: str = None) -> list[tuple[str, list[str], str, int, str, int]]:
        """
        Get a list of all books in a collection

        :param collection_name: Name of the collection to search
        :param username: Username of the user to query, if None use current user
        :return: List of books as tuple(name, authors, publisher, length, audience, rating, isbn)
        """
        if (username == None):
            username = self.__current_user
        
        try:            
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
                        rates.rates AS rating,
                        book.isbn
                    FROM 
                        collections
                    JOIN
                        creates ON creates.collectionid = collections.collectionid
                    JOIN
                        belongs_to ON collections.collectionid = belongs_to.collectionid
                    JOIN
                        book ON book.isbn = belongs_to.isbn
                    JOIN
                        authors ON book.isbn = authors.isbn
                    JOIN 
                        contributor AS authors_contrib ON authors.contributorID = authors_contrib.contributorID
                    JOIN 
                        publishes ON book.isbn = publishes.isbn
                    JOIN 
                        contributor AS publishes_contrib ON publishes.contributorID = publishes_contrib.contributorID
                    LEFT JOIN 
                        rates ON book.isbn = rates.isbn AND rates.username = '{username}'
                    WHERE
                        collections.name = '{collection_name}' AND creates.username = '{username}'
                    GROUP BY
                        rates.rates, book.title, book.length, book.audience, book.isbn;
                    """

            self.__cursor.execute(query)
            rows = self.__cursor.fetchall()
            
            return rows
        except:
            return False

    def search_for_book(self, search_method: str, val: str, sort_by: SortOptions, ascending: bool = True) -> list[tuple[str, list[str], str, int, str, int]]:
        """
        Search for a book by an attribute

        :param search_method: Either name, release_date, author, publisher, or genre
        :param val: Value to fill in the search method
        :param sort_by: Option to sort the resulting list by specified in the enum
        :param ascending: If we sort in ascending order or False for descending order
        :return: List of matching books in ascending alphabetical order tuple(name, authors, publisher, length,
                                                                                audience, rating, isbn)
        """
        try:
            search_method_str = None

            if (search_method == SearchMethods.BOOK_NAME):
                search_method_str = f"book.title ILIKE '%{val}%'"
            elif (search_method == SearchMethods.RELEASE_DATE):
                search_method_str = f"book.releasedate = '{val}'"
            elif (search_method == SearchMethods.AUTHOR):
                search_method_str = f"authors_contrib.name = '{val}'"
            elif (search_method == SearchMethods.PUBLISHER):
                search_method_str = f"publishes_contrib.name = '{val}'"
            else:
                search_method_str = f"genre.name = '{val}'"

            sort_by_str = None

            if (sort_by == SortOptions.PUBLISHER):
                sort_by_str = "publishes_contrib.name"
            elif (sort_by == SortOptions.GENRE):
                sort_by_str = "genre.name"
            elif (sort_by == SortOptions.RELEASED_YEAR):
                sort_by_str = "EXTRACT(YEAR FROM book.releasedate)"
            else:
                sort_by_str = "book.title"

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
                        rates.rates AS rating,
                        book.isbn
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
                    LEFT JOIN 
                        rates ON book.isbn = rates.isbn AND rates.username = '{self.__current_user}'
                    LEFT JOIN
                        category ON category.isbn = book.isbn
                    LEFT JOIN
                        genre ON genre.genreid = category.genreid
                    WHERE
                        {search_method_str}
                    GROUP BY
                        rates.rates, book.title, book.length, book.audience, book.releasedate,
                        publishes_contrib.name, genre.name, book.releasedate, book.isbn
                    ORDER BY
                        {sort_by_str}
                        {"ASC" if ascending else "DESC"};
                    """

            self.__cursor.execute(query)

            rows = self.__cursor.fetchall()

            return rows
        except:
            return False


    def rate_book(self, book_isbn: str, rating: int) -> bool:
        """
        Rate a book
        -- Book must exist
        -- If book is already rated by this user then the rating is overwritten

        :param book_isbn: ISBN of the book to rate
        :param rating: Rating of that book [1, 5]
        :return: If successful
        """
        try:
            # Check if book exists
            query = f"""
                        SELECT * FROM book WHERE isbn = '{book_isbn}';
                    """
            self.__cursor.execute(query)

            if self.__cursor.rowcount == 0:
                return False
            
            query = f"""
                        SELECT * FROM rates WHERE username = '{self.__current_user}'
                        AND isbn = '{book_isbn}';
                    """
            self.__cursor.execute(query)
            
            if (self.__cursor.rowcount == 0):
                query = f"""
                            INSERT INTO rates (username, isbn, rates)
                            VALUES ('{self.__current_user}', '{book_isbn}', {rating});
                        """
                self.__cursor.execute(query)
            else:
                query = f"""
                            UPDATE rates SET rates = {rating}
                            WHERE username = '{self.__current_user}'
                            AND isbn = '{book_isbn}';
                        """
                self.__cursor.execute(query)
            
            return self.__cursor.rowcount != 0
        except:
            return False

    def read_book_by_isbn(self, book_isbn: str, start_page: int, end_page: int) -> bool:
        """
        Read a book by it's ISBN
        -- ISBN must exist

        :param book_isbn: ISBN of the book to read
        :param start_page: Start page for the reading session
        :param end_page: End page for the reading session
        :return: If book read successfully
        """
        try:
            numMins = random.randint(15, 300)

            query = f"""
                        INSERT INTO reads (username, isbn, starttime, endtime, startpage, endpage)
                        VALUES
                        (
                            '{self.__current_user}',
                            '{book_isbn}',
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP + INTERVAL '{numMins} minutes',
                            {start_page},
                            {end_page}
                        );
                    """
                
            self.__cursor.execute(query)

            return self.__cursor.rowcount != 0
        except:
            return False

    def read_random_book_by_collection(self, collection_name: str, start_page: int, end_page: int) -> str:
        """
        Read a random book from a collection
        -- Collection name must exist

        :param collection_name: Name of collection to select from
        :param start_page: Start page for reading session
        :param end_page: End page for reading session
        :return: Name of the book that was read, empty string if failed
        """
        try:
            query = f"""
                        SELECT book.isbn, book.title
                        FROM
                            collections
                        JOIN
                            creates on creates.collectionid = collections.collectionid
                        JOIN
                            belongs_to ON collections.collectionid = belongs_to.collectionid
                        JOIN
                            book ON book.isbn = belongs_to.isbn
                        WHERE collections.name = '{collection_name}'
                            AND creates.username = '{self.__current_user}'
                        GROUP BY book.isbn, book.title
                        ORDER BY RANDOM()
                        LIMIT 1;
                    """
            
            self.__cursor.execute(query)
            
            if (self.__cursor.rowcount == 0):
                return ""
            
            book_info = self.__cursor.fetchone()
            book_isbn = book_info[0]
            book_name = book_info[1]

            numMins = random.randint(15, 300)

            query = f"""
                        INSERT INTO reads (username, isbn, starttime, endtime, startpage, endpage)
                        VALUES
                        (
                            '{self.__current_user}',
                            '{book_isbn}',
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP + INTERVAL '{numMins} minutes',
                            {start_page},
                            {end_page}
                        );
                    """
                
            self.__cursor.execute(query)

            if self.__cursor.rowcount == 0:
                return ""
            
            return book_name
        except:
            return False

    def get_top_books(self, username: str = None) -> list[tuple[str, list[str], str, int, str, int]]:
        """
        Get top 10 books for the given user

        :param username: Username of the user to query, if None use current user
        :return: Top books
        """
        if (username == None):
            username = self.__current_user
        
        try:
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
                            reads
                        JOIN
                            book on book.isbn = reads.isbn
                        JOIN
                            authors ON book.isbn = authors.isbn
                        JOIN
                            contributor AS authors_contrib ON authors.contributorID = authors_contrib.contributorID
                        JOIN
                            publishes ON book.isbn = publishes.isbn
                        JOIN
                            contributor AS publishes_contrib ON publishes.contributorID = publishes_contrib.contributorID
                        LEFT JOIN
                            rates ON book.isbn = rates.isbn AND rates.username = '{username}'
                        WHERE
                            reads.username = '{username}'
                        GROUP BY
                            rates.rates, book.title, book.length, book.audience, reads.endpage - reads.startpage
                        ORDER BY SUM(reads.endpage - reads.startpage) DESC
                        LIMIT 10;
                    """

            self.__cursor.execute(query)
            rows = self.__cursor.fetchall()
            
            return rows
        except:
            return False

    def get_top_recent_books(self, source_user: str = None) -> list[tuple[str, list[str], str, int, str, int]]:
        """
        Get top 20 books among source_user's followers, or among all users if source_user none
        -- over the past 90 days

        :param source_user: User to search followers, none if all users
        :return: Books
        """
        # TODO Implement
        pass

    def get_top_new_releases(self) -> list[tuple[str, list[str], str, int, str, int]]:
        """
        Get the top 5 new releases among all users

        :return: Top 5 new released books
        """
        # TODO Implement
        pass

    def get_recommendations(self) -> list[tuple[str, list[str], str, int, str, int]]:
        """
        Get recommendations for books to read for the current user

        :return: Books recommended by the system
        """
        # TODO Implement
        pass

    def shutdown(self):
        try:
            self.__cursor.close()
        except:
            pass
        try:
            self.__connection.close()
        except:
            pass
        try:
            self.__sshTunnel.close()
        except:
            pass

    def get_current_user(self):
        return self.__current_user