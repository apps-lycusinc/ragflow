# DocLing Integration: Complete Call Flow

## 🚀 How DocLing Gets Called in RAGFlow

When a user hits `/datasets/<dataset_id>/chunks`, here's the **exact execution path**:

### 1. **API Entry Point**
```python
# File: /api/apps/sdk/doc.py - Line 758
@manager.route("/datasets/<dataset_id>/chunks", methods=["POST"])
@token_required
def parse(tenant_id, dataset_id):
    # User sends: {"document_ids": ["doc_123"]}

    for doc_id in document_ids:
        # Get document from database
        e, doc = DocumentService.get_by_id(doc_id)
        doc_dict = doc.to_dict()
        doc_dict["tenant_id"] = tenant_id

        # Queue task for processing
        queue_tasks(doc_dict, bucket, name, 0)  # ← Task queued here
```

### 2. **Task Queueing**
```python
# File: /api/db/services/task_service.py - Line 318
def queue_tasks(doc: dict, bucket: str, name: str, priority: int):
    task = {
        "id": get_uuid(),
        "doc_id": doc["id"],
        "parser_id": doc["parser_id"],  # ← "docling" from document config
        "parser_config": doc["parser_config"],
        "tenant_id": doc["tenant_id"],
        "name": doc["name"],
        # ... other task data
    }

    # Add to Redis queue
    REDIS_CONN.queue_product(get_svr_queue_name(), task, priority)
```

### 3. **Task Executor Pickup**
```python
# File: /rag/svr/task_executor.py - Line 670
async def handle_task():
    # Consume from Redis
    redis_msg, task = await collect()

    # Process task
    await do_handle_task(task)

async def do_handle_task(task):
    # Build chunks using appropriate parser
    chunks = await build_chunks(task, progress_callback)  # ← Parser selection happens here
```

### 4. **Parser Selection**
```python
# File: /rag/svr/task_executor.py - Line 244
async def build_chunks(task, progress_callback):
    # Get chunker from FACTORY dictionary
    chunker = FACTORY[task["parser_id"].lower()]  # ← Gets docling_parser module

    # FACTORY = {
    #     "naive": naive,
    #     "paper": paper,
    #     "docling": docling_parser,  ← Our integration
    #     ...
    # }

    # Download file from storage
    binary = await get_storage_binary(bucket, name)

    # Call the chunker
    cks = await trio.to_thread.run_sync(
        lambda: chunker.chunk(  # ← docling_parser.chunk() called here
            task["name"],
            binary=binary,
            from_page=task["from_page"],
            to_page=task["to_page"],
            lang=task["language"],
            callback=progress_callback,
            **kwargs
        )
    )
```

### 5. **DocLing Parser Execution**
```python
# File: /rag/app/docling_parser.py - Our new file
def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """Main entry point called by task executor"""

    if re.search(r"\.pdf$", filename, re.IGNORECASE):
        # Initialize DocLing parser
        docling_parser = DoclingPdfParser()

        # Parse PDF with DocLing
        sections, tables = docling_parser(
            filename,
            binary=binary,  # ← PDF content from storage
            from_page=from_page,
            to_page=to_page,
            callback=callback
        )

        # Process results into chunks
        return process_sections_and_tables(sections, tables, parser_config)

class DoclingPdfParser:
    def __call__(self, filename, binary=None, **kwargs):
        """Actual DocLing processing happens here"""

        # Import DocLing
        from docling.document_converter import DocumentConverter
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        # Configure DocLing
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True

        doc_converter = DocumentConverter(...)

        # Convert PDF
        if binary:
            result = doc_converter.convert(BytesIO(binary))  # ← DocLing processes PDF
        else:
            result = doc_converter.convert(filename)

        # Extract content
        document = result.document
        sections = []
        tables = []

        for page in document.pages:
            for element in page.elements:
                if element.element_type.name == 'PARAGRAPH':
                    sections.append((element.text, metadata))
                elif element.element_type.name == 'TABLE':
                    tables.append(element_to_table_dict(element))

        return sections, tables  # ← Extracted content returned
```

### 6. **Chunk Processing & Storage**
```python
# Back in task_executor.py after chunks are created
async def do_handle_task(task):
    # ... DocLing processing completed, chunks created ...

    # Generate embeddings
    token_count, vector_size = await embedding(chunks, embedding_model, ...)

    # Store in document store (Elasticsearch/Infinity)
    for batch in chunks_batches:
        settings.docStoreConn.insert(batch, index_name, dataset_id)

    # Update document statistics
    DocumentService.increment_chunk_num(doc_id, dataset_id, token_count, chunk_count)

    # Mark as complete
    progress_callback(1.0, "DocLing processing completed")
```

## 🔄 Complete Request Flow Example

```bash
# 1. User Request
POST /v1/datasets/kb_123/chunks
{
  "document_ids": ["doc_456"]
}

# 2. Document Check (must have parser_id="docling")
SELECT * FROM documents WHERE id='doc_456' AND parser_id='docling';

# 3. Task Creation
{
  "id": "task_789",
  "doc_id": "doc_456",
  "parser_id": "docling",  ← Key field that triggers DocLing
  "parser_config": {"chunk_token_num": 512},
  "tenant_id": "tenant_123"
}

# 4. Parser Selection
FACTORY["docling"] → docling_parser module

# 5. DocLing Execution
docling_parser.chunk(
  filename="document.pdf",
  binary=<pdf_content>,
  parser_config={"chunk_token_num": 512}
) → Returns processed chunks

# 6. Storage
INSERT INTO elasticsearch/infinity INDEX chunks_tenant_123_kb_123
```

## 🎯 Key Integration Points

1. **Parser Registration**: `FACTORY["docling"] = docling_parser` in `task_executor.py`
2. **Document Config**: Document must have `parser_id="docling"` (set via PUT endpoint)
3. **Validation**: "docling" added to `valid_chunk_method` in `doc.py`
4. **Dependencies**: DocLing library must be installed (`pip install docling`)

## 🧪 Testing the Integration

```python
# 1. Set document parser to DocLing
PUT /v1/datasets/{dataset_id}/documents/{document_id}
{"chunk_method": "docling"}

# 2. Start parsing
POST /v1/datasets/{dataset_id}/chunks
{"document_ids": ["{document_id}"]}

# 3. Monitor progress
GET /v1/datasets/{dataset_id}/documents/{document_id}
# Watch progress field: 0.0 → 1.0

# 4. View results
GET /v1/datasets/{dataset_id}/documents/{document_id}/chunks
# See DocLing-processed chunks
```

## 🎉 That's It!

The integration is **seamless** - DocLing plugs into RAGFlow's existing parsing pipeline without breaking any existing functionality. Users just need to:

1. Install DocLing: `pip install docling`
2. Set chunk method: `"chunk_method": "docling"`
3. Parse documents: `POST /chunks`

DocLing will automatically handle PDF parsing with advanced OCR, table extraction, and layout analysis!
