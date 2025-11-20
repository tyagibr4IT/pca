from app.services.normalizer import normalize_provider_response

def test_normalize_aws():
    payload = {"instances":[{"id":"i-1","type":"t2.micro","region":"us-east-1"}]}
    out = normalize_provider_response("aws", payload)
    assert out["provider"] == "aws"
    assert len(out["resources"]) == 1
    assert out["resources"][0]["size"] == "t2.micro"