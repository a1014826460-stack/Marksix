Python API validation script for the frontend lives at:

`frontend/test/test_frontend_api_validation.py`

Requirements:

```bash
pip install pytest requests
```

Run after the frontend server is up:

```bash
cd frontend
pytest test/test_frontend_api_validation.py -q
```

Or run directly:

```bash
python test/test_frontend_api_validation.py --base-url http://127.0.0.1:3000
```

Optional environment variables:

```bash
FRONTEND_API_TEST_BASE_URL=http://127.0.0.1:3000
FRONTEND_API_TEST_TIMEOUT=5
```

Output:

- A JSON report is written to `frontend/test/test_results_<timestamp>.json`
- The report includes interface name, request parameters, status code, response body, response time, pass/fail, and error message
