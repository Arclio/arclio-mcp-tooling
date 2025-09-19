import os


def get_openai_api_key():
    """
    Retrieves the OpenAI API key from the environment variable 'WEAVIATE_OPENAI_API_KEY'.
    Raises:
        ValueError: If the environment variable is not set.
    Returns:
        str: The OpenAI API key.
    """
    api_key = os.environ.get("WEAVIATE_OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Environment variable 'WEAVIATE_OPENAI_API_KEY' is not set.")
    return api_key
