#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import logging
import re
from io import BytesIO
from timeit import default_timer as timer

from rag.nlp import naive_merge, rag_tokenizer, tokenize_chunks, tokenize_table


class DoclingPdfParser:
    """DocLing-based PDF parser for RAGFlow"""

    def __init__(self):
        try:
            # Import DocLing components
            from docling.document_converter import DocumentConverter
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import PdfFormatOption

            self.DocumentConverter = DocumentConverter
            self.InputFormat = InputFormat
            self.PdfPipelineOptions = PdfPipelineOptions
            self.PdfFormatOption = PdfFormatOption

        except ImportError as e:
            logging.error(f"DocLing not installed: {e}")
            raise ImportError("DocLing is required for this parser. Install with: pip install docling")

    def __call__(self, filename, binary=None, from_page=0, to_page=100000, callback=None):
        """Parse PDF using DocLing"""
        if callback:
            callback(0.1, "Starting DocLing PDF parsing...")

        try:
            # Configure DocLing pipeline
            pipeline_options = self.PdfPipelineOptions()
            pipeline_options.do_ocr = True  # Enable OCR
            pipeline_options.do_table_structure = True  # Enable table extraction

            # Create converter with PDF-specific options
            doc_converter = self.DocumentConverter(format_options={self.InputFormat.PDF: self.PdfFormatOption(pipeline_options=pipeline_options)})

            if callback:
                callback(0.3, "Converting document with DocLing...")

            # Convert document
            if binary:
                # Convert from binary data
                result = doc_converter.convert(BytesIO(binary))
            else:
                # Convert from file path
                result = doc_converter.convert(filename)

            if callback:
                callback(0.6, "Extracting content and structure...")

            # Extract content
            sections = []
            tables = []

            # Process the converted document
            document = result.document

            # Extract text content by pages
            for page_num, page in enumerate(document.pages):
                if page_num < from_page or page_num > to_page:
                    continue

                page_text = ""
                page_tables = []

                # Extract elements from the page
                for element in page.elements:
                    if element.element_type.name in [
                        "PARAGRAPH",
                        "TITLE",
                        "SECTION_HEADER",
                    ]:
                        # Text content
                        page_text += element.text + "\n"
                    elif element.element_type.name == "TABLE":
                        # Table content
                        table_data = {
                            "text": element.text,
                            "bbox": (
                                [
                                    element.bbox.l,
                                    element.bbox.t,
                                    element.bbox.r,
                                    element.bbox.b,
                                ]
                                if element.bbox
                                else None
                            ),
                            "page": page_num + 1,
                        }
                        page_tables.append(table_data)

                # Add page content to sections
                if page_text.strip():
                    sections.append((page_text.strip(), {"page_number": page_num + 1, "bbox": None}))

                # Add tables
                tables.extend(page_tables)

            if callback:
                callback(0.9, "DocLing parsing completed")

            return sections, tables

        except Exception as e:
            logging.error(f"DocLing parsing error: {e}")
            if callback:
                callback(-1, f"DocLing parsing failed: {str(e)}")
            raise


def chunk(
    filename,
    binary=None,
    from_page=0,
    to_page=100000,
    lang="Chinese",
    callback=None,
    **kwargs,
):
    """
    DocLing-based chunking method for PDFs.
    This method uses DocLing to parse PDFs and extract structured content.
    """

    is_english = lang.lower() == "english"
    parser_config = kwargs.get("parser_config", {"chunk_token_num": 512, "delimiter": "\n!?。；！？"})

    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename)),
    }
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])

    res = []

    if re.search(r"\.pdf$", filename, re.IGNORECASE):
        if callback:
            callback(0.1, "Starting DocLing PDF processing...")

        # Use DocLing parser
        docling_parser = DoclingPdfParser()
        sections, tables = docling_parser(
            filename,
            binary=binary,
            from_page=from_page,
            to_page=to_page,
            callback=callback,
        )

        # Process tables
        res = tokenize_table(tables, doc, is_english)

        if callback:
            callback(0.8, "Processing text sections...")

        # Process text sections
        st = timer()

        # Merge sections into chunks
        text_chunks = []
        for section_text, metadata in sections:
            text_chunks.append(section_text)

        # Apply naive merging strategy
        chunks = naive_merge(
            text_chunks,
            int(parser_config.get("chunk_token_num", 128)),
            parser_config.get("delimiter", "\n!?。；！？"),
        )

        # Tokenize chunks
        res.extend(tokenize_chunks(chunks, doc, is_english))

        logging.info("DocLing chunk processing ({}): {}".format(filename, timer() - st))

        if callback:
            callback(1.0, "DocLing processing completed")

        return res

    else:
        raise ValueError("DocLing parser only supports PDF files")
