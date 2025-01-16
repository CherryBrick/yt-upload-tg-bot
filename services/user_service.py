import logging
from contextlib import contextmanager

import psycopg2

from services.db import DBConfig


class UserService:
    def __init__(self, config: DBConfig, admin_chat_id: int):
        self.config = config
        self.admin_chat_id = admin_chat_id
        self.logger = logging.getLogger(__name__)
        self._init_db()

    def _init_db(self) -> None:
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
        Проверяет, является ли пользователь администратором.
        """
        return user_id == self.admin_chat_id

    def is_approved_user(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь одобренным.
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
        Проверяет, ожидает ли пользователь предоставления доступа.
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
        Добавляет пользователя в таблицу users с флагами по умолчанию (approved = FALSE, pending = FALSE).
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
        Обновляет флаги пользователя, устанавливая approved = FALSE и pending = TRUE.
        Предварительно архивирует текущий статус.
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
        Обновляет флаги пользователя, устанавливая approved = TRUE и pending = FALSE.
        Предварительно архивирует текущий статус.
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
        Обновляет флаги пользователя, устанавливая approved = FALSE и pending = FALSE.
        Предварительно архивирует текущий статус.
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
        Возвращает список ожидающих пользователей с учетом пагинации.

        :param page: Номер страницы (начиная с 1)
        :param page_size: Количество пользователей на странице
        :return: Кортеж из списка user_id и общего количества пользователей
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
