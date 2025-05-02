from io import BytesIO, StringIO
from pathlib import Path as FilePath
from typing import Dict, List

import httpx
import pandas as pd
from app.log import logger


async def forward_data(data: dict, url: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        response.raise_for_status()


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
