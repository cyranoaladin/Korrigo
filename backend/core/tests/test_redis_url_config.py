from core import settings


def test_redis_url_quotes_password_special_characters():
    url = settings.build_redis_url(
        host="redis",
        port="6379",
        db="1",
        password="str@nge:p/ss#word",
    )

    assert url == "redis://:str%40nge%3Ap%2Fss%23word@redis:6379/1"


def test_redis_url_without_password_keeps_auth_segment_absent():
    assert settings.build_redis_url(host="redis", port="6379", db="0") == (
        "redis://redis:6379/0"
    )
