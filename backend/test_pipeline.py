from pipeline_executor import execute_pipeline

pipeline = {
    "blocks": [
        {"block_type": "input_source", "block_id": 1, "csv_source": "imdb_top_1000.csv"},
        {"block_type": "process", "block_id": 2, "pre_req": [1], "prompt": "clean missing values"},
        {"block_type": "process", "block_id": 3, "pre_req": [2], "prompt": "aggregate movies by genre"},
        {"block_type": "destination", "block_id": 4, "pre_req": [3], "email_dest": "user@example.com"}
    ]
}

result = execute_pipeline(pipeline)