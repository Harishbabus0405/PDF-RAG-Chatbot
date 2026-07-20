import streamlit as st


class ChatMemoryManager:
    """Manages chat history in Streamlit session state."""

    MESSAGES_KEY = "messages"

    @classmethod
    def initialize(cls) -> None:
        if cls.MESSAGES_KEY not in st.session_state:
            st.session_state[cls.MESSAGES_KEY] = []

    @classmethod
    def get_messages(cls) -> list[dict]:
        cls.initialize()
        return st.session_state[cls.MESSAGES_KEY]

    @classmethod
    def add_user_message(cls, content: str) -> None:
        cls._add_message("user", content)

    @classmethod
    def add_assistant_message(
        cls,
        content: str,
        citations: list[dict] | None = None
    ) -> None:
        cls._add_message("assistant", content, citations or [])

    @classmethod
    def clear(cls) -> None:
        st.session_state[cls.MESSAGES_KEY] = []

    @classmethod
    def build_history_text(cls, max_messages: int = 10) -> str:
        messages = cls.get_messages()[-max_messages:]
        history_lines = []

        for message in messages:
            role = "User" if message["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {message['content']}")

        return "\n".join(history_lines)

    @classmethod
    def _add_message(
        cls,
        role: str,
        content: str,
        citations: list[dict] | None = None
    ) -> None:
        cls.initialize()
        st.session_state[cls.MESSAGES_KEY].append(
            {
                "role": role,
                "content": content,
                "citations": citations or [],
            }
        )
