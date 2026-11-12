#Loads the embedding model into memory once (@lru_cache) and gives us a simple .embed_text("...") function that returns a Python list[float] of 384 numbers ready for PostgreSQL.
from functools import lru_cache
from fastembed import TextEmbedding


class EmbeddingService:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):#One of the top-performing small open-source embedding models in the world.
        # Loads the lightweight 384-dimension embedding model once
        self.model = TextEmbedding(model_name=model_name)

    def embed_text(self, text: str) -> list[float]:
        # Convert a single string (like a search query or document chunk) into 384 floats
        embeddings = list(self.model.embed([text])) #rocesses lists of texts and returns a NumPy array of decimal numbers.
        return embeddings[0].tolist()#Converts that NumPy array into a standard Python list of 384 floats ([0.012, -0.043, ...]) so SQLAlchemy and pgvector can save it directly into PostgreSQL.


@lru_cache # @lru_cache ensures Python only loads the model once and reuses it for every request instead of reloading it from disk every time!
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()