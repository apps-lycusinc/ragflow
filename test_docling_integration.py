#!/usr/bin/env python3
"""
Test script to demonstrate DocLing integration with RAGFlow
Shows the complete flow from API request to DocLing execution
"""

import requests
import time

# Configuration
RAGFLOW_BASE_URL = "http://localhost:9380"
API_TOKEN = "your_api_token_here"
DATASET_ID = "your_dataset_id_here"
DOCUMENT_ID = "your_document_id_here"

headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


def step_1_update_document_parser():
    """Step 1: Update document to use DocLing parser"""
    print("Step 1: Updating document to use DocLing parser...")

    url = f"{RAGFLOW_BASE_URL}/v1/datasets/{DATASET_ID}/documents/{DOCUMENT_ID}"
    data = {
        "chunk_method": "docling",
        "parser_config": {"chunk_token_num": 512, "delimiter": "\n!?。；！？"},
    }

    response = requests.put(url, headers=headers, json=data)
    print(f"Response Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        print("✓ Document successfully updated to use DocLing parser")
        return True
    else:
        print("✗ Failed to update document parser")
        return False


def step_2_start_parsing():
    """Step 2: Start parsing with DocLing"""
    print("\nStep 2: Starting DocLing parsing...")

    url = f"{RAGFLOW_BASE_URL}/v1/datasets/{DATASET_ID}/chunks"
    data = {"document_ids": [DOCUMENT_ID]}

    response = requests.post(url, headers=headers, json=data)
    print(f"Response Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        print("✓ DocLing parsing started successfully")
        return True
    else:
        print("✗ Failed to start DocLing parsing")
        return False


def step_3_monitor_progress():
    """Step 3: Monitor parsing progress"""
    print("\nStep 3: Monitoring parsing progress...")

    url = f"{RAGFLOW_BASE_URL}/v1/datasets/{DATASET_ID}/documents/{DOCUMENT_ID}"

    while True:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            doc_data = response.json()["data"]
            progress = doc_data.get("progress", 0)
            status = doc_data.get("run", "UNKNOWN")

            print(f"Progress: {progress:.1%} - Status: {status}")

            if status == "DONE":
                print("✓ DocLing parsing completed successfully!")
                break
            elif status == "FAIL":
                print("✗ DocLing parsing failed!")
                break
            elif status in ["UNSTART", "RUNNING"]:
                time.sleep(2)  # Wait 2 seconds before checking again
            else:
                break
        else:
            print("Failed to get document status")
            break


def step_4_verify_chunks():
    """Step 4: Verify generated chunks"""
    print("\nStep 4: Verifying generated chunks...")

    url = f"{RAGFLOW_BASE_URL}/v1/datasets/{DATASET_ID}/documents/{DOCUMENT_ID}/chunks"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        chunks_data = response.json()["data"]
        total_chunks = chunks_data.get("total", 0)
        chunks = chunks_data.get("chunks", [])

        print(f"✓ Total chunks generated: {total_chunks}")

        if chunks:
            print("\nSample chunks:")
            for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                print(f"\nChunk {i + 1}:")
                print(f"  ID: {chunk['id']}")
                print(f"  Content: {chunk['content'][:100]}...")
                if chunk.get("important_keywords"):
                    print(f"  Keywords: {chunk['important_keywords']}")

        return True
    else:
        print("✗ Failed to retrieve chunks")
        return False


def demonstrate_complete_flow():
    """Demonstrate the complete DocLing integration flow"""
    print("=" * 60)
    print("DocLing Integration Test for RAGFlow")
    print("=" * 60)

    print("\nFlow Overview:")
    print("1. Update document parser method to 'docling'")
    print("2. Start parsing via /chunks endpoint")
    print("3. Monitor parsing progress")
    print("4. Verify generated chunks")
    print("\n" + "=" * 60)

    # Execute each step
    if step_1_update_document_parser():
        if step_2_start_parsing():
            step_3_monitor_progress()
            step_4_verify_chunks()

    print("\n" + "=" * 60)
    print("Test completed!")


def show_integration_summary():
    """Show how the integration works internally"""
    print("\n" + "=" * 60)
    print("INTERNAL INTEGRATION FLOW")
    print("=" * 60)

    flow_steps = [
        ("API Request", "/v1/datasets/{id}/chunks", "doc.py:parse()"),
        ("Task Queue", "Redis Queue", "task_service.py:queue_tasks()"),
        ("Task Executor", "Background Worker", "task_executor.py:handle_task()"),
        (
            "Parser Selection",
            "FACTORY Dictionary",
            "FACTORY['docling'] = docling_parser",
        ),
        ("DocLing Execution", "DocLing Library", "docling_parser.py:chunk()"),
        ("Content Processing", "Text + Tables", "DoclingPdfParser.__call__()"),
        ("Chunking", "Token-based Split", "naive_merge() + tokenize_chunks()"),
        ("Storage", "Elasticsearch/Infinity", "docStoreConn.insert()"),
        ("Completion", "Status Update", "progress_callback(1.0)"),
    ]

    for i, (stage, component, code_location) in enumerate(flow_steps, 1):
        print(f"{i:2d}. {stage:<20} → {component:<20} → {code_location}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("DocLing Integration Test Script")
    print("Please update the configuration variables at the top of this script:")
    print(f"- RAGFLOW_BASE_URL: {RAGFLOW_BASE_URL}")
    print(f"- API_TOKEN: {API_TOKEN}")
    print(f"- DATASET_ID: {DATASET_ID}")
    print(f"- DOCUMENT_ID: {DOCUMENT_ID}")

    show_integration_summary()

    # Uncomment the next line to run the actual test
    # demonstrate_complete_flow()
