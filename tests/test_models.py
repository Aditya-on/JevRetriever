from jevretrieve import RetrievedDocument, RetrievalAction


def test_public_models():
    document = RetrievedDocument(
        document_id="1",
        text="hello",
        score=0.8,
    )
    assert document.document_id == "1"
    assert RetrievalAction.STOP.value == "STOP"
