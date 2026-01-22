# Complete DocLing Integration Flow in RAGFlow

## Flow Diagram

```
User Request → API Endpoint → Task Queue → Task Executor → DocLing Parser → Chunks Storage
```

## Detailed Step-by-Step Flow

### Step 1: User API Request
```bash
POST /v1/datasets/{dataset_id}/chunks
{
  "document_ids": ["doc_123"]
}
```

### Step 2: API Endpoint Processing
**File**: `/api/apps/sdk/doc.py` - Line 758

```python
@manager.route("/datasets/<dataset_id>/chunks", methods=["POST"])
@token_required
def parse(tenant_id, dataset_id):
    # 1. Validate access permissions
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}.")

    # 2. Extract document IDs from request
    req = request.json
    doc_list = req.get("document_ids")

    # 3. Process each document
    for id in doc_list:
        doc = DocumentService.query(id=id, kb_id=dataset_id)

        # 4. Update document status to "RUNNING"
        info = {"run": "1", "progress": 0, "progress_msg": "", "chunk_num": 0, "token_num": 0}
        DocumentService.update_by_id(id, info)

        # 5. Get document details and storage location
        e, doc = DocumentService.get_by_id(id)
        doc = doc.to_dict()
        doc["tenant_id"] = tenant_id
        bucket, name = File2DocumentService.get_storage_address(doc_id=doc["id"])

        # 6. Queue the parsing task
        queue_tasks(doc, bucket, name, 0)  # ← This queues the task for processing
```

### Step 3: Task Queueing
**File**: `/api/db/services/task_service.py` - Line 318

```python
def queue_tasks(doc: dict, bucket: str, name: str, priority: int):
    # 1. Create task structure
    def new_task():
        return {"id": get_uuid(), "doc_id": doc["id"], "progress": 0.0, "from_page": 0, "to_page": 100000000}

    parse_task_array = []

    # 2. Handle PDF documents (DocLing case)
    if doc["type"] == FileType.PDF.value:
        # Get PDF page count and create page-based tasks
        file_bin = STORAGE_IMPL.get(bucket, name)
        pages = PdfParser.total_page_number(doc["name"], file_bin)
        page_size = doc["parser_config"].get("task_page_size") or 12

        # For DocLing, we might process the entire document at once
        if doc["parser_id"] == "docling":
            page_size = 10 ** 9  # Process all pages together

        # Create task for each page range
        for p in range(0, pages, page_size):
            task = new_task()
            task["from_page"] = p
            task["to_page"] = min(p + page_size, pages)
            parse_task_array.append(task)

    # 3. Add tasks to Redis queue
    for task in parse_task_array:
        task.update({
            "tenant_id": doc.get("tenant_id"),
            "parser_id": doc["parser_id"],  # ← "docling" for our case
            "parser_config": doc["parser_config"],
            "name": doc["name"],
            "size": doc["size"],
            "kb_id": doc["kb_id"],
            "location": bucket + "/" + name
        })

        # Add to Redis task queue
        REDIS_CONN.queue_product(get_svr_queue_name(), task, priority)
```

### Step 4: Task Executor Processing
**File**: `/rag/svr/task_executor.py` - Line 658

```python
async def handle_task():
    # 1. Consume task from Redis queue
    redis_msg, task = await collect()

    # 2. Process the task
    await do_handle_task(task)

async def do_handle_task(task):
    # Key task parameters
    task_id = task["id"]
    task_parser_id = task["parser_id"]  # ← "docling"
    task_from_page = task["from_page"]
    task_to_page = task["to_page"]

    # 3. Build chunks using the appropriate parser
    chunks = await build_chunks(task, progress_callback)
```

### Step 5: Parser Selection and Execution
**File**: `/rag/svr/task_executor.py` - Line 244

```python
async def build_chunks(task, progress_callback):
    # 1. Get the chunker from FACTORY based on parser_id
    chunker = FACTORY[task["parser_id"].lower()]  # ← Gets docling_parser module

    # 2. Download file from storage
    bucket, name = File2DocumentService.get_storage_address(doc_id=task["doc_id"])
    binary = await get_storage_binary(bucket, name)

    # 3. Call the chunker's chunk method
    async with chunk_limiter:
        cks = await trio.to_thread.run_sync(
            lambda: chunker.chunk(
                task["name"],
                binary=binary,
                from_page=task["from_page"],
                to_page=task["to_page"],
                lang=task["language"],
                callback=progress_callback,
                kb_id=task["kb_id"],
                parser_config=task["parser_config"],
                tenant_id=task["tenant_id"]
            )
        )
```

### Step 6: DocLing Parser Execution
**File**: `/rag/app/docling_parser.py` - Our new file

```python
def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """
    This is the main entry point that gets called by the task executor
    """

    # 1. Setup parser configuration
    parser_config = kwargs.get("parser_config", {
        "chunk_token_num": 512,
        "delimiter": "\n!?。；！？"
    })

    # 2. Initialize document metadata
    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))
    }

    # 3. Check if it's a PDF file
    if re.search(r"\.pdf$", filename, re.IGNORECASE):
        callback(0.1, "Starting DocLing PDF processing...")

        # 4. Create DocLing parser instance
        docling_parser = DoclingPdfParser()

        # 5. Parse the PDF using DocLing
        sections, tables = docling_parser(
            filename,
            binary=binary,     # ← PDF file content from storage
            from_page=from_page,
            to_page=to_page,
            callback=callback
        )

        # 6. Process extracted tables
        res = tokenize_table(tables, doc, is_english)

        # 7. Process text sections and create chunks
        text_chunks = [section_text for section_text, metadata in sections]
        chunks = naive_merge(
            text_chunks,
            int(parser_config.get("chunk_token_num", 128)),
            parser_config.get("delimiter", "\n!?。；！？")
        )

        # 8. Tokenize chunks and return
        res.extend(tokenize_chunks(chunks, doc, is_english))
        return res  # ← Returns processed chunks back to task executor

class DoclingPdfParser:
    def __call__(self, filename, binary=None, from_page=0, to_page=100000, callback=None):
        """
        This method does the actual DocLing processing
        """

        # 1. Import DocLing components
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import PdfFormatOption

        # 2. Configure DocLing pipeline
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True

        # 3. Create converter
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        # 4. Convert the document
        if binary:
            result = doc_converter.convert(BytesIO(binary))  # ← Process PDF from memory
        else:
            result = doc_converter.convert(filename)  # ← Process PDF from file

        # 5. Extract content
        document = result.document
        sections = []
        tables = []

        # 6. Process each page
        for page_num, page in enumerate(document.pages):
            if page_num < from_page or page_num > to_page:
                continue

            # Extract text and tables from page elements
            for element in page.elements:
                if element.element_type.name in ['PARAGRAPH', 'TITLE', 'SECTION_HEADER']:
                    sections.append((element.text, {'page_number': page_num + 1}))
                elif element.element_type.name == 'TABLE':
                    tables.append({
                        'text': element.text,
                        'page': page_num + 1
                    })

        return sections, tables  # ← Return extracted content
```

### Step 7: Chunk Storage
**File**: `/rag/svr/task_executor.py` - Line 625

```python
# Back in do_handle_task after chunks are created...

# 1. Generate embeddings for chunks
token_count, vector_size = await embedding(chunks, embedding_model, task_parser_config, progress_callback)

# 2. Store chunks in document store (Elasticsearch/Infinity)
for b in range(0, len(chunks), DOC_BULK_SIZE):
    doc_store_result = await trio.to_thread.run_sync(
        lambda: settings.docStoreConn.insert(
            chunks[b:b + DOC_BULK_SIZE],
            search.index_name(task_tenant_id),
            task_dataset_id
        )
    )

# 3. Update document statistics
DocumentService.increment_chunk_num(task_doc_id, task_dataset_id, token_count, chunk_count, 0)

# 4. Update progress to complete
progress_callback(prog=1.0, msg="Indexing done. Task done.")
```

## Complete Example Flow

### Input:
```bash
curl -X POST 'http://localhost:9380/v1/datasets/kb_123/chunks' \
     -H 'Authorization: Bearer token_456' \
     -H 'Content-Type: application/json' \
     -d '{"document_ids": ["doc_789"]}'
```

### Execution Path:
1. **API** (`doc.py:parse`) validates request and queues task
2. **Task Service** (`task_service.py:queue_tasks`) creates Redis task with `parser_id: "docling"`
3. **Task Executor** (`task_executor.py:handle_task`) consumes task from Redis
4. **Build Chunks** (`task_executor.py:build_chunks`) gets `docling_parser` from `FACTORY`
5. **DocLing Parser** (`docling_parser.py:chunk`) processes PDF with DocLing
6. **DocLing Library** extracts text, tables, and structure from PDF
7. **Chunking** splits content into manageable pieces
8. **Storage** saves chunks to Elasticsearch/Infinity with embeddings
9. **Response** returns success status to user

### Key Configuration Points:
- Document must have `parser_id: "docling"` (set via PUT `/documents/{id}` endpoint)
- DocLing library must be installed (`pip install docling`)
- Parser config can control chunking behavior (`chunk_token_num`, `delimiter`)

This flow ensures DocLing is seamlessly integrated into RAGFlow's existing parsing pipeline while maintaining all the framework's features like progress tracking, error handling, and chunk storage.
