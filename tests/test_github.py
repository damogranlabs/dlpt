import os

import pytest


def test_create_file(tmp_path):
    CONTENT = "content"

    d = tmp_path / "sub"
    d.mkdir()
    p = d / "hello.txt"
    p.write_text(CONTENT)

    p2 = os.path.join(d, "hello2.txt")
    with open(p2, "w+") as writer:
        writer.write(CONTENT)
    assert os.path.exists(p2)

    assert p.read_text() == CONTENT
    assert len(list(tmp_path.iterdir())) == 1
