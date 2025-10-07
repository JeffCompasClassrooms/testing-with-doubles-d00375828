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

        # verifies it returns 200 and JSON "[]" when DB has no squirrels
        def it_returns_200_and_empty_list_when_none(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            SquirrelDB_cls.return_value.getSquirrels.return_value = []

            h.handleSquirrelsIndex()

            h.send_response.assert_called_once_with(200)
            h.send_header.assert_any_call("Content-Type", "application/json")
            h.end_headers.assert_called_once()
            assert h.wfile.buffer == b"[]"

        # verifies UTF-8 round-trip for non-ASCII names in the JSON body
        def it_handles_utf8_names(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            SquirrelDB_cls.return_value.getSquirrels.return_value = [
                {"id": 1, "name": "Árvíztűrő", "size": "közepes"}
            ]

            h.handleSquirrelsIndex()

            body = h.wfile.buffer.decode("utf-8")
            data = json.loads(body)
            assert data[0]["name"] == "Árvíztűrő"


        # verifies DB errors bubble up (handler doesn't swallow exceptions)
        def it_bubbles_db_errors(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            SquirrelDB_cls.return_value.getSquirrels.side_effect = RuntimeError("boom")
            with pytest.raises(RuntimeError):
                h.handleSquirrelsIndex()


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

        # verifies that an empty dict (falsy) is treated as "not found"
        def it_treats_empty_dict_as_not_found(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            SquirrelDB_cls.return_value.getSquirrel.return_value = {}

            h.handle404 = SquirrelServerHandler.handle404.__get__(h, SquirrelServerHandler)
            h.handle404 = mocker.spy(h, "handle404")

            h.handleSquirrelsRetrieve("7")

            SquirrelDB_cls.return_value.getSquirrel.assert_called_once_with("7")
            h.handle404.assert_called_once_with()

        # verifies content-type header present on successful retrieve (JSON)
        def it_sets_json_content_type_on_success(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            SquirrelDB_cls.return_value.getSquirrel.return_value = {"id": 9, "name": "Nina", "size": "M"}

            h.handleSquirrelsRetrieve("9")

            h.send_header.assert_any_call("Content-Type", "application/json")


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

        # verifies DB errors from getSquirrel bubble up
        def it_bubbles_db_errors(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            SquirrelDB_cls.return_value.getSquirrel.side_effect = RuntimeError("db blew up")
            with pytest.raises(RuntimeError):
                h.handleSquirrelsRetrieve("123")

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

        # verifies that 201 response has no body and no Content-Type header is set
        def it_returns_201_with_no_body_and_no_content_type(handler_base, mocker):
            h = handler_base
            h.getRequestData.return_value = {"name": "Newt", "size": "medium"}
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")

            h.handleSquirrelsCreate()

            SquirrelDB_cls.return_value.createSquirrel.assert_called_once_with("Newt", "medium")
            h.send_response.assert_called_once_with(201)
            h.end_headers.assert_called_once()
            # ensure no Content-Type was set by create
            assert ("Content-Type", "application/json") not in [tuple(call.args) for call in h.send_header.mock_calls]
            assert h.wfile.buffer == b""

        # verifies DB errors from createSquirrel bubble up
        def it_bubbles_db_errors(handler_base, mocker):
            h = handler_base
            h.getRequestData.return_value = {"name": "Boomy", "size": "L"}
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            SquirrelDB_cls.return_value.createSquirrel.side_effect = RuntimeError("db error")
            with pytest.raises(RuntimeError):
                h.handleSquirrelsCreate()

        # verifies missing fields cause KeyError to bubble (no silent handling)
        def it_bubbles_keyerror_on_missing_field(handler_base, mocker):
            h = handler_base
            h.getRequestData.return_value = {"name": "NoSize"}  # 'size' missing
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            with pytest.raises(KeyError):
                h.handleSquirrelsCreate()



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

        # verifies getRequestData is only called after existence check passes
        def it_reads_body_only_after_squirrel_exists(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            # exists → True path
            SquirrelDB_cls.return_value.getSquirrel.return_value = {"id": "5", "name": "Old", "size": "S"}
            h.getRequestData.return_value = {"name": "Nova", "size": "L"}

            h.handleSquirrelsUpdate("5")

            # getSquirrel must be called, then getRequestData, then update
            SquirrelDB_cls.return_value.getSquirrel.assert_called_once_with("5")
            h.getRequestData.assert_called_once_with()
            SquirrelDB_cls.return_value.updateSquirrel.assert_called_once_with("5", "Nova", "L")

        # verifies falsy dict (empty {}) triggers 404 and no update call
        def it_treats_empty_dict_as_missing(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            SquirrelDB_cls.return_value.getSquirrel.return_value = {}

            h.handle404 = SquirrelServerHandler.handle404.__get__(h, SquirrelServerHandler)
            h.handle404 = mocker.spy(h, "handle404")

            h.handleSquirrelsUpdate("42")

            SquirrelDB_cls.return_value.updateSquirrel.assert_not_called()
            h.handle404.assert_called_once_with()

        # verifies DB errors propagate (during updateSquirrel)
        def it_bubbles_db_errors_from_update(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db = SquirrelDB_cls.return_value
            db.getSquirrel.return_value = {"id": "8"}
            h.getRequestData.return_value = {"name": "X", "size": "L"}
            db.updateSquirrel.side_effect = RuntimeError("update failed")

            with pytest.raises(RuntimeError):
                h.handleSquirrelsUpdate("8")


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

        # verifies falsy dict (empty {}) triggers 404 and no delete call
        def it_treats_empty_dict_as_missing(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            SquirrelDB_cls.return_value.getSquirrel.return_value = {}

            h.handle404 = SquirrelServerHandler.handle404.__get__(h, SquirrelServerHandler)
            h.handle404 = mocker.spy(h, "handle404")

            h.handleSquirrelsDelete("13")

            SquirrelDB_cls.return_value.deleteSquirrel.assert_not_called()
            h.handle404.assert_called_once_with()

        # verifies DB errors propagate (during deleteSquirrel)
        def it_bubbles_db_errors_from_delete(handler_base, mocker):
            h = handler_base
            SquirrelDB_cls = mocker.patch("squirrel_server.SquirrelDB")
            db = SquirrelDB_cls.return_value
            db.getSquirrel.return_value = {"id": "15"}
            db.deleteSquirrel.side_effect = RuntimeError("delete failed")

            with pytest.raises(RuntimeError):
                h.handleSquirrelsDelete("15")


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

        # verifies the handler writes the expected literal message
        def it_writes_exact_404_message(handler_base):
            h = handler_base
            h.handle404 = SquirrelServerHandler.handle404.__get__(h, SquirrelServerHandler)

            h.handle404()

            assert h.wfile.buffer == b"404 Not Found"

