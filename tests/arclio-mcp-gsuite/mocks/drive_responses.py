"""
Mock response data for Google Drive API tests.
"""

# Mock response for files.list
FILES_LIST_RESPONSE = {
    "kind": "drive#fileList",
    "incompleteSearch": False,
    "files": [
        {
            "kind": "drive#file",
            "id": "file_id_1",
            "name": "Test Document 1",
            "mimeType": "application/vnd.google-apps.document",
            "modifiedTime": "2023-01-01T12:00:00.000Z",
            "size": "0",
            "webViewLink": "https://docs.google.com/document/d/file_id_1/edit?usp=drivesdk",
        },
        {
            "kind": "drive#file",
            "id": "file_id_2",
            "name": "Test Spreadsheet",
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "modifiedTime": "2023-01-02T12:00:00.000Z",
            "size": "0",
            "webViewLink": "https://docs.google.com/spreadsheets/d/file_id_2/edit?usp=drivesdk",
        },
        {
            "kind": "drive#file",
            "id": "file_id_3",
            "name": "example.txt",
            "mimeType": "text/plain",
            "modifiedTime": "2023-01-03T12:00:00.000Z",
            "size": "1024",
            "webViewLink": "https://drive.google.com/file/d/file_id_3/view?usp=drivesdk",
        },
    ],
}

# Mock response for files.get
FILE_GET_RESPONSE = {
    "kind": "drive#file",
    "id": "file_id_3",
    "name": "example.txt",
    "mimeType": "text/plain",
    "modifiedTime": "2023-01-03T12:00:00.000Z",
    "size": "1024",
    "webViewLink": "https://drive.google.com/file/d/file_id_3/view?usp=drivesdk",
}

# Mock plain text file content
TEXT_FILE_CONTENT = b"This is the content of a test file.\nIt has multiple lines.\nThe end."

# Mock response for Google Doc export
GOOGLE_DOC_CONTENT = b"# Google Doc Title\n\nThis is a paragraph in a Google Doc."

# Mock HTTP errors
HTTP_ERRORS = {
    "file_not_found": {
        "error": {
            "errors": [{"domain": "global", "reason": "notFound", "message": "File not found"}],
            "code": 404,
            "message": "File not found",
        }
    },
    "permission_denied": {
        "error": {
            "errors": [
                {
                    "domain": "global",
                    "reason": "forbidden",
                    "message": "Permission denied",
                }
            ],
            "code": 403,
            "message": "Permission denied",
        }
    },
}
