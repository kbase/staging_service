"""
Generate a set of text files for testing filled with random ascii characters.
"""
import random
import string


def make_random_string(string_length: int) -> str:
    """
    Generate a string of random ascii letters of the given length
    """
    possible_letters = string.ascii_letters
    # ignore the SONAR warning below; this is just for generating test data, security is
    # not an issue.
    return "".join(random.choice(possible_letters) for i in range(string_length))  # NOSONAR


if __name__ == "__main__":
    for file_length in [1, 10, 100, 1000, 10000, 100000, 1000000, 10000000]:
        filename = f"sample-text-file-{file_length}"
        print(f"generating {filename}")
        with open(f"sample-text-file-{file_length}", "w", encoding="utf-8") as out:
            out.write(make_random_string(file_length))
