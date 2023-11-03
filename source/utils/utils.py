import os

def open_windows_partition(
    letter,
    mode="rb",
    buffering=-1,
    encoding=None,
    errors=None,
    newline=None,
    closefd=True,
    opener=None,
):
    """
    Opens a partition of a windows drive letter in read binary mode by default
    """
    return open(
        fr"\\.\{letter}:", mode, buffering, encoding, errors, newline, closefd, opener
    )

def print_vailable_volume():    
    volumes = [chr(x) + ":" for x in range(65, 91) if os.path.exists(chr(x) + ":")]
    print("Available volumes:")
    for i in range(len(volumes)):
        print(f"{i + 1}/", volumes[i])
