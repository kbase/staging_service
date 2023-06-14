import io


def generate_null_file(size: int, name: str):
    """
    Generate a file full of 0 bytes, for testing different
    file size scenarios.

    e.g. generate_null_file(5100000000, "5.1g.out")
    """
    with open(name, "wb") as out:
        bw = io.BufferedWriter(out, 10000000)
        for i in range(size):
            bw.write(b"\0")
        bw.flush()
