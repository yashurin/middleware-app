import asyncio
from io import BytesIO, StringIO
from pathlib import Path as FilePath
from typing import Any, Callable, Dict, List, Optional, TypeVar

import httpx
import pandas as pd
from jsonschema import ValidationError, validate

from app.crud import DataRepository
from app.errors import AuthenticationError
from app.log import logger
from app.schemas import ResponseData, RetryConfig

# Type for the authentication callable
T = TypeVar("T")
AuthCallable = Callable[[str, Dict[str, Any]], Dict[str, Any]]


async def fetch_data_from_api(
    source_url: str,
    params: Optional[Dict] = None,
    auth_handler: Optional[AuthCallable] = None,
    retry_config: Optional[RetryConfig] = None,
    timeout: Optional[float] = 30.0,
) -> List[Dict]:
    """
    Asynchronously fetch data from a REST API with support for retries, authentication, and error handling.

    This function attempts to retrieve data from the specified API endpoint using HTTP GET requests.
    It implements an exponential backoff retry mechanism for handling transient failures and
    automatically normalizes common API response formats.

    Args:
        source_url (str): The URL of the API endpoint to fetch data from.
        params (Optional[Dict], optional): Query parameters to include in the request. Defaults to None.
        auth_handler (Optional[AuthCallable], optional): Callback function that handles authentication.
            Should accept and modify a request. Defaults to None (authentication not implemented yet).
        retry_config (Optional[RetryConfig], optional): Configuration object for retry behavior.
            If not provided, default RetryConfig settings will be used.
        timeout (Optional[float], optional): Request timeout in seconds. Defaults to 30.0.

    Returns:
        List[Dict]: A list of dictionaries containing the API response data. The function attempts to
        extract data from common response structures (list, dict with 'data', 'results', or 'items' keys).
        If the structure doesn't match any expected format, it returns the response wrapped in a list.

    Raises:
        No exceptions are raised directly by this function. All exceptions are caught and
        returned as ResponseData objects with appropriate error information.

    Note:
        - The function automatically handles different API response formats:
          * Lists are returned directly
          * Dictionaries with 'data', 'results', or 'items' keys have their values extracted
          * Other formats are wrapped in a list
        - Authentication logic is not yet implemented (marked as TO DO in the code)
        - Uses exponential backoff for retries with configurable parameters via RetryConfig
        - Retries are only attempted for status codes specified in retry_config.retry_status_codes
        - Network errors (connection, timeout) are always considered retryable

    Examples:
        ```python
        # Basic usage
        data = await fetch_data_from_api("https://api.example.com/v1/resources")

        # With query parameters
        params = {"limit": 100, "offset": 0}
        data = await fetch_data_from_api("https://api.example.com/v1/search", params=params)

        # With custom retry configuration
        retry_config = RetryConfig(max_attempts=5, base_delay=1.0)
        data = await fetch_data_from_api(
            "https://api.example.com/v1/data",
            retry_config=retry_config,
            timeout=60.0
        )
        ```
    """
    if retry_config is None:
        retry_config = RetryConfig()

    # TO DO: add authentication logic

    attempt = 0
    last_exception = None

    while attempt < retry_config.max_attempts:
        attempt += 1
        delay = min(
            retry_config.base_delay * (retry_config.backoff_factor ** (attempt - 1)),
            retry_config.max_delay,
        )

        try:
            logger.debug(
                f"Attempt {attempt}/{retry_config.max_attempts} to fetch data from {source_url}"
            )

            async with httpx.AsyncClient() as client:
                response = await client.get(source_url, params=params)
                response.raise_for_status()
                data = response.json()

                # Handle different API response formats if necessary
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "data" in data:
                    return data["data"]
                elif isinstance(data, dict) and "results" in data:
                    return data["results"]
                elif isinstance(data, dict) and "items" in data:
                    return data["items"]
                else:
                    # If the structure doesn't match any expected format, return as is
                    # and let the caller handle it
                    return [data]

        except httpx.HTTPStatusError as e:
            last_exception = e
            status_code = e.response.status_code

            # Log the error
            logger.warning(
                f"Request failed with status {status_code}, "
                f"attempt {attempt}/{retry_config.max_attempts}"
            )

            # If not a retryable status code, raise immediately
            if status_code not in retry_config.retry_status_codes:
                return ResponseData(
                    success=False,
                    status_code=status_code,
                    content=e.response.content
                    if hasattr(e.response, "content")
                    else None,
                    error_message=f"HTTP error {status_code}: {str(e)}",
                )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            # Network-related errors
            last_exception = e
            logger.warning(
                f"Request failed due to connection error: {str(e)}, "
                f"attempt {attempt}/{retry_config.max_attempts}"
            )

        except Exception as e:
            # Unexpected errors
            last_exception = e
            logger.error(f"Unexpected error during request: {str(e)}")
            return ResponseData(
                success=False,
                status_code=500,
                content=None,
                error_message=f"Unexpected error: {str(e)}",
            )

            # If this wasn't the last attempt, wait before retrying
        if attempt < retry_config.max_attempts:
            logger.info(f"Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)

            # If we've exhausted all retries
        error_message = f"Maximum retry attempts ({retry_config.max_attempts}) exceeded"
        logger.error(error_message)

        return ResponseData(
            success=False,
            status_code=last_exception.response.status_code
            if hasattr(last_exception, "response")
            else 0,
            content=None,
            error_message=error_message,
        )


async def process_records(
    records: List[Dict], schema: Dict, schema_config: Dict, repo: DataRepository
) -> Dict:
    """Process records through validation, transformation, storage and forwarding."""
    results = []
    validation_errors = []
    errors = []

    for record in records:
        logger.info(f"Working with the record {record} of the type {type(record)}")
        try:
            validate(instance=record, schema=schema)
            transformed_data = schema_config["transform"](record)
            db_item = await repo.create(
                {
                    "schema_name": schema_config["schema_name"],
                    "raw_data": record,
                    "transformed_data": transformed_data,
                    "forwarded_to": schema_config["destination_url"],
                },
                refresh_fields=["id"],
            )
            await forward_data(transformed_data, schema_config["destination_url"])
            results.append({"id": db_item.id, "status": "success"})
        except ValidationError as ve:
            validation_errors.append(
                {"record": record, "status": "validation error", "detail": ve.message}
            )
        except Exception as e:
            errors.append({"record": record, "status": "error", "detail": str(e)})

    return {
        "results": results,
        "validation_errors": validation_errors,
        "errors": errors,
    }


async def forward_data(
    data: Dict[str, Any],
    url: str,
    auth_handler: Optional[AuthCallable] = None,
    retry_config: Optional[RetryConfig] = None,
    timeout: Optional[float] = 30.0,
    headers: Optional[Dict[str, str]] = None,
) -> ResponseData:
    """
    Forward data to a specified URL with authentication, retry logic, and error handling.

    This function sends the provided data to the specified URL using an HTTP POST request.
    It includes support for custom authentication, automatic retries on failure,
    and comprehensive error handling.

    Args:
        data: Dictionary containing the data to be forwarded
        url: Target URL to which the data will be forwarded
        auth_handler: Optional callable that handles authentication for the request
                     The function should accept the URL and data, and return headers or
                     modified data as needed for authentication
        retry_config: Optional configuration for retry behavior
        timeout: Optional timeout in seconds for the HTTP request
        headers: Optional dictionary of HTTP headers to include in the request

    Returns:
        ResponseData: Object containing success status, status code, and response content

    Raises:
        AuthenticationError: If authentication fails
        MaxRetriesExceededError: If maximum retry attempts are exceeded
        ForwardError: For other forwarding errors
        ValueError: If input parameters are invalid

    Example:
        ```python
        def my_auth_handler(url, data):
            return {"Authorization": f"Bearer {get_token()}"}

        try:
            result = await forward_data(
                data={"key": "value"},
                url="https://api.example.com/endpoint",
                auth_handler=my_auth_handler
            )
            print(f"Success: {result.success}, Status: {result.status_code}")
        except ForwardError as e:
            print(f"Error: {e.message}")
        ```
    """
    if retry_config is None:
        retry_config = RetryConfig()

    if not url:
        raise ValueError("URL cannot be empty")

    # Initialize headers if not provided
    request_headers = headers or {}

    # Apply authentication if handler is provided
    if auth_handler:
        try:
            auth_result = auth_handler(url, data)
            # Auth handler might return headers or modified data
            if isinstance(auth_result, dict):
                if any(isinstance(v, str) for v in auth_result.values()):
                    # Treat as headers
                    request_headers.update(auth_result)
                else:
                    # Treat as modified data
                    data = auth_result
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationError(
                message="Failed to authenticate request", original_exception=e
            )

    attempt = 0
    last_exception = None

    while attempt < retry_config.max_attempts:
        attempt += 1
        delay = min(
            retry_config.base_delay * (retry_config.backoff_factor ** (attempt - 1)),
            retry_config.max_delay,
        )

        try:
            logger.debug(
                f"Attempt {attempt}/{retry_config.max_attempts} to forward data to {url}"
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=data, headers=request_headers, timeout=timeout
                )

                # If we get a status code that indicates retry, raise to trigger retry logic
                if response.status_code in retry_config.retry_status_codes:
                    response.raise_for_status()  # This will raise an HTTPStatusError

                # For other non-2xx responses, raise for error handling
                if response.status_code >= 400:
                    response.raise_for_status()

                # Success case
                return ResponseData(
                    success=True,
                    status_code=response.status_code,
                    content=response.json() if response.content else None,
                )

        except httpx.HTTPStatusError as e:
            last_exception = e
            status_code = e.response.status_code

            # Log the error
            logger.warning(
                f"Request failed with status {status_code}, "
                f"attempt {attempt}/{retry_config.max_attempts}"
            )

            # If not a retryable status code, raise immediately
            if status_code not in retry_config.retry_status_codes:
                return ResponseData(
                    success=False,
                    status_code=status_code,
                    content=e.response.content
                    if hasattr(e.response, "content")
                    else None,
                    error_message=f"HTTP error {status_code}: {str(e)}",
                )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            # Network-related errors
            last_exception = e
            logger.warning(
                f"Request failed due to connection error: {str(e)}, "
                f"attempt {attempt}/{retry_config.max_attempts}"
            )

        except Exception as e:
            # Unexpected errors
            last_exception = e
            logger.error(f"Unexpected error during request: {str(e)}")
            return ResponseData(
                success=False,
                status_code=500,
                content=None,
                error_message=f"Unexpected error: {str(e)}",
            )

        # If this wasn't the last attempt, wait before retrying
        if attempt < retry_config.max_attempts:
            logger.info(f"Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)

    # If we've exhausted all retries
    error_message = f"Maximum retry attempts ({retry_config.max_attempts}) exceeded"
    logger.error(error_message)

    return ResponseData(
        success=False,
        status_code=last_exception.response.status_code
        if hasattr(last_exception, "response")
        else 0,
        content=None,
        error_message=error_message,
    )


async def process_file(filename: str, contents: bytes) -> List[Dict]:
    """
    Process uploaded file (CSV or Excel) and convert to a list of dictionaries.

    Args:
        filename: Original filename with extension
        contents: Raw file contents as bytes

    Returns:
        List of dictionaries, each representing a row from the file

    Raises:
        ValueError: If file format is unsupported or processing fails
    """
    file_extension = FilePath(filename).suffix.lower()

    if file_extension in [".csv", ".txt"]:
        logger.info("Process CSV file")
        try:
            text_content = contents.decode("utf-8")
            df = pd.read_csv(
                StringIO(text_content),
                dtype=str,  # Read all columns as strings initially
                na_values=["", "NA", "N/A", "null", "NULL", "None", "NONE"],
                keep_default_na=True,
            )
        except Exception as e:
            raise ValueError(f"Error processing CSV file: {str(e)}")

    elif file_extension in [".xlsx", ".xls", ".xlsm"]:
        logger.info("Process Excel file")
        try:
            df = pd.read_excel(
                BytesIO(contents),
                dtype=str,  # Read all columns as strings initially
                engine="openpyxl" if file_extension == ".xlsx" else "xlrd",
                na_values=["", "NA", "N/A", "null", "NULL", "None", "NONE"],
                keep_default_na=True,
            )
        except Exception as e:
            raise ValueError(f"Error processing Excel file: {str(e)}")

    else:
        raise ValueError(
            f"Unsupported file format: {file_extension}. Please upload a CSV or Excel file."
        )

    df.columns = [str(col).strip() for col in df.columns]

    records = clean_and_convert_dataframe(df)
    logger.info(f"Getting the records: {records}")

    return records


def clean_and_convert_dataframe(df: pd.DataFrame) -> List[Dict]:
    """
    Clean the dataframe and convert it to a list of dictionaries.

    Args:
        df: Pandas DataFrame to process

    Returns:
        List of dictionaries representing the cleaned data
    """
    # Drop fully empty rows
    df = df.dropna(how="all")

    # Handle empty dataframe
    if df.empty:
        return []

    # Replace NaN values with None for proper JSON serialization
    df = df.where(pd.notna(df), None)

    # Convert DataFrame to list of dictionaries
    records = df.to_dict(orient="records")

    # Strip whitespace from string values
    for record in records:
        for key, value in record.items():
            if isinstance(value, str):
                record[key] = value.strip()

    return records
