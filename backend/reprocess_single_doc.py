from app.services.document_processor import chunk_text, _chunk_string

# Test _chunk_string first
test_text = "This is a test. " * 200  # ~3200 characters
print(f"Test text length: {len(test_text)}")

result = _chunk_string(test_text, chunk_size=800, overlap=100)
print(f"_chunk_string returned: {len(result)} chunks")

if len(result) > 0:
    print(f"First chunk length: {len(result[0])}")

# Now test chunk_text
chunks = chunk_text(test_text)
print(f"\nchunk_text returned: {len(chunks)} chunks")

if len(chunks) > 0:
    print(f"First chunk: {type(chunks[0])}, length: {len(chunks[0][0])}")