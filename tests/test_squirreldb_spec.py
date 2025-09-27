import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import pytest

from squirrel_server import SquirrelServerHandler



# Tiny fake buffer

class _FakeWFile:
    def __init__(self):
        self.buffer = b""
    def write(self, data: bytes):
        self.buffer += data


@pytest.fixture
def handler_base(mocker):
    """
    Partially-constructed handler: no real BaseHTTPRequestHandler init.
    We inject HTTP I/O doubles; DB is patched per test.
    """
    h = object.__new__(SquirrelServerHandler)
    h.send_response = mocker.Mock()
    h.send_header   = mocker.Mock()
    h.end_headers   = mocker.Mock()
    h.wfile         = _FakeWFile()
    h.getRequestData = mocker.Mock()
    h.parsePath      = mocker.Mock()
    h.command = "GET"
    h.path    = "/squirrels"
    return h


def describe_SquirrelServerHandler():

    #  handleSquirrelsIndex 
    def describe_handleSquirrelsIndex():
        def it_returns_200_and_json_list(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db_instance = SquirrelDB_cls.return_value
            db_instance.getSquirrels.return_value = [
                {"id": 1, "name": "Nutmeg", "size": "smol"},
                {"id": 2, "name": "Chonk",  "size": "thicc"},
            ]

            h.handleSquirrelsIndex()

            SquirrelDB_cls.assert_called_once_with()
            db_instance.getSquirrels.assert_called_once_with()

            h.send_response.assert_called_once_with(200)
            h.send_header.assert_any_call("Content-Type", "application/json")
            h.end_headers.assert_called_once()
            body = json.loads(h.wfile.buffer.decode("utf-8"))
            assert body[0]["name"] == "Nutmeg"

    #  handleSquirrelsRetrieve 
    def describe_handleSquirrelsRetrieve():
        def it_returns_200_and_json_when_found(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db_instance = SquirrelDB_cls.return_value
            db_instance.getSquirrel.return_value = {"id": "2", "name": "Chonk", "size": "thicc"}

            h.handleSquirrelsRetrieve("2") 

            SquirrelDB_cls.assert_called_once_with()
            db_instance.getSquirrel.assert_called_once_with("2")

            h.send_response.assert_called_once_with(200)
            h.send_header.assert_any_call("Content-Type", "application/json")
            h.end_headers.assert_called_once()
            body = json.loads(h.wfile.buffer.decode("utf-8"))
            assert body["id"] == "2"

        def it_calls_handle404_when_not_found(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db_instance = SquirrelDB_cls.return_value
            db_instance.getSquirrel.return_value = None

            h.handle404 = SquirrelServerHandler.handle404.__get__(h, SquirrelServerHandler)
            h.handle404 = mocker.spy(h, "handle404")

            h.handleSquirrelsRetrieve("999")

            db_instance.getSquirrel.assert_called_once_with("999")
            h.handle404.assert_called_once_with()

    # handleSquirrelsCreate
    def describe_handleSquirrelsCreate():
        def it_creates_and_returns_201(handler_base, mocker):
            h = handler_base
            h.getRequestData.return_value = {"name": "Newt", "size": "medium"}
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db_instance = SquirrelDB_cls.return_value

            h.handleSquirrelsCreate()

            SquirrelDB_cls.assert_called_once_with()
            db_instance.createSquirrel.assert_called_once_with("Newt", "medium")
            h.send_response.assert_called_once_with(201)
            h.end_headers.assert_called_once()
            assert h.wfile.buffer == b""

    #  handleSquirrelsUpdate
    def describe_handleSquirrelsUpdate():
        def it_updates_and_returns_204_when_found(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db_instance = SquirrelDB_cls.return_value
            db_instance.getSquirrel.return_value = {"id": "3", "name": "Old", "size": "M"}
            h.getRequestData.return_value = {"name": "Updated", "size": "XL"}

            h.handleSquirrelsUpdate("3")

            db_instance.getSquirrel.assert_called_once_with("3")
            db_instance.updateSquirrel.assert_called_once_with("3", "Updated", "XL")
            h.send_response.assert_called_once_with(204)
            h.end_headers.assert_called_once()
            assert h.wfile.buffer == b""

        def it_calls_handle404_when_missing(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db_instance = SquirrelDB_cls.return_value
            db_instance.getSquirrel.return_value = None

            h.handle404 = SquirrelServerHandler.handle404.__get__(h, SquirrelServerHandler)
            h.handle404 = mocker.spy(h, "handle404")

            h.handleSquirrelsUpdate("404")

            db_instance.getSquirrel.assert_called_once_with("404")
            db_instance.updateSquirrel.assert_not_called()
            h.handle404.assert_called_once_with()

    #  handleSquirrelsDelete 
    def describe_handleSquirrelsDelete():
        def it_deletes_and_returns_204_when_found(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db_instance = SquirrelDB_cls.return_value
            db_instance.getSquirrel.return_value = {"id": "4", "name": "Nutty", "size": "S"}

            h.handleSquirrelsDelete("4")

            db_instance.getSquirrel.assert_called_once_with("4")
            db_instance.deleteSquirrel.assert_called_once_with("4")
            h.send_response.assert_called_once_with(204)
            h.end_headers.assert_called_once()
            assert h.wfile.buffer == b""

        def it_calls_handle404_when_missing(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db_instance = SquirrelDB_cls.return_value
            db_instance.getSquirrel.return_value = None

            h.handle404 = SquirrelServerHandler.handle404.__get__(h, SquirrelServerHandler)
            h.handle404 = mocker.spy(h, "handle404")

            h.handleSquirrelsDelete("404")

            db_instance.getSquirrel.assert_called_once_with("404")
            db_instance.deleteSquirrel.assert_not_called()
            h.handle404.assert_called_once_with()

    #  handle404 error
    def describe_handle404():
        def it_writes_minimal_404_response(handler_base):
            h = handler_base
            # Use the real method
            h.handle404 = SquirrelServerHandler.handle404.__get__(h, SquirrelServerHandler)

            h.handle404()

            h.send_response.assert_called_once_with(404)
            h.send_header.assert_any_call("Content-Type", "text/plain")
            h.end_headers.assert_called_once()
            assert h.wfile.buffer 
