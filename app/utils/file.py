from fastapi import HTTPException, UploadFile, status


async def read_file(
    file: UploadFile,
    encoding: str = "utf-8",
    max_size: int = 10 * 1024 * 1024,
    extension: str = ".txt",
):
    if not file.filename.endswith(extension):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"file file must be a text file with extension {extension}",
        )

    raw_text = await file.read()

    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="file is empty"
        )

    if len(raw_text) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"file is too large. Maximum size is {max_size} bytes",
        )

    try:
        return raw_text.decode(encoding)
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a UTF-8 encoded text file",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {e}",
        )
