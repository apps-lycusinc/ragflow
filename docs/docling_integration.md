# DocLing Integration for RAGFlow

This document describes how to integrate and use DocLing for PDF parsing in RAGFlow.

## Overview

DocLing is a powerful document parsing library that provides advanced PDF processing capabilities including:
- Advanced OCR (Optical Character Recognition)
- Table structure extraction
- Layout analysis
- Multi-language support

## Installation

1. Install DocLing:
```bash
./install_docling.sh
```

Or manually:
```bash
pip install docling
```

## Usage

### 1. Via API

Update a document to use DocLing parser:

```bash
curl -X PUT 'http://localhost:9380/v1/datasets/<dataset_id>/documents/<document_id>' \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{
       "chunk_method": "docling",
       "parser_config": {
         "chunk_token_num": 512,
         "delimiter": "\n!?。；！？"
       }
     }'
```

Start parsing:
```bash
curl -X POST 'http://localhost:9380/v1/datasets/<dataset_id>/chunks' \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{
       "document_ids": ["<document_id>"]
     }'
```

### 2. Via Python SDK

```python
from ragflow_sdk import RAGFlow

rag = RAGFlow(api_key="your_api_key", base_url="http://localhost:9380")

# Get dataset and document
dataset = rag.get_dataset("dataset_id")
document = dataset.get_document("document_id")

# Update to use DocLing parser
document.update({
    "chunk_method": "docling",
    "parser_config": {
        "chunk_token_num": 512,
        "delimiter": "\n!?。；！？"
    }
})

# Start parsing
dataset.parse_documents([document.id])
```

## Configuration Options

The DocLing parser supports the following configuration options:

- `chunk_token_num`: Maximum number of tokens per chunk (default: 512)
- `delimiter`: Text delimiters for chunking (default: "\n!?。；！？")

## Features

### Advanced PDF Processing
- **OCR**: Automatically extracts text from scanned PDFs and images
- **Table Extraction**: Identifies and extracts structured table data
- **Layout Analysis**: Recognizes document structure (headers, paragraphs, etc.)
- **Multi-format Support**: Handles various PDF types and qualities

### Integration Benefits
- **Accuracy**: Improved text extraction compared to basic PDF parsers
- **Structure Preservation**: Maintains document hierarchy and formatting
- **Robustness**: Handles complex PDF layouts and embedded content
- **Performance**: Optimized for large document processing

## Troubleshooting

### Common Issues

1. **Import Error**: "docling module not found"
   - Solution: Run `pip install docling` or use the installation script

2. **Memory Issues**: Large PDF processing fails
   - Solution: Adjust `task_page_size` in parser configuration
   - Increase system memory allocation

3. **OCR Performance**: Slow processing on scanned documents
   - Solution: DocLing uses advanced OCR which may take longer but provides better accuracy

### Logs and Monitoring

DocLing parser logs can be found in the standard RAGFlow logs:
- Check parsing progress via the API status endpoints
- Monitor task execution in the task executor logs

## API Endpoints

The DocLing parser integrates with existing RAGFlow endpoints:

- `PUT /datasets/{dataset_id}/documents/{document_id}` - Update parser method
- `POST /datasets/{dataset_id}/chunks` - Start parsing
- `GET /datasets/{dataset_id}/documents/{document_id}/chunks` - View results

## Performance Considerations

1. **Initial Setup**: First-time DocLing usage may require model downloads
2. **Processing Time**: Advanced features may increase processing time
3. **Memory Usage**: Complex PDFs require more memory
4. **Concurrent Processing**: Consider system resources when processing multiple documents

## Migration from Other Parsers

To migrate existing documents from other parsers to DocLing:

1. Update the document's `chunk_method` to `"docling"`
2. Optionally update `parser_config` settings
3. Re-parse the document using the chunks endpoint
4. Previous chunks will be replaced with DocLing-generated ones
