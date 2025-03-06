class Interface:
    def __init__(self):
        self.current_user = None

    def login(self, username: str, password: str) -> bool:
        """
        Attempt to login using a given username and password

        :param username: Username of account to access
        :param password: Password to try
        :return: If login was successful
        """
        pass

    def logout(self) -> bool:
        """
        Log out of the account
        :return: If logout was successful (will fail if no one is logged in)
        """
        pass
