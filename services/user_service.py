import logging
from contextlib import contextmanager

import psycopg2

from services.db import DBConfig


class UserService:
    def __init__(self, config: DBConfig, admin_chat_id: int):
        """
        Initialize the UserService with database configuration and admin settings.
        
        Parameters:
            config (DBConfig): Database configuration parameters for establishing connections.
            admin_chat_id (int): Unique identifier for the administrative user or chat.
        
        Behavior:
            - Sets up database configuration
            - Configures logging for the service
            - Initializes database schema by calling _init_db()
        """
        self.config = config
        self.admin_chat_id = admin_chat_id
        self.logger = logging.getLogger(__name__)
        self._init_db()

    def _init_db(self) -> None:
        """
        Initialize the database schema for user management.
        
        This method establishes the database tables and PostgreSQL function required for tracking user statuses:
        - Creates 'users' table to store current user status
        - Creates 'users_hist' table to archive user status changes
        - Defines a PostgreSQL function 'update_user_status' to manage status updates and history tracking
        - Performs test case insertions to validate database schema functionality
        
        The method uses a database connection context manager to execute SQL commands and commits the transaction.
        
        Note:
            - Automatically creates tables if they do not exist
            - Drops and recreates the 'update_user_status' function to ensure latest implementation
            - Includes test cases for inserting and updating a test user record
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        approved BOOLEAN DEFAULT FALSE,
                        pending BOOLEAN DEFAULT FALSE,
                        row_added_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS users_hist (
                        row_id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        approved BOOLEAN,
                        pending BOOLEAN,
                        row_added_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        row_changed_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    );
                   DROP FUNCTION IF EXISTS update_user_status(bigint, boolean, boolean);
                   CREATE OR REPLACE FUNCTION update_user_status(
                        new_user_id BIGINT,
                        new_approved BOOLEAN,
                        new_pending BOOLEAN
                    ) RETURNS VOID AS $$
                    DECLARE
                        current_timestamp_val TIMESTAMP WITH TIME ZONE := CURRENT_TIMESTAMP;
                    BEGIN
                        -- Добавление строки в историческую таблицу
                        INSERT INTO users_hist (user_id, approved, pending, row_added_timestamp, row_changed_timestamp)
                        SELECT user_id, approved, pending, row_added_timestamp, current_timestamp_val
                        FROM users
                        WHERE user_id = new_user_id;
                    
                        -- Обновление статуса пользователя
                        UPDATE users
                        SET approved = new_approved,
                            pending = new_pending,
                            row_added_timestamp = current_timestamp_val
                        WHERE user_id = new_user_id;
                    END;
                    $$ LANGUAGE plpgsql;
                            
                    -- Тест кейс
                    INSERT INTO users (user_id) 
                    VALUES (0) 
                    ON CONFLICT (user_id) DO NOTHING;
                            
                    SELECT update_user_status(0, TRUE, TRUE);
                            
                    SELECT user_id, approved, pending, row_added_timestamp
                    FROM users
                    WHERE user_id = 0;
                            
                    SELECT user_id, approved, pending, row_added_timestamp, row_changed_timestamp
                    FROM users_hist
                    WHERE user_id = 0;
                    
                    DELETE
                    FROM users_hist
                    WHERE user_id = 0;
                            
                    DELETE
                    FROM users
                    WHERE user_id = 0;
                """)
                conn.commit()

    @contextmanager
    def get_connection(self):
        """
        Provides a context manager for establishing a database connection.
        
        This method creates a PostgreSQL database connection using the configuration parameters
        provided during the UserService initialization. It ensures that the database connection
        is properly closed after use, even if an exception occurs.
        
        Yields:
            psycopg2.connection: An active database connection to the configured PostgreSQL database.
        
        Note:
            - Uses context manager protocol to automatically manage connection lifecycle
            - Closes the connection in the `finally` block to guarantee resource cleanup
        """
        conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password
        )
        try:
            yield conn
        finally:
            conn.close()

    def is_admin(self, user_id: int) -> bool:
        """
        Check if the given user is an admin based on their user ID.
        
        Args:
            user_id (int): The unique identifier of the user to check.
        
        Returns:
            bool: True if the user is an admin (matches the admin chat ID), False otherwise.
        """
        return user_id == self.admin_chat_id

    def is_approved_user(self, user_id: int) -> bool:
        """
        Check if a user is approved in the system.
        
        Parameters:
            user_id (int): The unique identifier of the user to check for approval status.
        
        Returns:
            bool: True if the user is approved, False otherwise. Returns False if no user record is found.
        
        Raises:
            psycopg2.Error: If a database error occurs during the query execution.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT approved FROM users WHERE user_id = %s",
                    (user_id,)
                )
                result = cur.fetchone()
                return result[0] if result else False

    def is_pending_user(self, user_id: int) -> bool:
        """
        Check if a user is currently in a pending status awaiting access approval.
        
        Parameters:
            user_id (int): The unique identifier of the user to check.
        
        Returns:
            bool: True if the user is pending, False otherwise.
        
        Raises:
            psycopg2.Error: If a database error occurs during the query.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pending FROM users WHERE user_id = %s",
                    (user_id,)
                )
                result = cur.fetchone()
                return result[0] if result else False

    def add_user(self, user_id):
        """
        Add a new user to the database with default status flags.
        
        This method attempts to insert a user into the 'users' table. If the user already exists,
        the insertion is silently ignored due to the ON CONFLICT clause.
        
        Parameters:
            user_id (int): The unique identifier of the user to be added.
        
        Raises:
            Exception: If an error occurs during the database insertion process.
        
        Notes:
            - Default flags are set to approved = FALSE, pending = FALSE
            - Uses an upsert strategy with ON CONFLICT DO NOTHING
            - Logs any errors encountered during user insertion
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO users (user_id) 
                        VALUES (%s) 
                        ON CONFLICT (user_id) DO NOTHING;
                        """,
                        (user_id,)
                    )
                    conn.commit()
                except Exception as e:
                    self.logger.error(f"Failed to add user {user_id}: {e}")
                    raise

    def set_pending(self, user_id):
        """
        Set a user's status to pending in the database.
        
        Marks the specified user as pending by updating their status flags and archiving the previous status.
        This method changes the user's 'approved' flag to False and 'pending' flag to True.
        
        Parameters:
            user_id (int): The unique identifier of the user to be set as pending.
        
        Raises:
            Exception: If there is an error updating the user's status in the database.
            The specific error is logged with details for debugging.
        
        Side Effects:
            - Updates the user's status in the 'users' table
            - Archives the previous user status in 'users_hist' table
            - Commits the database transaction if successful
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        SELECT update_user_status(%s, %s, %s);
                        """,
                        (user_id, False, True)
                    )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to set user {user_id} as pending: {e}")
                    raise

    def set_approved(self, user_id):
        """
        Update the status of a user to approved, archiving the previous status.
        
        This method sets the user's approved flag to TRUE and pending flag to FALSE
        in the database, while preserving the previous status in the users history table.
        
        Parameters:
            user_id (int): The unique identifier of the user to be approved.
        
        Raises:
            Exception: If there is an error during the database update process.
            The specific error is logged with details for debugging.
        
        Side Effects:
            - Updates the user's status in the 'users' table
            - Archives the previous user status in the 'users_hist' table
            - Commits the database transaction if successful
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        SELECT update_user_status(%s, %s, %s);
                        """,
                        (user_id, True, False)
                    )
                    conn.commit()
                except Exception as e:
                    self.logger.error(f"Failed to approve user {user_id}: {e}")
                    raise

    def remove_pending(self, user_id):
        """
        Remove a user's pending status by updating their approval flags.
        
        This method updates the user's status in the database, setting both 'approved' and 'pending' flags to False.
        It uses the custom PostgreSQL function 'update_user_status' to archive the previous status before updating.
        
        Parameters:
            user_id (int): The unique identifier of the user whose pending status will be removed.
        
        Raises:
            Exception: If there is an error updating the user's status in the database.
            The specific error is logged with details about the failure.
        
        Side Effects:
            - Updates the 'users' table in the database
            - Archives the previous user status in the 'users_hist' table
            - Logs an error message if the status update fails
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        SELECT update_user_status(%s, %s, %s);
                        """,
                        (user_id, False, False)
                    )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to remove pending status for user {user_id}: {e}")
                    raise

    def get_pending_users(self, page: int, page_size: int):
        """
        Retrieves a paginated list of pending users from the database.
        
        This method queries the users table to fetch pending users with pagination support,
        allowing controlled retrieval of users waiting for approval.
        
        Parameters:
            page (int): The page number to retrieve, starting from 1. 
                        Determines the offset of users to fetch.
            page_size (int): Number of users to return per page.
        
        Returns:
            tuple: A tuple containing two elements:
                - List[int]: User IDs of pending users on the specified page
                - int: Total number of pending users in the database
        
        Raises:
            psycopg2.Error: If a database error occurs during query execution
        
        Example:
            # Retrieve first page with 10 users per page
            pending_users, total = user_service.get_pending_users(1, 10)
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                offset = (page - 1) * page_size
                cur.execute(
                    """
                    SELECT user_id 
                    FROM users 
                    WHERE pending = TRUE 
                    ORDER BY row_added_timestamp 
                    LIMIT %s OFFSET %s
                    """,
                    (page_size, offset)
                )
                pending_users = [row[0] for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT COUNT(*) 
                    FROM users 
                    WHERE pending = TRUE
                    """
                )
                total_count = cur.fetchone()[0]

                return pending_users, total_count
