
from app.chunking import split_text_into_chunks


sample_text = (
    "Python is a programming language. "
    "FastAPI is used to build APIs. "
    "PostgreSQL stores application data. "
    "RAG retrieves relevant document information. "
    "Embeddings help compare semantic meaning."
)

chunks = split_text_into_chunks(
    text=sample_text,
    chunk_size=100,
    overlap=20,
)

print("Total chunks:", len(chunks))

for index, chunk in enumerate(chunks, start=1):
    print(f"\nChunk {index}:")
    print(chunk)
    print("Characters:", len(chunk))


# Test empty text
empty_result = split_text_into_chunks("")
print("\nEmpty text result:", empty_result)

# Test invalid settings
try:
    split_text_into_chunks("Hello world", chunk_size=100, overlap=100)
except ValueError as error:
    print("Validation test passed:", error)
